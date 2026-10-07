"""Pure, headless tests for profile-scoped shared creation repository primitives."""
from __future__ import annotations

import io
import tempfile
import unittest
import wave
from pathlib import Path

from PIL import Image
from greia_platform.creation_capacity import (
    CreationCapacityPolicy, CreationSpaceError, VolumeBudget, VolumeUsage,
)
from greia_platform.creation_media import CreationMediaError, CreationMediaRegistry
from greia_platform.creations import CreationLibrary, CreationLibraryError, CreationNotFound


def _png() -> bytes:
    with io.BytesIO() as target:
        Image.new("RGB", (800, 600), (40, 130, 210)).save(target, "PNG")
        return target.getvalue()


def _wav() -> bytes:
    with io.BytesIO() as target:
        with wave.open(target, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(22050)
            stream.writeframes(b"\0\0" * 22050)
        return target.getvalue()


class CreationCapacityTests(unittest.TestCase):
    def test_eight_gibibyte_volume_stops_growth_at_six_gibibytes_used(self):
        gib = 1024 ** 3
        policy = CreationCapacityPolicy()
        usage = VolumeUsage(total_bytes=8*gib, used_bytes=2*gib, free_bytes=6*gib)
        self.assertEqual(policy.remaining_growth_bytes(usage), 4*gib)
        policy.require_growth(usage, 4*gib)
        with self.assertRaises(CreationSpaceError):
            policy.require_growth(usage, 4*gib+1)

    def test_protects_small_volume_absolute_reserve(self):
        mib = 1024 ** 2
        usage = VolumeUsage(900*mib, 600*mib, 300*mib)
        self.assertEqual(CreationCapacityPolicy().remaining_growth_bytes(usage), 0)

    def test_rejects_invalid_data_and_ratios(self):
        with self.assertRaises(ValueError):
            VolumeUsage(10, 8, 8)
        with self.assertRaises(ValueError):
            CreationCapacityPolicy(maximum_used_fraction=1)


class CreationsTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        # Measured-volume probe is injectable; no dependency on host disk size.
        budget = VolumeBudget(probe=lambda _path: VolumeUsage(8*1024**3, 2*1024**3, 6*1024**3))
        self.library = CreationLibrary(self.root / "alice" / "creations", volume_budget=budget)

    def test_image_publish_large_preview_read_and_delete(self):
        original = _png()
        created = self.library.publish(original, producer_id="org.greia.painting", media_type="image/png", role="drawing")
        self.assertEqual(created.attributes, {"width":800,"height":600})
        self.assertEqual(self.library.list(media_type="image/png")[0].creation_id, created.creation_id)
        self.assertEqual(Image.open(io.BytesIO(self.library.read(created.creation_id))).size, (800,600))
        kind, preview = self.library.preview(created.creation_id)
        self.assertEqual(kind, "image/png")
        self.assertLessEqual(max(Image.open(io.BytesIO(preview)).size), 384)
        self.assertTrue(self.library.delete(created.creation_id))
        self.assertFalse(self.library.delete(created.creation_id))
        with self.assertRaises(CreationNotFound):
            self.library.read(created.creation_id)

    def test_audio_is_playable_before_selection(self):
        recording = self.library.publish(_wav(), producer_id="org.greia.voice", media_type="audio/wav", role="narration")
        typ, content = self.library.preview(recording.creation_id)
        self.assertEqual(typ, "audio/wav")
        with wave.open(io.BytesIO(content), "rb") as audio:
            self.assertEqual(audio.getframerate(), 22050)
            self.assertEqual(audio.getnframes(), 22050)

    def test_text_and_separate_profile_isolation(self):
        first = self.library.publish("hello world".encode(), producer_id="org.greia.writing", media_type="text/plain", role="story")
        second = CreationLibrary(self.root / "bob" / "creations", volume_budget=VolumeBudget(probe=lambda _: VolumeUsage(8*1024**3, 2*1024**3, 6*1024**3)))
        self.assertFalse(second.list())
        with self.assertRaises(CreationNotFound):
            second.read(first.creation_id)

    def test_invalid_format_and_unsupported_type_fail_closed(self):
        with self.assertRaises(CreationMediaError):
            self.library.publish(b"not an image", producer_id="org.greia.painting", media_type="image/png", role="drawing")
        with self.assertRaises(CreationMediaError):
            self.library.publish(b"something", producer_id="org.greia.painting", media_type="application/x-executable", role="drawing")
        with self.assertRaises(CreationMediaError):
            self.library.publish(b"\xff", producer_id="org.greia.writing", media_type="text/plain", role="story")
        self.assertEqual(self.library.list(), ())

    def test_immutable_snapshots_list_pagination_and_bad_ids(self):
        a = self.library.publish(b"one", producer_id="org.greia.writing", media_type="text/plain", role="story")
        b = self.library.publish(b"two", producer_id="org.greia.writing", media_type="text/plain", role="story")
        self.assertNotEqual(a.creation_id, b.creation_id)
        self.assertEqual(self.library.read(a.creation_id), b"one")
        self.assertEqual(self.library.read(b.creation_id), b"two")
        self.assertEqual(len(self.library.list(limit=1)), 1)
        self.assertEqual(len(self.library.list(limit=1, offset=1)), 1)
        with self.assertRaises(ValueError):
            self.library.read("../../anything")
        with self.assertRaises(ValueError):
            self.library.list(limit=90000)

    def test_corrupted_blob_is_rejected(self):
        record = self.library.publish(b"initial", producer_id="org.greia.writing", media_type="text/plain", role="story")
        blob = self.library.blobs / f"{record.creation_id}.txt"
        blob.write_bytes(b"tampered")
        with self.assertRaises(CreationLibraryError):
            self.library.read(record.creation_id)

    def test_blob_symlink_is_rejected(self):
        record = self.library.publish(b"original", producer_id="org.greia.writing", media_type="text/plain", role="story")
        blob = self.library.blobs / f"{record.creation_id}.txt"
        external = self.root / "untrusted.txt"
        external.write_bytes(b"external")
        blob.unlink()
        blob.symlink_to(external)
        with self.assertRaises(CreationLibraryError):
            self.library.read(record.creation_id)

    def test_volume_guard_refuses_write_without_evicting(self):
        blocked = CreationLibrary(self.root / "full" / "creations", volume_budget=VolumeBudget(
            probe=lambda _: VolumeUsage(900*1024**2, 600*1024**2, 300*1024**2)
        ))
        with self.assertRaises(CreationSpaceError):
            blocked.publish(b"first", producer_id="org.greia.writing", media_type="text/plain", role="story")
        self.assertEqual(blocked.list(), ())

    def test_symlink_root_is_refused(self):
        target = self.root / "actual"
        target.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(target, target_is_directory=True)
        with self.assertRaises(CreationLibraryError):
            CreationLibrary(alias)


if __name__ == "__main__":
    unittest.main()
