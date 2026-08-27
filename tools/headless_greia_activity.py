"""Headless launch of a single Greia Activity through the canonical
SimulatorPythonRuntimeAdapter.

This script exists for the `LAUNCH_ACCEPTANCE.md` gate when the
Activity under test is already a built-in (so the simulator's
"Load Activity Folder..." path is a no-op alias collision) or
when the developer-unsigned path is unavailable in the
terminal-only execution context. It invokes the Activity's
`main.py` exactly the way the simulator's child shell would,
through the trusted `greia_simulator.python_activity` bootstrap
with the synthetic display surface and the remote bridge bound
to 127.0.0.1:8767.

The script is deliberately narrow: it captures screenshots,
verifies the Shell (now the Activity) survives for the requested
number of seconds, sends a bounded interaction, and stops the
process through the proper SIGTERM / SIGKILL escalation that the
simulator's ActivitySupervisor also performs.

The headless launch is **not** a substitute for the canonical
simulator gate in every case — it does not exercise the launcher
UI, the profile picker, the ActivitySupervisor's normal launch
harness, or the read-only workspace contract. It is the right
tool for "this Activity's runtime launches, survives, responds
to input, exits cleanly" once the launcher and supervisor paths
are already known to work for a sibling Activity in the same
execution environment.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORT = 8767
BRIDGE_URL = f"http://127.0.0.1:{DEFAULT_PORT}"


def _log(msg: str) -> None:
    print(f"[hl-activity] {msg}", flush=True)


def _wait_for_bridge(port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def _http_post_json(path: str, payload: dict) -> int:
    import json as _json
    body = _json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BRIDGE_URL}{path}", data=body, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:  # noqa: S310
            return resp.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code


def _http_get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BRIDGE_URL}{path}", timeout=5.0) as resp:  # noqa: S310
        import json as _json
        return _json.loads(resp.read().decode("utf-8"))


def _screenshot(out_path: Path) -> bool:
    try:
        with urllib.request.urlopen(
            f"{BRIDGE_URL}/api/frame", timeout=10.0
        ) as resp:  # noqa: S310
            data = resp.read()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        _log(f"screenshot failed: {exc}")
        return False


def _bridge_click(x: int, y: int) -> bool:
    return _http_post_json(
        "/api/input/mouse",
        {"x": int(x), "y": int(y), "action": "click", "button": 1},
    ) in (200, 204)


def _bridge_key(name: str, action: str = "press") -> bool:
    return _http_post_json(
        "/api/input/key",
        {"key": name.upper(), "action": action},
    ) in (200, 204)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Headless launch of one Greia Activity under the canonical simulator bootstrap."
    )
    parser.add_argument("--activity-main", type=Path, required=True,
                        help="Absolute path to the Activity's main.py")
    parser.add_argument("--locale", default="it")
    parser.add_argument("--viewport", default="1024x600")
    parser.add_argument("--survival-seconds", type=float, default=12.0)
    parser.add_argument("--screenshot-prefix", type=Path,
                        default=Path("/tmp/greia-activity-evidence"))
    parser.add_argument("--click-x", type=int, default=None)
    parser.add_argument("--click-y", type=int, default=None)
    parser.add_argument("--press-key", default=None)
    args = parser.parse_args(argv)

    if not args.activity_main.is_file():
        _log(f"Activity entrypoint not found: {args.activity_main}")
        return 2

    # We invoke the Activity under the canonical simulator's
    # trusted bootstrap (`greia_simulator.python_activity`). The
    # bootstrap sets up the synthetic display, the remote bridge
    # on 127.0.0.1:8767, and the supervisor-style environment, then
    # exec's the Activity's main.py.
    activity_root = args.activity_main.resolve().parent
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["GREIA_SIMULATOR_HEADLESS"] = "1"
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["GREIA_PROFILE_LOCALE"] = args.locale
    env["GREIA_DEVICE_LOCALE"] = args.locale
    env["GREIA_OS_ROOT"] = str(REPO_ROOT)
    env["GREIA_ACTIVITY_ROOT"] = str(activity_root)
    # The Activity also needs the rest of the normal Greia env
    # so it can talk to its profile-scoped storage, etc.
    env["GREIA_PROFILES_DIR"] = str(
        Path(tempfile.mkdtemp(prefix="ramp-hl-profiles-", dir="/tmp")) / "profiles"
    )
    env["GREIA_DEVELOPER_ACTIVITY_ROOT"] = str(
        Path(tempfile.mkdtemp(prefix="ramp-hl-devact-", dir="/tmp"))
    )
    env["GREIA_PARENT_ACTIVITY_ROOT"] = str(
        Path(tempfile.mkdtemp(prefix="ramp-hl-pact-", dir="/tmp")) / "active"
    )
    env["GREIA_PARENT_ACTIVITY_PACKAGE_ROOT"] = str(
        Path(tempfile.mkdtemp(prefix="ramp-hl-pkg-", dir="/tmp"))
    )
    env["GREIA_MEDIA_ROOT"] = str(
        Path(tempfile.mkdtemp(prefix="ramp-hl-media-", dir="/tmp"))
    )
    env["GREIA_MAIN_CREDENTIAL_PATH"] = str(
        Path(tempfile.mkdtemp(prefix="ramp-hl-creds-", dir="/tmp"))
        / "main-credential.json"
    )
    env["GREIA_ACTIVE_PROFILE_STATUS"] = str(
        Path(tempfile.mkdtemp(prefix="ramp-hl-run-", dir="/tmp"))
        / "active-profile.json"
    )
    env["GREIA_SKIP_BOOT_HANDOFF"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "greia_simulator.python_activity",
        "--viewport",
        args.viewport,
        "--remote-port",
        str(DEFAULT_PORT),
        str(args.activity_main),
    ]
    _log(f"launching: {cmd}")
    child = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        if not _wait_for_bridge(DEFAULT_PORT, timeout=15.0):
            _log("remote bridge never came up")
            return 3
        _log("bridge up")
        # First frame
        deadline = time.monotonic() + 30.0
        first = False
        first_path = args.screenshot_prefix.with_name(
            args.screenshot_prefix.stem + "-01-first-frame.png"
        )
        while time.monotonic() < deadline:
            try:
                st = _http_get_json("/api/state")
                if int(st.get("frame_count", 0)) > 0:
                    first = True
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
        if not first:
            _log("first frame never arrived")
            return 4
        _log(f"first frame: {st}")
        if not _screenshot(first_path):
            return 5
        # Survival
        _log(f"survival {args.survival_seconds}s")
        deadline = time.monotonic() + args.survival_seconds
        interacted = False
        while time.monotonic() < deadline:
            if (
                args.click_x is not None
                and args.click_y is not None
                and not interacted
            ):
                _bridge_click(args.click_x, args.click_y)
                interacted = True
            if args.press_key and not interacted:
                _bridge_key(args.press_key)
                interacted = True
            time.sleep(0.5)
            if child.poll() is not None:
                _log(f"process died unexpectedly rc={child.returncode}")
                return 6
        # Post-interaction
        post = args.screenshot_prefix.with_name(
            args.screenshot_prefix.stem + "-02-post.png"
        )
        _screenshot(post)
        if child.poll() is not None:
            return 7
        # Clean stop
        _log("stopping Activity")
        child.terminate()
        try:
            code = child.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            child.kill()
            code = child.wait(timeout=3.0)
        _log(f"Activity exited rc={code}")
        return 0 if code == 0 else 8
    finally:
        if child.poll() is None:
            try:
                child.terminate()
                child.wait(timeout=3.0)
            except Exception:  # noqa: BLE001
                try:
                    child.kill()
                except Exception:  # noqa: BLE001
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
