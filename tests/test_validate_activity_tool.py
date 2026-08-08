from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL = PROJECT_ROOT / "tools" / "validate_activity.py"
SAMPLE = PROJECT_ROOT / "activities" / "shape_garden"


class ValidateActivityToolTests(unittest.TestCase):
    def test_repository_built_in_keeps_builtin_source_authority(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(TOOL), str(SAMPLE)],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS org.greia.shape-garden 0.1.0", completed.stdout)

    def test_external_copy_is_not_promoted_to_builtin_trust(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "shape_garden"
            shutil.copytree(SAMPLE, root)
            completed = subprocess.run(
                [sys.executable, str(TOOL), str(root)],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "legacy Activity aliases require built-in package origin",
            completed.stderr,
        )


if __name__ == "__main__":
    unittest.main()
