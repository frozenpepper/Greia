from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from greia_launcher.supervisor import ActivitySupervisor
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.profiles import ProfileStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SupervisorTests(unittest.TestCase):
    def test_environment_drops_unapproved_values_and_scopes_home(self) -> None:
        runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        manifests = ActivityRegistry([PROJECT_ROOT / "activities"], runtime).discover()
        manifest = next(item for item in manifests if item.activity_id == "workshop_settings")
        with tempfile.TemporaryDirectory() as temporary:
            store = ProfileStore.load(
                PROJECT_ROOT / "runtime" / "profile-defaults.toml",
                Path(temporary) / "profiles",
            )
            profile = store.ensure_initialized()[0]
            context = store.context(profile.profile_id)
            old = os.environ.get("SECRET_SHOULD_NOT_LEAK")
            os.environ["SECRET_SHOULD_NOT_LEAK"] = "nope"
            try:
                environment = ActivitySupervisor._sanitized_environment(manifest, context)
            finally:
                if old is None:
                    del os.environ["SECRET_SHOULD_NOT_LEAK"]
                else:
                    os.environ["SECRET_SHOULD_NOT_LEAK"] = old
        self.assertNotIn("SECRET_SHOULD_NOT_LEAK", environment)
        self.assertEqual(environment["GREIA_ACTIVITY_ID"], "workshop_settings")
        self.assertEqual(environment["GREIA_PROFILE_ID"], profile.profile_id)
        self.assertEqual(environment["HOME"], environment["GREIA_ACTIVITY_DATA_DIR"])
        self.assertIn("profile.manage_own", environment["GREIA_ACTIVITY_CAPABILITIES"])
        self.assertNotIn("GREIA_PROFILES_DIR", environment)
        self.assertNotIn("GREIA_PROFILE_DATA_DIR", environment)
        self.assertEqual(
            environment["GREIA_AVATAR_REQUEST_PATH"],
            str(context.activity_data_dir("workshop_settings") / ".greia" / "requests" / "avatar.json"),
        )
        self.assertEqual(environment["PYTHONNOUSERSITE"], "1")

    def test_installed_activity_sandbox_hides_sibling_and_parent_state(self) -> None:
        runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        manifests = ActivityRegistry([PROJECT_ROOT / "activities"], runtime).discover()
        manifest = next(item for item in manifests if item.activity_id == "shape_garden")
        with tempfile.TemporaryDirectory() as temporary:
            store = ProfileStore.load(
                PROJECT_ROOT / "runtime" / "profile-defaults.toml",
                Path(temporary) / "profiles",
            )
            profile = store.ensure_initialized()[0]
            context = store.context(profile.profile_id)
            command = ActivitySupervisor._sandbox_command(
                Path("/usr/bin/bwrap"),
                Path("/usr/bin/python3"),
                manifest,
                context,
            )
            environment = ActivitySupervisor._sanitized_environment(
                manifest, context, sandboxed=True
            )

        self.assertIn("--unshare-user", command)
        self.assertIn("--disable-userns", command)
        self.assertIn("--unshare-pid", command)
        self.assertIn("--unshare-net", command)
        self.assertIn("--new-session", command)
        self.assertIn("--die-with-parent", command)
        self.assertIn("/var/lib/greia-profiles", command)
        self.assertIn("/var/lib/greia-os", command)
        self.assertIn("/run/greia-os", command)
        self.assertIn("/media/greia", command)
        self.assertEqual(environment["HOME"], "/run/greia-activity-data")
        self.assertEqual(environment["GREIA_ACTIVITY_DATA_DIR"], environment["HOME"])
        self.assertNotIn(str(context.root), environment.values())
        self.assertNotIn(str(context.root), command)
        self.assertIn(str(context.activity_data_dir("shape_garden")), command)
        self.assertNotIn(str(context.customization_dir), command)
        self.assertNotIn("GREIA_CUSTOMIZATION_DIR", environment)
        self.assertNotIn("GREIA_AVATAR_REQUEST_PATH", environment)

    def test_settings_sandbox_keeps_read_only_media_visible(self) -> None:
        runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        manifests = ActivityRegistry([PROJECT_ROOT / "activities"], runtime).discover()
        manifest = next(item for item in manifests if item.activity_id == "workshop_settings")
        with tempfile.TemporaryDirectory() as temporary:
            store = ProfileStore.load(
                PROJECT_ROOT / "runtime" / "profile-defaults.toml",
                Path(temporary) / "profiles",
            )
            profile = store.ensure_initialized()[0]
            context = store.context(profile.profile_id)
            command = ActivitySupervisor._sandbox_command(
                Path("/usr/bin/bwrap"), Path("/usr/bin/python3"), manifest, context
            )
        media_tmpfs_pair = ["--tmpfs", "/media/greia"]
        self.assertFalse(
            any(command[index:index + 2] == media_tmpfs_pair for index in range(len(command) - 1))
        )
        self.assertIn(str(context.activity_data_dir("workshop_settings")), command)
        self.assertIn(str(context.customization_dir), command)
        self.assertNotIn(str(context.root), command)

    def test_forged_environment_capabilities_cannot_expand_sandbox_authority(self) -> None:
        runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        manifests = ActivityRegistry([PROJECT_ROOT / "activities"], runtime).discover()
        manifest = next(item for item in manifests if item.activity_id == "shape_garden")
        with tempfile.TemporaryDirectory() as temporary:
            store = ProfileStore.load(
                PROJECT_ROOT / "runtime" / "profile-defaults.toml",
                Path(temporary) / "profiles",
            )
            profile = store.ensure_initialized()[0]
            context = store.context(profile.profile_id)
            with mock.patch.dict(
                os.environ,
                {"GREIA_ACTIVITY_CAPABILITIES": "customization.manage,removable_media.read"},
                clear=False,
            ):
                command = ActivitySupervisor._sandbox_command(
                    Path("/usr/bin/bwrap"), Path("/usr/bin/python3"), manifest, context
                )
        self.assertNotIn(str(context.customization_dir), command)
        self.assertTrue(
            any(
                command[index:index + 2] == ["--tmpfs", "/media/greia"]
                for index in range(len(command) - 1)
            )
        )

    def test_installed_runtime_fails_closed_when_bubblewrap_is_missing(self) -> None:
        runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        manifests = ActivityRegistry([PROJECT_ROOT / "activities"], runtime).discover()
        manifest = next(item for item in manifests if item.activity_id == "shape_garden")
        with tempfile.TemporaryDirectory() as temporary:
            store = ProfileStore.load(
                PROJECT_ROOT / "runtime" / "profile-defaults.toml",
                Path(temporary) / "profiles",
            )
            profile = store.ensure_initialized()[0]
            context = store.context(profile.profile_id)
            result = ActivitySupervisor(
                python_executable=Path(__import__("sys").executable),
                sandbox_executable=Path(temporary) / "missing-bwrap",
                require_sandbox=True,
            ).launch(manifest, context)
        self.assertEqual(result.return_code, 126)

    def test_developer_run_uses_current_interpreter(self) -> None:
        old_root = os.environ.get("GREIA_OS_ROOT")
        os.environ["GREIA_OS_ROOT"] = str(PROJECT_ROOT)
        try:
            resolved = ActivitySupervisor()._resolve_interpreter()
        finally:
            if old_root is None:
                del os.environ["GREIA_OS_ROOT"]
            else:
                os.environ["GREIA_OS_ROOT"] = old_root
        self.assertEqual(resolved.resolve(), Path(__import__("sys").executable).resolve())


if __name__ == "__main__":
    unittest.main()
