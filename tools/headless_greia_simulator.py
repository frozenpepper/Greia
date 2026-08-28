"""Headless Greia Activity Simulator runner for development / agent use.

This script starts the real Greia child Shell in an isolated SimulatorWorkspace
without the Tk control plane. It supports two distinct source modes:

* external Activity source: publish through SimulatorWorkspace.load_activity()
  as developer-unsigned content, then launch it through the normal Shell;
* built-in Activity source: never republish it. The Activity already belongs to
  the built-in catalogue, so the runner launches that exact built-in identity
  through normal profile selection and launcher navigation.

The remote bridge is the same loopback control surface used by the desktop
Simulator. A targeted launch therefore exercises the production Shell
selection/supervisor path rather than directly executing an Activity entrypoint.

A targeted run proves mechanical Shell -> Activity launch, first Activity frame,
survival, optional interaction, protected Home -> Shell return, and clean
workspace teardown. It does not claim subjective visual/pre-reader quality.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILTIN_ACTIVITY_ROOT = (REPO_ROOT / "activities").resolve()
DEFAULT_PORT = 8767
BRIDGE_URL = f"http://127.0.0.1:{DEFAULT_PORT}"

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


def _http_get_json(path: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{BRIDGE_URL}{path}", timeout=5.0) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(path: str, payload: dict[str, Any]) -> int:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BRIDGE_URL}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5.0) as resp:  # noqa: S310
            return resp.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code


def _screenshot(out_path: Path) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(f"{BRIDGE_URL}/api/frame", timeout=10.0) as resp:  # noqa: S310
            out_path.write_bytes(resp.read())
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


def _is_builtin_activity_dir(path: Path) -> bool:
    """Whether path is exactly one first-party Activity root."""

    return path.resolve().parent == BUILTIN_ACTIVITY_ROOT


def _activity_id_from_dir(path: Path) -> str:
    manifest_path = path / "activity.toml"
    raw = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    activity = raw.get("activity")
    if not isinstance(activity, dict):
        raise ValueError(f"Activity manifest has no [activity] table: {manifest_path}")
    activity_id = str(activity.get("id", "")).strip()
    if not activity_id:
        raise ValueError(f"Activity manifest has no activity.id: {manifest_path}")
    return activity_id


def _prepare_workspace(
    workspace_dir: Path,
    activity_dir: Path | None,
    launch_activity_id: str | None,
):
    """Acquire one workspace and resolve the identity to launch.

    Built-in source is already authoritative under REPO_ROOT/activities and must
    never be copied into the developer root under the same identity. External
    source still uses the canonical developer publication transaction.
    """

    from greia_simulator.workspace import SimulatorWorkspace

    ws = SimulatorWorkspace(REPO_ROOT, workspace_dir)
    ws.ensure()
    ws.acquire_lock()

    target_id = launch_activity_id.strip() if launch_activity_id else None
    try:
        if activity_dir is None:
            _log("no --activity-dir: using already-discoverable Activity catalogue")
            return ws, target_id

        if _is_builtin_activity_dir(activity_dir):
            built_in_id = _activity_id_from_dir(activity_dir)
            if target_id is not None and target_id != built_in_id:
                raise ValueError(
                    "--launch-activity-id disagrees with built-in --activity-dir: "
                    f"{target_id!r} != {built_in_id!r}"
                )
            _log(
                "built-in Activity detected; skipping developer publication "
                f"and launching canonical identity {built_in_id}"
            )
            return ws, built_in_id

        _log("publishing external Activity to isolated developer workspace")
        registration = ws.load_activity(activity_dir)
        published_id = registration.manifest.activity_id
        if target_id is not None and target_id != published_id:
            raise ValueError(
                "--launch-activity-id disagrees with published Activity: "
                f"{target_id!r} != {published_id!r}"
            )
        return ws, published_id
    except Exception:
        try:
            ws.release_lock()
        except Exception:  # noqa: BLE001
            pass
        raise


def _discover_activity_index(ws, activity_id: str) -> tuple[int, tuple[str, ...]]:
    """Resolve target index using the same source classes as the Shell."""

    from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
    from greia_platform.trust import ActivitySource, PackageTrust

    runtime = RuntimeCatalogue.load(REPO_ROOT / "runtime" / "child-runtime.toml")
    sources = [
        ActivitySource(
            REPO_ROOT / "activities",
            trust=PackageTrust.BUILT_IN,
            source_id="greia-system",
        ),
        ActivitySource(
            ws.developer_root,
            trust=PackageTrust.DEVELOPER_UNSIGNED,
            source_id="greia-developer-remote",
        ),
    ]
    discovered = ActivityRegistry(tuple(sources), runtime, fail_closed=False).discover()
    ids = tuple(activity.activity_id for activity in discovered)
    try:
        return ids.index(activity_id), ids
    except ValueError as exc:
        raise ValueError(
            f"Activity {activity_id!r} is not discoverable; "
            f"catalogue contains {len(ids)} identities"
        ) from exc


def _wait_for_state(
    predicate: Callable[[dict[str, Any]], bool],
    *,
    timeout: float,
    child: subprocess.Popen | None = None,
) -> dict[str, Any] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child is not None and child.poll() is not None:
            return None
        try:
            state = _http_get_json("/api/state")
        except Exception:  # noqa: BLE001
            time.sleep(0.1)
            continue
        if predicate(state):
            return state
        time.sleep(0.1)
    return None


def _send_profile_and_activity_launch(
    *,
    child: subprocess.Popen,
    target_index: int,
) -> dict[str, Any] | None:
    """Launch via the real profile picker and semantic Activity selection."""

    if not _bridge_key("RETURN"):
        return None
    activities_state = _wait_for_state(
        lambda state: state.get("mode") == "activities",
        timeout=8.0,
        child=child,
    )
    if activities_state is None:
        _log("profile selection never reached Activity catalogue")
        return None

    for _ in range(target_index):
        if not _bridge_key("RIGHT"):
            return None
        time.sleep(0.025)

    before_launch_count = int(activities_state.get("frame_count", 0))
    if not _bridge_key("RETURN"):
        return None
    activity_state = _wait_for_state(
        lambda state: (
            state.get("mode") == "activity"
            and int(state.get("frame_count", 0)) > before_launch_count
        ),
        timeout=20.0,
        child=child,
    )
    if activity_state is None:
        _log("target Activity never produced a remote Activity frame")
    return activity_state


def _protected_home_center(viewport: str) -> tuple[int, int]:
    from greia_platform.system_chrome import ActivitySystemChromeLayout
    from greia_simulator.device import parse_viewport

    width, height = parse_viewport(viewport)
    hitbox = ActivitySystemChromeLayout.for_surface(width, height).home_hitbox
    return hitbox.x + hitbox.width // 2, hitbox.y + hitbox.height // 2


def _return_home(
    *,
    child: subprocess.Popen,
    viewport: str,
) -> dict[str, Any] | None:
    x, y = _protected_home_center(viewport)
    _log(f"invoking protected Greia Home at ({x}, {y})")
    if not _bridge_click(x, y):
        return None
    returned = _wait_for_state(
        lambda state: state.get("mode") == "activities",
        timeout=12.0,
        child=child,
    )
    if returned is None:
        _log("protected Home did not return to the Activity catalogue")
    return returned


def _output_path(prefix: Path, suffix: str) -> Path:
    return prefix.with_name(prefix.stem + suffix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Greia Activity Simulator headless."
    )
    parser.add_argument(
        "--activity-dir",
        type=Path,
        default=None,
        help=(
            "Activity source root. External source is published developer-unsigned; "
            "a direct child of repo activities/ is recognized as built-in and is "
            "launched in place without republishing."
        ),
    )
    parser.add_argument(
        "--launch-activity-id",
        default=None,
        help=(
            "Already-discoverable Activity identity to launch through the real Shell. "
            "When --activity-dir is supplied this defaults to that Activity's id."
        ),
    )
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--locale", default="it")
    parser.add_argument("--viewport", default="1024x600")
    parser.add_argument(
        "--survival-seconds",
        type=float,
        default=12.0,
        help="seconds the Shell/target Activity must remain alive after its first frame",
    )
    parser.add_argument(
        "--screenshot-prefix",
        type=Path,
        default=Path("/tmp/greia-evidence"),
    )
    parser.add_argument("--click-x", type=int, default=None)
    parser.add_argument("--click-y", type=int, default=None)
    parser.add_argument(
        "--press-key",
        default=None,
        help="optional single target-Activity key event (e.g. RETURN)",
    )
    args = parser.parse_args(argv)

    if args.activity_dir is not None and not args.activity_dir.is_dir():
        _log(f"Activity source folder not found: {args.activity_dir}")
        return 2
    if (args.click_x is None) != (args.click_y is None):
        _log("--click-x and --click-y must be supplied together")
        return 2

    if args.workspace_dir.exists():
        shutil.rmtree(args.workspace_dir, ignore_errors=True)
    args.workspace_dir.mkdir(parents=True, exist_ok=True)

    try:
        ws, target_id = _prepare_workspace(
            args.workspace_dir,
            args.activity_dir,
            args.launch_activity_id,
        )
    except Exception as exc:  # noqa: BLE001
        _log(f"failed to prepare Activity/workspace: {exc}")
        return 3

    target_index: int | None = None
    if target_id is not None:
        try:
            target_index, activity_ids = _discover_activity_index(ws, target_id)
        except Exception as exc:  # noqa: BLE001
            _log(f"failed to resolve target Activity: {exc}")
            try:
                ws.release_lock()
            except Exception:  # noqa: BLE001
                pass
            return 3
        _log(
            f"target Activity {target_id} is launcher index "
            f"{target_index}/{max(0, len(activity_ids) - 1)}"
        )

    _log("spawning real Greia child Shell in --headless mode")
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["GREIA_SIMULATOR_HEADLESS"] = "1"
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env.update(ws.environment())

    child_log_path = _output_path(args.screenshot_prefix, "-child.log")
    child_log_path.parent.mkdir(parents=True, exist_ok=True)
    child_log = child_log_path.open("wb")
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
        stdout=child_log,
        stderr=subprocess.STDOUT,
    )
    try:
        ws.update_lock_child_pid(child.pid)
    except Exception as exc:  # noqa: BLE001
        _log(f"failed to register child PID in workspace lease: {exc}")
        child.terminate()
        child.wait(timeout=5)
        child_log.close()
        return 4

    try:
        if not _wait_for_bridge(DEFAULT_PORT, timeout=15.0):
            _log(f"remote bridge never came up; child log: {child_log_path}")
            return 5
        _log("remote bridge is up")

        shell_state = _wait_for_state(
            lambda state: int(state.get("frame_count", 0)) > 0,
            timeout=30.0,
            child=child,
        )
        if shell_state is None:
            _log(f"first Shell frame never arrived; child log: {child_log_path}")
            return 6
        shell_frame_path = _output_path(args.screenshot_prefix, "-01-shell-frame.png")
        if not _screenshot(shell_frame_path):
            return 6
        _log(f"first Shell frame: {shell_frame_path}; state={shell_state}")

        if target_index is not None:
            activity_state = _send_profile_and_activity_launch(
                child=child,
                target_index=target_index,
            )
            if activity_state is None:
                _log(f"Activity launch failed; child log: {child_log_path}")
                return 7
            activity_frame_path = _output_path(
                args.screenshot_prefix, "-02-activity-first-frame.png"
            )
            if not _screenshot(activity_frame_path):
                return 7
            _log(f"target Activity frame: {activity_frame_path}; state={activity_state}")

        _log(f"survival window: {args.survival_seconds}s")
        survival_deadline = time.monotonic() + args.survival_seconds
        interaction_done = False
        while time.monotonic() < survival_deadline:
            if (
                args.click_x is not None
                and args.click_y is not None
                and not interaction_done
            ):
                _log(f"sending click at ({args.click_x}, {args.click_y})")
                if not _bridge_click(args.click_x, args.click_y):
                    return 8
                interaction_done = True
            if args.press_key and not interaction_done:
                _log(f"sending key {args.press_key}")
                if not _bridge_key(args.press_key, action="press"):
                    return 8
                interaction_done = True
            time.sleep(0.25)
            if child.poll() is not None:
                _log(
                    f"Shell exited unexpectedly with code {child.returncode}; "
                    f"child log: {child_log_path}"
                )
                return 8

        post_path = _output_path(args.screenshot_prefix, "-03-post-interaction.png")
        if not _screenshot(post_path):
            return 9
        _log(f"post-interaction screenshot: {post_path}")

        if target_index is not None:
            returned = _return_home(child=child, viewport=args.viewport)
            if returned is None:
                _log(f"Home return failed; child log: {child_log_path}")
                return 10
            returned_path = _output_path(args.screenshot_prefix, "-04-returned-shell.png")
            if not _screenshot(returned_path):
                return 10
            _log(f"returned Shell frame: {returned_path}; state={returned}")

        if child.poll() is not None:
            _log(f"Shell died after interaction: {child.returncode}")
            return 11

        _log("stopping Shell through normal lifecycle path")
        child.terminate()
        try:
            code = child.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            _log("Shell did not stop gracefully; killing")
            child.kill()
            code = child.wait(timeout=3.0)
        _log(f"Shell exited rc={code}")
        _log(f"child log: {child_log_path}")
        _log("PASS")
        return 0
    finally:
        try:
            ws.update_lock_child_pid(None)
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
        child_log.close()
        try:
            ws.release_lock()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
