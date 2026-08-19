from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.ssh_maintenance import (
    MockSshMaintenanceProvider,
    SshMaintenanceService,
    SshStatus,
    SystemSshMaintenanceProvider,
)


class SshMaintenanceTests(unittest.TestCase):
    def test_status_public_dict_and_connection_string(self) -> None:
        status = SshStatus(
            active=True,
            enabled=True,
            port=22,
            username="greia",
            host_ip="192.168.1.100",
        )
        data = status.public_dict()
        self.assertTrue(data["active"])
        self.assertTrue(data["enabled"])
        self.assertEqual(data["port"], 22)
        self.assertEqual(data["username"], "greia")
        self.assertEqual(data["host_ip"], "192.168.1.100")
        self.assertEqual(data["connection_string"], "ssh greia@192.168.1.100")

    def test_mock_provider_lifecycle_and_toggle(self) -> None:
        provider = MockSshMaintenanceProvider(active=False, enabled=False, host_ip="10.0.0.5")
        service = SshMaintenanceService(provider)

        initial = service.get_status()
        self.assertFalse(initial.active)
        self.assertFalse(initial.enabled)

        # Toggle -> Enabled
        toggled = service.toggle()
        self.assertTrue(toggled.active)
        self.assertTrue(toggled.enabled)

        # Toggle again -> Disabled
        toggled_off = service.toggle()
        self.assertFalse(toggled_off.active)
        self.assertFalse(toggled_off.enabled)

        # Enable with key
        enabled = service.enable("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 parent@laptop")
        self.assertTrue(enabled.active)

        # Disable
        disabled = service.disable()
        self.assertFalse(disabled.active)

    def test_system_provider_handles_missing_script_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_script = Path(temporary) / "nonexistent-enable-ssh"
            provider = SystemSshMaintenanceProvider(
                enable_script=fake_script,
                username="greia",
                port=22,
            )
            # Must not crash when querying status on development/host system
            status = provider.status()
            self.assertIsInstance(status, SshStatus)
            self.assertEqual(status.username, "greia")
            self.assertEqual(status.port, 22)


if __name__ == "__main__":
    unittest.main()
