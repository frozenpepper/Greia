from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_parent.production_api import ProductionParentApiApplication
from greia_platform.wifi import IwdWifiBackend, WifiError, WifiNetwork, WifiSecurity


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _UnavailableWifiBackend:
    def __init__(self) -> None:
        self.scan_calls = 0
        self.connect_calls = 0

    def available(self) -> bool:
        return False

    def management_available(self) -> bool:
        return False

    def scan(self):
        self.scan_calls += 1
        raise AssertionError("unavailable production Wi-Fi must not scan")

    def connect(self, network, passphrase=""):
        self.connect_calls += 1
        raise AssertionError("unavailable production Wi-Fi must not connect")


class _AvailableWifiBackend:
    def __init__(self, networks: tuple[WifiNetwork, ...]) -> None:
        self.networks = networks
        self.connected: list[WifiNetwork] = []

    def available(self) -> bool:
        return True

    def management_available(self) -> bool:
        return True

    def scan(self) -> tuple[WifiNetwork, ...]:
        return self.networks

    def connect(self, network: WifiNetwork, passphrase: str = ""):
        self.connected.append(network)
        return SimpleNamespace(network=network)


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
            self.assertEqual(app.api_meta_payload()["transport_security"], "self-signed-https")

    def test_unavailable_wifi_fails_closed_without_sample_data(self) -> None:
        backend = _UnavailableWifiBackend()
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary), wifi_backend=backend)
            self.assertEqual(app.wifi_payload(), {"available": False, "connected_ssid": "", "networks": []})
            self.assertEqual(backend.scan_calls, 0)
            with self.assertRaisesRegex(WifiError, "unavailable"):
                app.connect_wifi("Made Up Network", "password123")
            self.assertEqual(backend.scan_calls, 0)
            self.assertEqual(backend.connect_calls, 0)

    def test_real_iwd_management_no_longer_requires_writable_state(self) -> None:
        """Joining a network must not depend on writing iwd's private state.

        The passphrase is handed to iwd over its own agent API and iwd
        persists the profile itself, so the unprivileged Parent process needs
        no write access to the root-owned iwd state directory. This gate used
        to withhold network management whenever that directory was not
        writable, which would now hide a capability that genuinely works.
        """

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "iwd"
            state_dir.mkdir()
            backend = IwdWifiBackend(state_dir=state_dir)
            app = self._app(root, wifi_backend=backend)
            with (
                mock.patch.object(backend, "available", return_value=True),
                mock.patch.object(
                    backend, "management_available", return_value=True
                ),
            ):
                self.assertTrue(app.index_payload()["capabilities"]["network.manage"])

    def test_real_iwd_management_withheld_without_an_agent_capability(self) -> None:
        """A backend that cannot serve an agent must not advertise joining.

        This is the check that replaced the writability gate: the real
        requirement is the ability to serve a D-Bus passphrase agent, which
        needs python3-dbus with a main loop and PyGObject. An image missing
        those can list networks but must not claim it can join them.
        """

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "iwd"
            state_dir.mkdir()
            backend = IwdWifiBackend(state_dir=state_dir)
            app = self._app(root, wifi_backend=backend)
            with (
                mock.patch.object(backend, "available", return_value=True),
                mock.patch.object(
                    backend, "management_available", return_value=False
                ),
            ):
                self.assertFalse(
                    app.index_payload()["capabilities"]["network.manage"]
                )
                self.assertEqual(
                    app.wifi_payload(), {"available": False, "connected_ssid": "", "networks": []}
                )
                with self.assertRaisesRegex(WifiError, "unavailable"):
                    app.connect_wifi("Family Wi-Fi", "password123")

    def test_production_rejects_unscanned_network_without_synthesizing_it(self) -> None:
        real = WifiNetwork("Family Wi-Fi", WifiSecurity.OPEN, -42.0, "/net/connman/iwd/station/wlan0/family")
        backend = _AvailableWifiBackend((real,))
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary), wifi_backend=backend)
            with self.assertRaisesRegex(WifiError, "scan again"):
                app.connect_wifi("Invented Wi-Fi", "password123")
            self.assertEqual(backend.connected, [])

    def test_production_connects_the_exact_scanned_network(self) -> None:
        real = WifiNetwork("Family Wi-Fi", WifiSecurity.OPEN, -42.0, "/net/connman/iwd/station/wlan0/family")
        backend = _AvailableWifiBackend((real,))
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary), wifi_backend=backend)
            self.assertEqual(
                app.connect_wifi("Family Wi-Fi"),
                {"connected": True, "ssid": "Family Wi-Fi"},
            )
            self.assertEqual(backend.connected, [real])

    def test_ssh_capability_tracks_installed_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary), wifi_backend=_UnavailableWifiBackend())
            with mock.patch.object(app._parent_ssh_provider, "available", return_value=False):
                self.assertFalse(app.index_payload()["capabilities"]["maintenance.ssh"])
            with mock.patch.object(app._parent_ssh_provider, "available", return_value=True):
                self.assertTrue(app.index_payload()["capabilities"]["maintenance.ssh"])

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
