"""A8-UPDATE-SVC: SystemUpdateService on the common slot/journal seams (8A.6).

The privileged update side reuses the shared SlotWriter/SlotFinalizer and
the shared BootTransactionJournal behind the socket-activated service while
the inbox stays unprivileged: single-root layouts stay unavailable,
the active/accepted slot is never writable, every refusal leaves the
destination seam untouched, and the Parent semantic API keeps reporting
``system.update.activate=false``. No valued disk is touched: slot stores
are pre-sized loopback files under tmpdirs and every other seam is a fake.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import socket
import tempfile
import unittest
import zipfile
from pathlib import Path

from greia_platform.boot_transaction import BootTransactionJournal, FakeGrubBackend
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.system_updates import (
    HARDWARE_SUPPORT_NAME,
    MANIFEST_NAME,
    PAYLOAD_NAME,
    PERSISTENT_CONTRACT_NAME,
    SCHEMA_VERSION,
    SIGNATURE_NAME,
    SignatureEnvelope,
    SlotBackedSystemUpdateBackend,
    SystemIdentity,
    SystemUpdateService,
    SystemUpdateError,
    SystemUpdateInbox,
    SystemUpdateServiceAuthority,
    UnavailableSystemUpdateBackend,
    UpdateBackendUnavailable,
    UpdateCandidateSummary,
    UpdateManifest,
    UpdateSlotSeams,
    build_persistent_state_contract_bytes,
    inactive_slot_for,
    inspect_update_bundle,
    load_installed_layout_record,
    read_accepted_sequence,
)


HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None

_HW_BYTES = b"\x28\xb5\x2f\xfd" + b"hwset" * 32
_CONTRACT_BYTES = build_persistent_state_contract_bytes()

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32

_SLOT_BYTES = 1024 * 1024 * 1024


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_release_sequence": 7,
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


def _payload(size: int = 200 * 1024) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _manifest(payload: bytes, *, sequence: int = 9) -> UpdateManifest:
    hw_sha = hashlib.sha256(_HW_BYTES).hexdigest()
    contract_sha = hashlib.sha256(_CONTRACT_BYTES).hexdigest()
    return UpdateManifest(
        schema_version=SCHEMA_VERSION,
        release_id="greia-0.15.0",
        version="0.15.0",
        release_sequence=sequence,
        platform_family="standard-x86-64",
        architecture="x86-64",
        profile="modern-amd64",
        signer="greia-release-main",
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        payload_size=len(payload),
        payload_filesystem_bytes=len(payload),
        payload_minimum_slot_bytes=len(payload),
        hardware_support_name=HARDWARE_SUPPORT_NAME,
        hardware_support_schema_version=1,
        hardware_support_sha256=hw_sha,
        hardware_support_size=len(_HW_BYTES),
        persistent_contract_schema_version=1,
        persistent_contract_sha256=contract_sha,
        persistent_contract_size=len(_CONTRACT_BYTES),
        release_notes="Step 8A.6 test release.",
    )


def _unsigned_bundle(root: Path, payload: bytes, *, name: str = "candidate.greiaupdate") -> Path:
    manifest = _manifest(payload)
    signature = SignatureEnvelope(
        schema_version=SCHEMA_VERSION,
        algorithm="ed25519",
        signer=manifest.signer,
        signature=b"x" * 64,
    )
    path = root / name
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
        archive.writestr(SIGNATURE_NAME, signature.as_json_bytes())
        archive.writestr(PAYLOAD_NAME, payload)
        archive.writestr(HARDWARE_SUPPORT_NAME, _HW_BYTES)
        archive.writestr(PERSISTENT_CONTRACT_NAME, _CONTRACT_BYTES)
    return path


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
        )

        self._root = root
        self._attestation = HardwareInventoryAttestation
        self._loopback = LoopbackSlotFile
        self._support_set = ReleaseSupportSet
        self.contacts: list[str] = []
        self.filesystem = FakeSlotFilesystem(root / "mnt")
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
        return _CONTRACT_BYTES

    def seams(self) -> UpdateSlotSeams:
        return UpdateSlotSeams(
            slot_store_factory=self.slot_store_factory,
            filesystem_factory=self.filesystem_factory,
            package_installer_factory=self.package_installer_factory,
            inventory_factory=self.inventory_factory,
            support_set_factory=self.support_set_factory,
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
            bundle = inspect_update_bundle(_unsigned_bundle(root, _payload()))
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
            bundle = inspect_update_bundle(_unsigned_bundle(root, _payload()))
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
            bundle = inspect_update_bundle(_unsigned_bundle(root, _payload()))
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
            bundle = inspect_update_bundle(_unsigned_bundle(root, _payload()))
            with self.assertRaisesRegex(UpdateBackendUnavailable, "not configured"):
                backend.stage(bundle)

    def test_unavailable_backend_keeps_arm_confirm_reconcile_closed(self) -> None:
        backend = UnavailableSystemUpdateBackend("single-root layout")
        service = SystemUpdateService(
            Path("/nonexistent"), Path("/nonexistent"), _identity(), backend
        )
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
            bundle = inspect_update_bundle(_unsigned_bundle(root, _payload()))
            with self.assertRaises(SystemUpdateError):
                backend.stage(bundle)
            self.assertEqual(seams.contacts, [])

    def test_second_stage_while_transaction_active_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            first = inspect_update_bundle(
                _unsigned_bundle(root, _payload(), name="first.greiaupdate")
            )
            backend.stage(first)
            contacts_after_first = list(seams.contacts)
            self.assertTrue(contacts_after_first)
            second = inspect_update_bundle(
                _unsigned_bundle(root, b"second-payload" + _payload(), name="second.greiaupdate")
            )
            with self.assertRaisesRegex(SystemUpdateError, "already active"):
                backend.stage(second)


class InactiveSlotStagingTests(unittest.TestCase):
    def test_stage_writes_inactive_slot_and_records_shared_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            payload = _payload()
            bundle = inspect_update_bundle(_unsigned_bundle(root, payload))
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
            self.assertEqual(journal.release_sequence, 9)
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
            bundle = inspect_update_bundle(_unsigned_bundle(root, _payload()))
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


class ArmConfirmReconcileTests(unittest.TestCase):
    def _staged(
        self, root: Path
    ) -> tuple[SlotBackedSystemUpdateBackend, FakeGrubBackend, RecordingSeams]:
        seams = RecordingSeams(root)
        boot_state = root / "boot"
        boot_state.mkdir()
        grub = FakeGrubBackend.initialize(boot_state, default_slot="A")
        backend, _ = _backend(root, seams, boot_backend=grub)
        backend.stage(inspect_update_bundle(_unsigned_bundle(root, _payload())))
        return backend, grub, seams

    def test_arm_without_boot_backend_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            backend.stage(inspect_update_bundle(_unsigned_bundle(root, _payload())))
            with self.assertRaisesRegex(UpdateBackendUnavailable, "not wired"):
                backend.arm()

    def test_arm_confirm_round_trip_accepts_and_persists_sequence(self) -> None:
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
            self.assertEqual(read_accepted_sequence(root / "state"), 9)
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
            self.assertEqual(read_accepted_sequence(root / "state"), 0)

    def test_reconcile_without_observation_stays_steady(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            backend.stage(inspect_update_bundle(_unsigned_bundle(root, _payload())))
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


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is required for trust tests")
class ServiceTrustOrderingTests(unittest.TestCase):
    def _signed_bundle(
        self, root: Path, *, sequence: int = 9
    ) -> tuple[Path, Path, object]:
        from greia_platform.system_updates import (
            build_update_bundle,
            generate_ed25519_keypair,
        )

        private = root / "private.pem"
        public = root / "public.pem"
        generate_ed25519_keypair(private, public)
        payload = root / "slot.img"
        payload.write_bytes(_payload())
        hardware = root / "hw.tar.zst"
        hardware.write_bytes(_HW_BYTES)
        contract = root / "contract.json"
        contract.write_bytes(_CONTRACT_BYTES)
        bundle = root / "release.greiaupdate"
        manifest = build_update_bundle(
            payload_path=payload,
            hardware_support_path=hardware,
            persistent_contract_path=contract,
            output_path=bundle,
            version="0.15.0",
            release_id="greia-0.15.0",
            release_sequence=sequence,
            platform_family="standard-x86-64",
            architecture="x86-64",
            profile="modern-amd64",
            signer="greia-release-main",
            private_key_path=private,
        )
        return bundle, public, manifest

    def test_untrusted_bundle_never_reaches_the_slot_seam(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, _, _ = self._signed_bundle(root)
            key_dir = root / "trusted"
            key_dir.mkdir()
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            service = SystemUpdateService(
                root / "state", key_dir, _identity(), backend
            )
            # No trusted key installed: trust fails before any slot contact.
            with self.assertRaises(SystemUpdateError):
                service.stage(bundle)
            self.assertEqual(seams.contacts, [])

    def test_trusted_stage_flows_through_service_to_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, public, manifest = self._signed_bundle(root)
            key_dir = root / "trusted"
            key_dir.mkdir()
            (key_dir / "greia-release-main.pem").write_bytes(public.read_bytes())
            seams = RecordingSeams(root)
            boot_state = root / "boot"
            boot_state.mkdir()
            grub = FakeGrubBackend.initialize(boot_state, default_slot="A")
            backend, _ = _backend(root, seams, boot_backend=grub)
            service = SystemUpdateService(
                root / "state", key_dir, _identity(), backend
            )
            staged = service.stage(bundle)
            self.assertEqual(staged.manifest.release_id, "greia-0.15.0")
            self.assertIn("store:system-b", seams.contacts)
            journal = BootTransactionJournal.load(backend.journal_dir)
            self.assertEqual(journal.candidate_slot, "B")
            status = service.status_payload()
            self.assertTrue(status["activation"]["available"])
            self.assertEqual(status["accepted_release_sequence"], 0)

    def test_rollback_sequence_is_rejected_before_slot_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, public, _ = self._signed_bundle(root, sequence=3)
            key_dir = root / "trusted"
            key_dir.mkdir()
            (key_dir / "greia-release-main.pem").write_bytes(public.read_bytes())
            seams = RecordingSeams(root)
            backend, _ = _backend(root, seams)
            service = SystemUpdateService(
                root / "state", key_dir, _identity(), backend, accepted_sequence=7
            )
            with self.assertRaises(SystemUpdateError):
                service.stage(bundle)
            self.assertEqual(seams.contacts, [])


class AuthoritySocketTests(unittest.TestCase):
    def _authority(
        self, root: Path, *, present: bool = True
    ) -> SystemUpdateServiceAuthority:
        from greia_platform.system_updates import generate_ed25519_keypair

        key_dir = root / "trusted"
        key_dir.mkdir(exist_ok=True)
        if present:
            private = root / "private.pem"
            public = root / "public.pem"
            if not private.exists():
                generate_ed25519_keypair(private, public)
            (key_dir / "greia-release-main.pem").write_bytes(public.read_bytes())
        seams = RecordingSeams(root)
        backend, _ = _backend(root, seams)
        authority = SystemUpdateServiceAuthority(
            root / "state", key_dir, _identity(), backend
        )
        if present:
            from greia_platform.system_updates import build_update_bundle

            payload = root / "slot.img"
            payload.write_bytes(_payload())
            hardware = root / "hw.tar.zst"
            hardware.write_bytes(_HW_BYTES)
            contract = root / "contract.json"
            contract.write_bytes(_CONTRACT_BYTES)
            bundle = root / "release.greiaupdate"
            if not bundle.exists():
                build_update_bundle(
                    payload_path=payload,
                    hardware_support_path=hardware,
                    persistent_contract_path=contract,
                    output_path=bundle,
                    version="0.15.0",
                    release_id="greia-0.15.0",
                    release_sequence=9,
                    platform_family="standard-x86-64",
                    architecture="x86-64",
                    profile="modern-amd64",
                    signer="greia-release-main",
                    private_key_path=root / "private.pem",
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

    def test_single_root_layout_summary_reports_unavailable_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key_dir = root / "trusted"
            key_dir.mkdir()
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
            authority = SystemUpdateServiceAuthority(
                root / "state", key_dir, _identity(), backend
            )
            layout = authority.layout_summary()
            self.assertTrue(layout["single_root"])
            self.assertFalse(backend.available)

    @unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is required for trust tests")
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
            self.assertFalse(payload["candidate"]["signature_verified"])
            _, op, payload = read_response(
                endpoint.handle_request(
                    build_request("VERIFY_CURRENT_CANDIDATE"),
                    peer=root_peer,
                    boot_state="update_ready",
                )
            )
            self.assertEqual(payload["status"], "VERIFIED")
            self.assertTrue(payload["candidate"]["signature_verified"])
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
            # Staging again without arm/confirm is refused: the active
            # transaction must be reconciled or confirmed first.
            with self.assertRaisesRegex(SystemUpdateError, "already active"):
                endpoint.handle_request(
                    build_request("STAGE_CURRENT_CANDIDATE"),
                    peer=root_peer,
                    boot_state="update_ready",
                )

    @unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is required for trust tests")
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
                handle_update_connection(
                    forged_right,
                    authority=authority,
                    peer=0,  # type: ignore[arg-type]
                )
                frames = []
                while True:
                    chunk = forged_left.recv(65536)
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
                        "signature_verified": False,
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
        service = self._read(
            "build/overlay/etc/systemd/system/greia-system-update.service"
        )
        self.assertIn(
            "ExecStart=/usr/bin/python3 -m greia_platform.system_updates "
            "--socket-activated",
            service,
        )
        self.assertIn(
            "ConditionPathExists=/run/greia-os/enable-privileged-transactions",
            service,
        )
        self.assertNotIn("WantedBy=", service)
        self.assertIn("RestrictAddressFamilies=AF_UNIX", service)
        self.assertIn("ReadWritePaths=/var/lib/greia-os /run/greia-os", service)

    def test_update_socket_stays_separate_and_gated(self) -> None:
        text = self._read(
            "build/overlay/etc/systemd/system/greia-system-update.socket"
        )
        self.assertIn("ListenStream=/run/greia-os/system-update.sock", text)
        self.assertIn("SocketMode=0600", text)
        self.assertIn("SocketUser=root", text)
        self.assertIn("Accept=no", text)
        self.assertIn(
            "ConditionPathExists=/run/greia-os/enable-privileged-transactions", text
        )
        installer = self._read(
            "build/installer-overlay/etc/systemd/system/"
            "greia-install-transaction.socket"
        )
        self.assertIn("ListenStream=/run/greia-os/install-transaction.sock", installer)
        self.assertNotEqual(
            "system-update.sock", "install-transaction.sock",
        )

    def test_runtime_tmpfiles_creates_socket_directory(self) -> None:
        text = self._read("build/overlay/usr/lib/tmpfiles.d/greia-os-runtime.conf")
        self.assertIn("d /run/greia-os 0755 root root -", text)

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
        self.assertIn('"system.update.activate": False', source)
        self.assertIn('"activation_available"] = False', source)
        with tempfile.TemporaryDirectory() as directory:
            inbox = SystemUpdateInbox(Path(directory))
            status = inbox.status_payload()
            self.assertFalse(status["activation_available"])
            self.assertFalse(status["signature_verified"])


if __name__ == "__main__":
    unittest.main()
