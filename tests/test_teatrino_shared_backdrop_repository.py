"""Teatrino custom-backdrop persistence and cleanup contracts."""
from __future__ import annotations

import hashlib
import unittest

from activities.teatrino_fiabe.teatrino_model import ShowRepository


class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = value

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class TeatrinoBackdropRepositoryTests(unittest.TestCase):
    def test_saved_show_keeps_verified_custom_backdrop(self):
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        backdrop = b"custom-png"
        meta = repo.save_show(
            "cottage", [], [], [], 2.0, None, backdrop
        )
        self.assertTrue(meta["has_custom_backdrop"])
        self.assertEqual(
            meta["backdrop_sha256"], hashlib.sha256(backdrop).hexdigest()
        )
        self.assertEqual(repo.load_show_backdrop(meta["id"]), backdrop)

    def test_tampered_backdrop_fails_closed_to_builtin(self):
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        meta = repo.save_show(
            "cottage", [], [], [], 2.0, None, b"good"
        )
        storage.files[f"show_{meta['id']}_backdrop.png"] = b"tampered"
        repo._mem_files.pop(f"show_{meta['id']}_backdrop.png", None)
        self.assertIsNone(repo.load_show_backdrop(meta["id"]))

    def test_memory_cleanup_helper_is_bounded_and_nonrecursive(self):
        repo = ShowRepository(None)
        repo._mem_files = {
            "show_demo.json": b"{}",
            "show_demo.wav": b"RIFF",
            "show_demo_backdrop.png": b"png",
            "unrelated": b"keep",
        }
        repo._delete_mem_files("demo")
        self.assertEqual(repo._mem_files, {"unrelated": b"keep"})

    def test_delete_reclaims_json_audio_and_backdrop(self):
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        meta = repo.save_show(
            "forest", [], [], [], 2.0, b"RIFF-audio", b"png"
        )
        show_id = meta["id"]
        self.assertIn(f"show_{show_id}_backdrop.png", repo._mem_files)
        repo.delete_show(show_id)
        self.assertFalse(any(show_id in name for name in storage.files))
        self.assertFalse(any(show_id in name for name in repo._mem_files))
        self.assertFalse(any(item.get("id") == show_id for item in repo.list_shows()))


if __name__ == "__main__":
    unittest.main()
