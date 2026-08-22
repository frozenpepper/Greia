from __future__ import annotations

import json
import os
from pathlib import Path
import tomllib
import unittest

import pygame

from activities.sillabe_magiche.main import (
    CONSONANTS_IT,
    VOWELS_IT,
    WORDS_DATA_IT,
    WORDS_DATA_EN,
    LeoCompanion,
    SyllableCard,
    FloatingOrb,
    WordTile,
    Particle,
    SoundManager,
)
from greia_platform.typography import GreiaTypography

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_DIR = PROJECT_ROOT / "activities" / "sillabe_magiche"


class SillabeMagicheTests(unittest.TestCase):
    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.sillabe-magiche")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])
        self.assertIn("learn", data["presentation"]["categories"])
        self.assertIn("play", data["presentation"]["categories"])
        self.assertEqual(data["education"]["difficulty"], 1)

    def test_locales_contain_required_strings(self) -> None:
        it_json = json.loads((ACTIVITY_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        en_json = json.loads((ACTIVITY_DIR / "locales" / "en.json").read_text(encoding="utf-8"))

        for key in ("activity.title", "mode.explorer", "mode.catcher", "mode.builder", "prompt.explore", "feedback.correct"):
            self.assertIn(key, it_json["strings"])
            self.assertIn(key, en_json["strings"])

    def test_phonics_and_word_data(self) -> None:
        self.assertGreaterEqual(len(CONSONANTS_IT), 14)
        self.assertEqual(len(VOWELS_IT), 5)
        self.assertGreaterEqual(len(WORDS_DATA_IT), 20)
        self.assertGreaterEqual(len(WORDS_DATA_EN), 10)

        for word, (s1, s2), emoji, stem in WORDS_DATA_IT:
            self.assertEqual(word, f"{s1}{s2}")
            self.assertTrue(len(emoji) > 0)
            self.assertTrue(len(stem) > 0)

        for word, (s1, s2), emoji, stem in WORDS_DATA_EN:
            self.assertEqual(word, f"{s1}{s2}")
            self.assertTrue(len(emoji) > 0)
            self.assertTrue(len(stem) > 0)

    def test_audio_assets_exist_for_all_locales(self) -> None:
        for loc in ("it", "en"):
            audio_dir = ACTIVITY_DIR / "assets" / "audio" / loc
            self.assertTrue(audio_dir.is_dir())

            # Verify consonants & basic syllables
            for c in CONSONANTS_IT:
                for v in VOWELS_IT:
                    syl_wav = audio_dir / f"syl_{c.lower()}{v.lower()}.wav"
                    find_wav = audio_dir / f"find_{c.lower()}{v.lower()}.wav"
                    self.assertTrue(syl_wav.is_file(), f"Missing {syl_wav}")
                    self.assertTrue(find_wav.is_file(), f"Missing {find_wav}")

            # Verify praises
            self.assertTrue((audio_dir / "bravissima.wav" if loc == "it" else audio_dir / "great_job.wav").is_file())

    def test_sound_manager_initializes_and_synthesizes(self) -> None:
        sm = SoundManager()
        self.assertIsNotNone(sm)
        # Verify safe playback
        sm.play_syllable("BA", "it")
        sm.play_word("casa", "it")
        sm.play_praise("it")
        sm.play("pop")
        sm.play("chime")
        sm.play("fanfare")
        sm.play("wobble")
        sm.play("swoosh")

    def test_render_entities_and_components(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        surf = pygame.Surface((1024, 600))
        typography = GreiaTypography()

        mascot = LeoCompanion(900, 450)
        mascot.wiggle()
        mascot.cheer()
        mascot.update()
        mascot.draw(surf)
        self.assertTrue(mascot.contains(900, 450))

        card = SyllableCard("MA", 200, 200)
        self.assertTrue(card.contains(210, 210))
        card.bounce()
        card.update()
        card.draw(surf, typography)

        orb = FloatingOrb("BA", 400, 300, is_target=True)
        self.assertTrue(orb.contains(400, 300))
        orb.wobble()
        orb.update()
        orb.draw(surf, typography)

        tile = WordTile("CA", 500, 400)
        self.assertTrue(tile.contains(510, 410))
        tile.wobble()
        tile.bounce()
        tile.update()
        tile.draw(surf, typography)

        p = Particle(100, 100, (255, 200, 50))
        self.assertTrue(p.update())
        p.draw(surf)


if __name__ == "__main__":
    unittest.main()
