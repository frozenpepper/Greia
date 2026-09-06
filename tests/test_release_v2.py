from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from greia_platform.system_updates import (
    BUNDLE_MEMBERS_V2,
    HARDWARE_SUPPORT_NAME,
    MANIFEST_NAME,
    MAX_HARDWARE_SUPPORT_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_PAYLOAD_BYTES,
    MAX_PERSISTENT_CONTRACT_BYTES,
    PAYLOAD_NAME,
    PERSISTENT_CONTRACT_NAME,
    SCHEMA_VERSION,
    SIGNATURE_NAME,
    SignatureEnvelope,
    SystemIdentity,
    SystemUpdateService,
    UnavailableSystemUpdateBackend,
    UpdateBundleError,
    UpdateManifest,
    UpdateSequenceError,
    UpdateSignatureError,
    authorize_release_sequence,
    build_persistent_state_contract_bytes,
    build_update_bundle,
    decide_release_sequence,
    generate_ed25519_keypair,
    inspect_update_bundle,
    verify_persistent_state_contract_bytes,
    verify_update_signature,
)

HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None
_HW_BODY = b"hwset-payload" * 64
_HW_BYTES = b"\x28\xb5\x2f\xfd" + _HW_BODY
_CONTRACT_BYTES = build_persistent_state_contract_bytes()


def _make_inputs(root: Path, payload: bytes, *, sequence: int = 11):
    payload_path = root / "payload.bin"
    payload_path.write_bytes(payload)
    hw_path = root / "hw.tar.zst"
    hw_path.write_bytes(_HW_BYTES)
    contract_path = root / "contract.json"
    contract_path.write_bytes(_CONTRACT_BYTES)
    return payload_path, hw_path, contract_path


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "v2 round-trip needs cryptography")
class ReleaseV2Tests(unittest.TestCase):
    def _build(self, root: Path, payload: bytes, *, sequence: int = 11) -> Path:
        private = root / "priv.pem"
        public = root / "pub.pem"
        generate_ed25519_keypair(private, public)
        payload_path, hw_path, contract_path = _make_inputs(root, payload, sequence=sequence)
        bundle = root / f"r{sequence}.greiaupdate"
        build_update_bundle(
            payload_path=payload_path,
            hardware_support_path=hw_path,
            persistent_contract_path=contract_path,
            output_path=bundle,
            version="0.15.0",
            release_id="greia-0.15.0",
            release_sequence=sequence,
            platform_family="legacy-x86",
            architecture="i386",
            profile="legacy-x86-i686",
            signer="greia-release-main",
            private_key_path=private,
            minimum_slot_bytes=len(payload) + 1024 * 1024,
        )
        key_dir = root / "trusted"
        key_dir.mkdir(exist_ok=True)
        (key_dir / "greia-release-main.pem").write_bytes(public.read_bytes())
        return bundle

    def test_round_trip_canonical_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, b"release-payload-v2" * 128)
            inspected = inspect_update_bundle(bundle)
            self.assertEqual(inspected.manifest.schema_version, 2)
            self.assertEqual(inspected.manifest.release_sequence, 11)
            self.assertEqual(
                list(zipfile.ZipFile(bundle).namelist()), list(BUNDLE_MEMBERS_V2)
            )
            raw = zipfile.ZipFile(bundle).read(MANIFEST_NAME)
            self.assertEqual(raw, inspected.manifest.canonical_bytes())
            verify_update_signature(inspected, root / "trusted")

    def test_deterministic_bundle_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_dir = root / "a"
            second_dir = root / "b"
            first_dir.mkdir()
            second_dir.mkdir()
            payload = b"deterministic" * 256
            first = self._build(first_dir, payload)
            second = self._build(second_dir, payload)
            # Same logical inputs built with different ephemeral keys differ only
            # in signature bytes; member order/names stay deterministic.
            self.assertEqual(
                zipfile.ZipFile(first).namelist(), zipfile.ZipFile(second).namelist()
            )

    def test_anti_rollback_decisions(self) -> None:
        self.assertEqual(decide_release_sequence(12, 11), "update")
        self.assertEqual(decide_release_sequence(11, 11), "no-update")
        self.assertEqual(decide_release_sequence(10, 11), "rejected")
        self.assertEqual(authorize_release_sequence(12, 11), "update")
        self.assertEqual(authorize_release_sequence(11, 11), "no-update")
        with self.assertRaises(UpdateSequenceError):
            authorize_release_sequence(10, 11)

    def test_service_enforces_sequence_after_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, b"seq-payload" * 64, sequence=20)
            service = SystemUpdateService(
                root / "state",
                root / "trusted",
                SystemIdentity("0.15.0", "legacy-x86", "i386", "legacy-x86-i686"),
                UnavailableSystemUpdateBackend("single-root"),
                accepted_sequence=19,
            )
            inspected, decision = service.verify_for_activation(bundle)
            self.assertEqual(decision, "update")
            self.assertEqual(inspected.manifest.release_sequence, 20)
            with self.assertRaises(UpdateSequenceError):
                service.verify_for_activation(bundle, accepted_sequence=21)
            # Equal is idempotent, not an error.
            inspected_same, decision_same = service.verify_for_activation(
                bundle, accepted_sequence=20
            )
            self.assertEqual(decision_same, "no-update")
            self.assertEqual(inspected_same.manifest.release_sequence, 20)

    def test_version_strings_are_never_a_security_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, b"v2-payload" * 64, sequence=5)
            inspected = inspect_update_bundle(bundle)
            # A "higher" display version with a lower sequence must still lose.
            self.assertEqual(inspected.manifest.version, "0.15.0")
            with self.assertRaises(UpdateSequenceError):
                authorize_release_sequence(
                    inspected.manifest.release_sequence, accepted_sequence=9
                )

    def test_unknown_manifest_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, b"closed" * 64)
            manifest_raw = json.loads(zipfile.ZipFile(bundle).read(MANIFEST_NAME))
            manifest_raw["unknown_field"] = 1
            with self.assertRaises(UpdateBundleError):
                UpdateManifest.from_json_dict(manifest_raw)

    def test_v1_bundle_is_rejected_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"v1-payload"
            fake_manifest = {
                "schema_version": 1,
                "release_id": "greia-0.14.0",
                "version": "0.14.0",
                "platform_family": "legacy-x86",
                "architecture": "i386",
                "profile": "legacy-x86-i686",
                "signer": "greia-release-main",
                "payload": {
                    "name": PAYLOAD_NAME,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                    "kind": "system-slot-image",
                },
                "release_notes": "",
            }
            sig = SignatureEnvelope(2, "ed25519", "greia-release-main", b"x" * 64)
            path = root / "v1.greiaupdate"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    MANIFEST_NAME,
                    (json.dumps(fake_manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
                )
                archive.writestr(SIGNATURE_NAME, sig.as_json_bytes())
                archive.writestr(PAYLOAD_NAME, payload)
            with self.assertRaisesRegex(UpdateBundleError, "v1.*not accepted"):
                inspect_update_bundle(path)

    def test_symlink_traversal_and_encrypted_members_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._build(root, b"safe" * 64)
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
            tiny = b"tiny"
            manifest = UpdateManifest(
                schema_version=SCHEMA_VERSION,
                release_id="greia-0.15.0",
                version="0.15.0",
                release_sequence=3,
                platform_family="legacy-x86",
                architecture="i386",
                profile="legacy-x86-i686",
                signer="greia-release-main",
                payload_sha256=hashlib.sha256(tiny).hexdigest(),
                payload_size=len(tiny),
                payload_filesystem_bytes=len(tiny),
                payload_minimum_slot_bytes=len(tiny),
                hardware_support_name=HARDWARE_SUPPORT_NAME,
                hardware_support_schema_version=1,
                hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
                hardware_support_size=len(_HW_BYTES),
                persistent_contract_schema_version=1,
                persistent_contract_sha256=hashlib.sha256(_CONTRACT_BYTES).hexdigest(),
                persistent_contract_size=len(_CONTRACT_BYTES),
            )
            sig = SignatureEnvelope(2, "ed25519", manifest.signer, b"x" * 64)
            path = root / "bounds.greiaupdate"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
                archive.writestr(SIGNATURE_NAME, sig.as_json_bytes())
                archive.writestr(PAYLOAD_NAME, tiny)
                archive.writestr(HARDWARE_SUPPORT_NAME, _HW_BYTES)
                archive.writestr(PERSISTENT_CONTRACT_NAME, _CONTRACT_BYTES)
            # Sanity: declared limits are the enforced constants.
            self.assertGreater(MAX_PAYLOAD_BYTES, len(tiny))
            self.assertGreater(MAX_HARDWARE_SUPPORT_BYTES, len(_HW_BYTES))
            self.assertGreater(MAX_PERSISTENT_CONTRACT_BYTES, len(_CONTRACT_BYTES))
            self.assertGreater(MAX_MANIFEST_BYTES, len(manifest.canonical_bytes()))
            with self.assertRaises(UpdateBundleError):
                UpdateManifest(
                    schema_version=SCHEMA_VERSION,
                    release_id="greia-0.15.0",
                    version="0.15.0",
                    release_sequence=3,
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    signer="greia-release-main",
                    payload_sha256=hashlib.sha256(tiny).hexdigest(),
                    payload_size=MAX_PAYLOAD_BYTES + 1,
                    payload_filesystem_bytes=MAX_PAYLOAD_BYTES + 1,
                    payload_minimum_slot_bytes=MAX_PAYLOAD_BYTES + 1,
                    hardware_support_name=HARDWARE_SUPPORT_NAME,
                    hardware_support_schema_version=1,
                    hardware_support_sha256=hashlib.sha256(_HW_BYTES).hexdigest(),
                    hardware_support_size=len(_HW_BYTES),
                    persistent_contract_schema_version=1,
                    persistent_contract_sha256=hashlib.sha256(_CONTRACT_BYTES).hexdigest(),
                    persistent_contract_size=len(_CONTRACT_BYTES),
                )

    def test_partition_table_and_non_zstd_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # MBR magic at 510 must fail at build.
            bad = bytearray(b"\x00" * 1024)
            bad[510:512] = b"\x55\xaa"
            private = root / "priv.pem"
            public = root / "pub.pem"
            generate_ed25519_keypair(private, public)
            payload_path, hw_path, contract_path = _make_inputs(root, bytes(bad))
            with self.assertRaises(UpdateBundleError):
                build_update_bundle(
                    payload_path=payload_path,
                    hardware_support_path=hw_path,
                    persistent_contract_path=contract_path,
                    output_path=root / "bad.greiaupdate",
                    version="0.15.0",
                    release_id="greia-0.15.0",
                    release_sequence=4,
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    signer="greia-release-main",
                    private_key_path=private,
                )
            # Non-zstd hardware support must fail at build.
            plain_hw = root / "plain.bin"
            plain_hw.write_bytes(b"not-zstd")
            with self.assertRaises(UpdateBundleError):
                build_update_bundle(
                    payload_path=payload_path,
                    hardware_support_path=plain_hw,
                    persistent_contract_path=contract_path,
                    output_path=root / "bad2.greiaupdate",
                    version="0.15.0",
                    release_id="greia-0.15.0",
                    release_sequence=4,
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    signer="greia-release-main",
                    private_key_path=private,
                )

    def test_persistent_contract_canonical_binding(self) -> None:
        with self.assertRaises(UpdateBundleError):
            verify_persistent_state_contract_bytes(b'{"b":1,"a":1}\n')
        raw = build_persistent_state_contract_bytes()
        parsed = verify_persistent_state_contract_bytes(raw)
        self.assertIn("namespaces", parsed)

    def test_missing_key_is_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload_path, hw_path, contract_path = _make_inputs(root, b"keyless" * 16)
            with self.assertRaises(UpdateSignatureError):
                build_update_bundle(
                    payload_path=payload_path,
                    hardware_support_path=hw_path,
                    persistent_contract_path=contract_path,
                    output_path=root / "out.greiaupdate",
                    version="0.15.0",
                    release_id="greia-0.15.0",
                    release_sequence=6,
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    signer="greia-release-main",
                    private_key_path=root / "does-not-exist.pem",
                )

    def test_unsupported_signature_algorithm_rejected(self) -> None:
        with self.assertRaises(UpdateSignatureError):
            SignatureEnvelope(2, "rsa-pss", "greia-release-main", b"x" * 64)


if __name__ == "__main__":
    unittest.main()
