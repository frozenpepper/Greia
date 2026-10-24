from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_index import build_index
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.software_update_package import inspect_software_update_package


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "greia_software_update.py"
spec = importlib.util.spec_from_file_location("greia_software_update_tool", TOOL_PATH)
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)


class GreiaSoftwareUpdateToolTests(unittest.TestCase):
    def test_all_current_activities_uses_source_registry_without_installed_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activities_root = root / "activities"
            activities_root.mkdir()
            shutil.copytree(PROJECT_ROOT / "activities" / "writing", activities_root / "writing")
            output = root / "current.greia_update"
            with contextlib.redirect_stdout(io.StringIO()):
                result = tool.main(
                    [
                        "build-activities",
                        "--version", "1.4.0",
                        "--release-id", "greia-app-1.4.0",
                        "--scope", "all",
                        "--source", "built_in",
                        "--all-current-activities",
                        "--activities-root", str(activities_root),
                        "--runtime", str(PROJECT_ROOT / "runtime" / "child-runtime.toml"),
                        "--output", str(output),
                    ]
                )
            self.assertEqual(result, 0)
            inspected = inspect_software_update_package(output)
            self.assertEqual(inspected.manifest.activity_scope.value, "all")
            self.assertEqual(
                [item.activity_id for item in inspected.manifest.activity_items],
                ["org.greia.writing"],
            )

    def test_all_build_uses_validated_installed_index_and_exact_candidate_snapshot(self) -> None:
        runtime_source = PROJECT_ROOT / "runtime" / "child-runtime.toml"
        activity_source = PROJECT_ROOT / "activities" / "writing"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / "rootfs"
            installed_activities = installed / "opt" / "greia-os" / "activities"
            installed_runtime = installed / "opt" / "greia-os" / "runtime" / "child-runtime.toml"
            installed_index = installed / "usr" / "share" / "greia" / "activity-index-v1.json"
            installed_activities.mkdir(parents=True)
            installed_runtime.parent.mkdir(parents=True)
            installed_index.parent.mkdir(parents=True)
            shutil.copytree(activity_source, installed_activities / "writing")
            shutil.copyfile(runtime_source, installed_runtime)

            runtime = RuntimeCatalogue.load(installed_runtime)
            source = ActivitySource(installed_activities, PackageTrust.BUILT_IN, tool.BUILT_IN_SOURCE_ID)
            registrations = ActivityRegistry((source,), runtime).discover_registrations()
            build_index(registrations, source=source, runtime=runtime).write_file(installed_index)

            candidate_root = root / "candidate-activities"
            candidate_root.mkdir()
            shutil.copytree(activity_source, candidate_root / "writing")
            output = root / "all.greia_update"
            with contextlib.redirect_stdout(io.StringIO()):
                result = tool.main(
                    [
                        "build-activities",
                        "--version",
                        "1.4.0",
                        "--release-id",
                        "greia-app-1.4.0",
                        "--scope",
                        "all",
                        "--source",
                        "built_in",
                        "--all-from-installed-root",
                        str(installed),
                        "--activities-root",
                        str(candidate_root),
                        "--runtime",
                        str(runtime_source),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(result, 0)
            inspected = inspect_software_update_package(output)
            self.assertEqual(inspected.manifest.activity_scope.value, "all")
            self.assertEqual(inspected.manifest.activity_source.value, "built_in")
            self.assertEqual(
                [item.activity_id for item in inspected.manifest.activity_items],
                ["org.greia.writing"],
            )

    def test_all_build_refuses_arbitrary_ids_without_installed_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "all.greia_update"
            with contextlib.redirect_stderr(io.StringIO()):
                result = tool.main(
                    [
                        "build-activities",
                        "--version",
                        "1.4.0",
                        "--release-id",
                        "greia-app-1.4.0",
                        "--scope",
                        "all",
                        "--source",
                        "built_in",
                        "--activity",
                        "org.greia.writing=activities/writing",
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(result, 1)
            self.assertFalse(output.exists())

    def test_activity_source_walk_error_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "activity.greiaactivity"

            def fail_walk(_root, *, followlinks, onerror):
                onerror(PermissionError("traversal denied"))
                return iter(())

            with patch("greia_software_update_tool.os.walk", side_effect=fail_walk):
                with self.assertRaisesRegex(
                    tool.SoftwareUpdatePackageError,
                    "traverse Activity source tree",
                ):
                    tool._write_activity_archive(PROJECT_ROOT / "activities" / "writing", output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
