"""Focused v3 bundle proof (T01 acceptance).

Builds synthetic v3 bundles with no key material, round-trips through build
and inspect, proves ZIP_STORED for .zst members, optional hardware-support,
explicit v2/v1 migration rejection, manifest bound validation, and digest
mismatch failure. Does not migrate the wider suites (T04/T05 own them).
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from greia_platform.system_updates import (
    HARDWARE_SUPPORT_NAME,
    MANIFEST_NAME,
    PAYLOAD_NAME,
    SCHEMA_VERSION,
    UpdateBundleError,
    UpdateManifest,
    build_update_bundle,
    inspect_update_bundle,
)

_ZSTD = b"\x28\xb5\x2f\xfd"


def _zst_bytes(seed: bytes, size: int = 4096) -> bytes:
    assert size > 4
    body = (seed * ((size // len(seed)) + 1))[: size - 4]
    return _ZSTD + body


class V3BundleProofTests(unittest.TestCase):
    def _build(self, root: Path, *, with_hw: bool, board=None) -> Path:
        payload = _zst_bytes(b"v3-payload-")
        hw = _zst_bytes(b"v3-hwset-") if with_hw else None
        payload_path = root / "payload.ext4.zst"
        payload_path.write_bytes(payload)
        hw_path = None
        if hw is not None:
            hw_path = root / "hardware-support.tar.zst"
            hw_path.write_bytes(hw)
        out = root / ("with-hw.greiaupdate" if with_hw else "no-hw.greiaupdate")
        build_update_bundle(
            payload_path=payload_path,
            hardware_support_path=hw_path,
            output_path=out,
            version="0.15.0",
            release_id="greia-0.15.0",
            platform_family="legacy-x86",
            architecture="i386",
            profile="legacy-x86-i686",
            board=board,
            payload_uncompressed_bytes=8 * 1024 * 1024,
            minimum_slot_bytes=8 * 1024 * 1024,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
            release_notes="v3 proof",
        )
        return out

    def test_v3_round_trip_without_hw_and_stored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, with_hw=False)
            inspected = inspect_update_bundle(bundle)
            self.assertEqual(inspected.manifest.schema_version, 3)
            self.assertEqual(inspected.manifest.schema_version, SCHEMA_VERSION)
            self.assertIsNone(inspected.manifest.hardware_support_sha256)
            with zipfile.ZipFile(bundle, "r") as archive:
                names = [i.filename for i in archive.infolist()]
                self.assertEqual(names, [MANIFEST_NAME, PAYLOAD_NAME])
                for info in archive.infolist():
                    if info.filename.endswith(".zst"):
                        self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_v3_round_trip_with_hw_stored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, with_hw=True, board="pi-500")
            inspected = inspect_update_bundle(bundle)
            self.assertEqual(inspected.manifest.board, "pi-500")
            self.assertIsNotNone(inspected.manifest.hardware_support_sha256)
            with zipfile.ZipFile(bundle, "r") as archive:
                names = [i.filename for i in archive.infolist()]
                self.assertEqual(
                    names, [MANIFEST_NAME, PAYLOAD_NAME, HARDWARE_SUPPORT_NAME]
                )
                for info in archive.infolist():
                    if info.filename.endswith(".zst"):
                        self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_old_signed_layout_rejected_with_migration_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Minimal old signed v2-shaped layout (member names + schema 2).
            manifest = {
                "schema_version": 2,
                "release_id": "greia-0.14.0",
                "version": "0.14.0",
                "platform_family": "legacy-x86",
                "architecture": "i386",
                "profile": "legacy-x86-i686",
                "signer": "greia-release-main",
                "payload": {
                    "name": "payload.bin",
                    "sha256": "0" * 64,
                    "size": 4,
                    "kind": "system-slot-image",
                    "filesystem_bytes": 4,
                    "minimum_slot_bytes": 4,
                },
                "hardware_support": {
                    "name": HARDWARE_SUPPORT_NAME,
                    "schema_version": 1,
                    "sha256": "1" * 64,
                    "size": 4,
                },
                "persistent_state_contract": {
                    "name": "persistent-state-contract.json",
                    "schema_version": 1,
                    "sha256": "2" * 64,
                    "size": 4,
                },
                "release_notes": "",
            }
            raw = (
                json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode()
            path = root / "old.greiaupdate"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(MANIFEST_NAME, raw)
                archive.writestr("manifest.sig", b"{}")
                archive.writestr("payload.bin", b"data")
                archive.writestr(HARDWARE_SUPPORT_NAME, _zst_bytes(b"x"))
                archive.writestr("persistent-state-contract.json", b"{}")
            with self.assertRaises(UpdateBundleError) as ctx:
                inspect_update_bundle(path)
            message = str(ctx.exception).lower()
            self.assertIn("v3", message)
            self.assertTrue("rebuild" in message or "migration" in message)

    def test_manifest_rejects_unknown_missing_and_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, with_hw=False)
            with zipfile.ZipFile(bundle, "r") as archive:
                base = json.loads(archive.read(MANIFEST_NAME).decode())
        # Unknown field.
        bad = dict(base)
        bad["extra"] = 1
        with self.assertRaises(UpdateBundleError):
            UpdateManifest.from_json_dict(bad)
        # Missing field.
        bad = dict(base)
        del bad["board"]
        with self.assertRaises(UpdateBundleError):
            UpdateManifest.from_json_dict(bad)
        # Out-of-bounds: inverted PERSIST range.
        bad = dict(base)
        bad["persist_read_schema_min"] = 5
        bad["persist_read_schema_max"] = 2
        with self.assertRaises(UpdateBundleError):
            UpdateManifest.from_json_dict(bad)
        # Out-of-bounds: bad board.
        bad = dict(base)
        bad["board"] = "bad board!"
        with self.assertRaises(UpdateBundleError):
            UpdateManifest.from_json_dict(bad)
        # None board is accepted.
        good = dict(base)
        good["board"] = None
        UpdateManifest.from_json_dict(good)

    def test_digest_mismatch_fails_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, with_hw=False)
            tampered = root / "tampered.greiaupdate"
            with zipfile.ZipFile(bundle, "r") as src:
                manifest_raw = src.read(MANIFEST_NAME)
                payload = bytearray(src.read(PAYLOAD_NAME))
            payload[10] ^= 0xFF
            with zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as dst:
                info = zipfile.ZipInfo(
                    filename=MANIFEST_NAME, date_time=(1980, 1, 1, 0, 0, 0)
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                dst.writestr(info, manifest_raw)
                info2 = zipfile.ZipInfo(
                    filename=PAYLOAD_NAME, date_time=(1980, 1, 1, 0, 0, 0)
                )
                info2.compress_type = zipfile.ZIP_STORED
                dst.writestr(info2, bytes(payload))
            with self.assertRaises(UpdateBundleError) as ctx:
                inspect_update_bundle(tampered)
            self.assertIn("digest", str(ctx.exception).lower())

    def test_no_key_material_in_build_signature(self) -> None:
        import inspect as _inspect

        sig = _inspect.signature(build_update_bundle)
        names = set(sig.parameters)
        for forbidden in (
            "signer",
            "private_key_path",
            "release_sequence",
            "persistent_contract_path",
        ):
            self.assertNotIn(forbidden, names)
        self.assertIn("hardware_support_path", names)
        self.assertIn("payload_uncompressed_bytes", names)


if __name__ == "__main__":
    unittest.main()
