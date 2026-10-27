from __future__ import annotations

import hashlib
import hmac
import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from greia_installer import slots as installer_slots
from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_platform import slot_writer as slot_module
from greia_platform.hardware_enablement import (
    HardwareDevice,
    HardwareInventory,
    HardwareSupportPlan,
    HardwareSupportRecommendation,
    SupportDisposition,
    SupportKind,
)
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.slot_writer import (
    FINALIZER_VERSION,
    DestinationSlot,
    DeterministicBootArtifactBuilder,
    HardwareInventoryAttestation,
    InstalledPackage,
    LoopbackSlotFile,
    ReleaseSupportSet,
    ResolvedHardwareSelection,
    SlotBootArtifacts,
    SlotFinalizeError,
    SlotFinalizer,
    SlotProfilePolicy,
    SlotWriteError,
    SlotWriter,
    VerifiedBaseSlotWrite,
    VerifiedReleaseMember,
    resolve_hardware_selection,
)
from greia_platform.system_updates import UpdateManifest

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_UUID_BOOT_FS = "eeeeeeee-ffff-0000-1111-222222222222"
#: Release-builder template filesystem UUID: the deterministic base payload
#: carries this identity, so any staged slot still carrying it after
#: finalization proves the role UUID was cloned instead of restored.
_TEMPLATE_UUID = "dddddddd-eeee-ffff-0000-111111111111"
_INSTALL_SHA = "ab" * 32

_FW_PAYLOAD = b"firmware-bytes"
_UC_PAYLOAD = b"microcode-bytes"


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


def _payload(size: int = 200 * 1024) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _member(payload: bytes, *, minimum: int | None = None) -> VerifiedReleaseMember:
    hw = b"hwset-member"
    return VerifiedReleaseMember(
        release_id="greia-0.15.0",
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        payload_size=len(payload),
        payload_uncompressed_bytes=len(payload),
        minimum_slot_bytes=minimum if minimum is not None else len(payload),
        hardware_support_sha256=hashlib.sha256(hw).hexdigest(),
        hardware_support_size=len(hw),
    )


def _support(*, digest: str | None = None) -> ReleaseSupportSet:
    hw_digest = digest if digest is not None else hashlib.sha256(b"hwset-member").hexdigest()
    return ReleaseSupportSet(
        support_digest=hw_digest,
        support_size=len(b"hwset-member"),
        installed_size_bound=1024,
        provided_firmware=frozenset({"firmware-realtek"}),
        provided_microcode=frozenset({"amd64-microcode"}),
        packages=(
            InstalledPackage(
                "firmware-realtek", "1", "all",
                hashlib.sha256(_FW_PAYLOAD).hexdigest(), "firmware",
            ),
            InstalledPackage(
                "amd64-microcode", "1", "amd64",
                hashlib.sha256(_UC_PAYLOAD).hexdigest(), "microcode",
            ),
        ),
    )


def _policy(*, slot_bytes: int = 1024 * 1024 * 1024) -> SlotProfilePolicy:
    return SlotProfilePolicy(
        layout_id="modern-gpt-ab-v1",
        system_slot_bytes=slot_bytes,
        boot_backend="grub-ab-v1",
        persist_filesystem_uuid=_UUID_P_FS,
        boot_control_filesystem_uuid=_UUID_BOOT_FS,
    )


def _populate_slot_completeness(mount_dir: Path) -> None:
    """Create the required Greia userspace tree for a passing smoke.

    Uses the shared validator's documented path set so the fake proves
    the same mechanism as production. Command files are real regular
    files (executable) to satisfy the usable presence check.
    """
    from greia_platform.slot_writer import (
        REQUIRED_SLOT_COMPLETENESS_DIRS,
        REQUIRED_SLOT_COMPLETENESS_FILES,
    )

    for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
        (mount_dir / rel_path).mkdir(parents=True, exist_ok=True)
    boot_dir = mount_dir / "boot"
    boot_dir.mkdir(parents=True, exist_ok=True)
    (boot_dir / "vmlinuz-generic").write_bytes(b"generic-kernel")
    (boot_dir / "initrd-generic").write_bytes(b"generic-initramfs")
    for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
        candidate = mount_dir / rel_path
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if candidate.is_symlink() or not candidate.is_file():
            candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
            try:
                candidate.chmod(0o755)
            except OSError:
                pass


def _populate_d6_minimal(mount_dir: Path) -> None:
    """Create the V12G/D6 failure shape: only {etc, lost+found, run, var}."""
    for rel_path in ("etc", "lost+found", "run", "var"):
        (mount_dir / rel_path).mkdir(parents=True, exist_ok=True)


def _inventory() -> HardwareInventoryAttestation:
    return HardwareInventoryAttestation.from_inventory(
        HardwareInventory((), truncated=False, scan_errors=0)
    )


class FakeSlotFilesystem:
    """Destination-only fake: records every mutation in order."""

    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.ops: list[str] = []
        self.files: dict[str, bytes] = {}
        self.bound_uuid: str | None = None
        self.expanded = False
        self.mounted = False
        self.mount_count = 0
        self.unmount_count = 0
        self.sync_count = 0
        self.healthy = True

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.ops.append("bind")
        self.bound_uuid = filesystem_uuid

    def expand_to_capacity(self) -> None:
        self.ops.append("expand")
        self.expanded = True

    def mount(self) -> Path:
        self.ops.append("mount")
        if self.mounted:
            raise SlotFinalizeError("slot is already mounted")
        self.mounted = True
        self.mount_count += 1
        return self.mount_dir

    def unmount(self) -> None:
        self.ops.append("unmount")
        self.mounted = False
        self.unmount_count += 1

    def sync(self) -> None:
        self.ops.append("sync")
        self.sync_count += 1

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise SlotFinalizeError("slot writes require a mounted destination")
        self.ops.append(f"write:{relative_path}")
        self.files[relative_path] = bytes(data)

    def link_file(
        self, source_relative_path: str, target_relative_path: str
    ) -> None:
        if not self.mounted:
            raise SlotFinalizeError("slot links require a mounted destination")
        source = self.mount_dir / source_relative_path
        if source.is_symlink() or not source.is_file():
            raise SlotFinalizeError("slot link source is missing")
        self.ops.append(f"link:{source_relative_path}:{target_relative_path}")
        self.files[target_relative_path] = source.read_bytes()

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_completeness(self) -> None:
        self.ops.append("completeness")
        slot_module.check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        self.ops.append("health")
        if not self.healthy:
            raise SlotFinalizeError("slot filesystem is unhealthy")


class FakeSlotPackageInstaller:
    """Fake installer validating against the release-bound support set."""

    def __init__(self, support: ReleaseSupportSet) -> None:
        self.support = support
        self.calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        self.tamper: dict[str, str] = {}

    def install(
        self,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> tuple[InstalledPackage, ...]:
        wanted_firmware = self.support.require_firmware(tuple(firmware))
        wanted_microcode = self.support.require_microcode(tuple(microcode))
        self.calls.append((wanted_firmware, wanted_microcode))
        records = [
            self.support.record_for(name)
            for name in (*wanted_firmware, *wanted_microcode)
        ]
        tampered: list[InstalledPackage] = []
        for record in records:
            if record.name in self.tamper:
                tampered.append(
                    replace(record, sha256=self.tamper[record.name])
                )
            else:
                tampered.append(record)
        return tuple(tampered)


class BoundedReadStream(io.BytesIO):
    """Source stream refusing any single read larger than the working bound."""

    def __init__(self, payload: bytes, limit: int) -> None:
        super().__init__(payload)
        self._limit = limit
        self.max_single_read = 0

    def read(self, size: int = -1) -> bytes:  # type: ignore[override]
        if size is None or size < 0 or size > self._limit:
            raise AssertionError(f"source read exceeds the working bound: {size!r}")
        self.max_single_read = max(self.max_single_read, size)
        return super().read(size)


class InterruptingStream(io.BytesIO):
    """Source stream failing mid-read like an interrupted staged payload."""

    def __init__(self, payload: bytes, fail_after: int) -> None:
        super().__init__(payload)
        self._fail_after = fail_after
        self._delivered = 0

    def read(self, size: int = -1) -> bytes:  # type: ignore[override]
        if self._delivered >= self._fail_after:
            raise OSError("simulated interrupted payload stream")
        chunk = super().read(size)
        self._delivered += len(chunk)
        return chunk


class CorruptingStorage:
    """Wraps a store and flips one byte on every readback read."""

    def __init__(self, inner: LoopbackSlotFile) -> None:
        self._inner = inner

    @property
    def capacity_bytes(self) -> int:
        return self._inner.capacity_bytes

    def write_at(self, offset: int, data: bytes) -> None:
        self._inner.write_at(offset, data)

    def read_at(self, offset: int, length: int) -> bytes:
        raw = bytearray(self._inner.read_at(offset, length))
        raw[0] ^= 0x01
        return bytes(raw)

    def flush(self) -> None:
        self._inner.flush()


class ChunkProbeStorage:
    """Records the largest single write chunk handed to the store."""

    def __init__(self, inner: LoopbackSlotFile) -> None:
        self._inner = inner
        self.max_chunk = 0

    @property
    def capacity_bytes(self) -> int:
        return self._inner.capacity_bytes

    def write_at(self, offset: int, data: bytes) -> None:
        self.max_chunk = max(self.max_chunk, len(data))
        self._inner.write_at(offset, data)

    def read_at(self, offset: int, length: int) -> bytes:
        return self._inner.read_at(offset, length)

    def flush(self) -> None:
        self._inner.flush()


def _write_happy(
    root: Path,
    payload: bytes,
    *,
    semantic: str = "B",
    writer: SlotWriter | None = None,
) -> tuple[VerifiedBaseSlotWrite, DestinationSlot, LoopbackSlotFile, VerifiedReleaseMember]:
    record = _record()
    if semantic == "A":
        record = _record(
            accepted_slot="B",
            boot_control={"active_slot": "B", "kind": "grub-env-v1"},
        )
    destination = DestinationSlot.resolve_from_layout(record, semantic)
    member = _member(payload)
    store = LoopbackSlotFile.create(root / f"slot-{semantic}.img", destination.slot_capacity_bytes)
    active_writer = writer or SlotWriter()
    write = active_writer.write(
        member=member,
        destination=destination,
        source=io.BytesIO(payload),
        storage=store,
        support_installed_bytes=1024,
    )
    return write, destination, store, member


class SlotWriterTests(unittest.TestCase):
    def test_stream_flush_readback_issues_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload()
            write, destination, store, member = _write_happy(root, payload)
            try:
                self.assertEqual(write.bytes_written, len(payload))
                self.assertEqual(write.slot_digest, member.payload_sha256)
                self.assertEqual(write.destination, destination)
                self.assertTrue(write.write_token)
                self.assertEqual(
                    store.read_at(0, len(payload)),
                    payload,
                )
                # Bytes past the signed range stay zeroed: no overrun.
                self.assertEqual(
                    store.read_at(len(payload), 16),
                    b"\x00" * 16,
                )
            finally:
                store.close()

    def test_destination_must_not_be_active_or_accepted(self) -> None:
        with self.assertRaisesRegex(SlotWriteError, "active slot"):
            DestinationSlot.resolve_from_layout(_record(), "A")
        live_b = _record(
            accepted_slot="B",
            boot_control={"active_slot": "B", "kind": "grub-env-v1"},
        )
        with self.assertRaisesRegex(SlotWriteError, "active slot"):
            DestinationSlot.resolve_from_layout(live_b, "B")
        accepted_a = _record(
            accepted_slot="A",
            boot_control={"active_slot": "B", "kind": "grub-env-v1"},
        )
        with self.assertRaisesRegex(SlotWriteError, "accepted slot"):
            DestinationSlot.resolve_from_layout(accepted_a, "A")
        # The writer re-checks even if a destination is constructed directly.
        record = _record()
        destination = DestinationSlot.resolve_from_layout(record, "B")
        live = replace(destination, active_slot="B")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload(1024)
            store = LoopbackSlotFile.create(root / "slot.img", destination.slot_capacity_bytes)
            try:
                with self.assertRaisesRegex(SlotWriteError, "active slot"):
                    SlotWriter().write(
                        member=_member(payload),
                        destination=live,
                        source=io.BytesIO(payload),
                        storage=store,
                        support_installed_bytes=0,
                    )
            finally:
                store.close()

    def test_single_root_layout_has_no_destination(self) -> None:
        single = _record_dict(
            layout_id="bios-single-ext4",
            boot_backend="none-v1",
            boot_control={"active_slot": None, "kind": "none-v1"},
            accepted_slot=None,
            system_b=None,
            slot_bytes=1024 * 1024 * 1024,
        )
        record = InstalledLayoutRecord.from_dict(single)
        with self.assertRaisesRegex(SlotWriteError, "single-root"):
            DestinationSlot.resolve_from_layout(record, "B")

    def test_readback_mismatch_fails_closed_without_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload()
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            member = _member(payload)
            inner = LoopbackSlotFile.create(root / "slot.img", destination.slot_capacity_bytes)
            try:
                store = CorruptingStorage(inner)
                with self.assertRaisesRegex(SlotWriteError, "readback digest"):
                    SlotWriter().write(
                        member=member,
                        destination=destination,
                        source=io.BytesIO(payload),
                        storage=store,
                        support_installed_bytes=1024,
                    )
            finally:
                inner.close()

    def test_truncated_and_oversize_streams_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload()
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            member = _member(payload)
            for index, source in (
                (0, io.BytesIO(payload[:-100])),
                (1, io.BytesIO(payload + b"extra")),
            ):
                store = LoopbackSlotFile.create(
                    root / f"slot-{index}.img", destination.slot_capacity_bytes
                )
                try:
                    with self.assertRaises(SlotWriteError):
                        SlotWriter().write(
                            member=member,
                            destination=destination,
                            source=source,
                            storage=store,
                            support_installed_bytes=1024,
                        )
                finally:
                    store.close()

    def test_capacity_with_finalization_headroom_enforced(self) -> None:
        payload = _payload(1024)
        member = _member(payload)
        writer = SlotWriter()
        record = _record()
        capacity = record.slot_bytes if isinstance(record.slot_bytes, int) else 0
        destination = DestinationSlot.resolve_from_layout(record, "B")
        # Exact fit passes the proof.
        support = capacity - writer.required_slot_bytes(member, 0)
        self.assertGreater(support, 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = LoopbackSlotFile.create(root / "slot.img", capacity)
            try:
                write = writer.write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,
                    support_installed_bytes=support,
                )
                self.assertEqual(write.bytes_written, len(payload))
            finally:
                store.close()
        # One byte over fails closed before any byte is streamed.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = LoopbackSlotFile.create(root / "slot.img", capacity)
            try:
                with self.assertRaisesRegex(SlotWriteError, "headroom"):
                    writer.write(
                        member=member,
                        destination=destination,
                        source=io.BytesIO(payload),
                        storage=store,
                        support_installed_bytes=support + 1,
                    )
                self.assertEqual(store.read_at(0, 16), b"\x00" * 16)
            finally:
                store.close()

    def test_store_capacity_must_match_layout_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload(1024)
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            store = LoopbackSlotFile.create(root / "slot.img", 1024 * 1024)
            try:
                with self.assertRaisesRegex(SlotWriteError, "does not match"):
                    SlotWriter(
                        growth_bytes=0,
                        metadata_reserve_bytes=0,
                    ).write(
                        member=_member(payload),
                        destination=destination,
                        source=io.BytesIO(payload),
                        storage=store,
                        support_installed_bytes=0,
                    )
            finally:
                store.close()

    def test_streaming_uses_bounded_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload(100 * 1024)
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            inner = LoopbackSlotFile.create(root / "slot.img", destination.slot_capacity_bytes)
            try:
                probe = ChunkProbeStorage(inner)
                SlotWriter(chunk_bytes=8192).write(
                    member=_member(payload),
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=probe,
                    support_installed_bytes=1024,
                )
                self.assertLessEqual(probe.max_chunk, 8192)
                self.assertGreater(probe.max_chunk, 0)
            finally:
                inner.close()

    def test_streaming_memory_is_bounded(self) -> None:
        import tracemalloc

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload(4 * 1024 * 1024)
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            member = _member(payload)
            store = LoopbackSlotFile.create(root / "slot.img", destination.slot_capacity_bytes)
            try:
                source = BoundedReadStream(payload, limit=16 * 1024)
                writer = SlotWriter(chunk_bytes=16 * 1024)
                tracemalloc.start()
                try:
                    write = writer.write(
                        member=member,
                        destination=destination,
                        source=source,
                        storage=store,
                        support_installed_bytes=1024,
                    )
                finally:
                    _, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                self.assertEqual(write.bytes_written, len(payload))
                # No single source read ever exceeds the working chunk, and
                # peak Python working memory stays far below one full
                # payload: no second full-size copy is ever materialized
                # beside the bundle stream.
                self.assertLessEqual(source.max_single_read, 16 * 1024)
                self.assertGreater(source.max_single_read, 0)
                self.assertLess(peak, len(payload) // 4)
            finally:
                store.close()

    def test_interrupted_write_never_touches_accepted_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload()
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            member = _member(payload)
            accepted = LoopbackSlotFile.create(
                root / "accepted.img", destination.slot_capacity_bytes
            )
            store = LoopbackSlotFile.create(
                root / "slot.img", destination.slot_capacity_bytes
            )
            try:
                accepted_before = accepted.read_at(0, len(payload))
                issued_before = len(slot_module._ISSUED_WRITE_TOKENS)
                with self.assertRaises(SlotWriteError):
                    SlotWriter().write(
                        member=member,
                        destination=destination,
                        source=InterruptingStream(payload, fail_after=4096),
                        storage=store,
                        support_installed_bytes=1024,
                    )
                # The interrupted staging issues no capability and leaves the
                # accepted slot byte-identical.
                self.assertEqual(len(slot_module._ISSUED_WRITE_TOKENS), issued_before)
                self.assertEqual(accepted.read_at(0, len(payload)), accepted_before)
                # Retrying the full stream on the same destination store
                # succeeds and verifies: the interruption poisons nothing.
                write = SlotWriter().write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,
                    support_installed_bytes=1024,
                )
                self.assertEqual(write.slot_digest, member.payload_sha256)
                self.assertEqual(store.read_at(0, len(payload)), payload)
            finally:
                accepted.close()
                store.close()

    def test_digest_compare_is_constant_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload()
            calls: list[tuple[str, str]] = []
            original = hmac.compare_digest

            def counting(first: str, second: str) -> bool:
                calls.append((first, second))
                return original(first, second)

            import unittest.mock as mock

            with mock.patch("hmac.compare_digest", side_effect=counting):
                _, _, digest_store, _ = _write_happy(root, payload)
                digest_store.close()
            # v3 writer proves stream/readback agreement with a single
            # constant-time comparison (compressed transport digest was
            # already proven at inspection).
            self.assertGreaterEqual(len(calls), 1)
            for first, second in calls:
                self.assertEqual(len(first), 64)
                self.assertEqual(len(second), 64)

    def test_member_binds_unsigned_v3_manifest(self) -> None:
        payload = _payload(4096)
        manifest = UpdateManifest(
            schema_version=3,
            release_id="greia-0.15.0",
            version="0.15.0",
            platform_family="standard-x86-64",
            architecture="amd64",
            profile="modern-amd64",
            board=None,
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            payload_size=len(payload),
            payload_uncompressed_bytes=len(payload),
            payload_minimum_slot_bytes=len(payload),
            hardware_support_sha256=hashlib.sha256(b"hw").hexdigest(),
            hardware_support_size=2,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
        )
        member = VerifiedReleaseMember.from_manifest(manifest)
        self.assertEqual(member.payload_size, len(payload))
        self.assertEqual(member.payload_uncompressed_bytes, len(payload))
        self.assertEqual(member.minimum_slot_bytes, len(payload))
        self.assertEqual(member.release_id, "greia-0.15.0")


class SlotFinalizerTests(unittest.TestCase):
    def _finalize_happy(
        self,
        root: Path,
        payload: bytes,
        *,
        firmware: tuple[str, ...] = ("firmware-realtek",),
        microcode: tuple[str, ...] = ("amd64-microcode",),
    ) -> tuple[object, FakeSlotFilesystem, FakeSlotPackageInstaller]:
        write, destination, store, member = _write_happy(root, payload)
        try:
            mount_dir = root / "mnt"
            mount_dir.mkdir(exist_ok=True)
            _populate_slot_completeness(mount_dir)
            filesystem = FakeSlotFilesystem(mount_dir)
            support = _support()
            installer = FakeSlotPackageInstaller(support)
            receipt = SlotFinalizer().finalize(
                write=write,
                destination=destination,
                filesystem=filesystem,
                package_installer=installer,
                inventory=_inventory(),
                support=support,
                profile_policy=_policy(),
                firmware_packages=firmware,
                microcode_packages=microcode,
                slot_config={"locale": "en"},
            )
            return receipt, filesystem, installer
        finally:
            store.close()

    def test_finalize_binds_uuid_expands_installs_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload()
            receipt, filesystem, installer = self._finalize_happy(root, payload)
            assert isinstance(receipt, slot_module.FinalizationReceipt)
            # Role-stable restore: the destination role's recorded UUID is
            # rebound onto the staged payload — never minted fresh, never
            # the template clone, never the other role's UUID.
            bound = filesystem.bound_uuid
            assert bound is not None
            self.assertEqual(bound, _UUID_B_FS)
            self.assertNotEqual(bound, _UUID_A_FS)
            self.assertNotEqual(bound, _TEMPLATE_UUID)
            self.assertTrue(filesystem.expanded)
            # Strict staging order: expand/check -> bind -> mount -> writes ->
            # health -> unmount -> sync. The payload journal must be clean
            # before tune2fs accepts the role UUID.
            self.assertEqual(filesystem.ops[0], "expand")
            self.assertEqual(filesystem.ops[1], "bind")
            self.assertEqual(filesystem.ops[2], "mount")
            self.assertEqual(filesystem.ops[-3], "health")
            self.assertEqual(filesystem.ops[-2], "unmount")
            self.assertEqual(filesystem.ops[-1], "sync")
            self.assertEqual(filesystem.mount_count, 1)
            self.assertEqual(filesystem.unmount_count, 1)
            self.assertEqual(filesystem.sync_count, 1)
            self.assertEqual(
                installer.calls,
                [(("firmware-realtek",), ("amd64-microcode",))],
            )
            # Receipt binds every digest plus the finalizer version.
            self.assertEqual(receipt.finalizer_version, FINALIZER_VERSION)
            self.assertEqual(receipt.base_sha256, hashlib.sha256(payload).hexdigest())
            self.assertEqual(receipt.slot, "B")
            self.assertEqual(receipt.role, "system-b")
            self.assertEqual(receipt.filesystem_uuid, bound)
            self.assertEqual(
                receipt.support_sha256, hashlib.sha256(b"hwset-member").hexdigest()
            )
            self.assertEqual(
                receipt.inventory_token, _inventory().token
            )
            self.assertEqual(
                [package.name for package in receipt.packages],
                ["amd64-microcode", "firmware-realtek"],
            )
            expected_host = hashlib.sha256(
                f"{receipt.base_sha256}:{receipt.inventory_token}:"
                f"{receipt.packages_digest}\n".encode("utf-8")
            ).hexdigest()
            self.assertEqual(receipt.host_initramfs_sha256, expected_host)
            self.assertEqual(receipt.generic_kernel_sha256, receipt.base_sha256)
            # Receipt file bytes are the canonical receipt bytes.
            stored = filesystem.files["etc/greia-os/finalization-receipt.json"]
            self.assertEqual(stored, receipt.canonical_bytes())
            parsed = json.loads(stored.decode("utf-8"))
            self.assertEqual(parsed["finalizer_version"], FINALIZER_VERSION)
            self.assertIn("artifact_digests", parsed)

    def test_ab_role_uuids_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, first_fs, _ = self._finalize_happy(root, _payload(4096))
            assert isinstance(first, slot_module.FinalizationReceipt)
            assert first_fs.bound_uuid is not None
            second_root = root / "second"
            second_root.mkdir()
            payload = _payload(8192)
            record = _record(
                accepted_slot="B",
                boot_control={"active_slot": "B", "kind": "grub-env-v1"},
            )
            destination = DestinationSlot.resolve_from_layout(record, "A")
            member = _member(payload)
            store = LoopbackSlotFile.create(second_root / "slot-a.img", destination.slot_capacity_bytes)
            try:
                write = SlotWriter().write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,
                    support_installed_bytes=1024,
                )
                mount_dir = second_root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                _populate_slot_completeness(mount_dir)
                filesystem = FakeSlotFilesystem(mount_dir)
                support = _support()
                receipt = SlotFinalizer().finalize(
                    write=write,
                    destination=destination,
                    filesystem=filesystem,
                    package_installer=FakeSlotPackageInstaller(support),
                    inventory=_inventory(),
                    support=support,
                    profile_policy=_policy(),
                    firmware_packages=("firmware-realtek",),
                    microcode_packages=(),
                )
            finally:
                store.close()
            assert isinstance(receipt, slot_module.FinalizationReceipt)
            # The same template payload staged into both roles restores each
            # role's own stable UUID: distinct per role, never the template.
            self.assertEqual(first_fs.bound_uuid, _UUID_B_FS)
            self.assertEqual(filesystem.bound_uuid, _UUID_A_FS)
            self.assertEqual(receipt.filesystem_uuid, _UUID_A_FS)
            restored = {first_fs.bound_uuid, receipt.filesystem_uuid}
            self.assertEqual(restored, {_UUID_A_FS, _UUID_B_FS})
            self.assertNotIn(_TEMPLATE_UUID, restored)

    def test_forged_capability_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                forged = replace(write, write_token="f" * 32)
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                filesystem = FakeSlotFilesystem(mount_dir)
                support = _support()
                with self.assertRaisesRegex(SlotFinalizeError, "not a registered"):
                    SlotFinalizer().finalize(
                        write=forged,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
                self.assertEqual(filesystem.ops, [])
            finally:
                store.close()

    def test_destination_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, _, store, _ = _write_happy(root, _payload(4096))
            try:
                other_record = _record(
                    accepted_slot="B",
                    boot_control={"active_slot": "B", "kind": "grub-env-v1"},
                )
                other = DestinationSlot.resolve_from_layout(other_record, "A")
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                filesystem = FakeSlotFilesystem(mount_dir)
                support = _support()
                with self.assertRaisesRegex(SlotFinalizeError, "does not match"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=other,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
                # A refused role binding mutates nothing on the destination.
                self.assertEqual(filesystem.ops, [])
                self.assertIsNone(filesystem.bound_uuid)
                self.assertFalse(filesystem.expanded)
            finally:
                store.close()

    def test_finalize_consumes_capability_against_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                _populate_slot_completeness(mount_dir)
                support = _support()
                SlotFinalizer().finalize(
                    write=write,
                    destination=destination,
                    filesystem=FakeSlotFilesystem(mount_dir),
                    package_installer=FakeSlotPackageInstaller(support),
                    inventory=_inventory(),
                    support=support,
                    profile_policy=_policy(),
                )
                # Replaying the now-stale write against the same role fails
                # with zero further mutations...
                replay = FakeSlotFilesystem(mount_dir)
                with self.assertRaisesRegex(SlotFinalizeError, "not a registered"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=replay,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
                self.assertEqual(replay.ops, [])
                # ...and it cannot be rebound to the other role either.
                other_record = _record(
                    accepted_slot="B",
                    boot_control={"active_slot": "B", "kind": "grub-env-v1"},
                )
                other = DestinationSlot.resolve_from_layout(other_record, "A")
                cross = FakeSlotFilesystem(mount_dir)
                with self.assertRaises(SlotFinalizeError):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=other,
                        filesystem=cross,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
                self.assertEqual(cross.ops, [])
            finally:
                store.close()

    def test_readback_failure_issues_no_mutation_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload()
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            member = _member(payload)
            inner = LoopbackSlotFile.create(root / "slot.img", destination.slot_capacity_bytes)
            try:
                with self.assertRaisesRegex(SlotWriteError, "readback digest"):
                    SlotWriter().write(
                        member=member,
                        destination=destination,
                        source=io.BytesIO(payload),
                        storage=CorruptingStorage(inner),
                        support_installed_bytes=1024,
                    )
                # A failed readback issues no capability, so the only route
                # into binding is refused with the destination seam untouched:
                # readback strictly precedes UUID restore/expand.
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                filesystem = FakeSlotFilesystem(mount_dir)
                support = _support()
                forged = VerifiedBaseSlotWrite(
                    member=member,
                    destination=destination,
                    bytes_written=len(payload),
                    slot_digest=member.payload_sha256,
                    write_token="e" * 32,
                )
                with self.assertRaisesRegex(SlotFinalizeError, "not a registered"):
                    SlotFinalizer().finalize(
                        write=forged,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
                self.assertEqual(filesystem.ops, [])
                self.assertIsNone(filesystem.bound_uuid)
                self.assertFalse(filesystem.expanded)
            finally:
                inner.close()

    def test_active_slot_is_never_finalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                # A write presented against a live slot: the issuance token
                # still verifies, so the active-slot gate must refuse.
                live = replace(destination, active_slot="B")
                live_write = replace(write, destination=live)
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                filesystem = FakeSlotFilesystem(mount_dir)
                support = _support()
                with self.assertRaisesRegex(SlotFinalizeError, "active slot"):
                    SlotFinalizer().finalize(
                        write=live_write,
                        destination=live,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
                self.assertEqual(filesystem.mount_count, 0)
                self.assertIsNone(filesystem.bound_uuid)
                # And a mismatched role alone fails at the binding gate.
                other_record = _record(
                    accepted_slot="B",
                    boot_control={"active_slot": "B", "kind": "grub-env-v1"},
                )
                other = DestinationSlot.resolve_from_layout(other_record, "A")
                with self.assertRaisesRegex(SlotFinalizeError, "does not match"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=other,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
            finally:
                store.close()

    def test_support_set_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                support = _support()
                # Unapproved package fails closed.
                with self.assertRaisesRegex(SlotFinalizeError, "not approved firmware"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=FakeSlotFilesystem(mount_dir),
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                        firmware_packages=("firmware-evil",),
                    )
                # Firmware requested as microcode fails closed.
                with self.assertRaisesRegex(SlotFinalizeError, "not approved microcode"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=FakeSlotFilesystem(mount_dir),
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                        microcode_packages=("firmware-realtek",),
                    )
                # Tampered install records fail closed.
                tampering = FakeSlotPackageInstaller(support)
                tampering.tamper["firmware-realtek"] = "0" * 64
                _populate_slot_completeness(mount_dir)
                with self.assertRaisesRegex(SlotFinalizeError, "record changed"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=FakeSlotFilesystem(mount_dir),
                        package_installer=tampering,
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                        firmware_packages=("firmware-realtek",),
                    )
                # Support set bound to a different release member fails closed.
                foreign = _support(digest="1" * 64)
                with self.assertRaisesRegex(SlotFinalizeError, "not the release-bound"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=FakeSlotFilesystem(mount_dir),
                        package_installer=FakeSlotPackageInstaller(foreign),
                        inventory=_inventory(),
                        support=foreign,
                        profile_policy=_policy(),
                    )
            finally:
                store.close()

    def test_finalization_capacity_rechecked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload(4096)
            member = _member(payload)
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            store = LoopbackSlotFile.create(root / "slot.img", destination.slot_capacity_bytes)
            try:
                # Issued under zero headroom so the write passes...
                lean = SlotWriter(growth_bytes=0, metadata_reserve_bytes=0)
                write = lean.write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,
                    support_installed_bytes=destination.slot_capacity_bytes - len(payload),
                )
                # ...but production finalization headroom no longer fits.
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                support = _support()
                oversized = replace(
                    support,
                    installed_size_bound=destination.slot_capacity_bytes,
                )
                with self.assertRaisesRegex(SlotFinalizeError, "headroom"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=FakeSlotFilesystem(mount_dir),
                        package_installer=FakeSlotPackageInstaller(oversized),
                        inventory=_inventory(),
                        support=oversized,
                        profile_policy=_policy(),
                    )
            finally:
                store.close()

    def test_failure_still_unmounts_and_syncs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                _populate_slot_completeness(mount_dir)
                filesystem = FakeSlotFilesystem(mount_dir)
                filesystem.healthy = False
                support = _support()
                with self.assertRaisesRegex(SlotFinalizeError, "unhealthy"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
                self.assertEqual(filesystem.unmount_count, 1)
                self.assertEqual(filesystem.sync_count, 1)
                self.assertFalse(filesystem.mounted)
            finally:
                store.close()

    def test_profile_policy_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                support = _support()
                with self.assertRaisesRegex(SlotFinalizeError, "profile slot bytes"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=FakeSlotFilesystem(mount_dir),
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(slot_bytes=1024),
                    )
                with self.assertRaisesRegex(SlotFinalizeError, "profile layout"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=FakeSlotFilesystem(mount_dir),
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=SlotProfilePolicy(
                            layout_id="pi-mbr-tryboot-ab-v1",
                            system_slot_bytes=destination.slot_capacity_bytes,
                            boot_backend="pi-tryboot-ab-v1",
                        ),
                    )
            finally:
                store.close()

    def test_incomplete_inventory_refuses_finalization(self) -> None:
        with self.assertRaises(SlotFinalizeError):
            HardwareInventoryAttestation.from_inventory(
                HardwareInventory((), truncated=True, scan_errors=0)
            )
        with self.assertRaises(SlotFinalizeError):
            HardwareInventoryAttestation.from_inventory(
                HardwareInventory((), truncated=False, scan_errors=2)
            )
        with self.assertRaises((SlotWriteError, SlotFinalizeError)):
            HardwareInventoryAttestation(token="not-hex")


class SlotFinalizerReleaseTests(unittest.TestCase):
    """Step 8A.4: common release-bound finalizer over the support set.

    Selection is resolved deterministically from a synthetic hardware
    inventory through the shared resolver plan shape; the finalizer pins
    the attested inventory token and the installed package set to that
    selection, and boot-artifact build failures (initramfs) fail closed.
    """

    def _inventory(self, modalias: str = "pci:v000010ECd00008168sv0000sd0000bc02sc00i00") -> HardwareInventory:
        return HardwareInventory(
            devices=(
                HardwareDevice(
                    sysfs_path="/pci0000:00/device",
                    subsystem="pci",
                    modalias=modalias,
                    driver="r8169",
                ),
            ),
            truncated=False,
            scan_errors=0,
        )

    def _recommendations(self) -> tuple[HardwareSupportRecommendation, ...]:
        return (
            HardwareSupportRecommendation(
                "firmware-realtek",
                SupportKind.FIRMWARE,
                SupportDisposition.AUTO_ELIGIBLE,
                "synthetic-test",
            ),
            HardwareSupportRecommendation(
                "amd64-microcode",
                SupportKind.MICROCODE,
                SupportDisposition.AUTO_ELIGIBLE,
                "synthetic-test",
            ),
        )

    def _select(
        self,
        inventory: HardwareInventory,
        support: ReleaseSupportSet,
        *,
        recommendations: tuple[HardwareSupportRecommendation, ...] | None = None,
        complete: bool = True,
    ) -> ResolvedHardwareSelection:
        plan = HardwareSupportPlan(
            inventory.token,
            self._recommendations() if recommendations is None else recommendations,
            complete,
            (),
        )
        return resolve_hardware_selection(plan=plan, support=support)

    def _finalize_with_selection(
        self,
        root: Path,
        payload: bytes,
        inventory: HardwareInventory,
        support: ReleaseSupportSet,
        selection: ResolvedHardwareSelection,
        *,
        firmware: tuple[str, ...] | None = None,
        microcode: tuple[str, ...] | None = None,
        attestation: HardwareInventoryAttestation | None = None,
        artifact_builder: object = None,
    ) -> tuple[object, FakeSlotFilesystem]:
        write, destination, store, _ = _write_happy(root, payload)
        try:
            mount_dir = root / "mnt"
            mount_dir.mkdir(exist_ok=True)
            _populate_slot_completeness(mount_dir)
            filesystem = FakeSlotFilesystem(mount_dir)
            receipt = SlotFinalizer().finalize(
                write=write,
                destination=destination,
                filesystem=filesystem,
                package_installer=FakeSlotPackageInstaller(support),
                inventory=(
                    attestation
                    if attestation is not None
                    else HardwareInventoryAttestation.from_inventory(inventory)
                ),
                support=support,
                profile_policy=_policy(),
                firmware_packages=(
                    selection.firmware if firmware is None else firmware
                ),
                microcode_packages=(
                    selection.microcode if microcode is None else microcode
                ),
                selection=selection,
                artifact_builder=artifact_builder,  # type: ignore[arg-type]
            )
            return receipt, filesystem
        finally:
            store.close()

    def test_selection_is_deterministic_for_synthetic_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._inventory()
            support = _support()
            first = self._select(inventory, support)
            second = self._select(inventory, support)
            self.assertEqual(first, second)
            self.assertEqual(first.inventory_token, inventory.token)
            self.assertEqual(first.firmware, ("firmware-realtek",))
            self.assertEqual(first.microcode, ("amd64-microcode",))

            payload = _payload()
            receipt, filesystem = self._finalize_with_selection(
                root, payload, inventory, support, first
            )
            assert isinstance(receipt, slot_module.FinalizationReceipt)
            self.assertEqual(receipt.inventory_token, inventory.token)
            self.assertEqual(
                [package.name for package in receipt.packages],
                ["amd64-microcode", "firmware-realtek"],
            )
            # FINALIZED_GENERIC artifacts: generic kernel is the verified
            # base digest; the host initramfs binds base + inventory + set.
            stored = json.loads(
                filesystem.files["boot/finalized-generic.json"].decode("utf-8")
            )
            self.assertEqual(
                stored["generic_kernel_sha256"], hashlib.sha256(payload).hexdigest()
            )
            self.assertEqual(
                stored["host_initramfs_sha256"], receipt.host_initramfs_sha256
            )
            self.assertEqual(
                stored, DeterministicBootArtifactBuilder().build(
                    base_sha256=receipt.base_sha256,
                    inventory_token=inventory.token,
                    packages_digest=receipt.packages_digest,
                ).as_dict(),
            )
            # The GRUB A/B entries boot these adapter-owned aliases; a
            # finalized slot that only carried the generic payload names
            # would install successfully and then fail to boot.
            self.assertEqual(
                filesystem.files["boot/vmlinuz-greia"], b"generic-kernel"
            )
            self.assertEqual(
                filesystem.files["boot/initramfs-greia.img"],
                b"generic-initramfs",
            )

    def test_package_set_drift_from_selection_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._inventory()
            support = _support()
            selection = self._select(inventory, support)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                filesystem = FakeSlotFilesystem(mount_dir)
                with self.assertRaisesRegex(SlotFinalizeError, "resolved hardware selection"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=HardwareInventoryAttestation.from_inventory(inventory),
                        support=support,
                        profile_policy=_policy(),
                        firmware_packages=(),
                        microcode_packages=selection.microcode,
                        selection=selection,
                    )
                self.assertEqual(filesystem.ops, [])
                self.assertIsNone(filesystem.bound_uuid)
            finally:
                store.close()

    def test_inventory_token_mismatch_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            support = _support()
            selection = self._select(self._inventory(), support)
            other = self._inventory(modalias="pci:v00008086d00001234sv0000sd0000bc02sc00i00")
            self.assertNotEqual(other.token, selection.inventory_token)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                filesystem = FakeSlotFilesystem(mount_dir)
                with self.assertRaisesRegex(SlotFinalizeError, "attested inventory"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=HardwareInventoryAttestation.from_inventory(other),
                        support=support,
                        profile_policy=_policy(),
                        firmware_packages=selection.firmware,
                        microcode_packages=selection.microcode,
                        selection=selection,
                    )
                self.assertEqual(filesystem.ops, [])
                self.assertIsNone(filesystem.bound_uuid)
                self.assertFalse(filesystem.expanded)
            finally:
                store.close()

    def test_missing_provider_and_incomplete_plan_refused(self) -> None:
        inventory = self._inventory()
        support = _support()
        rogue = (
            HardwareSupportRecommendation(
                "firmware-evil",
                SupportKind.FIRMWARE,
                SupportDisposition.AUTO_ELIGIBLE,
                "synthetic-test",
            ),
        )
        with self.assertRaisesRegex(SlotFinalizeError, "no release provider"):
            self._select(inventory, support, recommendations=rogue)
        with self.assertRaisesRegex(SlotFinalizeError, "incomplete"):
            self._select(inventory, support, complete=False)
        # Advisory-only plans select nothing but stay deterministic.
        advisory = (
            HardwareSupportRecommendation(
                "firmware-realtek",
                SupportKind.HARDWARE_PACKAGE,
                SupportDisposition.ADVISORY,
                "synthetic-test",
            ),
        )
        empty = self._select(inventory, support, recommendations=advisory)
        self.assertEqual(empty.firmware, ())
        self.assertEqual(empty.microcode, ())

    def test_corrupted_support_set_refused_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                # Corrupted set: digest no longer binds the signed member.
                foreign = _support(digest="1" * 64)
                filesystem = FakeSlotFilesystem(mount_dir)
                with self.assertRaisesRegex(SlotFinalizeError, "not the release-bound"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(foreign),
                        inventory=_inventory(),
                        support=foreign,
                        profile_policy=_policy(),
                    )
                self.assertEqual(filesystem.ops, [])
                self.assertIsNone(filesystem.bound_uuid)
            finally:
                store.close()

    def test_over_capacity_refused_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = _payload(4096)
            member = _member(payload)
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            store = LoopbackSlotFile.create(root / "slot.img", destination.slot_capacity_bytes)
            try:
                lean = SlotWriter(growth_bytes=0, metadata_reserve_bytes=0)
                write = lean.write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,
                    support_installed_bytes=destination.slot_capacity_bytes - len(payload),
                )
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                filesystem = FakeSlotFilesystem(mount_dir)
                oversized = replace(
                    _support(),
                    installed_size_bound=destination.slot_capacity_bytes,
                )
                with self.assertRaisesRegex(SlotFinalizeError, "headroom"):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(oversized),
                        inventory=_inventory(),
                        support=oversized,
                        profile_policy=_policy(),
                    )
                self.assertEqual(filesystem.ops, [])
                self.assertIsNone(filesystem.bound_uuid)
            finally:
                store.close()

    def test_initramfs_build_failure_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._inventory()
            support = _support()
            selection = self._select(inventory, support)
            with self.assertRaisesRegex(SlotFinalizeError, "boot artifact build failed"):
                self._finalize_with_selection(
                    root,
                    _payload(4096),
                    inventory,
                    support,
                    selection,
                    artifact_builder=_FailingArtifactBuilder(),
                )
            # A builder returning the wrong shape fails closed as well.
            # NOTE: fresh staged write per attempt (capabilities are single-use).
            with tempfile.TemporaryDirectory() as second:
                root2 = Path(second)
                with self.assertRaisesRegex(SlotFinalizeError, "invalid result"):
                    self._finalize_with_selection(
                        root2,
                        _payload(4096),
                        inventory,
                        support,
                        selection,
                        artifact_builder=_WrongShapeArtifactBuilder(),
                    )
            with self.assertRaisesRegex(SlotFinalizeError, "invalid"):
                SlotBootArtifacts(
                    generic_kernel_sha256="not-hex",
                    host_initramfs_sha256="0" * 64,
                )

    def test_initramfs_failure_still_unmounts_and_syncs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._inventory()
            support = _support()
            selection = self._select(inventory, support)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                _populate_slot_completeness(mount_dir)
                filesystem = FakeSlotFilesystem(mount_dir)
                with self.assertRaises(SlotFinalizeError):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=HardwareInventoryAttestation.from_inventory(inventory),
                        support=support,
                        profile_policy=_policy(),
                        firmware_packages=selection.firmware,
                        microcode_packages=selection.microcode,
                        selection=selection,
                        artifact_builder=_FailingArtifactBuilder(),
                    )
                # Mount/install already ran, so cleanup must still detach.
                self.assertEqual(filesystem.unmount_count, 1)
                self.assertEqual(filesystem.sync_count, 1)
                self.assertFalse(filesystem.mounted)
                self.assertNotIn(
                    "etc/greia-os/finalization-receipt.json", filesystem.files
                )
            finally:
                store.close()

    def test_refusal_paths_leave_zero_ops(self) -> None:
        # Reviewer-1 hardening: every gate before capability consumption
        # must leave the destination seam untouched.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                support = _support()
                # Unapproved package request.
                refused = FakeSlotFilesystem(mount_dir)
                with self.assertRaises(SlotFinalizeError):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=refused,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                        firmware_packages=("firmware-evil",),
                    )
                self.assertEqual(refused.ops, [])
                # Profile policy mismatch.
                refused = FakeSlotFilesystem(mount_dir)
                with self.assertRaises(SlotFinalizeError):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=refused,
                        package_installer=FakeSlotPackageInstaller(support),
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(slot_bytes=1024),
                    )
                self.assertEqual(refused.ops, [])
            finally:
                store.close()

    def test_no_ambient_network_or_apt_trust_in_finalization_path(self) -> None:
        repo = Path(slot_module.__file__).resolve().parent.parent.parent
        platform_source = (repo / "src/greia_platform/slot_writer.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "urllib",
            "socket",
            "http://",
            "https://",
            "sources.list",
            "Acquire::",
        ):
            self.assertNotIn(forbidden, platform_source)
        # No APT invocation lives in the shared platform path: the only
        # apt/dpkg surface is the bounded presence smoke (fixed path
        # stats, no command run, no sources, no network).
        self.assertNotIn("subprocess", platform_source)
        self.assertNotIn("apt-get update", platform_source)
        self.assertNotIn("apt-get install", platform_source)
        self.assertNotIn("apt-get clean", platform_source)
        self.assertNotIn("Dir::Etc::sourcelist", platform_source)
        # The only apt/dpkg surface in the shared finalizer is the bounded
        # slot-completeness presence smoke (real userspace incl. usable
        # apt-get/dpkg files). It stats fixed paths only: no invocation,
        # no sources, no network.
        self.assertIn("usr/bin/apt-get", platform_source)
        self.assertIn("usr/bin/dpkg", platform_source)
        self.assertIn("REQUIRED_SLOT_COMPLETENESS_FILES", platform_source)
        self.assertIn("check_slot_completeness", platform_source)
        adapter_source = (repo / "src/greia_installer/slots.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("urllib", "socket", "http://", "https://"):
            self.assertNotIn(forbidden, adapter_source)
        # The only APT surface reachable from finalization is the pinned
        # release-pool install, with host sources disabled and no network
        # host allow-listed.
        installer_source = (
            repo / "src/greia_installer/hardware_support_install.py"
        ).read_text(encoding="utf-8")
        self.assertIn("Dir::Etc::sourcelist", installer_source)
        self.assertIn("sourceparts=-", installer_source)
        for forbidden in ("http://", "https://", "deb.debian.org", "sources.list.d"):
            self.assertNotIn(forbidden, installer_source)


class SlotCompletenessTests(unittest.TestCase):
    """T03 slot-completeness smoke: V12G-like slot fails before QEMU/boot."""

    def test_d6_minimal_shape_fails_with_named_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "slot"
            root.mkdir()
            _populate_d6_minimal(root)
            missing = slot_module.slot_completeness_missing(root)
            # No /usr, no apt-get: the D6 failure shape is named exactly.
            self.assertIn("usr", missing)
            self.assertIn("usr/bin/apt-get", missing)
            self.assertIn("usr/bin/dpkg", missing)
            self.assertIn("opt/greia-os", missing)
            with self.assertRaisesRegex(
                SlotFinalizeError, "slot completeness smoke failed"
            ):
                slot_module.check_slot_completeness(root)
            try:
                slot_module.check_slot_completeness(root)
            except SlotFinalizeError as exc:
                self.assertIn("usr/bin/apt-get", str(exc))
            else:  # pragma: no cover
                self.fail("D6 skeleton passed the completeness smoke")

    def test_populated_userspace_passes_without_boot_or_qemu(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "slot"
            root.mkdir()
            _populate_slot_completeness(root)
            self.assertEqual(slot_module.slot_completeness_missing(root), ())
            # No exception, no boot/QEMU surface involved.
            slot_module.check_slot_completeness(root)

    def test_single_removed_command_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "slot"
            root.mkdir()
            _populate_slot_completeness(root)
            self.assertEqual(slot_module.slot_completeness_missing(root), ())
            (root / "usr/bin/apt-get").unlink()
            missing = slot_module.slot_completeness_missing(root)
            self.assertEqual(missing, ("usr/bin/apt-get",))
            with self.assertRaisesRegex(SlotFinalizeError, "usr/bin/apt-get"):
                slot_module.check_slot_completeness(root)

    def test_symlink_command_leaf_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "slot"
            root.mkdir()
            _populate_slot_completeness(root)
            target = root / "usr/bin/apt-get"
            target.unlink()
            target.symlink_to("/bin/true")
            self.assertIn(
                "usr/bin/apt-get", slot_module.slot_completeness_missing(root)
            )
            with self.assertRaisesRegex(SlotFinalizeError, "usr/bin/apt-get"):
                slot_module.check_slot_completeness(root)

    def test_finalizer_refuses_incomplete_before_boot_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                _populate_d6_minimal(mount_dir)
                filesystem = FakeSlotFilesystem(mount_dir)
                support = _support()
                installer = FakeSlotPackageInstaller(support)
                with self.assertRaisesRegex(
                    SlotFinalizeError, "slot completeness smoke failed"
                ):
                    SlotFinalizer().finalize(
                        write=write,
                        destination=destination,
                        filesystem=filesystem,
                        package_installer=installer,
                        inventory=_inventory(),
                        support=support,
                        profile_policy=_policy(),
                    )
                # Fail-closed before boot assets: no support install ran,
                # no finalized files accepted, candidate cannot become bootable.
                self.assertEqual(installer.calls, [])
                self.assertNotIn(
                    "boot/finalized-generic.json", filesystem.files
                )
                self.assertNotIn(
                    "etc/greia-os/release-identity.json", filesystem.files
                )
                self.assertNotIn(
                    "etc/greia-os/finalization-receipt.json", filesystem.files
                )
                self.assertIn("completeness", filesystem.ops)
                self.assertNotIn("health", filesystem.ops)
                # Mount/install already ran, so cleanup still detaches.
                self.assertEqual(filesystem.unmount_count, 1)
                self.assertEqual(filesystem.sync_count, 1)
                self.assertFalse(filesystem.mounted)
            finally:
                store.close()

    def test_completeness_gate_runs_before_support_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write, destination, store, _ = _write_happy(root, _payload(4096))
            try:
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                _populate_slot_completeness(mount_dir)
                filesystem = FakeSlotFilesystem(mount_dir)
                support = _support()
                installer = FakeSlotPackageInstaller(support)
                SlotFinalizer().finalize(
                    write=write,
                    destination=destination,
                    filesystem=filesystem,
                    package_installer=installer,
                    inventory=_inventory(),
                    support=support,
                    profile_policy=_policy(),
                )
                ops = filesystem.ops
                self.assertLess(ops.index("completeness"), ops.index("health"))
                self.assertEqual(len(installer.calls), 1)
            finally:
                store.close()

    def test_single_shared_implementation_no_duplicate(self) -> None:
        repo = Path(slot_module.__file__).resolve().parent.parent.parent
        platform_source = (repo / "src/greia_platform/slot_writer.py").read_text(
            encoding="utf-8"
        )
        block_source = (repo / "src/greia_platform/block_slots.py").read_text(
            encoding="utf-8"
        )
        # One definition of the required-path set and the check.
        self.assertEqual(
            platform_source.count("REQUIRED_SLOT_COMPLETENESS_FILES"), 3
        )
        self.assertIn("def check_slot_completeness", platform_source)
        self.assertIn("def slot_completeness_missing", platform_source)
        # Production seam delegates to the shared implementation.
        self.assertIn("check_slot_completeness", block_source)
        self.assertNotIn("REQUIRED_SLOT_COMPLETENESS_FILES = ", block_source)
        self.assertNotIn("def check_slot_completeness", block_source)
        # Build-time staging gate keeps its own distinct payload-identity
        # paths; it must not duplicate the slot-completeness set.
        build_source = (repo / "tools/build_release.py").read_text(encoding="utf-8")
        self.assertNotIn("REQUIRED_SLOT_COMPLETENESS", build_source)
        self.assertNotIn("slot_completeness_missing", build_source)


class _FailingArtifactBuilder:
    """Boot-artifact backend whose initramfs rebuild explodes."""

    def build(
        self, *, base_sha256: str, inventory_token: str, packages_digest: str
    ) -> SlotBootArtifacts:
        raise RuntimeError("simulated initramfs rebuild failure")


class _WrongShapeArtifactBuilder:
    """Boot-artifact backend returning an unusable result shape."""

    def build(
        self, *, base_sha256: str, inventory_token: str, packages_digest: str
    ) -> object:
        return {"generic_kernel_sha256": base_sha256}


class SharedSeamTests(unittest.TestCase):
    def test_no_shell_dd_or_device_surface(self) -> None:
        source = Path(slot_module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "os.system",
            "os.popen",
            "os.exec",
            "shell=True",
            "shell =",
            "/dev/",
        ):
            self.assertNotIn(forbidden, source)

    def test_installer_reuses_the_shared_implementation(self) -> None:
        self.assertIs(installer_slots.SlotWriter, SlotWriter)
        self.assertIs(installer_slots.SlotFinalizer, SlotFinalizer)
        self.assertIs(installer_slots.VerifiedBaseSlotWrite, VerifiedBaseSlotWrite)

    def test_installer_adapter_converts_pool_without_copying_logic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_root = _make_pool(root)
            pool = VerifiedHardwareSupportPool.load(pool_root)
            support = installer_slots.pool_to_support_set(
                pool,
                support_digest="2" * 64,
                support_size=128,
            )
            self.assertEqual(
                support.provided_firmware, frozenset({"firmware-realtek"})
            )
            self.assertEqual(
                support.provided_microcode, frozenset({"amd64-microcode"})
            )
            self.assertEqual(
                support.require_firmware(("firmware-realtek",)),
                ("firmware-realtek",),
            )
            with self.assertRaises(SlotFinalizeError):
                support.require_firmware(("amd64-microcode",))

    def test_installer_adapter_delegates_to_existing_installer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_root = _make_pool(root)
            pool = VerifiedHardwareSupportPool.load(pool_root)
            target_root = root / "target"
            target_root.mkdir()
            mounted: list[Path] = []
            adapter = installer_slots.InstallerSlotPackageInstaller(
                runner=_RecordingRunner(),
                target_root=target_root,
                pool=pool,
                mounted=mounted,
            )
            installed = adapter.install(("firmware-realtek",), ())
            self.assertEqual([package.name for package in installed], ["firmware-realtek"])
            # The existing installer mounts the minimal chroot filesystems apt
            # needs (dev, proc, sys, run) plus the read-only support pool, and
            # records every one in the caller-owned list for reverse cleanup.
            self.assertEqual(
                mounted,
                [
                    target_root / "dev",
                    target_root / "proc",
                    target_root / "sys",
                    target_root / "run",
                    target_root / "run/greia-hardware-support",
                ],
            )
            self.assertFalse((target_root / "run/greia-hardware-support.list").exists())
            with self.assertRaises(Exception):
                adapter.install(("firmware-evil",), ())


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _make_pool(root: Path) -> Path:
    pool = root / "support"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    firmware = deb_dir / "firmware-realtek_1_all.deb"
    firmware.write_bytes(_FW_PAYLOAD)
    microcode = deb_dir / "amd64-microcode_1_amd64.deb"
    microcode.write_bytes(_UC_PAYLOAD)
    packages_payload = b"Package: firmware-realtek\n"
    packages_gzip_payload = b"gzip-placeholder"
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 2,
        "total_bytes": len(_FW_PAYLOAD) + len(_UC_PAYLOAD),
        "total_installed_bytes": len(_FW_PAYLOAD) + len(_UC_PAYLOAD) + 2 * 32 * 1024,
        "provided_candidate_packages": ["firmware-realtek", "amd64-microcode"],
        "provided_firmware_packages": ["firmware-realtek"],
        "provided_microcode_packages": ["amd64-microcode"],
        "broad_firmware_packages": ["firmware-realtek"],
        "firmware_providers": {"rtl.bin": ["firmware-realtek"]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-realtek",
                "version": "1",
                "architecture": "all",
                "filename": "pool/firmware-realtek_1_all.deb",
                "size": len(_FW_PAYLOAD),
                "sha256": _sha(_FW_PAYLOAD),
                "candidate": True,
                "installed_bytes": len(_FW_PAYLOAD) + 32 * 1024,
            },
            {
                "package": "amd64-microcode",
                "version": "1",
                "architecture": "amd64",
                "filename": "pool/amd64-microcode_1_amd64.deb",
                "size": len(_UC_PAYLOAD),
                "sha256": _sha(_UC_PAYLOAD),
                "candidate": True,
                "installed_bytes": len(_UC_PAYLOAD) + 32 * 1024,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_payload), "sha256": _sha(packages_payload)},
            "Packages.gz": {
                "size": len(packages_gzip_payload),
                "sha256": _sha(packages_gzip_payload),
            },
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


class _RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: object, *, check: bool = True) -> None:
        assert isinstance(command, (list, tuple))
        self.commands.append([str(part) for part in command])
        return None


if __name__ == "__main__":
    unittest.main()
