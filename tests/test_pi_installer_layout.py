"""Source-level Pi 400/500 DOS A/B layout: recording only, no device writes."""

from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from greia_installer.disk import DeviceObservation
from greia_installer.layout import (
    LayoutError,
    LayoutPlan,
    PI_LOGICAL_EBR_RESERVE_BYTES,
    ProfileSizing,
    adapter_for,
    minimum_device_bytes_for_profile,
)

MIB = 1024 * 1024
SLOT_BYTES = 1024 * MIB
PERSIST_MINIMUM = 1536 * MIB


def fake_microsd(*, size: int = 8 * 1024**3) -> DeviceObservation:
    return DeviceObservation(
        name="mmcblk0", path=Path("/dev/mmcblk0"), size_bytes=size,
        device_type="disk", model="test MMC", serial="TEST", transport="mmc",
        removable=True, read_only=False, mountpoints=(),
        mmc_cid="TEST-CID", mmc_host_built_in=True,
    )


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> None:
        assert isinstance(command, list)
        self.commands.append(command)


class RaspberryPiAbLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = adapter_for("pi-mbr-tryboot-ab-v1")
        self.sizing = ProfileSizing(
            layout_adapter_id="pi-mbr-tryboot-ab-v1",
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM,
            boot_backend="pi-tryboot-ab-v1",
        )

    def test_native_firmware_roles_and_fat_capacity(self) -> None:
        plan = self.adapter.plan(
            device_size_bytes=8 * 1024**3,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM,
        )
        self.assertEqual(
            [(p.number, p.role) for p in plan.partitions],
            [(1, "pi-boot-control"), (2, "pi-boot-a"),
             (3, "pi-boot-b"), (5, "system-a"),
             (6, "system-b"), (7, "persist")],
        )
        for p in plan.partitions[:3]:
            self.assertEqual("fat32", p.filesystem)
            self.assertEqual(256 * MIB, p.size_bytes)
        self.assertEqual(3 * MIB, PI_LOGICAL_EBR_RESERVE_BYTES)
        self.assertEqual(
            8 * 1024**3 - 4 * MIB - 3 * 256 * MIB - 2 * SLOT_BYTES,
            plan.remainder_bytes(),
        )

    def test_disk_geometry_includes_ebr_headroom(self) -> None:
        minimum = minimum_device_bytes_for_profile(self.sizing)
        self.assertEqual(
            4 * MIB + 3 * 256 * MIB + 2 * SLOT_BYTES + PERSIST_MINIMUM,
            minimum,
        )
        self.assertEqual(
            PERSIST_MINIMUM,
            self.adapter.plan(
                device_size_bytes=minimum,
                slot_bytes=SLOT_BYTES,
                persist_minimum_bytes=PERSIST_MINIMUM,
            ).remainder_bytes(),
        )
        with self.assertRaisesRegex(LayoutError, "does not fit"):
            self.adapter.plan(
                device_size_bytes=minimum - 1,
                slot_bytes=SLOT_BYTES,
                persist_minimum_bytes=PERSIST_MINIMUM,
            )

    def test_parted_creates_extended_and_three_logical_partitions(self) -> None:
        target = fake_microsd()
        plan = self.adapter.plan(
            device_size_bytes=target.size_bytes,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM,
        )
        runner = RecordingRunner()
        actual = self.adapter.execute(runner, target=target, plan=plan)
        commands = [tuple(args) for args in runner.commands]
        self.assertEqual(tuple(commands), actual)
        self.assertIn(
            ("parted", "--script", "/dev/mmcblk0", "mkpart", "extended", "769MiB", "100%"),
            commands,
        )
        for expected in (
            ("logical", "ext4", "770MiB", "1794MiB"),
            ("logical", "ext4", "1795MiB", "2819MiB"),
            ("logical", "ext4", "2820MiB", "100%"),
        ):
            self.assertTrue(any(c[-4:] == expected for c in commands), expected)
        formatted = [c for c in commands if c[0].startswith("mkfs.")]
        self.assertEqual(6, len(formatted))
        self.assertEqual(["/dev/mmcblk0p1", "/dev/mmcblk0p2", "/dev/mmcblk0p3"],
                         [c[-1] for c in formatted[:3]])
        self.assertEqual(["/dev/mmcblk0p5", "/dev/mmcblk0p6", "/dev/mmcblk0p7"],
                         [c[-1] for c in formatted[3:]])
        self.assertTrue(all(c[0] == "mkfs.vfat" for c in formatted[:3]))
        self.assertTrue(all(c[0] == "mkfs.ext4" for c in formatted[3:]))
        self.assertEqual(["wipefs", "parted"], [c[0] for c in commands[:2]])

    def test_rejects_tampered_fat_plan_before_any_commands(self) -> None:
        target = fake_microsd()
        plan = self.adapter.plan(
            device_size_bytes=target.size_bytes,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM,
        )
        altered = replace(plan.partitions[0], size_bytes=64 * MIB)
        tampered = replace(plan, partitions=(altered, *plan.partitions[1:]))
        runner = RecordingRunner()
        with self.assertRaisesRegex(LayoutError, "canonical role model"):
            self.adapter.execute(runner, target=target, plan=tampered)
        self.assertEqual([], runner.commands)

    def test_usb_or_missing_builtin_evidence_never_partitions(self) -> None:
        plan = self.adapter.plan(
            device_size_bytes=8 * 1024**3,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM,
        )
        for candidate in (
            replace(fake_microsd(), transport="usb"),
            replace(fake_microsd(), mmc_host_built_in=False),
            replace(fake_microsd(), mmc_cid=""),
        ):
            runner = RecordingRunner()
            with self.assertRaisesRegex(LayoutError, "built-in microSD"):
                self.adapter.execute(runner, target=candidate, plan=plan)
            self.assertEqual([], runner.commands)

    def test_rejects_wrong_device_type_before_any_commands(self) -> None:
        target = replace(fake_microsd(), device_type="part")
        plan = self.adapter.plan(
            device_size_bytes=target.size_bytes,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM,
        )
        runner = RecordingRunner()
        with self.assertRaisesRegex(LayoutError, "whole-disk"):
            self.adapter.execute(runner, target=target, plan=plan)
        self.assertEqual([], runner.commands)


if __name__ == "__main__":
    unittest.main()
