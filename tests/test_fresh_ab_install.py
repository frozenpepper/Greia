"""X8-INSTALL source-scope tests: fresh signed-release install to SYSTEM_A.

Phase 8B Step 8B.3 at source scope (Acer/QEMU execution deferred RED per the
source-first amendment): the orchestrator, its failure ordering and its
health-gated acceptance are proven on fakes with zero disk contact. No
loop devices, no partitions, no mounts, no subprocesses, no valued media.

Coverage:

- happy path consumes a real signed ``.greiaupdate`` v2 bundle (built +
  signature-verified in-test), streams SYSTEM_A through the shared
  ``SlotWriter``/``SlotFinalizer``, initializes PERSIST exactly once,
  installs the stable GRUB backend from the trusted record and writes
  ``FIRST_INSTALL_PENDING``; SYSTEM_B storage is never addressed;
- capacity/signature/profile/support refusals all fire **before** the first
  destructive partition command;
- acceptance commits only after an observed boot of A; failed health leaves
  the persistent default A in place (first install is not A/B rollback);
- the privileged install-transaction protocol routes EXECUTE through the
  same nonce+digest revalidation to the A/B executor when configured, and
  invalidation still never reaches destruction.
"""

from __future__ import annotations

import hashlib
import importlib.util
import shutil
import tempfile
import unittest
import uuid
from io import BytesIO
from pathlib import Path

from support_artifacts import valid_hardware_support_archive_bytes

from greia_installer.disk import (
    DeviceObservation,
    DiskInventory,
    LiveMediaAncestry,
    PcInternalTargetPolicy,
)
from greia_installer.fresh_ab_install import (
    AbExecutorFacts,
    FreshAbInstallError,
    FreshAbInstallRequest,
    FreshAbInstallSeams,
    accept_first_install,
    build_ab_executor,
    execute_fresh_ab_install,
)
from greia_installer.layout import (
    ProfileSizing,
    mint_fresh_partition_identities,
)
from greia_installer.persist import PersistCommandResult, PersistCommandRunner
from greia_installer.transaction_service import (
    InstallTransactionService,
    PlatformInstallAuthority,
    ServiceState,
    TransactionServiceError,
)
from greia_installer.transaction_client import (
    InstallTransactionClient,
    TransactionClientError,
)
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionCoordinator,
    BootTransactionError,
    BootTransactionJournal,
    BootTransactionState,
    FakeGrubBackend,
)
from greia_platform.grub_ab import GrubEnvBackend, validate_grub_ab_text
from greia_platform.privileged_channel import PeerCredential
from greia_platform.slot_writer import SlotFinalizeError
from greia_platform.system_updates import (
    build_update_bundle,
    inspect_update_bundle,
)

HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None

GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024

_PROFILE = "legacy-x86-i686"
_FAMILY = "legacy-x86"
_ARCH = "i386"
_INSTALL_SHA = "ab" * 32
_PASSWORD_HASH = "grub.pbkdf2.sha512.10000." + "A" * 128
_HW_BODY = b"hwset-payload" * 64
_HW_BYTES = valid_hardware_support_archive_bytes(architecture="i386")
_SUPPORT_BOUND = 1 * MIB


def _payload(size: int = 128 * 1024) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _target(size_bytes: int = 8 * GIB) -> DeviceObservation:
    return DeviceObservation(
        name="sda",
        path=Path("/dev/sda"),
        size_bytes=size_bytes,
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


def _sizing(slot_bytes: int = 1 * GIB) -> ProfileSizing:
    return ProfileSizing(
        layout_adapter_id="legacy-bios-ab-v1",
        slot_bytes=slot_bytes,
        persist_minimum_bytes=256 * MIB,
        boot_backend="grub-ab-v1",
    )


#: Observed legacy-MBR disk signature shared by every role (the T1-IDENT
#: observed ``<disk-signature>-<NN>`` form; never a minted UUID4).
_MBR_SIGNATURE = "a1b2c3d4"

#: Filesystem UUID the orchestration generates for PERSIST (role-owned, read
#: back through the persist runner; PARTUUIDs are the observed identities).
_PERSIST_FS_UUID = "cccccccc-cccc-cccc-cccc-ccccccccccc3"
_BOOT_CONTROL_FS_UUID = "dddddddd-dddd-dddd-dddd-dddddddddddd"


def _observed_mbr_identities(signature: str = _MBR_SIGNATURE):
    """Return scheme-explicit observed MBR identities for the legacy roles."""
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
            "filesystem_uuid": _PERSIST_FS_UUID,
        },
    }


def _observed_gpt_identities():
    """Return scheme-explicit observed GPT identities (canonical GUIDs)."""
    return {
        "system-a": {
            "scheme": "GPT_GUID",
            "partuuid": "11111111-1111-1111-1111-1111111111a1",
            "filesystem_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        },
        "system-b": {
            "scheme": "GPT_GUID",
            "partuuid": "22222222-2222-2222-2222-2222222222b2",
            "filesystem_uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
        },
        "persist": {
            "scheme": "GPT_GUID",
            "partuuid": "33333333-3333-3333-3333-3333333333c3",
            "filesystem_uuid": _PERSIST_FS_UUID,
        },
    }


class RecordingPartitionRunner:
    """Narrow adapter runner: records argument arrays, touches nothing."""

    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command) -> None:
        assert isinstance(command, list), "partition commands must be argument arrays"
        assert all(isinstance(word, str) and word for word in command)
        self.commands.append(list(command))
        return None


class SparseSlotStorage:
    """Destination-only sparse byte store: capacity-checked, never dense."""

    def __init__(self, capacity_bytes: int) -> None:
        self._capacity = capacity_bytes
        self._chunks: dict[int, bytes] = {}
        self.flushes = 0

    @property
    def capacity_bytes(self) -> int:
        return self._capacity

    def write_at(self, offset: int, data: bytes) -> None:
        if offset < 0 or offset + len(data) > self._capacity or not data:
            raise AssertionError("slot store write outside range")
        self._chunks[offset] = bytes(data)

    def read_at(self, offset: int, length: int) -> bytes:
        if offset < 0 or length <= 0 or offset + length > self._capacity:
            raise AssertionError("slot store read outside range")
        assembled = bytearray(length)
        for start, chunk in self._chunks.items():
            overlap_start = max(offset, start)
            overlap_end = min(offset + length, start + len(chunk))
            if overlap_start < overlap_end:
                assembled[
                    overlap_start - offset : overlap_end - offset
                ] = chunk[overlap_start - start : overlap_end - start]
        return bytes(assembled)

    def flush(self) -> None:
        self.flushes += 1


class FakeSlotFilesystem:
    """Destination-only fake: records mutations, writes slot-local files."""

    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.ops: list[str] = []
        self.files: dict[str, bytes] = {}
        self.bound_uuid: str | None = None
        self.mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.ops.append("bind")
        self.bound_uuid = filesystem_uuid

    def expand_to_capacity(self) -> None:
        self.ops.append("expand")

    def mount(self) -> Path:
        self.ops.append("mount")
        if self.mounted:
            raise SlotFinalizeError("slot is already mounted")
        self.mounted = True
        self.mount_dir.mkdir(parents=True, exist_ok=True)
        # Simulate a staged slot carrying real Greia userspace so the
        # shared completeness smoke passes (an empty mount would be a
        # V12G-like skeleton). Uses the shared validator's path set.
        from greia_platform.slot_writer import (
            REQUIRED_SLOT_COMPLETENESS_DIRS,
            REQUIRED_SLOT_COMPLETENESS_FILES,
        )

        for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
            (self.mount_dir / rel_path).mkdir(parents=True, exist_ok=True)
        for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
            candidate = self.mount_dir / rel_path
            candidate.parent.mkdir(parents=True, exist_ok=True)
            if candidate.is_symlink() or not candidate.is_file():
                candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
                try:
                    candidate.chmod(0o755)
                except OSError:
                    pass
        return self.mount_dir

    def unmount(self) -> None:
        self.ops.append("unmount")
        self.mounted = False

    def sync(self) -> None:
        self.ops.append("sync")

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise SlotFinalizeError("slot writes require a mounted destination")
        self.ops.append(f"write:{relative_path}")
        self.files[relative_path] = bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_completeness(self) -> None:
        from greia_platform.slot_writer import check_slot_completeness

        self.ops.append("completeness")
        check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        self.ops.append("health")


class FakePackageInstaller:
    """Empty support-set installer: approved sets install to nothing."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def install(self, firmware, microcode):  # type: ignore[no-untyped-def]
        firmware = tuple(firmware)
        microcode = tuple(microcode)
        self.calls.append((firmware, microcode))
        if firmware or microcode:
            raise AssertionError("empty support set installs nothing")
        return ()


class FakePersistRunner(PersistCommandRunner):
    """Stateful PERSIST fake: scripted blkid, recorded mkfs/mount/umount."""

    def __init__(self, *, readback_uuid: str) -> None:
        self.commands: list[list[str]] = []
        self._readback = readback_uuid
        self._blkid_calls = 0
        self.active_mounts: set[Path] = set()

    def run(self, command) -> PersistCommandResult:
        assert isinstance(command, list), "PERSIST commands must be argument arrays"
        assert all(isinstance(word, str) and word for word in command)
        self.commands.append(list(command))
        name = command[0]
        if name == "blkid":
            if command[-1] == "/dev/sda1":
                return PersistCommandResult(
                    stdout=_BOOT_CONTROL_FS_UUID, returncode=0
                )
            self._blkid_calls += 1
            if self._blkid_calls == 1:
                return PersistCommandResult(stdout="", returncode=1)
            return PersistCommandResult(stdout=self._readback, returncode=0)
        if name in ("mkfs.ext4", "mount", "umount"):
            if name == "mount":
                self.active_mounts.add(Path(command[-1]))
            elif name == "umount":
                self.active_mounts.discard(Path(command[-1]))
            return PersistCommandResult(stdout="", returncode=0)
        raise AssertionError(f"unexpected PERSIST command: {name}")

    def names(self) -> list[str]:
        return [command[0] for command in self.commands]


class FreshAbInstallTests(unittest.TestCase):
    def _bundle(self, root: Path, payload: bytes, *, sequence: int = 11) -> Path:
        import zstandard

        compressed = zstandard.ZstdCompressor(level=3).compress(payload)
        payload_path = root / "payload.ext4.zst"
        payload_path.write_bytes(compressed)
        hw_path = root / "hw.tar.zst"
        hw_path.write_bytes(_HW_BYTES)
        bundle = root / f"r{sequence}.greiaupdate"
        if bundle.exists():
            bundle.unlink()
        build_update_bundle(
            payload_path=payload_path,
            hardware_support_path=hw_path,
            output_path=bundle,
            version="0.15.0",
            release_id="greia-0.15.0",
            platform_family=_FAMILY,
            architecture=_ARCH,
            profile=_PROFILE,
            payload_uncompressed_bytes=len(payload),
            minimum_slot_bytes=len(payload) + MIB,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
        )
        return bundle

    def _harness(self, root: Path, payload: bytes):
        bundle = self._bundle(root, payload)
        manifest = inspect_update_bundle(bundle).manifest
        observed = _observed_mbr_identities()
        persist_stage = root / "persist-stage"
        persist_stage.mkdir()
        boot_control = root / "boot-control"
        boot_control.mkdir()
        branding = root / "branding"
        branding.mkdir()
        (branding / "greia-theme.txt").write_text(
            'title-text: ""\ndesktop-image: "greia-boot-logo.png"\n',
            encoding="utf-8",
        )
        (branding / "greia-boot-logo.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + b"0" * 64
        )
        backend_state = boot_control / "grub"
        journal = persist_stage / "greia" / "boot-journal"
        mount_dir = root / "slot-a-mnt"
        touched: list[str] = []
        storage_holder: dict[str, SparseSlotStorage] = {}
        observer_calls: list[str] = []
        boot_installs: list[tuple[DeviceObservation, Path]] = []

        def _storage(role: str):  # type: ignore[no-untyped-def]
            touched.append(role)
            storage = SparseSlotStorage(1 * GIB)
            storage_holder[role] = storage
            return storage

        def _observer(target, plan):  # type: ignore[no-untyped-def]
            # Post-layout seam: invoked only after adapter.execute created
            # the identities; records ordering for sequencing proof.
            observer_calls.append("observe")
            return {role: dict(values) for role, values in observed.items()}

        filesystem = FakeSlotFilesystem(mount_dir)
        installer = FakePackageInstaller()
        runner = RecordingPartitionRunner()
        persist_runner = FakePersistRunner(readback_uuid=_PERSIST_FS_UUID)

        def _install_bios_bootloader(
            target: DeviceObservation, boot_directory: Path
        ) -> None:
            if boot_directory not in persist_runner.active_mounts:
                raise AssertionError("BIOS GRUB install ran outside the boot-control mount")
            if not (boot_directory / "grub" / "grub.cfg").is_file():
                raise AssertionError("BIOS GRUB install ran before config was written")
            for name in ("greia-theme.txt", "greia-boot-logo.png"):
                if not (boot_directory / "grub" / name).is_file():
                    raise AssertionError(f"BIOS GRUB install ran before {name} was copied")
            if GrubEnvBackend.attach(boot_directory / "grub").inspect().default_slot != "A":
                raise AssertionError("BIOS GRUB install ran before grubenv was initialized")
            boot_installs.append((target, boot_directory))

        seams = FreshAbInstallSeams(
            partition_runner=runner,  # type: ignore[arg-type]
            slot_storage_factory=_storage,
            slot_filesystem_factory=lambda: filesystem,
            package_installer_factory=lambda: installer,
            inventory_token="cd" * 32,
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
            support_installed_bound=_SUPPORT_BOUND,
            persist_runner=persist_runner,
            persist_stage_dir=persist_stage,
            persist_uuid_factory=lambda: uuid.UUID(_PERSIST_FS_UUID),
            boot_control_dir=boot_control,
            boot_branding_dir=branding,
            post_layout_identity_observer=_observer,
            bios_bootloader_installer=_install_bios_bootloader,
        )
        request = FreshAbInstallRequest(
            bundle_path=bundle,
            expected_profile_id=_PROFILE,
            expected_platform_family=_FAMILY,
            expected_architecture=_ARCH,
            sizing=_sizing(),
            target=_target(),
            support_installed_bytes=_SUPPORT_BOUND,
            install_target_sha256=_INSTALL_SHA,
            password_hash=_PASSWORD_HASH,
            installed_at_unix=1757000000,
        )
        return {
            "bundle": bundle,
            "manifest": manifest,
            "observed": observed,
            "seams": seams,
            "request": request,
            "runner": runner,
            "touched": touched,
            "filesystem": filesystem,
            "installer": installer,
            "persist_runner": persist_runner,
            "observer_calls": observer_calls,
            "boot_installs": boot_installs,
            "dirs": {
                "root": root,
                "boot_control": boot_control,
                "backend_state": backend_state,
                "journal": journal,
                "branding": branding,
            },
        }

    def _install(self, payload: bytes = _payload()):
        directory = tempfile.mkdtemp(prefix="x8-install-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        harness = self._harness(root, payload)
        result = execute_fresh_ab_install(harness["request"], harness["seams"])
        harness["result"] = result
        return harness

    def test_missing_boot_branding_fails_closed(self) -> None:
        directory = tempfile.mkdtemp(prefix="x8-install-branding-")
        self.addCleanup(shutil.rmtree, directory, True)
        harness = self._harness(Path(directory), _payload())
        (harness["dirs"]["branding"] / "greia-boot-logo.png").unlink()
        with self.assertRaisesRegex(FreshAbInstallError, "boot branding"):
            execute_fresh_ab_install(harness["request"], harness["seams"])

    # -- happy path ------------------------------------------------------

    def test_fresh_install_finalizes_a_leaves_b_inactive_and_pends(self) -> None:
        payload = _payload()
        harness = self._install(payload)
        result = harness["result"]
        observed = harness["observed"]

        self.assertEqual(result.receipt.slot, "A")
        self.assertEqual(result.receipt.release_id, "greia-0.15.0")
        self.assertEqual(result.bytes_written, len(payload))
        # Role UUID restored exactly from layout authority, never the template.
        self.assertEqual(
            result.receipt.filesystem_uuid, observed["system-a"]["filesystem_uuid"]
        )
        self.assertEqual(
            harness["filesystem"].bound_uuid, observed["system-a"]["filesystem_uuid"]
        )
        # SYSTEM_B storage never addressed: no second-slot duplication.
        self.assertEqual(harness["touched"], ["A"])

        record = result.record
        self.assertEqual(record.layout_id, "legacy-bios-ab-v1")
        self.assertEqual(record.boot_backend, "grub-ab-v1")
        self.assertEqual(record.accepted_slot, "A")
        self.assertEqual(record.boot_control.active_slot, "A")
        self.assertIsNotNone(record.system_b)
        self.assertEqual(record.accepted_release_id, "greia-0.15.0")
        self.assertEqual(record.slot_bytes, 1 * GIB)

        self.assertEqual(
            result.journal.state, BootTransactionState.FIRST_INSTALL_PENDING
        )
        self.assertTrue(result.journal.first_install)

        # Stable GRUB backend: two fixed entries from the trusted record.
        grub_cfg = harness["dirs"]["boot_control"] / "grub" / "grub.cfg"
        self.assertTrue(grub_cfg.is_file())
        text = grub_cfg.read_text(encoding="utf-8")
        self.assertEqual(text, result.grub_config_text)
        validate_grub_ab_text(text)
        self.assertIn(observed["system-a"]["partuuid"], text)
        self.assertIn(observed["system-b"]["partuuid"], text)
        for name in ("greia-theme.txt", "greia-boot-logo.png"):
            self.assertEqual(
                (harness["dirs"]["boot_control"] / "grub" / name).read_bytes(),
                (harness["dirs"]["branding"] / name).read_bytes(),
            )
        self.assertIn("set theme=$prefix/greia-theme.txt", text)
        backend = GrubEnvBackend.attach(harness["dirs"]["backend_state"])
        self.assertEqual(backend.inspect().default_slot, "A")
        self.assertIsNone(backend.inspect().one_shot_slot)

        # Production composition: fresh PERSIST creates the marker/layout
        # record; generated fstab maps those canonical sources into the
        # installed root; installed boot-health reads the same durable
        # first-install journal from the mounted PERSIST root.
        from greia_platform.fstab import (
            BOOT_CONTROL_MOUNTPOINT,
            PERSIST_BOOT_MOUNTPOINT,
            read_fstab_uuid_for_mount,
        )
        from greia_platform.persistent_layout import (
            PERSIST_SCHEMA_CURRENT,
            PERSIST_SCHEMA_MARKER_NAME,
            build_namespace_map,
            parse_persist_schema_marker,
            persist_mount_source_path,
            persist_record_path,
            persist_schema_marker_path,
        )

        persist_root = harness["dirs"]["root"] / "persist-stage"
        schema_path = persist_schema_marker_path(persist_root)
        layout_path = persist_record_path(persist_root)
        self.assertTrue(schema_path.is_file())
        self.assertEqual(
            parse_persist_schema_marker(schema_path.read_bytes()),
            PERSIST_SCHEMA_CURRENT,
        )
        self.assertTrue(layout_path.is_file())
        self.assertEqual(schema_path.name, PERSIST_SCHEMA_MARKER_NAME)

        fstab = harness["filesystem"].files["etc/fstab"].decode("ascii")
        fstab_path = harness["dirs"]["root"] / "finalized-fstab"
        fstab_path.write_text(fstab, encoding="ascii")
        self.assertEqual(
            read_fstab_uuid_for_mount(fstab_path, PERSIST_BOOT_MOUNTPOINT),
            harness["result"].record.persist.filesystem_uuid,
        )
        self.assertEqual(
            read_fstab_uuid_for_mount(fstab_path, BOOT_CONTROL_MOUNTPOINT),
            _BOOT_CONTROL_FS_UUID,
        )
        for mount in build_namespace_map().mount_plan():
            source = persist_mount_source_path(
                Path(PERSIST_BOOT_MOUNTPOINT), mount
            )
            row = next(
                fields
                for fields in (
                    line.split()
                    for line in fstab.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                )
                if len(fields) >= 2 and fields[1] == mount.target
            )
            self.assertEqual(row[0], str(source))
        self.assertEqual(
            persist_mount_source_path(
                Path(PERSIST_BOOT_MOUNTPOINT),
                next(
                    mount
                    for mount in build_namespace_map().mount_plan()
                    if mount.target == "/etc/greia-os/layout"
                ),
            ),
            Path(PERSIST_BOOT_MOUNTPOINT)
            / "greia"
            / "namespaces"
            / "layout-authority",
        )
        self.assertEqual(
            layout_path,
            persist_root
            / "greia"
            / "namespaces"
            / "layout-authority"
            / "installed-layout.json",
        )
        first_install_journal = persist_root / "greia" / "boot-journal"
        self.assertEqual(harness["dirs"]["journal"], first_install_journal)
        self.assertEqual(
            BootTransactionJournal.load(first_install_journal).as_dict(),
            result.journal.as_dict(),
        )
        self.assertFalse(
            (
                persist_root
                / "greia"
                / "namespaces"
                / "parent-credentials"
                / "boot-journal"
            ).exists()
        )
        boot_health = (
            Path(__file__).resolve().parents[1]
            / "build/overlay/etc/systemd/system/greia-boot-health.service"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Environment=GREIA_BOOT_JOURNAL_DIR=/run/greia-persist/greia/boot-journal",
            boot_health,
        )
        self.assertIn("RequiresMountsFor=/run/greia-persist", boot_health)
        self.assertIn("/run/greia-persist/greia/boot-journal", boot_health)

        self.assertTrue(
            (harness["filesystem"].mount_dir / "run/greia-persist").is_dir()
        )
        self.assertEqual(
            harness["boot_installs"],
            [(_target(), harness["dirs"]["boot_control"])],
        )
        self.assertEqual(harness["persist_runner"].active_mounts, set())

        # Partitioning happened through argument arrays only.
        names = [command[0] for command in harness["runner"].commands]
        self.assertIn("wipefs", names)
        self.assertIn("parted", names)
        self.assertIn("mkfs.ext4", names)
        for command in harness["runner"].commands:
            for word in command:
                for marker in (";", "&", "|", "$", "`", "(", ")", "<", ">", "\n"):
                    self.assertNotIn(marker, word)

    def test_no_second_slot_payload_or_receipt(self) -> None:
        harness = self._install()
        # Only one storage object ever existed, and only for A.
        self.assertEqual(harness["touched"], ["A"])
        # The B entry in the installed GRUB config points at B's own
        # layout-bound PARTUUID (inactive: selecting it before staging
        # simply fails to boot — the X8-GRUB seam, not a staged system).
        text = harness["result"].grub_config_text
        self.assertIn(harness["observed"]["system-b"]["partuuid"], text)

    def test_missing_bios_bootloader_seam_refuses_before_partitioning(self) -> None:
        harness = self._harness(Path(tempfile.mkdtemp(prefix="x8-no-bios-seam-")), _payload())
        self.addCleanup(shutil.rmtree, harness["dirs"]["root"], True)
        harness["seams"].bios_bootloader_installer = None
        with self.assertRaisesRegex(FreshAbInstallError, "refusing to erase"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertEqual(harness["runner"].commands, [])

    def test_bios_install_failure_propagates_and_detaches_boot_control(self) -> None:
        harness = self._harness(Path(tempfile.mkdtemp(prefix="x8-failed-bios-")), _payload())
        self.addCleanup(shutil.rmtree, harness["dirs"]["root"], True)

        def _fail_install(target: DeviceObservation, boot_directory: Path) -> None:
            self.assertEqual(target, harness["request"].target)
            self.assertIn(boot_directory, harness["persist_runner"].active_mounts)
            raise FreshAbInstallError("simulated grub-install failure")

        harness["seams"].bios_bootloader_installer = _fail_install
        with self.assertRaisesRegex(FreshAbInstallError, "simulated grub-install failure"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertEqual(harness["persist_runner"].active_mounts, set())
        self.assertEqual(harness["persist_runner"].commands[-1][0], "umount")

    # -- observed-identity binding (POSTR1-P2 post-layout sequencing) --------

    def _harness_with_observer(self, identities=None, *, explode=None):
        """Build a harness whose post-layout observer returns ``identities``.

        ``explode`` (an exception instance) makes the observer raise instead,
        proving observation failure aborts before any SYSTEM_A payload write.
        """
        harness = self._fresh_harness()
        if explode is not None:

            def _exploding(target, plan):  # type: ignore[no-untyped-def]
                raise explode

            harness["seams"].post_layout_identity_observer = _exploding
            return harness

        mapping = (
            {role: dict(values) for role, values in identities.items()}
            if identities is not None
            else _observed_mbr_identities()
        )

        def _observer(target, plan):  # type: ignore[no-untyped-def]
            return {role: dict(values) for role, values in mapping.items()}

        harness["seams"].post_layout_identity_observer = _observer
        return harness

    def _fresh_harness(self, payload: bytes | None = None):
        directory = tempfile.mkdtemp(prefix="x8-install-")
        self.addCleanup(shutil.rmtree, directory, True)
        return self._harness(Path(directory), _payload() if payload is None else payload)

    def test_observed_mbr_identities_bound_to_record(self) -> None:
        harness = self._install()
        result = harness["result"]
        observed = harness["observed"]
        record = result.record
        self.assertEqual(record.system_a.partuuid, observed["system-a"]["partuuid"])
        self.assertEqual(
            record.system_b.partuuid, observed["system-b"]["partuuid"]  # type: ignore[union-attr]
        )
        self.assertEqual(record.persist.partuuid, observed["persist"]["partuuid"])
        self.assertEqual(record.system_a.scheme, "MBR_PARTUUID")
        # One disk signature across every bound role (no cross-disk binding).
        self.assertEqual(record.system_a.disk_signature, _MBR_SIGNATURE)
        self.assertEqual(record.system_b.disk_signature, _MBR_SIGNATURE)  # type: ignore[union-attr]
        self.assertEqual(record.persist.disk_signature, _MBR_SIGNATURE)
        # Role filesystem UUID restored exactly from the observed identities.
        self.assertEqual(
            result.receipt.filesystem_uuid,
            observed["system-a"]["filesystem_uuid"],
        )
        # Post-layout sequencing: partitioning ran, then the observer fired.
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["observer_calls"], ["observe"])

    def test_uuid4_as_mbr_partuuid_refused_after_partitioning(self) -> None:
        harness = self._harness_with_observer(mint_fresh_partition_identities())
        with self.assertRaisesRegex(FreshAbInstallError, "not authoritative"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        # Partitioning already ran (identities exist only after layout),
        # but no SYSTEM_A payload byte was written.
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    def test_missing_observer_refused_before_destruction(self) -> None:
        harness = self._fresh_harness()
        harness["seams"].post_layout_identity_observer = None
        with self.assertRaisesRegex(FreshAbInstallError, "post-layout identity observer"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertEqual(harness["runner"].commands, [])

    def test_retired_caller_supplied_identities_refused(self) -> None:
        import dataclasses

        harness = self._fresh_harness()
        bad = dataclasses.replace(
            harness["request"], fresh_identities=_observed_mbr_identities()
        )
        with self.assertRaisesRegex(FreshAbInstallError, "no longer accepts"):
            execute_fresh_ab_install(bad, harness["seams"])
        self.assertEqual(harness["runner"].commands, [])

    def test_observer_failure_aborts_before_system_a_write(self) -> None:
        harness = self._harness_with_observer(
            explode=RuntimeError("blkid reported no disk signature")
        )
        with self.assertRaisesRegex(FreshAbInstallError, "not authoritative"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    def test_partition_number_mismatch_refused_after_partitioning(self) -> None:
        swapped = _observed_mbr_identities()
        swapped["system-a"] = dict(swapped["system-a"], partuuid=f"{_MBR_SIGNATURE}-03")
        swapped["system-b"] = dict(swapped["system-b"], partuuid=f"{_MBR_SIGNATURE}-02")
        harness = self._harness_with_observer(swapped)
        with self.assertRaisesRegex(FreshAbInstallError, "partition number"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    def test_gpt_execution_still_deferred_before_observation(self) -> None:
        import dataclasses

        harness = self._fresh_harness()
        gpt_sizing = ProfileSizing(
            layout_adapter_id="modern-gpt-ab-v1",
            slot_bytes=1 * GIB,
            persist_minimum_bytes=256 * MIB,
            boot_backend="grub-ab-v1",
        )
        request = dataclasses.replace(
            harness["request"],
            sizing=gpt_sizing,
        )
        # The refusal below is the deferred Phase-8C GPT execution, not the
        # identity gate: the adapter fails before the observer ever fires.
        with self.assertRaisesRegex(FreshAbInstallError, "partitioning failed"):
            execute_fresh_ab_install(request, harness["seams"])
        self.assertEqual(harness["runner"].commands, [])

    def test_mbr_partuuid_rejected_for_gpt_adapter(self) -> None:
        import dataclasses

        harness = self._fresh_harness()
        gpt_sizing = ProfileSizing(
            layout_adapter_id="modern-gpt-ab-v1",
            slot_bytes=1 * GIB,
            persist_minimum_bytes=256 * MIB,
            boot_backend="grub-ab-v1",
        )
        request = dataclasses.replace(
            harness["request"],
            sizing=gpt_sizing,
        )
        with self.assertRaises(FreshAbInstallError):
            execute_fresh_ab_install(request, harness["seams"])
        self.assertEqual(harness["runner"].commands, [])

    def test_explicit_wrong_scheme_refused_after_partitioning(self) -> None:
        observed = _observed_mbr_identities()
        mismatched = {
            role: dict(values, scheme="GPT_GUID") for role, values in observed.items()
        }
        harness = self._harness_with_observer(mismatched)
        with self.assertRaisesRegex(FreshAbInstallError, "scheme"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    def test_mixed_mbr_disk_signature_refused_after_partitioning(self) -> None:
        observed = _observed_mbr_identities()
        mixed = {role: dict(values) for role, values in observed.items()}
        mixed["system-b"] = dict(mixed["system-b"], partuuid="deadbeef-03")
        harness = self._harness_with_observer(mixed)
        with self.assertRaisesRegex(FreshAbInstallError, "cross-disk"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    # -- refusal ordering: nothing destructive before preflight ------------

    def test_undersized_support_bound_refused_before_destruction(self) -> None:
        directory = tempfile.mkdtemp(prefix="x8-install-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        harness = self._harness(root, _payload())
        request = harness["request"]
        bad = FreshAbInstallRequest(
            bundle_path=request.bundle_path,
            expected_profile_id=_PROFILE,
            expected_platform_family=_FAMILY,
            expected_architecture=_ARCH,
            sizing=request.sizing,
            target=request.target,
            support_installed_bytes=2 * GIB,
            install_target_sha256=_INSTALL_SHA,
            password_hash=_PASSWORD_HASH,
        )
        bad_seams = harness["seams"]
        bad_seams.support_installed_bound = 2 * GIB
        with self.assertRaises(FreshAbInstallError):
            execute_fresh_ab_install(bad, bad_seams)
        self.assertEqual(harness["runner"].commands, [])

    def test_tampered_bundle_refused_before_destruction(self) -> None:
        directory = tempfile.mkdtemp(prefix="x8-install-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        harness = self._harness(root, _payload())
        raw = bytearray(harness["bundle"].read_bytes())
        raw[len(raw) // 2] ^= 0xFF
        harness["bundle"].write_bytes(bytes(raw))
        with self.assertRaises(FreshAbInstallError):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertEqual(harness["runner"].commands, [])

    def test_old_signed_bundle_refused_before_destruction(self) -> None:
        import json as _json
        import zipfile as _zipfile

        directory = tempfile.mkdtemp(prefix="x8-install-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        harness = self._harness(root, _payload())
        old = harness["bundle"]
        with _zipfile.ZipFile(old, "w", compression=_zipfile.ZIP_STORED) as archive:
            archive.writestr(
                "manifest.json",
                (
                    _json.dumps(
                        {
                            "schema_version": 2,
                            "release_id": "greia-0.14.0",
                            "version": "0.14.0",
                            "platform_family": _FAMILY,
                            "architecture": _ARCH,
                            "profile": _PROFILE,
                            "payload": {
                                "name": "payload.bin",
                                "sha256": "0" * 64,
                                "size": 4,
                                "kind": "system-slot-image",
                            },
                            "release_notes": "",
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode(),
            )
            archive.writestr("manifest.sig", b"{}")
            archive.writestr("payload.bin", b"data")
        with self.assertRaises(FreshAbInstallError) as ctx:
            execute_fresh_ab_install(harness["request"], harness["seams"])
        message = str(ctx.exception).lower()
        self.assertIn("v3", message)
        self.assertEqual(harness["runner"].commands, [])

    def test_profile_mismatch_refused_before_destruction(self) -> None:
        directory = tempfile.mkdtemp(prefix="x8-install-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        harness = self._harness(root, _payload())
        request = harness["request"]
        bad = FreshAbInstallRequest(
            bundle_path=request.bundle_path,
            expected_profile_id="modern-amd64",
            expected_platform_family=_FAMILY,
            expected_architecture=_ARCH,
            sizing=request.sizing,
            target=request.target,
            support_installed_bytes=_SUPPORT_BOUND,
            install_target_sha256=_INSTALL_SHA,
            password_hash=_PASSWORD_HASH,
        )
        with self.assertRaises(FreshAbInstallError):
            execute_fresh_ab_install(bad, harness["seams"])
        self.assertEqual(harness["runner"].commands, [])

    def test_foreign_support_set_refused_before_destruction(self) -> None:
        directory = tempfile.mkdtemp(prefix="x8-install-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        harness = self._harness(root, _payload())
        harness["seams"].support_digest = "00" * 32
        with self.assertRaises(FreshAbInstallError):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertEqual(harness["runner"].commands, [])

    def test_active_journal_claimed_exactly_once(self) -> None:
        harness = self._install()
        journal_dir = harness["dirs"]["journal"]
        artifact_a = BootArtifactSet.from_finalization(
            receipt=harness["result"].receipt, record=harness["result"].record
        )
        # The install already claimed the journal: a second claim refuses.
        with self.assertRaises(Exception):
            BootTransactionJournal.begin_first_install(
                journal_dir,
                layout_id="legacy-bios-ab-v1",
                boot_backend="grub-ab-v1",
                release_id="greia-0.15.0",
            )
        self.assertEqual(
            BootTransactionJournal.load(journal_dir).state,
            BootTransactionState.FIRST_INSTALL_PENDING,
        )
        self.assertEqual(artifact_a.slot, "A")

    # -- health-gated acceptance ------------------------------------------

    def test_acceptance_requires_observed_boot_of_a(self) -> None:
        harness = self._install()
        dirs = harness["dirs"]
        artifact_a = BootArtifactSet.from_finalization(
            receipt=harness["result"].receipt, record=harness["result"].record
        )
        backend = GrubEnvBackend.attach(dirs["backend_state"])
        # No authoritative boot observation yet: acceptance refuses.
        with self.assertRaises(FreshAbInstallError):
            accept_first_install(
                journal_dir=dirs["journal"], backend=backend, artifact_a=artifact_a
            )
        # First boot of A (fresh default, no one-shot): health commits it.
        self.assertEqual(backend.simulate_reboot(), "A")
        journal = accept_first_install(
            journal_dir=dirs["journal"], backend=backend, artifact_a=artifact_a
        )
        self.assertEqual(journal.state, BootTransactionState.ACCEPTED)
        self.assertEqual(
            GrubEnvBackend.attach(dirs["backend_state"]).inspect().default_slot, "A"
        )

    def test_first_install_needs_no_one_shot_arm(self) -> None:
        harness = self._install()
        dirs = harness["dirs"]
        artifact_a = BootArtifactSet.from_finalization(
            receipt=harness["result"].receipt, record=harness["result"].record
        )
        backend = GrubEnvBackend.attach(dirs["backend_state"])
        coordinator = BootTransactionCoordinator.begin_first_install(
            journal_dir=dirs["journal"] / "arm-probe",
            backend=backend,
            artifact_a=artifact_a,
        )
        with self.assertRaises(BootTransactionError):
            coordinator.arm()

    def test_failed_health_leaves_default_a_without_rollback(self) -> None:
        harness = self._install()
        dirs = harness["dirs"]
        artifact_a = BootArtifactSet.from_finalization(
            receipt=harness["result"].receipt, record=harness["result"].record
        )
        backend = GrubEnvBackend.attach(dirs["backend_state"])
        probe_dir = dirs["journal"] / "failed-probe"
        probe_dir.mkdir(parents=True)
        coordinator = BootTransactionCoordinator.begin_first_install(
            journal_dir=probe_dir, backend=backend, artifact_a=artifact_a
        )
        self.assertEqual(backend.simulate_reboot(), "A")
        coordinator.observe_boot()
        coordinator.mark_failed("post-intro interactive health never confirmed")
        self.assertEqual(coordinator.journal.state, BootTransactionState.FAILED)
        self.assertEqual(backend.inspect().default_slot, "A")
        with self.assertRaises(BootTransactionError):
            coordinator.commit()

    def test_fake_backend_acceptance_mirrors_grubenv(self) -> None:
        harness = self._install()
        artifact_a = BootArtifactSet.from_finalization(
            receipt=harness["result"].receipt, record=harness["result"].record
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            coordinator = BootTransactionCoordinator.begin_first_install(
                journal_dir=root / "journal", backend=backend, artifact_a=artifact_a
            )
            self.assertEqual(
                coordinator.journal.state, BootTransactionState.FIRST_INSTALL_PENDING
            )
            self.assertEqual(backend.simulate_reboot(), "A")
            coordinator.observe_boot()
            coordinator.commit()
            self.assertEqual(coordinator.journal.state, BootTransactionState.ACCEPTED)


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "signed bundles need cryptography")
class AbServiceRoutingTests(unittest.TestCase):
    """Narrow-protocol EXECUTE reaches the A/B executor only when live."""

    def _service(self, devices, *, ab_executor=None):
        from greia_installer.disk import DiskInventory

        probe_calls: list[int] = []

        class _Probe:
            def __init__(self) -> None:
                self.calls = 0

            def probe(self):  # type: ignore[no-untyped-def]
                self.calls += 1
                probe_calls.append(self.calls)
                return DiskInventory(tuple(devices), generation=self.calls)

        class _Resolver:
            def resolve(self, inventory=None):  # type: ignore[no-untyped-def]
                return LiveMediaAncestry.empty()

        project_root = Path(__file__).resolve().parents[1]
        state = ServiceState(
            payload=Path("/run/live/medium/payload/greia-rootfs.squashfs"),
            payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
            project_root=project_root,
            compatible_profile_id="profile-test",
            platform_family="legacy-x86",
            architecture="i386",
            target_policy_id="pc-internal-v1",
            layout_adapter_id="legacy-bios-ab-v1",
            boot_backend="grub-ab-v1",
            slot_bytes=1 * GIB,
            persist_minimum_bytes=256 * MIB,
        )
        authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile="profile-test",
            probe=_Probe(),  # type: ignore[arg-type]
            live_resolver=_Resolver(),  # type: ignore[arg-type]
        )
        return InstallTransactionService(
            authority=authority,
            state=state,
            ab_executor=ab_executor,
            install_mode="ab" if ab_executor is not None else "legacy-single",
        )

    def _disk(self):
        return _target()

    def _prepare_via_client(self, service, extra_settings=None):
        client = InstallTransactionClient(
            lambda raw: service.handle_request(
                raw, peer=PeerCredential(uid=65534), boot_state="installer_ready"
            )
        )
        snapshot = {
            "touchpad_tap": "false",
            "touchpad_speed": "0.35",
            "mouse_speed": "0.0",
            "natural_scrolling": "false",
            "resolution": "auto",
            "keyboard_layout": "us",
            "mic_gain": "2.0",
            "disable_while_typing": "false",
            "locale": "en",
        }
        snapshot.update(extra_settings or {})
        return client, client.prepare(
            expected_target_identity=service.authority.list_targets()[0].identity_digest,
            compatible_profile_id="profile-test",
            settings_snapshot=snapshot,
        )

    def test_execute_routes_to_ab_executor_with_revalidated_facts(self) -> None:
        from greia_installer.engine import InstallResult

        seen: dict[str, object] = {}

        def _executor(authorization, settings, locale, target):  # type: ignore[no-untyped-def]
            seen["identity"] = authorization.target_identity
            seen["locale"] = locale
            seen["target"] = target
            return InstallResult()

        service = self._service([self._disk()], ab_executor=_executor)
        client, prepared = self._prepare_via_client(service)
        receipt = client.execute(
            transaction_nonce=prepared.transaction_nonce,
            plan_digest=prepared.plan_digest,
        )
        self.assertEqual(receipt.target_identity, seen["identity"])
        self.assertEqual(seen["locale"], "en")
        self.assertIsInstance(seen["target"], DeviceObservation)
        self.assertEqual(service._last_installed_identity, seen["identity"])

    def test_execute_passes_authorized_wifi_to_ab_executor(self) -> None:
        from greia_installer.engine import InstallResult
        from greia_installer.wifi import WifiSecurity
        from greia_installer.wifi_carryover import WifiCarryoverChoice
        seen = []

        def executor(_authorization, _settings, locale, _target, *, progress, wifi_carryover):
            seen.append((locale, wifi_carryover))
            return InstallResult()
        executor.accepts_wifi_carryover = True
        service = self._service([self._disk()], ab_executor=executor)
        choice = WifiCarryoverChoice("Family", WifiSecurity.PERSONAL)
        client, prepared = self._prepare_via_client(service, {"locale": "it", **choice.snapshot_fields()})
        client.execute(transaction_nonce=prepared.transaction_nonce, plan_digest=prepared.plan_digest)
        self.assertEqual(seen, [("it", choice)])

    def test_invalidation_never_reaches_ab_executor(self) -> None:
        calls: list[object] = []

        def _executor(*args):  # type: ignore[no-untyped-def]
            calls.append(args)
            from greia_installer.engine import InstallResult

            return InstallResult()

        service = self._service([self._disk()], ab_executor=_executor)
        client, prepared = self._prepare_via_client(service)
        with self.assertRaises(TransactionClientError):
            client.execute(
                transaction_nonce=prepared.transaction_nonce,
                plan_digest="ff" * 32,
            )
        self.assertEqual(calls, [])

    def test_ab_entry_without_executor_refuses(self) -> None:
        service = self._service([self._disk()])
        client, prepared = self._prepare_via_client(service)
        # Socket EXECUTE without an executor still serves the legacy path,
        # but the explicit A/B entry refuses fail-closed.
        with self.assertRaises(TransactionServiceError):
            service.execute_ab_install(
                transaction_nonce=prepared.transaction_nonce,
                plan_digest=prepared.plan_digest,
            )

    def test_executor_factory_wires_request_from_service_facts(self) -> None:
        import zstandard

        directory = tempfile.mkdtemp(prefix="x8-abexec-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        payload = _payload()
        compressed = zstandard.ZstdCompressor(level=3).compress(payload)
        payload_path = root / "payload.ext4.zst"
        payload_path.write_bytes(compressed)
        hw_path = root / "hw.tar.zst"
        hw_path.write_bytes(_HW_BYTES)
        bundle = root / "r11.greiaupdate"
        build_update_bundle(
            payload_path=payload_path,
            hardware_support_path=hw_path,
            output_path=bundle,
            version="0.15.0",
            release_id="greia-0.15.0",
            platform_family=_FAMILY,
            architecture=_ARCH,
            profile=_PROFILE,
            payload_uncompressed_bytes=len(payload),
            minimum_slot_bytes=len(payload) + MIB,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
        )
        manifest = inspect_update_bundle(bundle).manifest
        observed = _observed_mbr_identities()
        persist_stage = root / "persist-stage"
        persist_stage.mkdir()
        boot_control = root / "boot-control"
        backend_state = root / "backend-state"
        boot_control.mkdir()
        backend_state = boot_control / "grub"
        journal = (
            persist_stage
            / "greia"
            / "namespaces"
            / "parent-credentials"
            / "boot-journal"
        )
        touched: list[str] = []
        seen: list[tuple[object, object]] = []
        partition_runners: list[RecordingPartitionRunner] = []

        def _identities(target, plan):  # type: ignore[no-untyped-def]
            # Post-layout observer: invoked with (target, plan) only after
            # the orchestrator partitioned, never pre-computed by the
            # executor. Records the call for sequencing proof.
            seen.append((target, plan))
            if not partition_runners or not partition_runners[0].commands:
                raise AssertionError(
                    "observer must fire only after partitioning created identities"
                )
            return {role: dict(values) for role, values in observed.items()}

        def _seams(target):  # type: ignore[no-untyped-def]
            runner = RecordingPartitionRunner()
            partition_runners.append(runner)
            return FreshAbInstallSeams(
                partition_runner=runner,  # type: ignore[arg-type]
                slot_storage_factory=lambda role: (
                    touched.append(role),
                    SparseSlotStorage(1 * GIB),
                )[1],
                slot_filesystem_factory=lambda: FakeSlotFilesystem(root / "mnt"),
                package_installer_factory=FakePackageInstaller,
                inventory_token="cd" * 32,
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
                support_installed_bound=_SUPPORT_BOUND,
                persist_runner=FakePersistRunner(readback_uuid=_PERSIST_FS_UUID),
                persist_stage_dir=persist_stage,
                persist_uuid_factory=lambda: uuid.UUID(_PERSIST_FS_UUID),
                boot_control_dir=boot_control,
                bios_bootloader_installer=lambda target, boot_directory: None,
            )

        facts = AbExecutorFacts(
            bundle_path=bundle,
            expected_profile_id=_PROFILE,
            expected_platform_family=_FAMILY,
            expected_architecture=_ARCH,
            sizing=_sizing(),
            support_installed_bytes=_SUPPORT_BOUND,
            password_hash=_PASSWORD_HASH,
        )
        executor = build_ab_executor(facts, _seams, identities_factory=_identities)

        from greia_platform.hardware import HardwareSettings

        settings = HardwareSettings(
            schema_version=2,
            touchpad_tap=True,
            touchpad_speed=-0.25,
            mouse_speed=0.5,
            natural_scrolling=True,
            resolution="800x600",
            keyboard_layout="it",
            mic_gain=1.0,
            disable_while_typing=True,
        )
        from types import SimpleNamespace
        from unittest.mock import patch
        from greia_installer.entrypoint import LanguageFirstInstallerApplication
        from greia_installer.wifi import IwdNetworkProfile, WifiNetwork, WifiSecurity
        from greia_installer.wifi_carryover import IwdProfileCarryover, WifiCarryoverChoice
        from greia_platform.hardware import HardwareSettingsStore
        from greia_platform.hal_legacy_x import LegacyXHardwareSessionController
        from greia_platform.hardware_session import run_watcher
        from greia_platform.persistent_layout import persist_namespace_root
        from greia_platform.system_language import SystemLanguageStore
        from test_hardware_session import FakeRunner

        live = root / "live-iwd"
        live.mkdir(mode=0o700)
        profile = live / "Family.psk"
        profile.write_text("[Security]\nPassphrase=examplepassword\n")
        profile.chmod(0o600)
        choice = WifiCarryoverChoice("Family", WifiSecurity.PERSONAL)
        ui = LanguageFirstInstallerApplication.__new__(LanguageFirstInstallerApplication)
        ui.locale = "it"
        ui.state = SimpleNamespace(settings=settings)
        ui.wifi = SimpleNamespace(profile=IwdNetworkProfile.for_network(
            WifiNetwork("Family", WifiSecurity.PERSONAL, -40, "/net/connman/iwd/0/1"),
            "examplepassword",
        ))
        snapshot = ui.settings_snapshot_for_service()
        routing = AbServiceRoutingTests()
        service = routing._service([_target()], ab_executor=executor)
        client, prepared = routing._prepare_via_client(service, snapshot)
        with patch("greia_installer.wifi_carryover.IwdProfileCarryover", return_value=IwdProfileCarryover(source_dir=live)):
            client.execute(transaction_nonce=prepared.transaction_nonce, plan_digest=prepared.plan_digest)

        state = persist_namespace_root(persist_stage, "device-settings")
        self.assertEqual(SystemLanguageStore(state).read().locale, "it")
        network = persist_namespace_root(persist_stage, "network-state")
        self.assertEqual((network / choice.filename).read_text(), profile.read_text())
        defaults = Path(__file__).resolve().parents[1] / "runtime/hardware-settings.toml"
        store = HardwareSettingsStore.load(defaults, state)
        self.assertEqual(store.read(), settings)
        runner = FakeRunner()
        run_watcher(store, root / "status.json", controller=LegacyXHardwareSessionController(runner), once=True)
        self.assertIn(("setxkbmap", "it"), runner.commands)
        self.assertIn(("xinput", "set-prop", "12", "libinput Accel Speed", "-0.25"), runner.commands)
        self.assertIn(("xinput", "set-prop", "13", "libinput Accel Speed", "0.50"), runner.commands)
        self.assertIn(("xinput", "set-prop", "12", "libinput Tapping Enabled", "1"), runner.commands)
        self.assertIn(("xinput", "set-prop", "12", "libinput Natural Scrolling Enabled", "1"), runner.commands)
        self.assertIn(("xinput", "set-prop", "12", "libinput Disable While Typing Enabled", "1"), runner.commands)
        self.assertIn(("xrandr", "--output", "LVDS1", "--mode", "800x600"), runner.commands)
        self.assertIn(("amixer", "-q", "set", "Capture", "50%", "unmute"), runner.commands)
        self.assertEqual(touched, ["A"])
        # The post-layout observer fired exactly once, after partitioning,
        # for the rematerialized target with the validated plan.
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0].name, "sda")
        self.assertEqual(seen[0][1].adapter_id, "legacy-bios-ab-v1")

    def test_executor_without_observer_refuses_before_destruction(self) -> None:
        directory = tempfile.mkdtemp(prefix="x8-abexec-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        harness = self._harness_bundle_only(root)
        manifest = inspect_update_bundle(harness["bundle"]).manifest
        facts = AbExecutorFacts(
            bundle_path=harness["bundle"],
            expected_profile_id=_PROFILE,
            expected_platform_family=_FAMILY,
            expected_architecture=_ARCH,
            sizing=_sizing(),
            support_installed_bytes=_SUPPORT_BOUND,
            password_hash=_PASSWORD_HASH,
        )
        runners: list[RecordingPartitionRunner] = []

        def _seams(target):  # type: ignore[no-untyped-def]
            runner = RecordingPartitionRunner()
            runners.append(runner)
            # No post-layout observer anywhere: neither the seams nor an
            # executor-level identities_factory supplies one.
            return FreshAbInstallSeams(
                partition_runner=runner,  # type: ignore[arg-type]
                slot_storage_factory=lambda role: SparseSlotStorage(1 * GIB),
                slot_filesystem_factory=lambda: FakeSlotFilesystem(root / "mnt"),
                package_installer_factory=FakePackageInstaller,
                inventory_token="cd" * 32,
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
                support_installed_bound=_SUPPORT_BOUND,
                bios_bootloader_installer=lambda target, boot_directory: None,
            )

        executor = build_ab_executor(facts, _seams)

        class _Authorization:
            target_identity = _INSTALL_SHA

        from greia_platform.hardware import HardwareSettings

        settings = HardwareSettings(
            schema_version=2,
            touchpad_tap=False,
            touchpad_speed=0.35,
            mouse_speed=0.0,
            natural_scrolling=False,
            resolution="auto",
            keyboard_layout="us",
            mic_gain=2.0,
            disable_while_typing=False,
        )
        with self.assertRaisesRegex(
            FreshAbInstallError, "post-layout identity observer"
        ):
            executor(_Authorization(), settings, "en", _target())
        # The observer wiring is checked before the first destructive
        # command: partitioning never ran.
        self.assertEqual(len(runners), 1)
        self.assertEqual(runners[0].commands, [])

    def _harness_bundle_only(self, root: Path):
        """Build an unsigned v3 bundle without a full install harness."""
        import zstandard

        payload = _payload()
        compressed = zstandard.ZstdCompressor(level=3).compress(payload)
        payload_path = root / "payload.ext4.zst"
        payload_path.write_bytes(compressed)
        hw_path = root / "hw.tar.zst"
        hw_path.write_bytes(_HW_BYTES)
        bundle = root / "r11.greiaupdate"
        if bundle.exists():
            bundle.unlink()
        build_update_bundle(
            payload_path=payload_path,
            hardware_support_path=hw_path,
            output_path=bundle,
            version="0.15.0",
            release_id="greia-0.15.0",
            platform_family=_FAMILY,
            architecture=_ARCH,
            profile=_PROFILE,
            payload_uncompressed_bytes=len(payload),
            minimum_slot_bytes=len(payload) + MIB,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
        )
        return {"bundle": bundle}


class ModuleHygieneTests(unittest.TestCase):
    """The fresh-install orchestrator carries no raw disk/shell authority."""

    def _source(self, relative: str) -> str:
        return (Path(__file__).resolve().parents[1] / relative).read_text(
            encoding="utf-8"
        )

    def test_orchestrator_carries_no_destructive_command_surface(self) -> None:
        source = self._source("src/greia_installer/fresh_ab_install.py")
        for token in (
            '"wipefs"',
            '"mkfs.ext4"',
            '"grub-install"',
            '"unsquashfs"',
            '"parted"',
            '"partprobe"',
            '"udevadm"',
            '"blkid"',
            '"chroot"',
            "import subprocess",
            "from subprocess",
            "shell=True",
            "shell = True",
            "/dev/",
            "os.system",
        ):
            self.assertNotIn(token, source)

    def test_transaction_protocol_files_unchanged_in_authority(self) -> None:
        source = self._source("src/greia_installer/install_transaction.py")
        self.assertIn("PREPARE_PLAN", source)
        self.assertIn("EXECUTE", source)


if __name__ == "__main__":
    unittest.main()
