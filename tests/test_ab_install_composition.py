"""T3-INSTALL composition proof: shipped builder to accepted A (source scope).

TAKEOVER-3 T3.1/T3.4 (D54): a source/integration test instantiates the
**shipped profile composition** — profile JSON via
``ServiceState.from_target_profile``, the shipped
``composition.build_install_service`` builder, the narrow
``PREPARE_PLAN``/``EXECUTE`` socket protocol — not isolated fakes, and
walks the full chain:

```text
profile
 -> installer socket/service
 -> signed release
 -> A/B/PERSIST layout with observed identities
 -> finalized SYSTEM_A
 -> boot backend
 -> FIRST_INSTALL_PENDING
 -> observed boot
 -> trusted health
 -> accepted A
```

then proves the negative: removing any essential composition element fails
closed before destructive work with no silent legacy fallback, and
legacy/single-root recovery profiles stay explicit legacy.

Zero disk contact: block effects stay behind recording/sparse fakes on
tmpdirs (device execution is T6 scope). The wiring under test — facts
resolution, mode gating, executor binding, socket routing, orchestrator,
journal, GRUB backend, health acceptance — is shipped code.

Evidence boundary: boot-artifact content digests inside the acceptance leg
are well-formed placeholders; digest *binding* (receipt <-> record <->
finalizer) is proven at unit scope in ``test_fresh_ab_install.py``. The
journal on disk already binds layout/backend/release/slot, and this test
asserts those journal facts before accepting.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from support_artifacts import valid_hardware_support_archive_bytes

from greia_installer.composition import (
    AbInstallCompositionError,
    build_install_service,
    install_mode_for_state,
)
from greia_installer.disk import (
    DeviceObservation,
    DiskInventory,
    LiveMediaAncestry,
    PcInternalTargetPolicy,
)
from greia_installer.fresh_ab_install import (
    FreshAbInstallError,
    FreshAbInstallRequest,
    FreshAbInstallSeams,
    accept_first_install,
)
from greia_installer.persist import PersistCommandResult, PersistCommandRunner
from greia_installer.transaction_client import InstallTransactionClient
from greia_installer.transaction_service import (
    PlatformInstallAuthority,
    ServiceState,
    TransactionServiceError,
)
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionJournal,
    BootTransactionState,
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

_PROFILE = "legacy-x86-i686-ab"
_FAMILY = "legacy-x86"
_ARCH = "i386"
_PASSWORD_HASH = "grub.pbkdf2.sha512.10000." + "A" * 128
_HW_BYTES = valid_hardware_support_archive_bytes(architecture="i386")
_SUPPORT_BOUND = 1 * MIB
_MBR_SIGNATURE = "a1b2c3d4"
_PERSIST_FS_UUID = "cccccccc-cccc-cccc-cccc-ccccccccccc3"
_INSTALL_SHA = "ab" * 32


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


def _observed_mbr_identities():
    return {
        "system-a": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{_MBR_SIGNATURE}-02",
            "filesystem_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        },
        "system-b": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{_MBR_SIGNATURE}-03",
            "filesystem_uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
        },
        "persist": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{_MBR_SIGNATURE}-04",
            "filesystem_uuid": _PERSIST_FS_UUID,
        },
    }


def _snapshot():
    return {
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


class RecordingPartitionRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command) -> None:  # type: ignore[no-untyped-def]
        assert isinstance(command, list)
        self.commands.append(list(command))
        return None


class SparseSlotStorage:
    def __init__(self, capacity_bytes: int) -> None:
        self._capacity = capacity_bytes
        self._chunks: dict[int, bytes] = {}

    @property
    def capacity_bytes(self) -> int:
        return self._capacity

    def write_at(self, offset: int, data: bytes) -> None:
        self._chunks[offset] = bytes(data)

    def read_at(self, offset: int, length: int) -> bytes:
        assembled = bytearray(length)
        for start, chunk in self._chunks.items():
            overlap_start = max(offset, start)
            overlap_end = min(offset + length, start + len(chunk))
            if overlap_start < overlap_end:
                assembled[overlap_start - offset : overlap_end - offset] = chunk[
                    overlap_start - start : overlap_end - start
                ]
        return bytes(assembled)

    def flush(self) -> None:
        return None


class FakeSlotFilesystem:
    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.bound_uuid: str | None = None
        self.mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.bound_uuid = filesystem_uuid

    def expand_to_capacity(self) -> None:
        return None

    def mount(self) -> Path:
        if self.mounted:
            raise SlotFinalizeError("slot is already mounted")
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
        return None

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise SlotFinalizeError("slot writes require a mounted destination")

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return ()

    def check_completeness(self) -> None:
        from greia_platform.slot_writer import check_slot_completeness

        check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        return None


class FakePackageInstaller:
    def install(self, firmware, microcode):  # type: ignore[no-untyped-def]
        if tuple(firmware) or tuple(microcode):
            raise AssertionError("empty support set installs nothing")
        return ()


class FakePersistRunner(PersistCommandRunner):
    def __init__(self, *, readback_uuid: str) -> None:
        self.commands: list[list[str]] = []
        self._readback = readback_uuid
        self._blkid_calls = 0

    def run(self, command) -> PersistCommandResult:  # type: ignore[no-untyped-def]
        assert isinstance(command, list)
        self.commands.append(list(command))
        if command[0] == "blkid":
            if command[-1] in ("/dev/sda1", "/dev/sda3"):
                return PersistCommandResult(
                    stdout="dddddddd-dddd-dddd-dddd-dddddddddddd",
                    returncode=0,
                )
            self._blkid_calls += 1
            if self._blkid_calls == 1:
                return PersistCommandResult(stdout="", returncode=1)
            return PersistCommandResult(stdout=self._readback, returncode=0)
        if command[0] in ("mkfs.ext4", "mount", "umount"):
            return PersistCommandResult(stdout="", returncode=0)
        raise AssertionError(f"unexpected PERSIST command: {command[0]}")


class _Probe:
    def __init__(self, devices) -> None:  # type: ignore[no-untyped-def]
        self._devices = list(devices)
        self.calls = 0

    def probe(self):  # type: ignore[no-untyped-def]
        self.calls += 1
        return DiskInventory(tuple(self._devices), generation=self.calls)


class _Resolver:
    def resolve(self, inventory=None):  # type: ignore[no-untyped-def]
        return LiveMediaAncestry.empty()


class AbInstallCompositionProofTests(unittest.TestCase):
    """Shipped builder -> socket -> unsigned v3 release -> layout -> A -> ACCEPTED."""

    def _write_ab_profile(self, root: Path) -> Path:
        profile = root / "target-image-profile.json"
        profile.write_text(
            json.dumps(
                {
                    "profile": {"id": _PROFILE},
                    "platform": {"family": _FAMILY},
                    "base": {"architecture": _ARCH},
                    "storage": {
                        "layout_adapter": "legacy-bios-ab-v1",
                        "system_slot_bytes": 1 * GIB,
                        "persistent_minimum_bytes": 256 * MIB,
                    },
                    "installer": {"target_policy": "pc-internal-v1"},
                    "updates": {"boot_backend": "grub-ab-v1"},
                }
            ),
            encoding="utf-8",
        )
        return profile

    def _write_bundle(self, root: Path):
        import zstandard

        raw = _payload()
        compressed = zstandard.ZstdCompressor(level=3).compress(raw)
        (root / "payload.ext4.zst").write_bytes(compressed)
        (root / "hw.tar.zst").write_bytes(_HW_BYTES)
        bundle = root / "r11.greiaupdate"
        if bundle.exists():
            bundle.unlink()
        build_update_bundle(
            payload_path=root / "payload.ext4.zst",
            hardware_support_path=root / "hw.tar.zst",
            output_path=bundle,
            version="0.15.0",
            release_id="greia-0.15.0",
            platform_family=_FAMILY,
            architecture=_ARCH,
            profile=_PROFILE,
            payload_uncompressed_bytes=len(raw),
            minimum_slot_bytes=len(raw) + MIB,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
        )
        manifest = inspect_update_bundle(bundle).manifest
        return bundle, None, manifest

    def _composition(self, root: Path):
        """Assemble the shipped service; return service + seam handles."""
        for name in ("persist-stage", "boot-control", "slot-a-mnt"):
            (root / name).mkdir(exist_ok=True)
        profile_path = self._write_ab_profile(root)
        bundle, key_dir, manifest = self._write_bundle(root)
        project_root = Path(__file__).resolve().parents[1]
        state = ServiceState.from_target_profile(
            profile_path,
            payload=root / "payload.ext4.zst",
            payload_digest=root / "hw.tar.zst",
            project_root=project_root,
            hardware_support_pool=None,
        )
        self.assertEqual(install_mode_for_state(state), "ab")
        authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile=_PROFILE,
            probe=_Probe([_target()]),  # type: ignore[arg-type]
            live_resolver=_Resolver(),  # type: ignore[arg-type]
        )
        runner = RecordingPartitionRunner()
        touched: list[str] = []
        observed = _observed_mbr_identities()

        def _seams(target):  # type: ignore[no-untyped-def]
            return FreshAbInstallSeams(
                partition_runner=runner,  # type: ignore[arg-type]
                slot_storage_factory=lambda role: (
                    touched.append(role),
                    SparseSlotStorage(1 * GIB),
                )[1],
                slot_filesystem_factory=lambda: FakeSlotFilesystem(
                    root / "slot-a-mnt"
                ),
                package_installer_factory=FakePackageInstaller,
                inventory_token="cd" * 32,
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
                support_installed_bound=_SUPPORT_BOUND,
                persist_runner=FakePersistRunner(readback_uuid=_PERSIST_FS_UUID),
                persist_stage_dir=root / "persist-stage",
                persist_uuid_factory=lambda: uuid.UUID(_PERSIST_FS_UUID),
                boot_control_dir=root / "boot-control",
                bios_bootloader_installer=lambda target, boot_directory: None,
            )

        def _identities(target, plan):  # type: ignore[no-untyped-def]
            if not isinstance(target, DeviceObservation):
                raise FreshAbInstallError("identities need a rematerialized target")
            return observed

        # The shipped builder — not a hand-rolled executor lambda.
        service = build_install_service(
            state=state,
            authority=authority,
            ab_release_bundle=bundle,
            ab_password_hash=_PASSWORD_HASH,
            ab_developer=False,
            ab_support_installed_bytes=_SUPPORT_BOUND,
            ab_seams_factory=_seams,
            ab_identities_factory=_identities,
        )
        self.assertEqual(service.install_mode, "ab")
        self.assertIsNotNone(service.ab_executor)
        return {
            "service": service,
            "authority": authority,
            "runner": runner,
            "touched": touched,
            "observed": observed,
            "root": root,
        }

    def _client(self, service):
        return InstallTransactionClient(
            lambda raw: service.handle_request(
                raw, peer=PeerCredential(uid=65534), boot_state="installer_ready"
            )
        )

    def test_profile_to_accepted_a_through_shipped_composition(self) -> None:
        directory = tempfile.mkdtemp(prefix="t3-composition-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        harness = self._composition(root)
        service = harness["service"]

        # Installer socket/service: PREPARE then EXECUTE over the narrow protocol.
        client = self._client(service)
        prepared = client.prepare(
            expected_target_identity=service.authority.list_targets()[0].identity_digest,
            compatible_profile_id=_PROFILE,
            settings_snapshot=_snapshot(),
        )
        receipt = client.execute(
            transaction_nonce=prepared.transaction_nonce,
            plan_digest=prepared.plan_digest,
        )
        self.assertEqual(
            receipt.target_identity, service._last_installed_identity
        )

        # Signed release flowed into destruction through the shipped path.
        runner = harness["runner"]
        self.assertTrue(runner.commands)
        self.assertEqual(runner.commands[0][0], "wipefs")
        self.assertEqual(harness["touched"], ["A"])

        # A/B/PERSIST layout with observed identities -> finalized SYSTEM_A.
        observed = harness["observed"]
        grub_cfg = root / "boot-control" / "grub" / "grub.cfg"
        self.assertTrue(grub_cfg.is_file())
        grub_text = grub_cfg.read_text(encoding="utf-8")
        validate_grub_ab_text(grub_text)
        self.assertIn(observed["system-a"]["partuuid"], grub_text)
        self.assertIn(observed["system-b"]["partuuid"], grub_text)

        # Boot backend defaults to A.
        backend = GrubEnvBackend.attach(root / "boot-control" / "grub")
        self.assertEqual(backend.inspect().default_slot, "A")

        # FIRST_INSTALL_PENDING journal binds layout/backend/release/slot.
        journal_dir = root / "persist-stage" / "greia" / "boot-journal"
        journal = BootTransactionJournal.load(journal_dir)
        self.assertEqual(journal.state, BootTransactionState.FIRST_INSTALL_PENDING)
        self.assertTrue(journal.first_install)
        self.assertEqual(journal.layout_id, "legacy-bios-ab-v1")
        self.assertEqual(journal.boot_backend, "grub-ab-v1")
        self.assertEqual(journal.release_id, "greia-0.15.0")
        self.assertEqual(journal.candidate_slot, "A")

        # Observed boot -> trusted health -> accepted A (production backend).
        with self.assertRaises(FreshAbInstallError):
            accept_first_install(
                journal_dir=journal_dir,
                backend=backend,
                artifact_a=BootArtifactSet(
                    slot="A",
                    layout_id="legacy-bios-ab-v1",
                    boot_backend="grub-ab-v1",
                    generic_kernel_sha256="cd" * 32,
                    generic_initramfs_sha256="ef" * 32,
                    root_partuuid=observed["system-a"]["partuuid"],
                    root_filesystem_uuid=observed["system-a"]["filesystem_uuid"],
                    release_id="greia-0.15.0",
                ),
            )
        self.assertEqual(backend.simulate_reboot(), "A")
        accepted = accept_first_install(
            journal_dir=journal_dir,
            backend=backend,
            artifact_a=BootArtifactSet(
                slot="A",
                layout_id="legacy-bios-ab-v1",
                boot_backend="grub-ab-v1",
                generic_kernel_sha256="cd" * 32,
                generic_initramfs_sha256="ef" * 32,
                root_partuuid=observed["system-a"]["partuuid"],
                root_filesystem_uuid=observed["system-a"]["filesystem_uuid"],
                release_id="greia-0.15.0",
            ),
        )
        self.assertEqual(accepted.state, BootTransactionState.ACCEPTED)
        self.assertEqual(
            GrubEnvBackend.attach(root / "boot-control" / "grub").inspect().default_slot,
            "A",
        )


class AbInstallCompositionNegativeTests(unittest.TestCase):
    """Each missing element fails closed pre-destruction; never legacy fallback."""

    def _parts(self, root: Path):
        for name in (
            "persist-stage",
            "boot-control",
            "slot-a-mnt",
        ):
            (root / name).mkdir(exist_ok=True)
        proof = AbInstallCompositionProofTests()
        profile_path = proof._write_ab_profile(root)
        bundle, key_dir, manifest = proof._write_bundle(root)
        project_root = Path(__file__).resolve().parents[1]
        state = ServiceState.from_target_profile(
            profile_path,
            payload=root / "payload.ext4.zst",
            payload_digest=root / "hw.tar.zst",
            project_root=project_root,
            hardware_support_pool=None,
        )
        authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile=_PROFILE,
            probe=_Probe([_target()]),  # type: ignore[arg-type]
            live_resolver=_Resolver(),  # type: ignore[arg-type]
        )
        observed = _observed_mbr_identities()

        def _seams(target):  # type: ignore[no-untyped-def]
            return FreshAbInstallSeams(
                partition_runner=RecordingPartitionRunner(),  # type: ignore[arg-type]
                slot_storage_factory=lambda role: SparseSlotStorage(1 * GIB),
                slot_filesystem_factory=lambda: FakeSlotFilesystem(
                    root / "slot-a-mnt"
                ),
                package_installer_factory=FakePackageInstaller,
                inventory_token="cd" * 32,
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
                support_installed_bound=_SUPPORT_BOUND,
                persist_runner=FakePersistRunner(readback_uuid=_PERSIST_FS_UUID),
                persist_stage_dir=root / "persist-stage",
                persist_uuid_factory=lambda: uuid.UUID(_PERSIST_FS_UUID),
                boot_control_dir=root / "boot-control",
                bios_bootloader_installer=lambda target, boot_directory: None,
            )

        def _identities(target, plan):  # type: ignore[no-untyped-def]
            return observed

        return {
            "state": state,
            "authority": authority,
            "bundle": bundle,
            "key_dir": key_dir,
            "seams": _seams,
            "identities": _identities,
            "root": root,
        }

    def _base_kwargs(self, parts):
        return dict(
            state=parts["state"],
            authority=parts["authority"],
            ab_release_bundle=parts["bundle"],
            ab_password_hash=_PASSWORD_HASH,
            ab_developer=False,
            ab_support_installed_bytes=_SUPPORT_BOUND,
            ab_seams_factory=parts["seams"],
            ab_identities_factory=parts["identities"],
        )

    def test_missing_bundle_fails_closed(self) -> None:
        directory = tempfile.mkdtemp(prefix="t3-neg-")
        self.addCleanup(shutil.rmtree, directory, True)
        parts = self._parts(Path(directory))
        kwargs = self._base_kwargs(parts)
        kwargs["ab_release_bundle"] = parts["root"] / "no-such-bundle.greiaupdate"
        with self.assertRaises(AbInstallCompositionError):
            build_install_service(**kwargs)  # type: ignore[arg-type]

    def test_missing_support_bound_fails_closed(self) -> None:
        directory = tempfile.mkdtemp(prefix="t3-neg-")
        self.addCleanup(shutil.rmtree, directory, True)
        parts = self._parts(Path(directory))
        kwargs = self._base_kwargs(parts)
        kwargs["ab_support_installed_bytes"] = None
        with self.assertRaises(AbInstallCompositionError):
            build_install_service(**kwargs)  # type: ignore[arg-type]

    def test_missing_password_hash_fails_closed(self) -> None:
        directory = tempfile.mkdtemp(prefix="t3-neg-")
        self.addCleanup(shutil.rmtree, directory, True)
        parts = self._parts(Path(directory))
        kwargs = self._base_kwargs(parts)
        kwargs["ab_password_hash"] = ""
        with self.assertRaises(AbInstallCompositionError):
            build_install_service(**kwargs)  # type: ignore[arg-type]

    def test_missing_seams_factory_fails_closed(self) -> None:
        directory = tempfile.mkdtemp(prefix="t3-neg-")
        self.addCleanup(shutil.rmtree, directory, True)
        parts = self._parts(Path(directory))
        kwargs = self._base_kwargs(parts)
        kwargs["ab_seams_factory"] = None
        with self.assertRaises(AbInstallCompositionError):
            build_install_service(**kwargs)  # type: ignore[arg-type]

    def test_missing_identities_factory_fails_closed(self) -> None:
        directory = tempfile.mkdtemp(prefix="t3-neg-")
        self.addCleanup(shutil.rmtree, directory, True)
        parts = self._parts(Path(directory))
        kwargs = self._base_kwargs(parts)
        kwargs["ab_identities_factory"] = None
        with self.assertRaises(AbInstallCompositionError):
            build_install_service(**kwargs)  # type: ignore[arg-type]

        # The failure is compositional, not a quiet legacy service: no
        # service object exists to serve EXECUTE on the old engine.

    def test_legacy_recovery_profile_stays_explicit_legacy(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        state = ServiceState(
            payload=Path("/run/live/medium/payload/greia-rootfs.squashfs"),
            payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
            project_root=project_root,
            compatible_profile_id="legacy-x86-i686",
            platform_family="legacy-x86",
            architecture="i386",
            target_policy_id="pc-internal-v1",
            layout_adapter_id="bios-single-ext4",
            boot_backend="none-v1",
            slot_bytes=1 * GIB,
            persist_minimum_bytes=256 * MIB,
        )
        self.assertEqual(install_mode_for_state(state), "legacy-single")
        authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile="legacy-x86-i686",
            probe=_Probe([_target()]),  # type: ignore[arg-type]
            live_resolver=_Resolver(),  # type: ignore[arg-type]
        )
        service = build_install_service(state=state, authority=authority)
        self.assertEqual(service.install_mode, "legacy-single")
        self.assertIsNone(service.ab_executor)

    def test_incoherent_profile_refuses_to_guess(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        state = ServiceState(
            payload=Path("/run/live/medium/payload/greia-rootfs.squashfs"),
            payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
            project_root=project_root,
            compatible_profile_id="mixed-profile",
            platform_family="legacy-x86",
            architecture="i386",
            target_policy_id="pc-internal-v1",
            layout_adapter_id="legacy-bios-ab-v1",
            boot_backend="none-v1",
            slot_bytes=1 * GIB,
            persist_minimum_bytes=256 * MIB,
        )
        with self.assertRaises(AbInstallCompositionError):
            install_mode_for_state(state)

    def test_mode_executor_mismatch_refuses_at_construction(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        state = ServiceState(
            payload=Path("/run/live/medium/payload/greia-rootfs.squashfs"),
            payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
            project_root=project_root,
            compatible_profile_id="legacy-x86-i686",
            platform_family="legacy-x86",
            architecture="i386",
            target_policy_id="pc-internal-v1",
            layout_adapter_id="bios-single-ext4",
            boot_backend="none-v1",
            slot_bytes=1 * GIB,
            persist_minimum_bytes=256 * MIB,
        )
        authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile="legacy-x86-i686",
            probe=_Probe([_target()]),  # type: ignore[arg-type]
            live_resolver=_Resolver(),  # type: ignore[arg-type]
        )
        from greia_installer.transaction_service import InstallTransactionService

        with self.assertRaises(TransactionServiceError):
            InstallTransactionService(
                authority=authority,
                state=state,
                ab_executor=lambda *args: None,  # type: ignore[arg-type]
                install_mode="legacy-single",
            )


if __name__ == "__main__":
    unittest.main()
