from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.activities import (
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
)
from greia_platform.input_core import InteractionProfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ActivityInputManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime/child-runtime.toml")

    def test_explicit_pointer_profile_is_parsed_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self._package(root, profile="pointer")
            manifest = ActivityRegistry([root], self.runtime).validate_package(package)
            self.assertEqual(manifest.input_profile, InteractionProfile.POINTER.value)

    def test_api_01_manifest_without_input_table_uses_compatibility_hybrid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self._package(root, profile=None)
            manifest = ActivityRegistry([root], self.runtime).validate_package(package)
            self.assertEqual(manifest.input_profile, InteractionProfile.HYBRID.value)

    def test_unknown_profile_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self._package(root, profile="joystick-magic")
            with self.assertRaises(ActivityValidationError):
                ActivityRegistry([root], self.runtime).validate_package(package)

    def test_first_party_creative_activities_declare_intent_explicitly(self) -> None:
        painting = (PROJECT_ROOT / "activities/painting/activity.toml").read_text()
        writing = (PROJECT_ROOT / "activities/writing/activity.toml").read_text()
        self.assertIn('[input]\nprofile = "pointer"', painting)
        self.assertIn('[input]\nprofile = "text"', writing)

    @staticmethod
    def _package(root: Path, *, profile: str | None) -> Path:
        package = root / "sample"
        package.mkdir()
        (package / "main.py").write_text("print('ok')\n", encoding="utf-8")
        input_table = "" if profile is None else f'\n[input]\nprofile = "{profile}"\n'
        (package / "activity.toml").write_text(
            """[activity]
id = "org.greia.sample"
legacy_ids = []
title_key = "activity.sample.title"
version = "0.1.0"
icon = "palette"
languages = ["*"]

[education]
categories = ["sample"]
difficulty = 1
skills = [
  { id = "sample.skill", weight = 1 },
]
events = []

[runtime]
type = "python"
api_version = "0.1"
entrypoint = "main.py"
"""
            + input_table
            + """
[requirements]
required_capabilities = ["display"]
optional_capabilities = ["controller"]

[permissions]
requested = []

[storage]
schema_version = 1
""",
            encoding="utf-8",
        )
        return package


if __name__ == "__main__":
    unittest.main()
