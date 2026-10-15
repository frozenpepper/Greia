"""Stories of My Voice: My Creations sharing, shelf custody and save failures.

The narration WAV route to Theatre / Orchestra (P5 interop): only durable
private card recordings are published, as ``audio/wav`` role ``narration``,
once per story. Source/headless evidence only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests", ROOT / "activities" / "storie_della_mia_voce"):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import pygame

from test_activity_storie_della_mia_voce import (
    FakeCreations,
    MemoryStorage,
    advance,
    make_app,
    make_wav,
    solve_order,
    tell_all,
)
import voice_app
from voice_content import MAX_SAVED_STORIES, STORIES
from voice_services import STORY_INDEX_KEY, VoiceStorage


def told_story(app, clock, index: int = 0) -> None:
    app._on_story(index)
    solve_order(app, clock)
    advance(app, clock, 3.0)
    tell_all(app, clock)


def fill_shelf(store: MemoryStorage, count: int = MAX_SAVED_STORIES) -> None:
    repo = VoiceStorage.load(store)
    template = STORIES[0]
    for _ in range(count):
        repo.save_story(template.story_id, template.card_ids, {template.card_ids[0]: make_wav()}, {template.card_ids[0]: 1.0})


class VoiceShareTests(unittest.TestCase):
    def test_share_publishes_each_told_card_once_as_narration_wav(self) -> None:
        creations = FakeCreations()
        app, clock, store = make_app(creations=creations)
        told_story(app, clock)
        self.assertIs(app.state, voice_app.Screen.WATCH)
        self.assertTrue(app.controls.share.visible)
        app._on_share()
        app._on_share()  # a second tap never duplicates
        story = app.storage.stories[0]
        self.assertEqual(len(creations.calls), len(story.recordings))
        for (filename, media_type, role, title), card in zip(creations.calls, story.order):
            self.assertEqual(filename, f"stories/{story.story_id}_{card}.wav")
            self.assertIn(filename, store.files)
            self.assertEqual(media_type, "audio/wav")
            self.assertEqual(role, "narration")
            self.assertTrue(title)
        self.assertTrue(story.shared)
        self.assertTrue(store.kv[STORY_INDEX_KEY][0]["shared"])
        # The shared mark survives a reload (no duplicate share next visit).
        self.assertTrue(VoiceStorage.load(store).stories[0].shared)

    def test_failed_publication_is_retryable_and_marks_nothing(self) -> None:
        creations = FakeCreations()
        app, clock, store = make_app(creations=creations)
        told_story(app, clock)
        with mock.patch.object(creations, "publish_private_file", side_effect=RuntimeError("broker")):
            app._on_share()
        self.assertFalse(app.storage.stories[0].shared)
        self.assertEqual(app.cast.feedback.pose.value, "think")
        app._on_share()
        self.assertTrue(app.storage.stories[0].shared)

    def test_no_share_control_without_creations_broker(self) -> None:
        app, clock, _ = make_app(creations=None)
        told_story(app, clock)
        self.assertFalse(app.controls.share.visible)
        self.assertNotIn("share", [target.control_id for target in app.controls.layer.targets])

    def test_saved_story_from_the_shelf_plays_and_shares(self) -> None:
        creations = FakeCreations()
        store = MemoryStorage()
        fill_shelf(store, 2)
        app, clock, _ = make_app(creations=creations, storage=store)
        app.open_shelf()
        self.assertEqual(len(app.controls.cards), 2)
        app._on_shelf_card(0)
        self.assertIs(app.state, voice_app.Screen.WATCH)
        self.assertTrue(app.watch.from_shelf)
        app._on_share()
        self.assertEqual(len(creations.calls), 1)
        advance(app, clock, 12.0)
        self.assertIs(app.state, voice_app.Screen.WATCH)  # shelf stories never end on completion
        app._on_picker_button()
        self.assertIs(app.state, voice_app.Screen.SHELF)


class ShelfCustodyTests(unittest.TestCase):
    def test_full_shelf_refuses_instead_of_evicting_and_keeps_the_draft(self) -> None:
        store = MemoryStorage()
        fill_shelf(store)
        app, clock, _ = make_app(storage=store)
        oldest = app.storage.stories[-1].story_id
        told_story(app, clock, 1)
        self.assertIsNotNone(app.sheet)
        self.assertEqual(app.sheet.surface_id, "storie.full")
        self.assertIsNotNone(app.pending)
        self.assertEqual(len(app.storage.stories), MAX_SAVED_STORIES)
        self.assertIn(oldest, [story.story_id for story in app.storage.stories])
        # Go to the shelf, make room deliberately, then save the waiting story.
        app.sheet.layer.target("full.shelf").activate()
        self.assertIs(app.state, voice_app.Screen.SHELF)
        self.assertTrue(app.controls.save_pending.visible)
        self.assertFalse(app.controls.save_pending.enabled)
        app._on_shelf_delete(0)
        clock.now += 1.0
        app.sheet.layer.target("delete.confirm").activate()
        self.assertEqual(len(app.storage.stories), MAX_SAVED_STORIES - 1)
        self.assertTrue(app.controls.save_pending.enabled)
        app._on_save_pending()
        self.assertIsNone(app.pending)
        self.assertEqual(len(app.storage.stories), MAX_SAVED_STORIES)
        self.assertEqual(app.storage.stories[0].template_id, STORIES[1].story_id)

    def test_full_shelf_can_still_watch_the_story(self) -> None:
        store = MemoryStorage()
        fill_shelf(store)
        app, clock, _ = make_app(storage=store)
        told_story(app, clock, 0)
        app.sheet.layer.target("full.watch").activate()
        self.assertIs(app.state, voice_app.Screen.WATCH)
        self.assertIsNone(app.watch.story)
        self.assertFalse(app.controls.share.visible)

    def test_picker_shelf_tile_shows_the_twelve_dot_meter(self) -> None:
        store = MemoryStorage()
        fill_shelf(store, 5)
        app, _, _ = make_app(storage=store)
        self.assertIn("shelf", [target.control_id for target in app.controls.layer.targets])
        self.assertIsNotNone(app.controls.shelf.icon)

    def test_save_failure_keeps_every_recording_and_stays_on_the_card(self) -> None:
        app, clock, _ = make_app()
        with mock.patch.object(app.storage._storage, "kv_set", side_effect=RuntimeError("disk")):
            told_story(app, clock)
        self.assertIs(app.state, voice_app.Screen.TELL)
        self.assertEqual(len(app.telling.recordings), len(STORIES[0].cards))
        self.assertEqual(app.storage.stories, ())
        app._on_next()  # retry succeeds once the store recovers
        self.assertIs(app.state, voice_app.Screen.WATCH)
        self.assertEqual(len(app.storage.stories), 1)


if __name__ == "__main__":
    unittest.main()
