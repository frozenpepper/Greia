from __future__ import annotations

import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_parent.protocol import RESOURCES
from greia_parent.update_api import UpdateParentApiApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ParentSystemUpdateTests(unittest.TestCase):
    def _app(self, root: Path) -> UpdateParentApiApplication:
        return UpdateParentApiApplication(
            PROJECT_ROOT,
            root / "state",
            hardware_settings_dir=root / "hardware-settings",
            hardware_status_path=root / "hardware-status.json",
            profiles_dir=root / "profiles",
            active_profile_status_path=root / "active-profile.json",
        )

    def _environment(self, root: Path, *, update_upload: str) -> dict[str, str]:
        return {
            "GREIA_PARENT_SYSTEM_UPDATE_UPLOAD": update_upload,
            "GREIA_PARENT_ACTIVITY_INSTALL": "0",
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(root / "activity-packages"),
        }

    def test_protocol_advertises_semantic_update_resources(self) -> None:
        by_name = {resource.name: resource for resource in RESOURCES}
        self.assertEqual(by_name["system_update"].path, "/api/v1/system/update")
        self.assertEqual(by_name["system_update"].methods, ("GET",))
        self.assertEqual(
            by_name["system_update_bundle"].path,
            "/api/v1/system/update/bundle",
        )
        self.assertEqual(by_name["system_update_bundle"].methods, ("POST",))

    def test_normal_parent_api_reports_update_upload_and_activation_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, self._environment(root, update_upload="0"), clear=False):
                app = self._app(root)
            index = app.index_payload()
            capabilities = index["capabilities"]
            self.assertTrue(capabilities["system.update.read"])
            self.assertFalse(capabilities["system.update.upload"])
            self.assertFalse(capabilities["system.update.activate"])
            status = app.system_update_payload()
            self.assertEqual(status["state"], "idle")
            self.assertFalse(status["upload_available"])
            self.assertFalse(status["activation_available"])

    def test_explicit_developer_upload_does_not_enable_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, self._environment(root, update_upload="1"), clear=False):
                app = self._app(root)
            index = app.index_payload()
            capabilities = index["capabilities"]
            self.assertTrue(capabilities["system.update.upload"])
            self.assertFalse(capabilities["system.update.activate"])
            status = app.system_update_payload()
            self.assertTrue(status["upload_available"])
            self.assertFalse(status["activation_available"])

    def test_current_legacy_release_profile_is_single_root_and_has_no_update_runtime(self) -> None:
        profile_path = PROJECT_ROOT / "build" / "profiles" / "legacy-x86-i686.toml"
        profile = tomllib.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(profile["image"]["layout"], "bios-single-ext4")
        self.assertNotIn("system-update", profile["packages"]["target_sets"])
        self.assertNotIn("system-update", profile["packages"]["installer_sets"])

    def test_installed_parent_service_uses_update_aware_unprivileged_composition(self) -> None:
        service = (
            PROJECT_ROOT
            / "build"
            / "overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-parent.service"
        ).read_text(encoding="utf-8")
        self.assertIn("-m greia_parent.production_api", service)
        self.assertIn("User=greiapanel", service)
        self.assertIn("NoNewPrivileges=yes", service)
        self.assertIn("ProtectSystem=strict", service)
        self.assertIn("CapabilityBoundingSet=\n", service)


if __name__ == "__main__":
    unittest.main()
