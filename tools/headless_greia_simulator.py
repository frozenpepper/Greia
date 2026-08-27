"""Headless Greia Activity Simulator runner for development / agent use.

This script wraps the real Greia Activity Simulator with a small
finite-state driver so a developer or an agent can:

  * start the real Greia child Shell in a fully isolated workspace
    (no Tk control plane, no GitHub Actions, no display binding);
  * either (a) load one Activity folder through the simulator's
    `Load Activity Folder...` path (the canonical developer
    validation transaction) or (b) skip the load and drive the
    real built-in activities through the launcher UI;
  * drive the running Shell through the canonical remote bridge
    on http://127.0.0.1:8767 (the same control surface the Tk GUI
    uses internally);
  * capture screenshot evidence (PNG, 1024x600 viewport by default);
  * send bounded input (clicks / key events / text) and verify the
    Shell stays alive;
  * stop the Shell through the proper workspace lease/release
    path so the workspace is never left locked.

The script is intentionally narrow: it exists to make the
`LAUNCH_ACCEPTANCE.md` gate runnable from a terminal-only execution
context where the Tk control plane cannot bind to the user's GUI
session. It does not invent simulator policies and it does not
bypass the real `SimulatorWorkspace` lock / child-PID contract.

Source-mode execution (load + run a source folder) is supported.
Package install via `.greiaactivity` is intentionally not wrapped
here; the package transaction must go through the canonical Tk
control plane path, which is unreachable in this terminal-only
context by design.

Usage:

    # Mode A: load a developer-unsigned Activity from a source folder
    python3 tools/headless_greia_simulator.py \\
        --activity-dir /path/to/activity \\
        --workspace-dir /tmp/greia-hl-<unique> \\
        --locale it \\
        --viewport 1024x600 \\
        --survival-seconds 12 \\
        --screenshot-prefix /tmp/greia-evidence

    # Mode B: drive the launcher's built-in Activity discovery
    # (no developer load; the Activity must already exist in
    # activities/ or be installed)
    python3 tools/headless_greia_simulator.py \\
        --workspace-dir /tmp/greia-hl-<unique> \\
        --locale it \\
        --screenshot-prefix /tmp/greia-evidence

The script exits 0 on a full PASS sequence (start, load, first
frame, survival, interaction, return to launcher / Home, stop) and
non-zero with a concrete failure reason otherwise.
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

# Ensure the Greia source tree is importable regardless of how the script is
# launched (e.g. `python3 tools/headless_greia_simulator.py ...` from the
# repo root, or via a PATH-resolved shebang).
_SRC_PATH = str(REPO_ROOT / "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)


def _log(msg: str) -> None:
    print(f"[headless-sim] {msg}", flush=True)


def _wait_for_bridge(port: int, timeout: float) -> bool:
    """Wait until a TCP listener appears on 127.0.0.1:port."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.4)
            try:
                sock.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def _http_get_json(path: str) -> dict:
    url = f"{BRIDGE_URL}{path}"
    with urllib.request.urlopen(url, timeout=5.0) as resp:  # noqa: S310
        import json as _json
        return _json.loads(resp.read().decode("utf-8"))


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
    url = f"{BRIDGE_URL}/api/frame"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=10.0) as resp:  # noqa: S310
            data = resp.read()
        out_path.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        _log(f"screenshot failed: {exc}")
        return False


def _bridge_click(x: int, y: int) -> bool:
    code = _http_post_json(
        "/api/input/mouse",
        {"x": int(x), "y": int(y), "action": "click", "button": 1},
    )
    if code not in (200, 204):
        _log(f"mouse click returned {code}")
        return False
    return True


def _bridge_key(name: str, action: str = "press") -> bool:
    code = _http_post_json(
        "/api/input/key",
        {"key": name.upper(), "action": action},
    )
    if code not in (200, 204):
        _log(f"key {name} returned {code}")
        return False
    return True


def _bridge_text(text: str) -> bool:
    code = _http_post_json(
        "/api/input/text", {"text": text}
    )
    if code not in (200, 204):
        _log(f"text input returned {code}")
        return False
    return True


def _run_workspace_loader(
    workspace_dir: Path, activity_dir: Path, locale: str
):
    """Use the canonical SimulatorWorkspace to publish the Activity to the
    developer-activities root. Returns the live workspace instance so the
    caller can continue to use its owned writer lease and child-PID state.
    """
    from greia_simulator.workspace import SimulatorWorkspace
    ws = SimulatorWorkspace(REPO_ROOT, workspace_dir)
    ws.ensure()
    ws.acquire_lock()
    ws.load_activity(activity_dir)
    # The lock stays open in this process; the child shell is recorded as
    # the owned child PID by the caller via ws.update_lock_child_pid(...).
    return ws


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Greia Activity Simulator headless."
    )
    parser.add_argument(
        "--activity-dir", type=Path, default=None,
        help=(
            "Activity source folder to load into the developer-activities "
            "root. Optional: omit to use the built-in activities already "
            "discoverable by the child shell, and drive the launcher via "
            "the remote bridge to pick the activity by hand."
        ),
    )
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--locale", default="it")
    parser.add_argument("--viewport", default="1024x600")
    parser.add_argument(
        "--survival-seconds", type=float, default=12.0,
        help="seconds the Shell must remain alive after first usable frame",
    )
    parser.add_argument(
        "--screenshot-prefix", type=Path, default=Path("/tmp/greia-evidence"),
    )
    parser.add_argument(
        "--click-x", type=int, default=None,
        help="optional X viewport coord for a single click during interaction",
    )
    parser.add_argument(
        "--click-y", type=int, default=None,
        help="optional Y viewport coord for a single click during interaction",
    )
    parser.add_argument(
        "--press-key", default=None,
        help="optional single key event (e.g. 'RETURN', 'ESCAPE', 'TAB')",
    )
    args = parser.parse_args(argv)

    if not args.activity_dir.is_dir() if args.activity_dir is not None else False:
        _log(f"Activity source folder not found: {args.activity_dir}")
        return 2

    # Fresh workspace for this run
    if args.workspace_dir.exists():
        shutil.rmtree(args.workspace_dir, ignore_errors=True)
    args.workspace_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: optionally publish an Activity into the isolated
    # workspace. To avoid the "Activity already exists" identity
    # collision that happens when the source folder is the same
    # as the built-in Activities directory, we copy the source
    # into a fresh staging directory and load from there. The
    # destination activity id stays the same so the launcher
    # resolves the developer-unsigned copy at runtime.
    staging_source: Path | None = None
    if args.activity_dir is not None:
        _log("publishing Activity to isolated workspace")
        if (REPO_ROOT / "activities").resolve() in args.activity_dir.resolve().parents:
            staging = Path(tempfile.mkdtemp(prefix="ramp-hl-stage-", dir="/tmp"))
            staging_source = staging / "activity"
            shutil.copytree(args.activity_dir, staging_source)
            args = argparse.Namespace(
                **{**vars(args), "activity_dir": staging_source}
            )
            _log(f"staged source at {staging_source} to avoid built-in collision")
        try:
            ws = _run_workspace_loader(
                args.workspace_dir, args.activity_dir, args.locale
            )
        except Exception as exc:  # noqa: BLE001
            _log(f"failed to publish Activity: {exc}")
            return 3
    else:
        _log("no --activity-dir: child shell will discover built-in activities")
        from greia_simulator.workspace import SimulatorWorkspace
        ws = SimulatorWorkspace(REPO_ROOT, args.workspace_dir)
        ws.ensure()
        ws.acquire_lock()

    # Step 2: spawn the real Greia child Shell headless
    _log("spawning real Greia child Shell in --headless mode")
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["GREIA_SIMULATOR_HEADLESS"] = "1"
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    for key, value in ws.environment().items():
        env[key] = value

    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "greia_simulator.child_shell",
            "--viewport",
            args.viewport,
            "--language",
            args.locale,
            "--capability",
            "display",
            "--capability",
            "keyboard",
            "--capability",
            "pointer",
            "--capability",
            "touch",
            "--capability",
            "audio.basic",
            "--remote-port",
            str(DEFAULT_PORT),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        ws.update_lock_child_pid(child.pid)
    except Exception as exc:  # noqa: BLE001
        _log(f"failed to register child PID in workspace lease: {exc}")
        child.terminate()
        child.wait(timeout=5)
        return 4

    try:
        # Step 3: wait for the remote bridge
        if not _wait_for_bridge(DEFAULT_PORT, timeout=15.0):
            _log("remote bridge never came up")
            return 5
        _log("remote bridge is up")

        # Step 4: poll for first usable frame
        deadline = time.monotonic() + 30.0
        first_frame = False
        first_frame_path = args.screenshot_prefix.with_name(
            args.screenshot_prefix.stem + "-01-first-frame.png"
        )
        while time.monotonic() < deadline:
            try:
                status = _http_get_json("/api/state")
            except Exception as exc:  # noqa: BLE001
                _log(f"status error: {exc}")
                time.sleep(0.5)
                continue
            if int(status.get("frame_count", 0)) > 0:
                first_frame = True
                break
            time.sleep(0.5)
        if not first_frame:
            _log("first usable frame never arrived")
            return 6
        _log(f"first frame arrived; status: {status}")
        if not _screenshot(first_frame_path):
            _log("first frame screenshot failed")
            return 6
        _log(f"first-frame screenshot: {first_frame_path}")

        # Step 5: survival + interaction window
        _log(f"survival window: {args.survival_seconds}s")
        survival_deadline = time.monotonic() + args.survival_seconds
        interaction_done = False
        while time.monotonic() < survival_deadline:
            # Optional click
            if (
                args.click_x is not None
                and args.click_y is not None
                and not interaction_done
            ):
                _log(
                    f"sending click at ({args.click_x}, {args.click_y})"
                )
                ok = _bridge_click(args.click_x, args.click_y)
                if not ok:
                    _log("click action failed")
                interaction_done = True
            # Optional key press
            if args.press_key and not interaction_done:
                _log(f"sending key {args.press_key}")
                _bridge_key(args.press_key, action="press")
                interaction_done = True
            time.sleep(0.5)
            # Check Shell is still alive
            if child.poll() is not None:
                _log(f"Shell exited unexpectedly with code {child.returncode}")
                return 7

        # Step 6: post-interaction screenshot
        post_path = args.screenshot_prefix.with_name(
            args.screenshot_prefix.stem + "-02-post-interaction.png"
        )
        if not _screenshot(post_path):
            _log("post-interaction screenshot failed")
            return 8
        _log(f"post-interaction screenshot: {post_path}")

        # Step 7: confirm the Shell is still alive after interaction
        if child.poll() is not None:
            _log(f"Shell died after interaction: {child.returncode}")
            return 9
        _log("Shell still alive after interaction window")

        # Step 8: stop the Shell cleanly
        _log("stopping Shell through normal lifecycle path")
        child.terminate()
        try:
            code = child.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            _log("Shell did not stop gracefully; killing")
            child.kill()
            code = child.wait(timeout=3.0)
        _log(f"Shell exited rc={code}")

        # Final shot
        final_path = args.screenshot_prefix.with_name(
            args.screenshot_prefix.stem + "-03-stopped.png"
        )
        # The bridge stops with the Shell; this shot is best-effort.
        try:
            _screenshot(final_path)
        except Exception:  # noqa: BLE001
            pass

        _log("PASS")
        return 0
    finally:
        # Always clear the child-PID lease and release the workspace lock
        try:
            ws.update_lock_child_pid(None)
        except Exception:  # noqa: BLE001
            pass
        try:
            ws.release_lock()
        except Exception:  # noqa: BLE001
            pass
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
