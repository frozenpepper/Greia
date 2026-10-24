"""POSTR1-P3-UPDATE-SEAMS: production seam composition contract (offline).

Proves the installed updater composes its production destination path by
default instead of an empty fail-closed seam set:

- ``build_live_update_service()`` with ``seams=None`` (the shipped
  ``main()`` path) binds all eight production factories without probing
  or writing any device at construction time;
- an explicitly empty ``UpdateSlotSeams()`` stays a deliberate
  fail-closed degraded construction at stage time;
- production factories refuse the active/accepted slot and single-root
  layouts through the real ``DestinationSlot``/resolution mechanism, and
  stay fail-closed (``UpdateBackendUnavailable``) where no A/B authority
  or inactive device exists -- with no fallback to a fake/loop
  destination store as the installed default;
- the contract/policy/inventory/support/selection factories return the
  production types over the shared primitives owner
  (``block_slots`` + ``SlotWriter``/``SlotFinalizer``); no second
  writer/finalizer or duplicate device-storage class exists.

All state stays in disposable tmpdirs; no valued disk, no loop device.
Device-positive staging on disposable loopback is proven separately on a
privileged Linux host (attempt evidence, outside this tree).
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import zipfile
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.persistent_layout import (
    emit_persist_schema_marker,
    parse_persist_schema_marker,
    persist_schema_marker_path,
)
from greia_platform.system_updates import (
    SlotBackedSystemUpdateBackend,
    SystemUpdateInbox,
    UpdateBackendUnavailable,
    UpdateCompatibilityError,
    UpdateSlotSeams,
    build_live_update_service,
    build_production_update_seams,
    build_update_bundle,
    inspect_update_bundle,
)
from update_mount_fixtures import installed_mount_patchers


@contextmanager
def _patched_env(**overrides: str):
    previous = dict(os.environ)
    os.environ.update(overrides)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


_ROOT = Path(__file__).resolve().parents[1]
_SOURCE = (_ROOT / "src" / "greia_platform" / "system_updates.py").read_text(
    encoding="utf-8"
)

_SLOT_BYTES = 1024 * 1024 * 1024

_FAMILY = "legacy-x86"
_ARCH = "i386"
_PROFILE = "legacy-x86-i686"
_VERSION = "0.16.0"

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32

_R8_ID = "greia-0.16.0"
_R8_SEQ = 8
_R9_ID = "greia-0.17.0"
_R9_SEQ = 9


@contextmanager
def _installed_mount_prerequisites():
    """Model exact installed mount and fstab facts for downstream tests."""
    with ExitStack() as stack:
        for patcher in installed_mount_patchers(_UUID_P_FS):
            stack.enter_context(patcher)
        yield


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": _R8_ID,
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": _PROFILE,
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "legacy-bios-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": _FAMILY,
        "schema_version": 1,
        "slot_bytes": _SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _canonical_record(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _payload(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def _pool_tree(root: Path, *, dirname: str = "hw-pool") -> Path:
    """Write a minimal verified hardware-support pool (pure file IO)."""
    import hashlib

    fw = b"p3-seams-firmware-bytes"
    uc = b"p3-seams-microcode-bytes"
    pool = root / dirname
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
        "dependency_closures": {
            "firmware-realtek": ["firmware-realtek"],
            "amd64-microcode": ["amd64-microcode"],
        },
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


def _hw_archive_from_pool(pool_dir: Path, output: Path) -> None:
    """Archive a pool tree as the candidate's tar.zst member (Repair D).

    Mirrors ``tools/build_release.py`` ``build_hardware_support_set``:
    deterministic PAX tar of the exact release tree, zstd-compressed.
    """
    import io
    import tarfile

    import zstandard

    members = [
        pool_dir / "manifest.json",
        pool_dir / "Packages",
        pool_dir / "Packages.gz",
    ]
    members.extend(sorted((pool_dir / "pool").glob("*.deb")))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for member in sorted(
            members, key=lambda p: p.relative_to(pool_dir).as_posix()
        ):
            arcname = member.relative_to(pool_dir).as_posix()
            info = tar.gettarinfo(str(member), arcname=arcname)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            info.mode = 0o644
            with member.open("rb") as src:
                tar.addfile(info, src)
    output.write_bytes(zstandard.ZstdCompressor(level=3).compress(buffer.getvalue()))


def _rig(
    root: Path,
    *,
    record: dict[str, object] | None = None,
    env_extra: dict[str, str] | None = None,
):
    """Disposable A/B machine composed through the shipped default path."""
    state_dir = root / "state"
    marker_path = persist_schema_marker_path(state_dir)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_bytes(emit_persist_schema_marker(1))
    layout_path = root / "installed-layout.json"
    layout_path.write_bytes(_canonical_record(record or _record_dict()))
    boot_dir = root / "boot-control"
    boot_dir.mkdir(parents=True, exist_ok=True)
    grub = GrubEnvBackend.initialize(boot_dir, default_slot="A")
    pool = _pool_tree(root)
    env = {
        "GREIA_SYSTEM_VERSION": _VERSION,
        "GREIA_SYSTEM_PLATFORM_FAMILY": _FAMILY,
        "GREIA_SYSTEM_ARCHITECTURE": _ARCH,
        "GREIA_SYSTEM_PROFILE": _PROFILE,
        "GREIA_UPDATE_HARDWARE_SUPPORT_POOL": str(pool),
        "GREIA_UPDATE_SYSFS_DEVICES": str(root / "sysfs"),
    }
    (root / "sysfs").mkdir(parents=True, exist_ok=True)
    env.update(env_extra or {})
    with _patched_env(**env):
        authority = build_live_update_service(
            state_dir=state_dir,
            layout_record_path=layout_path,
            persist_root=state_dir,
            boot_backend=grub,
            boot_backend_auto=False,
        )
    return authority, grub, layout_path, state_dir, None, root


def _v3_bundle(root: Path, _ignored: object = None) -> Path:
    import zstandard

    work = root / "releases" / "r9"
    work.mkdir(parents=True, exist_ok=True)
    raw = _payload(220 * 1024, b"p3-seams:")
    compressed = zstandard.ZstdCompressor(level=3).compress(raw)
    (work / "slot.ext4.zst").write_bytes(compressed)
    # Repair D: the bundle carries the candidate's own pool as its member.
    candidate_pool = _pool_tree(root, dirname="candidate-pool")
    _hw_archive_from_pool(candidate_pool, work / "hw.tar.zst")
    bundle = work / "r9.greiaupdate"
    if bundle.exists():
        bundle.unlink()
    build_update_bundle(
        payload_path=work / "slot.ext4.zst",
        hardware_support_path=work / "hw.tar.zst",
        output_path=bundle,
        version=_R9_ID.split("-", 1)[1],
        release_id=_R9_ID,
        platform_family=_FAMILY,
        architecture=_ARCH,
        profile=_PROFILE,
        payload_uncompressed_bytes=len(raw),
        minimum_slot_bytes=len(raw),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="POSTR1-P3-UPDATE-SEAMS composition release.",
    )
    return bundle


_signed_bundle = _v3_bundle


class DefaultCompositionTests(unittest.TestCase):
    """The shipped default binds production seams with no device IO."""

    def test_default_seams_are_all_production(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, _key, _r = _rig(root)
            seams = authority.backend.seams
            self.assertIsInstance(seams, UpdateSlotSeams)
            for name in (
                "slot_store_factory",
                "filesystem_factory",
                "package_installer_factory",
                "inventory_factory",
                "support_set_factory",
                "profile_policy_factory",
                "selection_factory",
                "installed_contract_factory",
                "support_pool_factory",
            ):
                self.assertIsNotNone(
                    getattr(seams, name), f"production {name} must be bound"
                )
            # Construction is pure: no journal, no slot image, no mount root.
            self.assertFalse(
                (state_dir / "system-updates" / "journal").exists()
            )
            self.assertEqual(list(root.rglob("slot-*.img")), [])

    def test_builder_binds_production_without_service(self) -> None:
        seams = build_production_update_seams(
            layout_record_path=Path("/no-such-layout.json")
        )
        for name in (
            "slot_store_factory",
            "filesystem_factory",
            "package_installer_factory",
            "inventory_factory",
            "support_set_factory",
            "profile_policy_factory",
            "selection_factory",
            "installed_contract_factory",
            "support_pool_factory",
        ):
            self.assertIsNotNone(getattr(seams, name))

    def test_empty_seams_stay_fail_closed_at_stage_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            layout_path = root / "installed-layout.json"
            layout_path.write_bytes(_canonical_record(_record_dict()))
            # Deliberate degraded construction: empty seams, direct backend.
            backend = SlotBackedSystemUpdateBackend(
                state_dir,
                layout_record_path=layout_path,
                seams=UpdateSlotSeams(),
                boot_backend=None,
            )
            self.assertTrue(backend.available)
            bundle = _v3_bundle(root)
            inspected = SystemUpdateInbox(state_dir).receive(bundle)
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                backend.stage(inspected)
            self.assertIn("destination seam", str(raised.exception))
            self.assertFalse(
                (state_dir / "system-updates" / "journal").exists()
            )


class ProductionRefusalTests(unittest.TestCase):
    """Production factories refuse live/single-root layouts (real mechanism)."""

    def test_store_factory_refuses_active_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, _state, _key, _r = _rig(root)
            destination = SimpleNamespace(
                semantic_slot="A",
                role="system-a",
                role_filesystem_uuid=_UUID_A_FS,
            )
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                authority.backend.seams.slot_store_factory(destination)
            self.assertIn("active slot", str(raised.exception))

    def test_store_factory_refuses_accepted_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = _record_dict(
                accepted_slot="B",
                boot_control={"active_slot": "A", "kind": "grub-env-v1"},
            )
            authority, _grub, _layout, _state, _key, _r = _rig(
                root, record=record
            )
            destination = SimpleNamespace(
                semantic_slot="B",
                role="system-b",
                role_filesystem_uuid=_UUID_B_FS,
            )
            with self.assertRaises(UpdateBackendUnavailable):
                authority.backend.seams.slot_store_factory(destination)

    def test_factories_refuse_single_root_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = _record_dict(
                layout_id="bios-single-ext4",
                boot_backend="none-v1",
                boot_control={"active_slot": None, "kind": "none-v1"},
                accepted_slot=None,
                system_b=None,
                platform_family="legacy-x86",
            )
            authority, _grub, _layout, _state, _key, _r = _rig(
                root, record=record
            )
            self.assertFalse(authority.backend.available)
            destination = SimpleNamespace(
                semantic_slot="B",
                role="system-b",
                role_filesystem_uuid=_UUID_B_FS,
            )
            with self.assertRaises(UpdateBackendUnavailable):
                authority.backend.seams.slot_store_factory(destination)
            with self.assertRaises(UpdateBackendUnavailable):
                authority.backend.seams.filesystem_factory()

    def test_staging_without_devices_fails_closed_with_no_loop_fallback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, grub, layout_path, state_dir, private_key, _r = _rig(root)
            self.assertTrue(authority.backend.available)
            bundle = _signed_bundle(root, private_key)
            SystemUpdateInbox(state_dir).receive(bundle)
            verified = authority.verify_current_candidate()
            self.assertTrue(verified.present)
            layout_before = layout_path.read_bytes()
            boot_before = grub.inspect().default_slot
            state_before = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
            )
            with _installed_mount_prerequisites():
                with self.assertRaises(UpdateBackendUnavailable) as raised:
                    authority.stage_current_candidate()
            message = str(raised.exception)
            # Production refusal names the inactive-slot device path, never
            # the degraded empty-seam construction and never a loop fallback.
            self.assertIn("inactive-slot", message)
            self.assertNotIn("destination seam is not configured", message)
            self.assertFalse(
                (state_dir / "system-updates" / "journal").exists()
            )
            self.assertEqual(layout_path.read_bytes(), layout_before)
            self.assertEqual(grub.inspect().default_slot, boot_before)
            state_after = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
            )
            new_files = [p for p in state_after if p not in state_before]
            for extra in new_files:
                self.assertNotIn("slot-", extra)
                self.assertNotIn(".img", extra)


class ProductionFactoryTypeTests(unittest.TestCase):
    """Contract/policy/inventory/support/selection use the production types."""

    def test_installed_contract_reads_canonical_mounted_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, _key, _r = _rig(root)
            raw = authority.backend.seams.installed_contract_factory()
            self.assertEqual(parse_persist_schema_marker(raw), 1)
            self.assertEqual(raw, emit_persist_schema_marker(1))
            self.assertEqual(
                persist_schema_marker_path(state_dir).read_bytes(), raw
            )

    def test_installed_contract_refuses_missing_and_malformed_markers(self) -> None:
        from greia_platform import system_updates

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            factory = system_updates._production_installed_contract_factory(
                persist_root=root
            )
            with self.assertRaisesRegex(UpdateBackendUnavailable, "missing"):
                factory()

            marker_path = persist_schema_marker_path(root)
            marker_path.parent.mkdir(parents=True)
            marker_path.write_bytes(b"not-json")
            with self.assertRaisesRegex(UpdateBackendUnavailable, "valid JSON"):
                factory()

    def test_missing_and_malformed_markers_refuse_before_slot_mutation(self) -> None:
        for marker_state in ("missing", "malformed"):
            with self.subTest(marker_state=marker_state):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    authority, _grub, _layout, state_dir, _key, _r = _rig(root)
                    marker_path = persist_schema_marker_path(state_dir)
                    if marker_state == "missing":
                        marker_path.unlink()
                    else:
                        marker_path.write_bytes(b"not-json")
                    bundle = _v3_bundle(root)
                    SystemUpdateInbox(state_dir).receive(bundle)

                    with _installed_mount_prerequisites():
                        with self.assertRaises(UpdateBackendUnavailable):
                            authority.stage_current_candidate()

                    self.assertFalse(
                        (state_dir / "system-updates" / "journal").exists()
                    )
                    self.assertEqual(list(root.rglob("slot-*.img")), [])

    def test_incompatible_marker_refuses_before_any_slot_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, _key, _r = _rig(root)
            persist_schema_marker_path(state_dir).write_bytes(
                emit_persist_schema_marker(2)
            )
            bundle = _v3_bundle(root)
            SystemUpdateInbox(state_dir).receive(bundle)

            with _installed_mount_prerequisites():
                with self.assertRaises(UpdateCompatibilityError) as raised:
                    authority.stage_current_candidate()

            self.assertIn("cannot read the installed PERSIST schema 2", str(raised.exception))
            self.assertFalse((state_dir / "system-updates" / "journal").exists())
            self.assertEqual(list(root.rglob("slot-*.img")), [])

    def test_profile_policy_derives_from_record(self) -> None:
        from greia_platform.slot_writer import SlotProfilePolicy

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, layout_path, _state, _key, _r = _rig(root)
            from greia_platform.system_updates import load_installed_layout_record

            record = load_installed_layout_record(layout_path)
            assert record is not None
            with _installed_mount_prerequisites():
                policy = authority.backend.seams.profile_policy_factory(record)
            self.assertIsInstance(policy, SlotProfilePolicy)
            self.assertEqual(policy.layout_id, record.layout_id)
            self.assertEqual(policy.system_slot_bytes, record.slot_bytes)
            self.assertEqual(policy.boot_backend, record.boot_backend)

    def test_inventory_attests_fresh_snapshot(self) -> None:
        from greia_platform.slot_writer import HardwareInventoryAttestation

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, _state, _key, _r = _rig(root)
            attestation = authority.backend.seams.inventory_factory()
            self.assertIsInstance(attestation, HardwareInventoryAttestation)
            self.assertRegex(attestation.token, r"^[0-9a-f]{64}$")

    def test_inventory_refuses_missing_sysfs(self) -> None:
        from greia_platform.slot_writer import SlotFinalizeError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, _state, _key, _r = _rig(
                root,
                env_extra={
                    "GREIA_UPDATE_SYSFS_DEVICES": str(root / "no-such-sysfs")
                },
            )
            with self.assertRaises(SlotFinalizeError):
                authority.backend.seams.inventory_factory()

    def test_support_set_binds_manifest_from_verified_pool(self) -> None:
        from greia_platform.slot_writer import ReleaseSupportSet

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, private_key, _r = _rig(root)
            bundle = _signed_bundle(root, private_key)
            inspected = SystemUpdateInbox(state_dir).receive(bundle)
            support = authority.backend.seams.support_set_factory(inspected)
            self.assertIsInstance(support, ReleaseSupportSet)
            self.assertEqual(
                support.support_digest,
                inspected.manifest.hardware_support_sha256,
            )
            self.assertEqual(
                support.support_size, inspected.manifest.hardware_support_size
            )
            # Classes come from the verified pool on disk, not the bundle.
            self.assertEqual(
                support.provided_firmware, frozenset({"firmware-realtek"})
            )
            self.assertEqual(
                support.provided_microcode, frozenset({"amd64-microcode"})
            )

    def test_support_set_refuses_corrupt_candidate_member(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, private_key, _r = _rig(root)
            bundle = _signed_bundle(root, private_key)
            inspected = SystemUpdateInbox(state_dir).receive(bundle)
            # Corrupt the staged inbox candidate after inspection: the
            # materializer re-verifies the member digest on the exact bytes
            # it extracts, so the release support set refuses fail-closed.
            staged = inspected.path
            with zipfile.ZipFile(staged, "r") as source:
                members = {
                    info.filename: source.read(info.filename)
                    for info in source.infolist()
                }
            corrupted = bytearray(members["hardware-support.tar.zst"])
            corrupted[10] ^= 0xFF
            members["hardware-support.tar.zst"] = bytes(corrupted)
            with zipfile.ZipFile(
                staged, "w", compression=zipfile.ZIP_STORED
            ) as target:
                for name, payload in members.items():
                    target.writestr(name, payload)
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                authority.backend.seams.support_set_factory(inspected)
            self.assertIn("support", str(raised.exception))

    def test_selection_contract(self) -> None:
        import hashlib

        from greia_platform.slot_writer import (
            InstalledPackage,
            ReleaseSupportSet,
            ResolvedHardwareSelection,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, _state, _key, _r = _rig(root)
            attestation = authority.backend.seams.inventory_factory()
            support = ReleaseSupportSet(
                support_digest="ab" * 32,
                support_size=128,
                installed_size_bound=0,
                provided_firmware=frozenset({"firmware-realtek"}),
                provided_microcode=frozenset({"amd64-microcode"}),
                packages=(
                    InstalledPackage(
                        "firmware-realtek",
                        "1",
                        "all",
                        hashlib.sha256(b"fw").hexdigest(),
                        "firmware",
                    ),
                    InstalledPackage(
                        "amd64-microcode",
                        "1",
                        "amd64",
                        hashlib.sha256(b"uc").hexdigest(),
                        "microcode",
                    ),
                ),
            )
            selection = authority.backend.seams.selection_factory(
                support, attestation.token
            )
            if selection is not None:
                self.assertIsInstance(selection, ResolvedHardwareSelection)
                self.assertEqual(selection.inventory_token, attestation.token)
                self.assertLessEqual(
                    set(selection.firmware), set(support.provided_firmware)
                )
                self.assertLessEqual(
                    set(selection.microcode), set(support.provided_microcode)
                )
            with self.assertRaises(Exception):
                authority.backend.seams.selection_factory(support, "00" * 32)

    def test_support_pool_factory_proves_selected_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, private_key, _r = _rig(root)
            bundle = _signed_bundle(root, private_key)
            inspected = SystemUpdateInbox(state_dir).receive(bundle)
            pool = authority.backend.seams.support_pool_factory(inspected)
            self.assertIsNotNone(pool)
            # Staged pool carries verified closures (not a legacy pool).
            self.assertEqual(
                dict(pool.dependency_closures),
                {
                    "firmware-realtek": ("firmware-realtek",),
                    "amd64-microcode": ("amd64-microcode",),
                },
            )
            # Empty selection binds zero without touching the whole-pool
            # total; single-class selections bind only their own closure.
            self.assertEqual(pool.selected_installed_bytes([], []), 0)
            single = pool.selected_installed_bytes(["firmware-realtek"], [])
            self.assertGreater(single, 0)
            self.assertLess(single, pool.total_installed_bytes)


class NoParallelMechanismTests(unittest.TestCase):
    """Only the shared owner + shared writer/finalizer exist (grepable)."""

    def test_no_second_writer_finalizer_or_loop_store(self) -> None:
        import re

        self.assertNotRegex(
            _SOURCE, r"(?m)^class \w*(Writer|Finalizer)\w*\s*[\(:]"
        )
        # No loop/file destination store is constructed on the production
        # path (a documentation mention is not a mechanism).
        self.assertNotRegex(_SOURCE, r"LoopbackSlotFile\s*\(")
        self.assertNotRegex(_SOURCE, r"import.*LoopbackSlotFile")
        self.assertIn("SharedBlockSlotPrimitives", _SOURCE)
        self.assertIn("SlotWriter", _SOURCE)
        self.assertIn("SlotFinalizer", _SOURCE)
        self.assertIn("InstallerSlotPackageInstaller", _SOURCE)
        self.assertIn("pool_to_support_set", _SOURCE)
        self.assertNotIn("shell=True", _SOURCE)
        # One narrow production entry point behind the shipped default.
        self.assertIn("def build_production_update_seams", _SOURCE)
        matches = re.findall(r"build_production_update_seams", _SOURCE)
        self.assertGreaterEqual(len(matches), 2)


if __name__ == "__main__":
    unittest.main()
