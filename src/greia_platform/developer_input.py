from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from .boot_markers import spool_path
from .developer_session import DeveloperDisplayEndpoint, DeveloperSessionError


DEVELOPER_MARKER = Path("/etc/greia-os/developer-remote")
_KEY_RE = re.compile(r"^[A-Za-z0-9_+.:=-]{1,64}$")

# --- Bounded pre-armed at-boot intro motion sweep (FIX-INTRO-INJECTOR) ---
#
# Developer-image-only one-shot injector. The operator arms the sweep via the
# bounded ``greia-devctl arm-intro-sweep`` verb before reboot; the at-boot
# ``greia-intro-sweep`` helper fires it once during the next live intro and
# disarms itself even on failure. SSH (and any xdotool driven over it) is only
# up after the ~7 s intro completes, so reboot+SSH polling can never inject
# motion inside the window; the pre-armed one-shot is the only path.
#
# Design bounds (all stated for the PROVE-INTRO-DRAIN-R burst verdict):
# - fixed small step count INTRO_SWEEP_STEP_COUNT with pacing
#   INTRO_SWEEP_STEP_INTERVAL_SECONDS between steps;
# - intro-enter observation window INTRO_SWEEP_WAIT_FOR_INTRO_TIMEOUT_SECONDS,
#   after which the sweep still fires once (launcher-start-with-deadline
#   fallback) so the one-shot is never left armed across boots;
# - worst-case occupancy WAIT + COUNT * INTERVAL stays below the ~7 s intro;
# - geometry stays inside the 1024x600 reference display;
# - transport is exactly the fixed ``xdotool mousemove --sync`` path below as
#   the declared display user (no clicks, keys, or text).

#: Fixed small step count for the bounded sweep.
INTRO_SWEEP_STEP_COUNT = 10
#: Pacing between sweep steps; the sweep itself, never boot orchestration.
INTRO_SWEEP_STEP_INTERVAL_SECONDS = 0.2
#: Hard deadline waiting for a fresh ``intro_enter`` spool observation.
INTRO_SWEEP_WAIT_FOR_INTRO_TIMEOUT_SECONDS = 3.0
#: Sweep geometry inside the 1024x600 reference display (mid-line horizontal).
INTRO_SWEEP_Y = 300
INTRO_SWEEP_X_START = 112
INTRO_SWEEP_X_END = 912
#: Timestamp log bounds (mirrors the boot-marker spool budget).
INTRO_SWEEP_LOG_MAX_LINES = 200
INTRO_SWEEP_LOG_MAX_BYTES = 64 * 1024
#: One-shot arm file. Persistent developer state (not tmpfs) so arm-before-
#: reboot survives the reboot; consumed (unlinked) on the single fire.
#: (The brief text says "volatile state", but a tmpfs arm would be wiped by
#: the very reboot that must carry it to the next intro, so persistence here
#: is required for the arm-before-reboot contract to hold at all.)
INTRO_SWEEP_ARM_DEFAULT = Path("/var/lib/greia-developer/intro-sweep.armed")
#: Bounded per-step timestamp log for the burst verdict.
INTRO_SWEEP_LOG_DEFAULT = Path("/var/lib/greia-developer/intro-sweep.log")


@dataclass(frozen=True, slots=True)
class IntroSweepResult:
    """Outcome of one :func:`run_intro_sweep` invocation.

    ``fired`` is True only when an arm file was consumed and at least the
    fire path was entered; ``steps`` counts mousemove steps actually issued.
    ``reason`` is a short machine-stable token for tests and the log verb.
    """

    fired: bool
    steps: int
    reason: str


def intro_sweep_arm_path() -> Path:
    """Return the active one-shot arm path (test override aware)."""
    override = os.environ.get("GREIA_INTRO_SWEEP_ARM")
    if override:
        return Path(override)
    return INTRO_SWEEP_ARM_DEFAULT


def intro_sweep_log_path() -> Path:
    """Return the active sweep timestamp-log path (test override aware)."""
    override = os.environ.get("GREIA_INTRO_SWEEP_LOG")
    if override:
        return Path(override)
    return INTRO_SWEEP_LOG_DEFAULT


def intro_sweep_coordinates() -> list[tuple[int, int]]:
    """Return the fixed bounded sweep geometry inside 1024x600."""
    count = INTRO_SWEEP_STEP_COUNT
    if count <= 1:
        return [(INTRO_SWEEP_X_START, INTRO_SWEEP_Y)]
    span = INTRO_SWEEP_X_END - INTRO_SWEEP_X_START
    return [
        (
            INTRO_SWEEP_X_START + round(span * index / (count - 1)),
            INTRO_SWEEP_Y,
        )
        for index in range(count)
    ]


def arm_intro_sweep(*, arm_path: Path | None = None) -> Path:
    """Arm the one-shot at-boot intro sweep. Fail-closed on non-developer images."""
    if not DEVELOPER_MARKER.is_file():
        raise DeveloperInputError(
            "developer remote control is not enabled on this image"
        )
    path = arm_path if arm_path is not None else intro_sweep_arm_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    path.write_text(
        f"armed utc={stamp} monotonic_ns={time.monotonic_ns()}\n",
        encoding="utf-8",
    )
    try:
        os.chmod(path, 0o600)
    except OSError as exc:
        raise DeveloperInputError(f"cannot seal intro-sweep arm file: {exc}") from exc
    return path


def _append_intro_sweep_log(line: str, *, log_path: Path | None = None) -> None:
    """Append one timestamp line to the sweep log, enforcing bounds. Never raises."""
    try:
        path = log_path if log_path is not None else intro_sweep_log_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            return
        try:
            if path.stat().st_size <= INTRO_SWEEP_LOG_MAX_BYTES:
                needs_trim = False
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        for index, _ in enumerate(handle):
                            if index >= INTRO_SWEEP_LOG_MAX_LINES:
                                needs_trim = True
                                break
                except OSError:
                    return
                if not needs_trim:
                    return
        except OSError:
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        tail = text.splitlines()[-INTRO_SWEEP_LOG_MAX_LINES:]
        try:
            path.write_text("\n".join(tail) + "\n", encoding="utf-8")
        except OSError:
            pass
    except Exception:  # noqa: BLE001 - sweep evidence must never fail boot
        pass


def read_intro_sweep_log_text(*, log_path: Path | None = None) -> str:
    """Return the current sweep-log content, bounded. Never raises."""
    try:
        path = log_path if log_path is not None else intro_sweep_log_path()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        lines = text.splitlines()
        if len(lines) > INTRO_SWEEP_LOG_MAX_LINES:
            lines = lines[-INTRO_SWEEP_LOG_MAX_LINES:]
        capped = "\n".join(lines)
        raw = capped.encode("utf-8")
        if len(raw) > INTRO_SWEEP_LOG_MAX_BYTES:
            raw = raw[-INTRO_SWEEP_LOG_MAX_BYTES:]
            capped = raw.decode("utf-8", errors="replace")
            if "\n" in capped:
                capped = capped.split("\n", 1)[1]
        if capped and not capped.endswith("\n"):
            capped += "\n"
        return capped
    except Exception:  # noqa: BLE001 - retrieval must never fail callers
        return ""


def wait_for_intro_enter(
    *,
    timeout_seconds: float = INTRO_SWEEP_WAIT_FOR_INTRO_TIMEOUT_SECONDS,
    poll_interval_seconds: float = 0.05,
) -> bool:
    """Wait up to ``timeout_seconds`` for a fresh ``intro_enter`` spool line.

    The spool is tmpfs-fresh each boot, so any ``intro_enter`` line is from
    the current boot. Returns False on timeout; the caller still fires once
    (launcher-start-with-deadline fallback) so the one-shot is never left
    armed across boots. Never raises.
    """
    try:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while True:
            try:
                text = spool_path().read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            if "event=intro_enter" in text:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(poll_interval_seconds)
    except Exception:  # noqa: BLE001 - waiting must never fail boot
        return False


def run_intro_sweep(
    *,
    arm_path: Path | None = None,
    log_path: Path | None = None,
    wait_timeout_seconds: float = INTRO_SWEEP_WAIT_FOR_INTRO_TIMEOUT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> IntroSweepResult:
    """Fire the armed one-shot sweep once, then disarm even on failure.

    Never raises: every error path consumes the arm file (when present) and
    returns a non-firing or partially-firing result, so boot is unaffected
    and the one-shot can never fire twice.
    """
    arm = arm_path if arm_path is not None else intro_sweep_arm_path()
    log = log_path if log_path is not None else intro_sweep_log_path()

    def _disarm() -> None:
        try:
            arm.unlink(missing_ok=True)
        except OSError:
            pass

    try:
        if not DEVELOPER_MARKER.is_file():
            _disarm()
            return IntroSweepResult(fired=False, steps=0, reason="non-developer-image")
        if not arm.is_file():
            return IntroSweepResult(fired=False, steps=0, reason="not-armed")
        # Intro-bound trigger with a hard deadline; on timeout the sweep
        # still fires once so the arm is never carried to a later boot.
        wait_for_intro_enter(timeout_seconds=wait_timeout_seconds)
        coordinates = intro_sweep_coordinates()
        steps = 0
        try:
            total = len(coordinates)
            for index, (x, y) in enumerate(coordinates):
                try:
                    mousemove(x, y)
                except DeveloperInputError:
                    break
                steps += 1
                stamp = datetime.now(timezone.utc).isoformat()
                _append_intro_sweep_log(
                    f"INTRO_SWEEP step={steps}/{total} x={x} y={y} "
                    f"utc={stamp} monotonic_ns={time.monotonic_ns()}",
                    log_path=log,
                )
                if index < total - 1:
                    sleep(INTRO_SWEEP_STEP_INTERVAL_SECONDS)
        finally:
            _disarm()
        return IntroSweepResult(fired=True, steps=steps, reason="fired")
    except Exception:  # noqa: BLE001 - the sweep must never fail boot
        _disarm()
        return IntroSweepResult(fired=False, steps=0, reason="error")


class DeveloperInputError(RuntimeError):
    """Raised when development-only GUI input injection must fail closed."""


def _developer_endpoint() -> DeveloperDisplayEndpoint:
    if os.geteuid() != 0:
        raise DeveloperInputError(
            "developer input helper must run through greia-devctl sudo"
        )
    if not DEVELOPER_MARKER.is_file():
        raise DeveloperInputError(
            "developer remote control is not enabled on this image"
        )
    try:
        return DeveloperDisplayEndpoint.load()
    except DeveloperSessionError as exc:
        raise DeveloperInputError(str(exc)) from exc


def _run_xdotool(args: Sequence[str]) -> None:
    endpoint = _developer_endpoint()
    argv = [
        *endpoint.runuser_prefix(),
        "/usr/bin/xdotool",
        *args,
    ]
    completed = subprocess.run(argv, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise DeveloperInputError(
            f"xdotool failed with status {completed.returncode}: {completed.stderr.strip()}"
        )


def key(keys: Sequence[str]) -> None:
    if not keys or len(keys) > 16:
        raise DeveloperInputError("key accepts between 1 and 16 key expressions")
    for value in keys:
        if not _KEY_RE.fullmatch(value):
            raise DeveloperInputError(f"invalid xdotool key expression: {value!r}")
    _run_xdotool(["key", "--clearmodifiers", *keys])


def mousemove(x: int, y: int) -> None:
    for name, value in (("x", x), ("y", y)):
        if isinstance(value, bool) or value < 0 or value > 16384:
            raise DeveloperInputError(
                f"mouse {name} coordinate must be between 0 and 16384"
            )
    _run_xdotool(["mousemove", "--sync", str(x), str(y)])


def click(button: int) -> None:
    if isinstance(button, bool) or button < 1 or button > 5:
        raise DeveloperInputError("mouse button must be between 1 and 5")
    _run_xdotool(["click", "--clearmodifiers", str(button)])


def type_text(text: str) -> None:
    if (
        not text
        or len(text) > 512
        or "\x00" in text
        or "\n" in text
        or "\r" in text
    ):
        raise DeveloperInputError("typed text must be 1..512 characters on one line")
    _run_xdotool(["type", "--clearmodifiers", "--delay", "10", "--", text])


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Greia development-only GUI input control"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    key_parser = sub.add_parser("key")
    key_parser.add_argument("keys", nargs="+")
    move = sub.add_parser("mousemove")
    move.add_argument("x", type=int)
    move.add_argument("y", type=int)
    click_parser = sub.add_parser("click")
    click_parser.add_argument("button", type=int, nargs="?", default=1)
    type_parser = sub.add_parser("type")
    type_parser.add_argument("text")
    sub.add_parser(
        "run-intro-sweep",
        help="fire the armed one-shot intro sweep (at-boot helper entry point)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "key":
            key(args.keys)
        elif args.command == "mousemove":
            mousemove(args.x, args.y)
        elif args.command == "click":
            click(args.button)
        elif args.command == "type":
            type_text(args.text)
        elif args.command == "run-intro-sweep":
            # At-boot one-shot: always fail-closed to exit 0 semantics via
            # run_intro_sweep's never-raises contract; the shell wrapper adds
            # `|| true` so no failure mode reaches boot.
            run_intro_sweep()
        else:  # pragma: no cover
            raise DeveloperInputError("unsupported input command")
    except DeveloperInputError as exc:
        print(f"greia-devctl: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
