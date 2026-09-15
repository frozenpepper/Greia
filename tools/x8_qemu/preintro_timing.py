"""POSTR1-P3-UPDATE-ACTIVATION additive pre-intro timing instrumentation.

Preregistered pre-intro comparison for the update-activation change:
``power/QEMU-start -> first visible intro frame`` and
``intro start/end -> interactive ready`` must show no regression relative
to the pre-change baseline, with the seven-second intro fixed.

Additive only (T7 scope): this module adds timing predicates/collection
without touching the disposable lifecycle harness (``lifecycle.py``,
``runner.py``, ``bootchain.py``) or its recorded evidence.

Preregistration record (fixed BEFORE observation, 2026-09-12):
  P1 power_to_first_frame_no_regression:
      activated.t_first_frame <= baseline.t_first_frame + max(2.0, 5% of baseline)
  P2 intro_duration_unchanged:
      |activated.intro - 7.0| <= 0.5s AND |activated.intro - baseline.intro| <= 0.5s
      (intro = t_intro_end - t_first_frame; the intro itself is fixed)
  P3 interactive_ready_reached:
      both runs observe INTERACTIVE_READY within the boot timeout
  P4 no_update_work_pre_intro:
      no UPDATE_SERVICE_STARTED marker before FIRST_INTRO_FRAME in the
      activated run (normal boot with no candidate performs no update work
      before the first frame)

Interpretation rule (frozen): ALL of P1..P4 must be PASS for the comparison
to support the activation. Any FAIL is a red result: it must be preserved
and escalated, never narrowed, waived, or reinterpreted. Any missing
marker or missing facility yields NOT_READY/BLOCKED, never a pass.

Guest-marker contract (canonical): the disposable boot forwards the guest
serial stream and this instrument matches the single-owner production
marker shape ``GREIA_BOOT event=<name> monotonic_ns=<int>`` emitted only
via ``src/greia_platform/boot_markers.py::emit_boot_marker``. Defaults:

- first frame = ``intro_first_frame_flipped``
  (``src/greia_launcher/boot_intro.py`` first visible flip);
- intro end = ``intro_end`` (``run_intro()`` finally block);
- interactive ready = ``launcher_interactive_ready``
  (``LauncherApplication.apply_prepared_state`` at the real
  ``INTERACTIVE_READY`` guard transition);
- update work = the systemd ``Started Greia OS system-update`` line
  (kept as a journal/serial pattern because the update service owns no
  ``GREIA_BOOT`` event; absence means no pre-intro update work, never a
  failure).

Each default is overridable via repeated ``--marker NAME=PATTERN`` flags
(and via the ``markers`` argument of :func:`measure_boot`). Absent markers
are NOT_READY, never interpolated.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

PREREGISTERED_DATE = "2026-09-12"

#: Fixed intro length in seconds (5 s animation + 2 s hold, see
#: ``src/greia_launcher/boot_intro.py``). The timing comparison must not
#: shorten it to improve the metric.
FIXED_INTRO_SECONDS = 7.0

#: Frozen regression tolerances (fixed before observation).
FIRST_FRAME_TOLERANCE_FLOOR_SECONDS = 2.0
FIRST_FRAME_TOLERANCE_RATIO = 0.05
INTRO_TOLERANCE_SECONDS = 0.5

#: Canonical ``GREIA_BOOT`` event names consumed by this instrument. These
#: must stay equal to the production emitters
#: (``src/greia_launcher/boot_intro.py`` for the intro pair,
#: ``LauncherApplication.apply_prepared_state`` for interactive-ready) and
#: to the ``KNOWN_EVENTS`` vocabulary in
#: ``tools/boot/analyze_boot_markers.py``. Enforced by
#: ``tests/test_update_activation_contract.py``.
CANONICAL_FIRST_FRAME_EVENT = "intro_first_frame_flipped"
CANONICAL_INTRO_END_EVENT = "intro_end"
CANONICAL_INTERACTIVE_READY_EVENT = "launcher_interactive_ready"


def _load_canonical_marker_module():  # type: ignore[no-untyped-def]
    """Load ``tools/boot/analyze_boot_markers.py`` without a package import.

    ``tools/`` has no ``__init__.py``, so a regular package import fails
    when this file runs as a script. Loading by file location keeps one
    shared parser/constants owner (``analyze_boot_markers``) while staying
    runnable as ``python3 tools/x8_qemu/preintro_timing.py``. Returns None
    when the sibling file is unavailable (the hardcoded canonical names
    above remain the contract, enforced by tests).
    """
    try:
        candidate = (
            Path(__file__).resolve().parents[1] / "boot" / "analyze_boot_markers.py"
        )
        if not candidate.is_file():
            return None
        spec = importlib.util.spec_from_file_location(
            "greia_canonical_boot_markers", candidate
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["greia_canonical_boot_markers"] = module
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            sys.modules.pop("greia_canonical_boot_markers", None)
            return None
        return module
    except Exception:  # noqa: BLE001 - canonical sharing is best-effort
        return None


_CANONICAL_MODULE = _load_canonical_marker_module()

#: Default guest serial markers (overridable; absence is NOT_READY). The
#: three Greia markers match the canonical ``GREIA_BOOT event=<name>``
#: line shape; the update marker matches the systemd start line because
#: the update service owns no ``GREIA_BOOT`` event.
DEFAULT_MARKERS = {
    "first_intro_frame": r"GREIA_BOOT event=intro_first_frame_flipped\b",
    "intro_end": r"GREIA_BOOT event=intro_end\b",
    "interactive_ready": r"GREIA_BOOT event=launcher_interactive_ready\b",
    "update_service_started": r"Started Greia OS system-update",
}

#: Logical marker key -> canonical ``GREIA_BOOT`` event name. The update
#: key maps to None: it is intentionally a non-``GREIA_BOOT`` journal
#: pattern (no canonical event exists for it).
MARKER_TO_CANONICAL_EVENT: dict[str, str | None] = {
    "first_intro_frame": CANONICAL_FIRST_FRAME_EVENT,
    "intro_end": CANONICAL_INTRO_END_EVENT,
    "interactive_ready": CANONICAL_INTERACTIVE_READY_EVENT,
    "update_service_started": None,
}

POLL_INTERVAL_SECONDS = 0.05


class PreIntroTimingError(RuntimeError):
    """Pre-intro timing measurement failed fail-closed."""


def require_timing_host(*, qemu_binary: str = "qemu-system-x86_64") -> str:
    """Fail closed unless this host can run a disposable QEMU boot."""
    if sys.platform != "linux":
        raise PreIntroTimingError(
            "BLOCKED: pre-intro timing needs a Linux host with "
            f"{qemu_binary} and the disposable-boot facility "
            f"(this host reports {sys.platform})"
        )
    resolved = shutil.which(qemu_binary)
    if resolved is None:
        for candidate in (f"/usr/bin/{qemu_binary}", f"/usr/local/bin/{qemu_binary}"):
            if Path(candidate).is_file():
                resolved = candidate
                break
    if resolved is None:
        raise PreIntroTimingError(
            f"BLOCKED: pre-intro timing needs {qemu_binary} on PATH "
            "(disposable-boot facility missing)"
        )
    return resolved


def parse_marker_override(raw: str) -> tuple[str, str]:
    """Parse one ``--marker NAME=PATTERN`` override (raises on misuse)."""
    name, separator, pattern = raw.partition("=")
    name = name.strip()
    if not separator or not name or not pattern:
        raise PreIntroTimingError(
            f"invalid --marker override {raw!r}: expected NAME=PATTERN"
        )
    if name not in DEFAULT_MARKERS:
        raise PreIntroTimingError(
            f"unknown marker name {name!r}: expected one of "
            f"{sorted(DEFAULT_MARKERS)}"
        )
    try:
        re.compile(pattern)
    except re.error as exc:
        raise PreIntroTimingError(
            f"invalid --marker regex for {name!r}: {exc}"
        ) from exc
    return name, pattern


def scan_serial_text(
    text: str,
    markers: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    """Return which markers appear anywhere in a serial-log text snapshot.

    Pure helper over the same ``DEFAULT_MARKERS`` regexes :func:`measure_boot`
    polls live, so synthetic canonical streams can drive the instrument
    without QEMU. Matching is first-appearance existence (timestamps come
    from the live poll or from :class:`BootMeasurement` construction).
    """
    active = dict(DEFAULT_MARKERS)
    if markers:
        active.update(markers)
    compiled = {name: re.compile(pattern) for name, pattern in active.items()}
    return {
        name: compiled[name].search(text) is not None for name in compiled
    }


@dataclass(frozen=True, slots=True)
class BootMeasurement:
    """One disposable boot timing observation (seconds, host monotonic)."""

    label: str
    qemu_start_monotonic: float
    first_intro_frame: float | None
    intro_end: float | None
    interactive_ready: float | None
    update_service_started: float | None
    timed_out: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "pre-intro-timing-v1",
            "label": self.label,
            "qemu_start_monotonic": self.qemu_start_monotonic,
            "first_intro_frame": self.first_intro_frame,
            "intro_end": self.intro_end,
            "interactive_ready": self.interactive_ready,
            "update_service_started": self.update_service_started,
            "timed_out": self.timed_out,
        }

    @staticmethod
    def from_dict(raw: dict[str, object]) -> "BootMeasurement":
        if raw.get("schema") != "pre-intro-timing-v1":
            raise PreIntroTimingError("measurement record schema mismatch")
        return BootMeasurement(
            label=str(raw["label"]),
            qemu_start_monotonic=float(raw["qemu_start_monotonic"]),  # type: ignore[arg-type]
            first_intro_frame=_maybe_float(raw.get("first_intro_frame")),
            intro_end=_maybe_float(raw.get("intro_end")),
            interactive_ready=_maybe_float(raw.get("interactive_ready")),
            update_service_started=_maybe_float(raw.get("update_service_started")),
            timed_out=bool(raw["timed_out"]),
        )


def _maybe_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)  # type: ignore[arg-type]


def measure_boot(
    *,
    label: str,
    qemu_argv: list[str],
    serial_log: Path,
    timeout_seconds: int = 300,
    markers: dict[str, str] | None = None,
    qemu_binary: str = "qemu-system-x86_64",
) -> BootMeasurement:
    """Boot one disposable image under QEMU and time the pre-intro markers.

    Spawns ``qemu_argv`` (which must write the guest serial stream to
    ``serial_log``), records the host-monotonic QEMU start, and polls the
    serial log for each marker, stamping first appearance. Stops at
    INTERACTIVE_READY or the timeout. Requires the Linux+QEMU facility;
    anything missing raises :class:`PreIntroTimingError` (BLOCKED).
    """
    require_timing_host(qemu_binary=qemu_binary)
    active = dict(DEFAULT_MARKERS)
    if markers:
        active.update(markers)
    compiled = {name: re.compile(pattern) for name, pattern in active.items()}
    serial_log = Path(serial_log)
    if serial_log.exists():
        raise PreIntroTimingError(
            f"refusing to reuse an existing serial log: {serial_log}"
        )
    serial_log.parent.mkdir(parents=True, exist_ok=True)
    serial_log.touch()
    found: dict[str, float | None] = {name: None for name in compiled}
    start = time.monotonic()
    process = subprocess.Popen(
        [str(part) for part in qemu_argv],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    timed_out = False
    try:
        deadline = start + timeout_seconds
        offset = 0
        while time.monotonic() < deadline:
            if process.poll() is not None and found["interactive_ready"] is not None:
                break
            with serial_log.open("rb") as handle:
                handle.seek(offset)
                chunk = handle.read()
                offset += len(chunk)
            if chunk:
                text = chunk.decode("utf-8", "ignore")
                now = time.monotonic()
                for name, pattern in compiled.items():
                    if found[name] is None and pattern.search(text):
                        found[name] = now
            if found["interactive_ready"] is not None:
                break
            if process.poll() is not None:
                break
            time.sleep(POLL_INTERVAL_SECONDS)
        else:
            timed_out = found["interactive_ready"] is None
        if found["interactive_ready"] is None and time.monotonic() >= deadline:
            timed_out = True
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
    return BootMeasurement(
        label=label,
        qemu_start_monotonic=start,
        first_intro_frame=found["first_intro_frame"],
        intro_end=found["intro_end"],
        interactive_ready=found["interactive_ready"],
        update_service_started=found["update_service_started"],
        timed_out=timed_out,
    )


def _elapsed(start: float, stamp: float | None) -> float | None:
    if stamp is None:
        return None
    return stamp - start


def compare(
    baseline: BootMeasurement, activated: BootMeasurement
) -> dict[str, object]:
    """Interpret one baseline/activated pair against the frozen predicates."""
    predicates: dict[str, dict[str, object]] = {}
    base_first = _elapsed(baseline.qemu_start_monotonic, baseline.first_intro_frame)
    act_first = _elapsed(activated.qemu_start_monotonic, activated.first_intro_frame)
    if base_first is None or act_first is None:
        predicates["P1_power_to_first_frame_no_regression"] = {
            "verdict": "NOT_READY",
            "detail": "FIRST_INTRO_FRAME marker missing in "
            + ("baseline" if base_first is None else "activated")
            + " run; absence is never a pass",
        }
    else:
        tolerance = max(
            FIRST_FRAME_TOLERANCE_FLOOR_SECONDS,
            FIRST_FRAME_TOLERANCE_RATIO * base_first,
        )
        predicates["P1_power_to_first_frame_no_regression"] = {
            "verdict": "PASS" if act_first <= base_first + tolerance else "FAIL",
            "detail": f"baseline={base_first:.2f}s activated={act_first:.2f}s "
            f"tolerance=+{tolerance:.2f}s",
        }
    base_intro = (
        None
        if baseline.first_intro_frame is None or baseline.intro_end is None
        else baseline.intro_end - baseline.first_intro_frame
    )
    act_intro = (
        None
        if activated.first_intro_frame is None or activated.intro_end is None
        else activated.intro_end - activated.first_intro_frame
    )
    if base_intro is None or act_intro is None:
        predicates["P2_intro_duration_unchanged"] = {
            "verdict": "NOT_READY",
            "detail": "intro start/end markers missing; absence is never a pass",
        }
    else:
        fixed_ok = abs(act_intro - FIXED_INTRO_SECONDS) <= INTRO_TOLERANCE_SECONDS
        stable_ok = abs(act_intro - base_intro) <= INTRO_TOLERANCE_SECONDS
        predicates["P2_intro_duration_unchanged"] = {
            "verdict": "PASS" if (fixed_ok and stable_ok) else "FAIL",
            "detail": f"baseline={base_intro:.2f}s activated={act_intro:.2f}s "
            f"fixed={FIXED_INTRO_SECONDS:.2f}s",
        }
    if baseline.interactive_ready is None or activated.interactive_ready is None:
        predicates["P3_interactive_ready_reached"] = {
            "verdict": "NOT_READY",
            "detail": "INTERACTIVE_READY marker missing in "
            + ("baseline" if baseline.interactive_ready is None else "activated")
            + " run",
        }
    else:
        predicates["P3_interactive_ready_reached"] = {
            "verdict": "PASS",
            "detail": "interactive ready observed in both runs",
        }
    if activated.first_intro_frame is None:
        predicates["P4_no_update_work_pre_intro"] = {
            "verdict": "NOT_READY",
            "detail": "FIRST_INTRO_FRAME marker missing; cannot order update work",
        }
    elif activated.update_service_started is not None and (
        activated.first_intro_frame is None
        or activated.update_service_started < activated.first_intro_frame
    ):
        predicates["P4_no_update_work_pre_intro"] = {
            "verdict": "FAIL",
            "detail": "update service started before the first intro frame",
        }
    else:
        predicates["P4_no_update_work_pre_intro"] = {
            "verdict": "PASS",
            "detail": "no update-service start observed before the first frame",
        }
    verdicts = [str(info["verdict"]) for info in predicates.values()]
    overall = (
        "PASS"
        if all(verdict == "PASS" for verdict in verdicts)
        else ("NOT_READY" if "NOT_READY" in verdicts else "FAIL")
    )
    return {
        "schema": "pre-intro-timing-comparison-v1",
        "preregistered": PREREGISTERED_DATE,
        "predicates": predicates,
        "overall": overall,
        "baseline": baseline.as_dict(),
        "activated": activated.as_dict(),
    }


def _preregistration_text() -> str:
    lines = [
        "POSTR1-P3-UPDATE-ACTIVATION preregistered pre-intro timing predicates",
        f"preregistered: {PREREGISTERED_DATE} (fixed before observation)",
        "P1 power_to_first_frame_no_regression: "
        "activated <= baseline + max("
        f"{FIRST_FRAME_TOLERANCE_FLOOR_SECONDS:.1f}s, "
        f"{FIRST_FRAME_TOLERANCE_RATIO:.0%} of baseline)",
        "P2 intro_duration_unchanged: |activated - 7.0s| <= "
        f"{INTRO_TOLERANCE_SECONDS:.1f}s AND |activated - baseline| <= "
        f"{INTRO_TOLERANCE_SECONDS:.1f}s",
        "P3 interactive_ready_reached: observed in both runs within timeout",
        "P4 no_update_work_pre_intro: no update-service start before first frame",
        "interpretation: ALL must PASS; any FAIL is red (preserve+escalate); "
        "any missing marker/facility is NOT_READY/BLOCKED, never a pass",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preregistered pre-intro timing for update activation"
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("preregister", help="print the frozen predicates")
    measure = sub.add_parser("measure", help="time one disposable QEMU boot")
    measure.add_argument("--label", required=True)
    measure.add_argument("--serial-log", required=True)
    measure.add_argument("--timeout", type=int, default=300)
    measure.add_argument("--output", required=True)
    measure.add_argument(
        "--marker",
        action="append",
        default=[],
        metavar="NAME=PATTERN",
        help=(
            "override one guest serial marker regex "
            f"(NAME in {sorted(DEFAULT_MARKERS)}; repeatable)"
        ),
    )
    measure.add_argument("qemu_argv", nargs="+")
    compare_parser = sub.add_parser("compare", help="interpret baseline/activated")
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--activated", required=True)
    compare_parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.mode == "preregister":
        sys.stdout.write(_preregistration_text())
        return 0
    if args.mode == "measure":
        try:
            overrides: dict[str, str] = {}
            for raw in args.marker:
                name, pattern = parse_marker_override(raw)
                overrides[name] = pattern
            measurement = measure_boot(
                label=args.label,
                qemu_argv=list(args.qemu_argv),
                serial_log=Path(args.serial_log),
                timeout_seconds=int(args.timeout),
                markers=overrides or None,
            )
        except PreIntroTimingError as exc:
            sys.stderr.write(str(exc) + "\n")
            return 2
        Path(args.output).write_text(
            json.dumps(measurement.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return 0
    if args.mode == "compare":
        try:
            baseline = BootMeasurement.from_dict(
                json.loads(Path(args.baseline).read_text(encoding="utf-8"))
            )
            activated = BootMeasurement.from_dict(
                json.loads(Path(args.activated).read_text(encoding="utf-8"))
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            sys.stderr.write(f"cannot load measurement records: {exc}\n")
            return 2
        result = compare(baseline, activated)
        Path(args.output).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        sys.stdout.write(f"overall: {result['overall']}\n")
        return 0 if result["overall"] == "PASS" else 1
    parser.error("unknown mode")
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
