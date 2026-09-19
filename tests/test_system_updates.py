from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from greia_platform.persistent_layout import (
    PersistentLayoutError,
    assert_persist_schema_compatible,
    emit_persist_schema_marker,
    parse_persist_schema_marker,
)
from greia_platform.system_updates import (
    BUNDLE_MEMBERS_V3,
    BUNDLE_MEMBERS_V3_WITH_HW,
    HARDWARE_SUPPORT_NAME,
    INBOX_CANDIDATE_NAME,
    MANIFEST_NAME,
    PAYLOAD_NAME,
    SCHEMA_VERSION,
    SystemIdentity,
    SystemUpdateInbox,
    SystemUpdateService,
    UnavailableSystemUpdateBackend,
    UpdateBackendUnavailable,
    UpdateBundleError,
    UpdateCompatibilityError,
    UpdateManifest,
    build_update_bundle,
    inspect_update_bundle,
)

_ZSTD = b"\x28\xb5\x2f\xfd"


def _zst_bytes(seed: bytes, size: int = 4096) -> bytes:
    assert size > 4
    body = (seed * ((size // len(seed)) + 1))[: size - 4]
    return _ZSTD + body


def _valid_hw_bytes() -> bytes:
    import zstandard

    packages = b""
    packages_gz = b""
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "i386",
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
_UNCOMPRESSED = 8 * 1024 * 1024


def _v3_bundle(root: Path, payload: bytes, *, name: str = "candidate.greiaupdate") -> Path:
    payload_path = root / f"payload-{name}.ext4.zst"
    payload_path.write_bytes(payload)
    hw_path = root / f"hw-{name}.tar.zst"
    hw_path.write_bytes(_HW_BYTES)
    out = root / name
    if out.exists():
        out.unlink()
    build_update_bundle(
        payload_path=payload_path,
        hardware_support_path=hw_path,
        output_path=out,
        version="0.14.0",
        release_id="greia-0.14.0",
        platform_family="legacy-x86",
        architecture="i386",
        profile="legacy-x86-i686",
        payload_uncompressed_bytes=_UNCOMPRESSED,
        minimum_slot_bytes=_UNCOMPRESSED,
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="v3",
    )
    return out


class SystemUpdateBundleTests(unittest.TestCase):
    def _manifest(self, payload: bytes) -> UpdateManifest:
        return UpdateManifest(
            schema_version=SCHEMA_VERSION,
            release_id="greia-0.14.0",
            version="0.14.0",
            platform_family="legacy-x86",
            architecture="i386",
            profile="legacy-x86-i686",
            board=None,
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            payload_size=len(payload),
            payload_uncompressed_bytes=len(payload),
            payload_minimum_slot_bytes=len(payload),
            hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
            hardware_support_size=len(_HW_BYTES),
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
            release_notes="Emoji and update plumbing.",
        )

    def test_inspection_binds_payload_to_manifest_without_granting_trust(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"slot-image-"))
            inspected = inspect_update_bundle(bundle)
            self.assertEqual(inspected.manifest.version, "0.14.0")
            self.assertEqual(inspected.manifest.release_id, "greia-0.14.0")
            self.assertEqual(inspected.manifest.schema_version, 3)
            # No provenance trust: the inspected bundle carries structure +
            # digests only, never a signature verdict.
            self.assertFalse(hasattr(inspected, "signature"))
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(
                    [i.filename for i in archive.infolist()],
                    list(BUNDLE_MEMBERS_V3_WITH_HW),
                )

    def test_tampered_payload_is_rejected_before_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"slot-image-"))
            with zipfile.ZipFile(bundle) as src:
                manifest_raw = src.read(MANIFEST_NAME)
            payload = bytearray(_zst_bytes(b"slot-image-"))
            payload[10] ^= 0xFF
            path = root / "tampered.greiaupdate"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as dst:
                info = zipfile.ZipInfo(MANIFEST_NAME, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                dst.writestr(info, manifest_raw)
                info2 = zipfile.ZipInfo(PAYLOAD_NAME, date_time=(1980, 1, 1, 0, 0, 0))
                info2.compress_type = zipfile.ZIP_STORED
                dst.writestr(info2, bytes(payload))
                info3 = zipfile.ZipInfo(
                    HARDWARE_SUPPORT_NAME, date_time=(1980, 1, 1, 0, 0, 0)
                )
                info3.compress_type = zipfile.ZIP_STORED
                dst.writestr(info3, _HW_BYTES)
            with self.assertRaises(UpdateBundleError) as ctx:
                inspect_update_bundle(path)
            self.assertIn("digest", str(ctx.exception).lower())

    def test_extra_or_reordered_members_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"slot-"))
            with zipfile.ZipFile(bundle) as src:
                members = {name: src.read(name) for name in src.namelist()}
            path = root / "bad.greiaupdate"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(MANIFEST_NAME, members[MANIFEST_NAME])
                archive.writestr("extra.txt", b"no")
                archive.writestr(PAYLOAD_NAME, members[PAYLOAD_NAME])
                archive.writestr(HARDWARE_SUPPORT_NAME, members[HARDWARE_SUPPORT_NAME])
            with self.assertRaises(UpdateBundleError):
                inspect_update_bundle(path)
            # Reordered members are also rejected (deterministic order).
            reordered = root / "reordered.greiaupdate"
            with zipfile.ZipFile(reordered, "w") as archive:
                archive.writestr(PAYLOAD_NAME, members[PAYLOAD_NAME])
                archive.writestr(MANIFEST_NAME, members[MANIFEST_NAME])
                archive.writestr(HARDWARE_SUPPORT_NAME, members[HARDWARE_SUPPORT_NAME])
            with self.assertRaises(UpdateBundleError):
                inspect_update_bundle(reordered)

    def test_manifest_rejects_type_coercion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"slot-"))
            base = json.loads(zipfile.ZipFile(bundle).read(MANIFEST_NAME).decode())
            bad = dict(base)
            bad["schema_version"] = True
            with self.assertRaises(UpdateBundleError):
                UpdateManifest.from_json_dict(bad)
            bad = dict(base)
            bad["persist_read_schema_min"] = 5
            bad["persist_read_schema_max"] = 2
            with self.assertRaises(UpdateBundleError):
                UpdateManifest.from_json_dict(bad)
            bad = dict(base)
            bad["board"] = "bad board!"
            with self.assertRaises(UpdateBundleError):
                UpdateManifest.from_json_dict(bad)
            good = dict(base)
            good["board"] = None
            UpdateManifest.from_json_dict(good)

    def test_inbox_receives_bounded_bytes_to_fixed_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"slot-image-"))
            inbox = SystemUpdateInbox(root / "state")
            queued = inbox.receive(bundle)
            self.assertTrue(queued.path.is_file())
            self.assertEqual(queued.path.name, INBOX_CANDIDATE_NAME)
            status = inbox.status_payload()
            self.assertEqual(status["state"], "received")
            self.assertFalse(status["activation_available"])
            self.assertRegex(str(status["bundle_sha256"]), r"^[0-9a-f]{64}$")
            self.assertNotIn("bundle_path", status)

    def test_inbox_fixed_candidate_reupload_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"slot-image-"))
            inbox = SystemUpdateInbox(root / "state")
            first = inbox.receive(bundle)
            original_bytes = first.path.read_bytes()
            second = inbox.receive(bundle)
            self.assertEqual(first.path, second.path)
            self.assertEqual(first.path.name, INBOX_CANDIDATE_NAME)
            self.assertEqual(first.path.read_bytes(), original_bytes)
            self.assertEqual(len(list(inbox.inbox_dir.glob("*.greiaupdate"))), 1)

    def test_new_candidate_overwrites_fixed_path_and_prunes_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_source = _v3_bundle(root, _zst_bytes(b"slot-image-a-"), name="first.greiaupdate")
            second_source = _v3_bundle(root, _zst_bytes(b"slot-image-b-"), name="second.greiaupdate")
            inbox = SystemUpdateInbox(root / "state")
            first = inbox.receive(first_source)
            first_path = first.path
            first_bytes = first_path.read_bytes()
            second = inbox.receive(second_source)
            self.assertEqual(first_path, second.path)
            self.assertEqual(second.path.name, INBOX_CANDIDATE_NAME)
            self.assertNotEqual(second.path.read_bytes(), first_bytes)
            self.assertTrue(second.path.is_file())
            self.assertEqual(len(list(inbox.inbox_dir.glob("*.greiaupdate"))), 1)
            # Legacy content-addressed duplicate is pruned on next receive.
            legacy = inbox.inbox_dir / "greia-0.14.0-deadbeef.greiaupdate"
            legacy.write_bytes(b"legacy")
            third = inbox.receive(second_source)
            self.assertEqual(third.path.name, INBOX_CANDIDATE_NAME)
            self.assertFalse(legacy.exists())
            self.assertEqual(len(list(inbox.inbox_dir.glob("*.greiaupdate"))), 1)

    def test_current_unavailable_backend_never_falls_back_to_active_root(self) -> None:
        backend = UnavailableSystemUpdateBackend("single-root layout")
        self.assertFalse(backend.available)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"slot-image-"))
            service = SystemUpdateService(
                root / "state",
                SystemIdentity("0.13.0", "legacy-x86", "i386", "legacy-x86-i686"),
                backend,
            )
            # Compatibility verification runs before backend authority. A
            # digest-tampered bundle must therefore fail at inspection rather
            # than reaching any destructive fallback.
            with zipfile.ZipFile(bundle) as src:
                manifest_raw = src.read(MANIFEST_NAME)
            payload = bytearray(_zst_bytes(b"slot-image-"))
            payload[10] ^= 0xFF
            tampered = root / "tampered.greiaupdate"
            with zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as dst:
                dst.writestr(MANIFEST_NAME, manifest_raw)
                dst.writestr(PAYLOAD_NAME, bytes(payload))
                dst.writestr(HARDWARE_SUPPORT_NAME, _HW_BYTES)
            with self.assertRaises(UpdateBundleError):
                service.stage(tampered)
            with self.assertRaises(UpdateBackendUnavailable):
                backend.stage(inspect_update_bundle(bundle))

    def test_system_identity_requires_exact_family_architecture_and_profile(self) -> None:
        manifest = self._manifest(_zst_bytes(b"slot-", size=64))
        SystemIdentity(
            "0.13.0", "legacy-x86", "i386", "legacy-x86-i686"
        ).assert_compatible(manifest)
        with self.assertRaises(UpdateCompatibilityError):
            SystemIdentity(
                "0.13.0", "legacy-x86", "amd64", "legacy-x86-i686"
            ).assert_compatible(manifest)
        with self.assertRaises(UpdateCompatibilityError):
            SystemIdentity().assert_compatible(manifest)

    def test_build_inspect_round_trip_without_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"complete-slot-"))
            inspected = inspect_update_bundle(bundle)
            self.assertEqual(inspected.manifest.schema_version, SCHEMA_VERSION)
            self.assertEqual(inspected.manifest.release_id, "greia-0.14.0")
            with zipfile.ZipFile(bundle) as archive:
                names = [i.filename for i in archive.infolist()]
                self.assertEqual(names, list(BUNDLE_MEMBERS_V3_WITH_HW))
                for info in archive.infolist():
                    if info.filename.endswith(".zst"):
                        self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_old_signed_format_rejected_with_migration_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                "schema_version": 2,
                "release_id": "greia-0.14.0",
                "version": "0.14.0",
                "platform_family": "legacy-x86",
                "architecture": "i386",
                "profile": "legacy-x86-i686",
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
            with self.assertRaises(UpdateBundleError) as ctx:
                inspect_update_bundle(path)
            message = str(ctx.exception).lower()
            self.assertIn("v3", message)
            self.assertTrue("rebuild" in message or "migration" in message)

    def test_persist_schema_range_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _v3_bundle(root, _zst_bytes(b"persist-"))
            manifest = inspect_update_bundle(bundle).manifest
            self.assertEqual(parse_persist_schema_marker(emit_persist_schema_marker(1)), 1)
            self.assertEqual(assert_persist_schema_compatible(1, manifest), 1)
            with self.assertRaises(PersistentLayoutError) as ctx:
                assert_persist_schema_compatible(10, manifest)
            self.assertIn("migration", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
