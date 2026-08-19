from __future__ import annotations

import unittest
from pathlib import Path
import tomllib
import json

from activities.acquario_magico.main import SPECIES, AquariumAudio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AQUARIUM_DIR = PROJECT_ROOT / "activities" / "acquario_magico"


class Phase5ActivitiesTests(unittest.TestCase):
    def test_aquarium_manifest_and_locales(self) -> None:
        manifest_path = AQUARIUM_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.acquario-magico")

        it_json = json.loads((AQUARIUM_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("tool.feed", it_json["strings"])

    def test_aquarium_species_and_audio(self) -> None:
        self.assertGreaterEqual(len(SPECIES), 4)
        audio = AquariumAudio()
        self.assertIsNotNone(audio)


if __name__ == "__main__":
    unittest.main()
