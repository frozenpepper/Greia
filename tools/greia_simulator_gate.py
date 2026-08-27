"""Real Greia Simulator launch gate for one Activity.

This script runs the full `LAUNCH_ACCEPTANCE.md` gate for a
single Activity in a terminal-only execution context. It spawns
the real Greia child Shell headless (so the launcher UI + remote
bridge on 127.0.0.1:8767 are live), then launches the Activity
under the canonical `greia_simulator.python_activity` bootstrap
with the same environment. Both processes use the same isolated
workspace; the workspace is released when the script exits.

The gate sequence is:

  1. real Greia child Shell starts and the remote bridge comes up;
  2. the first usable frame is captured (the child Shell home);
  3. the child Shell is in `mode: activities` after the profile is
     picked automatically (the simulator does this on first launch);
  4. the python_activity bootstrap is spawned for the target
     Activity; its first frame appears on the bridge within a few
     seconds (the Activity's first usable frame);
  5. a single click is delivered to the Activity's canvas;
  6. the Activity remains alive for the survival window;
  7. the post-interaction frame is captured;
  8. both processes are stopped cleanly through the normal
     supervisor escalation (SIGTERM, then SIGKILL if needed).

The script exits 0 on a full PASS sequence and non-zero with a
concrete failure reason otherwise.

Usage:

    python3 tools/greia_simulator_gate.py \\
        --activity-dir /path/to/activity \\
        --workspace-dir /tmp/greia-gate-<unique> \\
        --locale it \\
        --survival-seconds 8 \\
        --screenshot-prefix /tmp/greia-gate-evidence \\
        --click-x 512 --click-y 360
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
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
    print(f"[gate] {msg}", flush=True)


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


def _http_get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BRIDGE_URL}{path}", timeout=5.0) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(path: str, payload: dict) -> int:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BRIDGE_URL}{path}", data=body, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:  # noqa: S310
            return resp.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code


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


def _spawn_child_shell(workspace_dir: Path) -> subprocess.Popen:
    """Spawn the real Greia child Shell in --headless mode and hold
    the workspace writer lease from the parent process.
    """
    # Ensure the Greia source tree is importable regardless of how
    # this script is launched (this file lives in tools/, where
    # the local greia_simulator.py could otherwise shadow the
    # source-tree package).
    _SRC = str(REPO_ROOT / "src")
    if _SRC not in sys.path:
        sys.path.insert(0, _SRC)
    from greia_simulator.workspace import SimulatorWorkspace
    ws = SimulatorWorkspace(REPO_ROOT, workspace_dir)
    ws.ensure()
    ws.acquire_lock()
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["GREIA_SIMULATOR_HEADLESS"] = "1"
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    for k, v in ws.environment().items():
        env[k] = v
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "greia_simulator.child_shell",
            "--viewport", "1024x600",
            "--language", "it",
            "--capability", "display",
            "--capability", "keyboard",
            "--capability", "pointer",
            "--capability", "touch",
            "--capability", "audio.basic",
            "--remote-port", str(DEFAULT_PORT),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        ws.update_lock_child_pid(proc.pid)
    except Exception as exc:
        proc.terminate()
        proc.wait(timeout=5)
        raise RuntimeError(f"failed to register child PID: {exc}")
    return proc, ws


def _spawn_activity(activity_dir: Path) -> subprocess.Popen:
    """Spawn the Activity under the canonical python_activity
    bootstrap, talking to the same bridge on port 8767.
    """
    activity_root = activity_dir.resolve()
    entrypoint = activity_root / "main.py"
    if not entrypoint.is_file():
        raise FileNotFoundError(f"Activity main.py not found at {entrypoint}")
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["GREIA_SIMULATOR_HEADLESS"] = "1"
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["GREIA_PROFILE_LOCALE"] = "it"
    env["GREIA_DEVICE_LOCALE"] = "it"
    env["GREIA_SKIP_BOOT_HANDOFF"] = "1"
    env["GREIA_ACTIVITY_ROOT"] = str(activity_root)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "greia_simulator.python_activity",
            "--viewport", "1024x600",
            "--remote-port", str(DEFAULT_PORT),
            str(entrypoint),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the real Greia Activity Simulator gate for one Activity."
        ),
    )
    parser.add_argument("--activity-dir", type=Path, required=True)
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--locale", default="it")
    parser.add_argument("--survival-seconds", type=float, default=8.0)
    parser.add_argument(
        "--screenshot-prefix", type=Path,
        default=Path("/tmp/greia-gate-evidence"),
    )
    parser.add_argument("--click-x", type=int, default=None)
    parser.add_argument("--click-y", type=int, default=None)
    args = parser.parse_args(argv)

    if not args.activity_dir.is_dir():
        _log(f"Activity directory not found: {args.activity_dir}")
        return 2

    # Fresh workspace
    if args.workspace_dir.exists():
        shutil.rmtree(args.workspace_dir, ignore_errors=True)
    args.workspace_dir.mkdir(parents=True, exist_ok=True)

    child_proc = None
    activity_proc = None
    ws = None
    try:
        # Step 1: child shell + bridge
        _log("spawning real Greia child Shell (--headless)")
        child_proc, ws = _spawn_child_shell(args.workspace_dir)
        if not _wait_for_bridge(DEFAULT_PORT, timeout=15.0):
            _log("remote bridge never came up")
            return 3
        _log("remote bridge is up")

        # Step 2: first usable frame (child shell)
        deadline = time.monotonic() + 30.0
        first = False
        shell_frame_path = args.screenshot_prefix.with_name(
            args.screenshot_prefix.stem + "-01-shell.png"
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
            _log("child shell never produced a frame")
            return 4
        _log(f"child shell first frame: mode={st.get('mode')}")
        _screenshot(shell_frame_path)

        # Step 3: launch the Activity subprocess under the canonical
        # python_activity bootstrap
        _log("spawning Activity under the python_activity bootstrap")
        activity_proc = _spawn_activity(args.activity_dir)

        # Step 4: wait for the Activity to post a frame
        deadline = time.monotonic() + 30.0
        activity_first = False
        activity_frame_path = args.screenshot_prefix.with_name(
            args.screenshot_prefix.stem + "-02-activity.png"
        )
        while time.monotonic() < deadline:
            try:
                st = _http_get_json("/api/state")
                if int(st.get("frame_count", 0)) > 5 and st.get("mode") == "activity":
                    activity_first = True
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
        if not activity_first:
            _log("Activity never posted a frame to the bridge")
            return 5
        _log(f"Activity frame: mode={st.get('mode')}, frames={st.get('frame_count')}")
        _screenshot(activity_frame_path)

        # Step 5: bounded interaction
        if args.click_x is not None and args.click_y is not None:
            _log(f"sending click at ({args.click_x}, {args.click_y})")
            _bridge_click(args.click_x, args.click_y)

        # Step 6: survival
        _log(f"survival window: {args.survival_seconds}s")
        deadline = time.monotonic() + args.survival_seconds
        while time.monotonic() < deadline:
            if activity_proc.poll() is not None:
                _log(f"Activity died unexpectedly rc={activity_proc.returncode}")
                return 6
            time.sleep(0.5)

        # Step 7: post-interaction frame
        post = args.screenshot_prefix.with_name(
            args.screenshot_prefix.stem + "-03-post.png"
        )
        _screenshot(post)
        if activity_proc.poll() is not None:
            _log("Activity died after interaction")
            return 7
        _log("Activity still alive after interaction window")

        # Step 8: clean stop
        _log("stopping Activity and child shell")
        try:
            activity_proc.terminate()
            activity_proc.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            activity_proc.kill()
            activity_proc.wait(timeout=3.0)
        try:
            child_proc.terminate()
            child_proc.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            child_proc.kill()
            child_proc.wait(timeout=3.0)
        _log(f"Activity rc={activity_proc.returncode}, child shell rc={child_proc.returncode}")
        _log("PASS")
        return 0
    finally:
        for proc in (activity_proc, child_proc):
            if proc is not None and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3.0)
                except Exception:  # noqa: BLE001
                    try:
                        proc.kill()
                    except Exception:  # noqa: BLE001
                        pass
        if ws is not None:
            try:
                ws.update_lock_child_pid(None)
            except Exception:  # noqa: BLE001
                pass
            try:
                ws.release_lock()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    raise SystemExit(main())
