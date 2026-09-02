from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_parent.production_api import ProductionParentApiApplication
from greia_platform.wifi import IwdWifiBackend, WifiError


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _UnavailableWifiBackend:
    def __init__(self) -> None:
        self.scan_calls = 0
        self.connect_calls = 0

    def available(self) -> bool:
        return False

    def scan(self):
        self.scan_calls += 1
        raise AssertionError("unavailable production Wi-Fi must not scan")

    def connect(self, network, passphrase=""):
        self.connect_calls += 1
        raise AssertionError("unavailable production Wi-Fi must not connect")


class ParentProductionApiTests(unittest.TestCase):
    def _app(self, root: Path, *, wifi_backend=None) -> ProductionParentApiApplication:
        return ProductionParentApiApplication(
            PROJECT_ROOT,
            root / "parent-state",
            hardware_settings_dir=root / "hardware-settings",
            hardware_status_path=root / "hardware-status.json",
            profiles_dir=root / "profiles",
            active_profile_status_path=root / "active-profile.json",
            wifi_backend=wifi_backend,
        )

    def test_installed_composition_defaults_to_real_iwd_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary))
            self.assertIsInstance(app.wifi_backend, IwdWifiBackend)

    def test_unavailable_wifi_fails_closed_without_sample_data(self) -> None:
        backend = _UnavailableWifiBackend()
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary), wifi_backend=backend)
            self.assertEqual(app.wifi_payload(), {"available": False, "networks": []})
            self.assertEqual(backend.scan_calls, 0)
            with self.assertRaisesRegex(WifiError, "unavailable"):
                app.connect_wifi("Made Up Network", "password123")
            self.assertEqual(backend.scan_calls, 0)
            self.assertEqual(backend.connect_calls, 0)

    def test_capability_index_preserves_composed_features(self) -> None:
        backend = _UnavailableWifiBackend()
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary), wifi_backend=backend)
            capabilities = app.index_payload()["capabilities"]

        self.assertEqual(capabilities["activities.install"], app.activity_install_enabled)
        self.assertEqual(capabilities["activities.remove"], app.activity_remove_enabled)
        self.assertEqual(
            capabilities["system.update.upload"],
            app.system_update_upload_enabled,
        )
        self.assertFalse(capabilities["system.update.activate"])
        self.assertTrue(capabilities["settings.audio"])
        self.assertTrue(capabilities["settings.system_controls"])
        self.assertTrue(capabilities["profiles.presentation"])
        self.assertFalse(capabilities["network.manage"])


if __name__ == "__main__":
    unittest.main()
