"""Stories of My Voice durable storage: commits, rollback, migration, custody."""
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

from voice_content import LEGACY_STORY_ID, MAX_SAVED_STORIES, STORIES
from voice_services import (
    PROGRESS_KEY,
    STORY_INDEX_KEY,
    SavedStory,
    StoryLibrary,
    StoryProgress,
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
        if self.fail_file_after is not None and self.write_count > self.fail_file_after:
            raise RuntimeError("file failed")
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


TEMPLATE = STORIES[-1]  # a four-card story


def recordings():
    return {card: b"RIFF" + bytes([index]) for index, card in enumerate(TEMPLATE.card_ids)}


def durations():
    return {card: 2.0 for card in TEMPLATE.card_ids}


class VoiceStorageDurabilityTests(unittest.TestCase):
    def save(self, repo):
        return repo.save_story(TEMPLATE.story_id, TEMPLATE.card_ids, recordings(), durations())

    def test_story_commit_is_all_files_plus_index_or_rollback(self):
        storage = MemoryStorage()
        storage.fail_kv = True
        repo = VoiceStorage(StoryLibrary(), storage)
        with self.assertRaises(VoiceStorageError):
            self.save(repo)
        self.assertEqual(storage.files, {})
        self.assertEqual(repo.library.count, 0)

    def test_partial_card_file_failure_rolls_back_earlier_files(self):
        storage = MemoryStorage()
        storage.fail_file_after = 2
        repo = VoiceStorage(StoryLibrary(), storage)
        with self.assertRaises(VoiceStorageError):
            self.save(repo)
        self.assertEqual(storage.files, {})
        self.assertEqual(repo.library.count, 0)

    def test_unreadable_index_refuses_future_save_instead_of_overwriting(self):
        storage = MemoryStorage()
        storage.fail_get = True
        repo = VoiceStorage.load(storage)
        self.assertFalse(repo.available)
        with self.assertRaises(VoiceStorageError):
            self.save(repo)
        self.assertEqual(storage.files, {})
        self.assertEqual(storage.kv, {})

    def test_saved_story_round_trips_with_order_and_template(self):
        storage = MemoryStorage()
        repo = VoiceStorage(StoryLibrary(), storage)
        story = self.save(repo)
        assert story is not None
        reloaded = VoiceStorage.load(storage).stories[0]
        self.assertEqual(reloaded.story_id, story.story_id)
        self.assertEqual(reloaded.template_id, TEMPLATE.story_id)
        self.assertEqual(reloaded.order, TEMPLATE.card_ids)
        self.assertEqual(reloaded.recordings, story.recordings)

    def test_reload_keeps_newest_first_order(self):
        storage = MemoryStorage()
        repo = VoiceStorage(StoryLibrary(), storage)
        first = self.save(repo)
        second = self.save(repo)
        ids = [story.story_id for story in VoiceStorage.load(storage).stories]
        self.assertEqual(ids, [second.story_id, first.story_id])
        ids = [story.story_id for story in VoiceStorage.load(storage).stories]
        self.assertEqual(ids, [second.story_id, first.story_id])

    def test_private_share_name_requires_saved_story_and_card(self):
        storage = MemoryStorage()
        repo = VoiceStorage(StoryLibrary(), storage)
        story = self.save(repo)
        assert story is not None
        card = TEMPLATE.card_ids[0]
        self.assertEqual(repo.private_card_wav_name(story, card), f"stories/{story.story_id}_{card}.wav")
        forged = SavedStory("forged", 0, {card: b"x"}, {card: 1.0}, TEMPLATE.story_id)
        with self.assertRaises(ValueError):
            repo.private_card_wav_name(forged, card)
        with self.assertRaises(ValueError):
            repo.private_card_wav_name(story, "../escape")

    def test_delete_commits_index_before_private_files_are_removed(self):
        storage = MemoryStorage()
        repo = VoiceStorage(StoryLibrary(), storage)
        story = self.save(repo)
        storage.fail_kv = True
        self.assertFalse(repo.delete_story(story.story_id))
        self.assertEqual(len(storage.files), len(TEMPLATE.cards))
        storage.fail_kv = False
        self.assertTrue(repo.delete_story(story.story_id))
        self.assertEqual(repo.library.count, 0)
        self.assertEqual(storage.files, {})

    def test_full_shelf_returns_none_and_never_evicts(self):
        storage = MemoryStorage()
        repo = VoiceStorage(StoryLibrary(), storage)
        for _ in range(MAX_SAVED_STORIES):
            self.assertIsNotNone(self.save(repo))
        before = [story.story_id for story in repo.stories]
        files = dict(storage.files)
        self.assertIsNone(self.save(repo))
        self.assertEqual([story.story_id for story in repo.stories], before)
        self.assertEqual(storage.files, files)

    def test_rejects_cards_outside_the_story_order(self):
        repo = VoiceStorage(StoryLibrary(), MemoryStorage())
        with self.assertRaises(ValueError):
            repo.save_story(TEMPLATE.story_id, TEMPLATE.card_ids, {"other_card": b"RIFF"}, {})


class LegacyMigrationTests(unittest.TestCase):
    """Stories saved by the four-scene version keep loading (never lost)."""

    def legacy_store(self):
        storage = MemoryStorage()
        storage.kv[STORY_INDEX_KEY] = [
            {
                "story_id": "abc123def456",
                "created_at": 1_700_000_000,
                "scene_recordings": {
                    "forest": "stories/abc123def456_forest.wav",
                    "sky": "stories/abc123def456_sky.wav",
                },
                "scene_durations": {"forest": 3.5, "sky": 2.0},
            }
        ]
        storage.files["stories/abc123def456_forest.wav"] = b"RIFF-forest"
        storage.files["stories/abc123def456_sky.wav"] = b"RIFF-sky"
        return storage

    def test_v1_entries_load_as_the_legacy_story_in_scene_order(self):
        repo = VoiceStorage.load(self.legacy_store())
        self.assertEqual(repo.library.count, 1)
        story = repo.stories[0]
        self.assertEqual(story.template_id, LEGACY_STORY_ID)
        self.assertEqual(story.order, ("forest", "sky"))
        self.assertEqual(story.recordings["forest"], b"RIFF-forest")
        self.assertEqual(repo.private_card_wav_name(story, "sky"), "stories/abc123def456_sky.wav")

    def test_new_save_keeps_the_legacy_story_and_upgrades_its_entry(self):
        storage = self.legacy_store()
        repo = VoiceStorage.load(storage)
        repo.save_story(TEMPLATE.story_id, TEMPLATE.card_ids, recordings(), durations())
        entries = storage.kv[STORY_INDEX_KEY]
        self.assertEqual(len(entries), 2)
        legacy = entries[1]
        self.assertEqual(legacy["story_id"], "abc123def456")
        self.assertEqual(legacy["story"], LEGACY_STORY_ID)
        self.assertEqual(legacy["scene_recordings"]["forest"], "stories/abc123def456_forest.wav")
        self.assertIn("stories/abc123def456_forest.wav", storage.files)
        self.assertEqual(VoiceStorage.load(storage).library.count, 2)

    def test_forged_file_names_in_the_index_are_ignored(self):
        storage = self.legacy_store()
        storage.kv[STORY_INDEX_KEY][0]["scene_recordings"]["sea"] = "../../etc/passwd"
        story = VoiceStorage.load(storage).stories[0]
        self.assertNotIn("sea", story.recordings)


class ProgressTests(unittest.TestCase):
    def test_done_stories_persist_and_ignore_unknown_ids(self):
        storage = MemoryStorage()
        progress = StoryProgress.load(storage)
        progress.mark_done(STORIES[0].story_id)
        progress.mark_done("not_a_story")
        self.assertEqual(storage.kv[PROGRESS_KEY], {"done": [STORIES[0].story_id]})
        self.assertEqual(StoryProgress.load(storage).done, {STORIES[0].story_id})


if __name__ == "__main__":
    unittest.main()
