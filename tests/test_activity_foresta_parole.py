from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest

from activities.foresta_parole.main import PHONICS_DATA, SoundManager

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_DIR = PROJECT_ROOT / "activities" / "foresta_parole"


class ForestaParoleTests(unittest.TestCase):
    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.foresta-parole")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])

    def test_locales_contain_required_strings(self) -> None:
        it_json = json.loads((ACTIVITY_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        en_json = json.loads((ACTIVITY_DIR / "locales" / "en.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("activity.title", en_json["strings"])

    def test_phonics_data_and_audio_files_exist_for_both_languages(self) -> None:
        for lang in ("it", "en"):
            self.assertIn(lang, PHONICS_DATA)
            items = PHONICS_DATA[lang]
            self.assertGreaterEqual(len(items), 20)
            lang_dir = ACTIVITY_DIR / "assets" / "audio" / lang
            self.assertTrue(lang_dir.is_dir())
            for letter, letter_id, prompt_id, word_display, emoji, word_stem in items:
                letter_wav = lang_dir / f"{letter_id}.wav"
                prompt_wav = lang_dir / f"{prompt_id}.wav"
                word_wav = lang_dir / f"{word_stem}.wav"
                self.assertTrue(letter_wav.is_file(), f"Missing {letter_wav}")
                self.assertTrue(prompt_wav.is_file(), f"Missing {prompt_wav}")
                self.assertTrue(word_wav.is_file(), f"Missing {word_wav}")

    def test_audio_synthesizer_initializes(self) -> None:
        audio = SoundManager()
        self.assertIsNotNone(audio)


if __name__ == "__main__":
    unittest.main()
