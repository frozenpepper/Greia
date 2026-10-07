"""Teatrino custom-backdrop persistence, deduplication and cleanup."""
from __future__ import annotations

import hashlib
import unittest

from activities.teatrino_fiabe.teatrino_content import MAX_SAVED_SHOWS
from activities.teatrino_fiabe.teatrino_model import ShowRepository


class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}
        self.fail_kv = False

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_kv:
            raise RuntimeError("kv failed")
        self.kv[key] = value

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
        if prefix:
            names = [name for name in names if name.startswith(prefix)]
        return tuple(names)


class TeatrinoBackdropRepositoryTests(unittest.TestCase):
    def test_saved_show_keeps_verified_content_addressed_backdrop(self):
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        backdrop = b"custom-png"
        meta = repo.save_show(
            "cottage", [], [], [], 2.0, None, backdrop
        )
        digest = hashlib.sha256(backdrop).hexdigest()
        self.assertTrue(meta["has_custom_backdrop"])
        self.assertEqual(meta["backdrop_sha256"], digest)
        self.assertEqual(storage.files[f"backdrop_{digest}.png"], backdrop)
        self.assertEqual(repo.load_show_backdrop(meta["id"]), backdrop)

    def test_two_shows_share_one_blob_until_final_reference_is_deleted(self):
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        backdrop = b"same-picture"
        first = repo.save_show("cottage", [], [], [], 1.0, None, backdrop)
        second = repo.save_show("forest", [], [], [], 1.0, None, backdrop)
        backdrop_files = [
            name for name in storage.files if name.startswith("backdrop_")
        ]
        self.assertEqual(len(backdrop_files), 1)

        repo.delete_show(first["id"])
        self.assertEqual(len([
            name for name in storage.files if name.startswith("backdrop_")
        ]), 1)
        self.assertEqual(repo.load_show_backdrop(second["id"]), backdrop)

        repo.delete_show(second["id"])
        self.assertEqual([
            name for name in storage.files if name.startswith("backdrop_")
        ], [])

    def test_tampered_backdrop_fails_closed_to_builtin(self):
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        meta = repo.save_show(
            "cottage", [], [], [], 2.0, None, b"good"
        )
        name = repo._backdrop_name(meta["backdrop_sha256"])
        storage.files[name] = b"tampered"
        repo._mem_files.pop(name, None)
        self.assertIsNone(repo.load_show_backdrop(meta["id"]))

    def test_show_cap_reclaims_dropped_show_files_and_unreferenced_backdrop(self):
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        first = None
        for index in range(MAX_SAVED_SHOWS + 1):
            meta = repo.save_show(
                "cottage",
                [],
                [],
                [],
                1.0,
                b"RIFF" + bytes([index]),
                f"picture-{index}".encode(),
            )
            if index == 0:
                first = meta
        self.assertIsNotNone(first)
        first_id = first["id"]
        first_digest = first["backdrop_sha256"]
        self.assertFalse(any(
            item.get("id") == first_id for item in repo.list_shows()
        ))
        self.assertNotIn(repo._show_json_name(first_id), storage.files)
        self.assertNotIn(repo._show_wav_name(first_id), storage.files)
        self.assertNotIn(repo._backdrop_name(first_digest), storage.files)
        self.assertEqual(len([
            name for name in storage.files if name.startswith("backdrop_")
        ]), MAX_SAVED_SHOWS)

    def test_failed_index_commit_removes_unique_new_storage_files(self):
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        old = repo.save_show(
            "cottage", [], [], [], 1.0, None, b"existing"
        )
        old_digest = old["backdrop_sha256"]
        storage.fail_kv = True
        created = repo.save_show(
            "forest", [], [], [], 1.0, b"RIFF-new", b"new-unique"
        )
        storage.fail_kv = False
        self.assertIn(repo._backdrop_name(old_digest), storage.files)
        self.assertNotIn(repo._show_json_name(created["id"]), storage.files)
        self.assertNotIn(repo._show_wav_name(created["id"]), storage.files)
        self.assertNotIn(
            repo._backdrop_name(created["backdrop_sha256"]), storage.files
        )


if __name__ == "__main__":
    unittest.main()
