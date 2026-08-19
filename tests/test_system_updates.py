from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from greia_platform.system_updates import (
    MANIFEST_NAME,
    PAYLOAD_NAME,
    SCHEMA_VERSION,
    SIGNATURE_NAME,
    SignatureEnvelope,
    SystemIdentity,
    SystemUpdateInbox,
    SystemUpdateService,
    UnavailableSystemUpdateBackend,
    UpdateBackendUnavailable,
    UpdateBundleError,
    UpdateCompatibilityError,
    UpdateManifest,
    UpdateSignatureError,
    build_update_bundle,
    generate_ed25519_keypair,
    inspect_update_bundle,
    verify_update_signature,
)


HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None


class SystemUpdateBundleTests(unittest.TestCase):
    def _manifest(self, payload: bytes) -> UpdateManifest:
        import hashlib

        return UpdateManifest(
            schema_version=SCHEMA_VERSION,
            release_id="greia-0.14.0",
            version="0.14.0",
            platform_family="legacy-x86",
            architecture="i386",
            profile="legacy-x86-i686",
            signer="greia-release-main",
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            payload_size=len(payload),
            release_notes="Emoji and update plumbing.",
        )

    def _unsigned_structurally_valid_bundle(self, root: Path, payload: bytes) -> Path:
        manifest = self._manifest(payload)
        signature = SignatureEnvelope(
            schema_version=SCHEMA_VERSION,
            algorithm="ed25519",
            signer=manifest.signer,
            signature=b"x" * 64,
        )
        path = root / "candidate.greiaupdate"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
            archive.writestr(SIGNATURE_NAME, signature.as_json_bytes())
            archive.writestr(PAYLOAD_NAME, payload)
        return path

    def test_inspection_binds_payload_to_manifest_without_granting_trust(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._unsigned_structurally_valid_bundle(root, b"slot-image")
            inspected = inspect_update_bundle(bundle)
            self.assertEqual(inspected.manifest.version, "0.14.0")
            self.assertEqual(inspected.manifest.payload_size, len(b"slot-image"))
            self.assertEqual(inspected.signature.signature, b"x" * 64)

    def test_tampered_payload_is_rejected_before_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"slot-image"
            manifest = self._manifest(payload)
            signature = SignatureEnvelope(
                SCHEMA_VERSION, "ed25519", manifest.signer, b"x" * 64
            )
            path = root / "tampered.greiaupdate"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
                archive.writestr(SIGNATURE_NAME, signature.as_json_bytes())
                archive.writestr(PAYLOAD_NAME, b"changed!!!")
            with self.assertRaises(UpdateBundleError):
                inspect_update_bundle(path)

    def test_extra_or_reordered_members_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"slot"
            manifest = self._manifest(payload)
            signature = SignatureEnvelope(
                SCHEMA_VERSION, "ed25519", manifest.signer, b"x" * 64
            )
            path = root / "bad.greiaupdate"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
                archive.writestr("extra.txt", b"no")
                archive.writestr(SIGNATURE_NAME, signature.as_json_bytes())
                archive.writestr(PAYLOAD_NAME, payload)
            with self.assertRaises(UpdateBundleError):
                inspect_update_bundle(path)

    def test_inbox_receives_bounded_bytes_but_does_not_claim_signature_or_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._unsigned_structurally_valid_bundle(root, b"slot-image")
            inbox = SystemUpdateInbox(root / "state")
            queued = inbox.receive(bundle)
            self.assertTrue(queued.path.is_file())
            status = inbox.status_payload()
            self.assertEqual(status["state"], "received")
            self.assertFalse(status["signature_verified"])
            self.assertFalse(status["activation_available"])
            self.assertNotIn("bundle_path", status)

    def test_current_unavailable_backend_never_falls_back_to_active_root(self) -> None:
        backend = UnavailableSystemUpdateBackend("single-root layout")
        self.assertFalse(backend.available)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self._unsigned_structurally_valid_bundle(root, b"slot-image")
            service = SystemUpdateService(
                root / "state",
                root / "keys",
                SystemIdentity("0.13.0", "legacy-x86", "i386", "legacy-x86-i686"),
                backend,
            )
            # Trust verification runs before backend authority. A fake signature
            # must therefore fail rather than reaching any destructive fallback.
            with self.assertRaises(UpdateSignatureError):
                service.stage(bundle)
            with self.assertRaises(UpdateBackendUnavailable):
                backend.stage(inspect_update_bundle(bundle))

    def test_system_identity_requires_exact_family_architecture_and_profile(self) -> None:
        manifest = self._manifest(b"slot")
        SystemIdentity(
            "0.13.0", "legacy-x86", "i386", "legacy-x86-i686"
        ).assert_compatible(manifest)
        with self.assertRaises(UpdateCompatibilityError):
            SystemIdentity(
                "0.13.0", "legacy-x86", "amd64", "legacy-x86-i686"
            ).assert_compatible(manifest)
        with self.assertRaises(UpdateCompatibilityError):
            SystemIdentity().assert_compatible(manifest)

    @unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is optional until R13B package set is enabled")
    def test_keygen_build_and_signature_verification_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "private.pem"
            public = root / "public.pem"
            generate_ed25519_keypair(private, public)
            self.assertEqual(private.stat().st_mode & 0o777, 0o600)
            payload = root / "slot.img"
            payload.write_bytes(b"a complete slot image\0" * 1024)
            bundle = root / "release.greiaupdate"
            manifest = build_update_bundle(
                payload_path=payload,
                output_path=bundle,
                version="0.14.0",
                release_id="greia-0.14.0",
                platform_family="legacy-x86",
                architecture="i386",
                profile="legacy-x86-i686",
                signer="greia-release-main",
                private_key_path=private,
                release_notes="Test release",
            )
            key_dir = root / "trusted"
            key_dir.mkdir()
            (key_dir / f"{manifest.signer}.pem").write_bytes(public.read_bytes())
            inspected = inspect_update_bundle(bundle)
            verify_update_signature(inspected, key_dir)

    @unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is optional until R13B package set is enabled")
    def test_wrong_trusted_key_rejects_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "private.pem"
            public = root / "public.pem"
            wrong_private = root / "wrong-private.pem"
            wrong_public = root / "wrong-public.pem"
            generate_ed25519_keypair(private, public)
            generate_ed25519_keypair(wrong_private, wrong_public)
            payload = root / "slot.img"
            payload.write_bytes(b"slot")
            bundle = root / "release.greiaupdate"
            manifest = build_update_bundle(
                payload_path=payload,
                output_path=bundle,
                version="0.14.0",
                release_id="greia-0.14.0",
                platform_family="legacy-x86",
                architecture="i386",
                profile="legacy-x86-i686",
                signer="greia-release-main",
                private_key_path=private,
            )
            key_dir = root / "trusted"
            key_dir.mkdir()
            (key_dir / f"{manifest.signer}.pem").write_bytes(wrong_public.read_bytes())
            with self.assertRaises(UpdateSignatureError):
                verify_update_signature(inspect_update_bundle(bundle), key_dir)


if __name__ == "__main__":
    unittest.main()
