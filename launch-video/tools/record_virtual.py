"""Deterministic Activity capture on a virtual clock: python3 record_virtual.py ACTIVITY SCRIPT.json OUT_DIR [--viewport 1920x1125] [--fps 30]
SCRIPT.json = {"duration": seconds after settle, "settle": 1.0, "events": [{"t":..., "type": "move|down|up|click|key", "x":..,"y":..}]}
Event times are virtual seconds after the settle period. Independent of machine load."""
import argparse, os, subprocess, sys, tempfile, time
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from greia_simulator.remote_bridge import SimulatorRemoteBridge  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("activity"); ap.add_argument("script"); ap.add_argument("out")
ap.add_argument("--viewport", default="1920x1125"); ap.add_argument("--fps", default="30"); ap.add_argument("--locale", default="en"); ap.add_argument("--seed", default="7")
a = ap.parse_args()
main_py = (REPO / a.activity / "main.py").resolve()
bridge = SimulatorRemoteBridge(port=0, host="127.0.0.1"); bridge.start()
try:
    with tempfile.TemporaryDirectory(prefix="greia-vrec-") as sb:
        s = Path(sb)
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": f"{Path(__file__).resolve().parent / 'vclock'}:{REPO / 'src'}", "PYTHONDONTWRITEBYTECODE": "1",
            "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy", "GREIA_PROFILE_LOCALE": a.locale, "GREIA_DEVICE_LOCALE": a.locale,
            "GREIA_OS_ROOT": str(REPO), "GREIA_ACTIVITY_ROOT": str(main_py.parent), "GREIA_PROFILES_DIR": str(s / "profiles"),
            "GREIA_DEVELOPER_ACTIVITY_ROOT": str(s / "developer"), "GREIA_PARENT_ACTIVITY_ROOT": str(s / "parent" / "active"),
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(s / "packages"), "GREIA_MEDIA_ROOT": str(s / "media"),
            "GREIA_MAIN_CREDENTIAL_PATH": str(s / "credentials" / "main.json"), "GREIA_ACTIVE_PROFILE_STATUS": str(s / "active-profile.json"),
            "GREIA_SKIP_BOOT_HANDOFF": "1", "GREIA_STANDALONE_STORAGE_DIR": str(s / "standalone-storage"), "GREIA_FRAME_PROFILE": "standard", "PYTHONFAULTHANDLER": "1",
            "VCLOCK_SCRIPT": str(Path(a.script).resolve()), "VCLOCK_OUT": str(Path(a.out).resolve()), "VCLOCK_FPS": a.fps, "VCLOCK_SEED": a.seed,
        })
        cmd = [sys.executable, "-m", "greia_simulator.python_activity", "--viewport", a.viewport, "--remote-port", str(bridge.port), str(main_py)]
        for attempt in range(1, 5):
            import shutil
            shutil.rmtree(a.out, ignore_errors=True)
            t0 = time.time()
            p = subprocess.run(cmd, cwd=str(REPO), env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
            ok = "VCLOCK_DONE" in (p.stdout or "")
            print((p.stdout or "")[-60:].strip(), "| rc", p.returncode, "| attempt", attempt, "| wall %.0fs" % (time.time() - t0))
            if ok:
                break
            open("/Volumes/Venus/GREIA_LAUNCH_VIDEO/vrec_err.log", "w").write(p.stderr or "")
finally:
    bridge.stop()
