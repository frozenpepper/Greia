from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.activities import ActivityRegistry, ActivityValidationError, RuntimeCatalogue


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ActivityAudienceManifestTests(unittest.TestCase):
    def _write_activity(self, root: Path, education_extra: str, presentation_extra: str = "") -> Path:
        package = root / "sample"
        package.mkdir()
        (package / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (package / "activity.toml").write_text(
            f'''[activity]
id = "org.greia.audience-test"
legacy_ids = []
title_key = "activity.audience_test.title"
version = "0.1.0"
icon = "robot"
languages = ["it"]

[presentation]
categories = ["learn"]
{presentation_extra}

[education]
categories = ["test"]
difficulty = 4
{education_extra}
skills = [{{ id = "test.skill", weight = 1 }}]
events = []

[runtime]
type = "python"
api_version = "0.1"
entrypoint = "main.py"

[input]
profile = "hybrid"

[requirements]
required_capabilities = ["display"]
optional_capabilities = []

[permissions]
requested = []

[storage]
schema_version = 1
''',
            encoding="utf-8",
        )
        return package

    def _registry(self, root: Path) -> ActivityRegistry:
        return ActivityRegistry(
            [root], RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        )

    def test_manifest_parses_independent_age_difficulty_and_discovery_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_activity(
                root,
                '''recommended_age_min = 5
recommended_age_max = 9
difficulty_min = 2
difficulty_max = 8
adaptive_difficulty = true''',
                'discovery_tags = ["numbers", "puzzles"]',
            )
            manifest = self._registry(root).discover()[0]
            self.assertEqual(manifest.recommended_age_min, 5)
            self.assertEqual(manifest.recommended_age_max, 9)
            self.assertEqual(manifest.difficulty, 4)
            self.assertEqual((manifest.difficulty_min, manifest.difficulty_max), (2, 8))
            self.assertTrue(manifest.adaptive_difficulty)
            self.assertEqual(manifest.discovery_tags, ("numbers", "puzzles"))

    def test_age_range_must_be_ordered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_activity(
                root,
                "recommended_age_min = 9\nrecommended_age_max = 5",
            )
            with self.assertRaisesRegex(ActivityValidationError, "recommended_age_min"):
                self._registry(root).discover()

    def test_adaptive_range_requires_flag_and_contains_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_activity(root, "difficulty_min = 2\ndifficulty_max = 8")
            with self.assertRaisesRegex(ActivityValidationError, "adaptive_difficulty"):
                self._registry(root).discover()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_activity(
                root,
                "difficulty_min = 5\ndifficulty_max = 8\nadaptive_difficulty = true",
            )
            with self.assertRaisesRegex(ActivityValidationError, "inside"):
                self._registry(root).discover()

    def test_old_manifest_without_new_fields_remains_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_activity(root, "")
            manifest = self._registry(root).discover()[0]
            self.assertIsNone(manifest.recommended_age_min)
            self.assertIsNone(manifest.recommended_age_max)
            self.assertEqual(manifest.discovery_tags, ())
            self.assertFalse(manifest.adaptive_difficulty)


if __name__ == "__main__":
    unittest.main()
