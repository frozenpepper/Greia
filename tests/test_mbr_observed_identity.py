"""T1-IDENT: layout-specific observed MBR partition identity (TAKEOVER-1 T1.1, D51).

Supersedes the X8-LAYOUT minted-UUID evidence for MBR layouts: MBR
PARTUUIDs are the observed ``<disk-signature>-<partno>`` form, never a
minted UUID4. GPT and Pi adapters keep their own (deferred) observation
rules; no MBR parsing lives in them (see ``AdapterBoundaryTests``).

Evidence layers in this module:

* unit parsing/normalization of the scheme-aware identity model;
* scripted-``blkid`` observation proving the exact controlled tool path
  (argument arrays, locator from the verified target only) plus the
  wrong-disk / cloned-UUID / empty-probe fail-closed gates;
* a disposable genuinely-partitioned raw image: a sparse file carrying a
  real DOS MBR (magic, disk signature, four primary entries whose extents
  match the legacy adapter's declarative plan), parsed back with the
  production ``parse_dos_partition_table`` rule, bound into a persisted
  layout record, torn down, reloaded and proven for A/B/PERSIST
  resolution — with wrong-signature / swapped / cloned negatives;
* positive controls (break -> RED -> restore -> GREEN) proving the
  detectors are sensitive, not vacuously green.

Out of scope here by task boundary: the fresh-install orchestrator
rewire (T3-INSTALL) and the GRUB locator separation (T1-GRUB). The
pre-T1.1 minted-UUID path stays parseable as PROVISIONAL compat so the
unwired orchestrator does not regress; new MBR authority is strict.
"""

from __future__ import annotations

import gc
import inspect
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from greia_installer.disk import DeviceObservation
from greia_installer.layout import (
    DosTableObservation,
    LayoutError,
    MbrCommandResult,
    MbrProbeRunner,
    SubprocessMbrProbeRunner,
    adapter_for,
    build_observed_mbr_topology,
    mint_fresh_partition_identities,
    observe_legacy_mbr_identities,
    observe_partition_identities,
    parse_dos_partition_table,
    plan_for_profile,
    ProfileSizing,
    verify_mbr_topology_for_boot,
)
from greia_platform.persistent_layout import (
    PARTITION_SCHEME_GPT_GUID,
    PARTITION_SCHEME_MBR_PARTUUID,
    BlockTopology,
    InstalledLayoutRecord,
    PartitionFact,
    PersistentLayoutError,
    infer_partuuid_scheme,
    normalize_mbr_partuuid,
    require_mbr_disk_signature,
    require_mbr_topology_binding,
    split_mbr_partuuid,
    validate_layout_against_topology,
)

MIB = 1024 * 1024
SLOT_BYTES = 1024 * MIB
PERSIST_MINIMUM_BYTES = 256 * MIB
DEVICE_BYTES = 8 * 1024 * 1024 * 1024

LEGACY_ROLES = ("system-a", "system-b", "persist")
LEGACY_NUMBERS = {"system-a": 2, "system-b": 3, "persist": 4}

_MBRSIGNATURE = "9f3ac271"


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


def legacy_plan():
    sizing = ProfileSizing(
        layout_adapter_id="legacy-bios-ab-v1",
        slot_bytes=SLOT_BYTES,
        persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        boot_backend="grub-ab-v1",
    )
    return plan_for_profile(sizing, device_size_bytes=DEVICE_BYTES)


class ScriptedProbeRunner(MbrProbeRunner):
    """Fake controlled tool path: scripted stdout per (tool, tag, locator)."""

    def __init__(self, answers: dict[tuple[str, ...], tuple[str, int]]) -> None:
        self.answers = dict(answers)
        self.commands: list[list[str]] = []

    def run(self, command) -> MbrCommandResult:
        assert isinstance(command, list), "probe must receive an argument array"
        assert all(isinstance(word, str) for word in command)
        self.commands.append(list(command))
        key = tuple(command)
        if key not in self.answers:
            raise AssertionError(f"unexpected probe command: {command}")
        stdout, returncode = self.answers[key]
        return MbrCommandResult(stdout=stdout, returncode=returncode)


def scripted_mbr_answers(
    *,
    device: str = "/dev/loop99",
    signature: str = _MBRSIGNATURE,
    filesystem_uuids: dict[str, str] | None = None,
    partuuid_override: dict[str, str] | None = None,
    drop_ptuuid: bool = False,
) -> dict[tuple[str, ...], tuple[str, int]]:
    filesystem_uuids = filesystem_uuids or {
        "system-a": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "system-b": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
        "persist": "cccccccc-dddd-eeee-ffff-000000000000",
    }
    partuuid_override = partuuid_override or {}
    numbers = {"system-a": 2, "system-b": 3, "persist": 4}
    answers: dict[tuple[str, ...], tuple[str, int]] = {}
    if not drop_ptuuid:
        answers[("blkid", "-s", "PTUUID", "-o", "value", "--", device)] = (
            signature,
            0,
        )
    nodes = {
        "system-a": device + "p2",
        "system-b": device + "p3",
        "persist": device + "p4",
    }
    for role, node in nodes.items():
        partuuid = partuuid_override.get(role, f"{signature}-{numbers[role]:02d}")
        answers[("blkid", "-s", "PARTUUID", "-o", "value", "--", node)] = (
            partuuid,
            0,
        )
        answers[("blkid", "-s", "UUID", "-o", "value", "--", node)] = (
            filesystem_uuids[role],
            0,
        )
    return answers


def mbr_record_dict(
    identities: dict[str, dict[str, str]], *, slot_bytes: int = SLOT_BYTES
) -> dict[str, object]:
    return {
        "accepted_release_id": "greia-test-1",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "legacy-x86-test",
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1788640000,
        "layout_id": "legacy-bios-ab-v1",
        "persist": dict(identities["persist"]),
        "platform_family": "legacy-x86",
        "schema_version": 1,
        "slot_bytes": slot_bytes,
        "system_a": dict(identities["system-a"]),
        "system_b": dict(identities["system-b"]),
    }


class MbrSchemeParsingTests(unittest.TestCase):
    def test_normalization_spellings(self) -> None:
        self.assertEqual(
            normalize_mbr_partuuid("9F3AC271-2", field="partuuid"), "9f3ac271-02"
        )
        self.assertEqual(
            normalize_mbr_partuuid("9f3ac271-02", field="partuuid"), "9f3ac271-02"
        )
        self.assertEqual(
            normalize_mbr_partuuid("  0x9F3AC271-12  ", field="partuuid"),
            "9f3ac271-12",
        )
        signature, number = split_mbr_partuuid("9F3AC271-2")
        self.assertEqual((signature, number), ("9f3ac271", 2))

    def test_uuid4_is_not_an_mbr_partuuid(self) -> None:
        # Positive-control anchor: the fabrication this task removes must
        # fail at the parser, not silently normalize.
        minted = str(uuid.uuid4())
        with self.assertRaises(PersistentLayoutError):
            normalize_mbr_partuuid(minted, field="partuuid")
        with self.assertRaises(PersistentLayoutError):
            split_mbr_partuuid(minted)
        # And a UUID is never inferred as MBR.
        self.assertEqual(
            infer_partuuid_scheme("11111111-2222-3333-4444-555555555555"),
            PARTITION_SCHEME_GPT_GUID,
        )
        self.assertEqual(
            infer_partuuid_scheme("9f3ac271-02"), PARTITION_SCHEME_MBR_PARTUUID
        )

    def test_rejects_garbage(self) -> None:
        for bad in (
            "",
            "no-dash-here",
            "9f3ac27-02",  # 7 hex digits
            "9f3ac2710-02",  # 9 hex digits
            "zzzzzzzz-02",  # non-hex signature
            "9f3ac271-0",  # partition 0
            "9f3ac271-129",  # above the Greia bound
            "9f3ac271-",  # missing number
            "9f3ac271-02-extra",
            "/dev/sda2",
            123,
            None,
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(PersistentLayoutError):
                    normalize_mbr_partuuid(bad, field="partuuid")
        with self.assertRaises(PersistentLayoutError):
            infer_partuuid_scheme("not-an-identity")

    def test_disk_signature_rule(self) -> None:
        self.assertEqual(
            require_mbr_disk_signature("0x9F3AC271", field="disk signature"),
            "9f3ac271",
        )
        for bad in ("", "0x00000000", "00000000", "xyz", "9f3ac27", 0, None):
            with self.subTest(bad=bad):
                with self.assertRaises(PersistentLayoutError):
                    require_mbr_disk_signature(bad, field="disk signature")

    def test_gpt_path_untouched(self) -> None:
        value = "11111111-2222-3333-4444-555555555555"
        fact = PartitionFact.create(
            role="system-a",
            scheme=PARTITION_SCHEME_GPT_GUID,
            partuuid=value,
            filesystem_uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            size_bytes=SLOT_BYTES,
            disk_id="disk0",
        )
        self.assertEqual(fact.scheme, PARTITION_SCHEME_GPT_GUID)
        self.assertIsNone(fact.disk_signature)


class PartitionIdentitySchemeTests(unittest.TestCase):
    def test_explicit_mbr_identity_normalizes(self) -> None:
        from greia_platform.persistent_layout import PartitionIdentity

        identity = PartitionIdentity.from_dict(
            {
                "filesystem_uuid": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
                "partuuid": "9F3AC271-2",
                "scheme": PARTITION_SCHEME_MBR_PARTUUID,
            },
            field="system-a",
        )
        self.assertEqual(identity.scheme, PARTITION_SCHEME_MBR_PARTUUID)
        self.assertEqual(identity.partuuid, "9f3ac271-02")
        self.assertEqual(
            identity.filesystem_uuid, "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        )
        self.assertEqual(identity.disk_signature, "9f3ac271")
        self.assertEqual(identity.as_dict()["scheme"], PARTITION_SCHEME_MBR_PARTUUID)

    def test_explicit_scheme_must_match_value_shape(self) -> None:
        from greia_platform.persistent_layout import PartitionIdentity

        # UUID value claimed as MBR: the fabrication gate.
        with self.assertRaises(PersistentLayoutError):
            PartitionIdentity.from_dict(
                {
                    "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "partuuid": "11111111-2222-3333-4444-555555555555",
                    "scheme": PARTITION_SCHEME_MBR_PARTUUID,
                },
                field="system-a",
            )
        # MBR value claimed as GPT.
        with self.assertRaises(PersistentLayoutError):
            PartitionIdentity.from_dict(
                {
                    "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "partuuid": "9f3ac271-02",
                    "scheme": PARTITION_SCHEME_GPT_GUID,
                },
                field="system-a",
            )
        with self.assertRaises(PersistentLayoutError):
            PartitionIdentity.from_dict(
                {
                    "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "partuuid": "9f3ac271-02",
                    "scheme": "SOMETHING_ELSE",
                },
                field="system-a",
            )

    def test_legacy_scheme_less_mapping_still_parses(self) -> None:
        # PROVISIONAL compat for the pre-T1.1 orchestrator path (T3 rewires
        # it to observed identities). The inferred identity re-emits
        # without a scheme, so legacy records round-trip byte-identically.
        from greia_platform.persistent_layout import PartitionIdentity

        legacy = PartitionIdentity.from_dict(
            {
                "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "partuuid": "11111111-2222-3333-4444-555555555555",
            },
            field="system-a",
        )
        self.assertEqual(legacy.scheme, PARTITION_SCHEME_GPT_GUID)
        self.assertFalse(legacy.scheme_explicit)
        self.assertNotIn("scheme", legacy.as_dict())
        self.assertEqual(
            PartitionIdentity.from_dict(legacy.as_dict(), field="system-a"),
            legacy,
        )


class RecordSchemeBindingTests(unittest.TestCase):
    def _mbr_identities(self, signature: str = _MBRSIGNATURE) -> dict[str, dict[str, str]]:
        return {
            "system-a": {
                "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "partuuid": f"{signature}-02",
                "scheme": PARTITION_SCHEME_MBR_PARTUUID,
            },
            "system-b": {
                "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                "partuuid": f"{signature}-03",
                "scheme": PARTITION_SCHEME_MBR_PARTUUID,
            },
            "persist": {
                "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
                "partuuid": f"{signature}-04",
                "scheme": PARTITION_SCHEME_MBR_PARTUUID,
            },
        }

    def test_explicit_mbr_record_accepted(self) -> None:
        record = InstalledLayoutRecord.from_dict(mbr_record_dict(self._mbr_identities()))
        self.assertEqual(record.system_a.scheme, PARTITION_SCHEME_MBR_PARTUUID)
        self.assertEqual(record.system_a.partuuid, f"{_MBRSIGNATURE}-02")

    def test_guid_labeled_mbr_refused(self) -> None:
        identities = self._mbr_identities()
        identities["system-a"] = {
            "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "partuuid": "11111111-2222-3333-4444-555555555555",
            "scheme": PARTITION_SCHEME_GPT_GUID,
        }
        with self.assertRaisesRegex(PersistentLayoutError, "fabricated MBR identity"):
            InstalledLayoutRecord.from_dict(mbr_record_dict(identities))

    def test_mixed_disk_signatures_refused(self) -> None:
        identities = self._mbr_identities()
        identities["persist"]["partuuid"] = "deadbeef-04"
        with self.assertRaisesRegex(PersistentLayoutError, "disk signatures"):
            InstalledLayoutRecord.from_dict(mbr_record_dict(identities))

    def test_mbr_scheme_on_gpt_layout_refused(self) -> None:
        raw = mbr_record_dict(self._mbr_identities())
        raw.update(
            {
                "layout_id": "modern-gpt-ab-v1",
                "platform_family": "standard-x86-64",
                "install_profile": "modern-amd64",
            }
        )
        with self.assertRaises(PersistentLayoutError):
            InstalledLayoutRecord.from_dict(raw)

    def test_gpt_record_unaffected(self) -> None:
        raw = mbr_record_dict(self._mbr_identities())
        raw.update(
            {
                "layout_id": "modern-gpt-ab-v1",
                "platform_family": "standard-x86-64",
                "install_profile": "modern-amd64",
                "persist": {
                    "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
                    "partuuid": "33333333-4444-5555-6666-777777777777",
                    "scheme": PARTITION_SCHEME_GPT_GUID,
                },
                "system_a": {
                    "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "partuuid": "11111111-2222-3333-4444-555555555555",
                    "scheme": PARTITION_SCHEME_GPT_GUID,
                },
                "system_b": {
                    "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                    "partuuid": "22222222-3333-4444-5555-666666666666",
                    "scheme": PARTITION_SCHEME_GPT_GUID,
                },
            }
        )
        record = InstalledLayoutRecord.from_dict(raw)
        self.assertEqual(record.system_a.scheme, PARTITION_SCHEME_GPT_GUID)


class ObservationTests(unittest.TestCase):
    def test_happy_path_commands_and_binding(self) -> None:
        plan = legacy_plan()
        runner = ScriptedProbeRunner(scripted_mbr_answers())
        observed = observe_legacy_mbr_identities(
            runner, target=disposable_target(), plan=plan
        )
        self.assertEqual(set(observed), {"system-a", "system-b", "persist"})
        for role in LEGACY_ROLES:
            self.assertEqual(observed[role]["scheme"], PARTITION_SCHEME_MBR_PARTUUID)
            self.assertEqual(
                observed[role]["partuuid"],
                f"{_MBRSIGNATURE}-{LEGACY_NUMBERS[role]:02d}",
            )
        # Exact controlled tool path: blkid only, argument arrays, the
        # locator comes solely from the verified target.
        self.assertEqual(
            runner.commands[0],
            ["blkid", "-s", "PTUUID", "-o", "value", "--", "/dev/loop99"],
        )
        for argv in runner.commands:
            self.assertIsInstance(argv, list)
            self.assertEqual(argv[0], "blkid")
            for word in argv:
                for marker in (";", "&", "|", "$", "`", "(", ")", "<", ">", "\n"):
                    self.assertNotIn(marker, word)
            locators = [word for word in argv if word.startswith("/dev/")]
            for locator in locators:
                self.assertTrue(
                    locator == "/dev/loop99" or locator.startswith("/dev/loop99p")
                )

    def test_wrong_disk_partuuid_fails_closed(self) -> None:
        plan = legacy_plan()
        runner = ScriptedProbeRunner(
            scripted_mbr_answers(partuuid_override={"system-b": "deadbeef-03"})
        )
        with self.assertRaisesRegex(LayoutError, "wrong-disk"):
            observe_legacy_mbr_identities(
                runner, target=disposable_target(), plan=plan
            )

    def test_cloned_filesystem_uuids_fail_closed(self) -> None:
        plan = legacy_plan()
        runner = ScriptedProbeRunner(
            scripted_mbr_answers(
                filesystem_uuids={
                    "system-a": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "system-b": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "persist": "cccccccc-dddd-eeee-ffff-000000000000",
                }
            )
        )
        with self.assertRaisesRegex(LayoutError, "cloned"):
            observe_legacy_mbr_identities(
                runner, target=disposable_target(), plan=plan
            )

    def test_missing_signature_and_non_mbr_value_fail_closed(self) -> None:
        plan = legacy_plan()
        runner = ScriptedProbeRunner(scripted_mbr_answers(drop_ptuuid=True))
        with self.assertRaises(LayoutError):
            observe_legacy_mbr_identities(
                runner, target=disposable_target(), plan=plan
            )
        runner = ScriptedProbeRunner(
            scripted_mbr_answers(
                partuuid_override={"system-a": "11111111-2222-3333-4444-555555555555"}
            )
        )
        with self.assertRaisesRegex(LayoutError, "not an MBR PARTUUID"):
            observe_legacy_mbr_identities(
                runner, target=disposable_target(), plan=plan
            )

    def test_foreign_plan_non_disk_and_deferred_adapters(self) -> None:
        plan = legacy_plan()
        runner = ScriptedProbeRunner(scripted_mbr_answers())
        modern_plan = adapter_for("modern-gpt-ab-v1").plan(
            device_size_bytes=DEVICE_BYTES,
            slot_bytes=SLOT_BYTES,
            persist_minimum_bytes=PERSIST_MINIMUM_BYTES,
        )
        with self.assertRaisesRegex(LayoutError, "legacy-bios-ab-v1"):
            observe_legacy_mbr_identities(
                runner, target=disposable_target(), plan=modern_plan
            )
        partition_target = disposable_target()
        object.__setattr__(partition_target, "device_type", "part")
        with self.assertRaisesRegex(LayoutError, "whole-disk"):
            observe_legacy_mbr_identities(
                runner, target=partition_target, plan=plan
            )
        self.assertEqual(runner.commands, [])
        # Semantic interface: legacy observes; GPT/Pi defer to their phases.
        observed = observe_partition_identities(
            runner, target=disposable_target(), plan=plan
        )
        self.assertEqual(observed["system-a"]["partuuid"], f"{_MBRSIGNATURE}-02")
        with self.assertRaisesRegex(LayoutError, "deferred"):
            observe_partition_identities(
                ScriptedProbeRunner({}), target=disposable_target(), plan=modern_plan
            )

    def test_topology_builder_needs_full_observation(self) -> None:
        plan = legacy_plan()
        runner = ScriptedProbeRunner(scripted_mbr_answers())
        observed = observe_legacy_mbr_identities(
            runner, target=disposable_target(), plan=plan
        )
        topology = build_observed_mbr_topology(
            plan=plan, target=disposable_target(), identities=observed
        )
        self.assertEqual(
            topology.by_role("system-a").partuuid, f"{_MBRSIGNATURE}-02"
        )
        self.assertEqual(topology.by_role("system-a").size_bytes, SLOT_BYTES)
        self.assertEqual(
            topology.by_role("persist").size_bytes, plan.remainder_bytes()
        )
        partial = dict(observed)
        del partial["persist"]
        with self.assertRaisesRegex(LayoutError, "must cover"):
            build_observed_mbr_topology(
                plan=plan, target=disposable_target(), identities=partial
            )

    def test_subprocess_runner_stays_array_only(self) -> None:
        runner = SubprocessMbrProbeRunner()
        result = runner.run(["true"])
        self.assertEqual(result.returncode, 0)
        with self.assertRaises(LayoutError):
            runner.run(["true; id"])
        with self.assertRaises(LayoutError):
            runner.run(["true", "$(id)"])


class DosTableParserTests(unittest.TestCase):
    def _table_bytes(
        self, *, signature: int = 0x9F3AC271, magic: bool = True
    ) -> bytes:
        table = bytearray(512)
        struct.pack_into("<I", table, 440, signature)
        entries = [
            (0x80, 0x83, 2048, 63488),  # p1 boot-control
            (0x00, 0x83, 65536, 2097152),  # p2 system-a
            (0x00, 0x83, 2162688, 2097152),  # p3 system-b
            (0x00, 0x83, 4259840, 12517376),  # p4 persist
        ]
        for index, (status, ptype, start, count) in enumerate(entries):
            struct.pack_into(
                "<B3sB3sII",
                table,
                446 + index * 16,
                status,
                b"\x00\x00\x00",
                ptype,
                b"\x00\x00\x00",
                start,
                count,
            )
        table[510] = 0x55 if magic else 0x00
        table[511] = 0xAA if magic else 0x00
        return bytes(table)

    def test_happy_path(self) -> None:
        observation = parse_dos_partition_table(self._table_bytes())
        self.assertIsInstance(observation, DosTableObservation)
        self.assertEqual(observation.disk_signature, "9f3ac271")
        self.assertEqual([p.number for p in observation.partitions], [1, 2, 3, 4])
        self.assertEqual(
            [p.partition_type for p in observation.partitions], [0x83] * 4
        )
        self.assertEqual(
            [p.bootable for p in observation.partitions],
            [True, False, False, False],
        )
        self.assertEqual(observation.partuuid_for(2), "9f3ac271-02")
        with self.assertRaises(LayoutError):
            observation.partuuid_for(5)

    def test_positive_control_break_restore(self) -> None:
        # Break the magic -> RED; restore the exact bytes -> GREEN. This
        # proves the parser reads the table instead of passing vacuously.
        good = self._table_bytes()
        self.assertEqual(parse_dos_partition_table(good).disk_signature, "9f3ac271")
        broken = bytearray(good)
        broken[510] = 0x00
        with self.assertRaisesRegex(LayoutError, "magic"):
            parse_dos_partition_table(bytes(broken))
        self.assertEqual(
            parse_dos_partition_table(good).disk_signature, "9f3ac271"
        )

    def test_zero_signature_empty_table_bad_status_fail_closed(self) -> None:
        with self.assertRaisesRegex(LayoutError, "not authoritative"):
            parse_dos_partition_table(self._table_bytes(signature=0))
        empty = bytearray(512)
        empty[510] = 0x55
        empty[511] = 0xAA
        struct.pack_into("<I", empty, 440, 0x9F3AC271)
        with self.assertRaisesRegex(LayoutError, "no partitions"):
            parse_dos_partition_table(bytes(empty))
        bad = bytearray(self._table_bytes())
        bad[446] = 0x7F
        with self.assertRaisesRegex(LayoutError, "status is invalid"):
            parse_dos_partition_table(bytes(bad))
        with self.assertRaises(LayoutError):
            parse_dos_partition_table(b"short")


def write_plan_matching_mbr(path: Path, *, signature: int, plan) -> None:
    """Write a real DOS MBR whose entries match the adapter plan extents."""
    from greia_installer.layout import adapter_for as _adapter_for

    adapter = _adapter_for(plan.adapter_id)
    extents = {
        partition.role: (start_mib, end_mib)
        for partition, start_mib, end_mib in adapter._mkpart_extents(plan)
    }
    total_sectors = DEVICE_BYTES // 512
    table = bytearray(512)
    struct.pack_into("<I", table, 440, signature)
    order = {"boot-control": 1, "system-a": 2, "system-b": 3, "persist": 4}
    for role, number in order.items():
        start_mib, end_mib = extents[role]
        start_lba = start_mib * 2048
        end_sectors = total_sectors if end_mib is None else end_mib * 2048
        count = end_sectors - start_lba
        assert count > 0
        struct.pack_into(
            "<B3sB3sII",
            table,
            446 + (number - 1) * 16,
            0x80 if number == 1 else 0x00,
            b"\x00\x00\x00",
            0x83,
            b"\x00\x00\x00",
            start_lba,
            count,
        )
    table[510] = 0x55
    table[511] = 0xAA
    with open(path, "r+b") as handle:
        handle.seek(0)
        handle.write(bytes(table))
        handle.flush()
        os.fsync(handle.fileno())


class FileBackedMbrImageProbeTests(unittest.TestCase):
    """Disposable genuinely-partitioned raw image probe (T1.1/T1.3).

    A sparse file carries a real DOS partition table whose entries match
    the legacy adapter's declarative extents; the production parser reads
    the signature + partition numbers back, the record persists to disk,
    all in-memory authority is dropped (teardown analogue), the record
    reloads from bytes (remount analogue) and A/B/PERSIST resolution is
    proven. Host ``sfdisk``/``blkid`` cross-checks run only where those
    tools exist; the byte-level proof always runs.
    """

    def _image_with_table(self, directory: str) -> tuple[Path, DosTableObservation]:
        image = Path(directory) / "disposable-mbr.img"
        with open(image, "wb") as handle:
            handle.truncate(DEVICE_BYTES)
        plan = legacy_plan()
        write_plan_matching_mbr(image, signature=int(_MBRSIGNATURE, 16), plan=plan)
        with open(image, "rb") as handle:
            observation = parse_dos_partition_table(handle.read(512))
        self.assertEqual(observation.disk_signature, _MBRSIGNATURE)
        self.assertEqual([p.number for p in observation.partitions], [1, 2, 3, 4])
        return image, observation

    def test_record_matches_real_table_topology(self) -> None:
        plan = legacy_plan()
        with tempfile.TemporaryDirectory() as directory:
            image, observation = self._image_with_table(directory)
            # Role-owned filesystem UUIDs (what mkfs would mint per role).
            filesystem_uuids = {
                role: str(uuid.uuid4()) for role in LEGACY_ROLES
            }
            self.assertEqual(len(set(filesystem_uuids.values())), 3)
            identities = {
                role: {
                    "filesystem_uuid": filesystem_uuids[role],
                    "partuuid": observation.partuuid_for(LEGACY_NUMBERS[role]),
                    "scheme": PARTITION_SCHEME_MBR_PARTUUID,
                }
                for role in LEGACY_ROLES
            }
            record = InstalledLayoutRecord.from_dict(mbr_record_dict(identities))
            # Persist the record, drop every in-memory handle (teardown
            # analogue), reload from bytes (remount analogue).
            record_path = Path(directory) / "installed-layout.json"
            record.write_to(record_path)
            del record, identities, filesystem_uuids
            gc.collect()
            reloaded = InstalledLayoutRecord.read_from(record_path)
            topology = build_observed_mbr_topology(
                plan=plan, target=disposable_target(), identities={
                    role: reloaded.system_a.as_dict()
                    if role == "system-a"
                    else reloaded.system_b.as_dict()
                    if role == "system-b"
                    else reloaded.persist.as_dict()
                    for role in LEGACY_ROLES
                },
            )
            signature = verify_mbr_topology_for_boot(
                reloaded, topology, expected_disk_signature=observation.disk_signature
            )
            self.assertEqual(signature, _MBRSIGNATURE)
            # Prove A/B/PERSIST resolution from the reloaded record.
            self.assertEqual(
                topology.by_role("system-a").partuuid,
                reloaded.system_a.partuuid,
            )
            self.assertEqual(
                topology.by_role("system-b").partuuid,
                reloaded.system_b.partuuid,
            )
            self.assertEqual(
                topology.by_role("persist").partuuid, reloaded.persist.partuuid
            )
            for role in ("system-a", "system-b", "persist"):
                self.assertEqual(
                    topology.by_role(role).scheme, PARTITION_SCHEME_MBR_PARTUUID
                )
            # The bound signature is the table's signature, not a mint.
            for identity in (
                reloaded.system_a,
                reloaded.system_b,
                reloaded.persist,
            ):
                assert identity is not None
                self.assertTrue(
                    identity.partuuid.startswith(f"{_MBRSIGNATURE}-")
                )
            self.assertFalse(image.is_symlink())

    def test_tool_path_cross_check_where_available(self) -> None:
        sfdisk = shutil.which("sfdisk")
        blkid = shutil.which("blkid")
        if sfdisk is None and blkid is None:
            self.skipTest("no sfdisk/blkid on this host; byte proof above stands")
        with tempfile.TemporaryDirectory() as directory:
            image, observation = self._image_with_table(directory)
            if sfdisk is not None:
                disk_id = subprocess.run(
                    [sfdisk, "--disk-id", str(image)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(disk_id.returncode, 0)
                self.assertEqual(
                    require_mbr_disk_signature(
                        disk_id.stdout.strip(), field="disk signature"
                    ),
                    observation.disk_signature,
                )
                part2 = subprocess.run(
                    [sfdisk, "--part-uuid", str(image), "2"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(part2.returncode, 0)
                self.assertEqual(
                    part2.stdout.strip().lower(), observation.partuuid_for(2)
                )
            if blkid is not None:
                probed = subprocess.run(
                    [blkid, "-p", "-s", "PTUUID", "-o", "value", str(image)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(probed.returncode, 0)
                self.assertEqual(
                    require_mbr_disk_signature(
                        probed.stdout.strip(), field="disk signature"
                    ),
                    observation.disk_signature,
                )


class NegativeBindingTests(unittest.TestCase):
    def _bound(self) -> tuple[InstalledLayoutRecord, BlockTopology]:
        plan = legacy_plan()
        runner = ScriptedProbeRunner(scripted_mbr_answers())
        observed = observe_legacy_mbr_identities(
            runner, target=disposable_target(), plan=plan
        )
        record = InstalledLayoutRecord.from_dict(mbr_record_dict(observed))
        topology = build_observed_mbr_topology(
            plan=plan, target=disposable_target(), identities=observed
        )
        return record, topology

    def test_wrong_disk_signature_fails_closed(self) -> None:
        record, _ = self._bound()
        plan = legacy_plan()
        other = ScriptedProbeRunner(
            scripted_mbr_answers(signature="deadbeef")
        )
        other_observed = observe_legacy_mbr_identities(
            other, target=disposable_target(), plan=plan
        )
        other_topology = build_observed_mbr_topology(
            plan=plan, target=disposable_target(), identities=other_observed
        )
        with self.assertRaisesRegex(PersistentLayoutError, "disk signature"):
            validate_layout_against_topology(record, other_topology)
        with self.assertRaisesRegex(PersistentLayoutError, "disk signature"):
            require_mbr_topology_binding(record, other_topology)
        with self.assertRaisesRegex(LayoutError, "[Dd]isk signature"):
            verify_mbr_topology_for_boot(
                record, other_topology, expected_disk_signature="deadbeef"
            )

    def test_swapped_partitions_fail_closed(self) -> None:
        record, topology = self._bound()
        facts = {fact.role: fact for fact in topology.partitions}
        swapped = BlockTopology(
            partitions=(
                PartitionFact.create(
                    role="system-a",
                    scheme=facts["system-a"].scheme,
                    partuuid=facts["system-b"].partuuid,
                    filesystem_uuid=facts["system-b"].filesystem_uuid,
                    size_bytes=SLOT_BYTES,
                    disk_id="loop99",
                ),
                PartitionFact.create(
                    role="system-b",
                    scheme=facts["system-b"].scheme,
                    partuuid=facts["system-a"].partuuid,
                    filesystem_uuid=facts["system-a"].filesystem_uuid,
                    size_bytes=SLOT_BYTES,
                    disk_id="loop99",
                ),
                facts["persist"],
            )
        )
        with self.assertRaisesRegex(PersistentLayoutError, "swapped"):
            validate_layout_against_topology(record, swapped)

    def test_cloned_filesystem_uuids_fail_closed(self) -> None:
        record, _ = self._bound()
        plan = legacy_plan()
        cloned_identities = {
            role: {
                "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "partuuid": record.system_a.partuuid
                if role == "system-a"
                else record.system_b.partuuid
                if role == "system-b"
                else record.persist.partuuid,
                "scheme": PARTITION_SCHEME_MBR_PARTUUID,
            }
            for role in LEGACY_ROLES
        }
        # Cloned filesystem UUIDs cannot even form a record...
        with self.assertRaisesRegex(PersistentLayoutError, "must be unique"):
            InstalledLayoutRecord.from_dict(mbr_record_dict(cloned_identities))
        # ...nor an observed topology.
        with self.assertRaises(LayoutError):
            build_observed_mbr_topology(
                plan=plan, target=disposable_target(), identities=cloned_identities
            )
        # A cloned filesystem UUID smuggled into one role cannot even
        # form a topology: the duplicate-identity gate fires first.
        base = {fact.role: fact for fact in self._bound()[1].partitions}
        with self.assertRaisesRegex(PersistentLayoutError, "duplicate"):
            BlockTopology(
                partitions=(
                    base["system-a"],
                    PartitionFact.create(
                        role="system-b",
                        scheme=base["system-b"].scheme,
                        partuuid=base["system-b"].partuuid,
                        filesystem_uuid=base["system-a"].filesystem_uuid,
                        size_bytes=base["system-b"].size_bytes,
                        disk_id=base["system-b"].disk_id,
                    ),
                    base["persist"],
                )
            )

    def test_scheme_mismatch_fails_closed(self) -> None:
        record, topology = self._bound()
        gpt_fact = PartitionFact.create(
            role="system-a",
            scheme=PARTITION_SCHEME_GPT_GUID,
            partuuid="11111111-2222-3333-4444-555555555555",
            filesystem_uuid=topology.by_role("system-a").filesystem_uuid,
            size_bytes=SLOT_BYTES,
            disk_id="loop99",
        )
        mixed = BlockTopology(
            partitions=(
                gpt_fact,
                topology.by_role("system-b"),
                topology.by_role("persist"),
            )
        )
        with self.assertRaisesRegex(PersistentLayoutError, "scheme"):
            validate_layout_against_topology(record, mixed)

    def test_minted_uuid4_never_binds_as_mbr(self) -> None:
        # The fabrication this task removes: a fresh UUID4 labeled as an
        # MBR PARTUUID must fail at every gate, not just one.
        minted = mint_fresh_partition_identities()
        with self.assertRaises(PersistentLayoutError):
            normalize_mbr_partuuid(
                minted["system-a"]["partuuid"], field="partuuid"
            )
        fake_mbr = {
            role: {
                "filesystem_uuid": minted[role]["filesystem_uuid"],
                "partuuid": minted[role]["partuuid"],
                "scheme": PARTITION_SCHEME_MBR_PARTUUID,
            }
            for role in LEGACY_ROLES
        }
        with self.assertRaises(PersistentLayoutError):
            InstalledLayoutRecord.from_dict(mbr_record_dict(fake_mbr))


class AdapterBoundaryTests(unittest.TestCase):
    _MBR_HELPERS = (
        "normalize_mbr_partuuid",
        "require_mbr_disk_signature",
        "split_mbr_partuuid",
        "probe_mbr_partition_partuuid",
        "read_mbr_disk_signature",
        "observe_legacy_mbr_identities",
        "parse_dos_partition_table",
        "DosTableObservation",
        "MbrProbeRunner",
        "build_observed_mbr_topology",
        "verify_mbr_topology_for_boot",
    )

    def test_gpt_and_pi_adapters_carry_no_mbr_parsing(self) -> None:
        # Per-adapter parsing: GPT (8C) and Pi (8D) implement their own
        # observation rules behind observe_partition_identities; MBR
        # parsing must never leak into them.
        for adapter_id in ("modern-gpt-ab-v1", "pi-mbr-tryboot-ab-v1"):
            with self.subTest(adapter=adapter_id):
                source = inspect.getsource(adapter_for(adapter_id).__class__)
                for helper in self._MBR_HELPERS:
                    self.assertNotIn(
                        helper,
                        source,
                        f"{adapter_id} must not import MBR parsing ({helper})",
                    )


if __name__ == "__main__":
    unittest.main()
