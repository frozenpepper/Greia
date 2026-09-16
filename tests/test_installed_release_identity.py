"""POSTR1-INSTALLED-RELEASE-IDENTITY-FACTS acceptance: slot release authority states architecture.

The installed updater's compatibility check resolves from the image-owned
``etc/greia-os/release-identity.json`` written by ``SlotFinalizer``. This
suite proves both production finalization paths (fresh-install
orchestrator and update-staging backend, each through its real
``SlotFinalizer.finalize`` call with injected destination seams) state the
signed ``architecture`` fact so resolution needs no ``GREIA_SYSTEM_*``
environment and no ``image-profile.json``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
import uuid
from io import BytesIO
from pathlib import Path
from unittest import mock

from greia_platform.slot_writer import (
    DestinationSlot,
    HardwareInventoryAttestation,
    LoopbackSlotFile,
    SlotFinalizeError,
    SlotFinalizer,
    SlotProfilePolicy,
    SlotWriter,
    VerifiedReleaseMember,
)

HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None

_FAMILY = "legacy-x86"
_ARCH = "i386"
_PROFILE = "legacy-x86-i686"
_VERSION = "0.15.0"

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"

_SLOT_BYTES = 1024 * 1024 * 1024


def _canonical(payload: dict) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _payload(size: int = 128 * 1024) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _member(payload: bytes) -> VerifiedReleaseMember:
    digest = hashlib.sha256(payload).hexdigest()
    hw_digest = hashlib.sha256(b"hwset-member").hexdigest()
    return VerifiedReleaseMember(
        release_id="greia-r9",
        payload_sha256=digest,
        payload_size=len(payload),
        payload_uncompressed_bytes=len(payload),
        minimum_slot_bytes=len(payload),
        hardware_support_sha256=hw_digest,
        hardware_support_size=len(b"hwset-member"),
    )


def _record(*, slot: str = "B") -> DestinationSlot:
    return DestinationSlot(
        semantic_slot=slot,
        role=f"system-{slot.lower()}",
        slot_capacity_bytes=_SLOT_BYTES,
        active_slot="A",
        accepted_slot="A",
        layout_id="legacy-bios-ab-v1",
        role_filesystem_uuid=_UUID_B_FS if slot == "B" else _UUID_A_FS,
        other_role_filesystem_uuid=_UUID_A_FS if slot == "B" else _UUID_B_FS,
    )


class _FakeFilesystem:
    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.files: dict[str, bytes] = {}
        self.mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        return None

    def expand_to_capacity(self) -> None:
        return None

    def mount(self) -> Path:
        self.mounted = True
        self.mount_dir.mkdir(parents=True, exist_ok=True)
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
        self.files[relative_path] = bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_completeness(self) -> None:
        from greia_platform.slot_writer import check_slot_completeness

        check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        return None


class _FakeInstaller:
    def install(self, firmware, microcode):  # type: ignore[no-untyped-def]
        return ()


def _inventory() -> HardwareInventoryAttestation:
    return HardwareInventoryAttestation(token="cd" * 32)


def _support():  # type: ignore[no-untyped-def]
    from greia_platform.slot_writer import ReleaseSupportSet

    return ReleaseSupportSet(
        support_digest=hashlib.sha256(b"hwset-member").hexdigest(),
        support_size=len(b"hwset-member"),
        installed_size_bound=1024,
        provided_firmware=frozenset(),
        provided_microcode=frozenset(),
        packages=(),
    )


def _finalize_with_policy(root: Path, policy: SlotProfilePolicy) -> dict:
    from greia_platform.slot_writer import ReleaseSupportSet  # noqa: F401

    payload = _payload()
    member = _member(payload)
    destination = _record()
    store_path = root / f"slot-{uuid.uuid4().hex}.img"
    store = LoopbackSlotFile.create(store_path, destination.slot_capacity_bytes)
    try:
        write = SlotWriter().write(
            member=member,
            destination=destination,
            source=BytesIO(payload),
            storage=store,
            support_installed_bytes=1024,
        )
        filesystem = _FakeFilesystem(root / "mnt")
        from greia_platform.slot_writer import (
            REQUIRED_SLOT_COMPLETENESS_DIRS,
            REQUIRED_SLOT_COMPLETENESS_FILES,
        )

        mount_dir = root / "mnt"
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
        SlotFinalizer().finalize(
            write=write,
            destination=destination,
            filesystem=filesystem,  # type: ignore[arg-type]
            package_installer=_FakeInstaller(),  # type: ignore[arg-type]
            inventory=_inventory(),
            support=_support(),
            profile_policy=policy,
        )
        raw = filesystem.files["etc/greia-os/release-identity.json"]
        return json.loads(raw.decode("utf-8"))
    finally:
        store.close()


def _isolated_env(root: Path, extra: dict | None = None):
    return mock.patch.dict(
        os.environ,
        {
            "GREIA_RELEASE_IDENTITY_PATH": str(root / "release-identity.json"),
            "GREIA_INSTALLED_LAYOUT_RECORD": str(root / "installed-layout.json"),
            "GREIA_IMAGE_PROFILE_PATH": str(root / "image-profile.json"),
            "GREIA_SYSTEM_VERSION": "",
            "GREIA_SYSTEM_PLATFORM_FAMILY": "",
            "GREIA_SYSTEM_ARCHITECTURE": "",
            "GREIA_SYSTEM_PROFILE": "",
            **(extra or {}),
        },
        clear=False,
    )


def _layout_dict() -> dict:
    return {
        "accepted_release_id": "greia-r8",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": _PROFILE,
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "layout_id": "legacy-bios-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": _FAMILY,
        "schema_version": 1,
        "slot_bytes": 1073741824,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }


class InstalledReleaseIdentityFactsTests(unittest.TestCase):
    def test_finalizer_states_signed_facts_and_resolves_without_env(self) -> None:
        from greia_platform.system_updates import resolve_installed_system_identity

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = SlotProfilePolicy(
                layout_id="legacy-bios-ab-v1",
                system_slot_bytes=_SLOT_BYTES,
                boot_backend="grub-ab-v1",
                architecture=_ARCH,
                platform_family=_FAMILY,
                profile=_PROFILE,
                version=_VERSION,
            )
            document = _finalize_with_policy(root, policy)
            self.assertEqual(document["architecture"], _ARCH)
            self.assertEqual(document["platform_family"], _FAMILY)
            self.assertEqual(document["profile"], _PROFILE)
            self.assertEqual(document["version"], _VERSION)
            # Canonical bytes: the stored document reloads under the
            # fail-closed loader (proves the writer never emits
            # non-canonical bytes).
            (root / "release-identity.json").write_bytes(_canonical(document))
            with _isolated_env(root):
                identity = resolve_installed_system_identity()
        self.assertEqual(identity.architecture, _ARCH)
        self.assertEqual(identity.platform_family, _FAMILY)
        self.assertEqual(identity.profile, _PROFILE)
        self.assertEqual(identity.version, _VERSION)
        self.assertTrue(identity.compatibility_known)

    def test_missing_facts_stay_unknown_and_refuse_compat(self) -> None:
        from greia_platform.system_updates import (
            UpdateCompatibilityError,
            resolve_installed_system_identity,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Positive control RED: a finalization without authoritative
            # facts omits the keys (never a host guess).
            policy = SlotProfilePolicy(
                layout_id="legacy-bios-ab-v1",
                system_slot_bytes=_SLOT_BYTES,
                boot_backend="grub-ab-v1",
            )
            document = _finalize_with_policy(root, policy)
            self.assertNotIn("architecture", document)
            (root / "release-identity.json").write_bytes(_canonical(document))
            (root / "installed-layout.json").write_bytes(
                _canonical(_layout_dict())
            )
            with _isolated_env(root):
                identity = resolve_installed_system_identity()
            # Layout record carries platform_family/profile but nothing
            # carries architecture: still unknown and refusing.
            self.assertEqual(identity.architecture, "unknown")
            self.assertFalse(identity.compatibility_known)
            manifest = mock.Mock()
            manifest.platform_family = _FAMILY
            manifest.architecture = _ARCH
            manifest.profile = _PROFILE
            with self.assertRaises(UpdateCompatibilityError):
                identity.assert_compatible(manifest)
            # GREEN restore: the same harness with stated facts resolves.
            stated = SlotProfilePolicy(
                layout_id="legacy-bios-ab-v1",
                system_slot_bytes=_SLOT_BYTES,
                boot_backend="grub-ab-v1",
                architecture=_ARCH,
                platform_family=_FAMILY,
                profile=_PROFILE,
                version=_VERSION,
            )
            good = _finalize_with_policy(root, stated)
            self.assertEqual(good["architecture"], _ARCH)
            (root / "release-identity.json").write_bytes(_canonical(good))
            with _isolated_env(root):
                restored = resolve_installed_system_identity()
            self.assertTrue(restored.compatibility_known)

    def test_unknown_placeholder_is_unstated_not_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = SlotProfilePolicy(
                layout_id="legacy-bios-ab-v1",
                system_slot_bytes=_SLOT_BYTES,
                boot_backend="grub-ab-v1",
                architecture="unknown",
                platform_family="unknown",
                profile="unknown",
                version="unknown",
            )
            document = _finalize_with_policy(root, policy)
            self.assertNotIn("architecture", document)
            self.assertNotIn("platform_family", document)
            self.assertNotIn("profile", document)
            self.assertNotIn("version", document)

    def test_policy_rejects_malformed_oversized_facts(self) -> None:
        with self.assertRaises(SlotFinalizeError):
            SlotProfilePolicy(
                layout_id="legacy-bios-ab-v1",
                system_slot_bytes=_SLOT_BYTES,
                boot_backend="grub-ab-v1",
                architecture="has space",
            )
        with self.assertRaises(SlotFinalizeError):
            SlotProfilePolicy(
                layout_id="legacy-bios-ab-v1",
                system_slot_bytes=_SLOT_BYTES,
                boot_backend="grub-ab-v1",
                architecture="a" * 33,
            )
        with self.assertRaises(SlotFinalizeError):
            SlotProfilePolicy(
                layout_id="legacy-bios-ab-v1",
                system_slot_bytes=_SLOT_BYTES,
                boot_backend="grub-ab-v1",
                version="bad\x01version",
            )

    def test_loader_refuses_malformed_oversized_noncanonical_facts(self) -> None:
        from greia_platform.system_updates import (
            UpdateLayoutError,
            load_installed_release_identity,
        )

        base = {
            "boot_backend": "grub-ab-v1",
            "layout_id": "legacy-bios-ab-v1",
            "release_id": "greia-r9",
            "role": "system-b",
            "slot": "B",
            "architecture": _ARCH,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _isolated_env(root):
                cases = {
                    "bad-arch.json": dict(base, architecture="has space"),
                    "oversized-arch.json": dict(base, architecture="a" * 33),
                    "oversized-version.json": dict(base, version="v" * 65),
                    "empty-arch.json": dict(base, architecture=""),
                }
                for name, payload in cases.items():
                    target = root / name
                    target.write_bytes(_canonical(payload))
                    with mock.patch.dict(
                        os.environ,
                        {"GREIA_RELEASE_IDENTITY_PATH": str(target)},
                        clear=False,
                    ):
                        with self.assertRaises(UpdateLayoutError, msg=name):
                            load_installed_release_identity()
                non_canonical = root / "non-canonical.json"
                non_canonical.write_bytes(
                    (json.dumps(base, indent=2) + "\n").encode("utf-8")
                )
                with mock.patch.dict(
                    os.environ,
                    {"GREIA_RELEASE_IDENTITY_PATH": str(non_canonical)},
                    clear=False,
                ):
                    with self.assertRaises(UpdateLayoutError):
                        load_installed_release_identity()

    def test_no_host_architecture_source_or_second_identity(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        for relative in (
            "src/greia_platform/slot_writer.py",
            "src/greia_installer/fresh_ab_install.py",
            "src/greia_platform/system_updates.py",
        ):
            text = (repo / relative).read_text(encoding="utf-8")
            self.assertNotIn("uname", text, msg=relative)
            self.assertNotIn("platform.machine", text, msg=relative)
        writer_text = (repo / "src/greia_platform/slot_writer.py").read_text(
            encoding="utf-8"
        )
        # One identity authority: a single constant definition and a single
        # write_file site. Required-file tuples and docstrings reference the
        # constant but do not create a second source.
        import re

        self.assertEqual(
            writer_text.count("RELEASE_IDENTITY_REL_PATH = "),
            1,
            "exactly one release-identity path constant",
        )
        self.assertEqual(
            len(
                re.findall(
                    r"write_file\(\s*\n?\s*RELEASE_IDENTITY_REL_PATH",
                    writer_text,
                )
            ),
            1,
            "exactly one release-identity write site",
        )


class ProductionPathProofTests(unittest.TestCase):
    """Drive both production finalization call sites with unsigned v3 manifests."""

    def _v3_bundle(self, root: Path, payload: bytes):  # type: ignore[no-untyped-def]
        import zstandard

        from greia_platform.system_updates import (
            build_update_bundle,
            inspect_update_bundle,
        )

        compressed = zstandard.ZstdCompressor(level=3).compress(payload)
        payload_path = root / "payload.ext4.zst"
        payload_path.write_bytes(compressed)
        hw_path = root / "hw.tar.zst"
        hw_path.write_bytes(b"\x28\xb5\x2f\xfd" + b"hwset-payload" * 64)
        bundle = root / "r11.greiaupdate"
        if bundle.exists():
            bundle.unlink()
        build_update_bundle(
            payload_path=payload_path,
            hardware_support_path=hw_path,
            output_path=bundle,
            version=_VERSION,
            release_id="greia-r11",
            platform_family=_FAMILY,
            architecture=_ARCH,
            profile=_PROFILE,
            payload_uncompressed_bytes=len(payload),
            minimum_slot_bytes=len(payload) + 1024 * 1024,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
        )
        return bundle, inspect_update_bundle(bundle).manifest

    def test_installer_path_states_architecture(self) -> None:
        from greia_installer.disk import DeviceObservation
        from greia_installer.fresh_ab_install import (
            FreshAbInstallRequest,
            FreshAbInstallSeams,
            execute_fresh_ab_install,
        )
        from greia_installer.layout import ProfileSizing
        from greia_platform.slot_writer import SlotFinalizeError as _SFE
        from greia_platform.system_updates import resolve_installed_system_identity

        payload = _payload(128 * 1024)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, manifest = self._v3_bundle(root, payload)
            observed = {
                "system-a": {
                    "scheme": "MBR_PARTUUID",
                    "partuuid": "a1b2c3d4-02",
                    "filesystem_uuid": _UUID_A_FS,
                },
                "system-b": {
                    "scheme": "MBR_PARTUUID",
                    "partuuid": "a1b2c3d4-03",
                    "filesystem_uuid": _UUID_B_FS,
                },
                "persist": {
                    "scheme": "MBR_PARTUUID",
                    "partuuid": "a1b2c3d4-04",
                    "filesystem_uuid": "dddddddd-dddd-dddd-dddd-ddddddddddd4",
                },
            }

            class _Runner:
                def __init__(self) -> None:
                    self.commands: list = []

                def run(self, command):  # type: ignore[no-untyped-def]
                    self.commands.append(list(command))

            class _Store:
                def __init__(self, capacity: int) -> None:
                    self._capacity = capacity
                    self._chunks: dict[int, bytes] = {}

                @property
                def capacity_bytes(self) -> int:
                    return self._capacity

                def write_at(self, offset: int, data: bytes) -> None:
                    self._chunks[offset] = bytes(data)

                def read_at(self, offset: int, length: int) -> bytes:
                    assembled = bytearray(length)
                    for start, chunk in self._chunks.items():
                        lo = max(offset, start)
                        hi = min(offset + length, start + len(chunk))
                        if lo < hi:
                            assembled[lo - offset : hi - offset] = chunk[
                                lo - start : hi - start
                            ]
                    return bytes(assembled)

                def flush(self) -> None:
                    return None

            filesystem = _FakeFilesystem(root / "slot-a-mnt")

            class _EmptyInstaller:
                def install(self, firmware, microcode):  # type: ignore[no-untyped-def]
                    assert tuple(firmware) == () and tuple(microcode) == ()
                    return ()

            from greia_installer.persist import PersistCommandResult

            class _PersistRunner:
                def __init__(self) -> None:
                    self.calls = 0

                def run(self, command):  # type: ignore[no-untyped-def]
                    name = command[0]
                    if name == "blkid":
                        self.calls += 1
                        if self.calls == 1:
                            return PersistCommandResult(stdout="", returncode=1)
                        return PersistCommandResult(
                            stdout="cccccccc-cccc-cccc-cccc-ccccccccccc3",
                            returncode=0,
                        )
                    return PersistCommandResult(stdout="", returncode=0)

            persist_stage = root / "persist-stage"
            persist_stage.mkdir()
            boot_control = root / "boot-control"
            backend_state = root / "backend-state"
            journal = root / "journal"
            for directory in (boot_control, backend_state, journal):
                directory.mkdir()
            seams = FreshAbInstallSeams(
                partition_runner=_Runner(),  # type: ignore[arg-type]
                slot_storage_factory=lambda role: _Store(1024 * 1024 * 1024),  # type: ignore[return-value]
                slot_filesystem_factory=lambda: filesystem,  # type: ignore[return-value]
                package_installer_factory=lambda: _EmptyInstaller(),  # type: ignore[return-value]
                inventory_token="cd" * 32,
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
                support_installed_bound=1024 * 1024,
                persist_runner=_PersistRunner(),  # type: ignore[arg-type]
                persist_stage_dir=persist_stage,
                persist_uuid_factory=lambda: uuid.UUID(
                    "cccccccc-cccc-cccc-cccc-ccccccccccc3"
                ),
                boot_control_dir=boot_control,
                backend_state_dir=backend_state,
                journal_dir=journal,
                post_layout_identity_observer=lambda target, plan: {
                    role: dict(values) for role, values in observed.items()
                },
            )
            request = FreshAbInstallRequest(
                bundle_path=bundle,
                expected_profile_id=_PROFILE,
                expected_platform_family=_FAMILY,
                expected_architecture=_ARCH,
                sizing=ProfileSizing(
                    layout_adapter_id="legacy-bios-ab-v1",
                    slot_bytes=1024 * 1024 * 1024,
                    persist_minimum_bytes=256 * 1024 * 1024,
                    boot_backend="grub-ab-v1",
                ),
                target=DeviceObservation(
                    name="sda",
                    path=Path("/dev/sda"),
                    size_bytes=8 * 1024 * 1024 * 1024,
                    device_type="disk",
                    model="Test disk",
                    serial="SERIAL-1",
                    transport="sata",
                    removable=False,
                    read_only=False,
                    mountpoints=(),
                    wwn="WWN-1",
                    major_minor="8:0",
                ),
                support_installed_bytes=1024 * 1024,
                install_target_sha256="ab" * 32,
                password_hash="grub.pbkdf2.sha512.10000." + "A" * 128,
                installed_at_unix=1757000000,
            )
            try:
                execute_fresh_ab_install(request, seams)
            except Exception as exc:
                self.fail(f"production installer path failed: {exc}")
            raw = filesystem.files.get("etc/greia-os/release-identity.json")
            assert raw is not None, "installer finalized no release identity"
            document = json.loads(raw.decode("utf-8"))
            self.assertEqual(document["architecture"], _ARCH)
            (root / "release-identity.json").write_bytes(_canonical(document))
            with _isolated_env(root):
                identity = resolve_installed_system_identity()
            self.assertEqual(identity.architecture, _ARCH)
            self.assertTrue(identity.compatibility_known)

    def test_updater_staging_path_states_architecture(self) -> None:
        from greia_platform.system_updates import (
            SlotBackedSystemUpdateBackend,
            SystemUpdateInbox,
            UpdateSlotSeams,
            load_installed_layout_record,
            resolve_installed_system_identity,
        )

        payload = _payload(220 * 1024)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_path = root / "installed-layout.json"
            layout_path.write_bytes(_canonical(_layout_dict()))
            state_dir = root / "state"
            bundle, manifest = self._v3_bundle(root, payload)
            record = load_installed_layout_record(layout_path)
            assert record is not None
            from greia_platform.slot_writer import (
                DestinationSlot as _Destination,
            )

            destination = _Destination.resolve_from_layout(record, "B")
            store_holder: dict[str, object] = {}
            filesystem = _FakeFilesystem(root / "mnt-b")

            class _MemStore:
                def __init__(self, capacity: int) -> None:
                    self._capacity = capacity
                    self._chunks: dict[int, bytes] = {}

                @property
                def capacity_bytes(self) -> int:
                    return self._capacity

                def write_at(self, offset: int, data: bytes) -> None:
                    self._chunks[offset] = bytes(data)

                def read_at(self, offset: int, length: int) -> bytes:
                    assembled = bytearray(length)
                    for start, chunk in self._chunks.items():
                        lo = max(offset, start)
                        hi = min(offset + length, start + len(chunk))
                        if lo < hi:
                            assembled[lo - offset : hi - offset] = chunk[
                                lo - start : hi - start
                            ]
                    return bytes(assembled)

                def flush(self) -> None:
                    return None

                def close(self) -> None:
                    return None

            def _store(dest):  # type: ignore[no-untyped-def]
                store = _MemStore(dest.slot_capacity_bytes)
                store_holder["store"] = store
                return store

            inventory = _inventory()
            support = _support()
            # Support seam must bind the manifest's hardware-support digest
            # or staging refuses before finalization; reuse the manifest
            # digest with an empty installable set.
            from greia_platform.slot_writer import ReleaseSupportSet

            bound_support = ReleaseSupportSet(
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
                installed_size_bound=1024,
                provided_firmware=frozenset(),
                provided_microcode=frozenset(),
                packages=(),
            )
            seams = UpdateSlotSeams(
                slot_store_factory=_store,  # type: ignore[arg-type]
                filesystem_factory=lambda: filesystem,  # type: ignore[return-value]
                package_installer_factory=lambda: _FakeInstaller(),  # type: ignore[return-value]
                inventory_factory=lambda: inventory,  # type: ignore[return-value]
                support_set_factory=lambda _bundle: bound_support,  # type: ignore[return-value]
                profile_policy_factory=None,
                selection_factory=None,
                installed_contract_factory=(
                    lambda: __import__(
                        "greia_platform.persistent_layout", fromlist=["x"]
                    ).emit_persist_schema_marker(1)
                ),
            )
            backend = SlotBackedSystemUpdateBackend(
                state_dir,
                layout_record_path=layout_path,
                seams=seams,
                boot_backend=None,
            )
            inspected = SystemUpdateInbox(state_dir).receive(bundle)
            backend.stage(inspected)
            raw = filesystem.files.get("etc/greia-os/release-identity.json")
            assert raw is not None, "staged slot carries no release identity"
            document = json.loads(raw.decode("utf-8"))
            self.assertEqual(document["architecture"], _ARCH)
            self.assertEqual(document["platform_family"], _FAMILY)
            self.assertEqual(document["profile"], _PROFILE)
            self.assertEqual(document["version"], _VERSION)
            (root / "release-identity.json").write_bytes(_canonical(document))
            with _isolated_env(root):
                identity = resolve_installed_system_identity(
                    layout_record_path=layout_path,
                )
            self.assertEqual(identity.architecture, _ARCH)
            self.assertTrue(identity.compatibility_known)


if __name__ == "__main__":
    unittest.main()
