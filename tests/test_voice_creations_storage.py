"""Voice Stories durable storage + Creations publication contracts."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "storie_della_mia_voce"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from voice_content import SCENES
from voice_services import (
    SavedStory,
    StoryLibrary,
    VoiceStorage,
    VoiceStorageError,
)


class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}
        self.fail_kv = False
        self.fail_get = False
        self.fail_file_after = None
        self.write_count = 0

    def kv_get(self, key, default=None):
        if self.fail_get:
            raise RuntimeError("read failed")
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_kv:
            raise RuntimeError("kv failed")
        self.kv[key] = value

    def file_write_atomic(self, name, payload):
        self.write_count += 1
        if (
            self.fail_file_after is not None
            and self.write_count > self.fail_file_after
        ):
            raise RuntimeError("file failed")
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class VoiceStorageDurabilityTests(unittest.TestCase):
    def recordings(self):
        return {
            str(scene.scene_id): b"RIFF" + bytes([index])
            for index, scene in enumerate(SCENES)
        }

    def durations(self):
        return {str(scene.scene_id): 2.0 for scene in SCENES}

    def test_story_commit_is_all_files_plus_index_or_rollback(self):
        storage = MemoryStorage()
        storage.fail_kv = True
        repo = VoiceStorage(StoryLibrary(), storage)
        with self.assertRaises(VoiceStorageError):
            repo.save_story(self.recordings(), self.durations())
        self.assertEqual(storage.files, {})
        self.assertEqual(repo._library.count, 0)

    def test_partial_scene_file_failure_rolls_back_earlier_files(self):
        storage = MemoryStorage()
        storage.fail_file_after = 2
        repo = VoiceStorage(StoryLibrary(), storage)
        with self.assertRaises(VoiceStorageError):
            repo.save_story(self.recordings(), self.durations())
        self.assertEqual(storage.files, {})
        self.assertEqual(repo._library.count, 0)

    def test_unreadable_index_refuses_future_save_instead_of_overwriting(self):
        storage = MemoryStorage()
        storage.fail_get = True
        repo = VoiceStorage.load(storage)
        self.assertFalse(repo._index_readable)
        with self.assertRaises(VoiceStorageError):
            repo.save_story(self.recordings(), self.durations())
        self.assertEqual(storage.files, {})
        self.assertEqual(storage.kv, {})

    def test_private_share_name_requires_saved_story_and_scene(self):
        storage = MemoryStorage()
        repo = VoiceStorage(StoryLibrary(), storage)
        story = repo.save_story(self.recordings(), self.durations())
        assert story is not None
        forest = str(SCENES[0].scene_id)
        name = repo.private_scene_wav_name(story, forest)
        self.assertEqual(name, f"stories/{story.story_id}_{forest}.wav")
        forged = SavedStory(
            "forged",
            0,
            {forest: b"x"},
            {forest: 1.0},
        )
        with self.assertRaises(ValueError):
            repo.private_scene_wav_name(forged, forest)

    def test_delete_commits_index_before_private_files_are_removed(self):
        storage = MemoryStorage()
        repo = VoiceStorage(StoryLibrary(), storage)
        story = repo.save_story(self.recordings(), self.durations())
        assert story is not None
        self.assertTrue(repo.delete_story(story.story_id))
        self.assertEqual(repo._library.count, 0)
        self.assertEqual(storage.files, {})


if __name__ == "__main__":
    unittest.main()
