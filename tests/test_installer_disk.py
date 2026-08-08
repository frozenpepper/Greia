from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from greia_installer.disk import LsblkDiskProbe, partition_one_path


class FakeRunner:
    def run(self, command):
        payload = {
            "blockdevices": [
                {
                    "name": "sda",
                    "path": "/dev/sda",
                    "size": 7_500_000_000,
                    "type": "disk",
                    "rm": 0,
                    "ro": 0,
                    "mountpoints": [None],
                    "model": "Internal SSD",
                    "serial": "ABC",
                    "wwn": "WWN-ABC",
                    "maj:min": "8:0",
                    "tran": "ata",
                    "children": [],
                },
                {
                    "name": "sdb",
                    "path": "/dev/sdb",
                    "size": 12_000_000_000,
                    "type": "disk",
                    "rm": 0,
                    "ro": 0,
                    "mountpoints": [None],
                    "model": "Mounted data disk",
                    "serial": "MOUNTED",
                    "wwn": "",
                    "maj:min": "8:16",
                    "tran": "ata",
                    "children": [
                        {
                            "name": "sdb1",
                            "path": "/dev/sdb1",
                            "size": 11_900_000_000,
                            "type": "part",
                            "rm": 0,
                            "ro": 0,
                            "mountpoints": ["/mnt/family-photos"],
                            "model": None,
                            "serial": None,
                            "wwn": None,
                            "maj:min": "8:17",
                            "tran": None,
                        }
                    ],
                },
                {
                    # Some USB bridges report RM=0. Transport must still reject it.
                    "name": "sdc",
                    "path": "/dev/sdc",
                    "size": 16_000_000_000,
                    "type": "disk",
                    "rm": 0,
                    "ro": 0,
                    "mountpoints": [None],
                    "model": "External USB SSD",
                    "serial": "USB",
                    "wwn": "",
                    "maj:min": "8:32",
                    "tran": "usb",
                },
                {
                    # An unmounted external SATA/adapter disk can report a
                    # normal transport; HOTPLUG is another fail-closed signal.
                    "name": "sdd",
                    "path": "/dev/sdd",
                    "size": 20_000_000_000,
                    "type": "disk",
                    "rm": 0,
                    "hotplug": 1,
                    "ro": 0,
                    "mountpoints": [None],
                    "model": "Hotplug external disk",
                    "serial": "HOT",
                    "wwn": "",
                    "maj:min": "8:48",
                    "tran": "sata",
                },
                {
                    # Built-in SD readers may report RM=0/HOTPLUG=0 and must
                    # still never appear as Phase 0 erase targets.
                    "name": "mmcblk0",
                    "path": "/dev/mmcblk0",
                    "size": 32_000_000_000,
                    "type": "disk",
                    "rm": 0,
                    "hotplug": 0,
                    "ro": 0,
                    "mountpoints": [None],
                    "model": "Inserted SD card",
                    "serial": "SDCARD",
                    "wwn": "",
                    "maj:min": "179:0",
                    "tran": "mmc",
                },
                {
                    "name": "sdf",
                    "path": "/dev/sdf",
                    "size": 12_000_000_000,
                    "type": "disk",
                    "rm": 0,
                    "hotplug": 0,
                    "ro": 0,
                    "mountpoints": [None],
                    "model": "Active encrypted volume",
                    "serial": "ACTIVE",
                    "wwn": "",
                    "maj:min": "8:80",
                    "tran": "ata",
                    "children": [
                        {
                            "name": "sdf1",
                            "path": "/dev/sdf1",
                            "size": 11_900_000_000,
                            "type": "part",
                            "rm": 0,
                            "ro": 0,
                            "mountpoints": [None],
                            "children": [
                                {
                                    "name": "crypt-family",
                                    "path": "/dev/mapper/crypt-family",
                                    "size": 11_800_000_000,
                                    "type": "crypt",
                                    "rm": 0,
                                    "ro": 0,
                                    "mountpoints": [None],
                                }
                            ],
                        }
                    ],
                },
                {
                    "name": "sde",
                    "path": "/dev/sde",
                    "size": 2_000_000_000,
                    "type": "disk",
                    "rm": 0,
                    "hotplug": 0,
                    "ro": 0,
                    "mountpoints": [None],
                    "model": "Too small",
                    "serial": "SMALL",
                    "wwn": "",
                    "maj:min": "8:64",
                    "tran": "ata",
                },
            ]
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")


class InstallerDiskTests(unittest.TestCase):
    def test_only_unmounted_non_usb_internal_disk_is_offered(self) -> None:
        targets = LsblkDiskProbe(FakeRunner()).probe().install_targets()
        self.assertEqual([target.path for target in targets], [Path("/dev/sda")])
        self.assertEqual(targets[0].major_minor, "8:0")
        self.assertEqual(len(targets[0].identity_digest), 64)


    def test_active_crypt_lvm_or_raid_descendants_are_never_offered(self) -> None:
        inventory = LsblkDiskProbe(FakeRunner()).probe()
        active = inventory.by_path(Path("/dev/sdf"))
        self.assertIsNotNone(active)
        self.assertTrue(active.has_active_storage_stack())
        self.assertNotIn(Path("/dev/sdf"), [target.path for target in inventory.install_targets()])

    def test_mmc_requires_explicit_future_profile_opt_in(self) -> None:
        inventory = LsblkDiskProbe(FakeRunner()).probe()
        default_paths = [target.path for target in inventory.install_targets()]
        opted_in_paths = [
            target.path for target in inventory.install_targets(allow_mmc=True)
        ]
        self.assertNotIn(Path("/dev/mmcblk0"), default_paths)
        self.assertIn(Path("/dev/mmcblk0"), opted_in_paths)

    def test_partition_path_handles_classic_and_mmc_names(self) -> None:
        self.assertEqual(partition_one_path(Path("/dev/sda")), Path("/dev/sda1"))
        self.assertEqual(partition_one_path(Path("/dev/mmcblk0")), Path("/dev/mmcblk0p1"))
        self.assertEqual(partition_one_path(Path("/dev/nvme0n1")), Path("/dev/nvme0n1p1"))


if __name__ == "__main__":
    unittest.main()
