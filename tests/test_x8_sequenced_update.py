"""X8-UPDATE (Phase 8B Step 8B.4): signed-sequence A->B->A updates plus broken candidates.

Source scope only (Acer/QEMU execution stays RED/deferred per the
source-first amendment): every test runs on disposable tmpdirs through the
narrow privileged update service
(``SystemUpdateServiceAuthority``/``UpdatePrivilegedEndpoint``) and the real
x86 one-shot backend (``GrubEnvBackend``), reusing the shared
``SlotWriter``/``SlotFinalizer``/``BootTransactionJournal`` seams. Slot
stores are sparse loopback files; no valued disk is contacted.

Proven here:

- successful A->B then B->A updates with different signed release sequences
  (8 -> 9 -> 10), where the health commit advances the trusted layout
  authority so the second update resolves the other inactive slot;
- the accepted slot (persistent default) is never the candidate before a
  verified health commit: stage and arm leave it unchanged;
- the broken-candidate matrix: generic-kernel missing (firmware cannot boot
  the candidate), wrong root identity (BOOT_HEALTHY refuses), userspace
  crash before health, power loss while arming (torn one-shot), and power
  loss during the healthy commit (torn backend/journal). Failed candidates
  return automatically to the accepted slot;
- PERSIST shared state survives update and rollback per the release state
  contract (candidate must bind the installed contract before any
  inactive-slot write);
- signature, compatibility, anti-rollback, capacity and state-contract
  preflights all refuse before any inactive-slot write; staging streams the
  retained bundle in bounded chunks with no second payload-sized temporary.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from dataclasses import replace as _replace
from pathlib import Path

from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionCoordinator,
    BootTransactionJournal,
    BootTransactionState,
)
from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.persistent_layout import (
    InstalledLayoutRecord,
    assert_persistent_contract_accepted,
)
from greia_platform.privileged_channel import PeerCredential
from greia_platform.slot_writer import (
    FINALIZER_VERSION,
    DestinationSlot,
    FinalizationReceipt,
    HardwareInventoryAttestation,
    LoopbackSlotFile,
    ReleaseSupportSet,
    SlotWriteError,
    SlotWriter,
    VerifiedReleaseMember,
)
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
    SystemUpdateError,
    SystemUpdateInbox,
    SystemUpdateService,
    SystemUpdateServiceAuthority,
    UpdateBackendUnavailable,
    UpdateManifest,
    UpdateSlotSeams,
    advance_layout_authority_for_acceptance,
    build_persistent_state_contract_bytes,
    build_update_bundle,
    generate_ed25519_keypair,
    inspect_update_bundle,
    load_installed_layout_record,
    read_accepted_sequence,
    write_accepted_sequence,
)
from greia_platform.update_privileged import (
    UpdatePrivilegedEndpoint,
    build_request,
    read_response,
)


HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None

_LEGACY_LAYOUT = "legacy-bios-ab-v1"
_BOOT_BACKEND = "grub-ab-v1"
_FAMILY = "legacy-x86"
_ARCH = "x86-64"
_PROFILE = "legacy-x86-base"
_SIGNER = "greia-release-main"
_SLOT_BYTES = 1024 * 1024 * 1024

_HW_BYTES = b"\x28\xb5\x2f\xfd" + b"x8-update-hw" * 64
_CONTRACT_BYTES = build_persistent_state_contract_bytes()

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32

_KERNEL = hashlib.sha256(b"x8-candidate-kernel").hexdigest()
_INITRAMFS = hashlib.sha256(b"x8-candidate-initramfs").hexdigest()
_INVENTORY = "cd" * 32
_SUPPORT = "ef" * 32

_R8_ID = "greia-0.16.0"
_R8_SEQ = 8
_R9_ID = "greia-0.17.0"
_R9_SEQ = 9
_R10_ID = "greia-0.18.0"
_R10_SEQ = 10


def _payload(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": _R8_ID,
        "accepted_release_sequence": _R8_SEQ,
        "accepted_slot": "A",
        "boot_backend": _BOOT_BACKEND,
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": _PROFILE,
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": _LEGACY_LAYOUT,
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": _FAMILY,
        "schema_version": 1,
        "slot_bytes": _SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _write_layout(root: Path, name: str = "installed-layout.json", **overrides: object) -> Path:
    path = root / name
    path.write_bytes(
        (json.dumps(_record_dict(**overrides), sort_keys=True) + "\n").encode()
    )
    return path


def _identity() -> SystemIdentity:
    return SystemIdentity("0.16.0", _FAMILY, _ARCH, _PROFILE)


class _FakeSlotFilesystem:
    """Destination-only fake: records every mutation in order."""

    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.mount_dir.mkdir(parents=True, exist_ok=True)
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


class _FakeSlotPackageInstaller:
    def install(
        self, firmware: tuple[str, ...], microcode: tuple[str, ...]
    ) -> tuple[object, ...]:
        return ()


class _Seams:
    """Recording factories: sparse loopback stores, fakes elsewhere."""

    def __init__(self, root: Path, persist_root: Path) -> None:
        self._root = root
        self._persist_root = persist_root
        self.slots_dir = root / "slots"
        self.slots_dir.mkdir(parents=True, exist_ok=True)
        self.contacts: list[str] = []
        self.filesystem = _FakeSlotFilesystem(root / "mnt")
        self.package_installer = _FakeSlotPackageInstaller()

    def token(self) -> str:
        return hashlib.sha256(b"inventory-x8-update").hexdigest()

    def slot_store_factory(self, destination: object) -> object:
        self.contacts.append(f"store:{getattr(destination, 'role', '?')}")
        capacity = int(getattr(destination, "slot_capacity_bytes", 0))
        role = str(getattr(destination, "role", "system-b"))
        return LoopbackSlotFile.create(self.slots_dir / f"slot-{role}.img", capacity)

    def filesystem_factory(self) -> object:
        self.contacts.append("filesystem")
        return self.filesystem

    def package_installer_factory(self) -> object:
        self.contacts.append("package-installer")
        return self.package_installer

    def inventory_factory(self) -> object:
        self.contacts.append("inventory")
        return HardwareInventoryAttestation(token=self.token())

    def support_set_factory(self, bundle: object) -> object:
        self.contacts.append("support")
        manifest = getattr(bundle, "manifest")
        return ReleaseSupportSet(
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
            installed_size_bound=0,
            provided_firmware=frozenset(),
            provided_microcode=frozenset(),
            packages=(),
        )

    def installed_contract_factory(self) -> bytes:
        self.contacts.append("contract")
        return (
            self._persist_root / "greia" / "persistent-state-contract.json"
        ).read_bytes()

    def seams(self) -> UpdateSlotSeams:
        return UpdateSlotSeams(
            slot_store_factory=self.slot_store_factory,
            filesystem_factory=self.filesystem_factory,
            package_installer_factory=self.package_installer_factory,
            inventory_factory=self.inventory_factory,
            support_set_factory=self.support_set_factory,
            installed_contract_factory=self.installed_contract_factory,
        )


class _Rig:
    """One disposable legacy A/B machine: dirs, keys, releases, service."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_dir = root / "state"
        self.key_dir = root / "trusted"
        self.key_dir.mkdir(parents=True, exist_ok=True)
        self.persist_root = root / "persist"
        self.layout_path = _write_layout(root)
        self.private_key = root / "release-private.pem"
        self.public_key = root / "release-public.pem"
        generate_ed25519_keypair(self.private_key, self.public_key)
        (self.key_dir / f"{_SIGNER}.pem").write_bytes(self.public_key.read_bytes())
        self.releases: dict[str, Path] = {}
        self._write_persist_fixture()
        write_accepted_sequence(self.state_dir, _R8_SEQ)
        boot_dir = root / "boot"
        boot_dir.mkdir(parents=True, exist_ok=True)
        self.grub = GrubEnvBackend.initialize(boot_dir, default_slot="A")
        self.seams = _Seams(root, self.persist_root)
        self.backend = SlotBackedSystemUpdateBackend(
            self.state_dir,
            layout_record_path=self.layout_path,
            seams=self.seams.seams(),
            boot_backend=self.grub,
        )
        self.authority = SystemUpdateServiceAuthority(
            self.state_dir, self.key_dir, _identity(), self.backend
        )
        self.endpoint = UpdatePrivilegedEndpoint(self.authority)  # type: ignore[arg-type]
        self.peer = PeerCredential(uid=0)
        self.markers = self._snapshot_markers()

    def build_release(
        self, name: str, *, release_id: str, sequence: int, size: int
    ) -> Path:
        work = self.root / "releases" / name
        work.mkdir(parents=True, exist_ok=True)
        payload = work / "slot.img"
        payload.write_bytes(_payload(size, f"x8-{name}:".encode()))
        hardware = work / "hw.tar.zst"
        hardware.write_bytes(_HW_BYTES)
        contract = work / "contract.json"
        contract.write_bytes(_CONTRACT_BYTES)
        bundle = work / f"{name}.greiaupdate"
        build_update_bundle(
            payload_path=payload,
            hardware_support_path=hardware,
            persistent_contract_path=contract,
            output_path=bundle,
            version=release_id.split("-", 1)[1],
            release_id=release_id,
            release_sequence=sequence,
            platform_family=_FAMILY,
            architecture=_ARCH,
            profile=_PROFILE,
            signer=_SIGNER,
            private_key_path=self.private_key,
            release_notes=f"X8-UPDATE test release {name}.",
        )
        self.releases[name] = bundle
        return bundle

    def op(self, name: str) -> tuple[str, dict[str, object]]:
        raw = self.endpoint.handle_request(
            build_request(name), peer=self.peer, boot_state="update_ready"
        )
        _, op_name, payload = read_response(raw)
        return op_name, payload

    def receive(self, name: str) -> None:
        SystemUpdateInbox(self.state_dir).receive(self.releases[name])

    def record(self) -> InstalledLayoutRecord:
        loaded = load_installed_layout_record(self.layout_path)
        assert loaded is not None
        return loaded

    def _write_persist_fixture(self) -> None:
        state = self.persist_root / "greia"
        (state / "namespaces" / "child-profiles").mkdir(parents=True, exist_ok=True)
        (state / "namespaces" / "activity-saves").mkdir(parents=True, exist_ok=True)
        (state / "persistent-state-contract.json").write_bytes(_CONTRACT_BYTES)
        (state / "namespaces" / "child-profiles" / "profile.json").write_bytes(
            b'{"schema":1,"name":"test-child"}\n'
        )
        (state / "namespaces" / "activity-saves" / "save.json").write_bytes(
            b'{"schema":1,"stars":3}\n'
        )

    def _snapshot_markers(self) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for marker in (
            self.persist_root / "greia" / "namespaces" / "child-profiles" / "profile.json",
            self.persist_root / "greia" / "namespaces" / "activity-saves" / "save.json",
            self.persist_root / "greia" / "persistent-state-contract.json",
        ):
            digest = hashlib.sha256()
            with marker.open("rb") as handle:
                while True:
                    chunk = handle.read(65536)
                    if not chunk:
                        break
                    digest.update(chunk)
            snapshot[str(marker.relative_to(self.persist_root))] = digest.hexdigest()
        return snapshot

    def assert_persist_intact(self) -> None:
        live = self._snapshot_markers()
        assert live == self.markers, "PERSIST shared state did not survive"


def _receipt(*, slot: str, release_id: str, sequence: int) -> FinalizationReceipt:
    return FinalizationReceipt(
        schema_version=1,
        finalizer_version=FINALIZER_VERSION,
        release_id=release_id,
        release_sequence=sequence,
        slot=slot,
        role=f"system-{slot.lower()}",
        base_sha256=_KERNEL,
        base_bytes=200 * 1024,
        support_sha256=_SUPPORT,
        support_size=1024,
        inventory_token=_INVENTORY,
        packages=(),
        packages_digest=hashlib.sha256(b"\n").hexdigest(),
        generic_kernel_sha256=_KERNEL,
        host_initramfs_sha256=_INITRAMFS,
        filesystem_uuid=_UUID_B_FS if slot == "B" else _UUID_A_FS,
        layout_id=_LEGACY_LAYOUT,
        slot_capacity_bytes=_SLOT_BYTES,
    )


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is required for trust tests")
class SequencedABAUpdateTests(unittest.TestCase):
    """A->B->A through the privileged service and the x86 one-shot backend."""

    def _rig(self, root: Path) -> _Rig:
        rig = _Rig(root)
        rig.build_release("r9", release_id=_R9_ID, sequence=_R9_SEQ, size=220 * 1024)
        rig.build_release("r10", release_id=_R10_ID, sequence=_R10_SEQ, size=240 * 1024)
        rig.build_release("r8r", release_id="greia-0.16.1", sequence=_R8_SEQ, size=210 * 1024)
        return rig

    def test_ab_then_ba_accepts_and_advances_layout_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            # -- Phase 1: A -> B -------------------------------------------
            rig.receive("r9")
            op, status = rig.op("STATUS")
            self.assertEqual(op, "STATUS")
            self.assertTrue(status["candidate"]["present"])
            op, verified = rig.op("VERIFY_CURRENT_CANDIDATE")
            self.assertEqual(verified["status"], "VERIFIED")
            # Accepted slot is untouched before any restart.
            self.assertEqual(rig.grub.inspect().default_slot, "A")
            self.assertEqual(rig.record().accepted_slot, "A")
            op, staged = rig.op("STAGE_CURRENT_CANDIDATE")
            self.assertEqual(staged["status"], "STAGED")
            self.assertEqual(staged["detail"]["candidate_slot"], "B")
            self.assertIn("store:system-b", rig.seams.contacts)
            self.assertNotIn("store:system-a", rig.seams.contacts)
            self.assertEqual(rig.seams.filesystem.bound_uuid, _UUID_B_FS)
            self.assertEqual(rig.grub.inspect().default_slot, "A")
            self.assertEqual(rig.record().accepted_slot, "A")
            op, armed = rig.op("ARM_CURRENT_CANDIDATE")
            self.assertEqual(armed["status"], "ARMED")
            # Arming sets only the one-shot; the persistent default holds.
            self.assertEqual(rig.grub.inspect().default_slot, "A")
            self.assertEqual(rig.grub.inspect().one_shot_slot, "B")
            self.assertEqual(rig.record().accepted_slot, "A")
            self.assertEqual(rig.grub.simulate_reboot(), "B")
            op, confirmed = rig.op("CONFIRM_BOOT_HEALTH")
            self.assertEqual(confirmed["status"], "CONFIRMED")
            detail = confirmed["detail"]
            self.assertTrue(detail["confirmed"])
            self.assertEqual(detail["state"], "accepted")
            self.assertEqual(detail["booted_slot"], "B")
            self.assertEqual(rig.grub.inspect().default_slot, "B")
            self.assertEqual(read_accepted_sequence(rig.state_dir), _R9_SEQ)
            record = rig.record()
            self.assertEqual(record.accepted_slot, "B")
            self.assertEqual(record.boot_control.active_slot, "B")
            self.assertEqual(record.accepted_release_id, _R9_ID)
            self.assertEqual(record.accepted_release_sequence, _R9_SEQ)
            # Confirm is idempotent once terminal.
            op, again = rig.op("CONFIRM_BOOT_HEALTH")
            self.assertTrue(again["detail"]["confirmed"])
            self.assertEqual(rig.record().accepted_slot, "B")
            rig.assert_persist_intact()

            # -- Phase 2: B -> A with the SAME authority object ------------
            phase1_contacts = len(rig.seams.contacts)
            rig.receive("r10")
            op, staged = rig.op("STAGE_CURRENT_CANDIDATE")
            self.assertEqual(staged["status"], "STAGED")
            self.assertEqual(staged["detail"]["candidate_slot"], "A")
            new_contacts = rig.seams.contacts[phase1_contacts:]
            self.assertIn("store:system-a", new_contacts)
            self.assertNotIn("store:system-b", new_contacts)
            self.assertEqual(rig.seams.filesystem.bound_uuid, _UUID_A_FS)
            self.assertEqual(rig.grub.inspect().default_slot, "B")
            self.assertEqual(rig.record().accepted_slot, "B")
            rig.op("ARM_CURRENT_CANDIDATE")
            self.assertEqual(rig.grub.inspect().default_slot, "B")
            self.assertEqual(rig.grub.inspect().one_shot_slot, "A")
            self.assertEqual(rig.grub.simulate_reboot(), "A")
            op, confirmed = rig.op("CONFIRM_BOOT_HEALTH")
            self.assertTrue(confirmed["detail"]["confirmed"])
            self.assertEqual(confirmed["detail"]["booted_slot"], "A")
            self.assertEqual(rig.grub.inspect().default_slot, "A")
            self.assertEqual(read_accepted_sequence(rig.state_dir), _R10_SEQ)
            record = rig.record()
            self.assertEqual(record.accepted_slot, "A")
            self.assertEqual(record.boot_control.active_slot, "A")
            self.assertEqual(record.accepted_release_id, _R10_ID)
            self.assertEqual(record.accepted_release_sequence, _R10_SEQ)
            rig.assert_persist_intact()

    def test_equal_sequence_replays_as_no_update_after_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            rig.receive("r9")
            rig.op("STAGE_CURRENT_CANDIDATE")
            rig.op("ARM_CURRENT_CANDIDATE")
            rig.grub.simulate_reboot()
            rig.op("CONFIRM_BOOT_HEALTH")
            contacts_after_accept = list(rig.seams.contacts)
            # Re-receiving the just-accepted bundle is a no-update replay:
            # the same long-lived authority re-reads the persisted sequence.
            rig.receive("r9")
            op, staged = rig.op("STAGE_CURRENT_CANDIDATE")
            self.assertEqual(staged["status"], "STAGED")
            self.assertFalse(staged["detail"]["staged"])
            self.assertEqual(staged["detail"]["decision"], "no-update")
            self.assertEqual(rig.seams.contacts, contacts_after_accept)
            self.assertEqual(rig.record().accepted_slot, "B")

    def test_older_signed_sequence_is_rejected_after_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            rig.receive("r9")
            rig.op("STAGE_CURRENT_CANDIDATE")
            rig.op("ARM_CURRENT_CANDIDATE")
            rig.grub.simulate_reboot()
            rig.op("CONFIRM_BOOT_HEALTH")
            contacts_after_accept = list(rig.seams.contacts)
            rig.receive("r8r")
            with self.assertRaises(SystemUpdateError):
                rig.op("STAGE_CURRENT_CANDIDATE")
            self.assertEqual(rig.seams.contacts, contacts_after_accept)
            self.assertEqual(rig.record().accepted_slot, "B")
            self.assertEqual(rig.grub.inspect().default_slot, "B")


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is required for trust tests")
class BrokenCandidateMatrixTests(unittest.TestCase):
    """Each failure mode leaves accepted pre-restart and returns to it."""

    def _rig(self, root: Path) -> _Rig:
        rig = _Rig(root)
        rig.build_release("r9", release_id=_R9_ID, sequence=_R9_SEQ, size=220 * 1024)
        return rig

    def _stage_and_arm(self, rig: _Rig) -> None:
        rig.receive("r9")
        _, staged = rig.op("STAGE_CURRENT_CANDIDATE")
        self.assertEqual(staged["detail"]["candidate_slot"], "B")
        rig.op("ARM_CURRENT_CANDIDATE")
        self.assertEqual(rig.grub.inspect().default_slot, "A")
        self.assertEqual(rig.record().accepted_slot, "A")

    def _assert_rolled_back(self, rig: _Rig) -> None:
        self.assertEqual(rig.grub.inspect().default_slot, "A")
        record = rig.record()
        self.assertEqual(record.accepted_slot, "A")
        self.assertEqual(record.boot_control.active_slot, "A")
        self.assertEqual(record.accepted_release_sequence, _R8_SEQ)
        self.assertEqual(read_accepted_sequence(rig.state_dir), _R8_SEQ)
        journal = BootTransactionJournal.load(rig.backend.journal_dir)
        self.assertEqual(journal.state, BootTransactionState.ROLLED_BACK)
        rig.assert_persist_intact()

    def test_generic_kernel_missing_falls_back_to_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            self._stage_and_arm(rig)
            # Firmware cannot boot the kernel-less candidate: the one-shot
            # is consumed and the machine stays on the accepted slot.
            rig.grub.reconcile("A")
            _, confirmed = rig.op("CONFIRM_BOOT_HEALTH")
            self.assertFalse(confirmed["detail"]["confirmed"])
            self.assertEqual(confirmed["detail"]["state"], "rolled_back")
            self._assert_rolled_back(rig)

    def test_wrong_root_identity_refused_by_health_then_falls_back(self) -> None:
        from greia_launcher.boot_health import TRUSTED_BOOTSTRAP_PATH
        from greia_platform.boot_health import (
            BootHealthCredentialVault,
            BootHealthError,
            BootHealthyProtocol,
            FakeActualBootIdentity,
            ActualBootIdentity,
            IntroEvidence,
        )

        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            self._stage_and_arm(rig)
            self.assertEqual(rig.grub.simulate_reboot(), "B")
            record = rig.record()
            coordinator = BootTransactionCoordinator.resume(
                journal_dir=rig.backend.journal_dir,
                backend=rig.grub,
                candidate_artifacts=BootArtifactSet.from_finalization(
                    receipt=_receipt(slot="B", release_id=_R9_ID, sequence=_R9_SEQ),
                    record=record,
                ),
                accepted_artifacts=BootArtifactSet.from_finalization(
                    receipt=_receipt(slot="A", release_id=_R8_ID, sequence=_R8_SEQ),
                    record=record,
                ),
            )
            observed, _ = coordinator.observe_boot()
            self.assertEqual(observed, "B")
            vault = BootHealthCredentialVault(rig.root / "health-vault")
            protocol = BootHealthyProtocol(
                coordinator=coordinator,
                candidate_root_partuuid=_UUID_B,
                candidate_release_id=_R9_ID,
                candidate_release_sequence=_R9_SEQ,
                vault=vault,
                observer=FakeActualBootIdentity(
                    ActualBootIdentity(
                        booted_slot="B",
                        root_partuuid=_UUID_A,  # wrong root: accepted slot's PARTUUID
                        release_id=_R9_ID,
                        release_sequence=_R9_SEQ,
                    )
                ),
                trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            credential = protocol.provision_for_boot_attempt(
                boot_attempt="attempt-x8-wrongroot", peer_uid=0
            )
            with self.assertRaises(BootHealthError):
                protocol.confirm(
                    token=credential.token,
                    boot_attempt="attempt-x8-wrongroot",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=0,
                    intro=IntroEvidence(
                        first_frame_visible=True,
                        intro_completed=True,
                        lifecycle_state="interactive_ready",
                        untrusted_activity_launched=False,
                    ),
                )
            # No commit happened: the persistent default never moved.
            self.assertEqual(rig.grub.inspect().default_slot, "A")
            # The machine falls back to the accepted slot on next boot.
            rig.grub.reconcile("A")
            _, confirmed = rig.op("CONFIRM_BOOT_HEALTH")
            self.assertFalse(confirmed["detail"]["confirmed"])
            self.assertEqual(confirmed["detail"]["state"], "rolled_back")
            self._assert_rolled_back(rig)

    def test_userspace_crash_before_health_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            self._stage_and_arm(rig)
            # The candidate boots, then userspace crashes before any health
            # evidence exists: no confirm ever runs on this boot.
            self.assertEqual(rig.grub.simulate_reboot(), "B")
            # Crash: fresh objects on the same durable files (reboot path).
            grub2 = GrubEnvBackend.attach(rig.grub.state_dir)
            backend2 = SlotBackedSystemUpdateBackend(
                rig.state_dir,
                layout_record_path=rig.layout_path,
                seams=rig.seams.seams(),
                boot_backend=grub2,
            )
            authority2 = SystemUpdateServiceAuthority(
                rig.state_dir, rig.key_dir, _identity(), backend2
            )
            # Watchdog reboots into the persistent default (one-shot spent).
            self.assertEqual(grub2.simulate_reboot(), "A")
            outcome = authority2.confirm_boot_health()
            self.assertFalse(outcome["confirmed"])
            self.assertEqual(outcome["state"], "rolled_back")
            self._assert_rolled_back(rig)

    def test_power_loss_while_arming_recovers_to_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            rig.receive("r9")
            rig.op("STAGE_CURRENT_CANDIDATE")
            # Torn arm: the grubenv one-shot persisted, the journal record
            # did not (crash between the two writes of backend.arm).
            rig.grub.arm_one_shot("B")
            self.assertEqual(rig.grub.inspect().default_slot, "A")
            journal = BootTransactionJournal.load(rig.backend.journal_dir)
            self.assertEqual(journal.state, BootTransactionState.UPDATE_STAGED)
            # Recovery: fresh objects, the reboot consumes the torn one-shot.
            grub2 = GrubEnvBackend.attach(rig.grub.state_dir)
            backend2 = SlotBackedSystemUpdateBackend(
                rig.state_dir,
                layout_record_path=rig.layout_path,
                seams=rig.seams.seams(),
                boot_backend=grub2,
            )
            authority2 = SystemUpdateServiceAuthority(
                rig.state_dir, rig.key_dir, _identity(), backend2
            )
            self.assertEqual(grub2.simulate_reboot(), "B")
            outcome = authority2.confirm_boot_health()
            self.assertTrue(outcome["confirmed"])
            self.assertEqual(outcome["state"], "accepted")
            self.assertEqual(grub2.inspect().default_slot, "B")
            self.assertEqual(rig.record().accepted_slot, "B")
            self.assertEqual(read_accepted_sequence(rig.state_dir), _R9_SEQ)
            rig.assert_persist_intact()

    def test_power_loss_during_commit_recovers_to_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            self._stage_and_arm(rig)
            self.assertEqual(rig.grub.simulate_reboot(), "B")
            # Torn commit: journal folded the candidate boot and the backend
            # default flipped, then power died before the sequence file,
            # the ACCEPTED record and the layout advancement.
            journal = BootTransactionJournal.load(rig.backend.journal_dir)
            decision = journal.reconcile("B")
            self.assertIsNotNone(decision.transition)
            assert decision.transition is not None
            journal.record(decision.transition, decision.explanation)
            rig.grub.commit_accepted("B")
            self.assertEqual(rig.grub.inspect().default_slot, "B")
            stale = BootTransactionJournal.load(rig.backend.journal_dir)
            self.assertEqual(stale.state, BootTransactionState.CANDIDATE_BOOTING)
            self.assertEqual(rig.record().accepted_slot, "A")
            self.assertEqual(read_accepted_sequence(rig.state_dir), _R8_SEQ)
            # Recovery: re-attached confirm re-observes the candidate boot;
            # the backend commit is idempotent, so acceptance converges.
            grub2 = GrubEnvBackend.attach(rig.grub.state_dir)
            backend2 = SlotBackedSystemUpdateBackend(
                rig.state_dir,
                layout_record_path=rig.layout_path,
                seams=rig.seams.seams(),
                boot_backend=grub2,
            )
            authority2 = SystemUpdateServiceAuthority(
                rig.state_dir, rig.key_dir, _identity(), backend2
            )
            outcome = authority2.confirm_boot_health()
            self.assertTrue(outcome["confirmed"])
            self.assertEqual(outcome["state"], "accepted")
            self.assertEqual(outcome["booted_slot"], "B")
            self.assertEqual(grub2.inspect().default_slot, "B")
            self.assertEqual(read_accepted_sequence(rig.state_dir), _R9_SEQ)
            record = rig.record()
            self.assertEqual(record.accepted_slot, "B")
            self.assertEqual(record.accepted_release_sequence, _R9_SEQ)
            rig.assert_persist_intact()


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is required for trust tests")
class UpdatePreflightOrderingTests(unittest.TestCase):
    """Every preflight refuses before any inactive-slot write."""

    def _rig(self, root: Path) -> _Rig:
        rig = _Rig(root)
        rig.build_release("r9", release_id=_R9_ID, sequence=_R9_SEQ, size=200 * 1024)
        return rig

    def _assert_no_slot_contact(self, rig: _Rig) -> None:
        self.assertNotIn("store:system-a", rig.seams.contacts)
        self.assertNotIn("store:system-b", rig.seams.contacts)
        self.assertEqual(list((rig.seams.slots_dir).glob("slot-*.img")), [])

    def test_tampered_bundle_never_reaches_the_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            rig.receive("r9")
            bundle_path = Path(
                json.loads(
                    (rig.state_dir / "system-updates" / "status.json").read_text(
                        encoding="utf-8"
                    )
                )["bundle_path"]
            )
            with zipfile.ZipFile(bundle_path, "a") as archive:
                archive.writestr("attacker-note.txt", b"tamper")
            with self.assertRaises(SystemUpdateError):
                rig.op("STAGE_CURRENT_CANDIDATE")
            self._assert_no_slot_contact(rig)

    def test_untrusted_signer_never_reaches_the_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            (rig.key_dir / f"{_SIGNER}.pem").unlink()
            rig.receive("r9")
            with self.assertRaises(SystemUpdateError):
                rig.op("STAGE_CURRENT_CANDIDATE")
            self._assert_no_slot_contact(rig)

    def test_foreign_profile_never_reaches_the_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            rig.build_release("other", release_id="greia-9.9.9", sequence=99, size=200 * 1024)
            identity = SystemIdentity("0.16.0", "developer-vm", _ARCH, _PROFILE)
            service = SystemUpdateService(
                rig.state_dir, rig.key_dir, identity, rig.backend
            )
            with self.assertRaises(SystemUpdateError):
                service.stage(rig.releases["other"])
            self._assert_no_slot_contact(rig)

    def test_rollback_sequence_never_reaches_the_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            rig.build_release("old", release_id="greia-0.15.0", sequence=7, size=200 * 1024)
            service = SystemUpdateService(
                rig.state_dir,
                rig.key_dir,
                _identity(),
                rig.backend,
                accepted_sequence=_R8_SEQ,
            )
            with self.assertRaises(SystemUpdateError):
                service.stage(rig.releases["old"])
            self._assert_no_slot_contact(rig)

    def test_contract_mismatch_never_reaches_the_slot(self) -> None:
        from greia_platform.system_updates import build_persistent_state_contract_bytes

        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            rig.receive("r9")
            contacts_before = list(rig.seams.contacts)
            (rig.persist_root / "greia" / "persistent-state-contract.json").write_bytes(
                build_persistent_state_contract_bytes(
                    namespaces=("layout-authority", "child-profiles")
                )
            )
            with self.assertRaises(SystemUpdateError):
                rig.op("STAGE_CURRENT_CANDIDATE")
            self.assertNotIn("store:system-a", rig.seams.contacts)
            self.assertNotIn("store:system-b", rig.seams.contacts)
            self.assertEqual(list(rig.seams.slots_dir.glob("slot-*.img")), [])
            self.assertIn("contract", rig.seams.contacts)
            self.assertEqual(rig.seams.contacts[: len(contacts_before)], contacts_before)

    def test_missing_contract_seam_reports_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            rig.receive("r9")
            backend = SlotBackedSystemUpdateBackend(
                rig.state_dir,
                layout_record_path=rig.layout_path,
                seams=UpdateSlotSeams(
                    slot_store_factory=rig.seams.slot_store_factory,
                    filesystem_factory=rig.seams.filesystem_factory,
                    package_installer_factory=rig.seams.package_installer_factory,
                    inventory_factory=rig.seams.inventory_factory,
                    support_set_factory=rig.seams.support_set_factory,
                ),
                boot_backend=rig.grub,
            )
            service = SystemUpdateService(
                rig.state_dir, rig.key_dir, _identity(), backend
            )
            with self.assertRaises(UpdateBackendUnavailable):
                service.stage(rig.releases["r9"])

    def test_unsigned_bundle_bytes_never_reach_the_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = self._rig(Path(directory))
            payload = _payload(64 * 1024, b"x8-unsigned:")
            bundle = rig.root / "unsigned.greiaupdate"
            manifest = UpdateManifest(
                schema_version=SCHEMA_VERSION,
                release_id="greia-0.17.0",
                version="0.17.0",
                release_sequence=_R9_SEQ,
                platform_family=_FAMILY,
                architecture=_ARCH,
                profile=_PROFILE,
                signer=_SIGNER,
                payload_sha256=hashlib.sha256(payload).hexdigest(),
                payload_size=len(payload),
                payload_filesystem_bytes=len(payload),
                payload_minimum_slot_bytes=len(payload),
                hardware_support_name=HARDWARE_SUPPORT_NAME,
                hardware_support_schema_version=1,
                hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
                hardware_support_size=len(_HW_BYTES),
                persistent_contract_schema_version=1,
                persistent_contract_sha256=hashlib.sha256(_CONTRACT_BYTES).hexdigest(),
                persistent_contract_size=len(_CONTRACT_BYTES),
                release_notes="Unsigned X8-UPDATE probe.",
            )
            signature = SignatureEnvelope(
                schema_version=SCHEMA_VERSION,
                algorithm="ed25519",
                signer=manifest.signer,
                signature=b"x" * 64,
            )
            with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
                archive.writestr(SIGNATURE_NAME, signature.as_json_bytes())
                archive.writestr(PAYLOAD_NAME, payload)
                archive.writestr(HARDWARE_SUPPORT_NAME, _HW_BYTES)
                archive.writestr(PERSISTENT_CONTRACT_NAME, _CONTRACT_BYTES)
            with self.assertRaises(SystemUpdateError):
                rig.authority.service.stage(bundle)
            self._assert_no_slot_contact(rig)


class StreamingAndCapacityTests(unittest.TestCase):
    """Bounded streaming stage: chunked reads, no second payload copy."""

    def test_writer_streams_in_bounded_chunks(self) -> None:
        from greia_platform.slot_writer import SLOT_WRITE_CHUNK_BYTES

        class MeteredSource:
            def __init__(self, data: bytes) -> None:
                self._data = data
                self._offset = 0
                self.max_read = 0
                self.reads = 0

            def read(self, size: int) -> bytes:
                self.reads += 1
                self.max_read = max(self.max_read, size)
                chunk = self._data[self._offset : self._offset + size]
                self._offset += len(chunk)
                return chunk

        class MemStore:
            """Sparse in-memory slot store: no giant allocation."""

            def __init__(self, capacity: int) -> None:
                self._chunks: dict[int, bytes] = {}
                self._capacity = capacity
                self.max_write = 0
                self.max_read = 0
                self.writes = 0

            @property
            def capacity_bytes(self) -> int:
                return self._capacity

            def write_at(self, offset: int, data: bytes) -> None:
                self.writes += 1
                self.max_write = max(self.max_write, len(data))
                self._chunks[offset] = bytes(data)

            def read_at(self, offset: int, length: int) -> bytes:
                self.max_read = max(self.max_read, length)
                assembled = bytearray()
                cursor = offset
                remaining = length
                while remaining > 0:
                    chunk = self._chunks.get(cursor)
                    if chunk is None:
                        raise AssertionError("readback of an unwritten range")
                    take = min(len(chunk), remaining)
                    assembled += chunk[:take]
                    cursor += take
                    remaining -= take
                return bytes(assembled)

            def flush(self) -> None:
                pass

            def close(self) -> None:
                pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = InstalledLayoutRecord.from_dict(_record_dict())
            destination = DestinationSlot.resolve_from_layout(record, "B")
            payload = _payload(200 * 1024, b"x8-stream:")
            member = VerifiedReleaseMember(
                release_id=_R9_ID,
                release_sequence=_R9_SEQ,
                payload_sha256=hashlib.sha256(payload).hexdigest(),
                payload_size=len(payload),
                minimum_slot_bytes=len(payload),
                hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
                hardware_support_size=len(_HW_BYTES),
            )
            source = MeteredSource(payload)
            store = MemStore(_SLOT_BYTES)
            SlotWriter().write(
                member=member,
                destination=destination,
                source=source,  # type: ignore[arg-type]
                storage=store,  # type: ignore[arg-type]
                support_installed_bytes=0,
            )
            self.assertLessEqual(source.max_read, SLOT_WRITE_CHUNK_BYTES)
            self.assertLessEqual(store.max_write, SLOT_WRITE_CHUNK_BYTES)
            self.assertLessEqual(store.max_read, SLOT_WRITE_CHUNK_BYTES)
            self.assertGreater(source.reads, 1)
            self.assertGreater(store.writes, 1)

    def test_capacity_preflight_refuses_before_any_write(self) -> None:
        class MemStore:
            def __init__(self, capacity: int) -> None:
                self._capacity = capacity
                self.writes = 0

            @property
            def capacity_bytes(self) -> int:
                return self._capacity

            def write_at(self, offset: int, data: bytes) -> None:
                self.writes += 1

            def read_at(self, offset: int, length: int) -> bytes:
                raise AssertionError("no readback after a refused write")

            def flush(self) -> None:
                pass

            def close(self) -> None:
                pass

        import io

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = InstalledLayoutRecord.from_dict(_record_dict())
            destination = DestinationSlot.resolve_from_layout(record, "B")
            small = _replace(destination, slot_capacity_bytes=1024 * 1024)
            payload = _payload(64 * 1024, b"x8-capacity:")
            member = VerifiedReleaseMember(
                release_id=_R9_ID,
                release_sequence=_R9_SEQ,
                payload_sha256=hashlib.sha256(payload).hexdigest(),
                payload_size=len(payload),
                minimum_slot_bytes=2 * 1024 * 1024,
                hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
                hardware_support_size=len(_HW_BYTES),
            )
            store = MemStore(1024 * 1024)
            with self.assertRaises(SlotWriteError):
                SlotWriter().write(
                    member=member,
                    destination=small,
                    source=io.BytesIO(payload),  # type: ignore[arg-type]
                    storage=store,  # type: ignore[arg-type]
                    support_installed_bytes=0,
                )
            self.assertEqual(store.writes, 0)

    @unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is required for trust tests")
    def test_stage_adds_no_second_payload_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rig = _Rig(root)
            rig.build_release("r9", release_id=_R9_ID, sequence=_R9_SEQ, size=220 * 1024)
            bundle_size = rig.releases["r9"].stat().st_size
            rig.receive("r9")

            def inventory(base: Path) -> dict[str, int]:
                found: dict[str, int] = {}
                for path in sorted(base.rglob("*")):
                    if path.is_file():
                        found[str(path.relative_to(base))] = path.stat().st_size
                return found

            before = inventory(rig.state_dir)
            rig.op("STAGE_CURRENT_CANDIDATE")
            after = inventory(rig.state_dir)
            added = {name for name in after if name not in before}
            # Only the shared journal appears beside the retained bundle:
            # the payload streams from the inbox bytes, never via a second
            # payload-sized temporary.
            self.assertEqual(added, {"system-updates/journal/boot-journal.json"})
            payload_scale = [
                name for name, size in after.items() if size >= bundle_size
            ]
            self.assertEqual(len(payload_scale), 1)
            self.assertTrue(payload_scale[0].endswith(".greiaupdate"))


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is required for trust tests")
class PersistContractEnduranceTests(unittest.TestCase):
    """Shared PERSIST state stays bound and readable across update/rollback."""

    def test_contract_stays_bound_to_old_and_new_releases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rig = _Rig(root)
            rig.build_release("r8", release_id=_R8_ID, sequence=_R8_SEQ, size=200 * 1024)
            rig.build_release("r9", release_id=_R9_ID, sequence=_R9_SEQ, size=220 * 1024)
            rig.build_release("r10", release_id=_R10_ID, sequence=_R10_SEQ, size=240 * 1024)
            installed = (
                rig.persist_root / "greia" / "persistent-state-contract.json"
            ).read_bytes()
            for name in ("r8", "r9", "r10"):
                manifest = inspect_update_bundle(rig.releases[name]).manifest
                self.assertEqual(
                    assert_persistent_contract_accepted(installed, manifest),
                    manifest.release_sequence,
                )
            # After a full A->B acceptance the previously accepted slot's
            # release still binds the same shared contract bytes.
            rig.receive("r9")
            rig.op("STAGE_CURRENT_CANDIDATE")
            rig.op("ARM_CURRENT_CANDIDATE")
            rig.grub.simulate_reboot()
            rig.op("CONFIRM_BOOT_HEALTH")
            live = (
                rig.persist_root / "greia" / "persistent-state-contract.json"
            ).read_bytes()
            self.assertEqual(live, installed)
            for name in ("r8", "r9", "r10"):
                manifest = inspect_update_bundle(rig.releases[name]).manifest
                self.assertEqual(
                    assert_persistent_contract_accepted(live, manifest),
                    manifest.release_sequence,
                )
            rig.assert_persist_intact()


class LayoutAdvancementTests(unittest.TestCase):
    """Direct unit proof for the layout-authority advancement helper."""

    def test_advance_flips_accepted_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_path = _write_layout(root)
            advanced = advance_layout_authority_for_acceptance(
                layout_path,
                candidate_slot="B",
                accepted_slot="A",
                release_id=_R9_ID,
                release_sequence=_R9_SEQ,
            )
            self.assertEqual(advanced.accepted_slot, "B")
            self.assertEqual(advanced.boot_control.active_slot, "B")
            self.assertEqual(advanced.accepted_release_id, _R9_ID)
            self.assertEqual(advanced.accepted_release_sequence, _R9_SEQ)
            reloaded = load_installed_layout_record(layout_path)
            assert reloaded is not None
            self.assertEqual(reloaded.as_dict(), advanced.as_dict())
            # Idempotent: the converged record returns unchanged.
            again = advance_layout_authority_for_acceptance(
                layout_path,
                candidate_slot="B",
                accepted_slot="A",
                release_id=_R9_ID,
                release_sequence=_R9_SEQ,
            )
            self.assertEqual(again.as_dict(), advanced.as_dict())

    def test_advance_refuses_unexpected_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_path = _write_layout(root)
            # The journal's accepted slot (B here) disagrees with the record
            # (still A): the authority moved under the transaction.
            with self.assertRaises(SystemUpdateError):
                advance_layout_authority_for_acceptance(
                    layout_path,
                    candidate_slot="B",
                    accepted_slot="B",
                    release_id=_R9_ID,
                    release_sequence=_R9_SEQ,
                )
            # Same slot with a different release bound is also refused.
            converged_path = _write_layout(
                root,
                "converged-layout.json",
                accepted_slot="B",
                boot_control={"active_slot": "B", "kind": "grub-env-v1"},
                accepted_release_id=_R9_ID,
                accepted_release_sequence=_R9_SEQ,
            )
            with self.assertRaises(SystemUpdateError):
                advance_layout_authority_for_acceptance(
                    converged_path,
                    candidate_slot="B",
                    accepted_slot="A",
                    release_id=_R10_ID,
                    release_sequence=_R10_SEQ,
                )
            # Candidate equal to accepted is never an advancement.
            with self.assertRaises(SystemUpdateError):
                advance_layout_authority_for_acceptance(
                    layout_path,
                    candidate_slot="A",
                    accepted_slot="A",
                    release_id=_R9_ID,
                    release_sequence=_R9_SEQ,
                )
            # Single-root layouts carry no second slot to advance to.
            single_path = _write_layout(
                root,
                "single-layout.json",
                layout_id="bios-single-ext4",
                boot_backend="none-v1",
                boot_control={"active_slot": None, "kind": "none-v1"},
                accepted_slot=None,
                accepted_release_id="greia-0.16.0",
                accepted_release_sequence=_R8_SEQ,
                system_b=None,
            )
            with self.assertRaises(SystemUpdateError):
                advance_layout_authority_for_acceptance(
                    single_path,
                    candidate_slot="B",
                    accepted_slot="A",
                    release_id=_R9_ID,
                    release_sequence=_R9_SEQ,
                )
            untouched = load_installed_layout_record(layout_path)
            assert untouched is not None
            self.assertEqual(untouched.accepted_slot, "A")


if __name__ == "__main__":
    unittest.main()
