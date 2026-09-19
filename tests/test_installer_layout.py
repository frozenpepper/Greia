"""A8-LAYOUT loop/disposable-media proofs (source gate, fake runner).

All destructive commands run against a RecordingRunner, never a valued
device: the locator is a disposable ``/dev/loopN``-style observation and no
test performs losetup/parted/mkfs. Real loop-device execution stays in the
deferred hardware backlog (source-first amendment 2026-09-06).
"""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path

from greia_installer.disk import DeviceObservation, DiskProbeError, partition_number_path
from greia_installer.layout import (
    KNOWN_LAYOUT_ADAPTER_IDS,
    LAYOUT_ADAPTERS,
    LayoutError,
    LayoutPlan,
    PlannedPartition,
    adapter_for,
)


SLOT_BYTES = 1024**3
PERSIST_MINIMUM_BYTES = 256 * 1024**2
DEVICE_BYTES = 8 * 1024**3
LEGACY_BOOT_CONTROL_MIB = 64


def disposable_target(
    *, path: str = "/dev/loop99", size_bytes: int = DEVICE_BYTES
) -> DeviceObservation:
    return DeviceObservation(
        name=Path(path).name,
        path=Path(path),
        size_bytes=size_bytes,
        device_type="disk",
        model="disposable loop file",
        serial="PRIVATE-SERIAL",
        transport="ata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="PRIVATE-WWN",
        major_minor="7:99",
    )


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command) -> object:
        assert isinstance(command, list), "runner must receive an argument array"
        assert all(isinstance(word, str) for word in command)
        self.commands.append(list(command))
        return None


class LayoutAdapterRegistryTests(unittest.TestCase):
    def test_canonical_ids_registered_and_unknown_fails_closed(self) -> None:
        self.assertEqual(
            KNOWN_LAYOUT_ADAPTER_IDS,
            {"legacy-bios-ab-v1", "modern-gpt-ab-v1", "pi-mbr-tryboot-ab-v1"},
        )
        for adapter_id in sorted(KNOWN_LAYOUT_ADAPTER_IDS):
            self.assertIs(adapter_for(adapter_id), LAYOUT_ADAPTERS[adapter_id])
        with self.assertRaisesRegex(LayoutError, "unknown layout adapter"):
            adapter_for("modern-uefi-ab-v1")
        with self.assertRaisesRegex(LayoutError, "unknown layout adapter"):
            adapter_for("bios-single-ext4")

    def test_skeleton_role_models_fit_the_common_interface(self) -> None:
        for adapter_id in ("modern-gpt-ab-v1", "pi-mbr-tryboot-ab-v1"):
            adapter = adapter_for(adapter_id)
            plan = adapter.plan(
                device_size_bytes=DEVICE_BYTES,
                slot_bytes=SLOT_BYTES,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
            )
            self.assertIsNotNone(plan.by_role("system-a"))
            self.assertIsNotNone(plan.by_role("system-b"))
            self.assertIsNotNone(plan.by_role("persist"))
            self.assertEqual(plan.by_role("system-a").size_bytes, SLOT_BYTES)
            self.assertEqual(plan.by_role("system-b").size_bytes, SLOT_BYTES)
            self.assertIsNone(plan.by_role("persist").size_bytes)

    def test_skeleton_execution_deferred_with_zero_commands(self) -> None:
        cases = (
            ("modern-gpt-ab-v1", "8C"),
            ("pi-mbr-tryboot-ab-v1", "8D"),
        )
        for adapter_id, phase in cases:
            adapter = adapter_for(adapter_id)
            plan = adapter.plan(
                device_size_bytes=DEVICE_BYTES,
                slot_bytes=SLOT_BYTES,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
            )
            runner = RecordingRunner()
            with self.assertRaisesRegex(LayoutError, phase):
                adapter.execute(runner, target=disposable_target(), plan=plan)
            self.assertEqual(runner.commands, [])


class LegacyPlanValidationTests(unittest.TestCase):
    def test_roles_order_sizes_and_remainder_math(self) -> None:
        plan = adapter_for("legacy-bios-ab-v1").plan(
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        self.assertEqual(
            [(item.number, item.role) for item in plan.partitions],
            [(1, "boot-control"), (2, "system-a"), (3, "system-b"), (4, "persist")],
        )
        self.assertEqual(plan.by_role("boot-control").size_bytes, 64 * 1024**2)
        self.assertEqual(
            plan.remainder_bytes(),
            DEVICE_BYTES - 1024**2 - LEGACY_BOOT_CONTROL_MIB * 1024**2 - 2 * SLOT_BYTES,
        )
        self.assertGreaterEqual(plan.remainder_bytes(), PERSIST_MINIMUM_BYTES)

    def test_undersize_device_fails_closed(self) -> None:
        fixed = 1024**2 + LEGACY_BOOT_CONTROL_MIB * 1024**2 + 2 * SLOT_BYTES
        with self.assertRaisesRegex(LayoutError, "does not fit"):
            adapter_for("legacy-bios-ab-v1").plan(
                device_size_bytes=fixed + PERSIST_MINIMUM_BYTES - 1,
                slot_bytes=SLOT_BYTES,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
            )
        # Exact fit is accepted.
        plan = adapter_for("legacy-bios-ab-v1").plan(
            device_size_bytes=fixed + PERSIST_MINIMUM_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        self.assertEqual(plan.remainder_bytes(), PERSIST_MINIMUM_BYTES)

    def test_unaligned_or_out_of_bounds_slot_rejected(self) -> None:
        adapter = adapter_for("legacy-bios-ab-v1")
        with self.assertRaisesRegex(LayoutError, "1 MiB aligned"):
            adapter.plan(
                device_size_bytes=DEVICE_BYTES,
                slot_bytes=SLOT_BYTES + 1,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
            )
        with self.assertRaisesRegex(LayoutError, "slot bound"):
            adapter.plan(
                device_size_bytes=DEVICE_BYTES,
                slot_bytes=512 * 1024**2,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
            )
        with self.assertRaisesRegex(LayoutError, "slot bound"):
            adapter.plan(
                device_size_bytes=DEVICE_BYTES,
                slot_bytes=3 * 1024**3,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
            )

    def test_tampered_role_model_rejected(self) -> None:
        # system-a resized away from the profile slot_bytes.
        tampered_system_a = PlannedPartition(
            number=2,
            role="system-a",
            size_bytes=SLOT_BYTES + 1024**2,
            filesystem="ext4",
            label="GREIA_SYS_A",
        )
        with self.assertRaisesRegex(LayoutError, "must equal the profile slot_bytes"):
            LayoutPlan(
                adapter_id="legacy-bios-ab-v1",
                label_type="msdos",
                device_size_bytes=DEVICE_BYTES,
                slot_bytes=SLOT_BYTES,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
                boot_backend="grub-ab-v1",
                partitions=(
                    PlannedPartition(
                        number=1,
                        role="boot-control",
                        size_bytes=64 * 1024**2,
                        filesystem="ext4",
                        label="GREIA_BOOT",
                        flags=("boot",),
                    ),
                    tampered_system_a,
                    PlannedPartition(
                        number=3,
                        role="system-b",
                        size_bytes=SLOT_BYTES,
                        filesystem="ext4",
                        label="GREIA_SYS_B",
                    ),
                    PlannedPartition(
                        number=4,
                        role="persist",
                        size_bytes=None,
                        filesystem="ext4",
                        label="GREIA_PERSIST",
                    ),
                ),
            )

    def test_duplicate_roles_and_missing_remainder_rejected(self) -> None:
        base = dict(
            adapter_id="legacy-bios-ab-v1",
            label_type="msdos",
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
            boot_backend="grub-ab-v1",
        )
        with self.assertRaisesRegex(LayoutError, "duplicate semantic roles"):
            LayoutPlan(
                **base,  # type: ignore[arg-type]
                partitions=(
                    PlannedPartition(
                        number=1, role="system-a", size_bytes=SLOT_BYTES,
                        filesystem="ext4", label="GREIA_SYS_A",
                    ),
                    PlannedPartition(
                        number=2, role="system-a", size_bytes=SLOT_BYTES,
                        filesystem="ext4", label="GREIA_SYS_B",
                    ),
                    PlannedPartition(
                        number=3, role="persist", size_bytes=None,
                        filesystem="ext4", label="GREIA_PERSIST",
                    ),
                ),
            )
        with self.assertRaisesRegex(LayoutError, "exactly one remainder"):
            LayoutPlan(
                **base,  # type: ignore[arg-type]
                partitions=(
                    PlannedPartition(
                        number=1, role="boot-control", size_bytes=64 * 1024**2,
                        filesystem="ext4", label="GREIA_BOOT", flags=("boot",),
                    ),
                    PlannedPartition(
                        number=2, role="system-a", size_bytes=SLOT_BYTES,
                        filesystem="ext4", label="GREIA_SYS_A",
                    ),
                    PlannedPartition(
                        number=3, role="system-b", size_bytes=SLOT_BYTES,
                        filesystem="ext4", label="GREIA_SYS_B",
                    ),
                    PlannedPartition(
                        number=4, role="persist", size_bytes=64 * 1024**2,
                        filesystem="ext4", label="GREIA_PERSIST",
                    ),
                ),
            )


class LegacyExecutionTests(unittest.TestCase):
    def test_command_sequence_alignments_and_labels(self) -> None:
        adapter = adapter_for("legacy-bios-ab-v1")
        plan = adapter.plan(
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        runner = RecordingRunner()
        commands = adapter.execute(runner, target=disposable_target(), plan=plan)
        self.assertEqual([list(argv) for argv in commands], runner.commands)
        device = "/dev/loop99"
        expected = [
            ["wipefs", "--all", "--force", device],
            ["parted", "--script", device, "mklabel", "msdos"],
            ["parted", "--script", device, "mkpart", "primary", "ext4", "1MiB", "65MiB"],
            ["parted", "--script", device, "mkpart", "primary", "ext4", "65MiB", "1089MiB"],
            ["parted", "--script", device, "mkpart", "primary", "ext4", "1089MiB", "2113MiB"],
            ["parted", "--script", device, "mkpart", "primary", "ext4", "2113MiB", "100%"],
            ["parted", "--script", device, "set", "1", "boot", "on"],
            ["partprobe", device],
            ["udevadm", "settle"],
            ["mkfs.ext4", "-F", "-m", "1", "-L", "GREIA_BOOT", device + "p1"],
            ["mkfs.ext4", "-F", "-m", "1", "-L", "GREIA_SYS_A", device + "p2"],
            ["mkfs.ext4", "-F", "-m", "1", "-L", "GREIA_SYS_B", device + "p3"],
            ["mkfs.ext4", "-F", "-m", "1", "-L", "GREIA_PERSIST", device + "p4"],
        ]
        self.assertEqual(runner.commands, expected)

    def test_commands_are_arrays_without_shell_authority(self) -> None:
        adapter = adapter_for("legacy-bios-ab-v1")
        plan = adapter.plan(
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        runner = RecordingRunner()
        adapter.execute(runner, target=disposable_target(), plan=plan)
        for argv in runner.commands:
            self.assertIsInstance(argv, list)
            for word in argv:
                self.assertIsInstance(word, str)
                for marker in (";", "&", "|", "$", "`", "&&", "\n"):
                    self.assertNotIn(marker, word)

    def test_locator_comes_only_from_the_verified_target(self) -> None:
        adapter = adapter_for("legacy-bios-ab-v1")
        plan = adapter.plan(
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        # Plans carry no device paths at all.
        field_names = set(LayoutPlan.__dataclass_fields__)
        self.assertNotIn("path", field_names)
        self.assertTrue(
            {"device_path", "partition", "device", "node"}.isdisjoint(field_names)
        )
        # execute() takes the verified observation, never a raw path string.
        signature = inspect.signature(adapter.execute)
        self.assertEqual(
            signature.parameters["target"].annotation, "DeviceObservation"
        )
        runner = RecordingRunner()
        adapter.execute(
            runner, target=disposable_target(path="/dev/loop7"), plan=plan
        )
        locator_words = [
            word
            for argv in runner.commands
            for word in argv
            if word.startswith("/dev/")
        ]
        self.assertTrue(locator_words)
        for word in locator_words:
            self.assertTrue(
                word == "/dev/loop7" or word.startswith("/dev/loop7p"),
                f"unexpected device locator: {word}",
            )

    def test_foreign_plan_non_disk_and_shrunk_target_rejected(self) -> None:
        legacy = adapter_for("legacy-bios-ab-v1")
        modern_plan = adapter_for("modern-gpt-ab-v1").plan(
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        runner = RecordingRunner()
        with self.assertRaisesRegex(LayoutError, "does not belong to this adapter"):
            legacy.execute(runner, target=disposable_target(), plan=modern_plan)
        plan = legacy.plan(
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        with self.assertRaisesRegex(LayoutError, "does not belong to this adapter"):
            adapter_for("modern-gpt-ab-v1").build_commands(plan, disposable_target())
        self.assertEqual(runner.commands, [])
        partition = DeviceObservation(
            name="loop99p1",
            path=Path("/dev/loop99p1"),
            size_bytes=DEVICE_BYTES,
            device_type="part",
            model="",
            serial="PRIVATE-SERIAL",
            transport="ata",
            removable=False,
            read_only=False,
            mountpoints=(),
            wwn="PRIVATE-WWN",
            major_minor="7:99",
        )
        with self.assertRaisesRegex(LayoutError, "whole-disk target"):
            legacy.execute(runner, target=partition, plan=plan)
        with self.assertRaisesRegex(LayoutError, "smaller than the proven plan"):
            legacy.execute(
                runner,
                target=disposable_target(size_bytes=DEVICE_BYTES - 1),
                plan=plan,
            )
        relative = disposable_target()
        object.__setattr__(relative, "path", Path("loop99"))
        with self.assertRaisesRegex(LayoutError, "absolute device locator"):
            legacy.execute(runner, target=relative, plan=plan)
        self.assertEqual(runner.commands, [])

    def test_execute_reproves_fit_on_a_larger_verified_target(self) -> None:
        adapter = adapter_for("legacy-bios-ab-v1")
        plan = adapter.plan(
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        runner = RecordingRunner()
        commands = adapter.execute(
            runner,
            target=disposable_target(size_bytes=2 * DEVICE_BYTES),
            plan=plan,
        )
        mkparts = [argv for argv in commands if argv[0] == "parted" and "mkpart" in argv]
        self.assertEqual(len(mkparts), 4)
        # Fixed partitions keep their proven extents; only the remainder grows.
        self.assertEqual(mkparts[0][-2:], ("1MiB", "65MiB"))
        self.assertEqual(mkparts[-1][-2:], ("2113MiB", "100%"))


class PartitionNumberPathTests(unittest.TestCase):
    def test_separator_rule_matches_historical_behavior(self) -> None:
        self.assertEqual(
            partition_number_path(Path("/dev/sda"), 1), Path("/dev/sda1")
        )
        self.assertEqual(
            partition_number_path(Path("/dev/sda"), 2), Path("/dev/sda2")
        )
        self.assertEqual(
            partition_number_path(Path("/dev/mmcblk0"), 2), Path("/dev/mmcblk0p2")
        )
        self.assertEqual(
            partition_number_path(Path("/dev/loop7"), 3), Path("/dev/loop7p3")
        )
        self.assertEqual(
            partition_number_path(Path("/dev/nvme0n1"), 1), Path("/dev/nvme0n1p1")
        )

    def test_out_of_bounds_numbers_fail_closed(self) -> None:
        for bad in (0, -1, 129, True):
            with self.assertRaises(DiskProbeError):
                partition_number_path(Path("/dev/sda"), bad)


if __name__ == "__main__":
    unittest.main()
