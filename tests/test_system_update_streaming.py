from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from greia_platform.system_updates import (
    HARDWARE_SUPPORT_NAME,
    MANIFEST_NAME,
    MIN_INBOX_FREE_BYTES,
    PAYLOAD_NAME,
    PERSISTENT_CONTRACT_NAME,
    SCHEMA_VERSION,
    SIGNATURE_NAME,
    SignatureEnvelope,
    SystemUpdateInbox,
    UpdateBundleError,
    UpdateManifest,
    build_persistent_state_contract_bytes,
)


_HW_BYTES = b"\x28\xb5\x2f\xfd" + b"hwset" * 32
_CONTRACT_BYTES = build_persistent_state_contract_bytes()


class SystemUpdateStreamingTests(unittest.TestCase):
    def _bundle(self, root: Path) -> Path:
        payload = b"synthetic-slot-image" * 64
        hw_sha = hashlib.sha256(_HW_BYTES).hexdigest()
        contract_sha = hashlib.sha256(_CONTRACT_BYTES).hexdigest()
        manifest = UpdateManifest(
            schema_version=SCHEMA_VERSION,
            release_id="greia-0.14.0",
            version="0.14.0",
            release_sequence=7,
            platform_family="legacy-x86",
            architecture="i386",
            profile="legacy-x86-i686",
            signer="greia-release-main",
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            payload_size=len(payload),
            payload_filesystem_bytes=len(payload),
            payload_minimum_slot_bytes=len(payload),
            hardware_support_name=HARDWARE_SUPPORT_NAME,
            hardware_support_schema_version=1,
            hardware_support_sha256=hw_sha,
            hardware_support_size=len(_HW_BYTES),
            persistent_contract_schema_version=1,
            persistent_contract_sha256=contract_sha,
            persistent_contract_size=len(_CONTRACT_BYTES),
        )
        signature = SignatureEnvelope(
            schema_version=SCHEMA_VERSION,
            algorithm="ed25519",
            signer=manifest.signer,
            signature=b"x" * 64,
        )
        path = root / "source.greiaupdate"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
            archive.writestr(SIGNATURE_NAME, signature.as_json_bytes())
            archive.writestr(PAYLOAD_NAME, payload)
            archive.writestr(HARDWARE_SUPPORT_NAME, _HW_BYTES)
            archive.writestr(PERSISTENT_CONTRACT_NAME, _CONTRACT_BYTES)
        return path

    def test_stream_staging_publishes_same_inode_without_second_local_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._bundle(root)
            inbox = SystemUpdateInbox(root / "state")
            staging = inbox.create_receive_staging(source.stat().st_size)
            staging.write_bytes(source.read_bytes())
            staged_stat = staging.stat()

            queued = inbox.receive_staged(staging)
            queued_stat = queued.path.stat()

            self.assertEqual(staged_stat.st_dev, queued_stat.st_dev)
            self.assertEqual(staged_stat.st_ino, queued_stat.st_ino)
            self.assertTrue(staging.exists())
            staging.unlink()
            self.assertTrue(queued.path.is_file())
            self.assertEqual(len(list(inbox.inbox_dir.glob("*.greiaupdate"))), 1)

    def test_receive_staged_rejects_file_outside_owned_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._bundle(root)
            inbox = SystemUpdateInbox(root / "state")
            inbox.inbox_dir.mkdir(parents=True)
            with self.assertRaisesRegex(UpdateBundleError, "regular inbox file"):
                inbox.receive_staged(source)

    def test_receive_staging_reserves_space_before_streaming(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = SystemUpdateInbox(root / "state")

            class Usage:
                total = 10_000
                used = 9_000
                free = MIN_INBOX_FREE_BYTES

            with patch(
                "greia_platform.system_updates.shutil.disk_usage",
                return_value=Usage(),
            ):
                with self.assertRaisesRegex(UpdateBundleError, "not enough free space"):
                    inbox.create_receive_staging(1)


if __name__ == "__main__":
    unittest.main()
