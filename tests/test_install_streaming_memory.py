"""T2-STREAM: true streaming install path with 768 MiB gate (D33/D53).

Preregistered acceptance (frozen before observation):
- P1 streaming-vs-buffered: tracemalloc peak for consuming the payload via
  ``open_bundle_payload_stream`` stays bounded (~chunk scale, <4 MiB for a
  32 MiB payload) while the legacy whole-buffering control
  (``ZipFile.read -> BytesIO``) peaks at ~payload scale (>= payload bytes).
  Peak must NOT scale ~1:1 with payload: peak(32MiB)-peak(8MiB) < 25% of the
  24 MiB delta.
- P2 archive lifetime: the stream stays readable after the factory returns
  (archive not closed early), yields byte-identical payload digest, and
  closes both member and archive deterministically on success and failure.
- P3 size bounded before write: manifest/size skew is refused at stream open
  (before any slot byte is written); unbounded read() is refused fail-closed.
- P4 stream errors propagate as transaction failure: truncated/corrupt
  payload mid-stream raises FreshAbInstallError (via SlotWriteError), never
  an unhandled OSError/BadZipFile, with handles closed.
- P5 whole-path memory: ``execute_fresh_ab_install`` peak (verification,
  decompression, slot write, readback, finalization, PERSIST, GRUB, journal)
  with file-backed slot storage does not scale 1:1 with payload and stays
  far below payload size at 32 MiB.
- P6 no second copy on disk: streaming creates no extracted payload file;
  no full uncompressed allocation helper (``archive.read(PAYLOAD)``) remains
  in the production seam.

Production proof: all memory/stream assertions drive the real production
entry points (``open_bundle_payload_stream`` + ``SlotWriter.write`` +
``execute_fresh_ab_install``), not helper return values.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import tracemalloc
import unittest
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from greia_installer.disk import DeviceObservation
from greia_installer.fresh_ab_install import (
    BundlePayloadStream,
    FreshAbInstallError,
    FreshAbInstallRequest,
    FreshAbInstallSeams,
    execute_fresh_ab_install,
    open_bundle_payload_stream,
)
from greia_installer.layout import ProfileSizing
from greia_installer.persist import PersistCommandResult, PersistCommandRunner
from greia_platform.slot_writer import (
    DestinationSlot,
    LoopbackSlotFile,
    SlotFinalizeError,
    SlotWriteError,
    SlotWriter,
    VerifiedReleaseMember,
)
from greia_platform.system_updates import (
    PAYLOAD_NAME,
    build_persistent_state_contract_bytes,
    build_update_bundle,
    generate_ed25519_keypair,
    inspect_update_bundle,
)

GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024

_PROFILE = "legacy-x86-i686"
_FAMILY = "legacy-x86"
_ARCH = "i386"
_SIGNER = "greia-release-main"
_INSTALL_SHA = "ab" * 32
_PASSWORD_HASH = "grub.pbkdf2.sha512.10000." + "A" * 128
_HW_BYTES = b"\x28\xb5\x2f\xfd" + b"hwset-payload" * 64
_SUPPORT_BOUND = 1 * MIB

_SMALL = 8 * MIB
_LARGE = 32 * MIB


def _payload(size: int) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _build_bundle(root: Path, payload: bytes, *, sequence: int):
    private = root / f"priv-{sequence}.pem"
    public = root / f"pub-{sequence}.pem"
    generate_ed25519_keypair(private, public)
    payload_path = root / f"payload-{sequence}.bin"
    payload_path.write_bytes(payload)
    hw_path = root / f"hw-{sequence}.tar.zst"
    hw_path.write_bytes(_HW_BYTES)
    contract_path = root / f"contract-{sequence}.json"
    contract_path.write_bytes(build_persistent_state_contract_bytes())
    bundle = root / f"r{sequence}.greiaupdate"
    build_update_bundle(
        payload_path=payload_path,
        hardware_support_path=hw_path,
        persistent_contract_path=contract_path,
        output_path=bundle,
        version="0.15.0",
        release_id=f"greia-0.15.{sequence}",
        release_sequence=sequence,
        platform_family=_FAMILY,
        architecture=_ARCH,
        profile=_PROFILE,
        signer=_SIGNER,
        private_key_path=private,
        minimum_slot_bytes=len(payload) + MIB,
    )
    key_dir = root / f"trusted-{sequence}"
    key_dir.mkdir(exist_ok=True)
    (key_dir / f"{_SIGNER}.pem").write_bytes(public.read_bytes())
    return bundle, key_dir


def _consume_fully(stream, *, chunk: int = 64 * 1024) -> int:
    total = 0
    while True:
        piece = stream.read(chunk)
        if not piece:
            break
        total += len(piece)
    return total


def _peak_of(func):
    tracemalloc.start()
    try:
        result = func()
        _current, peak = tracemalloc.get_traced_memory()
        return result, peak
    finally:
        tracemalloc.stop()


class _DiscardingStorage:
    """SlotStorage stand-in that hashes and discards (no Python-heap copy)."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self.written = 0

    @property
    def capacity_bytes(self) -> int:
        return self._capacity

    def write_at(self, offset: int, data: bytes) -> None:
        if offset < 0 or offset + len(data) > self._capacity or not data:
            raise SlotWriteError("slot store write is outside the slot range")
        self.written += len(data)

    def read_at(self, offset: int, length: int) -> bytes:
        raise AssertionError("discarding storage has no readback; use file storage")

    def flush(self) -> None:
        pass


class RecordingPartitionRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command) -> None:
        self.commands.append(list(command))
        return None


class FakeSlotFilesystem:
    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.bound_uuid: str | None = None
        self.mounted = False
        self.files: dict[str, bytes] = {}

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.bound_uuid = filesystem_uuid

    def expand_to_capacity(self) -> None:
        pass

    def mount(self) -> Path:
        self.mounted = True
        self.mount_dir.mkdir(parents=True, exist_ok=True)
        return self.mount_dir

    def unmount(self) -> None:
        self.mounted = False

    def sync(self) -> None:
        pass

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise SlotFinalizeError("slot writes require a mounted destination")
        self.files[relative_path] = bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_health(self) -> None:
        pass


class FakePackageInstaller:
    def install(self, firmware, microcode):
        if tuple(firmware) or tuple(microcode):
            raise AssertionError("empty support set installs nothing")
        return ()


class FakePersistRunner(PersistCommandRunner):
    def __init__(self, *, readback_uuid: str) -> None:
        self.commands: list[list[str]] = []
        self._readback = readback_uuid
        self._blkid_calls = 0

    def run(self, command) -> PersistCommandResult:
        self.commands.append(list(command))
        if command[0] == "blkid":
            self._blkid_calls += 1
            if self._blkid_calls == 1:
                return PersistCommandResult(stdout="", returncode=1)
            return PersistCommandResult(stdout=self._readback, returncode=0)
        if command[0] in ("mkfs.ext4", "mount", "umount"):
            return PersistCommandResult(stdout="", returncode=0)
        raise AssertionError(f"unexpected PERSIST command: {command[0]}")


def _target() -> DeviceObservation:
    return DeviceObservation(
        name="sda",
        path=Path("/dev/sda"),
        size_bytes=8 * GIB,
        device_type="disk",
        model="Test disk",
        serial="SERIAL-1",
        transport="sata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="WWN-1",
        major_minor="8:0",
    )


_MBR_SIGNATURE = "a1b2c3d4"


def _observed_mbr_identities(signature: str = _MBR_SIGNATURE):
    """Scheme-explicit observed MBR identities (T3-INSTALL/D51)."""
    return {
        "system-a": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{signature}-02",
            "filesystem_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        },
        "system-b": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{signature}-03",
            "filesystem_uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
        },
        "persist": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{signature}-04",
            "filesystem_uuid": "dddddddd-dddd-dddd-dddd-ddddddddddd4",
        },
    }


def _sizing(slot_bytes: int = 1 * GIB) -> ProfileSizing:
    return ProfileSizing(
        layout_adapter_id="legacy-bios-ab-v1",
        slot_bytes=slot_bytes,
        persist_minimum_bytes=256 * MIB,
        boot_backend="grub-ab-v1",
    )


class StreamingSeamTests(unittest.TestCase):
    """P2/P3/P4/P6: production seam behavior, lifetime, bounds, errors."""

    def test_stream_yields_identical_bytes_and_closes_deterministically(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-stream-seam-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        payload = _payload(2 * MIB)
        bundle, _key_dir = _build_bundle(root, payload, sequence=41)
        expected_digest = hashlib.sha256(payload).hexdigest()

        stream = open_bundle_payload_stream(bundle)
        self.assertIsInstance(stream, BundlePayloadStream)
        # Archive lifetime spans consumption: readable immediately, no early close.
        self.assertFalse(stream.closed)
        digest = hashlib.sha256()
        total = 0
        while True:
            piece = stream.read(64 * 1024)
            if not piece:
                break
            digest.update(piece)
            total += len(piece)
        self.assertEqual(total, len(payload))
        self.assertEqual(digest.hexdigest(), expected_digest)
        stream.close()
        self.assertTrue(stream.closed)
        # Deterministic double-close is safe.
        stream.close()
        with self.assertRaises(FreshAbInstallError):
            stream.read(64 * 1024)

    def test_stream_context_manager_closes_on_success(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-stream-ctx-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        bundle, _key_dir = _build_bundle(root, _payload(1 * MIB), sequence=42)
        with open_bundle_payload_stream(bundle) as stream:
            self.assertEqual(_consume_fully(stream), 1 * MIB)
        self.assertTrue(stream.closed)

    def test_unbounded_read_refused_fail_closed(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-stream-unbounded-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        bundle, _key_dir = _build_bundle(root, _payload(256 * 1024), sequence=43)
        stream = open_bundle_payload_stream(bundle)
        try:
            with self.assertRaises(FreshAbInstallError):
                stream.read()
            with self.assertRaises(FreshAbInstallError):
                stream.read(-1)
        finally:
            stream.close()

    def test_size_skew_refused_before_any_slot_write(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-stream-skew-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        bundle, _key_dir = _build_bundle(root, _payload(1 * MIB), sequence=44)
        manifest = inspect_update_bundle(bundle).manifest
        # Wrong expected size (TOCTOU guard) must refuse at open, before write.
        with self.assertRaises(FreshAbInstallError):
            open_bundle_payload_stream(bundle, expected_size=manifest.payload_size + 1)

    def test_truncated_payload_propagates_as_transaction_failure(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-stream-trunc-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        payload = _payload(1 * MIB)
        bundle, _key_dir = _build_bundle(root, payload, sequence=45)
        manifest = inspect_update_bundle(bundle).manifest
        member = VerifiedReleaseMember.from_manifest(manifest)
        observed = _observed_mbr_identities()
        destination = DestinationSlot(
            semantic_slot="A",
            role="system-a",
            slot_capacity_bytes=1 * GIB,
            active_slot=None,
            accepted_slot=None,
            layout_id="legacy-bios-ab-v1",
            role_filesystem_uuid=observed["system-a"]["filesystem_uuid"],
            other_role_filesystem_uuid=observed["system-b"]["filesystem_uuid"],
        )

        class _Truncated:
            def read(self, size: int = -1) -> bytes:
                return b""  # immediate EOF: shorter than the signed size

            def close(self) -> None:
                pass

        writer = SlotWriter()
        with self.assertRaises(SlotWriteError):
            writer.write(
                member=member,
                destination=destination,
                source=_Truncated(),  # type: ignore[arg-type]
                storage=_DiscardingStorage(1 * GIB),
                support_installed_bytes=_SUPPORT_BOUND,
            )

    def test_mid_stream_oserror_becomes_fresh_install_failure(self) -> None:
        """Production proof: OSError mid-stream -> FreshAbInstallError."""
        directory = tempfile.mkdtemp(prefix="t2-stream-txnerr-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        payload = _payload(1 * MIB)
        bundle, key_dir = _build_bundle(root, payload, sequence=47)
        manifest = inspect_update_bundle(bundle).manifest
        observed = _observed_mbr_identities()
        persist_stage = root / "persist-stage"
        persist_stage.mkdir()
        boot_control = root / "boot-control"
        backend_state = root / "backend-state"
        journal = root / "journal"
        mount_dir = root / "mnt"
        for directory_path in (boot_control, backend_state, journal):
            directory_path.mkdir()
        slot_file = root / "slot-a.bin"
        storage = LoopbackSlotFile.create(slot_file, 1 * GIB)
        self.addCleanup(storage.close)
        filesystem = FakeSlotFilesystem(mount_dir)
        runner = RecordingPartitionRunner()
        persist_runner = FakePersistRunner(
            readback_uuid=observed["persist"]["filesystem_uuid"]
        )

        closed = {"value": False}

        class _Interrupting:
            def __init__(self) -> None:
                self._real = open_bundle_payload_stream(
                    bundle, expected_size=len(payload)
                )

            def read(self, size: int = -1) -> bytes:
                data = self._real.read(size)
                if data:
                    # Fail after the first chunk: simulates a torn ZIP read.
                    self._real.close()
                    raise OSError("simulated interrupted payload stream")
                return data

            def close(self) -> None:
                closed["value"] = True
                self._real.close()

        seams = FreshAbInstallSeams(
            partition_runner=runner,  # type: ignore[arg-type]
            slot_storage_factory=lambda _role: storage,
            slot_filesystem_factory=lambda: filesystem,
            package_installer_factory=FakePackageInstaller,
            inventory_token="cd" * 32,
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
            support_installed_bound=_SUPPORT_BOUND,
            persist_runner=persist_runner,
            persist_stage_dir=persist_stage,
            persist_uuid_factory=lambda: uuid.UUID(
                observed["persist"]["filesystem_uuid"]
            ),
            boot_control_dir=boot_control,
            backend_state_dir=backend_state,
            journal_dir=journal,
            payload_stream_factory=_Interrupting,
        )
        request = FreshAbInstallRequest(
            bundle_path=bundle,
            trusted_key_dir=key_dir,
            expected_profile_id=_PROFILE,
            expected_platform_family=_FAMILY,
            expected_architecture=_ARCH,
            sizing=_sizing(),
            target=_target(),
            support_installed_bytes=_SUPPORT_BOUND,
            install_target_sha256=_INSTALL_SHA,
            password_hash=_PASSWORD_HASH,
            installed_at_unix=1757000000,
            fresh_identities=observed,
        )
        with self.assertRaises(FreshAbInstallError):
            execute_fresh_ab_install(request, seams)
        self.assertTrue(closed["value"])
        # No finalization happened: no receipt files were bound.
        self.assertEqual(filesystem.files, {})

    def test_no_whole_buffering_path_in_production_seam(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src/greia_installer/fresh_ab_install.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("archive.read(PAYLOAD_NAME)", source)
        self.assertNotIn("BytesIO(data)", source)
        self.assertNotIn("from io import BytesIO", source)

    def test_no_second_extracted_copy_on_disk(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-stream-nocopy-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        payload = _payload(2 * MIB)
        bundle, _key_dir = _build_bundle(root, payload, sequence=46)
        before = {path.name for path in root.iterdir()}
        stream = open_bundle_payload_stream(bundle)
        try:
            self.assertEqual(_consume_fully(stream), len(payload))
        finally:
            stream.close()
        after = {path.name for path in root.iterdir()}
        self.assertEqual(before, after)


class StreamingMemoryTests(unittest.TestCase):
    """P1/P5: bounded peak vs payload-scale positive control (tracemalloc)."""

    def test_streaming_peak_bounded_positive_control_scales(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-stream-mem-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        small = _payload(_SMALL)
        large = _payload(_LARGE)
        small_bundle, _ = _build_bundle(root, small, sequence=51)
        large_bundle, _ = _build_bundle(root, large, sequence=52)

        def _stream_peak(bundle: Path, size: int) -> int:
            def _run() -> int:
                stream = open_bundle_payload_stream(
                    bundle, expected_size=size
                )
                try:
                    return _consume_fully(stream)
                finally:
                    stream.close()

            total, peak = _peak_of(_run)
            self.assertEqual(total, size)
            return peak

        def _buffered_peak(bundle: Path, size: int) -> int:
            # Positive control: the pre-T2 whole-buffering path.
            def _run() -> int:
                with zipfile.ZipFile(bundle, "r") as archive:
                    data = archive.read(PAYLOAD_NAME)
                stream = BytesIO(data)
                total = _consume_fully(stream)
                stream.close()
                return total

            total, peak = _peak_of(_run)
            self.assertEqual(total, size)
            return peak

        small_stream = _stream_peak(small_bundle, _SMALL)
        large_stream = _stream_peak(large_bundle, _LARGE)
        large_buffered = _buffered_peak(large_bundle, _LARGE)

        # Streaming stays at chunk scale for a 32 MiB payload.
        self.assertLess(
            large_stream,
            4 * MIB,
            f"streaming peak {large_stream} exceeds chunk-scale bound for 32MiB payload",
        )
        # Positive control proves the detector is sensitive: whole-buffering
        # peaks at payload scale.
        self.assertGreaterEqual(
            large_buffered,
            _LARGE,
            f"positive control peak {large_buffered} does not reach payload scale",
        )
        # Peak does not scale ~1:1 with payload: 24 MiB more payload must add
        # less than 25% of the delta to the streaming peak.
        delta_payload = _LARGE - _SMALL
        delta_peak = abs(large_stream - small_stream)
        self.assertLess(
            delta_peak,
            delta_payload // 4,
            f"streaming peak scales with payload: delta_peak={delta_peak} delta_payload={delta_payload}",
        )

    def test_whole_path_peak_does_not_scale_with_payload(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-stream-wholepath-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)

        def _install_peak(payload: bytes, sequence: int) -> int:
            case = root / f"case-{sequence}"
            case.mkdir()
            bundle, key_dir = _build_bundle(case, payload, sequence=sequence)
            manifest = inspect_update_bundle(bundle).manifest
            observed = _observed_mbr_identities()
            persist_stage = case / "persist-stage"
            persist_stage.mkdir()
            boot_control = case / "boot-control"
            backend_state = case / "backend-state"
            journal = case / "journal"
            mount_dir = case / "mnt"
            for directory_path in (boot_control, backend_state, journal):
                directory_path.mkdir()
            slot_file = case / "slot-a.bin"
            storage = LoopbackSlotFile.create(slot_file, 1 * GIB)
            filesystem = FakeSlotFilesystem(mount_dir)
            runner = RecordingPartitionRunner()
            persist_runner = FakePersistRunner(
                readback_uuid=observed["persist"]["filesystem_uuid"]
            )
            seams = FreshAbInstallSeams(
                partition_runner=runner,  # type: ignore[arg-type]
                slot_storage_factory=lambda _role: storage,
                slot_filesystem_factory=lambda: filesystem,
                package_installer_factory=FakePackageInstaller,
                inventory_token="cd" * 32,
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
                support_installed_bound=_SUPPORT_BOUND,
                persist_runner=persist_runner,
                persist_stage_dir=persist_stage,
                persist_uuid_factory=lambda: uuid.UUID(
                    observed["persist"]["filesystem_uuid"]
                ),
                boot_control_dir=boot_control,
                backend_state_dir=backend_state,
                journal_dir=journal,
            )
            request = FreshAbInstallRequest(
                bundle_path=bundle,
                trusted_key_dir=key_dir,
                expected_profile_id=_PROFILE,
                expected_platform_family=_FAMILY,
                expected_architecture=_ARCH,
                sizing=_sizing(),
                target=_target(),
                support_installed_bytes=_SUPPORT_BOUND,
                install_target_sha256=_INSTALL_SHA,
                password_hash=_PASSWORD_HASH,
                installed_at_unix=1757000000,
                fresh_identities=observed,
            )

            def _run():
                return execute_fresh_ab_install(request, seams)

            try:
                _result, peak = _peak_of(_run)
            finally:
                storage.close()
            self.assertEqual(_result.bytes_written, len(payload))
            return peak

        small_peak = _install_peak(_payload(_SMALL), 61)
        large_peak = _install_peak(_payload(_LARGE), 62)
        # Whole path (verify + decompress + write + readback + finalize +
        # PERSIST + GRUB + journal) must stay far below the 32 MiB payload and
        # must not grow ~1:1 with the 24 MiB payload delta.
        self.assertLess(
            large_peak,
            _LARGE,
            f"whole-path peak {large_peak} reaches payload scale (32MiB)",
        )
        self.assertLess(
            abs(large_peak - small_peak),
            (_LARGE - _SMALL) // 2,
            f"whole-path peak scales with payload: small={small_peak} large={large_peak}",
        )


if __name__ == "__main__":
    unittest.main()
