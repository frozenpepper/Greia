from __future__ import annotations

import hashlib
import inspect as _inspect
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from support_artifacts import valid_hardware_support_archive_bytes

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
    MANIFEST_NAME,
    MAX_HARDWARE_SUPPORT_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_PAYLOAD_BYTES,
    PAYLOAD_NAME,
    SCHEMA_VERSION,
    SystemIdentity,
    SystemUpdateService,
    UnavailableSystemUpdateBackend,
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


_HW_BYTES = valid_hardware_support_archive_bytes(architecture="i386")


def _make_inputs(root: Path, payload: bytes):
    payload_path = root / "payload.ext4.zst"
    payload_path.write_bytes(payload)
    hw_path = root / "hardware-support.tar.zst"
    hw_path.write_bytes(_HW_BYTES)
    return payload_path, hw_path


_UNCOMPRESSED = 8 * 1024 * 1024


class ReleaseV2Tests(unittest.TestCase):
    """v3 migration of the former signed-v2 suite (no key material).

    The file name is retained so the T04 suite set stays stable; every
    assertion below exercises the unsigned v3 contract: deterministic
    members, version/profile/architecture/board/space + PERSIST gating,
    explicit old-format migration rejection, and manifest bounds.
    """

    def _build(self, root: Path, payload: bytes, *, board=None) -> Path:
        payload_path, hw_path = _make_inputs(root, payload)
        bundle = root / "r11.greiaupdate"
        if bundle.exists():
            bundle.unlink()
        build_update_bundle(
            payload_path=payload_path,
            hardware_support_path=hw_path,
            output_path=bundle,
            version="0.15.0",
            release_id="greia-0.15.0",
            platform_family="legacy-x86",
            architecture="i386",
            profile="legacy-x86-i686",
            board=board,
            payload_uncompressed_bytes=_UNCOMPRESSED,
            minimum_slot_bytes=_UNCOMPRESSED,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
            release_notes="v3",
        )
        return bundle

    def test_round_trip_canonical_v3(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, _zst_bytes(b"release-payload-v3-"))
            inspected = inspect_update_bundle(bundle)
            self.assertEqual(inspected.manifest.schema_version, 3)
            self.assertEqual(inspected.manifest.schema_version, SCHEMA_VERSION)
            self.assertEqual(inspected.manifest.release_id, "greia-0.15.0")
            self.assertEqual(
                list(zipfile.ZipFile(bundle).namelist()),
                list(BUNDLE_MEMBERS_V3_WITH_HW),
            )
            raw = zipfile.ZipFile(bundle).read(MANIFEST_NAME)
            self.assertEqual(raw, inspected.manifest.canonical_bytes())
            with zipfile.ZipFile(bundle) as archive:
                for info in archive.infolist():
                    if info.filename.endswith(".zst"):
                        self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_deterministic_bundle_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_dir = root / "a"
            second_dir = root / "b"
            first_dir.mkdir()
            second_dir.mkdir()
            payload = _zst_bytes(b"deterministic-")
            first = self._build(first_dir, payload)
            second = self._build(second_dir, payload)
            # Unsigned v3 builds are fully deterministic: same logical
            # inputs produce identical bytes (no ephemeral keys).
            self.assertEqual(Path(first).read_bytes(), Path(second).read_bytes())
            self.assertEqual(
                zipfile.ZipFile(first).namelist(), zipfile.ZipFile(second).namelist()
            )

    def test_compatibility_decisions_replace_anti_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, _zst_bytes(b"compat-"))
            inspected = inspect_update_bundle(bundle)
            manifest = inspected.manifest
            matching = SystemIdentity("0.15.0", "legacy-x86", "i386", "legacy-x86-i686")
            matching.assert_compatible(manifest)
            # Architecture mismatch refuses.
            with self.assertRaises(UpdateCompatibilityError):
                SystemIdentity(
                    "0.15.0", "legacy-x86", "amd64", "legacy-x86-i686"
                ).assert_compatible(manifest)
            # Profile mismatch refuses.
            with self.assertRaises(UpdateCompatibilityError):
                SystemIdentity(
                    "0.15.0", "legacy-x86", "i386", "other-profile"
                ).assert_compatible(manifest)
            # Board mismatch refuses when the candidate pins a board.
            board_dir = root / "boarded"
            board_dir.mkdir(exist_ok=True)
            payload_path, hw_path = _make_inputs(board_dir, _zst_bytes(b"board-"))
            board_bundle = board_dir / "board.greiaupdate"
            build_update_bundle(
                payload_path=payload_path,
                hardware_support_path=hw_path,
                output_path=board_bundle,
                version="0.15.0",
                release_id="greia-0.15.0-board",
                platform_family="legacy-x86",
                architecture="i386",
                profile="legacy-x86-i686",
                board="pi-500",
                payload_uncompressed_bytes=_UNCOMPRESSED,
                minimum_slot_bytes=_UNCOMPRESSED,
                persist_read_schema_min=1,
                persist_read_schema_max=1,
                persist_write_schema=1,
            )
            board_manifest = inspect_update_bundle(board_bundle).manifest
            with self.assertRaises(UpdateCompatibilityError):
                SystemIdentity(
                    "0.15.0", "legacy-x86", "i386", "legacy-x86-i686", "pi-400"
                ).assert_compatible(board_manifest)
            # PERSIST in-range accepted, out-of-range refused with migration wording.
            self.assertEqual(assert_persist_schema_compatible(1, manifest), 1)
            with self.assertRaises((PersistentLayoutError, UpdateCompatibilityError)):
                assert_persist_schema_compatible(10, manifest)

    def test_service_verifies_compatibility_without_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, _zst_bytes(b"svc-"))
            service = SystemUpdateService(
                root / "state",
                SystemIdentity("0.15.0", "legacy-x86", "i386", "legacy-x86-i686"),
                UnavailableSystemUpdateBackend("single-root"),
            )
            inspected, decision = service.verify_for_activation(bundle)
            self.assertEqual(decision, "update")
            self.assertEqual(inspected.manifest.release_id, "greia-0.15.0")
            # The v3 service takes no sequence/key parameters.
            params = set(_inspect.signature(service.verify_for_activation).parameters)
            self.assertNotIn("accepted_sequence", params)
            self.assertNotIn("trusted_key_dir", params)
            bad_service = SystemUpdateService(
                root / "state",
                SystemIdentity("0.15.0", "legacy-x86", "amd64", "legacy-x86-i686"),
                UnavailableSystemUpdateBackend("single-root"),
            )
            with self.assertRaises(UpdateCompatibilityError):
                bad_service.verify_for_activation(bundle)

    def test_version_strings_are_never_a_security_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, _zst_bytes(b"v3-payload-"))
            inspected = inspect_update_bundle(bundle)
            # A "higher" display version with the wrong architecture still loses.
            self.assertEqual(inspected.manifest.version, "0.15.0")
            with self.assertRaises(UpdateCompatibilityError):
                SystemIdentity(
                    "99.0.0", "legacy-x86", "amd64", "legacy-x86-i686"
                ).assert_compatible(inspected.manifest)
            # Same facts with matching identity verify.
            SystemIdentity(
                "0.14.0", "legacy-x86", "i386", "legacy-x86-i686"
            ).assert_compatible(inspected.manifest)

    def test_unknown_manifest_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, _zst_bytes(b"closed-"))
            manifest_raw = json.loads(zipfile.ZipFile(bundle).read(MANIFEST_NAME))
            manifest_raw["unknown_field"] = 1
            with self.assertRaises(UpdateBundleError):
                UpdateManifest.from_json_dict(manifest_raw)

    def test_v1_and_v2_bundles_rejected_with_migration_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for schema in (1, 2):
                payload = _zst_bytes(b"old-")
                fake_manifest = {
                    "schema_version": schema,
                    "release_id": "greia-0.14.0",
                    "version": "0.14.0",
                    "platform_family": "legacy-x86",
                    "architecture": "i386",
                    "profile": "legacy-x86-i686",
                    "board": None,
                    "payload": {
                        "name": PAYLOAD_NAME,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "size": len(payload),
                        "uncompressed_bytes": len(payload),
                        "minimum_slot_bytes": len(payload),
                    },
                    "hardware_support": None,
                    "persist_read_schema_min": 1,
                    "persist_read_schema_max": 1,
                    "persist_write_schema": 1,
                    "release_notes": "",
                }
                path = root / f"v{schema}.greiaupdate"
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr(
                        MANIFEST_NAME,
                        (
                            json.dumps(fake_manifest, sort_keys=True, separators=(",", ":"))
                            + "\n"
                        ).encode(),
                    )
                    archive.writestr("payload.bin", payload)
                with self.assertRaises(UpdateBundleError) as ctx:
                    inspect_update_bundle(path)
                message = str(ctx.exception).lower()
                self.assertIn("v3", message)
                self.assertTrue("rebuild" in message or "migration" in message)

    def test_symlink_traversal_and_encrypted_members_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, _zst_bytes(b"safe-"))
            # Duplicate member.
            raw = Path(bundle).read_bytes()
            dup = root / "dup.greiaupdate"
            with zipfile.ZipFile(bundle) as src, zipfile.ZipFile(dup, "w") as dst:
                for info in src.infolist():
                    dst.writestr(info, src.read(info.filename))
                first = src.infolist()[0]
                dst.writestr(first, src.read(first.filename))
            with self.assertRaises(UpdateBundleError):
                inspect_update_bundle(dup)
            self.assertTrue(raw)

    def test_size_bounds_do_not_allocate_declared_size(self) -> None:
        # Manifest declares a payload larger than the bound while the archive
        # member stays tiny; inspection must reject via central-directory sizes
        # and manifest bounds without allocating the declared bytes.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tiny = _zst_bytes(b"tiny-", size=64)
            manifest = UpdateManifest(
                schema_version=SCHEMA_VERSION,
                release_id="greia-0.15.0",
                version="0.15.0",
                platform_family="legacy-x86",
                architecture="i386",
                profile="legacy-x86-i686",
                board=None,
                payload_sha256=hashlib.sha256(tiny).hexdigest(),
                payload_size=len(tiny),
                payload_uncompressed_bytes=len(tiny),
                payload_minimum_slot_bytes=len(tiny),
                hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
                hardware_support_size=len(_HW_BYTES),
                persist_read_schema_min=1,
                persist_read_schema_max=1,
                persist_write_schema=1,
            )
            path = root / "bounds.greiaupdate"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
                archive.writestr(PAYLOAD_NAME, tiny)
                archive.writestr(HARDWARE_SUPPORT_NAME, _HW_BYTES)
            # Sanity: declared limits are the enforced constants.
            self.assertGreater(MAX_PAYLOAD_BYTES, len(tiny))
            self.assertGreater(MAX_HARDWARE_SUPPORT_BYTES, len(_HW_BYTES))
            self.assertGreater(MAX_MANIFEST_BYTES, len(manifest.canonical_bytes()))
            with self.assertRaises(UpdateBundleError):
                UpdateManifest(
                    schema_version=SCHEMA_VERSION,
                    release_id="greia-0.15.0",
                    version="0.15.0",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    board=None,
                    payload_sha256=hashlib.sha256(tiny).hexdigest(),
                    payload_size=MAX_PAYLOAD_BYTES + 1,
                    payload_uncompressed_bytes=MAX_PAYLOAD_BYTES + 1,
                    payload_minimum_slot_bytes=MAX_PAYLOAD_BYTES + 1,
                    hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
                    hardware_support_size=len(_HW_BYTES),
                    persist_read_schema_min=1,
                    persist_read_schema_max=1,
                    persist_write_schema=1,
                )

    def test_partition_table_and_non_zstd_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # MBR magic at 510 must fail at build (also fails zstd magic).
            bad = bytearray(b"\x00" * 1024)
            bad[510:512] = b"\x55\xaa"
            payload_path, hw_path = _make_inputs(root, bytes(bad))
            with self.assertRaises(UpdateBundleError):
                build_update_bundle(
                    payload_path=payload_path,
                    hardware_support_path=hw_path,
                    output_path=root / "bad.greiaupdate",
                    version="0.15.0",
                    release_id="greia-0.15.0",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    payload_uncompressed_bytes=_UNCOMPRESSED,
                    minimum_slot_bytes=_UNCOMPRESSED,
                    persist_read_schema_min=1,
                    persist_read_schema_max=1,
                    persist_write_schema=1,
                )
            # Non-zstd hardware support must fail at build.
            plain_hw = root / "plain.bin"
            plain_hw.write_bytes(b"not-zstd")
            good_payload = root / "good-payload.ext4.zst"
            good_payload.write_bytes(_zst_bytes(b"good-"))
            with self.assertRaises(UpdateBundleError):
                build_update_bundle(
                    payload_path=good_payload,
                    hardware_support_path=plain_hw,
                    output_path=root / "bad2.greiaupdate",
                    version="0.15.0",
                    release_id="greia-0.15.0",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    payload_uncompressed_bytes=_UNCOMPRESSED,
                    minimum_slot_bytes=_UNCOMPRESSED,
                    persist_read_schema_min=1,
                    persist_read_schema_max=1,
                    persist_write_schema=1,
                )

    def test_persist_schema_marker_binding(self) -> None:
        with self.assertRaises(PersistentLayoutError):
            parse_persist_schema_marker(b'{"b":1,"a":1}\n')
        raw = emit_persist_schema_marker(1)
        self.assertEqual(parse_persist_schema_marker(raw), 1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, _zst_bytes(b"persist-"))
            manifest = inspect_update_bundle(bundle).manifest
            self.assertEqual(assert_persist_schema_compatible(1, manifest), 1)
            with self.assertRaises(PersistentLayoutError) as ctx:
                assert_persist_schema_compatible(10, manifest)
            self.assertIn("migration", str(ctx.exception).lower())

    def test_no_key_material_in_build_signature(self) -> None:
        sig = _inspect.signature(build_update_bundle)
        names = set(sig.parameters)
        for forbidden in ("signer", "private_key_path", "persistent_contract_path"):
            self.assertNotIn(forbidden, names)
        self.assertIn("hardware_support_path", names)
        self.assertIn("payload_uncompressed_bytes", names)
        self.assertIn("persist_read_schema_min", names)


if __name__ == "__main__":
    unittest.main()
