"""Record real frames of a Greia Activity driven by scripted input.

Reuses the Simulator's owned loopback bridge (same mechanism as
tools/headless_greia_activity.py) but keeps sampling frames at a fixed rate
while a timeline of mouse/key events is injected. Output: numbered PNGs.

Usage:
  python3 record_activity.py ACTIVITY_DIR SCRIPT.json OUT_DIR [--viewport 1280x720] [--fps 20]

SCRIPT.json: {"duration": 6.0, "events": [
  {"t": 0.5, "type": "move", "x": 100, "y": 200},
  {"t": 0.6, "type": "down"}, {"t": 0.7, "type": "move", ...}, {"t": 1.0, "type": "up"},
  {"t": 2.0, "type": "click", "x": 300, "y": 300}, {"t": 3, "type": "key", "key": "SPACE"}]}
Coordinates are in the viewport's own pixels.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from greia_simulator.remote_bridge import SimulatorRemoteBridge  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("activity")
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--viewport", default="1280x720")
    ap.add_argument("--fps", type=float, default=20.0)
    ap.add_argument("--locale", default="en")
    a = ap.parse_args()

    spec = json.loads(Path(a.script).read_text())
    events = sorted(spec["events"], key=lambda e: e["t"])
    duration = float(spec["duration"])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    main_py = (REPO / a.activity / "main.py").resolve()

    bridge = SimulatorRemoteBridge(port=0, host="127.0.0.1")
    bridge.start()
    child = None
    try:
        with tempfile.TemporaryDirectory(prefix="greia-rec-") as sb:
            s = Path(sb)
            env = os.environ.copy()
            env.update({
                "PYTHONPATH": str(REPO / "src"), "PYTHONDONTWRITEBYTECODE": "1",
                "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
                "GREIA_PROFILE_LOCALE": a.locale, "GREIA_DEVICE_LOCALE": a.locale,
                "GREIA_OS_ROOT": str(REPO), "GREIA_ACTIVITY_ROOT": str(main_py.parent),
                "GREIA_PROFILES_DIR": str(s / "profiles"),
                "GREIA_DEVELOPER_ACTIVITY_ROOT": str(s / "developer"),
                "GREIA_PARENT_ACTIVITY_ROOT": str(s / "parent" / "active"),
                "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(s / "packages"),
                "GREIA_MEDIA_ROOT": str(s / "media"),
                "GREIA_MAIN_CREDENTIAL_PATH": str(s / "credentials" / "main.json"),
                "GREIA_ACTIVE_PROFILE_STATUS": str(s / "active-profile.json"),
                "GREIA_SKIP_BOOT_HANDOFF": "1",
                "GREIA_STANDALONE_STORAGE_DIR": str(s / "standalone-storage"),
            })
            cmd = [sys.executable, "-m", "greia_simulator.python_activity",
                   "--viewport", a.viewport, "--remote-port", str(bridge.port), str(main_py)]
            log = open(s / "child.log", "wb")
            child = subprocess.Popen(cmd, cwd=str(REPO), env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT)
            until = time.monotonic() + 40
            while time.monotonic() < until:
                st = bridge.get_state()
                if st.get("mode") == "activity" and st.get("frame_count", 0) > 0:
                    break
                if child.poll() is not None:
                    print("child died", (s / "child.log").read_text()[-800:])
                    return 2
                time.sleep(0.1)
            else:
                print("no frame")
                return 3
            time.sleep(1.0)  # let intro animation settle
            t0 = time.monotonic()
            n = 0
            idx = 0
            step = 1.0 / a.fps
            nxt = 0.0
            while True:
                now = time.monotonic() - t0
                while idx < len(events) and events[idx]["t"] <= now:
                    e = events[idx]
                    idx += 1
                    k = e["type"]
                    if k == "click":
                        bridge.queue_mouse(e["x"], e["y"], "click")
                    elif k == "move":
                        bridge.queue_mouse(e["x"], e["y"], "move")
                    elif k == "down":
                        bridge.queue_mouse(e.get("x", 0), e.get("y", 0), "down")
                    elif k == "up":
                        bridge.queue_mouse(e.get("x", 0), e.get("y", 0), "up")
                    elif k == "key":
                        bridge.queue_key(e["key"])
                if now >= nxt:
                    png = bridge.get_latest_frame_png()
                    if png:
                        (out / f"f{n:05d}.png").write_bytes(png)
                        n += 1
                    nxt += step
                if now >= duration:
                    break
                time.sleep(0.004)
            print(f"recorded {n} frames in {now:.1f}s -> {out}")
    finally:
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
        bridge.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
