from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InstallerHardwareSupportServiceTests(unittest.TestCase):
    def test_root_transaction_service_explicitly_opts_into_frozen_hardware_support(self) -> None:
        # Step 8A.5 split: the unprivileged UI owns no pool/profile facts.
        # The root transaction service rematerializes them from its own
        # Greia-owned environment.
        service = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/systemd/system/greia-install-transaction.service"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Environment=GREIA_HARDWARE_SUPPORT_POOL=/opt/greia-hardware-support",
            service,
        )
        self.assertIn(
            "Environment=GREIA_TARGET_IMAGE_PROFILE=/etc/greia-os/target-image-profile.json",
            service,
        )
        ui = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text(encoding="utf-8")
        self.assertNotIn("GREIA_HARDWARE_SUPPORT_POOL", ui)

    def test_service_does_not_grant_network_or_vendor_driver_install_commands(self) -> None:
        for unit_name in (
            "greia-installer.service",
            "greia-install-transaction.service",
        ):
            with self.subTest(unit=unit_name):
                service = (
                    PROJECT_ROOT
                    / "build/installer-overlay/etc/systemd/system"
                    / unit_name
                ).read_text(encoding="utf-8")
                self.assertNotIn("apt-get", service)
                self.assertNotIn("curl", service)
                self.assertNotIn("wget", service)


if __name__ == "__main__":
    unittest.main()
