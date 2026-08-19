from __future__ import annotations

import unittest
from pathlib import Path
import tomllib
import json

from activities.nascondino_bosco.main import ANIMALS, SEASONS, WoodlandAudio
from activities.piccola_serra.main import PLANTS, GreenhouseAudio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WOODLAND_DIR = PROJECT_ROOT / "activities" / "nascondino_bosco"
GREENHOUSE_DIR = PROJECT_ROOT / "activities" / "piccola_serra"


class Phase3ActivitiesTests(unittest.TestCase):
    def test_woodland_manifest_and_locales(self) -> None:
        manifest_path = WOODLAND_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.nascondino-bosco")

        it_json = json.loads((WOODLAND_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("victory.title", it_json["strings"])

    def test_woodland_audio_and_seasons(self) -> None:
        self.assertGreaterEqual(len(ANIMALS), 4)
        self.assertEqual(len(SEASONS), 3)
        audio = WoodlandAudio()
        self.assertIsNotNone(audio)

    def test_greenhouse_manifest_and_locales(self) -> None:
        manifest_path = GREENHOUSE_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.piccola-serra")

        it_json = json.loads((GREENHOUSE_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("tool.water", it_json["strings"])

    def test_greenhouse_plants_and_audio(self) -> None:
        self.assertGreaterEqual(len(PLANTS), 4)
        audio = GreenhouseAudio()
        self.assertIsNotNone(audio)


if __name__ == "__main__":
    unittest.main()
