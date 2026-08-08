from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_installer.power import PowerStatus, PowerSupplyProbe


class InstallerPowerTests(unittest.TestCase):
    def test_low_battery_without_external_power_is_blocked(self) -> None:
        reason = PowerStatus(True, 19, False).installation_block_reason()
        self.assertIn("Connect the power adapter", reason or "")
        self.assertIsNone(PowerStatus(True, 80, False).installation_block_reason())
        self.assertIsNone(PowerStatus(True, 10, True).installation_block_reason())
        self.assertIsNone(PowerStatus(True, 10, None).installation_block_reason())
        unknown_reason = PowerStatus(True, None, False).installation_block_reason()
        self.assertIn("could not be read", unknown_reason or "")

    def test_sysfs_probe_combines_battery_and_ac_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            battery = root / "BAT0"
            battery.mkdir()
            (battery / "type").write_text("Battery\n")
            (battery / "present").write_text("1\n")
            (battery / "capacity").write_text("25\n")
            ac = root / "AC"
            ac.mkdir()
            (ac / "type").write_text("Mains\n")
            (ac / "online").write_text("0\n")
            status = PowerSupplyProbe(root).probe()
        self.assertEqual(status.battery_percent, 25)
        self.assertFalse(status.external_power_online)
        self.assertIsNotNone(status.installation_block_reason())

    def test_sysfs_tracks_present_battery_when_capacity_is_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            battery = root / "BAT0"
            battery.mkdir()
            (battery / "type").write_text("Battery\n")
            (battery / "present").write_text("1\n")
            ac = root / "AC"
            ac.mkdir()
            (ac / "type").write_text("Mains\n")
            (ac / "online").write_text("0\n")
            status = PowerSupplyProbe(root).probe()
        self.assertTrue(status.battery_present)
        self.assertIsNone(status.battery_percent)
        self.assertIsNotNone(status.installation_block_reason())


if __name__ == "__main__":
    unittest.main()
