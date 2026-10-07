"""Voice Stories share chips, pagination and save-failure behavior."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "storie_della_mia_voce"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from voice_app import Phase, VoiceApp
from voice_content import SCENES
from voice_renderer import VoiceRenderer
from voice_services import SavedStory, StoryLibrary, VoiceStorage, VoiceStorageError


class FakeCreations:
    def __init__(self):
        self.calls = []

    def publish_private_file(self, filename, *, media_type, role, title):
        self.calls.append((filename, media_type, role, title))
        return {"creation_id": "shared"}


class FakeResources:
    def text(self, key):
        return {
            "ui.story": "Story",
            "ui.scene_forest": "Forest",
        }.get(key, key)


class VoiceCreationFlowTests(unittest.TestCase):
    def story(self):
        scene_id = str(SCENES[0].scene_id)
        return SavedStory(
            "story-1",
            0,
            {scene_id: b"RIFF-demo"},
            {scene_id: 2.0},
        )

    def make_app(self):
        story = self.story()
        storage = VoiceStorage(StoryLibrary([story]), SimpleNamespace())
        app = object.__new__(VoiceApp)
        app.creations = FakeCreations()
        app.storage = storage
        app.resources = FakeResources()
        app.shared_scene_keys = set()
        app.share_feedback = None
        app.share_feedback_until = 0.0
        return app, story

    def test_share_publishes_only_saved_private_wav_and_deduplicates_tap(self):
        app, story = self.make_app()
        scene = SCENES[0]
        with mock.patch("voice_app.time.monotonic", return_value=10.0):
            app._share_scene(story, scene)
            app._share_scene(story, scene)
        self.assertEqual(len(app.creations.calls), 1)
        filename, media_type, role, title = app.creations.calls[0]
        self.assertEqual(
            filename,
            f"stories/{story.story_id}_{scene.scene_id}.wav",
        )
        self.assertEqual(media_type, "audio/wav")
        self.assertEqual(role, "narration")
        self.assertIn("Forest", title)
        self.assertEqual(app.share_feedback[2], "saved")

    def test_library_story_cards_never_extend_below_reference_canvas(self):
        for local_index in range(4):
            rect = VoiceRenderer.library_story_rect(local_index)
            self.assertLessEqual(rect.bottom, 600)
            for scene_index in range(4):
                share = VoiceRenderer.library_scene_share_rect(
                    local_index, scene_index
                )
                self.assertTrue(rect.contains(share))

    def test_save_failure_remains_retryable_and_emits_no_story_event(self):
        app = object.__new__(VoiceApp)
        app.storage = SimpleNamespace(
            save_story=mock.Mock(side_effect=VoiceStorageError("disk"))
        )
        app.pending_recordings = {"forest": b"RIFF"}
        app.pending_durations = {"forest": 1.0}
        app.phase = Phase.REPLAY
        app.events = SimpleNamespace(
            story_saved=mock.Mock(),
            first_story_recorded=mock.Mock(),
        )
        app.first_story_emitted = False
        app.save_error_until = 0.0
        with mock.patch("voice_app.time.monotonic", return_value=20.0):
            app._save_story()
        self.assertEqual(app.phase, Phase.REPLAY)
        self.assertGreater(app.save_error_until, 20.0)
        app.events.story_saved.assert_not_called()

    def test_full_or_unavailable_storage_result_is_also_retryable(self):
        app = object.__new__(VoiceApp)
        app.storage = SimpleNamespace(save_story=mock.Mock(return_value=None))
        app.pending_recordings = {"forest": b"RIFF"}
        app.pending_durations = {"forest": 1.0}
        app.phase = Phase.REPLAY
        app.events = SimpleNamespace(
            story_saved=mock.Mock(),
            first_story_recorded=mock.Mock(),
        )
        app.first_story_emitted = False
        app.save_error_until = 0.0
        with mock.patch("voice_app.time.monotonic", return_value=30.0):
            app._save_story()
        self.assertEqual(app.phase, Phase.REPLAY)
        self.assertGreater(app.save_error_until, 30.0)


if __name__ == "__main__":
    unittest.main()
