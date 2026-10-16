"""Measure each Activity's idle CPU time headlessly (desktop proxy only).

For every requested Activity this tool starts ``activities/<id>/main.py`` in a
child Python process with the SDL *dummy* video/audio drivers and disposable
Greia lifecycle/storage paths.  A tiny in-child probe thread waits for the
Activity's READY marker, records ``resource.getrusage(RUSAGE_SELF)`` (user +
system CPU of every thread), waits the idle window with no input, records it
again, writes the result as JSON and then requests a graceful Greia stop.
It also counts ``pygame.display.flip``/``update`` calls in the window, so a
loop that presents unchanged frames is visible as "presents/s".

The reported figure is CPU-seconds per wall-second over the idle window, as a
percentage of one logical CPU.  It is a desktop *proxy* for the Atom N270:
absolute values differ by roughly an order of magnitude and the dummy SDL
driver makes ``display.flip`` almost free, but the ratio between "redraws every
frame" and "frame-governed" loops is what this tool is for.

Set ``GREIA_FRAME_PROFILE=reference-floor`` to apply the Atom frame budget
(``greia_platform.frame_governor.FramePolicy``) on a desktop.  Use
``--settle`` to skip the intro voice/hint window after READY.

No evidence is written into the repository; all state lives in a temporary
directory that is removed at exit.

    PYTHONDONTWRITEBYTECODE=1 python3 tools/measure_activity_idle_cpu.py \
        --seconds 10 --jobs 3 writing painting costruiamo_ponti
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES = REPO_ROOT / "activities"

# Executed inside the child with ``python -c``: argv = main, result, seconds, settle.
_PROBE = r"""
import json, os, resource, runpy, sys, threading, time
main, result_path, seconds, settle = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
ready = os.environ["GREIA_ACTIVITY_READY_PATH"]
stop = os.environ["GREIA_ACTIVITY_STOP_PATH"]
session = os.environ["GREIA_ACTIVITY_SESSION_ID"]

import pygame
presents = [0]
def _counting(original):
    def wrapper(*args, **kwargs):
        presents[0] += 1
        return original(*args, **kwargs)
    return wrapper
pygame.display.flip = _counting(pygame.display.flip)
pygame.display.update = _counting(pygame.display.update)

def cpu():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime

def watch():
    started = time.monotonic()
    while not os.path.exists(ready):
        if time.monotonic() - started > 90:
            return
        time.sleep(0.05)
    ready_after = time.monotonic() - started
    time.sleep(settle)
    c0, w0, p0 = cpu(), time.monotonic(), presents[0]
    time.sleep(seconds)
    c1, w1, p1 = cpu(), time.monotonic(), presents[0]
    with open(result_path, "w") as handle:
        json.dump({"cpu": c1 - c0, "wall": w1 - w0, "presents": p1 - p0, "ready_after": ready_after}, handle)
    with open(stop, "w") as handle:
        handle.write(session)

threading.Thread(target=watch, daemon=True).start()
sys.argv = [main]
sys.path.insert(0, os.path.dirname(main))
runpy.run_path(main, run_name="__main__")
"""


def measure(activity_id: str, seconds: float, locale: str, settle: float = 0.0) -> dict[str, object]:
    main = ACTIVITIES / activity_id / "main.py"
    if not main.is_file():
        return {"activity": activity_id, "error": "no main.py"}
    with tempfile.TemporaryDirectory(prefix="greia-idle-cpu-") as sandbox:
        scratch = Path(sandbox)
        data = scratch / "data"
        data.mkdir()
        result = scratch / "result.json"
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "GREIA_PROFILE_LOCALE": locale,
            "GREIA_DEVICE_LOCALE": locale,
            "GREIA_OS_ROOT": str(REPO_ROOT),
            "GREIA_ACTIVITY_ROOT": str(main.parent),
            "GREIA_PROFILES_DIR": str(scratch / "profiles"),
            "GREIA_MEDIA_ROOT": str(scratch / "media"),
            "GREIA_SKIP_BOOT_HANDOFF": "1",
            "GREIA_STANDALONE_STORAGE_DIR": str(scratch / "storage"),
            "GREIA_ACTIVITY_SESSION_ID": "idle-cpu-probe",
            "GREIA_ACTIVITY_DATA_DIR": str(data),
            "GREIA_ACTIVITY_READY_PATH": str(data / "ready"),
            "GREIA_ACTIVITY_STOP_PATH": str(data / "stop"),
        })
        command = [sys.executable, "-c", _PROBE, str(main), str(result), str(seconds), str(settle)]
        child = subprocess.Popen(
            command, cwd=str(main.parent), env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            _, stderr = child.communicate(timeout=seconds + settle + 120)
        except subprocess.TimeoutExpired:
            child.kill()
            _, stderr = child.communicate()
            return {"activity": activity_id, "error": "timeout"}
        deadline = time.monotonic() + 1.0
        while not result.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not result.exists():
            tail = stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or ["?"]
            return {"activity": activity_id, "error": f"no result (rc={child.returncode}): {tail[0][:120]}"}
        values = json.loads(result.read_text())
        return {
            "activity": activity_id,
            "cpu_percent": round(100.0 * values["cpu"] / max(values["wall"], 1e-6), 1),
            "presents_per_s": round(values["presents"] / max(values["wall"], 1e-6), 1),
            "ready_s": round(values["ready_after"], 1),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("activities", nargs="*", help="Activity ids (default: all)")
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--locale", default="it")
    parser.add_argument(
        "--settle", type=float, default=0.0,
        help="seconds to wait after READY before measuring (skip intro voice/hints)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON lines")
    args = parser.parse_args(argv)
    ids = args.activities or sorted(p.name for p in ACTIVITIES.iterdir() if (p / "main.py").is_file())
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        rows = list(pool.map(lambda a: measure(a, args.seconds, args.locale, args.settle), ids))
    for row in rows:
        if args.json:
            print(json.dumps(row))
        elif "error" in row:
            print(f"{row['activity']:<26} ERROR {row['error']}")
        else:
            print(
                f"{row['activity']:<26} {row['cpu_percent']:>6.1f}%  "
                f"{row['presents_per_s']:>5.1f} presents/s  (ready {row['ready_s']}s)"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
