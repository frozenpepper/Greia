from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from support_artifacts import valid_hardware_support_archive_bytes

from greia_platform import persistent_layout as persist
from greia_platform.persistent_layout import (
    AB_LAYOUT_ADAPTERS,
    ALLOWED_BOOT_BACKENDS,
    ALLOWED_LAYOUT_ADAPTERS,
    ALLOWED_PLATFORM_FAMILIES,
    DURABLE_PATH_AUDIT,
    LAYOUT_BIND_ORDER,
    LAYOUT_RECORD_MODE,
    MAX_SYSTEM_SLOT_BYTES,
    MIN_PERSIST_BYTES,
    MIN_SYSTEM_SLOT_BYTES,
    NAMESPACE_MAP_SCHEMA_VERSION,
    PERSISTENT_NAMESPACE_ORDER,
    PERSIST_SCHEMA_MARKER_NAME,
    BlockTopology,
    Durability,
    InstalledLayoutRecord,
    MountKind,
    PartitionFact,
    PersistRecoveryRequired,
    PersistentLayoutError,
    PersistentNamespaceMap,
    assert_persistent_contract_accepted,
    build_namespace_map,
    emit_persistent_state_contract,
    find_audit_entry,
    fresh_initialize_persist,
    open_existing_persist,
    read_partuuid_map,
    read_persist_schema_marker,
    persist_record_path,
    persist_mount_source_path,
    persist_schema_marker_path,
    validate_layout_against_topology,
    verify_host_mount_targets,
)
from greia_platform.system_updates import (
    _PERSISTENT_NAMESPACES,
    build_update_bundle,
    inspect_update_bundle,
    verify_persistent_state_contract_bytes,
)

HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "modern-gpt-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": 1024 * 1024 * 1024,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _record(**overrides: object) -> InstalledLayoutRecord:
    return InstalledLayoutRecord.from_dict(_record_dict(**overrides))


def _topology(
    *,
    slot_bytes: int = 1024 * 1024 * 1024,
    persist_bytes: int = MIN_PERSIST_BYTES,
    disk: str = "disk0",
    single: bool = False,
) -> BlockTopology:
    facts = [
        PartitionFact.create(
            role="system-a",
            partuuid=_UUID_A,
            filesystem_uuid=_UUID_A_FS,
            size_bytes=slot_bytes,
            disk_id=disk,
        ),
        PartitionFact.create(
            role="persist",
            partuuid=_UUID_P,
            filesystem_uuid=_UUID_P_FS,
            size_bytes=persist_bytes,
            disk_id=disk,
        ),
    ]
    if not single:
        facts.insert(
            1,
            PartitionFact.create(
                role="system-b",
                partuuid=_UUID_B,
                filesystem_uuid=_UUID_B_FS,
                size_bytes=slot_bytes,
                disk_id=disk,
            ),
        )
    return BlockTopology(partitions=tuple(facts))


class AuthoritySyncTests(unittest.TestCase):
    def _load_build_profile_module(self):  # noqa: ANN202
        import sys

        repo_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "build_profile_authority", repo_root / "tools" / "build_profile.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            del sys.modules[spec.name]
        return module

    def test_identifier_sets_match_l7_profiles_authority(self) -> None:
        authority = self._load_build_profile_module()
        self.assertEqual(set(ALLOWED_LAYOUT_ADAPTERS), set(authority._ALLOWED_LAYOUT_ADAPTERS))
        self.assertEqual(set(AB_LAYOUT_ADAPTERS), set(authority._AB_LAYOUT_ADAPTERS))
        self.assertEqual(set(ALLOWED_BOOT_BACKENDS), set(authority._ALLOWED_BOOT_BACKENDS))
        self.assertEqual(
            set(ALLOWED_PLATFORM_FAMILIES), set(authority._ALLOWED_PLATFORM_FAMILIES)
        )
        self.assertEqual(MIN_SYSTEM_SLOT_BYTES, authority._MIN_SYSTEM_SLOT_BYTES)
        self.assertEqual(MAX_SYSTEM_SLOT_BYTES, authority._MAX_SYSTEM_SLOT_BYTES)
        self.assertEqual(MIN_PERSIST_BYTES, authority._MIN_PERSISTENT_BYTES)

    def test_namespace_order_matches_release_contract_authority(self) -> None:
        self.assertEqual(tuple(_PERSISTENT_NAMESPACES), PERSISTENT_NAMESPACE_ORDER)


class AuditTests(unittest.TestCase):
    def test_no_bare_filesystem_persistence(self) -> None:
        bare = {"/", "/var", "/etc", "/run", "/tmp", "/opt", "/usr", "/boot"}
        for entry in DURABLE_PATH_AUDIT:
            if entry.mount not in (MountKind.BIND_DIR, MountKind.BIND_FILE):
                continue
            target = entry.path
            self.assertNotIn(target, bare, f"bare persistence: {target}")
            depth = len([part for part in target.split("/") if part])
            if entry.mount == MountKind.BIND_DIR:
                self.assertGreaterEqual(depth, 3, f"bind-dir too broad: {target}")
            else:
                self.assertGreaterEqual(depth, 2, f"bind-file too broad: {target}")

    def test_no_duplicate_mounted_targets(self) -> None:
        mounted = [
            entry.path
            for entry in DURABLE_PATH_AUDIT
            if entry.mount in (MountKind.BIND_DIR, MountKind.BIND_FILE)
        ]
        self.assertEqual(len(set(mounted)), len(mounted))

    def test_brief_domains_are_all_classified(self) -> None:
        probes = {
            # child profiles + Activity data + progression + Parent state
            "/var/lib/greia-profiles": (Durability.PERSISTENT_SHARED, "child-profiles"),
            "/var/lib/greia-profiles/profiles.json": (
                Durability.PERSISTENT_SHARED,
                "child-profiles",
            ),
            "/var/lib/greia-profiles/usage-limits.json": (
                Durability.PERSISTENT_SHARED,
                "child-profiles",
            ),
            "/var/lib/greia-profiles/data/abc123/storage/org.example.game": (
                Durability.PERSISTENT_SHARED,
                "activity-saves",
            ),
            "/var/lib/greia-profiles/data/abc123/progress": (
                Durability.PERSISTENT_SHARED,
                "progression-rewards",
            ),
            "/var/lib/greia-os/parent-devices.json": (
                Durability.PERSISTENT_SHARED,
                "parent-credentials",
            ),
            "/var/lib/greia-os/main-credential.json": (
                Durability.PERSISTENT_SHARED,
                "parent-credentials",
            ),
            # activation state
            "/var/lib/greia-os/activity-packages": (
                Durability.PERSISTENT_SHARED,
                "activity-activation",
            ),
            # device/hardware settings + language
            "/var/lib/greia-system-settings": (
                Durability.PERSISTENT_SHARED,
                "device-settings",
            ),
            # network state
            "/var/lib/iwd": (Durability.PERSISTENT_SHARED, "network-state"),
            # machine identity
            "/etc/machine-id": (Durability.PERSISTENT_SHARED, "machine-identity"),
            # update inbox/status
            "/var/lib/greia-os/system-updates/inbox": (
                Durability.PERSISTENT_SHARED,
                "update-acceptance-state",
            ),
            # developer state
            "/var/lib/greia-developer": (
                Durability.PERSISTENT_SHARED,
                "developer-state",
            ),
            "/var/lib/greia-admin/greia-dev-upload": (
                Durability.PERSISTENT_SHARED,
                "developer-state",
            ),
            # logs/evidence staging (bounded, reserved)
            "/var/lib/greia-os/diagnostics": (
                Durability.PERSISTENT_SHARED,
                "bounded-logs",
            ),
            # first-boot markers
            "/var/lib/greia-os/initialized": (
                Durability.PERSISTENT_SHARED,
                "update-acceptance-state",
            ),
            "/var/lib/greia-os/migrations": (
                Durability.PERSISTENT_SHARED,
                "update-acceptance-state",
            ),
            # layout authority directory and its atomic record file
            "/etc/greia-os/layout": (
                Durability.PERSISTENT_SHARED,
                "layout-authority",
            ),
            "/etc/greia-os/layout/installed-layout.json": (
                Durability.PERSISTENT_SHARED,
                "layout-authority",
            ),
            # slot-local install evidence
            "/etc/greia-os/install-record.json": (Durability.SLOT_LOCAL, None),
            "/opt/greia-os": (Durability.SLOT_LOCAL, None),
            # volatile runtime
            "/run/greia-os/active-profile.json": (Durability.VOLATILE, None),
            "/tmp": (Durability.VOLATILE, None),
            "/media/greia": (Durability.VOLATILE, None),
            # restore-only copies
            "/var/lib/greia-profiles/profiles.backup.json": (
                Durability.BACKUP_ONLY,
                "child-profiles",
            ),
            "/media/greia/backup-1.greiabackup": (Durability.BACKUP_ONLY, None),
        }
        for path, (durability, namespace) in probes.items():
            with self.subTest(path=path):
                entry = find_audit_entry(path)
                self.assertIsNotNone(entry, f"unclassified durable path: {path}")
                assert entry is not None
                self.assertEqual(entry.durability, durability)
                self.assertEqual(entry.namespace, namespace)

    def test_unclassified_identity_path_blocks_migration(self) -> None:
        for path in (
            "/var/lib/greia-future-service/state.json",
            "/etc/greia-os/unknown-flag",
            "/var/lib/greia-os-unrelated",
        ):
            with self.subTest(path=path):
                self.assertIsNone(find_audit_entry(path))

    def test_shared_entries_have_registered_namespaces(self) -> None:
        for entry in DURABLE_PATH_AUDIT:
            if entry.durability != Durability.PERSISTENT_SHARED:
                continue
            self.assertIsNotNone(entry.namespace)
            assert entry.namespace is not None
            self.assertIn(entry.namespace, PERSISTENT_NAMESPACE_ORDER)

    def test_every_namespace_is_grounded(self) -> None:
        grounded = {
            entry.namespace
            for entry in DURABLE_PATH_AUDIT
            if entry.durability == Durability.PERSISTENT_SHARED and entry.namespace
        }
        self.assertEqual(grounded, set(PERSISTENT_NAMESPACE_ORDER))


class NamespaceMapTests(unittest.TestCase):
    def test_mount_plan_is_deterministic_and_layout_first(self) -> None:
        namespace_map = build_namespace_map()
        self.assertEqual(namespace_map.schema_version, NAMESPACE_MAP_SCHEMA_VERSION)
        self.assertEqual(tuple(namespace_map.namespaces), PERSISTENT_NAMESPACE_ORDER)
        plan = namespace_map.mount_plan()
        orders = [item.order for item in plan]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(plan[0].target, "/etc/greia-os/layout")
        self.assertEqual(plan[0].order, LAYOUT_BIND_ORDER)
        # rebuild is byte-identical
        self.assertEqual(build_namespace_map().as_dict(), namespace_map.as_dict())

    def test_path_escape_is_rejected(self) -> None:
        with self.assertRaises(PersistentLayoutError):
            persist._check_canonical_target("/var/lib/../etc/x")
        with self.assertRaises(PersistentLayoutError):
            persist._check_canonical_target("relative/path")
        with self.assertRaises(PersistentLayoutError):
            persist._check_canonical_target("/var/lib/greia-os/*")

    def test_host_symlink_rejected(self) -> None:
        namespace_map = build_namespace_map()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "var" / "lib").mkdir(parents=True)
            os.symlink("/tmp", root / "var" / "lib" / "greia-profiles")
            with self.assertRaises(PersistentLayoutError):
                verify_host_mount_targets(namespace_map, root)

    def test_host_clean_tree_passes(self) -> None:
        namespace_map = build_namespace_map()
        with tempfile.TemporaryDirectory() as directory:
            verify_host_mount_targets(namespace_map, Path(directory))


class LayoutRecordTests(unittest.TestCase):
    def test_canonical_round_trip(self) -> None:
        record = _record()
        raw = record.canonical_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(raw, persist._canonical_bytes(json.loads(raw.decode("utf-8"))))
        self.assertEqual(InstalledLayoutRecord.from_dict(json.loads(raw)).canonical_bytes(), raw)

    def test_write_enforces_owner_only_mode(self) -> None:
        record = _record()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installed-layout.json"
            record.write_to(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), LAYOUT_RECORD_MODE)
            self.assertEqual(InstalledLayoutRecord.read_from(path), record)

    def test_symlink_is_rejected(self) -> None:
        record = _record()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real.json"
            record.write_to(real)
            link = root / "link.json"
            os.symlink(real, link)
            with self.assertRaises(PersistentLayoutError):
                InstalledLayoutRecord.read_from(link)

    def test_non_canonical_bytes_rejected(self) -> None:
        record = _record()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installed-layout.json"
            path.write_bytes(json.dumps(record.as_dict(), separators=(",", ":")).encode())
            os.chmod(path, 0o600)
            with self.assertRaisesRegex(PersistentLayoutError, "canonical"):
                InstalledLayoutRecord.read_from(path)

    def test_wrong_mode_rejected(self) -> None:
        record = _record()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installed-layout.json"
            path.write_bytes(record.canonical_bytes())
            os.chmod(path, 0o644)
            with self.assertRaisesRegex(PersistentLayoutError, "0600"):
                InstalledLayoutRecord.read_from(path)

    def test_expect_uid_enforced(self) -> None:
        record = _record()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installed-layout.json"
            record.write_to(path)
            with self.assertRaisesRegex(PersistentLayoutError, "ownership"):
                InstalledLayoutRecord.read_from(path, expect_uid=os.geteuid() + 1)
            self.assertEqual(
                InstalledLayoutRecord.read_from(path, expect_uid=os.geteuid()), record
            )

    def test_parent_controlled_and_device_fields_rejected(self) -> None:
        for extra in (
            {"device_path": "/dev/sda3"},
            {"parent_approved": True},
            {"slot_device": "/dev/disk/by-partuuid/abc"},
        ):
            with self.subTest(extra=extra):
                raw = _record_dict()
                raw.update(extra)
                with self.assertRaisesRegex(
                    PersistentLayoutError, "non-authoritative"
                ):
                    InstalledLayoutRecord.from_dict(raw)

    def test_malformed_records_rejected(self) -> None:
        cases = [
            _record_dict(schema_version=2),
            _record_dict(layout_id="nope"),
            _record_dict(boot_backend="grub-ab-v1", layout_id="bios-single-ext4",
                          boot_control={"active_slot": None, "kind": "grub-env-v1"},
                          accepted_slot=None, system_b=None),
            _record_dict(system_b=None),  # A/B requires system_b
            _record_dict(layout_id="bios-single-ext4", boot_backend="none-v1",
                          boot_control={"active_slot": None, "kind": "none-v1"},
                          accepted_slot=None),  # system_b present on single
            _record_dict(system_b={"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_A}),
            _record_dict(platform_family="arm64"),  # x86 layout, ARM family
            _record_dict(slot_bytes=128 * 1024 * 1024),
            _record_dict(accepted_release_id=""),
            _record_dict(system_a={"filesystem_uuid": _UUID_A_FS, "partuuid": "not-a-uuid"}),
            _record_dict(install_target_sha256="xyz"),
        ]
        for raw in cases:
            with self.subTest(raw=raw.get("layout_id"), extra=sorted(raw)):
                with self.assertRaises(PersistentLayoutError):
                    InstalledLayoutRecord.from_dict(raw)

    def test_missing_field_rejected(self) -> None:
        raw = _record_dict()
        del raw["persist"]
        with self.assertRaisesRegex(PersistentLayoutError, "missing"):
            InstalledLayoutRecord.from_dict(raw)


class TopologyTests(unittest.TestCase):
    def test_happy_paths(self) -> None:
        validate_layout_against_topology(_record(), _topology())
        single = _record(
            layout_id="bios-single-ext4",
            boot_backend="none-v1",
            platform_family="legacy-x86",
            boot_control={"active_slot": None, "kind": "none-v1"},
            accepted_slot=None,
            system_b=None,
        )
        validate_layout_against_topology(single, _topology(single=True))

    def test_swapped_slots_detected(self) -> None:
        record = _record()
        swapped = BlockTopology(
            partitions=(
                PartitionFact.create(
                    role="system-a", partuuid=_UUID_B, filesystem_uuid=_UUID_B_FS,
                    size_bytes=record.slot_bytes, disk_id="disk0",
                ),
                PartitionFact.create(
                    role="system-b", partuuid=_UUID_A, filesystem_uuid=_UUID_A_FS,
                    size_bytes=record.slot_bytes, disk_id="disk0",
                ),
                PartitionFact.create(
                    role="persist", partuuid=_UUID_P, filesystem_uuid=_UUID_P_FS,
                    size_bytes=MIN_PERSIST_BYTES, disk_id="disk0",
                ),
            )
        )
        with self.assertRaisesRegex(PersistentLayoutError, "swapped"):
            validate_layout_against_topology(record, swapped)

    def test_missing_partition_detected(self) -> None:
        record = _record()
        topology = BlockTopology(
            partitions=tuple(f for f in _topology().partitions if f.role != "persist")
        )
        with self.assertRaisesRegex(PersistentLayoutError, "missing partition"):
            validate_layout_against_topology(record, topology)

    def test_duplicate_uuids_rejected(self) -> None:
        with self.assertRaisesRegex(PersistentLayoutError, "duplicate"):
            BlockTopology(
                partitions=(
                    PartitionFact.create(
                        role="system-a", partuuid=_UUID_A, filesystem_uuid=_UUID_A_FS,
                        size_bytes=1024**3, disk_id="disk0",
                    ),
                    PartitionFact.create(
                        role="persist", partuuid=_UUID_A, filesystem_uuid=_UUID_P_FS,
                        size_bytes=MIN_PERSIST_BYTES, disk_id="disk0",
                    ),
                )
            )
        with self.assertRaisesRegex(PersistentLayoutError, "duplicate"):
            BlockTopology(
                partitions=(
                    PartitionFact.create(
                        role="system-a", partuuid=_UUID_A, filesystem_uuid=_UUID_A_FS,
                        size_bytes=1024**3, disk_id="disk0",
                    ),
                    PartitionFact.create(
                        role="system-a", partuuid=_UUID_B, filesystem_uuid=_UUID_B_FS,
                        size_bytes=1024**3, disk_id="disk0",
                    ),
                )
            )

    def test_wrong_ancestry_detected(self) -> None:
        topology = _topology()
        moved = BlockTopology(
            partitions=tuple(
                replace(fact, disk_id="disk1") if fact.role == "persist" else fact
                for fact in topology.partitions
            )
        )
        with self.assertRaisesRegex(PersistentLayoutError, "ancestry"):
            validate_layout_against_topology(_record(), moved)

    def test_changed_capacity_detected(self) -> None:
        record = _record()
        with self.assertRaisesRegex(PersistentLayoutError, "capacity"):
            validate_layout_against_topology(record, _topology(slot_bytes=record.slot_bytes - 1))
        with self.assertRaisesRegex(PersistentLayoutError, "capacity"):
            validate_layout_against_topology(record, _topology(persist_bytes=MIN_PERSIST_BYTES - 1))

    def test_identity_mismatch_detected(self) -> None:
        record = _record()
        topology = _topology()
        other_uuid = "44444444-5555-6666-7777-888888888888"
        wrong = BlockTopology(
            partitions=tuple(
                replace(fact, partuuid=other_uuid) if fact.role == "system-a" else fact
                for fact in topology.partitions
            )
        )
        with self.assertRaisesRegex(PersistentLayoutError, "system-a PARTUUID"):
            validate_layout_against_topology(record, wrong)

    def test_unexpected_role_on_single_root(self) -> None:
        single = _record(
            layout_id="bios-single-ext4",
            boot_backend="none-v1",
            platform_family="legacy-x86",
            boot_control={"active_slot": None, "kind": "none-v1"},
            accepted_slot=None,
            system_b=None,
        )
        with self.assertRaisesRegex(PersistentLayoutError, "unexpected"):
            validate_layout_against_topology(single, _topology())

    def test_device_paths_never_authority(self) -> None:
        with self.assertRaisesRegex(PersistentLayoutError, "never a device path"):
            PartitionFact.create(
                role="system-a", partuuid="/dev/sda3", filesystem_uuid=_UUID_A_FS,
                size_bytes=1024**3, disk_id="disk0",
            )

    def test_partuuid_map_reader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os.symlink("../../sda3", root / _UUID_A)
            mapping = read_partuuid_map(root)
            self.assertEqual(mapping, {_UUID_A: "sda3"})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "plain-file").write_text("x")
            with self.assertRaises(PersistentLayoutError):
                read_partuuid_map(root)


class PersistLifecycleTests(unittest.TestCase):
    def _init(self, root: Path) -> tuple[InstalledLayoutRecord, PersistentNamespaceMap]:
        namespace_map = build_namespace_map()
        record = _record()
        fresh_initialize_persist(root, record, namespace_map)
        return record, namespace_map

    def test_fresh_init_mints_each_namespace_and_places_record_in_layout_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            namespace_map = build_namespace_map()
            state = fresh_initialize_persist(root, _record(), namespace_map)
            namespaces_root = state / "namespaces"
            created = sorted(p.name for p in namespaces_root.iterdir())
            self.assertEqual(created, sorted(namespace_map.namespaces))
            for child in namespaces_root.iterdir():
                self.assertTrue(child.is_dir())
                expected = {
                    "layout-authority": ["installed-layout.json"],
                    "machine-identity": ["machine-id"],
                }.get(child.name, [])
                self.assertEqual(sorted(path.name for path in child.iterdir()), expected)
            # Layout authority lives inside its directory bind and remains
            # atomically replaceable from either installed slot.
            record_path = persist_record_path(root)
            self.assertEqual(stat.S_IMODE(record_path.stat().st_mode), 0o600)
            contract_raw = (state / "persistent-state-contract.json").read_bytes()
            verify_persistent_state_contract_bytes(contract_raw)
            marker_path = persist_schema_marker_path(root)
            marker_raw = marker_path.read_bytes()
            self.assertEqual(marker_path.name, PERSIST_SCHEMA_MARKER_NAME)
            self.assertEqual(persist.parse_persist_schema_marker(marker_raw), 1)
            self.assertEqual(
                marker_raw, persist.emit_persist_schema_marker(1)
            )
            # second fresh init never re-mints
            with self.assertRaisesRegex(PersistentLayoutError, "already exists"):
                fresh_initialize_persist(root, _record(), namespace_map)

    def test_layout_authority_directory_bind_tracks_atomic_record_replacement(self) -> None:
        from greia_platform.fstab import PERSIST_BOOT_MOUNTPOINT, render_fstab

        with tempfile.TemporaryDirectory() as directory:
            persist_root = Path(directory)
            record = _record()
            namespace_map = build_namespace_map()
            fresh_initialize_persist(persist_root, record, namespace_map)
            layout_mount = next(
                mount
                for mount in namespace_map.mount_plan()
                if mount.target == "/etc/greia-os/layout"
            )
            self.assertEqual(layout_mount.kind, MountKind.BIND_DIR)
            source = persist_mount_source_path(persist_root, layout_mount)
            backing_record = persist_record_path(persist_root)
            self.assertEqual(backing_record.parent, source)

            # Both slot fstab plans bind the same directory source. Atomic
            # os.replace in InstalledLayoutRecord.write_to therefore changes
            # the record visible at the canonical path in either slot.
            fstab_sources = []
            for root_uuid in (_UUID_A_FS, _UUID_B_FS):
                rendered = render_fstab(
                    root_uuid,
                    persist_filesystem_uuid=_UUID_P_FS,
                    boot_control_filesystem_uuid="dddddddd-eeee-ffff-0000-111111111111",
                )
                rows = [
                    line.split()
                    for line in rendered.splitlines()
                    if line.split() and line.split()[1] == layout_mount.target
                ]
                self.assertEqual(len(rows), 1)
                self.assertEqual(
                    rows[0][2:4],
                    [
                        "none",
                        "bind,x-systemd.requires-mounts-for=/run/greia-persist",
                    ],
                )
                fstab_sources.append(Path(rows[0][0]))
            canonical_source = (
                Path(PERSIST_BOOT_MOUNTPOINT)
                / "greia"
                / "namespaces"
                / "layout-authority"
            )
            self.assertEqual(fstab_sources, [canonical_source, canonical_source])
            mapped_sources = [
                persist_root / path.relative_to(PERSIST_BOOT_MOUNTPOINT)
                for path in fstab_sources
            ]
            self.assertEqual(mapped_sources, [source, source])

            advanced = replace(
                record,
                accepted_slot="B",
                accepted_release_id="greia-0.15.0",
            )
            advanced.write_to(backing_record)
            for mounted_source in mapped_sources:
                visible_record = InstalledLayoutRecord.read_from(
                    mounted_source / "installed-layout.json",
                    expect_uid=os.geteuid(),
                )
                self.assertEqual(visible_record.accepted_slot, "B")
                self.assertEqual(
                    visible_record.accepted_release_id, "greia-0.15.0"
                )

    def test_fresh_init_refuses_preexisting_schema_marker_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker_path = persist_schema_marker_path(root)
            marker_path.parent.mkdir(parents=True)
            original = persist.emit_persist_schema_marker(7)
            marker_path.write_bytes(original)
            with self.assertRaisesRegex(PersistentLayoutError, "schema marker already exists"):
                fresh_initialize_persist(root, _record(), build_namespace_map())
            self.assertEqual(marker_path.read_bytes(), original)

    def test_schema_marker_reader_is_bounded_canonical_and_no_follow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker_path = root / "persist-schema.json"
            with self.assertRaisesRegex(PersistentLayoutError, "missing"):
                read_persist_schema_marker(marker_path)

            marker_path.write_bytes(persist.emit_persist_schema_marker(1))
            self.assertEqual(read_persist_schema_marker(marker_path),
                             persist.emit_persist_schema_marker(1))

            marker_path.write_bytes(b'{ "schema_version": 1 }\n')
            with self.assertRaisesRegex(PersistentLayoutError, "canonical"):
                read_persist_schema_marker(marker_path)

            marker_path.write_bytes(b" " * (persist.MAX_PERSIST_SCHEMA_MARKER_BYTES + 1))
            with self.assertRaisesRegex(PersistentLayoutError, "exceeds Greia bound"):
                read_persist_schema_marker(marker_path)

            marker_path.unlink()
            target = root / "target"
            target.write_bytes(persist.emit_persist_schema_marker(1))
            marker_path.symlink_to(target)
            with self.assertRaisesRegex(PersistentLayoutError, "unreadable"):
                read_persist_schema_marker(marker_path)

    def test_open_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self._init(root)
            opened, namespace_map = open_existing_persist(root, _topology())
            self.assertEqual(opened, record)
            self.assertEqual(tuple(namespace_map.namespaces), PERSISTENT_NAMESPACE_ORDER)

    def test_missing_persist_fails_to_recovery_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "empty"
            root.mkdir()
            before = list(root.iterdir())
            with self.assertRaises(PersistRecoveryRequired):
                open_existing_persist(root, _topology())
            self.assertEqual(list(root.iterdir()), before)

    def test_corrupt_record_fails_to_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._init(root)
            record_path = root / "greia" / "namespaces" / "layout-authority" / "installed-layout.json"
            record_path.write_bytes(b"{not json")
            os.chmod(record_path, 0o600)
            with self.assertRaises(PersistRecoveryRequired):
                open_existing_persist(root, _topology())

    def test_topology_mismatch_fails_to_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._init(root)
            topology = _topology()
            split = BlockTopology(
                partitions=tuple(
                    replace(fact, disk_id="disk1") if fact.role == "persist" else fact
                    for fact in topology.partitions
                )
            )
            with self.assertRaises(PersistRecoveryRequired):
                open_existing_persist(root, split)

    def test_missing_namespace_fails_to_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._init(root)
            import shutil

            shutil.rmtree(root / "greia" / "namespaces" / "network-state")
            with self.assertRaisesRegex(PersistRecoveryRequired, "namespace is missing"):
                open_existing_persist(root, _topology())


class ContractTests(unittest.TestCase):
    def test_registry_contract_is_canonical_and_boundable(self) -> None:
        namespace_map = build_namespace_map()
        raw = emit_persistent_state_contract(namespace_map)
        parsed = verify_persistent_state_contract_bytes(raw)
        self.assertEqual(parsed["namespaces"], list(PERSISTENT_NAMESPACE_ORDER))
        self.assertEqual(raw, emit_persistent_state_contract(build_namespace_map()))

    def test_emission_requires_registered_order(self) -> None:
        namespace_map = build_namespace_map()
        shuffled = PersistentNamespaceMap(
            schema_version=namespace_map.schema_version,
            namespaces=tuple(reversed(namespace_map.namespaces)),
            mounts=namespace_map.mounts,
        )
        with self.assertRaises(PersistentLayoutError):
            emit_persistent_state_contract(shuffled)

    def test_persist_schema_bound_into_v3_release_and_consumed(self) -> None:
        from greia_platform.persistent_layout import emit_persist_schema_marker

        namespace_map = build_namespace_map()
        contract_raw = emit_persistent_state_contract(namespace_map)
        # The installed PERSIST marker is the canonical schema document;
        # the v3 bundle carries only the readable range.
        installed_marker = emit_persist_schema_marker(1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"\x28\xb5\x2f\xfd" + b"slot-image" * 128
            payload_path = root / "payload.ext4.zst"
            payload_path.write_bytes(payload)
            hw_path = root / "hw.tar.zst"
            hw_path.write_bytes(
                valid_hardware_support_archive_bytes(architecture="amd64")
            )
            manifest = build_update_bundle(
                payload_path=payload_path,
                hardware_support_path=hw_path,
                output_path=root / "out.greiaupdate",
                version="0.14.0",
                release_id="greia-0.14.0",
                platform_family="standard-x86-64",
                architecture="amd64",
                profile="modern-amd64",
                payload_uncompressed_bytes=8 * 1024 * 1024,
                minimum_slot_bytes=8 * 1024 * 1024,
                persist_read_schema_min=1,
                persist_read_schema_max=1,
                persist_write_schema=1,
            )
            inspected = inspect_update_bundle(root / "out.greiaupdate")
            self.assertEqual(inspected.manifest.persist_read_schema_min, 1)
            self.assertEqual(inspected.manifest.persist_read_schema_max, 1)
            # PERSIST gate accepts the in-range schema, returns it.
            self.assertEqual(
                assert_persistent_contract_accepted(installed_marker, manifest), 1
            )
            # A Parent-supplied "approved" claim cannot override range:
            # a narrow manifest that cannot read schema 1 is refused.
            narrow = replace(
                manifest,
                persist_read_schema_min=10,
                persist_read_schema_max=10,
            )
            with self.assertRaises(PersistentLayoutError):
                assert_persistent_contract_accepted(installed_marker, narrow)
            other_marker = emit_persist_schema_marker(10)
            with self.assertRaises(PersistentLayoutError):
                assert_persistent_contract_accepted(other_marker, manifest)
            # The legacy whole-contract document is not a marker.
            with self.assertRaises(PersistentLayoutError):
                assert_persistent_contract_accepted(contract_raw, manifest)


if __name__ == "__main__":
    unittest.main()
