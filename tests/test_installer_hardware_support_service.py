from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InstallerHardwareSupportServiceTests(unittest.TestCase):
    def test_live_installer_explicitly_opts_into_frozen_hardware_support(self) -> None:
        service = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Environment=GREIA_HARDWARE_SUPPORT_POOL=/opt/greia-hardware-support",
            service,
        )
        self.assertIn(
            "Environment=GREIA_TARGET_IMAGE_PROFILE=/etc/greia-os/target-image-profile.json",
            service,
        )

    def test_service_does_not_grant_network_or_vendor_driver_install_commands(self) -> None:
        service = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text(encoding="utf-8")
        self.assertNotIn("apt-get", service)
        self.assertNotIn("curl", service)
        self.assertNotIn("wget", service)


if __name__ == "__main__":
    unittest.main()
