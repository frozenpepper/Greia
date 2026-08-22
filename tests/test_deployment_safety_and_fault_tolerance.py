from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from greia_platform.activities import (
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
)
from greia_platform.customization import ThemePalette
from greia_platform.hardware import HardwareDefaults
from greia_platform.profiles import ProfilePolicy
from greia_platform.trust import ActivitySource, PackageTrust

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DeploymentSafetyAndFaultToleranceTests(unittest.TestCase):
    def test_runtime_catalogue_falls_back_to_default_safe_on_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            empty_file = Path(temporary) / "child-runtime.toml"
            empty_file.touch()
            catalogue = RuntimeCatalogue.load(empty_file)
            self.assertEqual(catalogue.api_version, "0.1")
            self.assertIn("audio.basic", catalogue.allowed_capabilities)
            self.assertIn(".ds_store", catalogue.forbidden_file_names)

            corrupt_file = Path(temporary) / "bad-runtime.toml"
            corrupt_file.write_text("invalid [[ toml :::", encoding="utf-8")
            corrupt_catalogue = RuntimeCatalogue.load(corrupt_file)
            self.assertEqual(corrupt_catalogue.api_version, "0.1")

    def test_hardware_defaults_falls_back_to_default_safe_on_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            empty_file = Path(temporary) / "hardware-settings.toml"
            empty_file.touch()
            defaults = HardwareDefaults.load(empty_file)
            self.assertEqual(defaults.schema_version, 1)
            self.assertEqual(defaults.keyboard_layout, "us")
            self.assertEqual(defaults.mic_gain, 2.0)

            corrupt_file = Path(temporary) / "bad.toml"
            corrupt_file.write_text("invalid [[ toml :::", encoding="utf-8")
            corrupt_defaults = HardwareDefaults.load(corrupt_file)
            self.assertEqual(corrupt_defaults.schema_version, 1)

    def test_theme_palette_falls_back_to_default_safe_on_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            empty_file = Path(temporary) / "theme-defaults.toml"
            empty_file.touch()
            palette = ThemePalette.load(empty_file)
            self.assertEqual(palette.schema_version, 1)
            self.assertEqual(palette.default_background, "cream")
            self.assertEqual(palette.default_accent, "sunshine")

    def test_profile_policy_falls_back_to_default_safe_on_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            empty_file = Path(temporary) / "profile-defaults.toml"
            empty_file.touch()
            policy = ProfilePolicy.load(empty_file)
            self.assertEqual(policy.schema_version, 1)
            self.assertEqual(policy.default_avatar, "rainbow")

    def test_activity_registry_isolates_corrupted_activity_in_non_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activities_dir = Path(temporary) / "activities"
            activities_dir.mkdir()

            valid_dest = activities_dir / "shape_garden"
            shutil.copytree(PROJECT_ROOT / "activities" / "shape_garden", valid_dest)

            corrupt_dest = activities_dir / "broken_activity"
            corrupt_dest.mkdir()
            (corrupt_dest / "activity.toml").write_text(
                "invalid toml content = = = broken", encoding="utf-8"
            )

            source = ActivitySource(activities_dir, PackageTrust.BUILT_IN, "test-source")
            registry = ActivityRegistry(
                [source],
                RuntimeCatalogue.default_safe(),
                fail_closed=False,
            )
            discovered = registry.discover()
            self.assertEqual(len(discovered), 1)
            self.assertEqual(discovered[0].activity_id, "org.greia.shape-garden")
            self.assertIn(str(corrupt_dest.resolve()), registry.unvalidated_activities)

            with self.assertRaises(ActivityValidationError):
                registry.discover(fail_closed=True)


if __name__ == "__main__":
    unittest.main()
