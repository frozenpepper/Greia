"""Capture Encyclopedia v0.1 golden-master Simulator evidence.

This driver runs one real Greia Shell session per golden-master page
against the built-in ``org.greia.enciclopedia`` Activity, navigates from
the Home portal to the required section and entry, and captures the
required frames. The protected Greia Home return is exercised at the
end of every session to prove clean lifecycle ownership.

This script deliberately does NOT walk the full 43-page mechanical
traversal: that is owned by tools/encyclopedia_v01_headless_traversal.py.
Golden-master evidence is a small, owner-reviewable set, not a full
acceptance run.
"""
from __future__ import annotations

import argparse
import json as _json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = Path(__file__).resolve().parent
ACTIVITY_ID = "org.greia.enciclopedia"
ACTIVITY_DIR = REPO_ROOT / "activities" / "enciclopedia_greia"
DEFAULT_PORT = 8767
BRIDGE_URL = f"http://127.0.0.1:{DEFAULT_PORT}"

for candidate in (str(REPO_ROOT), str(REPO_ROOT / "src"), str(TOOLS_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import headless_greia_simulator as headless  # noqa: E402


# Home is a 3x2 portal grid laid out
# row-major: animals(0), space(1), earth(2), body(3), machines(4), history(5).
HOME_PORTAL_COLUMNS = 3
SECTION_INDEX: dict[str, int] = {
    "animals": 0,
    "space": 1,
    "earth": 2,
    "body": 3,
    "machines": 4,
    "history": 5,
}

# Per-section entry layout for the four golden-master factual entries.
SECTION_ENTRY: dict[str, dict[str, int]] = {
    "animals": {"lion": 0},
    "space": {"saturn": 7},
    "machines": {"gears": 0},
    "history": {"pyramids": 4},
}

PAGE_CHANGE_FRAME_ADVANCE = 3
ACTIVATE_FRAME_ADVANCE = 1
POST_ACTIVATE_SETTLE_SECONDS = 0.8


@dataclass(frozen=True, slots=True)
class Capture:
    label: str
    relative_path: str
    activate: bool = False


def _log(msg: str) -> None:
    print(f"[golden-master] {msg}", flush=True)


def _screenshot(out_path: Path) -> bool:
    try:
        with urllib.request.urlopen(f"{BRIDGE_URL}/api/frame", timeout=10.0) as resp:  # noqa: S310
            data = resp.read()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        _log(f"screenshot failed: {exc}")
        return False


def _http_post(path: str, payload: dict) -> int:
    body = _json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{BRIDGE_URL}{path}", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:  # noqa: S310
            return resp.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:  # noqa: BLE001
        return -1


def _key(name: str) -> bool:
    return _http_post("/api/input/key", {"key": name.upper(), "action": "press"}) in (200, 204)


def _click(x: int, y: int) -> bool:
    return _http_post(
        "/api/input/mouse",
        {"x": int(x), "y": int(y), "action": "click", "button": 1},
    ) in (200, 204)


def _get_state() -> dict:
    with urllib.request.urlopen(f"{BRIDGE_URL}/api/state", timeout=5.0) as resp:  # noqa: S310
        return _json.loads(resp.read().decode("utf-8"))


def _wait_for_state(predicate, *, timeout: float, child: subprocess.Popen) -> dict | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            return None
        try:
            state = _get_state()
        except Exception:
            time.sleep(0.1)
            continue
        if predicate(state):
            return state
        time.sleep(0.1)
    return None


def _press_and_wait(
    key: str,
    *,
    child: subprocess.Popen,
    frame_advance: int = PAGE_CHANGE_FRAME_ADVANCE,
    settle_seconds: float = 0.0,
    timeout: float = 6.0,
) -> bool:
    before = int(_get_state().get("frame_count", 0))
    if not _key(key):
        _log(f"key {key} was rejected")
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            return False
        try:
            state = _get_state()
        except Exception:
            time.sleep(0.05)
            continue
        if int(state.get("frame_count", 0)) - before >= frame_advance:
            if settle_seconds > 0:
                time.sleep(settle_seconds)
            return True
        time.sleep(0.05)
    return False


def _open_activity_through_shell(
    child: subprocess.Popen, route, *, timeout: float = 30.0
) -> bool:
    state = _wait_for_state(
        lambda s: s.get("mode") in ("profiles", "activities", "activity"),
        timeout=timeout,
        child=child,
    )
    if state is None:
        _log("Shell did not reach a profile/activities surface")
        return False
    if state.get("mode") == "activity":
        return True
    activity_state = headless._send_profile_and_activity_launch(
        child=child, route=route
    )
    return activity_state is not None


def _navigate_internal(
    child: subprocess.Popen,
    *,
    stage: str,
    keys: tuple[str, ...],
    frame_advance: int = PAGE_CHANGE_FRAME_ADVANCE,
) -> bool:
    for index, key in enumerate(keys, start=1):
        if not _press_and_wait(
            key,
            child=child,
            frame_advance=frame_advance,
            timeout=8.0,
        ):
            _log(f"internal navigation failed at {stage} key #{index}={key}")
            return False
    return True


def _route_home_to_section(section_id: str) -> tuple[str, ...]:
    """Return the keyboard sequence to reach ``section_id`` from Home.

    Home portal selection starts at index 0 (Animals). Move focus to the
    requested portal, then press RETURN to open the section.
    """
    index = SECTION_INDEX[section_id]
    rights = index % HOME_PORTAL_COLUMNS
    downs = index // HOME_PORTAL_COLUMNS
    keys: list[str] = []
    if rights:
        keys.extend(["RIGHT"] * rights)
    if downs:
        keys.extend(["DOWN"] * downs)
    keys.append("RETURN")
    return tuple(keys)


def _route_section_to_entry(section_id: str, entry_id: str) -> tuple[str, ...]:
    """Return the keyboard sequence to open ``entry_id`` inside ``section_id``."""
    index = SECTION_ENTRY[section_id][entry_id]
    keys: list[str] = []
    if section_id == "animals":
        rights = index % 3
        downs = index // 3
        if rights:
            keys.extend(["RIGHT"] * rights)
        if downs:
            keys.extend(["DOWN"] * downs)
    elif section_id == "space":
        delta = index - 3
        if delta >= 0:
            keys.extend(["RIGHT"] * delta)
        else:
            keys.extend(["LEFT"] * (-delta))
    elif section_id == "machines":
        rights = index % 3
        downs = index // 3
        if rights:
            keys.extend(["RIGHT"] * rights)
        if downs:
            keys.extend(["DOWN"] * downs)
    elif section_id == "history":
        if index > 0:
            keys.extend(["RIGHT"] * index)
    else:
        raise ValueError(f"unknown section: {section_id!r}")
    keys.append("RETURN")
    return tuple(keys)


def _press_protected_home(viewport: str) -> bool:
    try:
        from greia_platform.system_chrome import ActivitySystemChromeLayout
        from greia_simulator.device import parse_viewport
        w, h = parse_viewport(viewport)
        home = ActivitySystemChromeLayout.for_surface(w, h).home_hitbox
        return _click(home.x + home.width // 2, home.y + home.height // 2)
    except Exception as exc:  # noqa: BLE001
        _log(f"protected Home click failed: {exc}")
        return False


def _set_profile_interface_size(workspace, profile_id: str, value: str) -> None:
    try:
        workspace.set_interface_size(profile_id, value)
        _log(f"set profile={profile_id!r} interface_size={value!r}")
    except Exception as exc:  # noqa: BLE001
        _log(f"failed to set interface_size {value!r} for {profile_id!r}: {exc}")
        raise


def _run_session(
    *,
    workspace_dir: Path,
    evidence_dir: Path,
    locale: str,
    viewport: str,
    interface_size: str,
    navigation_keys: tuple[str, ...],
    captures: tuple[Capture, ...],
) -> int:
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir, ignore_errors=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "screenshots").mkdir(parents=True, exist_ok=True)

    try:
        workspace, target_id = headless._prepare_workspace(
            workspace_dir, ACTIVITY_DIR, ACTIVITY_ID
        )
    except Exception as exc:  # noqa: BLE001
        _log(f"workspace prep failed: {exc}")
        return 2
    if target_id != ACTIVITY_ID:
        _log(f"resolved wrong Activity identity: {target_id}")
        workspace.release_lock()
        return 3

    profile_store = workspace.profile_store()
    profile = profile_store.ensure_initialized()[0]
    _set_profile_interface_size(workspace, profile.profile_id, interface_size)

    try:
        route, _visible = headless._discover_launch_route(
            workspace, ACTIVITY_ID, locale=locale
        )
    except Exception as exc:  # noqa: BLE001
        _log(f"route discovery failed: {exc}")
        workspace.release_lock()
        return 4
    _log(f"route: {route.describe()}")

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["GREIA_SIMULATOR_HEADLESS"] = "1"
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env.update(workspace.environment())

    child_log_path = evidence_dir / "child.log"
    child_log = child_log_path.open("wb")
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "greia_simulator.child_shell",
            "--viewport",
            viewport,
            "--language",
            locale,
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
        workspace.update_lock_child_pid(child.pid)
    except Exception as exc:  # noqa: BLE001
        _log(f"failed to register child PID: {exc}")
        child.terminate()
        child.wait(timeout=5)
        child_log.close()
        return 5

    failures: list[str] = []
    try:
        if not headless._wait_for_bridge(DEFAULT_PORT, timeout=15.0):
            _log("remote bridge never came up")
            return 6
        _log("remote bridge is up")
        if not _open_activity_through_shell(child, route):
            _log("Activity did not reach activity mode")
            return 7

        # Settle on the Encyclopedia Home page.
        time.sleep(0.4)

        if navigation_keys:
            if not _navigate_internal(
                child,
                stage="session-navigation",
                keys=navigation_keys,
                frame_advance=PAGE_CHANGE_FRAME_ADVANCE,
            ):
                failures.append("session-navigation failed")
            else:
                time.sleep(0.3)

        for capture in captures:
            if child.poll() is not None:
                _log(f"Shell died before {capture.label}")
                return 8
            out = evidence_dir / "screenshots" / capture.relative_path
            if not _screenshot(out):
                failures.append(f"screenshot failed: {capture.label}")
            else:
                _log(f"captured {capture.label} -> {out.name}")
            if capture.activate:
                if not _press_and_wait(
                    "RETURN",
                    child=child,
                    frame_advance=ACTIVATE_FRAME_ADVANCE,
                    settle_seconds=POST_ACTIVATE_SETTLE_SECONDS,
                    timeout=6.0,
                ):
                    failures.append(f"ACTIVATE failed: {capture.label}")
                else:
                    activated_path = out.with_name(
                        out.stem.replace("-initial", "-activated") + out.suffix
                    )
                    if out.stem.endswith("-initial"):
                        if not _screenshot(activated_path):
                            failures.append(
                                f"screenshot failed: {capture.label} activated"
                            )
                        else:
                            _log(
                                f"captured {capture.label} activated -> "
                                f"{activated_path.name}"
                            )
                    else:
                        _log(
                            f"capture {capture.label} has activate=True but is not an initial frame; "
                            f"activated screenshot skipped"
                        )
    finally:
        if child.poll() is None:
            _log("invoking protected Greia Home at platform home-hitbox")
            _press_protected_home(viewport)
            time.sleep(0.5)
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=8.0)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3.0)
        try:
            workspace.update_lock_child_pid(None)
        except Exception:  # noqa: BLE001
            pass
        try:
            workspace.release_lock()
        except Exception:  # noqa: BLE001
            pass
        child_log.close()

    if failures:
        for failure in failures:
            _log(f"FAIL: {failure}")
        return 9
    _log("PASS")
    return 0


def _build_session_jobs(
    *, viewport: str, interface_size: str
) -> list[dict[str, object]]:
    """One session per golden-master capture, plus Home and Animals."""
    return [
        {
            "tag": "home",
            "navigation_keys": (),
            "captures": (Capture("home", "01-home.png"),),
            "viewport": viewport,
            "interface_size": interface_size,
        },
        {
            "tag": "animals",
            "navigation_keys": ("RETURN",),
            "captures": (Capture("animals", "02-animals.png"),),
            "viewport": viewport,
            "interface_size": interface_size,
        },
        {
            "tag": "lion",
            "navigation_keys": (
                "RETURN",   # Home -> Animals
                "RETURN",   # Animals -> Lion
            ),
            "captures": (
                Capture("lion-initial", "03-lion-initial.png", activate=True),
            ),
            "viewport": viewport,
            "interface_size": interface_size,
        },
        {
            "tag": "saturn",
            "navigation_keys": (
                "RIGHT",    # focus Space portal
                "RETURN",   # Home -> Space
                "RIGHT", "RIGHT", "RIGHT", "RIGHT",  # Earth -> Saturn (delta=4)
                "RETURN",   # Space -> Saturn
            ),
            "captures": (
                Capture("saturn-initial", "05-saturn-initial.png", activate=True),
            ),
            "viewport": viewport,
            "interface_size": interface_size,
        },
        {
            "tag": "gears",
            "navigation_keys": (
                "RIGHT",    # col=1
                "DOWN",     # row=1 -> Machines portal
                "RETURN",   # Home -> Machines
                "RETURN",   # Machines -> Gears (initial focus)
            ),
            "captures": (
                Capture("gears-initial", "07-gears-initial.png", activate=True),
            ),
            "viewport": viewport,
            "interface_size": interface_size,
        },
        {
            "tag": "pyramids",
            "navigation_keys": (
                "RIGHT", "RIGHT",  # col=2
                "DOWN",            # row=1 -> History portal
                "RETURN",          # Home -> History
                "RIGHT", "RIGHT", "RIGHT", "RIGHT",  # Dinosaurs -> Pyramids
                "RETURN",          # History -> Pyramids
            ),
            "captures": (
                Capture("pyramids-initial", "09-pyramids-initial.png", activate=True),
            ),
            "viewport": viewport,
            "interface_size": interface_size,
        },
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locale", default="it")
    parser.add_argument("--viewport", default="1024x600")
    parser.add_argument(
        "--interface-size",
        default="normal",
        choices=("compact", "normal", "large"),
    )
    parser.add_argument(
        "--jobs",
        default="all",
        help=(
            "Comma-separated job tags. Default 'all' runs every job. "
            "Use one of home, animals, lion, saturn, gears, pyramids."
        ),
    )
    parser.add_argument("--responsive-tag", default=None,
                        help="Override the evidence-dir subfolder name")
    parser.add_argument("--evidence-root", required=True)
    args = parser.parse_args(argv)

    evidence_root = Path(args.evidence_root).expanduser()
    evidence_root.mkdir(parents=True, exist_ok=True)

    requested = {tag.strip() for tag in args.jobs.split(",") if tag.strip()}
    if "all" in requested:
        requested = {"home", "animals", "lion", "saturn", "gears", "pyramids"}

    jobs = _build_session_jobs(
        viewport=args.viewport, interface_size=args.interface_size
    )
    selected = [job for job in jobs if job["tag"] in requested]
    if not selected:
        _log(f"no jobs match {args.jobs!r}")
        return 1

    overall = 0
    for job in selected:
        tag = str(job["tag"])
        # Workspace MUST live outside the Greia source tree.
        workspace = Path(f"~/.greia-simulator-goldenmaster-{tag}").expanduser()
        evidence_name = args.responsive_tag or tag
        evidence = evidence_root / evidence_name
        code = _run_session(
            workspace_dir=workspace,
            evidence_dir=evidence,
            locale=args.locale,
            viewport=str(job["viewport"]),
            interface_size=str(job["interface_size"]),
            navigation_keys=tuple(job["navigation_keys"]),  # type: ignore[arg-type]
            captures=tuple(job["captures"]),  # type: ignore[arg-type]
        )
        if code != 0:
            overall = code
            _log(f"job {tag} returned {code}")
            break
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
