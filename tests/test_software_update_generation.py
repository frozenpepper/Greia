from __future__ import annotations

import shutil
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_index import build_index
from greia_platform.software_update_generation import (
    ApplicationGenerationBuilder,
    GenerationLayout,
    SoftwareUpdateGenerationError,
)
from greia_platform.software_update_package import (
    ActivityPackageInput,
    ActivityPackageSource,
    ActivityUpdateScope,
    PYTHON_RUNTIME_ALLOWLIST,
    PYTHON_SOURCE_ROOTS,
    SoftwareUpdateType,
    build_software_update_package,
    inspect_software_update_package,
)
from greia_platform.software_update_jobs import SoftwareUpdateJobStore
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = (
    PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/software-update-bootstrap.py"
)
BOOTSTRAP_SPEC = importlib.util.spec_from_file_location(
    "greia_software_update_generation_bootstrap_test", BOOTSTRAP_PATH
)
assert BOOTSTRAP_SPEC is not None and BOOTSTRAP_SPEC.loader is not None
bootstrap = importlib.util.module_from_spec(BOOTSTRAP_SPEC)
sys.modules[BOOTSTRAP_SPEC.name] = bootstrap
BOOTSTRAP_SPEC.loader.exec_module(bootstrap)
ACTIVITY_IDS = {"org.greia.painting", "org.greia.writing"}


def _copy_python_snapshot(source: Path, destination: Path) -> None:
    for relative in PYTHON_SOURCE_ROOTS:
        package_name = relative.rstrip("/").split("/")[-1]
        shutil.copytree(source / relative, destination / "src" / package_name)
    for relative in PYTHON_RUNTIME_ALLOWLIST | {
        "runtime/parent-app-client.toml",
        "runtime/parent-app-client.manifest.json",
    }:
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, output)


def _activity_archive(source: Path, destination: Path, version: str) -> Path:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            payload = path.read_bytes()
            if relative == "activity.toml":
                text = payload.decode("utf-8").replace(
                    'version = "0.1.0"', f'version = "{version}"', 1
                )
                payload = text.encode("utf-8")
            archive.writestr(relative, payload)
    return destination


class SoftwareUpdateGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="greia-app-generation-")
        self.root = Path(self.temporary.name)
        self.generations = self.root / "opt" / "greia-software" / "generations"
        self.generations.mkdir(parents=True)
        self.base = self.generations / "base"
        self.base.mkdir()
        self.application_root = self.root / "opt" / "greia-os"
        self.application_root.symlink_to(
            Path("greia-software/generations/base"), target_is_directory=True
        )
        _copy_python_snapshot(PROJECT_ROOT, self.base)
        activities = self.base / "activities"
        activities.mkdir()
        for folder in ("painting", "writing"):
            shutil.copytree(PROJECT_ROOT / "activities" / folder, activities / folder)
        (self.base / "assets").mkdir()
        (self.base / "assets" / "generation-sentinel.bin").write_bytes(b"unchanged asset")
        runtime = RuntimeCatalogue.load(self.base / "runtime" / "child-runtime.toml")
        registrations = ActivityRegistry(
            (
                ActivitySource(
                    activities,
                    PackageTrust.BUILT_IN,
                    "greia-system",
                ),
            ),
            runtime,
        ).discover_registrations()
        build_index(
            registrations,
            source=ActivitySource(activities, PackageTrust.BUILT_IN, "greia-system"),
            runtime=runtime,
        ).write_file(self.base / "activity-index-v1.json")
        self.profile_data = self.root / "var/lib/greia-profiles/data/profile/storage"
        self.profile_data.mkdir(parents=True)
        (self.profile_data / "saved.txt").write_text("keep", encoding="utf-8")
        self.package_state = self.root / "var/lib/greia-os/activity-packages"
        self.layout = GenerationLayout(
            application_root=self.application_root,
            generation_root=self.generations,
            activity_package_state=self.package_state,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _changed_python_source(self) -> Path:
        root = self.root / "python-update-source"
        _copy_python_snapshot(PROJECT_ROOT, root)
        changed = root / "src/greia_platform/software_update_apply.py"
        changed.write_text(
            changed.read_text(encoding="utf-8") + "\n# generation test change\n",
            encoding="utf-8",
        )
        return root

    def _updated_activity(self, folder: str, version: str = "0.1.1") -> Path:
        return _activity_archive(
            PROJECT_ROOT / "activities" / folder,
            self.root / f"{folder}-{version}.greiaactivity",
            version,
        )

    def test_python_platform_switch_stages_changed_code_and_hardlinks_unchanged_data(self) -> None:
        package = self.root / "python.greia_update"
        build_software_update_package(
            package,
            version="1.1.0",
            release_id="greia-python-1.1.0",
            python_source_root=self._changed_python_source(),
        )
        inspected = inspect_software_update_package(package)
        self.assertEqual(inspected.manifest.type, SoftwareUpdateType.PYTHON_PLATFORM)
        old_source = self.base / "src/greia_platform/software_update_apply.py"
        old_launcher = self.base / "src/greia_launcher/main.py"
        old_asset = self.base / "assets/generation-sentinel.bin"
        old_pin = self.base / "runtime/parent-app-client.toml"
        staged = ApplicationGenerationBuilder(self.layout).stage(
            package, inspected, job_id="a" * 32
        )
        candidate = staged.generation_path
        self.assertNotEqual(
            old_source.stat().st_ino,
            (candidate / "src/greia_platform/software_update_apply.py").stat().st_ino,
        )
        for relative in (
            "src/greia_launcher/main.py",
            "assets/generation-sentinel.bin",
            "runtime/parent-app-client.toml",
            "runtime/parent-app-client.manifest.json",
            "activities/painting/assets/icon.png",
            "activities/writing/assets/icon.png",
        ):
            self.assertEqual(
                (self.base / relative).stat().st_ino,
                (candidate / relative).stat().st_ino,
                relative,
            )
        self.assertEqual(old_launcher.stat().st_size, (candidate / "src/greia_launcher/main.py").stat().st_size)
        self.assertEqual(old_asset.read_bytes(), (candidate / "assets/generation-sentinel.bin").read_bytes())
        self.assertEqual(old_pin.read_bytes(), (candidate / "runtime/parent-app-client.toml").read_bytes())
        self.assertEqual("keep", (self.profile_data / "saved.txt").read_text("utf-8"))

    def test_builtin_one_update_preserves_unlisted_activities_and_reuses_assets(self) -> None:
        painting = self._updated_activity("painting")
        package = self.root / "activities.greia_update"
        build_software_update_package(
            package,
            version="1.2.0",
            release_id="greia-builtins-1.2.0",
            activity_packages=(ActivityPackageInput("org.greia.painting", painting),),
            activity_scope=ActivityUpdateScope.ONE,
            activity_source=ActivityPackageSource.BUILT_IN,
        )
        inspected = inspect_software_update_package(package)
        self.assertEqual(inspected.manifest.type, SoftwareUpdateType.ACTIVITIES)
        staged = ApplicationGenerationBuilder(self.layout).stage(
            package, inspected, job_id="b" * 32
        )
        candidate = staged.generation_path
        self.assertTrue((candidate / "activities/writing/activity.toml").is_file())
        self.assertIn('version = "0.1.1"', (candidate / "activities/painting/activity.toml").read_text("utf-8"))
        self.assertEqual(
            (self.base / "activities/painting/assets/icon.png").stat().st_ino,
            (candidate / "activities/painting/assets/icon.png").stat().st_ino,
        )
        self.assertEqual(
            (self.base / "activities/writing/assets/icon.png").stat().st_ino,
            (candidate / "activities/writing/assets/icon.png").stat().st_ino,
        )
        self.assertTrue((candidate / "activity-index-v1.json").is_file())

    def test_combined_all_updates_one_application_generation(self) -> None:
        packages = tuple(
            ActivityPackageInput(
                activity_id,
                self._updated_activity(folder),
            )
            for activity_id, folder in (
                ("org.greia.painting", "painting"),
                ("org.greia.writing", "writing"),
            )
        )
        package = self.root / "combined.greia_update"
        build_software_update_package(
            package,
            version="1.3.0",
            release_id="greia-combined-1.3.0",
            python_source_root=self._changed_python_source(),
            activity_packages=packages,
            activity_scope=ActivityUpdateScope.ALL,
            activity_source=ActivityPackageSource.BUILT_IN,
            approved_activity_ids=ACTIVITY_IDS,
        )
        inspected = inspect_software_update_package(package)
        self.assertEqual(inspected.manifest.type, SoftwareUpdateType.COMBINED)
        staged = ApplicationGenerationBuilder(self.layout).stage(
            package, inspected, job_id="c" * 32
        )
        self.assertIn(
            'version = "0.1.1"',
            (staged.generation_path / "activities/painting/activity.toml").read_text("utf-8"),
        )
        self.assertIn(
            'version = "0.1.1"',
            (staged.generation_path / "activities/writing/activity.toml").read_text("utf-8"),
        )
        self.assertTrue((staged.generation_path / "activity-index-v1.json").is_file())

    def test_all_scope_must_match_the_installed_builtin_inventory(self) -> None:
        package = self.root / "incomplete-all.greia_update"
        build_software_update_package(
            package,
            version="1.3.0",
            release_id="greia-bad-all-1.3.0",
            activity_packages=(
                ActivityPackageInput(
                    "org.greia.painting", self._updated_activity("painting")
                ),
            ),
            activity_scope=ActivityUpdateScope.ALL,
            activity_source=ActivityPackageSource.BUILT_IN,
            approved_activity_ids=frozenset({"org.greia.painting"}),
        )
        with self.assertRaisesRegex(SoftwareUpdateGenerationError, "complete installed built-in"):
            ApplicationGenerationBuilder(self.layout).stage(
                package, job_id="d" * 32
            )
        self.assertFalse((self.generations / ("app-" + "d" * 32)).exists())

    def test_durable_job_runs_real_prepare_and_commits_after_mock_health(self) -> None:
        state = self.root / "var/lib/greia-os/software-updates"
        state.mkdir(parents=True)
        package = state / "staging.greia_update"
        build_software_update_package(
            package,
            version="1.4.0",
            release_id="greia-python-1.4.0",
            python_source_root=PROJECT_ROOT,
        )
        store = SoftwareUpdateJobStore(state)
        accepted = store.accept_received(package, package.stat().st_size)
        job_id = str(accepted["job_id"])

        etc = self.root / "etc/greia-os"
        marker = etc / "software-update-bootstrap.json"
        marker.parent.mkdir(parents=True)
        marker.write_text('{"schema_version":1}\n', encoding="utf-8")
        helper = self.root / "usr/local/lib/greia-os/software-update-bootstrap.py"
        helper.parent.mkdir(parents=True)
        helper.write_text("#!/usr/bin/python3\n", encoding="utf-8")
        helper.chmod(0o755)
        root_uuid = etc / "root-filesystem-uuid"
        root_uuid.write_text("44444444-4444-4444-8444-444444444444\n", encoding="ascii")

        active_profile = self.root / "run/greia-os/active-profile.json"
        active_profile.parent.mkdir(parents=True)
        active_profile.write_text(
            '{"schema":1,"state":"profile_picker_idle"}\n', encoding="utf-8"
        )
        runtime = self.root / "run/greia-update-authority"
        runtime.mkdir(parents=True)
        boot_spool = active_profile.parent / "boot-markers.log"
        paths = bootstrap.BootstrapPaths(
            marker=marker,
            helper=helper,
            application_root=self.application_root,
            generation_root=self.generations,
            software_update_root=state,
            candidate=store.candidate_path,
            job=store.job_path,
            job_lock=store.lock_path,
            pending=store.pending_path,
            journal=self.root / "var/lib/greia-os/apply-journal.json",
            active_profile=active_profile,
            active_profile_lock=runtime / "profile-session.lock",
            restart_fence=runtime / "restart-pending.json",
            boot_marker_spool=boot_spool,
            builtin_index=self.root / "usr/share/greia/activity-index-v1.json",
            root_filesystem_uuid=root_uuid,
        )
        paths.builtin_index.parent.mkdir(parents=True)
        paths.builtin_index.symlink_to(
            str(self.application_root / "activity-index-v1.json")
        )

        def systemctl(*arguments: str) -> None:
            if arguments[:2] == ("start", "greia-launcher.service"):
                with boot_spool.open("a", encoding="utf-8") as output:
                    output.write(
                        "GREIA_BOOT event=launcher_interactive_ready "
                        f"monotonic_ns={bootstrap.time.monotonic_ns() + 100}\n"
                    )

        environment = {
            "GREIA_OS_ROOT": str(self.application_root),
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(self.package_state),
        }
        with mock.patch.dict(os.environ, environment), mock.patch.object(
            bootstrap, "_run_systemctl", side_effect=systemctl
        ), mock.patch.object(
            bootstrap, "_wait_for_parent_ready", return_value=True
        ), mock.patch(
            "greia_platform.software_update_apply.GenerationLayout",
            return_value=self.layout,
        ):
            self.assertEqual(bootstrap.apply_pending(paths), 0)

        self.assertEqual(bootstrap.current_generation_id(paths), f"app-{job_id}")
        self.assertEqual(store.snapshot()["state"], "applied")
        self.assertFalse(store.pending_path.exists())
        self.assertEqual((self.profile_data / "saved.txt").read_text("utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
