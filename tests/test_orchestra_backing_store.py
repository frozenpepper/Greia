"""Orchestra private backing-track storage contracts.

Execution is intentionally deferred to the accumulated desktop acceptance.
"""
from __future__ import annotations

import hashlib
import unittest

from activities.orchestra_animali.orchestra_backing import (
    BackingTrackRepository,
    BackingTrackStoreError,
)


class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}
        self.fail_get = False
        self.fail_set = False

    def kv_get(self, key, default=None):
        if self.fail_get:
            raise RuntimeError("read failed")
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_set:
            raise RuntimeError("write failed")
        self.kv[key] = value

    def kv_delete(self, key):
        return self.kv.pop(key, None) is not None

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None

    def file_list(self, prefix=None):
        names = sorted(self.files)
        if prefix is not None:
            names = [name for name in names if name.startswith(prefix)]
        return tuple(names)


class OrchestraBackingStoreTests(unittest.TestCase):
    def test_save_load_and_replace_are_content_addressed(self):
        storage = MemoryStorage()
        repo = BackingTrackRepository(storage)
        first = repo.save(
            b"RIFF-first",
            role="narration",
            title="Voice",
            duration_seconds=1.0,
        )
        first_name = repo._name(first.sha256)
        self.assertEqual(storage.files[first_name], b"RIFF-first")
        self.assertEqual(repo.load(), (first, b"RIFF-first"))

        second = repo.save(
            b"RIFF-second",
            role="song",
            title="Song",
            duration_seconds=2.0,
        )
        second_name = repo._name(second.sha256)
        self.assertNotIn(first_name, storage.files)
        self.assertEqual(storage.files[second_name], b"RIFF-second")
        self.assertEqual(repo.load(), (second, b"RIFF-second"))

    def test_failed_pointer_commit_preserves_previous_track(self):
        storage = MemoryStorage()
        repo = BackingTrackRepository(storage)
        previous = repo.save(
            b"RIFF-old",
            role="music",
            title="Old",
            duration_seconds=1.0,
        )
        before_files = dict(storage.files)
        before_kv = dict(storage.kv)

        storage.fail_set = True
        with self.assertRaises(BackingTrackStoreError):
            repo.save(
                b"RIFF-new",
                role="music",
                title="New",
                duration_seconds=1.0,
            )
        storage.fail_set = False

        self.assertEqual(storage.kv, before_kv)
        self.assertEqual(storage.files, before_files)
        self.assertEqual(repo.load()[0], previous)

    def test_unreadable_metadata_refuses_overwrite(self):
        storage = MemoryStorage()
        repo = BackingTrackRepository(storage)
        storage.fail_get = True
        with self.assertRaises(BackingTrackStoreError):
            repo.save(
                b"RIFF-new",
                role="narration",
                title="No",
                duration_seconds=1.0,
            )
        self.assertEqual(storage.files, {})

    def test_corrupt_blob_fails_closed(self):
        storage = MemoryStorage()
        repo = BackingTrackRepository(storage)
        record = repo.save(
            b"RIFF-good",
            role="narration",
            title="Voice",
            duration_seconds=1.0,
        )
        storage.files[repo._name(record.sha256)] = b"tampered"
        self.assertIsNone(repo.load())

    def test_clear_commits_pointer_removal_before_blob_delete(self):
        storage = MemoryStorage()
        repo = BackingTrackRepository(storage)
        record = repo.save(
            b"RIFF-good",
            role="music",
            title="Track",
            duration_seconds=1.0,
        )
        name = repo._name(record.sha256)
        self.assertTrue(repo.clear())
        self.assertNotIn(name, storage.files)
        self.assertIsNone(repo.load())


if __name__ == "__main__":
    unittest.main()
