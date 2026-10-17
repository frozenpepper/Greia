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
IMPORT_SAMPLE = PROJECT_ROOT / "activities" / "colline_allegre"


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

    def _validate_copy_with_extra_source(self, source: str | None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "colline_allegre"
            shutil.copytree(IMPORT_SAMPLE, root, ignore=shutil.ignore_patterns("__pycache__"))
            if source is not None:
                (root / "extra_probe.py").write_text(source, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(TOOL), str(root)],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_unmodified_external_copy_passes_the_runtime_package_policy(self) -> None:
        completed = self._validate_copy_with_extra_source(None)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_curated_imports_outside_the_runtime_policy_are_rejected(self) -> None:
        # The launcher refuses these at start (exit 126); validation must too.
        for module in ("socket", "notarealmodule_xyz"):
            with self.subTest(module=module):
                completed = self._validate_copy_with_extra_source(f"import {module}\n")
                self.assertNotEqual(completed.returncode, 0)
                self.assertNotIn("PASS", completed.stdout)
                self.assertIn(module, completed.stderr)

    def test_policy_allowed_imports_pass(self) -> None:
        completed = self._validate_copy_with_extra_source("import cmath\nimport math\n")
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
