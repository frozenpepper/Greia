from __future__ import annotations

import unittest
from pathlib import Path
import tomllib
import json

from activities.treno_numeri.main import ITEMS as TRAIN_ITEMS, TrainAudio
from activities.memory_meraviglie.main import THEMES, GRID_CONFIGS, MemoryAudio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRAIN_DIR = PROJECT_ROOT / "activities" / "treno_numeri"
MEMORY_DIR = PROJECT_ROOT / "activities" / "memory_meraviglie"


class Phase2ActivitiesTests(unittest.TestCase):
    def test_train_manifest_and_locales(self) -> None:
        manifest_path = TRAIN_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.treno-numeri")
        self.assertIn("learn", data["presentation"]["categories"])

        it_json = json.loads((TRAIN_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("prompt.load", it_json["strings"])

    def test_train_audio_and_items(self) -> None:
        self.assertGreaterEqual(len(TRAIN_ITEMS), 4)
        audio = TrainAudio()
        self.assertIsNotNone(audio)

    def test_memory_manifest_and_locales(self) -> None:
        manifest_path = MEMORY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.memory-meraviglie")

        it_json = json.loads((MEMORY_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("victory.title", it_json["strings"])

    def test_memory_themes_and_grids(self) -> None:
        self.assertEqual(len(THEMES), 4)
        self.assertGreaterEqual(len(GRID_CONFIGS), 3)
        for theme in THEMES:
            self.assertGreaterEqual(len(theme["items"]), 6)
        audio = MemoryAudio()
        self.assertIsNotNone(audio)


if __name__ == "__main__":
    unittest.main()
