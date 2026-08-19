from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest

from activities.treno_numeri.main import FRUITS, TrainAudio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_DIR = PROJECT_ROOT / "activities" / "treno_numeri"


class TrenoNumeriTests(unittest.TestCase):
    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.treno-numeri")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])

    def test_locales_contain_required_strings(self) -> None:
        it_json = json.loads((ACTIVITY_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        en_json = json.loads((ACTIVITY_DIR / "locales" / "en.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("activity.title", en_json["strings"])

    def test_fruits_metadata(self) -> None:
        self.assertGreaterEqual(len(FRUITS), 4)
        for f in FRUITS:
            self.assertIn("id", f)
            self.assertIn("color", f)

    def test_audio_synthesizer_initializes(self) -> None:
        audio = TrainAudio()
        self.assertIsNotNone(audio)


if __name__ == "__main__":
    unittest.main()
