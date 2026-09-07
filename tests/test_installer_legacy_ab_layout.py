"""X8-LAYOUT integrated delta: profile sizing, capacity bound, identities (8B.1).

Source gate on disposable loop observations with a recording runner only.
No test performs losetup/parted/mkfs/blkid and no valued physical disk is
addressed: every device locator is a ``/dev/loop``-style observation and
every block command is captured, never executed. Real loop-device execution
stays in the deferred hardware backlog (source-first amendment 2026-09-06).
"""

from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from greia_installer.disk import DeviceObservation
from greia_installer.layout import (
    FRESH_IDENTITY_ROLES,
    LayoutError,
    LayoutPlan,
    ProfileSizing,
    adapter_for,
    mint_fresh_partition_identities,
    plan_for_profile,
    require_finalized_slot_capacity,
)
from greia_platform.persistent_layout import (
    BlockTopology,
    InstalledLayoutRecord,
    PartitionFact,
    PersistentLayoutError,
    validate_layout_against_topology,
)
from greia_platform.slot_writer import (
    FINALIZATION_GROWTH_BYTES,
    SLOT_METADATA_RESERVE_BYTES,
)

MIB = 1024 * 1024
SLOT_BYTES = 1024 * MIB
PERSIST_MINIMUM_BYTES = 256 * MIB
DEVICE_BYTES = 8 * 1024 * 1024 * 1024


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


def profile_sizing() -> ProfileSizing:
    """Profile-owned sizing facts mirroring the typed TOML schema values."""
    return ProfileSizing(
        layout_adapter_id="legacy-bios-ab-v1",
        slot_bytes=SLOT_BYTES,
        persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        boot_backend="grub-ab-v1",
    )


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command) -> object:
        assert isinstance(command, list), "runner must receive an argument array"
        assert all(isinstance(word, str) for word in command)
        self.commands.append(list(command))
        return None


class ProfileSizingTests(unittest.TestCase):
    def test_profile_facts_produce_the_legacy_ab_plan(self) -> None:
        plan = plan_for_profile(profile_sizing(), device_size_bytes=DEVICE_BYTES)
        self.assertEqual(plan.adapter_id, "legacy-bios-ab-v1")
        self.assertEqual(plan.label_type, "msdos")
        self.assertEqual(plan.boot_backend, "grub-ab-v1")
        self.assertEqual(plan.slot_bytes, SLOT_BYTES)
        self.assertEqual(plan.persist_minimum_bytes, PERSIST_MINIMUM_BYTES)
        self.assertEqual(
            [(item.number, item.role) for item in plan.partitions],
            [(1, "boot-control"), (2, "system-a"), (3, "system-b"), (4, "persist")],
        )

    def test_sizes_come_only_from_profile_data(self) -> None:
        sizing = ProfileSizing(
            layout_adapter_id="legacy-bios-ab-v1",
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=512 * MIB,
            boot_backend="grub-ab-v1",
        )
        plan = plan_for_profile(sizing, device_size_bytes=DEVICE_BYTES)
        self.assertEqual(plan.by_role("system-a").size_bytes, SLOT_BYTES)
        self.assertEqual(plan.by_role("system-b").size_bytes, SLOT_BYTES)
        self.assertEqual(plan.persist_minimum_bytes, 512 * MIB)
        self.assertGreaterEqual(plan.remainder_bytes(), 512 * MIB)

    def test_single_root_profile_adapter_fails_closed(self) -> None:
        # The pre-A/B `bios-single-ext4` profile layout is not a registered
        # destructive adapter: no guessing, no silent single-partition path.
        with self.assertRaisesRegex(LayoutError, "unknown layout adapter"):
            ProfileSizing(
                layout_adapter_id="bios-single-ext4",
                slot_bytes=SLOT_BYTES,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
                boot_backend="none-v1",
            )

    def test_backend_mismatch_and_bad_inputs_fail_closed(self) -> None:
        with self.assertRaisesRegex(LayoutError, "boot_backend"):
            ProfileSizing(
                layout_adapter_id="legacy-bios-ab-v1",
                slot_bytes=SLOT_BYTES,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
                boot_backend="pi-tryboot-ab-v1",
            )
        with self.assertRaisesRegex(LayoutError, "positive integer"):
            ProfileSizing(
                layout_adapter_id="legacy-bios-ab-v1",
                slot_bytes=0,
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
                boot_backend="grub-ab-v1",
            )
        with self.assertRaisesRegex(LayoutError, "positive integer"):
            ProfileSizing(
                layout_adapter_id="legacy-bios-ab-v1",
                slot_bytes=True,  # type: ignore[arg-type]
                persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
                boot_backend="grub-ab-v1",
            )
        with self.assertRaisesRegex(LayoutError, "profile-owned sizing"):
            plan_for_profile(object(), device_size_bytes=DEVICE_BYTES)  # type: ignore[arg-type]
        with self.assertRaisesRegex(LayoutError, "positive integer"):
            plan_for_profile(profile_sizing(), device_size_bytes=0)


class FinalizedSlotCapacityTests(unittest.TestCase):
    def test_headroom_accepted_and_returned(self) -> None:
        required = require_finalized_slot_capacity(
            slot_bytes=SLOT_BYTES,
            base_bytes=800 * MIB,
            minimum_slot_bytes=800 * MIB,
            support_installed_bytes=32 * MIB,
        )
        expected = 800 * MIB + 32 * MIB + FINALIZATION_GROWTH_BYTES + SLOT_METADATA_RESERVE_BYTES
        self.assertEqual(required, expected)
        self.assertLessEqual(required, SLOT_BYTES)
        headroom = SLOT_BYTES - required
        self.assertGreater(headroom, 0)

    def test_defaults_are_the_platform_owned_bounds(self) -> None:
        self.assertEqual(FINALIZATION_GROWTH_BYTES, 64 * MIB)
        self.assertEqual(SLOT_METADATA_RESERVE_BYTES, 16 * MIB)
        required = require_finalized_slot_capacity(
            slot_bytes=SLOT_BYTES,
            base_bytes=800 * MIB,
            minimum_slot_bytes=800 * MIB,
            support_installed_bytes=32 * MIB,
        )
        self.assertEqual(required, 800 * MIB + 32 * MIB + 64 * MIB + 16 * MIB)

    def test_manifest_minimum_above_base_governs(self) -> None:
        required = require_finalized_slot_capacity(
            slot_bytes=SLOT_BYTES,
            base_bytes=700 * MIB,
            minimum_slot_bytes=900 * MIB,
            support_installed_bytes=0,
        )
        self.assertEqual(required, 900 * MIB + 64 * MIB + 16 * MIB)

    def test_exact_fit_accepted_undersized_rejected(self) -> None:
        exact = 800 * MIB + 32 * MIB + 64 * MIB + 16 * MIB
        self.assertEqual(
            require_finalized_slot_capacity(
                slot_bytes=exact,
                base_bytes=800 * MIB,
                minimum_slot_bytes=800 * MIB,
                support_installed_bytes=32 * MIB,
            ),
            exact,
        )
        with self.assertRaisesRegex(LayoutError, "finalized-slot capacity bound"):
            require_finalized_slot_capacity(
                slot_bytes=exact - 1,
                base_bytes=800 * MIB,
                minimum_slot_bytes=800 * MIB,
                support_installed_bytes=32 * MIB,
            )
        # Realistic undersized profile: 950 MiB base + 100 MiB support
        # exceeds the 1 GiB reference slot once growth/reserve apply.
        with self.assertRaisesRegex(LayoutError, "finalized-slot capacity bound"):
            require_finalized_slot_capacity(
                slot_bytes=SLOT_BYTES,
                base_bytes=950 * MIB,
                minimum_slot_bytes=950 * MIB,
                support_installed_bytes=100 * MIB,
            )

    def test_non_integer_bounds_fail_closed(self) -> None:
        with self.assertRaisesRegex(LayoutError, "positive integer"):
            require_finalized_slot_capacity(
                slot_bytes=True,  # type: ignore[arg-type]
                base_bytes=800 * MIB,
                minimum_slot_bytes=800 * MIB,
                support_installed_bytes=0,
            )
        with self.assertRaisesRegex(LayoutError, "non-negative integer"):
            require_finalized_slot_capacity(
                slot_bytes=SLOT_BYTES,
                base_bytes=800 * MIB,
                minimum_slot_bytes=800 * MIB,
                support_installed_bytes=-1,
            )


class FreshIdentityTests(unittest.TestCase):
    def test_roles_shape_and_distinctness(self) -> None:
        self.assertEqual(FRESH_IDENTITY_ROLES, ("system-a", "system-b", "persist"))
        minted = mint_fresh_partition_identities()
        self.assertEqual(set(minted), {"system-a", "system-b", "persist"})
        for role, identity in minted.items():
            self.assertEqual(set(identity), {"partuuid", "filesystem_uuid"})
            for key, value in identity.items():
                self.assertEqual(value, str(uuid.UUID(value)).lower(), f"{role}.{key}")
        seen = [minted[role][key] for role in FRESH_IDENTITY_ROLES for key in ("partuuid", "filesystem_uuid")]
        self.assertEqual(len(set(seen)), 6)

    def test_boot_control_is_outside_layout_authority(self) -> None:
        plan = plan_for_profile(profile_sizing(), device_size_bytes=DEVICE_BYTES)
        self.assertIsNotNone(plan.by_role("boot-control"))
        self.assertNotIn("boot-control", mint_fresh_partition_identities())

    def test_two_mints_never_clone(self) -> None:
        first = mint_fresh_partition_identities()
        second = mint_fresh_partition_identities()
        first_seen = {first[role][key] for role in FRESH_IDENTITY_ROLES for key in ("partuuid", "filesystem_uuid")}
        second_seen = {second[role][key] for role in FRESH_IDENTITY_ROLES for key in ("partuuid", "filesystem_uuid")}
        self.assertTrue(first_seen.isdisjoint(second_seen))

    def test_colliding_or_broken_factory_fails_closed(self) -> None:
        with self.assertRaisesRegex(LayoutError, "must be unique"):
            mint_fresh_partition_identities(uuid_factory=lambda: uuid.UUID(int=1))
        with self.assertRaisesRegex(LayoutError, "not a valid UUID"):
            mint_fresh_partition_identities(uuid_factory=lambda: "not-a-uuid")  # type: ignore[return-value]


class IntegratedLayoutAuthorityTests(unittest.TestCase):
    def _record_dict(self, minted: dict[str, dict[str, str]]) -> dict[str, object]:
        return {
            "accepted_release_id": "greia-release-1",
            "accepted_release_sequence": 1,
            "accepted_slot": "A",
            "boot_backend": "grub-ab-v1",
            "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
            "install_profile": "legacy-x86-i686",
            "install_target_sha256": "ab" * 32,
            "installed_at_unix": 1788640000,
            "layout_id": "legacy-bios-ab-v1",
            "persist": dict(minted["persist"]),
            "platform_family": "legacy-x86",
            "schema_version": 1,
            "slot_bytes": SLOT_BYTES,
            "system_a": dict(minted["system-a"]),
            "system_b": dict(minted["system-b"]),
        }

    def _topology(self, plan: LayoutPlan, minted: dict[str, dict[str, str]]) -> BlockTopology:
        assert plan.by_role("system-a") is not None
        return BlockTopology(
            partitions=(
                PartitionFact.create(
                    role="system-a",
                    partuuid=minted["system-a"]["partuuid"],
                    filesystem_uuid=minted["system-a"]["filesystem_uuid"],
                    size_bytes=SLOT_BYTES,
                    disk_id="loop99",
                ),
                PartitionFact.create(
                    role="system-b",
                    partuuid=minted["system-b"]["partuuid"],
                    filesystem_uuid=minted["system-b"]["filesystem_uuid"],
                    size_bytes=SLOT_BYTES,
                    disk_id="loop99",
                ),
                PartitionFact.create(
                    role="persist",
                    partuuid=minted["persist"]["partuuid"],
                    filesystem_uuid=minted["persist"]["filesystem_uuid"],
                    size_bytes=plan.remainder_bytes(),
                    disk_id="loop99",
                ),
            )
        )

    def test_record_and_topology_agree_on_disposable_image(self) -> None:
        plan = plan_for_profile(profile_sizing(), device_size_bytes=DEVICE_BYTES)
        minted = mint_fresh_partition_identities()
        record = InstalledLayoutRecord.from_dict(self._record_dict(minted))
        self.assertEqual(record.slot_bytes, SLOT_BYTES)
        validate_layout_against_topology(record, self._topology(plan, minted))

    def test_swapped_or_cloned_identities_rejected(self) -> None:
        plan = plan_for_profile(profile_sizing(), device_size_bytes=DEVICE_BYTES)
        minted = mint_fresh_partition_identities()
        record = InstalledLayoutRecord.from_dict(self._record_dict(minted))
        swapped = BlockTopology(
            partitions=(
                PartitionFact.create(
                    role="system-a",
                    partuuid=minted["system-b"]["partuuid"],
                    filesystem_uuid=minted["system-b"]["filesystem_uuid"],
                    size_bytes=SLOT_BYTES,
                    disk_id="loop99",
                ),
                PartitionFact.create(
                    role="system-b",
                    partuuid=minted["system-a"]["partuuid"],
                    filesystem_uuid=minted["system-a"]["filesystem_uuid"],
                    size_bytes=SLOT_BYTES,
                    disk_id="loop99",
                ),
                PartitionFact.create(
                    role="persist",
                    partuuid=minted["persist"]["partuuid"],
                    filesystem_uuid=minted["persist"]["filesystem_uuid"],
                    size_bytes=plan.remainder_bytes(),
                    disk_id="loop99",
                ),
            )
        )
        with self.assertRaises(PersistentLayoutError):
            validate_layout_against_topology(record, swapped)
        cloned = {role: dict(identity) for role, identity in minted.items()}
        cloned["system-b"] = dict(cloned["system-a"])
        with self.assertRaisesRegex(PersistentLayoutError, "must be unique"):
            InstalledLayoutRecord.from_dict(self._record_dict(cloned))


class DisposableCommandTests(unittest.TestCase):
    def test_partition_roles_alignment_and_no_shell_authority(self) -> None:
        adapter = adapter_for("legacy-bios-ab-v1")
        plan = plan_for_profile(profile_sizing(), device_size_bytes=DEVICE_BYTES)
        runner = RecordingRunner()
        commands = adapter.execute(runner, target=disposable_target(), plan=plan)
        self.assertEqual([list(argv) for argv in commands], runner.commands)
        device = "/dev/loop99"
        self.assertEqual(
            runner.commands,
            [
                ["wipefs", "--all", "--force", device],
                ["parted", "--script", device, "mklabel", "msdos"],
                ["parted", "--script", device, "mkpart", "primary", "ext4", "1MiB", "33MiB"],
                ["parted", "--script", device, "mkpart", "primary", "ext4", "33MiB", "1057MiB"],
                ["parted", "--script", device, "mkpart", "primary", "ext4", "1057MiB", "2081MiB"],
                ["parted", "--script", device, "mkpart", "primary", "ext4", "2081MiB", "100%"],
                ["parted", "--script", device, "set", "1", "boot", "on"],
                ["partprobe", device],
                ["udevadm", "settle"],
                ["mkfs.ext4", "-F", "-m", "1", "-L", "GREIA_BOOT", device + "p1"],
                ["mkfs.ext4", "-F", "-m", "1", "-L", "GREIA_SYS_A", device + "p2"],
                ["mkfs.ext4", "-F", "-m", "1", "-L", "GREIA_SYS_B", device + "p3"],
                ["mkfs.ext4", "-F", "-m", "1", "-L", "GREIA_PERSIST", device + "p4"],
            ],
        )
        # MBR GRUB embedding space: nothing starts before 1 MiB; every fixed
        # extent is 1 MiB aligned; only the PERSIST remainder is open-ended.
        mkparts = [argv for argv in runner.commands if "mkpart" in argv]
        self.assertEqual(len(mkparts), 4)
        self.assertTrue(mkparts[0][-2].startswith("1MiB"))
        self.assertEqual(mkparts[-1][-1], "100%")
        for argv in runner.commands:
            self.assertIsInstance(argv, list)
            for word in argv:
                self.assertIsInstance(word, str)
                for marker in (";", "&", "|", "$", "`", "&&", "\n", " ", "\t"):
                    if word.startswith("/dev/"):
                        continue
                    self.assertNotIn(marker, word)
            for word in argv:
                if word.startswith("/dev/"):
                    self.assertTrue(
                        word == device or word.startswith(device + "p"),
                        f"locator escapes the disposable target: {word}",
                    )
        # Plans carry no device paths: the locator comes only from the
        # verified observation at execute() time.
        field_names = set(LayoutPlan.__dataclass_fields__)
        self.assertTrue({"device_path", "partition", "device", "node", "path"}.isdisjoint(field_names))


if __name__ == "__main__":
    unittest.main()
