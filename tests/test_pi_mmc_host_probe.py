"""Physical-topology target eligibility: injectable Pi board/sysfs fixtures only."""

from __future__ import annotations

import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from greia_installer.disk import (
    LsblkDiskProbe,
    PiBuiltInMicroSdTargetPolicy,
    PiMmcHostObserver,
    DeviceObservation,
)


CID = "1234567890abcdef1234567890abcdef"


class PiMmcSysfsTests(unittest.TestCase):
    def _fixture(self, root: Path, *, board: str, usb: bool = False) -> PiMmcHostObserver:
        model = root / "proc/device-tree/model"
        model.parent.mkdir(parents=True)
        model.write_bytes((board + "\x00").encode("ascii"))
        platform = root / "sys/devices/platform"
        platform.mkdir(parents=True)
        cls = root / "sys/class/block"
        cls.mkdir(parents=True)
        if usb:
            actual = root / "sys/devices/pci0000:00/usb1/mmc_host/mmc0/mmc0:0001/block/mmcblk0"
        else:
            actual = platform / "soc/mmc-host/mmc_host/mmc0/mmc0:0001/block/mmcblk0"
        actual.mkdir(parents=True)
        card = actual.parent.parent
        (card / "cid").write_text(CID + "\n", encoding="ascii")
        (actual / "device").symlink_to(card, target_is_directory=True)
        (cls / "mmcblk0").symlink_to(actual, target_is_directory=True)
        return PiMmcHostObserver(
            board_model_path=model, class_block_root=cls, platform_root=platform
        )

    def test_pi400_and_pi500_platform_card_with_cid(self) -> None:
        for board in ("Raspberry Pi 400 Rev 1.0", "Raspberry Pi 500 Rev 1.0"):
            with self.subTest(board=board), tempfile.TemporaryDirectory() as tmp:
                observer = self._fixture(Path(tmp), board=board)
                self.assertEqual((CID, True), observer.observe("mmcblk0"))
                self.assertEqual(("", False), observer.observe("mmcblk0boot0"))

    def test_other_board_and_usb_bridge_never_become_built_in(self) -> None:
        for board, usb in (
            ("Raspberry Pi 500+ Rev 1.0", False),
            ("Raspberry Pi 5 Model B Rev 1.0", False),
            ("Generic ARM computer", False),
            ("Raspberry Pi 500 Rev 1.0", True),
        ):
            with self.subTest(board=board, usb=usb), tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(
                    ("", False), self._fixture(Path(tmp), board=board, usb=usb).observe("mmcblk0")
                )

    def test_malformed_or_missing_cid_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            observer = self._fixture(Path(tmp), board="Raspberry Pi 400 Rev 1.0")
            cid_path = (
                observer.class_block_root / "mmcblk0" / "device" / "cid"
            )
            cid_path.write_text("??\n", encoding="ascii")
            self.assertEqual(("", False), observer.observe("mmcblk0"))

    def test_lsblk_to_sysfs_to_policy_end_to_end(self) -> None:
        """Do not merely test injected DeviceObservation booleans.

        The *real* lsblk JSON adapter must populate built-in/CID evidence
        from sysfs; an SD card and USB installer are present together.
        """
        with tempfile.TemporaryDirectory() as tmp:
            sysfs = self._fixture(Path(tmp), board="Raspberry Pi 500 Rev 1.0")
            devices = [
                dict(name="mmcblk0", path="/dev/mmcblk0", size=16 * 1024**3,
                     type="disk", rm=1, hotplug=1, ro=0, mountpoints=[],
                     model="SD", serial="", wwn="", tran="mmc", **{"maj:min": "179:0"}),
                dict(name="sda", path="/dev/sda", size=16 * 1024**3,
                     type="disk", rm=1, hotplug=1, ro=0, mountpoints=[],
                     model="USB", serial="USB-SERIAL", wwn="", tran="usb", **{"maj:min": "8:0"}),
            ]

            class FakeRunner:
                def run(self, command):
                    self.command = command
                    return SimpleNamespace(
                        returncode=0,
                        stdout=json.dumps({"blockdevices": devices}),
                        stderr="",
                    )

            runner = FakeRunner()
            inventory = LsblkDiskProbe(
                runner, mmc_host_observer=sysfs
            ).probe()
            self.assertIn("MOUNTPOINTS", runner.command[-1])
            self.assertEqual(CID, inventory.devices[0].mmc_cid)
            self.assertTrue(inventory.devices[0].mmc_host_built_in)
            self.assertFalse(inventory.devices[1].mmc_host_built_in)
            self.assertEqual(
                ["/dev/mmcblk0"],
                [str(item.path) for item in inventory.install_targets(PiBuiltInMicroSdTargetPolicy())],
            )

    def test_removable_unproven_card_returns_rejection_not_exception(self) -> None:
        """Regression: zero-arg super() in slots dataclass raised TypeError."""
        policy = PiBuiltInMicroSdTargetPolicy()
        common = dict(
            name="mmcblk0", path=Path("/dev/mmcblk0"), size_bytes=16 * 1024**3,
            device_type="disk", model="SD", serial="", transport="mmc",
            removable=True, hotplug=False, read_only=False, mountpoints=(),
            mmc_cid=CID, mmc_host_built_in=False,
        )
        decision = policy.evaluate(DeviceObservation(**common))
        self.assertFalse(decision.eligible)
        self.assertIn("removable", decision.reason)
        self.assertFalse(
            policy.evaluate(
                DeviceObservation(**{**common, "mmc_host_built_in": True, "mmc_cid": ""})
            ).eligible
        )

    def test_removable_builtin_mmc_allowed_and_usb_excluded(self) -> None:
        policy = PiBuiltInMicroSdTargetPolicy()
        common = dict(
            name="mmcblk0", path=Path("/dev/mmcblk0"), size_bytes=16 * 1024**3,
            device_type="disk", model="SD", serial="CARD", transport="mmc",
            removable=True, hotplug=True, read_only=False, mountpoints=(),
            mmc_cid=CID, mmc_host_built_in=True,
        )
        positive = DeviceObservation(**common)
        self.assertTrue(policy.evaluate(positive).eligible)
        self.assertFalse(policy.evaluate(
            DeviceObservation(**{**common, "mmc_host_built_in": False})
        ).eligible)
        self.assertFalse(policy.evaluate(
            DeviceObservation(**{**common, "transport": "usb"})
        ).eligible)
        self.assertFalse(policy.evaluate(
            DeviceObservation(**{**common, "mmc_cid": ""})
        ).eligible)


if __name__ == "__main__":
    unittest.main()
