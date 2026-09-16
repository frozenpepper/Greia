from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from greia_platform.system_updates import (
    HARDWARE_SUPPORT_NAME,
    INBOX_CANDIDATE_NAME,
    MANIFEST_NAME,
    MIN_INBOX_FREE_BYTES,
    PAYLOAD_NAME,
    SCHEMA_VERSION,
    SystemUpdateInbox,
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


_HW_BYTES = _zst_bytes(b"hwset-", size=2048)
_UNCOMPRESSED = 8 * 1024 * 1024


class SystemUpdateStreamingTests(unittest.TestCase):
    def _bundle(self, root: Path) -> Path:
        payload = _zst_bytes(b"synthetic-slot-image-")
        payload_path = root / "payload.ext4.zst"
        payload_path.write_bytes(payload)
        hw_path = root / "hw.tar.zst"
        hw_path.write_bytes(_HW_BYTES)
        out = root / "source.greiaupdate"
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
        )
        return out

    def test_stream_staging_publishes_via_atomic_rename_without_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._bundle(root)
            inbox = SystemUpdateInbox(root / "state")
            staging = inbox.create_receive_staging(source.stat().st_size)
            staging.write_bytes(source.read_bytes())
            staged_stat = staging.stat()

            queued = inbox.receive_staged(staging)
            queued_stat = queued.path.stat()

            self.assertEqual(queued.path.name, INBOX_CANDIDATE_NAME)
            self.assertEqual(staged_stat.st_dev, queued_stat.st_dev)
            self.assertEqual(staged_stat.st_ino, queued_stat.st_ino)
            # The temporary is consumed by the atomic rename: only the
            # fixed candidate remains, no second local copy.
            self.assertFalse(staging.exists())
            self.assertTrue(queued.path.is_file())
            self.assertEqual(len(list(inbox.inbox_dir.glob("*.greiaupdate"))), 1)
            inspected = inspect_update_bundle(queued.path)
            self.assertEqual(inspected.manifest.schema_version, SCHEMA_VERSION)

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

    def test_old_signed_staging_rejected_with_migration_message(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = SystemUpdateInbox(root / "state")
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
            fake = root / "fake.greiaupdate"
            with zipfile.ZipFile(fake, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(
                    MANIFEST_NAME,
                    (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
                )
                archive.writestr("manifest.sig", b"{}")
                archive.writestr("payload.bin", b"data")
            staging = inbox.create_receive_staging(fake.stat().st_size)
            staging.write_bytes(fake.read_bytes())
            with self.assertRaises(UpdateBundleError) as ctx:
                inbox.receive_staged(staging)
            message = str(ctx.exception).lower()
            self.assertIn("v3", message)
            self.assertTrue("rebuild" in message or "migration" in message)


if __name__ == "__main__":
    unittest.main()
