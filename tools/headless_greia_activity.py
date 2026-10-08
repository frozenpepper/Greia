"""Focused headless Activity capture through Greia's real Simulator bridge.

This tool deliberately does NOT simulate the entire Greia Shell. It owns a
temporary loopback SimulatorRemoteBridge, launches the trusted Python Activity
bootstrap as a client of that server, and captures real Pygame frames. The
full-Shell route is tools/headless_greia_simulator.py and must be used for
profile, catalogue, supervisor, trusted Home and installation acceptance.

All test state is disposable; only explicitly requested evidence is retained.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
TRUSTED_SOURCE = REPO_ROOT / "src"
if str(TRUSTED_SOURCE) not in sys.path:
    sys.path.insert(0, str(TRUSTED_SOURCE))

from greia_simulator.remote_bridge import SimulatorRemoteBridge  # noqa: E402


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _log(message: str) -> None:
    print(f"[hl-activity] {message}", flush=True)


def _evidence_path(prefix: Path, suffix: str) -> Path:
    return prefix.with_name(prefix.stem + suffix)


def _capture_frame(bridge: SimulatorRemoteBridge, path: Path) -> bool:
    data = bridge.get_latest_frame_png()
    if not isinstance(data, bytes) or not data.startswith(PNG_SIGNATURE):
        _log("Activity bridge has no valid PNG frame")
        return False
    try:
        with path.open("xb") as output:
            output.write(data)
    except FileExistsError:
        _log(f"refusing to overwrite screenshot: {path}")
        return False
    _log(f"saved {len(data)} bytes: {path}")
    return True


def _wait_for_frame(
    bridge: SimulatorRemoteBridge,
    child: subprocess.Popen[bytes],
    *,
    after: int = 0,
    timeout: float = 30.0,
) -> bool:
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if child.poll() is not None:
            _log(f"Activity exited before a frame (rc={child.returncode})")
            return False
        state = bridge.get_state()
        if int(state.get("frame_count", 0)) > after and state.get("mode") == "activity":
            return True
        time.sleep(0.1)
    _log(f"no Activity frame after {timeout:g}s; bridge state: {bridge.get_state()}")
    return False


def _stop_child(child: subprocess.Popen[bytes]) -> bool:
    """A graceful SIGTERM is expected in the Supervisor-compatible probe."""
    if child.poll() is not None:
        _log(f"Activity already stopped unexpectedly (rc={child.returncode})")
        return False
    child.terminate()
    try:
        rc = child.wait(timeout=8.0)
    except subprocess.TimeoutExpired:
        _log("Activity ignored SIGTERM: forced kill; probe is NOT accepted")
        child.kill()
        child.wait(timeout=3.0)
        return False
    _log(f"Activity stopped on request (rc={rc})")
    return rc in (0, -signal.SIGTERM)


def _probe(
    *,
    activity_main: Path,
    locale: str,
    viewport: str,
    survival_seconds: float,
    screenshot_prefix: Path,
    click: tuple[int, int] | None,
    key: str | None,
) -> int:
    """Return nonzero on launch/frame/interaction/teardown failure."""
    if not activity_main.is_file():
        _log(f"Activity entrypoint not found: {activity_main}")
        return 2

    screenshot_prefix.parent.mkdir(parents=True, exist_ok=True)
    first = _evidence_path(screenshot_prefix, "-01-first-frame.png")
    post = _evidence_path(screenshot_prefix, "-02-post.png")
    log_path = _evidence_path(screenshot_prefix, "-child.log")
    if any(path.exists() or path.is_symlink() for path in (first, post, log_path)):
        _log("evidence already exists: choose a NEW screenshot prefix")
        return 2

    # port=0 owns a fresh loopback listener. Never attach to a stale 8767
    # server or rely on somebody else running the full Greia Shell.
    bridge = SimulatorRemoteBridge(port=0, host="127.0.0.1")
    try:
        bridge.start()
    except OSError as exc:
        _log(f"could not start owned loopback bridge: {exc}")
        return 3
    child: subprocess.Popen[bytes] | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="greia-hl-activity-") as sandbox:
            scratch = Path(sandbox)
            env = os.environ.copy()
            env.update({
                "PYTHONPATH": str(TRUSTED_SOURCE),
                "PYTHONDONTWRITEBYTECODE": "1",
                "SDL_VIDEODRIVER": "dummy",
                "SDL_AUDIODRIVER": "dummy",
                "GREIA_PROFILE_LOCALE": locale,
                "GREIA_DEVICE_LOCALE": locale,
                "GREIA_OS_ROOT": str(REPO_ROOT),
                "GREIA_ACTIVITY_ROOT": str(activity_main.resolve().parent),
                "GREIA_PROFILES_DIR": str(scratch / "profiles"),
                "GREIA_DEVELOPER_ACTIVITY_ROOT": str(scratch / "developer"),
                "GREIA_PARENT_ACTIVITY_ROOT": str(scratch / "parent" / "active"),
                "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(scratch / "packages"),
                "GREIA_MEDIA_ROOT": str(scratch / "media"),
                "GREIA_MAIN_CREDENTIAL_PATH": str(scratch / "credentials" / "main.json"),
                "GREIA_ACTIVE_PROFILE_STATUS": str(scratch / "active-profile.json"),
                "GREIA_SKIP_BOOT_HANDOFF": "1",
            })
            command = [
                sys.executable, "-m", "greia_simulator.python_activity",
                "--viewport", viewport,
                "--remote-port", str(bridge.port),
                str(activity_main.resolve()),
            ]
            _log(f"owned bridge: {bridge.url}; launching: {command}")
            # A real file avoids a child PIPE deadlock and preserves tracebacks
            # from failures before the first simulator frame.
            with log_path.open("xb") as child_log:
                child = subprocess.Popen(
                    command, cwd=str(REPO_ROOT), env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=child_log, stderr=subprocess.STDOUT,
                )
                if not _wait_for_frame(bridge, child, timeout=30.0):
                    _log(f"Activity never produced a frame. Inspect {log_path}")
                    return 4
                if not _capture_frame(bridge, first):
                    return 5

                _log(f"survival window: {survival_seconds:g}s")
                initial = time.monotonic()
                sent = False
                while time.monotonic() - initial < survival_seconds:
                    if child.poll() is not None:
                        _log(f"Activity exited during survival (rc={child.returncode}); see {log_path}")
                        return 6
                    if not sent:
                        if click is not None:
                            bridge.queue_mouse(*click)
                            _log(f"queued mouse click {click}")
                            sent = True
                        elif key is not None:
                            bridge.queue_key(key)
                            _log(f"queued key {key}")
                            sent = True
                    time.sleep(0.1)

                if child.poll() is not None:
                    _log(f"Activity exited before post-frame (rc={child.returncode})")
                    return 7
                if sent:
                    before = bridge.get_state()["frame_count"]
                    # Allow event polling plus the 1 Hz idle My Time redraw.
                    # Static Activities may not redraw on every input: in
                    # that case capture the last valid frame without lying.
                    _wait_for_frame(bridge, child, after=int(before), timeout=2.0)
                    if child.poll() is not None:
                        _log(f"Activity died after interaction (rc={child.returncode})")
                        return 7
                if not _capture_frame(bridge, post):
                    return 7
                if not _stop_child(child):
                    return 8
                _log(f"PASS: isolated Activity probe (not full Shell); child log: {log_path}")
                return 0
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3.0)
        bridge.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture a standalone Greia Activity against an OWNED remote bridge.",
    )
    parser.add_argument("--activity-main", type=Path, required=True)
    parser.add_argument("--locale", default="it")
    parser.add_argument("--viewport", default="1024x600")
    parser.add_argument("--survival-seconds", type=float, default=12.0)
    parser.add_argument(
        "--screenshot-prefix", type=Path, default=Path("/tmp/greia-activity-evidence"),
    )
    parser.add_argument("--click-x", type=int, default=None)
    parser.add_argument("--click-y", type=int, default=None)
    parser.add_argument("--press-key", default=None)
    args = parser.parse_args(argv)
    if (args.click_x is None) != (args.click_y is None):
        parser.error("--click-x and --click-y must be supplied together")
    if not 0 <= args.survival_seconds <= 120:
        parser.error("--survival-seconds must be between 0 and 120")
    return _probe(
        activity_main=args.activity_main,
        locale=args.locale,
        viewport=args.viewport,
        survival_seconds=args.survival_seconds,
        screenshot_prefix=args.screenshot_prefix,
        click=(args.click_x, args.click_y) if args.click_x is not None else None,
        key=args.press_key,
    )


if __name__ == "__main__":
    raise SystemExit(main())
