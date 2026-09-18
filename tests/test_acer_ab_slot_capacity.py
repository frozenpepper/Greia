"""T01: Acer A/B 1536 MiB slot sizing capacity regression (Repair A).

Loads the real ``build/profiles/acer-aspire-one-i386-ab.toml`` and proves,
through the real production owners, that 1536 MiB system slots validate
everywhere and that the real capacity formula both fits a normal candidate
(with finalization reserve + a representative hardware-support installed
bound) and refuses an over-capacity candidate before destination mutation.

Production path crossed: BuildProfile.load (profile loader) ->
ProfileSizing/plan_for_profile (installer layout) ->
InstalledLayoutRecord.from_dict (persistent layout) ->
DestinationSlot.resolve_from_layout + SlotWriter.write (capacity formula,
pre-stream refusal) + require_finalized_slot_capacity (install-plan gate).
No SSH, mounts, flashing, Docker, signing or network involved.
"""

from __future__ import annotations

import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from build_profile import BuildProfile  # noqa: E402

from greia_installer.layout import (  # noqa: E402
    LABEL_RESERVED_BYTES,
    LayoutError,
    LegacyBiosAbAdapter,
    ProfileSizing,
    plan_for_profile,
    require_finalized_slot_capacity,
)
from greia_platform.persistent_layout import InstalledLayoutRecord  # noqa: E402
from greia_platform.slot_writer import (  # noqa: E402
    DestinationSlot,
    LoopbackSlotFile,
    SlotWriteError,
    SlotWriter,
    VerifiedReleaseMember,
)

ACER_AB_PROFILE = PROJECT_ROOT / "build/profiles/acer-aspire-one-i386-ab.toml"

#: Lifecycle plan A21 product default: 1536 MiB A/B system slots.
SLOT_1536_MIB = 1536 * 1024 * 1024

MIB = 1024 * 1024

#: Representative hardware-support installed-size bound (firmware/microcode
#: installed into the slot during finalization). Tens of MiB is the
#: realistic magnitude; 64 MiB is taken as an upper bound here, not a
#: measured per-machine value.
SUPPORT_INSTALLED_BOUND = 64 * MIB

_INSTALL_SHA = "ab" * 32
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"


def _payload(size: int = MIB) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _member(payload: bytes, *, minimum_slot_bytes: int) -> VerifiedReleaseMember:
    hw = b"hwset-member"
    return VerifiedReleaseMember(
        release_id="greia-0.15.0",
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        payload_size=len(payload),
        payload_uncompressed_bytes=len(payload),
        minimum_slot_bytes=minimum_slot_bytes,
        hardware_support_sha256=hashlib.sha256(hw).hexdigest(),
        hardware_support_size=len(hw),
    )


def _layout_record(*, slot_bytes: int) -> InstalledLayoutRecord:
    return InstalledLayoutRecord.from_dict(
        {
            "accepted_release_id": "greia-0.14.0",
            "accepted_slot": "A",
            "boot_backend": "grub-ab-v1",
            "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
            "install_profile": "acer-aspire-one-i386-ab",
            "install_target_sha256": _INSTALL_SHA,
            "installed_at_unix": 1757000000,
            "layout_id": "legacy-bios-ab-v1",
            "persist": {
                "filesystem_uuid": _UUID_P_FS,
                "partuuid": "1234abcd-04",
                "scheme": "MBR_PARTUUID",
            },
            "platform_family": "legacy-x86",
            "schema_version": 1,
            "slot_bytes": slot_bytes,
            "system_a": {
                "filesystem_uuid": _UUID_A_FS,
                "partuuid": "1234abcd-02",
                "scheme": "MBR_PARTUUID",
            },
            "system_b": {
                "filesystem_uuid": _UUID_B_FS,
                "partuuid": "1234abcd-03",
                "scheme": "MBR_PARTUUID",
            },
        }
    )


class AcerAbSlotCapacityTests(unittest.TestCase):
    def test_real_profile_declares_1536_mib_slots(self) -> None:
        profile = BuildProfile.load(ACER_AB_PROFILE)
        self.assertEqual(profile.storage.system_slot_bytes, SLOT_1536_MIB)
        self.assertEqual(profile.storage.system_slot_bytes, 1610612736)
        self.assertEqual(profile.storage.layout_adapter, "legacy-bios-ab-v1")
        self.assertEqual(profile.updates.boot_backend, "grub-ab-v1")

    def test_real_profile_declares_1024_mib_persist_minimum(self) -> None:
        profile = BuildProfile.load(ACER_AB_PROFILE)
        self.assertEqual(profile.storage.persistent_minimum_bytes, 1024 * MIB)
        self.assertEqual(profile.storage.persistent_minimum_bytes, 1073741824)
        self.assertNotEqual(
            profile.storage.persistent_minimum_bytes, 256 * MIB
        )

    def test_real_planner_enforces_1gib_persist_minimum_and_refusal(self) -> None:
        profile = BuildProfile.load(ACER_AB_PROFILE)
        sizing = ProfileSizing(
            layout_adapter_id=profile.storage.layout_adapter,
            slot_bytes=profile.storage.system_slot_bytes,
            persist_minimum_bytes=profile.storage.persistent_minimum_bytes,
            boot_backend=profile.updates.boot_backend,
        )
        self.assertEqual(sizing.persist_minimum_bytes, 1024 * MIB)
        # Smallest accepted device derived from the production adapter
        # constants (label reserve + boot-control + both slots + PERSIST),
        # proven through the real planner rather than hand arithmetic.
        minimum_device = (
            LABEL_RESERVED_BYTES
            + LegacyBiosAbAdapter.BOOT_CONTROL_BYTES
            + 2 * profile.storage.system_slot_bytes
            + profile.storage.persistent_minimum_bytes
        )
        with self.assertRaisesRegex(LayoutError, "does not fit"):
            plan_for_profile(sizing, device_size_bytes=minimum_device - 1)
        plan = plan_for_profile(sizing, device_size_bytes=minimum_device)
        self.assertGreaterEqual(plan.remainder_bytes(), 1024 * MIB)
        self.assertEqual(plan.remainder_bytes(), 1024 * MIB)

    def test_1536_mib_validates_across_profile_and_layout_owners(self) -> None:
        profile = BuildProfile.load(ACER_AB_PROFILE)
        # Profile loader already validated on load; the installer layout seam
        # must accept the same profile-owned sizing on a real-size target
        # (8 GiB Acer-class disk) with slot roles bound to the profile slot.
        sizing = ProfileSizing(
            layout_adapter_id=profile.storage.layout_adapter,
            slot_bytes=profile.storage.system_slot_bytes,
            persist_minimum_bytes=profile.storage.persistent_minimum_bytes,
            boot_backend=profile.updates.boot_backend,
        )
        plan = plan_for_profile(sizing, device_size_bytes=8 * 1024 * MIB)
        for role in ("system-a", "system-b"):
            partition = plan.by_role(role)
            self.assertIsNotNone(partition)
            assert partition is not None
            self.assertEqual(partition.size_bytes, SLOT_1536_MIB)
        # Persistent-layout record owner accepts the same slot size.
        record = _layout_record(slot_bytes=profile.storage.system_slot_bytes)
        self.assertEqual(record.slot_bytes, SLOT_1536_MIB)

    def test_valid_candidate_fits_with_reserve_and_support_bound(self) -> None:
        profile = BuildProfile.load(ACER_AB_PROFILE)
        slot_bytes = profile.storage.system_slot_bytes
        # Justified base minimum from the real profile: the preferred core
        # size (800 MiB) as the candidate's minimum base filesystem size.
        base_minimum = profile.resources.preferred_core_mib * MIB
        payload = _payload()
        member = _member(payload, minimum_slot_bytes=base_minimum)
        writer = SlotWriter()
        # Install-plan gate and writer must agree on the identical bound.
        planned = require_finalized_slot_capacity(
            slot_bytes=slot_bytes,
            base_bytes=len(payload),
            minimum_slot_bytes=base_minimum,
            support_installed_bytes=SUPPORT_INSTALLED_BOUND,
        )
        self.assertEqual(
            planned, writer.required_slot_bytes(member, SUPPORT_INSTALLED_BOUND)
        )
        reserve = slot_bytes - planned
        self.assertGreater(reserve, 0)
        # A normal candidate keeps a substantial reserve, not a 1-byte fit.
        self.assertGreaterEqual(reserve, 256 * MIB)
        record = _layout_record(slot_bytes=slot_bytes)
        destination = DestinationSlot.resolve_from_layout(record, "B")
        with tempfile.TemporaryDirectory() as directory:
            store = LoopbackSlotFile.create(
                Path(directory) / "slot-b.img", destination.slot_capacity_bytes
            )
            try:
                write = writer.write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,
                    support_installed_bytes=SUPPORT_INSTALLED_BOUND,
                )
                self.assertEqual(write.bytes_written, len(payload))
                self.assertEqual(store.read_at(0, len(payload)), payload)
            finally:
                store.close()

    def test_over_capacity_candidate_refused_before_mutation(self) -> None:
        profile = BuildProfile.load(ACER_AB_PROFILE)
        slot_bytes = profile.storage.system_slot_bytes
        payload = _payload()
        # Sensitivity control: a manifest minimum equal to the slot size
        # (the habitual error the release docs warn against) plus any
        # support/finalization headroom must exceed the slot and be refused.
        oversized_minimum = slot_bytes
        with self.assertRaisesRegex(LayoutError, "capacity bound"):
            require_finalized_slot_capacity(
                slot_bytes=slot_bytes,
                base_bytes=len(payload),
                minimum_slot_bytes=oversized_minimum,
                support_installed_bytes=SUPPORT_INSTALLED_BOUND,
            )
        member = _member(payload, minimum_slot_bytes=oversized_minimum)
        record = _layout_record(slot_bytes=slot_bytes)
        destination = DestinationSlot.resolve_from_layout(record, "B")
        with tempfile.TemporaryDirectory() as directory:
            store = LoopbackSlotFile.create(
                Path(directory) / "slot-b.img", destination.slot_capacity_bytes
            )
            try:
                with self.assertRaisesRegex(SlotWriteError, "headroom"):
                    SlotWriter().write(
                        member=member,
                        destination=destination,
                        source=io.BytesIO(payload),
                        storage=store,
                        support_installed_bytes=SUPPORT_INSTALLED_BOUND,
                    )
                # Refusal happens before any byte is streamed: destination
                # storage is untouched (still zeroed).
                self.assertEqual(store.read_at(0, 16), b"\x00" * 16)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
