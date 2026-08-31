from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


REPO = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = REPO / "activities" / "enciclopedia_greia"


class EncyclopediaScriptLaunchTests(unittest.TestCase):
    def test_entrypoint_import_graph_works_in_greia_script_mode(self) -> None:
        """Greia executes main.py as a script, not as an imported package."""

        probe = (
            "import runpy, sys; "
            f"sys.path.insert(0, {str(ACTIVITY_ROOT)!r}); "
            f"runpy.run_path({str(ACTIVITY_ROOT / 'main.py')!r}, "
            "run_name='greia_encyclopedia_script_import_probe')"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(REPO / "src")
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=REPO,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            "Encyclopedia script-mode import graph failed before Activity startup:\n"
            + completed.stderr,
        )


if __name__ == "__main__":
    unittest.main()
