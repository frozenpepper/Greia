"""A8-UPDATE-SVC: SystemUpdateService on the common slot/journal seams (8A.6).

The privileged update side reuses the shared SlotWriter/SlotFinalizer and
the shared BootTransactionJournal behind the socket-activated service while
the inbox stays unprivileged: single-root layouts stay unavailable,
the active/accepted slot is never writable, every refusal leaves the
destination seam untouched, and the Parent semantic API keeps reporting
``system.update.activate=false``. No valued disk is touched: slot stores
are pre-sized loopback files under tmpdirs and every other seam is a fake.

v3 contract (ADR 0036): unsigned bundles, no key material, no
anti-rollback sequence. Compatibility is version/profile/architecture/
board/space + PERSIST-schema-range gating.
"""

from __future__ import annotations

import hashlib
import io
import json
import socket
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from greia_platform.boot_transaction import BootTransactionJournal, FakeGrubBackend
from greia_platform.persistent_layout import (
    InstalledLayoutRecord,
    emit_persist_schema_marker,
)
from greia_platform.system_updates import (
    HARDWARE_SUPPORT_NAME,
    MANIFEST_NAME,
    PAYLOAD_NAME,
    SCHEMA_VERSION,
    SlotBackedSystemUpdateBackend,
    SystemIdentity,
    SystemUpdateService,
    SystemUpdateError,
    SystemUpdateInbox,
    SystemUpdateServiceAuthority,
    UnavailableSystemUpdateBackend,
    UpdateBackendUnavailable,
    UpdateBundleError,
    UpdateCandidateSummary,
    UpdateCompatibilityError,
    UpdateManifest,
    UpdateSlotSeams,
    build_update_bundle,
    inactive_slot_for,
    inspect_update_bundle,
    load_installed_layout_record,
)


def _valid_hw_bytes() -> bytes:
    import zstandard

    packages = b""
    packages_gz = b""
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 0,
        "total_bytes": 0,
        "total_installed_bytes": 0,
        "provided_candidate_packages": [],
        "provided_firmware_packages": [],
        "provided_microcode_packages": [],
        "broad_firmware_packages": [],
        "firmware_providers": {},
        "unavailable_candidate_packages": [],
        "packages": [],
        "repository_indexes": {
            "Packages": {"size": 0, "sha256": hashlib.sha256(packages).hexdigest()},
            "Packages.gz": {"size": 0, "sha256": hashlib.sha256(packages_gz).hexdigest()},
        },
    }
    raw_tar = io.BytesIO()
    with tarfile.open(fileobj=raw_tar, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, payload in (
            ("manifest.json", json.dumps(manifest).encode("utf-8")),
            ("Packages", packages),
            ("Packages.gz", packages_gz),
        ):
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            info.mode = 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(payload))
    return zstandard.ZstdCompressor(level=3).compress(raw_tar.getvalue())


_HW_BYTES = _valid_hw_bytes()
_PERSIST_MARKER = emit_persist_schema_marker(1)

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_UUID_BOOT_FS = "dddddddd-eeee-ffff-0000-111111111111"
_INSTALL_SHA = "ab" * 32

_SLOT_BYTES = 1024 * 1024 * 1024


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
        "slot_bytes": _SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _write_layout(root: Path, **overrides: object) -> Path:
    path = root / "installed-layout.json"
    path.write_bytes(
        (json.dumps(_record_dict(**overrides), sort_keys=True) + "\n").encode()
    )
    return path


def _raw_payload(size: int = 200 * 1024) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _compress_raw(raw: bytes) -> bytes:
    import zstandard

    return zstandard.ZstdCompressor(level=3).compress(raw)


def _manifest_for(compressed: bytes, raw_len: int) -> UpdateManifest:
    return UpdateManifest(
        schema_version=SCHEMA_VERSION,
        release_id="greia-0.15.0",
        version="0.15.0",
        platform_family="standard-x86-64",
        architecture="x86-64",
        profile="modern-amd64",
        board=None,
        payload_sha256=hashlib.sha256(compressed).hexdigest(),
        payload_size=len(compressed),
        payload_uncompressed_bytes=raw_len,
        payload_minimum_slot_bytes=raw_len,
        hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
        hardware_support_size=len(_HW_BYTES),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="Step 8A.6 test release.",
    )


def _unsigned_bundle(
    root: Path, raw: bytes, *, name: str = "candidate.greiaupdate"
) -> Path:
    compressed = _compress_raw(raw)
    payload_path = root / f"payload-{name}.ext4.zst"
    payload_path.write_bytes(compressed)
    hw_path = root / f"hw-{name}.tar.zst"
    hw_path.write_bytes(_HW_BYTES)
    out = root / name
    if out.exists():
        out.unlink()
    build_update_bundle(
        payload_path=payload_path,
        hardware_support_path=hw_path,
        output_path=out,
        version="0.15.0",
        release_id="greia-0.15.0",
        platform_family="standard-x86-64",
        architecture="x86-64",
        profile="modern-amd64",
        payload_uncompressed_bytes=len(raw),
        minimum_slot_bytes=len(raw),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="Step 8A.6 test release.",
    )
    return out


def _populate_slot_completeness(mount_dir: Path) -> None:
    """Create the required Greia userspace tree for a passing smoke."""
    from greia_platform.slot_writer import (
        REQUIRED_SLOT_COMPLETENESS_DIRS,
        REQUIRED_SLOT_COMPLETENESS_FILES,
    )

    for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
        (mount_dir / rel_path).mkdir(parents=True, exist_ok=True)
    for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
        candidate = mount_dir / rel_path
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if candidate.is_symlink() or not candidate.is_file():
            candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
            try:
                candidate.chmod(0o755)
            except OSError:
                pass


class FakeSlotFilesystem:
    """Destination-only fake: records every mutation in order."""

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
        self.mounted = True
        return self.mount_dir

    def unmount(self) -> None:
        self.ops.append("unmount")
        self.mounted = False

    def sync(self) -> None:
        self.ops.append("sync")

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise AssertionError("slot writes require a mounted destination")
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


class FakeSlotPackageInstaller:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def install(
        self, firmware: tuple[str, ...], microcode: tuple[str, ...]
    ) -> tuple[object, ...]:
        self.calls.append((tuple(firmware), tuple(microcode)))
        return ()


class RecordingSeams:
    """Seam factories recording every destination contact."""

    def __init__(self, root: Path) -> None:
        from greia_platform.slot_writer import (
            HardwareInventoryAttestation,
            LoopbackSlotFile,
            ReleaseSupportSet,
            SlotProfilePolicy,
        )

        self._root = root
        self._attestation = HardwareInventoryAttestation
        self._loopback = LoopbackSlotFile
        self._support_set = ReleaseSupportSet
        self._slot_profile_policy = SlotProfilePolicy
        self.contacts: list[str] = []
        mount_dir = root / "mnt"
        mount_dir.mkdir(parents=True, exist_ok=True)
        _populate_slot_completeness(mount_dir)
        self.filesystem = FakeSlotFilesystem(mount_dir)
        self.package_installer = FakeSlotPackageInstaller()

    def token(self) -> str:
        return hashlib.sha256(b"inventory-8a6").hexdigest()

    def slot_store_factory(self, destination: object) -> object:
        self.contacts.append(f"store:{getattr(destination, 'role', '?')}")
        capacity = int(getattr(destination, "slot_capacity_bytes", 0))
        role = str(getattr(destination, "role", "system-b"))
        return self._loopback.create(self._root / f"slot-{role}.img", capacity)

    def filesystem_factory(self) -> object:
        self.contacts.append("filesystem")
        return self.filesystem

    def package_installer_factory(self) -> object:
        self.contacts.append("package-installer")
        return self.package_installer

    def inventory_factory(self) -> object:
        self.contacts.append("inventory")
        return self._attestation(token=self.token())

    def support_set_factory(self, bundle: object) -> object:
        self.contacts.append("support")
        manifest = getattr(bundle, "manifest")
        return self._support_set(
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
            installed_size_bound=0,
            provided_firmware=frozenset(),
            provided_microcode=frozenset(),
            packages=(),
        )

    def installed_contract_factory(self) -> bytes:
        self.contacts.append("contract")
        return _PERSIST_MARKER

    def profile_policy_factory(self, record: object) -> object:
        persist = getattr(record, "persist")
        return self._slot_profile_policy(
            layout_id=str(getattr(record, "layout_id")),
            system_slot_bytes=int(getattr(record, "slot_bytes")),
            boot_backend=str(getattr(record, "boot_backend")),
            persist_filesystem_uuid=str(getattr(persist, "filesystem_uuid")),
            boot_control_filesystem_uuid=_UUID_BOOT_FS,
        )

    def seams(self) -> UpdateSlotSeams:
        return UpdateSlotSeams(
            slot_store_factory=self.slot_store_factory,
            filesystem_factory=self.filesystem_factory,
            package_installer_factory=self.package_installer_factory,
            inventory_factory=self.inventory_factory,
            support_set_factory=self.support_set_factory,
            profile_policy_factory=self.profile_policy_factory,
            installed_contract_factory=self.installed_contract_factory,
        )


def _backend(
    root: Path,
    seams: RecordingSeams,
    *,
    layout_overrides: dict[str, object] | None = None,
    boot_backend: object | None = None,
) -> tuple[SlotBackedSystemUpdateBackend, Path]:
    layout_path = _write_layout(root, **(layout_overrides or {}))
    backend = SlotBackedSystemUpdateBackend(
        root / "state",
        layout_record_path=layout_path,
        seams=seams.seams(),
        boot_backend=boot_backend,
    )
    return backend, layout_path


def _identity() -> SystemIdentity:
    return SystemIdentity("0.14.0", "standard-x86-64", "x86-64", "modern-amd64")


class InactiveSlotResolutionTests(unittest.TestCase):
    def test_active_a_accepted_a_selects_b(self) -> None:
        record = InstalledLayoutRecord.from_dict(_record_dict())
        self.assertEqual(inactive_slot_for(record), "B")

    def test_active_b_accepted_b_selects_a(self) -> None:
        record = InstalledLayoutRecord.from_dict(
            _record_dict(
                accepted_slot="B",
                boot_control={"active_slot": "B", "kind": "grub-env-v1"},
            )
        )
        self.assertEqual(inactive_slot_for(record), "A")

    def test_single_root_has_no_inactive_slot(self) -> None:
        record = InstalledLayoutRecord.from_dict(
            _record_dict(
                layout_id="bios-single-ext4",
                boot_backend="none-v1",
                boot_control={"active_slot": None, "kind": "none-v1"},
                accepted_slot=None,
                system_b=None,
            )
        )
        self.assertIsNone(inactive_slot_for(record))

    def test_every_slot_live_is_refused(self) -> None:
        record = InstalledLayoutRecord.from_dict(
            _record_dict(
                accepted_slot="A",
                boot_control={"active_slot": "B", "kind": "grub-env-v1"},
            )
        )
        with self.assertRaises(SystemUpdateError):
            inactive_slot_for(record)


class SingleRootUnavailableTests(unittest.TestCase):
    def test_missing_layout_record_is_unavailable_with_zero_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend = SlotBackedSystemUpdateBackend(
                root / "state",
                layout_record_path=root / "no-such-layout.json",
                seams=seams.seams(),
            )
            bundle = inspect_update_bundle(_unsigned_bundle(root, _raw_payload()))
            self.assertFalse(backend.available)
            with self.assertRaises(UpdateBackendUnavailable):
                backend.stage(bundle)
            self.assertEqual(seams.contacts, [])
            payload = backend.status_payload()
            self.assertFalse(payload["available"])

    def test_single_root_layout_is_unavailable_with_zero_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(
                root,
                seams,
                layout_overrides={
                    "layout_id": "bios-single-ext4",
                    "boot_backend": "none-v1",
                    "boot_control": {"active_slot": None, "kind": "none-v1"},
                    "accepted_slot": None,
                    "system_b": None,
                },
            )
            bundle = inspect_update_bundle(_unsigned_bundle(root, _raw_payload()))
            self.assertFalse(backend.available)
            with self.assertRaises(UpdateBackendUnavailable):
                backend.stage(bundle)
            self.assertEqual(seams.contacts, [])
            self.assertIn("not configured", str(backend.status_payload()["reason"]))

    def test_corrupt_layout_record_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_path = root / "installed-layout.json"
            layout_path.write_text("not json\n", encoding="utf-8")
            seams = RecordingSeams(root)
            backend = SlotBackedSystemUpdateBackend(
                root / "state",
                layout_record_path=layout_path,
                seams=seams.seams(),
            )
            self.assertFalse(backend.available)
            bundle = inspect_update_bundle(_unsigned_bundle(root, _raw_payload()))
            with self.assertRaises(SystemUpdateError):
                backend.stage(bundle)
            self.assertEqual(seams.contacts, [])

    def test_unconfigured_seams_report_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_path = _write_layout(root)
            backend = SlotBackedSystemUpdateBackend(
                root / "state", layout_record_path=layout_path
            )
            self.assertTrue(backend.available)
            bundle = inspect_update_bundle(_unsigned_bundle(root, _raw_payload()))
            with self.assertRaisesRegex(UpdateBackendUnavailable, "not configured"):
                backend.stage(bundle)

    def test_unavailable_backend_keeps_arm_confirm_reconcile_closed(self) -> None:
        backend = UnavailableSystemUpdateBackend("single-root layout")
        service = SystemUpdateService(Path("/nonexistent"), _identity(), backend)
        with self.assertRaises(UpdateBackendUnavailable):
            service.arm()
        with self.assertRaises(UpdateBackendUnavailable):
            service.confirm_boot_health()
        with self.assertRaises(UpdateBackendUnavailable):
            service.reconcile()


class ActiveSlotDenialTests(unittest.TestCase):
    def test_stage_into_live_layout_is_refused_with_zero_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(
                root,
                seams,
                layout_overrides={
                    "accepted_slot": "A",
                    "boot_control": {"active_slot": "B", "kind": "grub-env-v1"},
                },
            )
            bundle = inspect_update_bundle(_unsigned_bundle(root, _raw_payload()))
            with self.assertRaises(SystemUpdateError):
                backend.stage(bundle)
            self.assertEqual(seams.contacts, [])

    def test_second_stage_while_transaction_active_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            first = inspect_update_bundle(
                _unsigned_bundle(root, _raw_payload(), name="first.greiaupdate")
            )
            backend.stage(first)
            contacts_after_first = list(seams.contacts)
            self.assertTrue(contacts_after_first)
            second = inspect_update_bundle(
                _unsigned_bundle(
                    root, b"second-payload" + _raw_payload(), name="second.greiaupdate"
                )
            )
            with self.assertRaisesRegex(SystemUpdateError, "already active"):
                backend.stage(second)


class InactiveSlotStagingTests(unittest.TestCase):
    def test_stage_writes_inactive_slot_and_records_shared_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            raw = _raw_payload()
            bundle = inspect_update_bundle(_unsigned_bundle(root, raw))
            self.assertTrue(backend.available)
            backend.stage(bundle)
            # Destination seam saw exactly the inactive role, never the live one.
            self.assertIn("store:system-b", seams.contacts)
            self.assertNotIn("store:system-a", seams.contacts)
            # Role-stable UUID restored: B keeps its own layout UUID.
            self.assertEqual(
                seams.filesystem.bound_uuid,
                _record_dict()["system_b"]["filesystem_uuid"],  # type: ignore[index]
            )
            self.assertIn("health", seams.filesystem.ops)
            # Shared journal names the candidate and the accepted slot.
            journal = BootTransactionJournal.load(backend.journal_dir)
            self.assertEqual(journal.candidate_slot, "B")
            self.assertEqual(journal.accepted_slot, "A")
            self.assertEqual(journal.release_id, "greia-0.15.0")
            self.assertEqual(journal.state.value, "update_staged")
            status = backend.status_payload()
            self.assertTrue(status["available"])
            self.assertEqual(status["candidate_slot"], "B")
            self.assertEqual(status["journal_state"], "update_staged")

    def test_support_mismatch_fails_before_any_slot_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            bundle = inspect_update_bundle(_unsigned_bundle(root, _raw_payload()))
            from greia_platform.slot_writer import ReleaseSupportSet

            def wrong_support(candidate: object) -> object:
                return ReleaseSupportSet(
                    support_digest="0" * 64,
                    support_size=1,
                    installed_size_bound=0,
                    provided_firmware=frozenset(),
                    provided_microcode=frozenset(),
                    packages=(),
                )

            backend.seams = UpdateSlotSeams(
                slot_store_factory=seams.slot_store_factory,
                filesystem_factory=seams.filesystem_factory,
                package_installer_factory=seams.package_installer_factory,
                inventory_factory=seams.inventory_factory,
                support_set_factory=wrong_support,
            )
            with self.assertRaises(SystemUpdateError):
                backend.stage(bundle)
            self.assertNotIn("store:system-b", seams.contacts)
            self.assertNotIn("store:system-a", seams.contacts)

    def test_digest_mismatch_fails_before_any_slot_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            bundle_path = _unsigned_bundle(root, _raw_payload())
            with zipfile.ZipFile(bundle_path) as src:
                manifest_raw = src.read(MANIFEST_NAME)
                hw = src.read(HARDWARE_SUPPORT_NAME)
            with zipfile.ZipFile(bundle_path) as src:
                payload_compressed = src.read(PAYLOAD_NAME)
            tampered = bytearray(payload_compressed)
            tampered[10] ^= 0xFF
            tampered_path = root / "tampered.greiaupdate"
            with zipfile.ZipFile(tampered_path, "w", compression=zipfile.ZIP_STORED) as dst:
                dst.writestr(MANIFEST_NAME, manifest_raw)
                dst.writestr(PAYLOAD_NAME, bytes(tampered))
                dst.writestr(HARDWARE_SUPPORT_NAME, hw)
            with self.assertRaises(UpdateBundleError):
                inspect_update_bundle(tampered_path)
            self.assertEqual(seams.contacts, [])

    def test_persist_range_refusal_fails_before_any_slot_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            raw = _raw_payload()
            compressed = _compress_raw(raw)
            payload_path = root / "payload-narrow.ext4.zst"
            payload_path.write_bytes(compressed)
            hw_path = root / "hw-narrow.tar.zst"
            hw_path.write_bytes(_HW_BYTES)
            narrow = root / "narrow.greiaupdate"
            build_update_bundle(
                payload_path=payload_path,
                hardware_support_path=hw_path,
                output_path=narrow,
                version="0.15.0",
                release_id="greia-0.15.0-narrow",
                platform_family="standard-x86-64",
                architecture="x86-64",
                profile="modern-amd64",
                payload_uncompressed_bytes=len(raw),
                minimum_slot_bytes=len(raw),
                persist_read_schema_min=10,
                persist_read_schema_max=10,
                persist_write_schema=10,
            )
            bundle = inspect_update_bundle(narrow)
            with self.assertRaises(SystemUpdateError):
                backend.stage(bundle)
            self.assertNotIn("store:system-b", seams.contacts)


class ArmConfirmReconcileTests(unittest.TestCase):
    def _staged(
        self, root: Path
    ) -> tuple[SlotBackedSystemUpdateBackend, FakeGrubBackend, RecordingSeams]:
        seams = RecordingSeams(root)
        boot_state = root / "boot"
        boot_state.mkdir()
        grub = FakeGrubBackend.initialize(boot_state, default_slot="A")
        backend, _ = _backend(root, seams, boot_backend=grub)
        backend.stage(inspect_update_bundle(_unsigned_bundle(root, _raw_payload())))
        return backend, grub, seams

    def test_arm_without_boot_backend_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            backend.stage(inspect_update_bundle(_unsigned_bundle(root, _raw_payload())))
            with self.assertRaisesRegex(UpdateBackendUnavailable, "not wired"):
                backend.arm()

    def test_arm_confirm_round_trip_accepts_release_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend, grub, _ = self._staged(root)
            armed = backend.arm()
            self.assertEqual(armed, {"armed": True, "slot": "B"})
            journal = BootTransactionJournal.load(backend.journal_dir)
            self.assertEqual(journal.state.value, "one_shot_armed")
            # Firmware boots the candidate exactly once.
            self.assertEqual(grub.simulate_reboot(), "B")
            confirmed = backend.confirm_boot_health()
            self.assertTrue(confirmed["confirmed"])
            self.assertEqual(confirmed["state"], "accepted")
            self.assertEqual(confirmed["booted_slot"], "B")
            journal_after = BootTransactionJournal.load(backend.journal_dir)
            self.assertEqual(journal_after.release_id, "greia-0.15.0")
            # Confirm is idempotent once terminal.
            again = backend.confirm_boot_health()
            self.assertTrue(again["confirmed"])

    def test_fallback_boot_rolls_back_without_committing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend, grub, _ = self._staged(root)
            backend.arm()
            # Unhealthy candidate: firmware falls back to the persistent default.
            grub.simulate_reboot()
            grub.reconcile("A")
            confirmed = backend.confirm_boot_health()
            self.assertFalse(confirmed["confirmed"])
            self.assertEqual(confirmed["state"], "rolled_back")

    def test_reconcile_without_observation_stays_steady(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            backend.stage(inspect_update_bundle(_unsigned_bundle(root, _raw_payload())))
            outcome = backend.reconcile()
            self.assertTrue(outcome["reconciled"])
            self.assertEqual(outcome["state"], "update_staged")
            self.assertIsNone(outcome["booted_slot"])

    def test_double_arm_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend, _, _ = self._staged(root)
            backend.arm()
            with self.assertRaises(SystemUpdateError):
                backend.arm()


class ServiceTrustOrderingTests(unittest.TestCase):
    """v3 trust ordering: compatibility + PERSIST before slot contact."""

    def _v3_bundle(self, root: Path, *, name: str = "release.greiaupdate") -> Path:
        return _unsigned_bundle(root, _raw_payload(), name=name)

    def test_compatibility_refusal_never_reaches_the_slot_seam(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._v3_bundle(root)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            service = SystemUpdateService(
                root / "state",
                SystemIdentity("0.15.0", "standard-x86-64", "arm64", "modern-amd64"),
                backend,
            )
            with self.assertRaises(SystemUpdateError):
                service.stage(bundle)
            self.assertEqual(seams.contacts, [])

    def test_verified_stage_flows_through_service_to_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._v3_bundle(root)
            seams = RecordingSeams(root)
            boot_state = root / "boot"
            boot_state.mkdir()
            grub = FakeGrubBackend.initialize(boot_state, default_slot="A")
            backend, _ = _backend(root, seams, boot_backend=grub)
            service = SystemUpdateService(root / "state", _identity(), backend)
            staged = service.stage(bundle)
            self.assertEqual(staged.manifest.release_id, "greia-0.15.0")
            self.assertIn("store:system-b", seams.contacts)
            journal = BootTransactionJournal.load(backend.journal_dir)
            self.assertEqual(journal.candidate_slot, "B")
            self.assertEqual(journal.release_id, "greia-0.15.0")
            status = service.status_payload()
            self.assertTrue(status["activation"]["available"])

    def test_persist_range_refused_before_slot_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = _raw_payload()
            compressed = _compress_raw(raw)
            payload_path = root / "payload-persist.ext4.zst"
            payload_path.write_bytes(compressed)
            hw_path = root / "hw-persist.tar.zst"
            hw_path.write_bytes(_HW_BYTES)
            narrow = root / "narrow.greiaupdate"
            build_update_bundle(
                payload_path=payload_path,
                hardware_support_path=hw_path,
                output_path=narrow,
                version="0.15.0",
                release_id="greia-0.15.0-narrow",
                platform_family="standard-x86-64",
                architecture="x86-64",
                profile="modern-amd64",
                payload_uncompressed_bytes=len(raw),
                minimum_slot_bytes=len(raw),
                persist_read_schema_min=10,
                persist_read_schema_max=10,
                persist_write_schema=10,
            )
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            service = SystemUpdateService(root / "state", _identity(), backend)
            with self.assertRaises(SystemUpdateError):
                service.stage(narrow)
            # PERSIST preflight runs before any destination slot store is
            # addressed; support/contract seam reads are allowed, slot
            # stores are not.
            self.assertNotIn("store:system-b", seams.contacts)
            self.assertNotIn("store:system-a", seams.contacts)

    def test_old_signed_format_rejected_with_migration_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                "schema_version": 2,
                "release_id": "greia-0.14.0",
                "version": "0.14.0",
                "platform_family": "standard-x86-64",
                "architecture": "x86-64",
                "profile": "modern-amd64",
                "payload": {
                    "name": "payload.bin",
                    "sha256": "0" * 64,
                    "size": 4,
                    "kind": "system-slot-image",
                },
                "release_notes": "",
            }
            path = root / "old-signed.greiaupdate"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(
                    MANIFEST_NAME,
                    (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
                )
                archive.writestr("manifest.sig", b"{}")
                archive.writestr("payload.bin", b"data")
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            service = SystemUpdateService(root / "state", _identity(), backend)
            with self.assertRaises(UpdateBundleError) as ctx:
                service.stage(path)
            message = str(ctx.exception).lower()
            self.assertIn("v3", message)
            self.assertTrue("rebuild" in message or "migration" in message)
            self.assertEqual(seams.contacts, [])


class AuthoritySocketTests(unittest.TestCase):
    def _authority(
        self, root: Path, *, present: bool = True
    ) -> SystemUpdateServiceAuthority:
        seams = RecordingSeams(root)
        backend, _ = _backend(root, seams)
        authority = SystemUpdateServiceAuthority(root / "state", _identity(), backend)
        if present:
            raw = _raw_payload()
            compressed = _compress_raw(raw)
            payload = root / "slot.img.ext4.zst"
            payload.write_bytes(compressed)
            hardware = root / "hw.tar.zst"
            hardware.write_bytes(_HW_BYTES)
            bundle = root / "release.greiaupdate"
            if not bundle.exists():
                build_update_bundle(
                    payload_path=payload,
                    hardware_support_path=hardware,
                    output_path=bundle,
                    version="0.15.0",
                    release_id="greia-0.15.0",
                    platform_family="standard-x86-64",
                    architecture="x86-64",
                    profile="modern-amd64",
                    payload_uncompressed_bytes=len(raw),
                    minimum_slot_bytes=len(raw),
                    persist_read_schema_min=1,
                    persist_read_schema_max=1,
                    persist_write_schema=1,
                )
            inbox = SystemUpdateInbox(root / "state")
            inbox.receive(bundle)
        authority._seams_recording = seams  # type: ignore[attr-defined]
        return authority

    def test_status_without_candidate_reports_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = self._authority(Path(directory), present=False)
            summary = authority.candidate_summary()
            self.assertIsInstance(summary, UpdateCandidateSummary)
            self.assertFalse(summary.present)
            layout = authority.layout_summary()
            self.assertFalse(layout["single_root"])
            self.assertEqual(layout["active_slot"], "A")

    def test_fixed_candidate_is_authoritative_without_status_receipt(self) -> None:
        for receipt in ("absent", "malformed", "stale"):
            with self.subTest(receipt=receipt), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                authority = self._authority(root)
                inbox = SystemUpdateInbox(root / "state")
                if receipt == "absent":
                    inbox.status_path.unlink()
                elif receipt == "malformed":
                    inbox.status_path.write_text("{not json", encoding="utf-8")
                else:
                    outside = root / "untrusted.greiaupdate"
                    outside.write_bytes(b"not the inbox candidate")
                    inbox.status_path.write_text(
                        json.dumps(
                            {
                                "state": "failed",
                                "bundle_path": str(outside),
                                "release": {"release_id": "stale-release"},
                                "bundle_sha256": "0" * 64,
                            }
                        ),
                        encoding="utf-8",
                    )

                summary = authority.candidate_summary()
                self.assertTrue(summary.present)
                self.assertEqual(summary.release_id, "greia-0.15.0")
                self.assertEqual(summary.bundle_sha256, "")
                verified = authority.verify_current_candidate()
                self.assertTrue(verified.present)
                self.assertEqual(verified.release_id, summary.release_id)
                public_status = inbox.status_payload()
                self.assertEqual(public_status["state"], "received")
                self.assertEqual(
                    public_status["release"]["release_id"], "greia-0.15.0"
                )
                # Discovery and verification do not stage or consume bytes.
                self.assertTrue(inbox.candidate_path.is_file())

    def test_corrupt_and_consumed_candidates_are_not_discovered_or_restored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._authority(root)
            inbox = SystemUpdateInbox(root / "state")
            inbox.candidate_path.write_bytes(b"corrupt package")
            self.assertFalse(authority.candidate_summary().present)
            with self.assertRaises(SystemUpdateError):
                authority.verify_current_candidate()

            # A consumed candidate is represented by absence; historical
            # progress metadata cannot recreate or redirect package authority.
            inbox.candidate_path.unlink()
            inbox.status_path.write_text(
                json.dumps(
                    {
                        "state": "staging",
                        "bundle_path": str(inbox.candidate_path),
                        "release": {"release_id": "old-release"},
                    }
                ),
                encoding="utf-8",
            )
            self.assertFalse(authority.candidate_summary().present)
            with self.assertRaises(SystemUpdateError):
                authority.verify_current_candidate()

    def test_privileged_status_reports_bounded_installed_readiness_sections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = self._authority(Path(directory), present=False)
            payload = authority.status_payload()
            self.assertEqual(payload["status"], "OK")
            for section in (
                "identity",
                "backend",
                "layout",
                "persist",
                "journal",
                "candidate",
            ):
                self.assertIsInstance(payload.get(section), dict)
            self.assertEqual(
                set(payload["identity"]),
                {
                    "version",
                    "release_id",
                    "profile",
                    "platform_family",
                    "architecture",
                    "board",
                    "current_slot",
                },
            )
            self.assertEqual(
                set(payload["persist"]),
                {"available", "readable", "schema", "readable_min", "readable_max", "free_bytes"},
            )
            self.assertFalse(payload["persist"]["available"])
            self.assertFalse(payload["activation_available"])
            self.assertTrue(payload["activation_reason"])

    def test_single_root_layout_summary_reports_unavailable_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_path = _write_layout(
                root,
                layout_id="bios-single-ext4",
                boot_backend="none-v1",
                boot_control={"active_slot": None, "kind": "none-v1"},
                accepted_slot=None,
                system_b=None,
            )
            backend = SlotBackedSystemUpdateBackend(
                root / "state", layout_record_path=layout_path
            )
            authority = SystemUpdateServiceAuthority(root / "state", _identity(), backend)
            layout = authority.layout_summary()
            self.assertTrue(layout["single_root"])
            self.assertFalse(backend.available)

    def test_verify_and_stage_through_real_endpoint(self) -> None:
        from greia_platform.privileged_channel import PeerCredential
        from greia_platform.update_privileged import (
            UPDATE_PRIVILEGED_ALLOWED_UIDS,
            UpdatePrivilegedEndpoint,
            build_request,
            read_response,
        )
        from greia_platform.system_updates import UPDATE_SERVICE_ALLOWED_UIDS

        self.assertEqual(
            tuple(UPDATE_SERVICE_ALLOWED_UIDS), tuple(UPDATE_PRIVILEGED_ALLOWED_UIDS)
        )
        with tempfile.TemporaryDirectory() as directory:
            authority = self._authority(Path(directory))
            endpoint = UpdatePrivilegedEndpoint(authority)  # type: ignore[arg-type]
            root_peer = PeerCredential(uid=0)
            _, op, payload = read_response(
                endpoint.handle_request(
                    build_request("STATUS"), peer=root_peer, boot_state="update_ready"
                )
            )
            self.assertEqual(op, "STATUS")
            self.assertTrue(payload["candidate"]["present"])
            self.assertEqual(
                set(payload["candidate"].keys()),
                {"present", "release_id", "bundle_sha256"},
            )
            self.assertEqual(payload["candidate"]["release_id"], "greia-0.15.0")
            _, op, payload = read_response(
                endpoint.handle_request(
                    build_request("VERIFY_CURRENT_CANDIDATE"),
                    peer=root_peer,
                    boot_state="update_ready",
                )
            )
            self.assertEqual(payload["status"], "VERIFIED")
            self.assertEqual(
                set(payload["candidate"].keys()),
                {"present", "release_id", "bundle_sha256"},
            )
            self.assertTrue(payload["candidate"]["present"])
            self.assertEqual(payload["candidate"]["release_id"], "greia-0.15.0")
            _, op, payload = read_response(
                endpoint.handle_request(
                    build_request("STAGE_CURRENT_CANDIDATE"),
                    peer=root_peer,
                    boot_state="update_ready",
                )
            )
            self.assertEqual(payload["status"], "STAGED")
            self.assertTrue(payload["detail"]["staged"])
            self.assertEqual(payload["detail"]["candidate_slot"], "B")
            # After a successful stage the large inbox candidate is
            # discarded (T03 fixed-candidate inbox) while the backend
            # journal keeps the staged transaction: a second stage
            # without arm/confirm is refused fail-closed.
            with self.assertRaises(SystemUpdateError):
                endpoint.handle_request(
                    build_request("STAGE_CURRENT_CANDIDATE"),
                    peer=root_peer,
                    boot_state="update_ready",
                )

    def test_socket_connection_serves_one_request_then_refuses_bad_peer(self) -> None:
        import struct

        from greia_platform.privileged_channel import (
            PeerCredential,
            PrivilegedChannelError,
        )
        from greia_platform.system_updates import (
            attest_peer_from_connection,
            handle_update_connection,
        )
        from greia_platform.update_privileged import build_request, read_response

        class _PeerConnection:
            """Real transport, kernel-shaped peer credential for one UID.

            ``getsockopt(SO_PEERCRED)`` answers with the fixed UID so the
            test proves attestation (not caller supply) decides service;
            all other socket behavior stays real.
            """

            def __init__(self, transport: socket.socket, uid: int) -> None:
                self._transport = transport
                self._uid = uid

            def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
                return struct.pack("3i", 12345, self._uid, 12345)

            def settimeout(self, value: float) -> None:
                self._transport.settimeout(value)

            def recv(self, size: int) -> bytes:
                return self._transport.recv(size)

            def sendall(self, data: bytes) -> None:
                self._transport.sendall(data)

            def close(self) -> None:
                self._transport.close()

        with tempfile.TemporaryDirectory() as directory:
            authority = self._authority(Path(directory))

            def attested_uid(uid: int, transport: socket.socket) -> PeerCredential:
                """Attest one UID through the production helper when possible.

                Platforms without ``SO_PEERCRED`` fail attestation closed
                (proven separately); there the credential is constructed
                directly so the serving/refusal contract is still proven.
                """
                try:
                    return attest_peer_from_connection(
                        _PeerConnection(transport, uid)  # type: ignore[arg-type]
                    )
                except PrivilegedChannelError:
                    if hasattr(socket, "SO_PEERCRED"):
                        raise
                    return PeerCredential(uid=uid)

            left, right = socket.socketpair()
            try:
                left.sendall(build_request("STATUS"))
                left.shutdown(socket.SHUT_WR)
                peer = attested_uid(0, right)
                self.assertIsInstance(peer, PeerCredential)
                self.assertEqual(peer.uid, 0)
                handle_update_connection(
                    _PeerConnection(right, 0),  # type: ignore[arg-type]
                    authority=authority,
                    peer=peer,
                )
                frames = []
                while True:
                    chunk = left.recv(65536)
                    if not chunk:
                        break
                    frames.append(chunk)
                _, op, payload = read_response(b"".join(frames))
                self.assertEqual(op, "STATUS")
                self.assertTrue(payload["candidate"]["present"])
            finally:
                left.close()
            refused_left, refused_right = socket.socketpair()
            try:
                refused_left.sendall(build_request("STATUS"))
                refused_left.shutdown(socket.SHUT_WR)
                handle_update_connection(
                    _PeerConnection(refused_right, 1000),  # type: ignore[arg-type]
                    authority=authority,
                    peer=PeerCredential(uid=1000),
                )
                frames = []
                while True:
                    chunk = refused_left.recv(65536)
                    if not chunk:
                        break
                    frames.append(chunk)
                _, op, payload = read_response(b"".join(frames))
                self.assertEqual(op, "ERROR")
                self.assertEqual(payload["status"], "REFUSED")
            finally:
                refused_left.close()
            # Caller-supplied identity (no attested credential) is rejected
            # before any request byte is served.
            forged_left, forged_right = socket.socketpair()
            try:
                forged_left.sendall(build_request("STATUS"))
                forged_left.shutdown(socket.SHUT_WR)
                # Linux sends RST when a socket closes with unread request
                # bytes; darwin closes cleanly. Drain the production side's
                # inbound request bytes before the refused close so the
                # REFUSED frame survives on both hosts. The refusal happens
                # before any request byte is served, so draining does not
                # change what the test proves.
                forged_right.settimeout(2.0)
                try:
                    while True:
                        drained = forged_right.recv(4096)
                        if not drained:
                            break
                        if drained.endswith(b"\n"):
                            break
                except OSError:
                    pass
                handle_update_connection(
                    forged_right,
                    authority=authority,
                    peer=0,  # type: ignore[arg-type]
                )
                frames = []
                while True:
                    try:
                        chunk = forged_left.recv(65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    frames.append(chunk)
                _, op, payload = read_response(b"".join(frames))
                self.assertEqual(op, "ERROR")
                self.assertEqual(payload["status"], "REFUSED")
                self.assertIn("attested", str(payload["reason"]))
            finally:
                forged_left.close()

    def test_candidate_outside_inbox_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._authority(root, present=False)
            outside = root / "outside.greiaupdate"
            outside.write_bytes(b"not-an-inbox-file")
            status_path = root / "state" / "system-updates" / "status.json"
            status_path.parent.mkdir(parents=True, exist_ok=True)
            status_path.write_text(
                json.dumps(
                    {
                        "state": "received",
                        "bundle_path": str(outside),
                        "bundle_sha256": "0" * 64,
                    }
                ),
                encoding="utf-8",
            )
            self.assertFalse(authority.candidate_summary().present)
            with self.assertRaises(SystemUpdateError):
                authority.verify_current_candidate()


class OverlayContractTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def _read(self, relative: str) -> str:
        return (self.ROOT / relative).read_text(encoding="utf-8")

    def test_update_service_is_wired_and_never_boot_enabled(self) -> None:
        # Activated contract (POSTR1-P3-UPDATE-ACTIVATION): the old
        # ConditionPathExists gate is absent. On-demand activation is
        # structural: Requires/After the socket only, no [Install] section
        # and no WantedBy=, so the service starts only on first connection
        # and never via any boot target.
        service = self._read(
            "build/overlay/etc/systemd/system/greia-system-update.service"
        )
        self.assertIn(
            "ExecStart=/usr/bin/python3 -m greia_platform.update_privileged "
            "--socket-activated",
            service,
        )
        for line in service.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped or stripped.startswith("["):
                continue
            self.assertFalse(
                stripped.startswith("Condition"),
                f"activated contract must not gate: {stripped!r}",
            )
        self.assertNotIn("ConditionPathExists=", service)
        self.assertNotIn("WantedBy=", service)
        self.assertNotIn("[Install]", service)
        self.assertIn("Requires=greia-system-update.socket", service)
        self.assertIn("After=greia-system-update.socket", service)
        self.assertIn(
            "Environment=GREIA_BOOT_JOURNAL_DIR="
            "/run/greia-persist/greia/boot-journal",
            service,
        )
        non_comment = [
            line.strip()
            for line in service.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        for line in non_comment:
            self.assertFalse(
                line.startswith("Before="),
                f"activated contract keeps no Before= edge: {line!r}",
            )
        self.assertIn("User=root", service)
        self.assertNotIn("RestrictAddressFamilies=", service)
        self.assertNotIn("ProtectSystem=", service)
        self.assertIn(
            "RequiresMountsFor=/run/greia-persist /var/lib/greia-os "
            "/boot/grub /etc/greia-os/layout",
            service,
        )

    def test_update_socket_stays_separate_and_on_demand(self) -> None:
        # Activated contract: gate absent on the socket too; the listener
        # keeps its narrow identity and stays separate from the installer
        # transaction socket (installer media only).
        text = self._read(
            "build/overlay/etc/systemd/system/greia-system-update.socket"
        )
        self.assertIn("ListenStream=/run/greia-os/system-update.sock", text)
        self.assertIn("SocketMode=0660", text)
        self.assertIn("SocketGroup=greiapanel", text)
        self.assertIn("SocketUser=root", text)
        self.assertIn("Accept=no", text)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped or stripped.startswith("["):
                continue
            self.assertFalse(
                stripped.startswith("Condition"),
                f"activated contract must not gate: {stripped!r}",
            )
        self.assertNotIn("ConditionPathExists=", text)
        self.assertIn("WantedBy=sockets.target", text)
        installer = self._read(
            "build/installer-overlay/etc/systemd/system/"
            "greia-install-transaction.socket"
        )
        self.assertIn("ListenStream=/run/greia-os/install-transaction.sock", installer)
        self.assertNotEqual(
            "system-update.sock", "install-transaction.sock",
        )

    def test_runtime_tmpfiles_does_not_re_declare_the_socket_directory(self) -> None:
        """One owner of record for /run/greia-os, or Xorg cannot write its log.

        This file used to re-declare the path as root:root 0755. /etc/tmpfiles.d
        sorts before /usr/lib/tmpfiles.d, so the duplicate won, Xorg (greiakid)
        could not open Xorg.0.log, and greia-launcher.service restart-looped with
        the boot-marker spool unwritable in the same directory.
        """
        text = self._read("build/overlay/usr/lib/tmpfiles.d/greia-os-runtime.conf")
        directives = [
            " ".join(line.split()[:5])
            for line in text.splitlines()
            if line.split() and not line.strip().startswith("#")
        ]
        self.assertFalse(
            [line for line in directives if line.startswith(("d ", "d+ "))],
            f"this file must not declare directories; found {directives}",
        )
        owner_of_record = self._read("build/overlay/etc/tmpfiles.d/greia-os.conf")
        self.assertIn("d /run/greia-os 0770 greiakid greiaprofiles -", owner_of_record)

    def test_update_service_module_reuses_shared_seams(self) -> None:
        import re

        source = self._read("src/greia_platform/system_updates.py")
        self.assertNotIn("class SlotWriter", source)
        self.assertNotIn("class SlotFinalizer", source)
        self.assertNotIn("class BootTransactionJournal", source)
        self.assertIn("from .slot_writer import", source)
        self.assertIn("from .boot_transaction import", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("/dev/", source)
        self.assertIsNone(re.search(r"^class \w*Manager\b", source, re.M))
        self.assertIsNone(re.search(r"^class \w*Daemon\b", source, re.M))

    def test_single_root_backend_contract_preserved(self) -> None:
        backend = UnavailableSystemUpdateBackend()
        self.assertFalse(backend.available)
        self.assertEqual(
            backend.status_payload()["reason"],
            "A/B system-slot backend is not configured",
        )
        # Structural protocol conformance (Protocol is not runtime_checkable).
        for method in ("stage", "arm", "confirm_boot_health", "reconcile"):
            self.assertTrue(callable(getattr(backend, method)))
            self.assertTrue(callable(getattr(SlotBackedSystemUpdateBackend, method)))

    def test_parent_activation_stays_unavailable(self) -> None:
        source = self._read("src/greia_parent/update_api.py")
        self.assertNotIn('"system.update.activate": False', source)
        self.assertIn(
            '"system.update.activate": self._system_update_activation_available()',
            source,
        )
        self.assertIn('"activation_available"] = activation_available', source)
        with tempfile.TemporaryDirectory() as directory:
            inbox = SystemUpdateInbox(Path(directory))
            status = inbox.status_payload()
            self.assertFalse(status["activation_available"])


if __name__ == "__main__":
    unittest.main()
