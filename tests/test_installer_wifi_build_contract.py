from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InstallerWifiBuildContractTests(unittest.TestCase):
    def test_installer_base_contains_required_wireless_stack(self) -> None:
        packages = {
            line.strip()
            for line in (PROJECT_ROOT / "build/package-sets/installer-base.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertTrue(
            {"iwd", "python3-dbus", "rfkill", "systemd-resolved", "wireless-regdb"}
            <= packages
        )

    def test_live_iwd_owns_network_configuration_without_changing_target_policy(self) -> None:
        live = (PROJECT_ROOT / "build/installer-overlay/etc/iwd/main.conf").read_text(
            encoding="utf-8"
        )
        target = (PROJECT_ROOT / "build/overlay/etc/iwd/main.conf").read_text(
            encoding="utf-8"
        )
        self.assertIn("EnableNetworkConfiguration=true", live)
        self.assertIn("NameResolvingService=systemd", live)
        self.assertIn("EnableNetworkConfiguration=false", target)

    def test_graphical_installer_orders_after_wireless_services(self) -> None:
        service = (
            PROJECT_ROOT
            / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text(encoding="utf-8")
        self.assertIn("Wants=iwd.service systemd-resolved.service", service)
        self.assertIn("iwd.service systemd-resolved.service", service)


if __name__ == "__main__":
    unittest.main()
