from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from greia_installer.disk import BlockDevice
from greia_installer.engine import InstallRequest, InstallationEngine
from greia_installer.wifi import IwdNetworkProfile, WifiNetwork, WifiSecurity
from greia_platform.hardware import HardwareDefaults, HardwareSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command, *, check=True):
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, "", "")


def target() -> BlockDevice:
    return BlockDevice(
        name="sda",
        path=Path("/dev/sda"),
        size_bytes=7_500_000_000,
        device_type="disk",
        model="Acer internal drive",
        serial="SERIAL-SECRET",
        transport="ata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="WWN-SECRET",
        major_minor="8:0",
    )


def settings() -> HardwareSettings:
    defaults = HardwareDefaults.load(PROJECT_ROOT / "runtime/hardware-settings.toml")
    return HardwareSettings(
        schema_version=defaults.schema_version,
        touchpad_tap=defaults.touchpad_tap,
        touchpad_speed=defaults.touchpad_speed,
        mouse_speed=defaults.mouse_speed,
        natural_scrolling=defaults.natural_scrolling,
        resolution=defaults.resolution,
        keyboard_layout=defaults.keyboard_layout,
    )


class InstallerWifiPersistenceTests(unittest.TestCase):
    def test_tested_profile_is_private_and_install_record_contains_no_network_secret(self) -> None:
        ssid = "Family Wi-Fi"
        secret = "correct-horse"
        wifi = IwdNetworkProfile.for_network(
            WifiNetwork(
                ssid,
                WifiSecurity.PERSONAL,
                -42.0,
                "/net/connman/iwd/demo/home",
            ),
            secret,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            defaults = root / "opt/greia-os/runtime/hardware-settings.toml"
            defaults.parent.mkdir(parents=True)
            defaults.write_bytes(
                (PROJECT_ROOT / "runtime/hardware-settings.toml").read_bytes()
            )
            engine = InstallationEngine(
                project_root=PROJECT_ROOT,
                runner=RecordingRunner(),
            )
            request = InstallRequest(
                target(),
                root / "unused",
                settings(),
                wifi_profile=wifi,
            )
            engine._write_initial_configuration(root, request)

            saved = root / "var/lib/iwd" / wifi.filename
            self.assertTrue(saved.is_file())
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
            self.assertIn("Passphrase=", saved.read_text(encoding="utf-8"))

            record_path = root / "etc/greia-os/install-record.json"
            record_text = record_path.read_text(encoding="utf-8")
            record = json.loads(record_text)
            self.assertTrue(record["wifi_configured"])
            self.assertNotIn(ssid, record_text)
            self.assertNotIn(secret, record_text)
            self.assertNotIn("SERIAL-SECRET", record_text)
            self.assertNotIn("WWN-SECRET", record_text)

    def test_offline_install_records_wifi_as_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            defaults = root / "opt/greia-os/runtime/hardware-settings.toml"
            defaults.parent.mkdir(parents=True)
            defaults.write_bytes(
                (PROJECT_ROOT / "runtime/hardware-settings.toml").read_bytes()
            )
            engine = InstallationEngine(
                project_root=PROJECT_ROOT,
                runner=RecordingRunner(),
            )
            request = InstallRequest(target(), root / "unused", settings())
            engine._write_initial_configuration(root, request)
            record = json.loads(
                (root / "etc/greia-os/install-record.json").read_text(encoding="utf-8")
            )
            self.assertFalse(record["wifi_configured"])
            self.assertFalse((root / "var/lib/iwd").exists())


if __name__ == "__main__":
    unittest.main()
