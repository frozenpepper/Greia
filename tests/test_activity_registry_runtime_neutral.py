from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeManager,
    RuntimeValidationError,
)
from greia_platform.activities import (
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
)
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"


class RuntimeNeutralActivityRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = RuntimeCatalogue.load(RUNTIME_PATH)

    def test_duplicate_canonical_activity_id_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activities = Path(temporary) / "activities"
            activities.mkdir()
            for name in ("first", "second"):
                copied = activities / name
                shutil.copytree(PROJECT_ROOT / "activities" / "shape_garden", copied)
                manifest = copied / "activity.toml"
                manifest.write_text(
                    manifest.read_text(encoding="utf-8").replace(
                        'legacy_ids = ["shape_garden"]\n', ""
                    ),
                    encoding="utf-8",
                )
            registry = ActivityRegistry(
                [ActivitySource(activities, PackageTrust.DEVELOPER_UNSIGNED, "external")],
                self.runtime,
            )
            with self.assertRaisesRegex(ActivityValidationError, "identity/alias collision"):
                registry.discover()

    def test_unconfigured_source_cannot_replace_registry_origin(self) -> None:
        source = ActivitySource(
            PROJECT_ROOT / "activities",
            PackageTrust.BUILT_IN,
            "greia-system",
        )
        registry = ActivityRegistry([source], self.runtime)
        fake_source = ActivitySource(
            PROJECT_ROOT / "activities",
            PackageTrust.DEVELOPER_UNSIGNED,
            "fake-source",
        )
        with self.assertRaisesRegex(ActivityValidationError, "not configured"):
            registry.validate_registration(
                PROJECT_ROOT / "activities" / "shape_garden",
                fake_source,
            )

    def test_python_package_rule_belongs_to_python_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activities = Path(temporary) / "activities"
            activities.mkdir()
            copied = activities / "shape"
            shutil.copytree(PROJECT_ROOT / "activities" / "shape_garden", copied)
            (copied / "requirements.txt").write_text("example==1\n", encoding="utf-8")
            registry = ActivityRegistry(
                [ActivitySource(activities, PackageTrust.BUILT_IN, "test-system")],
                self.runtime,
            )
            manifest = registry.discover()[0]
            manager = RuntimeManager(
                [
                    PythonRuntimeAdapter(
                        policy=PythonRuntimePolicy.load(RUNTIME_PATH)
                    )
                ],
                DeviceCapabilityService.static(
                    set(self.runtime.allowed_capabilities),
                    source_id="registry-runtime-test",
                ),
            )
            with self.assertRaisesRegex(RuntimeValidationError, "Python package file"):
                manager.validate_package(manifest)


if __name__ == "__main__":
    unittest.main()
