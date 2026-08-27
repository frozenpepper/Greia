"""Tests for storie_della_mia_voce Activity (content + storage + recorder)."""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "storie_della_mia_voce"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)


from voice_content import MAX_SAVED_STORIES, SCENES, SCENE_IDS, SceneId
from voice_services import (
    SavedStory,
    STORY_INDEX_KEY,
    StoryLibrary,
    VoiceStorage,
)


class VoiceContentTests(unittest.TestCase):
    def test_scenes_are_four_distinct_ids(self) -> None:
        self.assertEqual(len(SCENES), 4)
        seen = set()
        for scene in SCENES:
            self.assertNotIn(scene.scene_id, seen)
            seen.add(scene.scene_id)
        self.assertEqual(seen, set(SceneId))

    def test_scene_id_tuple_matches_manifest_events(self) -> None:
        # The Activity declares five+ events; SCENE_IDS is what
        # the storage layer uses to whitelist scene ids in saved
        # stories, so it must cover all SceneId values.
        self.assertEqual(set(SCENE_IDS), set(SceneId))


class VoiceStorageContractTests(unittest.TestCase):
    def test_storage_key_is_namespaced(self) -> None:
        self.assertTrue(STORY_INDEX_KEY.startswith("storie_della_mia_voce."))
        self.assertIn("stories", STORY_INDEX_KEY)

    def test_story_library_bounded(self) -> None:
        library = StoryLibrary()
        self.assertFalse(library.is_full)
        for i in range(MAX_SAVED_STORIES + 2):
            library.add(
                SavedStory(
                    story_id=f"id-{i}",
                    created_at=0,
                    scene_recordings={"forest": b"x" * 100},
                    scene_durations={"forest": 1.0},
                )
            )
        self.assertEqual(library.count, MAX_SAVED_STORIES)
        self.assertTrue(library.is_full)

    def test_saved_story_validates_scene_ids(self) -> None:
        with self.assertRaises(ValueError):
            SavedStory(
                story_id="bad",
                created_at=0,
                scene_recordings={"nope": b"x" * 100},
                scene_durations={"nope": 1.0},
            )


class VoiceRecorderContractTests(unittest.TestCase):
    """The recorder must follow MICROPHONE_RECORDING.md: never
    enumerate or select hardware, always go through the SDK.
    """

    def test_recorder_uses_get_sdl_capture_device(self) -> None:
        from pathlib import Path
        # Static check: voice_microphone.py must import the Greia
        # SDK accessors and must not do production device policy.
        # ``get_audio_device_names`` is the documented simulator/
        # development fallback when BOTH SDK accessors return None,
        # so it is allowed but only after the SDK path.
        text = (ACTIVITY_ROOT / "voice_microphone.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("get_sdl_capture_device", text)
        self.assertIn("get_audio_capture_device", text)
        for forbidden in ("soundcard", "/dev/snd", "hw:0,0", "plughw"):
            self.assertNotIn(forbidden, text)
        # The fallback must come AFTER the SDK accessors (the
        # production policy is "use the SDK or fail" before any
        # fallback is consulted).
        sdk_pos = text.find("get_sdl_capture_device()")
        fallback_pos = text.find("get_audio_device_names(True)")
        self.assertGreater(fallback_pos, sdk_pos)


if __name__ == "__main__":
    unittest.main()
