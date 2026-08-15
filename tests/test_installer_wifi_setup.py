from __future__ import annotations

import time
import unittest

from greia_installer.wifi import IwdNetworkProfile, WifiConnection, WifiNetwork, WifiSecurity
from greia_installer.wifi_setup import WifiSetupController, WifiSetupPhase


class FakeBackend:
    def __init__(self) -> None:
        self.networks = (
            WifiNetwork("Home", WifiSecurity.PERSONAL, -40.0, "/net/connman/iwd/demo/home"),
            WifiNetwork("Guest", WifiSecurity.OPEN, -60.0, "/net/connman/iwd/demo/guest"),
            WifiNetwork("School", WifiSecurity.ENTERPRISE, -65.0, "/net/connman/iwd/demo/school"),
        )
        self.available_value = True
        self.calls = 0

    def available(self) -> bool:
        return self.available_value

    def scan(self) -> tuple[WifiNetwork, ...]:
        return self.networks

    def connect(self, network: WifiNetwork, passphrase: str = "") -> WifiConnection:
        self.calls += 1
        return WifiConnection(network, IwdNetworkProfile.for_network(network, passphrase))


def finish(controller: WifiSetupController) -> None:
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        controller.drain()
        if not controller.busy:
            controller.drain()
            return
        time.sleep(0.005)
    raise AssertionError("Wi-Fi worker did not finish")


class InstallerWifiSetupTests(unittest.TestCase):
    def test_scan_and_personal_connection(self) -> None:
        backend = FakeBackend()
        controller = WifiSetupController(backend)
        controller.begin()
        finish(controller)
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.READY)
        controller.append_password("correct-horse")
        controller.connect()
        finish(controller)
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.CONNECTED)
        self.assertEqual(controller.snapshot.passphrase, "")
        self.assertIsNotNone(controller.profile)

    def test_enterprise_is_deferred_without_backend_connect(self) -> None:
        backend = FakeBackend()
        controller = WifiSetupController(backend)
        controller.begin()
        finish(controller)
        controller.select(2)
        controller.connect()
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.ERROR)
        self.assertEqual(backend.calls, 0)

    def test_no_adapter_is_nonfatal(self) -> None:
        backend = FakeBackend()
        backend.available_value = False
        controller = WifiSetupController(backend)
        controller.begin()
        finish(controller)
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.UNAVAILABLE)
        self.assertIsNone(controller.profile)

    def test_password_is_hard_bounded(self) -> None:
        controller = WifiSetupController(FakeBackend())
        controller.begin()
        finish(controller)
        controller.append_password("x" * 100)
        self.assertEqual(len(controller.snapshot.passphrase), 63)


if __name__ == "__main__":
    unittest.main()
