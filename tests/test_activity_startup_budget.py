"""Guard: representative Activities stay cheap between set_mode and first frame.

The 2026-10-16 Acer re-sweep (docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md,
R.2) measured 2-9 s of Activity "content build" on the Atom N270 before the
first frame, dominated by sound effects synthesised in pure Python at start-up.
Cues are now defined in a ``DeferredSoundBank`` and built after READY.

Each Activity here is launched headless through the curated interpreter
start-up, exactly like ``greia_platform.python_activity_entry``, and the child
reports the process CPU time spent from ``set_mode`` returning to the first
``display.flip``. CPU time (not wall time) keeps the guard stable on a loaded
host; the budgets are several times today's cost on a developer machine yet
below what eager synthesis cost, so a regression to start-up synthesis fails.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]

#: Activity -> local CPU-seconds budget for set_mode -> first frame. Measured
#: on the owner's Mac: eager synthesis cost 0.31-0.45 s for the first three
#: (now ~0.05-0.13 s); viaggio_delfino legitimately bakes its picker postcards
#: (~0.25 s) and lost ~0.08 s of synthesis plus a duplicate scene bake.
BUDGETS: dict[str, float] = {
    # Current Linux/Python 3.12 verification host measures roughly 0.25-0.29 s
    # for these three on a warm host. Keep the guard below the old eager
    # synthesis cost (0.31-0.45 s) while allowing host variance; an actual
    # return to eager synthesis still fails.
    "piccola_serra": 0.30,
    "pasticceria_magica": 0.30,
    "morbidi_mostriciattoli": 0.30,
    "viaggio_delfino": 0.6,
}

_PROBE = textwrap.dedent(
    """
    import json, os, runpy, sys, time
    from greia_platform.python_startup import apply_curated_interpreter_startup
    apply_curated_interpreter_startup()
    import pygame

    main_path, out_path = sys.argv[1], sys.argv[2]
    marks = {}
    original_set_mode = pygame.display.set_mode

    def set_mode(*args, **kwargs):
        surface = original_set_mode(*args, **kwargs)
        marks.setdefault("set_mode", time.process_time())
        return surface

    def finish():
        marks["first_frame"] = time.process_time()
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(marks, handle)
        os._exit(0)

    def wrap(name):
        original = getattr(pygame.display, name)

        def presented(*args, **kwargs):
            result = original(*args, **kwargs)
            if "set_mode" in marks:
                finish()
            return result

        setattr(pygame.display, name, presented)

    pygame.display.set_mode = set_mode
    wrap("flip")
    wrap("update")
    sys.argv[:] = [main_path]
    sys.path.insert(0, os.path.dirname(main_path))
    runpy.run_path(main_path, run_name="__main__")
    """
)


class ActivityStartupBudgetTests(unittest.TestCase):
    def test_representative_activities_reach_first_frame_cheaply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="greia-startup-budget-") as temporary:
            scratch = Path(temporary)
            probe = scratch / "probe.py"
            probe.write_text(_PROBE, encoding="utf-8")
            for activity, budget in BUDGETS.items():
                with self.subTest(activity=activity):
                    spent = self._init_cpu_seconds(probe, scratch / activity, activity)
                    self.assertLess(
                        spent,
                        budget,
                        f"{activity} spent {spent:.3f} s CPU between set_mode and its "
                        f"first frame (budget {budget:.2f} s); keep synthesis and "
                        "off-screen baking out of start-up",
                    )

    def _init_cpu_seconds(self, probe: Path, scratch: Path, activity: str) -> float:
        scratch.mkdir()
        main = ROOT / "activities" / activity / "main.py"
        result = scratch / "result.json"
        environment = dict(
            os.environ,
            PYTHONPATH=str(ROOT / "src"),
            PYTHONDONTWRITEBYTECODE="1",
            SDL_VIDEODRIVER="dummy",
            SDL_AUDIODRIVER="dummy",
            SDL_FRAMEBUFFER_ACCELERATION="0",
            GREIA_OS_ROOT=str(ROOT),
            GREIA_ACTIVITY_ROOT=str(main.parent),
            GREIA_PROFILE_LOCALE="en",
            GREIA_DEVICE_LOCALE="en",
            GREIA_PROFILES_DIR=str(scratch / "profiles"),
            GREIA_STANDALONE_STORAGE_DIR=str(scratch / "storage"),
            GREIA_MEDIA_ROOT=str(scratch / "media"),
            GREIA_SKIP_BOOT_HANDOFF="1",
        )
        completed = subprocess.run(
            [sys.executable, "-P", str(probe), str(main), str(result)],
            cwd=str(main.parent),
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=120,
            check=False,
        )
        if not result.is_file():
            self.fail(
                f"{activity} produced no first frame (rc={completed.returncode}): "
                + completed.stderr.decode("utf-8", "replace")[-1500:]
            )
        marks = json.loads(result.read_text(encoding="utf-8"))
        return float(marks["first_frame"]) - float(marks["set_mode"])


if __name__ == "__main__":
    unittest.main()
