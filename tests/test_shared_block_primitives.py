"""Zero-device tests for the shared production block/filesystem primitives.

All device nodes are regular tmpdir files (size == layout slot capacity)
behind injected observation seams; no physical disk is contacted.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from greia_installer import slots as installer_slots
from greia_platform import block_slots
from greia_platform.block_slots import (
    BlockSlotError,
    BlockSlotFilesystem,
    BlockSlotStorage,
    SharedBlockSlotPrimitives,
    SharedSlotPackageInstaller,
    resolve_slot_device,
)
from greia_platform.persistent_layout import (
    BlockTopology,
    InstalledLayoutRecord,
    PartitionFact,
)
from greia_platform.slot_writer import (
    DestinationSlot,
    HardwareInventoryAttestation,
    ReleaseSupportSet,
    SlotFinalizer,
    SlotProfilePolicy,
    SlotWriter,
    VerifiedReleaseMember,
)

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_UUID_EVIL = "eeeeeeee-ffff-0000-1111-222222222222"
_SLOT_BYTES = 1024 * 1024 * 1024


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "layout_id": "modern-gpt-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": _SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _record(**overrides: object) -> InstalledLayoutRecord:
    return InstalledLayoutRecord.from_dict(_record_dict(**overrides))


def _topology(*, disk_id: str = "disk0", b_partuuid: str = _UUID_B,
              b_fs: str = _UUID_B_FS) -> BlockTopology:
    return BlockTopology(
        partitions=(
            PartitionFact.create(
                role="system-a", partuuid=_UUID_A, filesystem_uuid=_UUID_A_FS,
                size_bytes=_SLOT_BYTES, disk_id=disk_id,
            ),
            PartitionFact.create(
                role="system-b", partuuid=b_partuuid, filesystem_uuid=b_fs,
                size_bytes=_SLOT_BYTES, disk_id=disk_id,
            ),
            PartitionFact.create(
                role="persist", partuuid=_UUID_P, filesystem_uuid=_UUID_P_FS,
                size_bytes=512 * 1024 * 1024, disk_id=disk_id,
            ),
        )
    )


class _FakeFsRunner:
    """Filesystem runner backed by real tmp mount dirs + in-memory UUIDs."""

    def __init__(self) -> None:
        self.uuids: dict[str, str] = {}
        self.ops: list[str] = []
        self.fail_check = False

    def blkid_uuid(self, device: Path) -> str:
        self.ops.append(f"blkid:{device.name}")
        if str(device) not in self.uuids:
            raise BlockSlotError("fake blkid knows no UUID for device")
        return self.uuids[str(device)]

    def set_uuid(self, device: Path, filesystem_uuid: str) -> None:
        self.ops.append(f"set-uuid:{device.name}")
        self.uuids[str(device)] = filesystem_uuid

    def check(self, device: Path) -> None:
        self.ops.append(f"check:{device.name}")
        if self.fail_check:
            raise BlockSlotError("fake filesystem is unhealthy")

    def expand(self, device: Path) -> None:
        self.ops.append(f"expand:{device.name}")

    def mount(self, device: Path, mountpoint: Path) -> None:
        self.ops.append(f"mount:{device.name}")
        mountpoint.mkdir(parents=True, exist_ok=True)
        # Simulate a staged slot carrying real Greia userspace: the
        # production mount would expose the streamed payload content, so
        # the shared completeness smoke passes here. An empty mount would
        # be a V12G-like skeleton and must fail closed in finalization.
        from greia_platform.slot_writer import (
            REQUIRED_SLOT_COMPLETENESS_DIRS,
            REQUIRED_SLOT_COMPLETENESS_FILES,
        )

        for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
            (mountpoint / rel_path).mkdir(parents=True, exist_ok=True)
        for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
            candidate = mountpoint / rel_path
            candidate.parent.mkdir(parents=True, exist_ok=True)
            if candidate.is_symlink() or not candidate.is_file():
                candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
                try:
                    candidate.chmod(0o755)
                except OSError:
                    pass

    def unmount(self, mountpoint: Path) -> None:
        self.ops.append(f"unmount:{mountpoint.name}")

    def sync(self) -> None:
        self.ops.append("sync")


class _Harness:
    """Tmpdir dev-root with sparse device files + fresh-call counting seams."""

    def __init__(self, root: Path, *, record: InstalledLayoutRecord | None = None) -> None:
        self.root = root
        self.dev_root = root / "dev"
        self.dev_root.mkdir(parents=True)
        self.mount_root = root / "mnt"
        self.mount_root.mkdir(parents=True)
        self.record = record or _record()
        self.topology_calls = 0
        self.map_calls = 0
        self.live_topology = _topology()
        self.live_map = {_UUID_A: "sda2", _UUID_B: "sda3", _UUID_P: "sda4"}
        self.fs_runner = _FakeFsRunner()
        self._nodes: dict[str, Path] = {}
        for partuuid, kernel in self.live_map.items():
            node = self.dev_root / kernel
            with node.open("wb") as handle:
                handle.truncate(_SLOT_BYTES)
            os.chmod(node, 0o600)
            self._nodes[partuuid] = node
        # Persist node for the evil PARTUUID too (wrong-disk substitution peer).
        evil = self.dev_root / "sdb9"
        with evil.open("wb") as handle:
            handle.truncate(_SLOT_BYTES)
        self._nodes[_UUID_EVIL] = evil

    def observe(self) -> BlockTopology:
        self.topology_calls += 1
        return self.live_topology

    def read_map(self) -> dict[str, str]:
        self.map_calls += 1
        return dict(self.live_map)

    def probe(self, device: Path) -> str:
        # Reverse lookup: node -> PARTUUID it actually carries.
        for partuuid, node in self._nodes.items():
            if node == device:
                return partuuid
        raise BlockSlotError("fake probe knows no identity for device")

    def primitives(self, **overrides: object) -> SharedBlockSlotPrimitives:
        kwargs: dict[str, object] = {
            "record": self.record,
            "observe_topology": self.observe,
            "read_partuuid_map": self.read_map,
            "probe_device_partuuid": self.probe,
            "dev_root": self.dev_root,
            "filesystem_runner": self.fs_runner,
            "mount_root": self.mount_root,
            "package_runner": _RecordingPkgRunner(),
        }
        kwargs.update(overrides)
        return SharedBlockSlotPrimitives(**kwargs)  # type: ignore[arg-type]

    def resolve_b(self) -> object:
        return resolve_slot_device(
            record=self.record,
            semantic_slot="B",
            observe_topology=self.observe,
            read_partuuid_map=self.read_map,
            probe_device_partuuid=self.probe,
            dev_root=self.dev_root,
        )


class _FakeSupportInstaller:
    """Minimal release-bound installer (mirrors the shared fake semantics)."""

    def __init__(self, support: ReleaseSupportSet) -> None:
        self.support = support

    def install(
        self,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> tuple[object, ...]:
        wanted_firmware = self.support.require_firmware(tuple(firmware))
        wanted_microcode = self.support.require_microcode(tuple(microcode))
        return tuple(
            self.support.record_for(name)
            for name in (*wanted_firmware, *wanted_microcode)
        )


class _RecordingPkgRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: object, *, check: bool = True) -> None:
        self.commands.append(list(command))  # type: ignore[arg-type]


def _member(payload: bytes) -> VerifiedReleaseMember:
    hw = b"hwset-member"
    return VerifiedReleaseMember(
        release_id="greia-0.15.0",
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        payload_size=len(payload),
        payload_uncompressed_bytes=len(payload),
        minimum_slot_bytes=len(payload),
        hardware_support_sha256=hashlib.sha256(hw).hexdigest(),
        hardware_support_size=len(hw),
    )


def _support(member: VerifiedReleaseMember) -> ReleaseSupportSet:
    from greia_platform.slot_writer import InstalledPackage

    fw = b"firmware-bytes"
    uc = b"microcode-bytes"
    return ReleaseSupportSet(
        support_digest=member.hardware_support_sha256,
        support_size=member.hardware_support_size,
        installed_size_bound=1024,
        provided_firmware=frozenset({"firmware-realtek"}),
        provided_microcode=frozenset({"amd64-microcode"}),
        packages=(
            InstalledPackage(
                "firmware-realtek", "1", "all",
                hashlib.sha256(fw).hexdigest(), "firmware",
            ),
            InstalledPackage(
                "amd64-microcode", "1", "amd64",
                hashlib.sha256(uc).hexdigest(), "microcode",
            ),
        ),
    )


def _make_pool(root: Path) -> Path:
    fw = b"firmware-bytes"
    uc = b"microcode-bytes"
    pool = root / "support"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    (deb_dir / "firmware-realtek_1_all.deb").write_bytes(fw)
    (deb_dir / "amd64-microcode_1_amd64.deb").write_bytes(uc)
    packages_payload = b"Package: firmware-realtek\n"
    packages_gzip_payload = b"gzip-placeholder"
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)

    def _sha(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 2,
        "total_bytes": len(fw) + len(uc),
        "total_installed_bytes": len(fw) + len(uc) + 2 * 32 * 1024,
        "provided_candidate_packages": ["firmware-realtek", "amd64-microcode"],
        "provided_firmware_packages": ["firmware-realtek"],
        "provided_microcode_packages": ["amd64-microcode"],
        "broad_firmware_packages": ["firmware-realtek"],
        "firmware_providers": {"rtl.bin": ["firmware-realtek"]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-realtek", "version": "1",
                "architecture": "all", "filename": "pool/firmware-realtek_1_all.deb",
                "size": len(fw), "sha256": _sha(fw), "candidate": True,
                "installed_bytes": len(fw) + 32 * 1024,
            },
            {
                "package": "amd64-microcode", "version": "1",
                "architecture": "amd64", "filename": "pool/amd64-microcode_1_amd64.deb",
                "size": len(uc), "sha256": _sha(uc), "candidate": True,
                "installed_bytes": len(uc) + 32 * 1024,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_payload), "sha256": _sha(packages_payload)},
            "Packages.gz": {"size": len(packages_gzip_payload), "sha256": _sha(packages_gzip_payload)},
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


class ResolutionTests(unittest.TestCase):
    def test_resolve_inactive_role_through_real_mechanism(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            resolved = harness.resolve_b()
            self.assertEqual(resolved.role, "system-b")
            self.assertEqual(resolved.partuuid, _UUID_B)
            self.assertEqual(resolved.device_node, harness.dev_root / "sda3")
            self.assertEqual(resolved.capacity_bytes, _SLOT_BYTES)
            self.assertGreaterEqual(harness.topology_calls, 1)
            self.assertGreaterEqual(harness.map_calls, 1)

    def test_refuses_partuuid_off_installed_disk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            # Map the trusted B PARTUUID at another disk's node; the probe
            # of that node reports the evil identity, so resolution refuses.
            harness.live_map[_UUID_B] = "sdb9"
            with self.assertRaises(BlockSlotError):
                harness.resolve_b()

    def test_refuses_symlinked_device_node(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            target = harness.dev_root / "sda3"
            target.unlink()
            real = harness.dev_root / "real-sda3"
            with real.open("wb") as handle:
                handle.truncate(_SLOT_BYTES)
            os.symlink(real.name, target)
            with self.assertRaises(BlockSlotError):
                harness.resolve_b()

    def test_refuses_ambiguous_topology_map(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            harness.live_map[_UUID_P] = "sda3"  # two PARTUUIDs, one node
            with self.assertRaises(BlockSlotError):
                harness.resolve_b()

    def test_refuses_wrong_disk_topology(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            harness.live_topology = BlockTopology(
                partitions=(
                    PartitionFact.create(
                        role="system-a", partuuid=_UUID_A,
                        filesystem_uuid=_UUID_A_FS, size_bytes=_SLOT_BYTES,
                        disk_id="disk0",
                    ),
                    PartitionFact.create(
                        role="system-b", partuuid=_UUID_B,
                        filesystem_uuid=_UUID_B_FS, size_bytes=_SLOT_BYTES,
                        disk_id="disk9",
                    ),
                    PartitionFact.create(
                        role="persist", partuuid=_UUID_P,
                        filesystem_uuid=_UUID_P_FS, size_bytes=512 * 1024 * 1024,
                        disk_id="disk0",
                    ),
                )
            )
            with self.assertRaises(BlockSlotError):
                harness.resolve_b()

    def test_refuses_active_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            with self.assertRaises(BlockSlotError):
                resolve_slot_device(
                    record=harness.record, semantic_slot="A",
                    observe_topology=harness.observe,
                    read_partuuid_map=harness.read_map,
                    probe_device_partuuid=harness.probe,
                    dev_root=harness.dev_root,
                )

    def test_refuses_accepted_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = _record(
                accepted_slot="B",
                boot_control={"active_slot": "A", "kind": "grub-env-v1"},
            )
            harness = _Harness(Path(directory), record=record)
            with self.assertRaises(BlockSlotError):
                harness.resolve_b()

    def test_refuses_single_root_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = _record(
                layout_id="bios-single-ext4",
                boot_backend="none-v1",
                boot_control={"active_slot": None, "kind": "none-v1"},
                accepted_slot=None,
                system_b=None,
                platform_family="legacy-x86",
            )
            harness = _Harness(Path(directory), record=record)
            with self.assertRaises(BlockSlotError):
                harness.resolve_b()

    def test_reobserves_topology_at_call_time(self) -> None:
        """A stale pre-captured observation must not satisfy resolution."""
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            stale = harness.observe()  # pre-captured good topology
            calls_before = harness.topology_calls
            # Topology drifts (wrong disk) after capture; resolution must
            # observe fresh and refuse instead of trusting `stale`.
            harness.live_topology = BlockTopology(
                partitions=(
                    PartitionFact.create(
                        role="system-a", partuuid=_UUID_A,
                        filesystem_uuid=_UUID_A_FS, size_bytes=_SLOT_BYTES,
                        disk_id="disk0",
                    ),
                    PartitionFact.create(
                        role="system-b", partuuid=_UUID_B,
                        filesystem_uuid=_UUID_B_FS, size_bytes=_SLOT_BYTES,
                        disk_id="other-disk",
                    ),
                    PartitionFact.create(
                        role="persist", partuuid=_UUID_P,
                        filesystem_uuid=_UUID_P_FS, size_bytes=512 * 1024 * 1024,
                        disk_id="disk0",
                    ),
                )
            )
            with self.assertRaises(BlockSlotError):
                harness.resolve_b()
            self.assertGreater(harness.topology_calls, calls_before)
            self.assertIsNotNone(stale)  # stale value exists but was unused

    def test_boot_control_is_outside_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            with self.assertRaises(BlockSlotError):
                resolve_slot_device(
                    record=harness.record, semantic_slot="boot-control",  # type: ignore[arg-type]
                    observe_topology=harness.observe,
                    read_partuuid_map=harness.read_map,
                    probe_device_partuuid=harness.probe,
                    dev_root=harness.dev_root,
                )
            self.assertNotIn("boot-control", block_slots.RESOLVABLE_SLOT_ROLES)


class StorageTests(unittest.TestCase):
    def test_block_storage_bounded_io_and_flush(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            resolved = harness.resolve_b()
            with BlockSlotStorage(resolved.device_node, resolved.capacity_bytes) as store:
                self.assertEqual(store.capacity_bytes, _SLOT_BYTES)
                store.write_at(0, b"hello-block")
                self.assertEqual(store.read_at(0, len(b"hello-block")), b"hello-block")
                store.flush()
                with self.assertRaises(BlockSlotError):
                    store.write_at(_SLOT_BYTES - 2, b"abc")
                with self.assertRaises(BlockSlotError):
                    store.read_at(_SLOT_BYTES - 1, 2)
                with self.assertRaises(BlockSlotError):
                    store.write_at(0, b"")
            with self.assertRaises(BlockSlotError):
                store.read_at(0, 1)

    def test_storage_refuses_size_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            resolved = harness.resolve_b()
            with self.assertRaises(BlockSlotError):
                BlockSlotStorage(resolved.device_node, _SLOT_BYTES + 1)


class FilesystemTests(unittest.TestCase):
    def test_bind_mount_write_missing_health_unmount_sync(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            resolved = harness.resolve_b()
            filesystem = BlockSlotFilesystem(
                resolved, harness.fs_runner, harness.mount_root
            )
            with self.assertRaises(BlockSlotError):
                filesystem.write_file("etc/greia-os/x", b"1")  # not mounted
            filesystem.bind_filesystem_uuid(_UUID_B_FS)
            self.assertEqual(harness.fs_runner.uuids[str(resolved.device_node)], _UUID_B_FS)
            with self.assertRaises(BlockSlotError):
                filesystem.bind_filesystem_uuid(_UUID_A_FS)  # clone refusal
            filesystem.expand_to_capacity()
            mountpoint = filesystem.mount()
            self.assertTrue(mountpoint.is_dir())
            filesystem.write_file("etc/greia-os/release-identity.json", b"{}")
            self.assertEqual(filesystem.missing_files(("etc/greia-os/release-identity.json",)), ())
            self.assertEqual(
                filesystem.missing_files(("etc/greia-os/nope",)), ("etc/greia-os/nope",)
            )
            with self.assertRaises(BlockSlotError):
                filesystem.write_file("/absolute", b"x")
            with self.assertRaises(BlockSlotError):
                filesystem.write_file("../escape", b"x")
            filesystem.check_health()
            filesystem.unmount()
            filesystem.sync()
            self.assertIn("sync", harness.fs_runner.ops)

    def test_health_refuses_uuid_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            harness = _Harness(Path(directory))
            resolved = harness.resolve_b()
            filesystem = BlockSlotFilesystem(
                resolved, harness.fs_runner, harness.mount_root
            )
            filesystem.bind_filesystem_uuid(_UUID_B_FS)
            mountpoint = filesystem.mount()
            self.assertTrue(mountpoint.is_dir())
            harness.fs_runner.uuids[str(resolved.device_node)] = _UUID_A_FS
            with self.assertRaises(BlockSlotError):
                filesystem.check_health()
            filesystem.unmount()


class PackageInstallerTests(unittest.TestCase):
    def test_shared_installer_reuses_installer_support_path(self) -> None:
        from greia_installer.hardware_support import VerifiedHardwareSupportPool

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = VerifiedHardwareSupportPool.load(_make_pool(root))
            target_root = root / "target"
            target_root.mkdir()
            mounted: list[Path] = []
            installer = SharedSlotPackageInstaller(
                runner=_RecordingPkgRunner(),
                target_root=target_root,
                pool=pool,
                mounted=mounted,
            )
            installed = installer.install(("firmware-realtek",), ())
            self.assertEqual([package.name for package in installed], ["firmware-realtek"])
            # Same adapter class the installer path owns: no copied logic.
            self.assertTrue(hasattr(installer_slots.InstallerSlotPackageInstaller, "install"))
            with self.assertRaises(Exception):
                installer.install(("firmware-evil",), ())

    def test_bundle_package_installer_and_support_set(self) -> None:
        from greia_installer.hardware_support import VerifiedHardwareSupportPool

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = _Harness(root)
            pool = VerifiedHardwareSupportPool.load(_make_pool(root))
            support = block_slots.pool_to_release_support_set(
                pool, support_digest="2" * 64, support_size=128
            )
            self.assertEqual(support.provided_firmware, frozenset({"firmware-realtek"}))
            bundle = harness.primitives()
            target = root / "target2"
            target.mkdir()
            installer = bundle.make_package_installer(
                target_root=target, pool=pool, mounted=[]
            )
            self.assertIsInstance(installer, SharedSlotPackageInstaller)


class FinalizerIntegrationTests(unittest.TestCase):
    def test_write_read_bind_finalize_through_block_primitives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = _Harness(root)
            bundle = harness.primitives()
            resolved = bundle.resolve("B")
            self.assertNotEqual(resolved.semantic_slot, harness.record.boot_control.active_slot)
            self.assertNotEqual(resolved.semantic_slot, harness.record.accepted_slot)
            destination = DestinationSlot.resolve_from_layout(harness.record, "B")
            payload = bytes((index * 31 + 7) % 256 for index in range(200 * 1024))
            member = _member(payload)
            support = _support(member)
            store = bundle.open_storage(resolved)
            try:
                writer = SlotWriter()
                write = writer.write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,  # type: ignore[arg-type]
                    support_installed_bytes=support.installed_size_bound,
                )
                filesystem = bundle.open_filesystem(resolved)
                package_installer = _FakeSupportInstaller(support)
                inventory = HardwareInventoryAttestation(token="ab" * 32)
                policy = SlotProfilePolicy(
                    layout_id="modern-gpt-ab-v1",
                    system_slot_bytes=_SLOT_BYTES,
                    boot_backend="grub-ab-v1",
                    persist_filesystem_uuid="cccccccc-dddd-eeee-ffff-000000000000",
                    boot_control_filesystem_uuid="dddddddd-eeee-ffff-0000-111111111111",
                )
                receipt = SlotFinalizer().finalize(
                    write=write,
                    destination=destination,
                    filesystem=filesystem,  # type: ignore[arg-type]
                    package_installer=package_installer,  # type: ignore[arg-type]
                    inventory=inventory,
                    support=support,
                    profile_policy=policy,
                )
                self.assertEqual(receipt.filesystem_uuid, _UUID_B_FS)
                self.assertEqual(receipt.slot, "B")
                # The role UUID was restored, never cloned from a template.
                self.assertNotEqual(receipt.filesystem_uuid, _UUID_A_FS)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
