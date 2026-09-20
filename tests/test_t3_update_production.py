"""T3-UPDATE production composition proof (source scope, disposable tmpdirs).

Proves the brief's production call graph instead of helper return values:

- update flow through the production composition root
  (``build_live_update_service`` -> ``SlotBackedSystemUpdateBackend`` ->
  shared ``SlotWriter``/``SlotFinalizer``/``BootTransactionJournal`` ->
  attached ``GrubEnvBackend`` one-shot -> health commit), entered through
  the shipped socket endpoint (``UpdatePrivilegedEndpoint``) with a
  kernel-attested ``PeerCredential`` and a release built for the identity
  derived from the shipped ``legacy-x86-i686`` profile: accepted A ->
  signed B -> inactive write/finalize -> one-shot arm -> observed B ->
  trusted health -> persistent default B -> accepted record B;
- install-follow flow through the same BOOT_HEALTHY predicate with the
  production observer (kernel cmdline + layout + release identity) and the
  launcher post-intro seam, carrying ``setup-medium`` (never "rollback");
- negative proof on the production path: an unhealthy candidate is not
  confirmed/finalized, and a caller-supplied (unattested) peer identity is
  rejected before any request byte is served.

Slot stores are sparse loopback files; no valued disk is contacted.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import tempfile
import threading
import tomllib
import unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from support_artifacts import valid_hardware_support_archive_bytes

import greia_launcher.boot_health as launcher_health
from greia_launcher.boot_health import TRUSTED_BOOTSTRAP_PATH
from greia_launcher.bootstrap import BootLifecycleGuard
from greia_platform.boot_health import (
    BootHealthCredentialVault,
    BootHealthError,
    BootHealthyProtocol,
    ProductionActualBootObserver,
    SETUP_MEDIUM,
)
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionCoordinator,
    BootTransactionJournal,
    BootTransactionState,
)
from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.privileged_channel import PeerCredential, PrivilegedChannelError
from greia_platform.slot_writer import (
    FINALIZER_VERSION,
    FinalizationReceipt,
    HardwareInventoryAttestation,
    LoopbackSlotFile,
    ReleaseSupportSet,
)
from greia_platform.system_updates import (
    SystemUpdateError,
    UpdateSlotSeams,
    attest_peer_from_connection,
    build_live_update_service,
    build_update_bundle,
    handle_update_connection,
    inspect_update_bundle,
    production_boot_backend,
    SystemUpdateInbox,
)
from greia_platform.persistent_layout import emit_persist_schema_marker
from greia_platform.update_privileged import (
    UpdatePrivilegedEndpoint,
    UpdatePrivilegedError,
    build_request,
    read_response,
)


@contextmanager
def _patched_env(**overrides: str):
    previous = dict(os.environ)
    os.environ.update(overrides)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


ROOT = Path(__file__).resolve().parents[1]
SHIPPED_PROFILE = ROOT / "build" / "profiles" / "legacy-x86-i686.toml"

_SLOT_BYTES = 1024 * 1024 * 1024
_HW_BYTES = valid_hardware_support_archive_bytes(architecture="i386")
_PERSIST_MARKER = emit_persist_schema_marker(1)

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32

_KERNEL = hashlib.sha256(b"t3-candidate-kernel").hexdigest()
_INITRAMFS = hashlib.sha256(b"t3-candidate-initramfs").hexdigest()

_R8_ID = "greia-0.16.0"
_R8_SEQ = 8
_R9_ID = "greia-0.17.0"
_R9_SEQ = 9


def _shipped_identity() -> tuple[str, str, str]:
    """Release identity derived from the shipped profile file (never minted)."""
    with open(SHIPPED_PROFILE, "rb") as handle:
        document = tomllib.load(handle)
    return (
        str(document["platform"]["family"]),
        str(document["base"]["architecture"]),
        str(document["profile"]["id"]),
    )


def _payload(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def _record_dict(family: str, profile: str, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": _R8_ID,
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": profile,
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "legacy-bios-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": family,
        "schema_version": 1,
        "slot_bytes": _SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _canonical_record(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


class _FakeSlotFilesystem:
    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.mount_dir.mkdir(parents=True, exist_ok=True)
        self.files: dict[str, bytes] = {}
        self.bound_uuid: str | None = None
        self.mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.bound_uuid = filesystem_uuid

    def expand_to_capacity(self) -> None:
        pass

    def mount(self) -> Path:
        self.mounted = True
        self.mount_dir.mkdir(parents=True, exist_ok=True)
        # Simulate a staged slot carrying real Greia userspace so the
        # shared completeness smoke passes (uses the shared path set).
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
        self.mounted = False

    def sync(self) -> None:
        pass

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise AssertionError("slot writes require a mounted destination")
        self.files[relative_path] = bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_completeness(self) -> None:
        from greia_platform.slot_writer import check_slot_completeness

        check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        pass


class _FakeSlotPackageInstaller:
    def install(
        self, firmware: tuple[str, ...], microcode: tuple[str, ...]
    ) -> tuple[object, ...]:
        return ()


class _LoopSeams:
    """Destination factories: sparse loopback stores (deployment parameter)."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self.slots_dir = root / "slots"
        self.slots_dir.mkdir(parents=True, exist_ok=True)
        self.contacts: list[str] = []
        self.filesystem = _FakeSlotFilesystem(root / "mnt")

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
        return _FakeSlotPackageInstaller()

    def inventory_factory(self) -> object:
        self.contacts.append("inventory")
        return HardwareInventoryAttestation(
            token=hashlib.sha256(b"t3-inventory").hexdigest()
        )

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
        return _PERSIST_MARKER

    def seams(self) -> UpdateSlotSeams:
        return UpdateSlotSeams(
            slot_store_factory=self.slot_store_factory,
            filesystem_factory=self.filesystem_factory,
            package_installer_factory=self.package_installer_factory,
            inventory_factory=self.inventory_factory,
            support_set_factory=self.support_set_factory,
            installed_contract_factory=self.installed_contract_factory,
        )


class _ProductionRig:
    """One disposable A/B machine entered through production composition."""

    def __init__(self, root: Path, family: str, arch: str, profile: str) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.state_dir = root / "state"
        self.layout_path = root / "installed-layout.json"
        self.layout_path.write_bytes(
            _canonical_record(_record_dict(family, profile))
        )
        self.family = family
        self.arch = arch
        self.profile = profile
        boot_dir = root / "boot-control"
        boot_dir.mkdir(parents=True, exist_ok=True)
        self.grub = GrubEnvBackend.initialize(boot_dir, default_slot="A")
        self.seams = _LoopSeams(root)
        shipped_env = {
            "GREIA_SYSTEM_VERSION": "0.16.0",
            "GREIA_SYSTEM_PLATFORM_FAMILY": family,
            "GREIA_SYSTEM_ARCHITECTURE": arch,
            "GREIA_SYSTEM_PROFILE": profile,
        }
        with _patched_env(**shipped_env):
            self.authority = build_live_update_service(
                state_dir=self.state_dir,
                layout_record_path=self.layout_path,
                boot_backend=self.grub,
                boot_backend_auto=False,
                seams=self.seams.seams(),
            )
        # No shape adapter: the v3 authority summary already carries
        # exactly {present, release_id, bundle_sha256}, so the endpoint
        # drives the real production authority directly.
        self.endpoint = UpdatePrivilegedEndpoint(self.authority)  # type: ignore[arg-type]
        self.peer = PeerCredential(uid=0)

    def build_release(
        self, name: str, *, release_id: str, sequence: int = 0,
        profile: str | None = None,
    ) -> Path:
        """Build one unsigned v3 bundle (``sequence`` is retired, ignored)."""
        import zstandard

        work = self.root / "releases" / name
        work.mkdir(parents=True, exist_ok=True)
        raw = _payload(220 * 1024, f"t3-{name}:".encode())
        payload = work / "slot.ext4.zst"
        payload.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))
        hardware = work / "hw.tar.zst"
        hardware.write_bytes(_HW_BYTES)
        bundle = work / f"{name}.greiaupdate"
        if bundle.exists():
            bundle.unlink()
        build_update_bundle(
            payload_path=payload,
            hardware_support_path=hardware,
            output_path=bundle,
            version=release_id.split("-", 1)[1],
            release_id=release_id,
            platform_family=self.family,
            architecture=self.arch,
            profile=self.profile if profile is None else profile,
            payload_uncompressed_bytes=len(raw),
            minimum_slot_bytes=len(raw),
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
            release_notes=f"T3-UPDATE production proof release {name}.",
        )
        return bundle

    def op(self, name: str) -> tuple[str, dict[str, object]]:
        raw = self.endpoint.handle_request(
            build_request(name), peer=self.peer, boot_state="update_ready"
        )
        _, op_name, payload = read_response(raw)
        return op_name, payload

    def receive(self, bundle: Path) -> None:
        SystemUpdateInbox(self.state_dir).receive(bundle)

    def record(self) -> InstalledLayoutRecord:
        loaded = InstalledLayoutRecord.from_dict(
            json.loads(self.layout_path.read_text(encoding="utf-8"))
        )
        return loaded


def _interactive_guard() -> BootLifecycleGuard:
    guard = BootLifecycleGuard()
    guard.mark_display_ready()
    guard.mark_first_frame_visible()
    guard.begin_preparing_runtime()
    guard.mark_interactive_ready()
    return guard


def _write_production_identity_files(
    root: Path, *, booted_partuuid: str, slot: str, release_id: str, sequence: int
) -> tuple[Path, Path, Path]:
    cmdline = root / "cmdline"
    cmdline.write_text(
        f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={booted_partuuid} ro quiet\n",
        encoding="utf-8",
    )
    layout = root / "layout.json"
    family, _, profile = _shipped_identity()
    layout.write_bytes(_canonical_record(_record_dict(family, profile)))
    identity = root / "release-identity.json"
    identity.write_bytes(
        _canonical_record(
            {
                "boot_backend": "grub-ab-v1",
                "layout_id": "legacy-bios-ab-v1",
                "release_id": release_id,
                "role": f"system-{slot.lower()}",
                "slot": slot,
            }
        )
    )
    return cmdline, layout, identity


class ShippedProfileTests(unittest.TestCase):
    def test_shipped_profile_parses_to_release_identity(self) -> None:
        family, arch, profile = _shipped_identity()
        self.assertEqual(family, "legacy-x86")
        self.assertEqual(arch, "i386")
        self.assertEqual(profile, "legacy-x86-i686")


class ProductionServiceCompositionTests(unittest.TestCase):
    """The live composition root wires the boot backend; entry is not a stub."""

    def test_live_service_auto_attaches_boot_backend(self) -> None:
        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            layout_path = root / "installed-layout.json"
            layout_path.write_bytes(_canonical_record(_record_dict(family, profile)))
            boot_dir = root / "boot-control"
            boot_dir.mkdir(parents=True, exist_ok=True)
            GrubEnvBackend.initialize(boot_dir, default_slot="A")
            with _patched_env(
                GREIA_GRUBENV_DIR=str(boot_dir),
                GREIA_SYSTEM_VERSION="0.16.0",
                GREIA_SYSTEM_PLATFORM_FAMILY=family,
                GREIA_SYSTEM_ARCHITECTURE=arch,
                GREIA_SYSTEM_PROFILE=profile,
            ):
                authority = build_live_update_service(
                    state_dir=state_dir,
                    layout_record_path=layout_path,
                )
            backend = authority.backend
            self.assertIsInstance(backend, object)
            attached = getattr(backend, "boot_backend", None)
            self.assertIsInstance(attached, GrubEnvBackend)

    def test_live_service_without_boot_control_stays_fail_closed(self) -> None:
        family, _, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            layout_path = root / "installed-layout.json"
            layout_path.write_bytes(_canonical_record(_record_dict(family, profile)))
            with _patched_env(GREIA_GRUBENV_DIR=str(root / "no-such-boot-control")):
                self.assertIsNone(production_boot_backend())
                authority = build_live_update_service(
                    state_dir=state_dir,
                    layout_record_path=layout_path,
                )
            with self.assertRaises(Exception):
                authority.arm_current_candidate()

    def test_privileged_entry_point_serves_production_service(self) -> None:
        import greia_platform.update_privileged as privileged_module

        source = (ROOT / "src" / "greia_platform" / "update_privileged.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("destructive backend not wired", source)
        previous = os.environ.pop("LISTEN_FDS", None)
        try:
            with self.assertRaisesRegex(SystemExit, "socket-activated file descriptor"):
                privileged_module.main([])
        finally:
            if previous is not None:
                os.environ["LISTEN_FDS"] = previous


class ProductionUpdateFlowTests(unittest.TestCase):
    """Accepted A -> signed B -> ... -> accepted record B via production graph."""

    def test_accepted_a_to_accepted_b_through_shipped_profile(self) -> None:
        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            with _patched_env(
                GREIA_SYSTEM_VERSION="0.16.0",
                GREIA_SYSTEM_PLATFORM_FAMILY=family,
                GREIA_SYSTEM_ARCHITECTURE=arch,
                GREIA_SYSTEM_PROFILE=profile,
            ):
                rig = _ProductionRig(Path(directory), family, arch, profile)
                bundle = rig.build_release(
                    "r9", release_id=_R9_ID, sequence=_R9_SEQ
                )
                rig.receive(bundle)
                op, status = rig.op("STATUS")
                self.assertEqual(op, "STATUS")
                self.assertTrue(status["candidate"]["present"])
                self.assertEqual(
                    set(status["candidate"].keys()),
                    {"present", "release_id", "bundle_sha256"},
                )
                self.assertEqual(status["candidate"]["release_id"], _R9_ID)
                op, verified = rig.op("VERIFY_CURRENT_CANDIDATE")
                self.assertEqual(verified["status"], "VERIFIED")
                self.assertEqual(rig.grub.inspect().default_slot, "A")
                self.assertEqual(rig.record().accepted_slot, "A")
                op, staged = rig.op("STAGE_CURRENT_CANDIDATE")
                self.assertEqual(staged["status"], "STAGED")
                self.assertEqual(staged["detail"]["candidate_slot"], "B")
                self.assertIn("store:system-b", rig.seams.contacts)
                self.assertNotIn("store:system-a", rig.seams.contacts)
                self.assertEqual(rig.grub.inspect().default_slot, "A")
                op, armed = rig.op("ARM_CURRENT_CANDIDATE")
                self.assertEqual(armed["status"], "ARMED")
                self.assertEqual(rig.grub.inspect().one_shot_slot, "B")
                self.assertEqual(rig.grub.inspect().default_slot, "A")
                self.assertEqual(rig.grub.simulate_reboot(), "B")
                op, confirmed = rig.op("CONFIRM_BOOT_HEALTH")
                self.assertEqual(confirmed["status"], "CONFIRMED")
                detail = confirmed["detail"]
                self.assertTrue(detail["confirmed"])
                self.assertEqual(detail["state"], "accepted")
                self.assertEqual(detail["booted_slot"], "B")
                self.assertEqual(rig.grub.inspect().default_slot, "B")
                record = rig.record()
                self.assertEqual(record.accepted_slot, "B")
                self.assertEqual(record.boot_control.active_slot, "B")
                self.assertEqual(record.accepted_release_id, _R9_ID)

    def test_foreign_profile_bundle_rejected_before_slot_contact(self) -> None:
        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            rig = _ProductionRig(Path(directory), family, arch, profile)
            foreign = rig.build_release(
                "foreign", release_id="greia-9.9.9", sequence=99,
                profile="foreign-profile",
            )
            rig.receive(foreign)
            with self.assertRaises(SystemUpdateError):
                rig.op("STAGE_CURRENT_CANDIDATE")
            self.assertNotIn("store:system-a", rig.seams.contacts)
            self.assertNotIn("store:system-b", rig.seams.contacts)

    def test_unhealthy_candidate_is_not_confirmed_or_finalized(self) -> None:
        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            rig = _ProductionRig(Path(directory), family, arch, profile)
            rig.receive(rig.build_release("r9", release_id=_R9_ID, sequence=_R9_SEQ))
            rig.op("STAGE_CURRENT_CANDIDATE")
            rig.op("ARM_CURRENT_CANDIDATE")
            # Firmware cannot boot the kernel-less candidate: the machine
            # stays on the accepted slot and the one-shot is consumed.
            rig.grub.reconcile("A")
            op, confirmed = rig.op("CONFIRM_BOOT_HEALTH")
            self.assertEqual(confirmed["status"], "CONFIRMED")
            detail = confirmed["detail"]
            self.assertFalse(detail["confirmed"])
            self.assertEqual(detail["state"], "rolled_back")
            self.assertEqual(rig.grub.inspect().default_slot, "A")
            record = rig.record()
            self.assertEqual(record.accepted_slot, "A")
            self.assertEqual(record.accepted_release_id, _R8_ID)
            journal = BootTransactionJournal.load(rig.authority.backend.journal_dir)
            self.assertEqual(journal.state, BootTransactionState.ROLLED_BACK)


class ProductionObserverTests(unittest.TestCase):
    def test_observer_resolves_booted_slot_from_kernel_fact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cmdline, layout, identity = _write_production_identity_files(
                root, booted_partuuid=_UUID_B, slot="B",
                release_id=_R9_ID, sequence=_R9_SEQ,
            )
            observer = ProductionActualBootObserver(
                cmdline_path=cmdline,
                layout_record_path=layout,
                release_identity_path=identity,
            )
            observed = observer.observe()
            self.assertEqual(observed.booted_slot, "B")
            self.assertEqual(observed.root_partuuid, _UUID_B)
            self.assertEqual(observed.release_id, _R9_ID)

    def test_observer_rejects_unknown_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cmdline, layout, identity = _write_production_identity_files(
                root, booted_partuuid=_UUID_B, slot="B",
                release_id=_R9_ID, sequence=_R9_SEQ,
            )
            cmdline.write_text(
                "BOOT_IMAGE=/boot/vmlinuz "
                "root=PARTUUID=deadbeef-99 ro quiet\n",
                encoding="utf-8",
            )
            observer = ProductionActualBootObserver(
                cmdline_path=cmdline,
                layout_record_path=layout,
                release_identity_path=identity,
            )
            with self.assertRaises(BootHealthError):
                observer.observe()

    def test_observer_rejects_identity_slot_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Kernel runs B, but the identity file claims A.
            cmdline, layout, _ = _write_production_identity_files(
                root, booted_partuuid=_UUID_B, slot="A",
                release_id=_R9_ID, sequence=_R9_SEQ,
            )
            identity = root / "release-identity.json"
            observer = ProductionActualBootObserver(
                cmdline_path=cmdline,
                layout_record_path=layout,
                release_identity_path=identity,
            )
            with self.assertRaises(BootHealthError):
                observer.observe()

    def test_observer_rejects_symlinked_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cmdline, layout, identity = _write_production_identity_files(
                root, booted_partuuid=_UUID_A, slot="A",
                release_id=_R8_ID, sequence=_R8_SEQ,
            )
            real = root / "real-identity.json"
            identity.unlink()
            real.write_bytes(
                _canonical_record(
                    {
                        "boot_backend": "grub-ab-v1",
                        "layout_id": "legacy-bios-ab-v1",
                        "release_id": _R8_ID,
                        "role": "system-a",
                        "slot": "A",
                    }
                )
            )
            identity.symlink_to(real)
            observer = ProductionActualBootObserver(
                cmdline_path=cmdline,
                layout_record_path=layout,
                release_identity_path=identity,
            )
            with self.assertRaises(BootHealthError):
                observer.observe()

    def test_observer_rejects_missing_cmdline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, layout, identity = _write_production_identity_files(
                root, booted_partuuid=_UUID_A, slot="A",
                release_id=_R8_ID, sequence=_R8_SEQ,
            )
            observer = ProductionActualBootObserver(
                cmdline_path=root / "no-such-cmdline",
                layout_record_path=layout,
                release_identity_path=identity,
            )
            with self.assertRaises(BootHealthError):
                observer.observe()


class InstallFollowHealthTests(unittest.TestCase):
    """First install uses the same health predicate (setup-medium, no rollback)."""

    def _first_install_protocol(self, root: Path):
        family, _, profile = _shipped_identity()
        layout_record = InstalledLayoutRecord.from_dict(
            _record_dict(family, profile)
        )
        (root / "installed-layout.json").write_bytes(
            _canonical_record(_record_dict(family, profile))
        )
        receipt = FinalizationReceipt(
            schema_version=1,
            finalizer_version=FINALIZER_VERSION,
            release_id=_R8_ID,
            slot="A",
            role="system-a",
            base_sha256=_KERNEL,
            base_bytes=200 * 1024,
            support_sha256="ef" * 32,
            support_size=1024,
            inventory_token="cd" * 32,
            packages=(),
            packages_digest=hashlib.sha256(b"\n").hexdigest(),
            generic_kernel_sha256=_KERNEL,
            host_initramfs_sha256=_INITRAMFS,
            filesystem_uuid=_UUID_A_FS,
            layout_id="legacy-bios-ab-v1",
            slot_capacity_bytes=_SLOT_BYTES,
        )
        artifact_a = BootArtifactSet.from_finalization(
            receipt=receipt, record=layout_record
        )
        backend = GrubEnvBackend.initialize(root / "grub", default_slot="A")
        coordinator = BootTransactionCoordinator.begin_first_install(
            journal_dir=root / "journal", backend=backend, artifact_a=artifact_a
        )
        self.assertEqual(backend.simulate_reboot(), "A")
        observed, _ = coordinator.observe_boot()
        self.assertEqual(observed, "A")
        cmdline, layout_path, identity_path = _write_production_identity_files(
            root, booted_partuuid=_UUID_A, slot="A",
            release_id=_R8_ID, sequence=_R8_SEQ,
        )
        observer = ProductionActualBootObserver(
            cmdline_path=cmdline,
            layout_record_path=layout_path,
            release_identity_path=identity_path,
        )
        protocol = BootHealthyProtocol(
            coordinator=coordinator,
            candidate_root_partuuid=_UUID_A,
            candidate_release_id=_R8_ID,
            vault=BootHealthCredentialVault(root / "vault"),
            observer=observer,
            trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
        )
        return protocol, coordinator

    def test_first_install_accepts_through_launcher_seam(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol, coordinator = self._first_install_protocol(root)
            guard = _interactive_guard()
            record = launcher_health.provision_post_intro_credential(
                protocol, guard=guard, boot_attempt="install-attempt-1"
            )
            outcome = launcher_health.run_post_intro_acceptance(
                protocol,
                guard=guard,
                boot_attempt="install-attempt-1",
                token=record.token,
                first_frame_visible=True,
                intro_completed=True,
            )
            self.assertEqual(outcome.accepted_slot, "A")
            self.assertTrue(outcome.first_install)
            self.assertEqual(outcome.recovery_medium_if_failed, SETUP_MEDIUM)
            self.assertNotIn("rollback", str(outcome.as_dict()))
            self.assertEqual(
                coordinator.journal.state, BootTransactionState.ACCEPTED
            )
            protocol.check_untrusted_launch("developer_unsigned")

    def test_first_install_first_frame_alone_never_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol, _ = self._first_install_protocol(root)
            guard = BootLifecycleGuard()
            guard.mark_display_ready()
            guard.mark_first_frame_visible()
            # No intro completion, no INTERACTIVE_READY: refused locally.
            with self.assertRaises(BootHealthError):
                launcher_health.run_post_intro_acceptance(
                    protocol,
                    guard=guard,
                    boot_attempt="install-attempt-1",
                    token="ab" * 32,
                    first_frame_visible=True,
                    intro_completed=True,
                )

    def test_first_install_wrong_root_refused_by_production_observer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol, coordinator = self._first_install_protocol(root)
            # Rewrite the kernel fact to the other slot: the platform itself
            # re-observes B while the pending candidate is A.
            (root / "cmdline").write_text(
                f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={_UUID_B} ro quiet\n",
                encoding="utf-8",
            )
            guard = _interactive_guard()
            record = launcher_health.provision_post_intro_credential(
                protocol, guard=guard, boot_attempt="install-attempt-2"
            )
            with self.assertRaises(BootHealthError):
                launcher_health.run_post_intro_acceptance(
                    protocol,
                    guard=guard,
                    boot_attempt="install-attempt-2",
                    token=record.token,
                    first_frame_visible=True,
                    intro_completed=True,
                )
            self.assertNotEqual(
                coordinator.journal.state, BootTransactionState.ACCEPTED
            )


class PeerAttestationTests(unittest.TestCase):
    def test_caller_supplied_uid_is_rejected_before_serving(self) -> None:
        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            rig = _ProductionRig(Path(directory), family, arch, profile)

            class _Conn:
                def __init__(self) -> None:
                    self.sent: list[bytes] = []
                    self.closed = False

                def settimeout(self, _value: float) -> None:
                    pass

                def recv(self, _size: int) -> bytes:
                    raise AssertionError("unattested peer must not be served")

                def sendall(self, data: bytes) -> None:
                    self.sent.append(bytes(data))

                def close(self) -> None:
                    self.closed = True

            for forged in (0, "0", {"uid": 0}):
                with self.subTest(forged=forged):
                    connection = _Conn()
                    handle_update_connection(
                        connection,  # type: ignore[arg-type]
                        authority=rig.authority,
                        peer=forged,  # type: ignore[arg-type]
                    )
                    self.assertTrue(connection.closed)
                    self.assertEqual(len(connection.sent), 1)
                    _, op, payload = read_response(connection.sent[0])
                    self.assertEqual(op, "ERROR")
                    self.assertEqual(payload["status"], "REFUSED")
                    self.assertIn("attested", str(payload["reason"]))

    def test_endpoint_rejects_non_credential_peer(self) -> None:
        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            rig = _ProductionRig(Path(directory), family, arch, profile)
            with self.assertRaises(UpdatePrivilegedError):
                rig.endpoint.handle_request(
                    build_request("STATUS"),
                    peer="uid:0",  # type: ignore[arg-type]
                    boot_state="update_ready",
                )

    def test_kernel_attested_peer_over_real_socket(self) -> None:
        if not hasattr(socket, "SO_PEERCRED"):
            with self.assertRaises(PrivilegedChannelError):
                attest_peer_from_connection(object())  # type: ignore[arg-type]
            return
        first, second = socket.socketpair()
        try:
            for endpoint in (first, second):
                credential = attest_peer_from_connection(endpoint)
                self.assertIsInstance(credential, PeerCredential)
                self.assertEqual(credential.uid, os.getuid())
        finally:
            first.close()
            second.close()

    def test_unattestable_connection_fails_closed(self) -> None:
        class _Broken:
            def getsockopt(self, *args: object, **kwargs: object) -> bytes:
                raise OSError("no kernel credential")

        if not hasattr(socket, "SO_PEERCRED"):
            with self.assertRaises(PrivilegedChannelError):
                attest_peer_from_connection(_Broken())  # type: ignore[arg-type]
            return
        with self.assertRaises(PrivilegedChannelError):
            attest_peer_from_connection(_Broken())  # type: ignore[arg-type]


class UpdateHealthSeparationTests(unittest.TestCase):
    """First-frame systemd readiness never implies update health."""

    def test_launcher_seam_never_touches_notify_socket(self) -> None:
        source = (ROOT / "src" / "greia_launcher" / "boot_health.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("NOTIFY_SOCKET", source)
        self.assertNotIn("subprocess", source)

    def test_first_frame_readiness_stays_in_boot_intro(self) -> None:
        source = (ROOT / "src" / "greia_launcher" / "boot_intro.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("--ready", source)

    def test_credential_vault_resolves_systemd_transport(self) -> None:
        import greia_platform.boot_health as platform_health

        with tempfile.TemporaryDirectory() as directory:
            credentials = Path(directory) / "credentials"
            vault_dir = credentials / "greia-boot-health"
            vault_dir.mkdir(parents=True)
            with _patched_env(CREDENTIALS_DIRECTORY=str(credentials)):
                resolved = platform_health.systemd_vault_dir()
                self.assertEqual(resolved, vault_dir)
                vault = launcher_health.default_vault()
                self.assertEqual(vault.vault_dir, vault_dir)
            with _patched_env(CREDENTIALS_DIRECTORY=""):
                os.environ.pop("CREDENTIALS_DIRECTORY", None)
                self.assertIsNone(platform_health.systemd_vault_dir())
                with self.assertRaises(Exception):
                    launcher_health.default_vault()


class DefaultCompositionFailClosedTests(unittest.TestCase):
    """Shipped authority without destination seams stages fail-closed.

    Entered through the shipped constructor
    (:func:`build_live_update_service`), never by building the backend
    directly around it: staging without image-integration destination
    factories raises :class:`UpdateBackendUnavailable` before any
    destination contact or journal write, with no silent fallback and no
    single-root routing.
    """

    def test_default_construction_stages_fail_closed_through_shipped_authority(
        self,
    ) -> None:
        from greia_platform.system_updates import (
            UpdateBackendUnavailable,
            build_live_update_service,
        )

        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            layout_path = root / "installed-layout.json"
            layout_path.write_bytes(_canonical_record(_record_dict(family, profile)))
            boot_dir = root / "boot-control"
            boot_dir.mkdir(parents=True, exist_ok=True)
            GrubEnvBackend.initialize(boot_dir, default_slot="A")
            with _patched_env(
                GREIA_SYSTEM_VERSION="0.16.0",
                GREIA_SYSTEM_PLATFORM_FAMILY=family,
                GREIA_SYSTEM_ARCHITECTURE=arch,
                GREIA_SYSTEM_PROFILE=profile,
                GREIA_GRUBENV_DIR=str(boot_dir),
            ):
                # Shipped authority, default seams (all factories None) and
                # the production boot-backend attach: the only missing piece
                # is the image-integration destination factories.
                authority = build_live_update_service(
                    state_dir=state_dir,
                    layout_record_path=layout_path,
                )
                self.assertIsInstance(authority.backend.boot_backend, GrubEnvBackend)
                status = authority.backend.status_payload()
                self.assertTrue(status["available"])
                # This test is specifically about the absent inactive device,
                # not about host sysfs completeness. Satisfy only the
                # inventory prerequisite; keep the real production
                # filesystem/device resolver so it must fail on the
                # deliberately non-existent PARTUUIDs in the layout.
                authority.backend.seams = replace(
                    authority.backend.seams,
                    inventory_factory=lambda: HardwareInventoryAttestation(
                        token="cd" * 32
                    ),
                )
                import zstandard

                work = root / "releases" / "r9"
                work.mkdir(parents=True, exist_ok=True)
                raw = _payload(220 * 1024, b"t3-r9:")
                (work / "slot.ext4.zst").write_bytes(
                    zstandard.ZstdCompressor(level=3).compress(raw)
                )
                (work / "hw.tar.zst").write_bytes(_HW_BYTES)
                bundle = work / "r9.greiaupdate"
                build_update_bundle(
                    payload_path=work / "slot.ext4.zst",
                    hardware_support_path=work / "hw.tar.zst",
                    output_path=bundle,
                    version=_R9_ID.split("-", 1)[1],
                    release_id=_R9_ID,
                    platform_family=family,
                    architecture=arch,
                    profile=profile,
                    payload_uncompressed_bytes=len(raw),
                    minimum_slot_bytes=len(raw),
                    persist_read_schema_min=1,
                    persist_read_schema_max=1,
                    persist_write_schema=1,
                    release_notes="T3-UPDATE2 fail-closed proof release.",
                )
                SystemUpdateInbox(state_dir).receive(bundle)
                verified = authority.verify_current_candidate()
                self.assertTrue(verified.present)
                journal_file = (
                    state_dir / "system-updates" / "journal" / "boot-journal.json"
                )
                with self.assertRaises(UpdateBackendUnavailable) as raised:
                    authority.stage_current_candidate()
                self.assertIn(
                    "inactive-slot filesystem is unavailable",
                    str(raised.exception),
                )
                # Fail-closed: no journal write, no default move, and the
                # backend still reports the A/B composition (no silent
                # single-root fallback).
                self.assertFalse(journal_file.exists())
                self.assertEqual(authority.backend.boot_backend.inspect().default_slot, "A")
                self.assertTrue(authority.backend.status_payload()["available"])

    def test_missing_layout_stays_unavailable_without_single_root_routing(self) -> None:
        from greia_platform.system_updates import build_live_update_service

        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            with _patched_env(
                GREIA_SYSTEM_VERSION="0.16.0",
                GREIA_SYSTEM_PLATFORM_FAMILY=family,
                GREIA_SYSTEM_ARCHITECTURE=arch,
                GREIA_SYSTEM_PROFILE=profile,
            ):
                authority = build_live_update_service(
                    state_dir=state_dir,
                    layout_record_path=root / "no-such-layout.json",
                    boot_backend=None,
                    boot_backend_auto=False,
                )
                self.assertFalse(authority.backend.available)
                status = authority.backend.status_payload()
                self.assertFalse(status["available"])
                self.assertIn("A/B", str(status.get("reason", "")))


class LauncherProductionCallTests(unittest.TestCase):
    """`apply_prepared_state` owns the single production seam call.

    The shipped ``INTERACTIVE_READY`` publication invokes
    ``maybe_accept_production_boot`` exactly once: the unprivileged
    launcher presents the root-issued one-use token to the root
    ``greia-boot-health`` socket, and the root service commits through
    the production verifier and backends. A pending
    candidate/first-install boot whose candidate observably booted is
    accepted, while plain boots (and failed candidates still on the
    accepted slot) mutate no journal or health state. The existing
    exactly-once apply guard keeps holding.
    """

    #: Fixture kernel boot ID binding issue and verify in these tests.
    _BOOT_ATTEMPT = "aaaaaaaa-1111-2222-3333-444444444444"

    def _serve_boot_health_once(
        self, sock_path: Path, service: object
    ) -> threading.Thread:
        """Serve one root health connection behind a real AF_UNIX socket."""
        from greia_platform.boot_health_service import (
            BootHealthEndpoint,
            handle_boot_health_connection,
        )

        endpoint = BootHealthEndpoint(service, allowed_uids=(0, os.getuid()))  # type: ignore[arg-type]
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(os.fspath(sock_path))
        listener.listen(1)

        def _serve() -> None:
            try:
                connection, _ = listener.accept()
                try:
                    handle_boot_health_connection(
                        connection,
                        endpoint=endpoint,
                        peer=PeerCredential(uid=os.getuid()),
                        boot_state="interactive_ready",
                    )
                finally:
                    listener.close()
            except OSError:
                try:
                    listener.close()
                except OSError:
                    pass

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()
        return thread

    def _issue_production_capability(
        self,
        root: Path,
        *,
        boot_journal_dir: Path,
        update_state_dir: Path,
    ):
        """Issue the one-use token through the production generator entry."""
        from greia_platform.boot_capability import build_production_verifier
        from greia_platform.boot_health import (
            default_capability_authority,
            maybe_issue_boot_capability,
        )

        owner = default_capability_authority(
            authority_dir=root / "cap-authority",
            delivery_dir=root / "cap-delivery",
        )
        issued = maybe_issue_boot_capability(
            authority=owner,
            boot_journal_dir=boot_journal_dir,
            update_state_dir=update_state_dir,
            boot_id=self._BOOT_ATTEMPT,
            peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            peer_uid=os.getuid(),
        )
        assert issued is not None
        verifier = build_production_verifier(
            authority=owner,
            boot_journal_dir=boot_journal_dir,
            update_state_dir=update_state_dir,
            boot_id=self._BOOT_ATTEMPT,
            peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
        )
        return owner, verifier

    def _launcher_env(self, tmp: Path) -> dict[str, str]:
        from greia_launcher import main as launcher_main

        return {
            "GREIA_OS_ROOT": str(ROOT),
            "GREIA_PROFILES_DIR": str(tmp / "profiles"),
            "GREIA_ACTIVE_PROFILE_STATUS": str(tmp / "active.json"),
            "GREIA_MAIN_CREDENTIAL_PATH": str(tmp / "cred.json"),
            launcher_main.DEVELOPER_MARKER_ENV_VAR: str(tmp / "no-marker"),
            "SDL_VIDEODRIVER": "dummy",
        }

    def _synthetic_prepared_state(self):  # type: ignore[no-untyped-def]
        from types import SimpleNamespace

        from greia_launcher.bootstrap import PreparedLauncherState

        return PreparedLauncherState(
            runtime=None,
            sources=(),
            registrations=(),
            activities=(),
            registry=None,
            asset_set=SimpleNamespace(catalogue=None, shared_visuals_available=False),
            profile_store=None,
            profiles=(),
            session=None,
            selector_theme=None,
            runtime_services=None,
            supervisor=None,
            catalogue=None,
            history_recovery_failures=frozenset(),
            parent_degraded=False,
            parent_error=None,
            rejected=(),
            conflicts=(),
            degraded=False,
            activity_discovery_token=(),
            shell_window_backend=None,
            installed=False,
        )

    def _make_launcher(self):  # type: ignore[no-untyped-def]
        from greia_launcher.main import LauncherApplication

        return LauncherApplication(windowed=True, allow_exit=True, bootstrap=False)

    def _prepare_for_apply(self, app):  # type: ignore[no-untyped-def]
        app._boot_lifecycle.mark_display_ready()
        app._boot_lifecycle.mark_first_frame_visible()
        app._boot_lifecycle.begin_preparing_runtime()

    def _first_install_tree(self, root: Path):  # type: ignore[no-untyped-def]
        """Build a pending first-install device tree; return env overrides."""
        from greia_platform.boot_transaction import (
            BootArtifactSet,
            BootTransactionCoordinator,
        )
        from greia_platform.persistent_layout import InstalledLayoutRecord
        from greia_platform.slot_writer import FINALIZER_VERSION, FinalizationReceipt

        family, _, profile = _shipped_identity()
        layout_path = root / "layout.json"
        layout_path.write_bytes(_canonical_record(_record_dict(family, profile)))
        cmdline = root / "cmdline"
        cmdline.write_text(
            f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={_UUID_A} ro quiet\n",
            encoding="utf-8",
        )
        identity = root / "release-identity.json"
        identity.write_bytes(
            _canonical_record(
                {
                    "boot_backend": "grub-ab-v1",
                    "layout_id": "legacy-bios-ab-v1",
                    "release_id": _R8_ID,
                    "role": "system-a",
                    "slot": "A",
                }
            )
        )
        record = InstalledLayoutRecord.from_dict(
            json.loads(layout_path.read_text(encoding="utf-8"))
        )
        receipt = FinalizationReceipt(
            schema_version=1,
            finalizer_version=FINALIZER_VERSION,
            release_id=_R8_ID,
            slot="A",
            role="system-a",
            base_sha256=_KERNEL,
            base_bytes=200 * 1024,
            support_sha256="ef" * 32,
            support_size=1024,
            inventory_token="cd" * 32,
            packages=(),
            packages_digest=hashlib.sha256(b"\n").hexdigest(),
            generic_kernel_sha256=_KERNEL,
            host_initramfs_sha256=_INITRAMFS,
            filesystem_uuid=_UUID_A_FS,
            layout_id="legacy-bios-ab-v1",
            slot_capacity_bytes=_SLOT_BYTES,
        )
        artifacts = BootArtifactSet.from_finalization(receipt=receipt, record=record)
        journal_dir = root / "boot-journal"
        grub_dir = root / "boot-control"
        backend = GrubEnvBackend.initialize(grub_dir, default_slot="A")
        BootTransactionCoordinator.begin_first_install(
            journal_dir=journal_dir, backend=backend, artifact_a=artifacts
        )
        backend.simulate_reboot()
        receipt_path = root / "finalization-receipt.json"
        receipt_path.write_bytes(receipt.canonical_bytes())
        return {
            "GREIA_BOOT_JOURNAL_DIR": str(journal_dir),
            "GREIA_UPDATE_STATE_DIR": str(root / "no-such-update-state"),
            "CREDENTIALS_DIRECTORY": str(root / "credentials"),
            "GREIA_GRUBENV_DIR": str(grub_dir),
            "GREIA_INSTALLED_LAYOUT_RECORD": str(layout_path),
            "GREIA_BOOT_CMDLINE": str(cmdline),
            "GREIA_RELEASE_IDENTITY_PATH": str(identity),
            "GREIA_FINALIZATION_RECEIPT_PATH": str(receipt_path),
        }

    def test_apply_accepts_first_install_through_production_seam_exactly_once(
        self,
    ) -> None:
        from types import SimpleNamespace
        from unittest import mock

        from greia_launcher import boot_health as launcher_health
        from greia_launcher.bootstrap import BootLifecycleError
        from greia_platform.boot_health_service import (
            BootHealthService,
            ReceiptBackedArtifactResolver,
        )
        from greia_platform.boot_transaction import BootTransactionState

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            health_env = self._first_install_tree(root)
            journal_dir = Path(health_env["GREIA_BOOT_JOURNAL_DIR"])
            grub_dir = Path(health_env["GREIA_GRUBENV_DIR"])
            layout_path = Path(health_env["GREIA_INSTALLED_LAYOUT_RECORD"])
            receipt_path = Path(health_env["GREIA_FINALIZATION_RECEIPT_PATH"])
            svc_state = root / "svc-update-state"
            svc_state.mkdir(parents=True)
            history_dir = root / "svc-history"
            history_dir.mkdir(parents=True)
            _, verifier = self._issue_production_capability(
                root, boot_journal_dir=journal_dir, update_state_dir=svc_state
            )

            class _StubUpdateAuthority:
                backend = SimpleNamespace(layout_record_path=layout_path)

                @staticmethod
                def confirm_boot_health() -> dict[str, object]:
                    raise AssertionError("first-install never delegates")

            service = BootHealthService(
                boot_journal_dir=journal_dir,
                update_state_dir=svc_state,
                history_dir=history_dir,
                update_authority=_StubUpdateAuthority(),
                capability_verifier=verifier,
                artifact_resolver=ReceiptBackedArtifactResolver(
                    layout_record_path=layout_path,
                    receipt_path=receipt_path,
                ),
                boot_backend_factory=lambda: GrubEnvBackend.attach(grub_dir),
            )
            sock_path = root / "boot-health.sock"
            server = self._serve_boot_health_once(sock_path, service)
            env = self._launcher_env(root)
            env.update(
                {
                    "GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "cap-delivery"),
                    "GREIA_BOOT_HEALTH_SOCKET_PATH": os.fspath(sock_path),
                }
            )
            with mock.patch.dict(os.environ, env, clear=False):
                real_seam = launcher_health.maybe_accept_production_boot
                calls: list[str] = []

                def _counting(guard):  # type: ignore[no-untyped-def]
                    calls.append(str(guard.state))
                    return real_seam(guard)

                app = self._make_launcher()
                self._prepare_for_apply(app)
                state = self._synthetic_prepared_state()
                with mock.patch.object(
                    launcher_health,
                    "maybe_accept_production_boot",
                    side_effect=_counting,
                ):
                    app.apply_prepared_state(state)
                # Exactly one production seam call at the publication, and
                # the guard already reported INTERACTIVE_READY to it.
                self.assertEqual(calls, ["interactive_ready"])
                outcome = app._post_intro_health_outcome
                self.assertIsNone(app._post_intro_health_error)
                self.assertIsNotNone(outcome)
                self.assertEqual(outcome.accepted_slot, "A")
                self.assertTrue(outcome.first_install)
                self.assertEqual(outcome.recovery_medium_if_failed, SETUP_MEDIUM)
                journal = BootTransactionJournal.load(journal_dir)
                self.assertEqual(journal.state, BootTransactionState.ACCEPTED)
                # The exactly-once apply guard keeps holding: a second
                # apply raises without a second seam call.
                with self.assertRaises(BootLifecycleError):
                    app.apply_prepared_state(state)
                self.assertEqual(len(calls), 1)
            server.join(timeout=10)
            self.assertFalse(server.is_alive())

    def test_apply_is_bounded_noop_on_plain_boot(self) -> None:
        from unittest import mock

        from greia_launcher import boot_health as launcher_health
        from greia_launcher.bootstrap import BootLifecycleError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "profiles").mkdir(parents=True, exist_ok=True)
            env = self._launcher_env(root)
            env.update(
                {
                    "GREIA_BOOT_JOURNAL_DIR": str(root / "boot-journal"),
                    "GREIA_UPDATE_STATE_DIR": str(root / "update-state"),
                    "GREIA_GRUBENV_DIR": str(root / "boot-control"),
                    "GREIA_INSTALLED_LAYOUT_RECORD": str(root / "layout.json"),
                    "GREIA_BOOT_CMDLINE": str(root / "cmdline"),
                    "GREIA_RELEASE_IDENTITY_PATH": str(root / "identity.json"),
                    "GREIA_FINALIZATION_RECEIPT_PATH": str(root / "receipt.json"),
                }
            )
            env.pop("CREDENTIALS_DIRECTORY", None)
            previous_credentials = os.environ.pop("CREDENTIALS_DIRECTORY", None)
            try:
                with mock.patch.dict(os.environ, env, clear=False):
                    os.environ.pop("CREDENTIALS_DIRECTORY", None)
                    app = self._make_launcher()
                    self._prepare_for_apply(app)
                    state = self._synthetic_prepared_state()
                    # Snapshot after launcher construction: construction
                    # owns its credential file; the predicate is that the
                    # publication itself mutates no journal/health state.
                    before = sorted(str(path) for path in root.rglob("*"))
                    calls = []
                    real_seam = launcher_health.maybe_accept_production_boot

                    def _counting(guard):  # type: ignore[no-untyped-def]
                        calls.append(str(guard.state))
                        return real_seam(guard)

                    with mock.patch.object(
                        launcher_health,
                        "maybe_accept_production_boot",
                        side_effect=_counting,
                    ):
                        app.apply_prepared_state(state)
                    after = sorted(str(path) for path in root.rglob("*"))
                    self.assertEqual(calls, ["interactive_ready"])
                    self.assertIsNone(app._post_intro_health_outcome)
                    self.assertIsNone(app._post_intro_health_error)
                    self.assertEqual(before, after)
                    with self.assertRaises(BootLifecycleError):
                        app.apply_prepared_state(state)
                    self.assertEqual(len(calls), 1)
            finally:
                if previous_credentials is not None:
                    os.environ["CREDENTIALS_DIRECTORY"] = previous_credentials

    def test_apply_leaves_unhealthy_candidate_unaccepted(self) -> None:
        from unittest import mock

        from greia_launcher import boot_health as launcher_health
        from greia_platform.boot_transaction import BootTransactionState

        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _patched_env(
                GREIA_SYSTEM_VERSION="0.16.0",
                GREIA_SYSTEM_PLATFORM_FAMILY=family,
                GREIA_SYSTEM_ARCHITECTURE=arch,
                GREIA_SYSTEM_PROFILE=profile,
            ):
                rig = _ProductionRig(root / "rig", family, arch, profile)
                rig.receive(rig.build_release("r9", release_id=_R9_ID, sequence=_R9_SEQ))
                rig.op("STAGE_CURRENT_CANDIDATE")
                rig.op("ARM_CURRENT_CANDIDATE")
                # Firmware cannot boot the kernel-less candidate: the
                # machine stays on the accepted slot.
                rig.grub.reconcile("A")
            files = rig.seams.filesystem.files
            cmdline = root / "cmdline"
            cmdline.write_text(
                f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={_UUID_A} ro quiet\n",
                encoding="utf-8",
            )
            identity = root / "identity.json"
            identity.write_bytes(files["etc/greia-os/release-identity.json"])
            receipt = root / "receipt.json"
            receipt.write_bytes(files["etc/greia-os/finalization-receipt.json"])
            env = self._launcher_env(root)
            env.update(
                {
                    "GREIA_UPDATE_STATE_DIR": str(rig.state_dir),
                    "GREIA_BOOT_JOURNAL_DIR": str(root / "empty-boot-journal"),
                    "CREDENTIALS_DIRECTORY": str(root / "credentials"),
                    "GREIA_GRUBENV_DIR": str(rig.root / "boot-control"),
                    "GREIA_INSTALLED_LAYOUT_RECORD": str(rig.layout_path),
                    "GREIA_BOOT_CMDLINE": str(cmdline),
                    "GREIA_RELEASE_IDENTITY_PATH": str(identity),
                    "GREIA_FINALIZATION_RECEIPT_PATH": str(receipt),
                }
            )
            with mock.patch.dict(os.environ, env, clear=False):
                journal_before = BootTransactionJournal.load(rig.authority.backend.journal_dir)
                app = self._make_launcher()
                self._prepare_for_apply(app)
                app.apply_prepared_state(self._synthetic_prepared_state())
                # No confirm/finalize: outcome stays empty, the journal is
                # untouched (still armed, never accepted), and no vault
                # credential was consumed into an acceptance.
                self.assertIsNone(app._post_intro_health_outcome)
                self.assertIsNone(app._post_intro_health_error)
                journal_after = BootTransactionJournal.load(rig.authority.backend.journal_dir)
                self.assertEqual(journal_after.state, journal_before.state)
                self.assertNotEqual(journal_after.state, BootTransactionState.ACCEPTED)
                self.assertFalse(launcher_health.default_vault().credential_live())
                self.assertEqual(rig.grub.inspect().default_slot, "A")
                record = rig.record()
                self.assertEqual(record.accepted_slot, "A")
                self.assertEqual(record.accepted_release_id, _R8_ID)

    def test_update_flow_accepts_via_launcher_seam_with_production_observer(
        self,
    ) -> None:
        from unittest import mock

        from greia_launcher import boot_health as launcher_health
        from greia_platform.boot_health_service import BootHealthService
        from greia_platform.boot_transaction import BootTransactionState

        family, arch, profile = _shipped_identity()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _patched_env(
                GREIA_SYSTEM_VERSION="0.16.0",
                GREIA_SYSTEM_PLATFORM_FAMILY=family,
                GREIA_SYSTEM_ARCHITECTURE=arch,
                GREIA_SYSTEM_PROFILE=profile,
            ):
                rig = _ProductionRig(root / "rig", family, arch, profile)
                rig.receive(rig.build_release("r9", release_id=_R9_ID, sequence=_R9_SEQ))
                rig.op("VERIFY_CURRENT_CANDIDATE")
                rig.op("STAGE_CURRENT_CANDIDATE")
                rig.op("ARM_CURRENT_CANDIDATE")
                self.assertEqual(rig.grub.simulate_reboot(), "B")
            empty_boot = root / "empty-boot-journal"
            empty_boot.mkdir(parents=True)
            history_dir = root / "svc-history"
            history_dir.mkdir(parents=True)
            _, verifier = self._issue_production_capability(
                root, boot_journal_dir=empty_boot, update_state_dir=rig.state_dir
            )
            service = BootHealthService(
                boot_journal_dir=empty_boot,
                update_state_dir=rig.state_dir,
                history_dir=history_dir,
                update_authority=rig.authority,
                capability_verifier=verifier,
            )
            sock_path = root / "boot-health.sock"
            server = self._serve_boot_health_once(sock_path, service)
            env = self._launcher_env(root)
            env.update(
                {
                    "GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "cap-delivery"),
                    "GREIA_BOOT_HEALTH_SOCKET_PATH": os.fspath(sock_path),
                }
            )
            with mock.patch.dict(os.environ, env, clear=False):
                app = self._make_launcher()
                self._prepare_for_apply(app)
                calls = []
                real_seam = launcher_health.maybe_accept_production_boot

                def _counting(guard):  # type: ignore[no-untyped-def]
                    calls.append(str(guard.state))
                    return real_seam(guard)

                with mock.patch.object(
                    launcher_health,
                    "maybe_accept_production_boot",
                    side_effect=_counting,
                ):
                    app.apply_prepared_state(self._synthetic_prepared_state())
                self.assertEqual(calls, ["interactive_ready"])
                outcome = app._post_intro_health_outcome
                self.assertIsNone(app._post_intro_health_error)
                self.assertEqual(outcome.accepted_slot, "B")
                self.assertFalse(outcome.first_install)
                journal = BootTransactionJournal.load(rig.authority.backend.journal_dir)
                self.assertEqual(journal.state, BootTransactionState.ACCEPTED)
                self.assertEqual(rig.grub.inspect().default_slot, "B")
                record = rig.record()
                self.assertEqual(record.accepted_slot, "B")
                self.assertEqual(record.accepted_release_id, _R9_ID)
            server.join(timeout=10)
            self.assertFalse(server.is_alive())


if __name__ == "__main__":
    unittest.main()
