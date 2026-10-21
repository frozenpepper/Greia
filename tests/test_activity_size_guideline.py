"""The per-Activity size limit is a warning guideline, never a refusal.

Owner decision 2026-10-21: 64 MiB guideline; larger Activities are allowed
with a build-time warning and an install-time size notice.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from greia_platform import activities
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_packages import ActivityPackageService
from greia_platform.trust import ActivitySource, PackageTrust

from test_activity_packages import PAINTING, RUNTIME, write_activity_archive

REPO = Path(__file__).resolve().parents[1]
TINY_GUIDELINE = 1000


def tiny_runtime(directory: Path) -> Path:
    text = RUNTIME.read_text(encoding="utf-8")
    assert "maximum_activity_bytes = 67108864" in text
    path = directory / "child-runtime.toml"
    path.write_text(
        text.replace("maximum_activity_bytes = 67108864", f"maximum_activity_bytes = {TINY_GUIDELINE}"),
        encoding="utf-8",
    )
    return path


class ActivitySizeGuidelineTests(unittest.TestCase):
    def test_default_guideline_is_64_mib(self) -> None:
        self.assertEqual(RuntimeCatalogue.load(RUNTIME).maximum_activity_bytes, 64 * 1024 * 1024)
        self.assertEqual(RuntimeCatalogue.default_safe().maximum_activity_bytes, 64 * 1024 * 1024)

    def test_over_guideline_validates_with_warning(self) -> None:
        activities._validated_tree_cache.clear()
        with tempfile.TemporaryDirectory() as tmp:
            runtime = RuntimeCatalogue.load(tiny_runtime(Path(tmp)))
            source = ActivitySource(PAINTING.parent, PackageTrust.BUILT_IN, "greia-system")
            registry = ActivityRegistry((source,), runtime)
            with self.assertLogs("greia_platform.activities", level="WARNING") as logs:
                registration = registry.validate_registration(PAINTING, source)
        self.assertTrue(registration.oversize)
        self.assertIn("large Activity", registration.size_notice() or "")
        self.assertTrue(any("large Activity" in line for line in logs.output))

    def test_install_is_not_refused_for_size_and_reports_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=tiny_runtime(root),
                built_in_root=root / "empty-builtins",
            )
            receipt = service.install_archive(archive)
        self.assertTrue(receipt.large_activity)
        payload = receipt.as_json_dict()
        self.assertTrue(payload["large_activity"])
        self.assertGreater(payload["size_bytes"], TINY_GUIDELINE)
        self.assertIn("over the", str(payload["size_notice"]))

    def test_validator_tool_warns_and_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(REPO / "tools" / "validate_activity.py"),
                 str(PAINTING), "--runtime", str(tiny_runtime(Path(tmp)))],
                capture_output=True, text=True, cwd=REPO,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("WARNING", result.stderr)


if __name__ == "__main__":
    unittest.main()
