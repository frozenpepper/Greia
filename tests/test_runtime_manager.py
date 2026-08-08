from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeCommand,
    RuntimeCompatibilityError,
    RuntimeInvocation,
    RuntimeLifecycleSupport,
    RuntimeManager,
    RuntimeUnavailableError,
    RuntimeValidationError,
)
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"


class _CommandAdapter:
    runtime_type = "python"
    lifecycle_support = RuntimeLifecycleSupport()
    required_device_capabilities = frozenset()

    def __init__(self, command: RuntimeCommand):
        self.command = command

    def validate_package(self, manifest) -> None:
        return None

    def command_for(self, manifest) -> RuntimeCommand:
        return self.command


class RuntimeManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalogue = RuntimeCatalogue.load(RUNTIME_PATH)
        self.python_policy = PythonRuntimePolicy.load(RUNTIME_PATH)

    def _built_in_manifests(self):
        return ActivityRegistry(
            [ActivitySource(PROJECT_ROOT / "activities", PackageTrust.BUILT_IN, "greia-system")],
            self.catalogue,
        ).discover()

    def _manager(self, capabilities: set[str]) -> RuntimeManager:
        return RuntimeManager(
            [PythonRuntimeAdapter(policy=self.python_policy)],
            DeviceCapabilityService.static(capabilities, source_id="runtime-manager-test"),
        )

    def test_registry_is_runtime_neutral_but_manager_fails_closed_for_unknown_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activities = Path(temporary) / "activities"
            activities.mkdir()
            copied = activities / "webish"
            shutil.copytree(PROJECT_ROOT / "activities" / "shape_garden", copied)
            manifest_path = copied / "activity.toml"
            text = manifest_path.read_text(encoding="utf-8")
            text = text.replace('legacy_ids = ["shape_garden"]\n', "")
            text = text.replace('type = "python"', 'type = "web"')
            text = text.replace('entrypoint = "main.py"', 'entrypoint = "index.html"')
            manifest_path.write_text(text, encoding="utf-8")
            (copied / "index.html").write_text("<!doctype html>", encoding="utf-8")
            manifest = ActivityRegistry(
                [ActivitySource(activities, PackageTrust.DEVELOPER_UNSIGNED, "external-test")],
                self.catalogue,
            ).discover()[0]

            self.assertEqual(manifest.runtime_type, "web")
            with self.assertRaises(RuntimeUnavailableError):
                self._manager({"display", "pointer"}).prepare_launch(manifest)

    def test_python_adapter_owns_forbidden_import_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activities = Path(temporary) / "activities"
            activities.mkdir()
            copied = activities / "shape"
            shutil.copytree(PROJECT_ROOT / "activities" / "shape_garden", copied)
            (copied / "main.py").write_text("import subprocess\n", encoding="utf-8")
            manifest = ActivityRegistry(
                [ActivitySource(activities, PackageTrust.BUILT_IN, "greia-system-test")],
                self.catalogue,
            ).discover()[0]

            with self.assertRaisesRegex(RuntimeValidationError, "forbidden Python import"):
                self._manager({"display", "pointer"}).validate_package(manifest)

    def test_python_adapter_rejects_dynamic_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activities = Path(temporary) / "activities"
            activities.mkdir()
            copied = activities / "shape"
            shutil.copytree(PROJECT_ROOT / "activities" / "shape_garden", copied)
            (copied / "main.py").write_text('__import__("math")\n', encoding="utf-8")
            manifest = ActivityRegistry(
                [ActivitySource(activities, PackageTrust.BUILT_IN, "greia-system-test")],
                self.catalogue,
            ).discover()[0]

            with self.assertRaisesRegex(RuntimeValidationError, "dynamic Python imports"):
                self._manager({"display", "pointer"}).validate_package(manifest)

    def test_missing_required_device_capability_blocks_runtime_launch(self) -> None:
        shape = next(
            item for item in self._built_in_manifests()
            if item.activity_id == "org.greia.shape-garden"
        )
        with self.assertRaisesRegex(RuntimeCompatibilityError, "display"):
            self._manager({"pointer"}).prepare_launch(shape)

    def test_missing_optional_device_capability_does_not_block_runtime_launch(self) -> None:
        settings = next(
            item for item in self._built_in_manifests()
            if item.activity_id == "org.greia.workshop-settings"
        )
        preparation = self._manager({"display", "pointer"}).prepare_launch(settings)

        self.assertTrue(preparation.compatibility.compatible)
        self.assertNotIn(
            "removable_media", preparation.compatibility.effective_optional_capabilities
        )

    def test_launch_preparation_rejects_stale_device_snapshot_token(self) -> None:
        shape = next(
            item for item in self._built_in_manifests()
            if item.activity_id == "org.greia.shape-garden"
        )
        stale_token = DeviceCapabilityService.static(
            {"display", "pointer", "audio.basic"},
            source_id="runtime-manager-test",
        ).snapshot().token
        manager = self._manager({"display", "pointer"})

        with self.assertRaisesRegex(RuntimeCompatibilityError, "snapshot changed"):
            manager.prepare_launch(shape, expected_device_snapshot_token=stale_token)

    def test_python_runtime_owns_python_specific_environment(self) -> None:
        shape = next(
            item for item in self._built_in_manifests()
            if item.activity_id == "org.greia.shape-garden"
        )
        preparation = self._manager({"display", "pointer"}).prepare_launch(shape)
        self.assertEqual(
            dict(preparation.command.environment),
            {"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_runtime_environment_cannot_override_platform_authority(self) -> None:
        shape = next(
            item for item in self._built_in_manifests()
            if item.activity_id == "org.greia.shape-garden"
        )
        manager = RuntimeManager(
            [
                _CommandAdapter(
                    RuntimeCommand(
                        command=("runtime",),
                        cwd=shape.root,
                        environment=(("GREIA_PROFILE_ID", "forged"),),
                    )
                )
            ],
            DeviceCapabilityService.static(
                {"display", "pointer"}, source_id="runtime-manager-test"
            ),
        )
        with self.assertRaisesRegex(RuntimeValidationError, "platform-owned"):
            manager.prepare_launch(shape)

    def test_runtime_working_directory_cannot_escape_package(self) -> None:
        shape = next(
            item for item in self._built_in_manifests()
            if item.activity_id == "org.greia.shape-garden"
        )
        manager = RuntimeManager(
            [
                _CommandAdapter(
                    RuntimeCommand(command=("runtime",), cwd=PROJECT_ROOT)
                )
            ],
            DeviceCapabilityService.static(
                {"display", "pointer"}, source_id="runtime-manager-test"
            ),
        )
        with self.assertRaisesRegex(RuntimeValidationError, "escapes Activity package"):
            manager.prepare_launch(shape)

    def test_runtime_manager_delegates_launch_and_exit_collection_to_adapter(self) -> None:
        shape = next(
            item for item in self._built_in_manifests()
            if item.activity_id == "org.greia.shape-garden"
        )
        process = mock.Mock()
        process.poll.return_value = 7
        factory = mock.Mock(return_value=process)
        manager = RuntimeManager(
            [
                PythonRuntimeAdapter(
                    Path("/usr/bin/python3"),
                    policy=self.python_policy,
                    process_factory=factory,
                )
            ],
            DeviceCapabilityService.static(
                {"display", "pointer"}, source_id="runtime-manager-test"
            ),
        )
        preparation = manager.prepare_launch(shape)
        invocation = RuntimeInvocation(
            command=preparation.command.command,
            cwd=preparation.command.cwd,
            environment=preparation.command.environment,
        )
        launched = manager.launch(preparation, invocation)
        runtime_exit = manager.collect_exit(preparation, launched)

        self.assertIs(launched, process)
        self.assertEqual(runtime_exit.return_code, 7)
        self.assertEqual(runtime_exit.kind.value, "crash")
        factory.assert_called_once()

    def test_activity_environment_cannot_forge_runtime_device_truth(self) -> None:
        shape = next(
            item for item in self._built_in_manifests()
            if item.activity_id == "org.greia.shape-garden"
        )
        manager = self._manager({"pointer"})
        with mock.patch.dict(
            os.environ,
            {"GREIA_ACTIVITY_CAPABILITIES": "display,pointer,audio.basic"},
            clear=False,
        ):
            with self.assertRaises(RuntimeCompatibilityError):
                manager.prepare_launch(shape)


if __name__ == "__main__":
    unittest.main()
