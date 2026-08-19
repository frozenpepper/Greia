from __future__ import annotations

import unittest
from pathlib import Path
import tomllib
import json

from activities.costruiamo_ponti.main import BLOCK_TYPES, LEVELS, BridgeAudio
from activities.clinica_cuccioli.main import PATIENTS, TOOLS, VetAudio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DIR = PROJECT_ROOT / "activities" / "costruiamo_ponti"
CLINIC_DIR = PROJECT_ROOT / "activities" / "clinica_cuccioli"


class Phase4ActivitiesTests(unittest.TestCase):
    def test_bridge_manifest_and_locales(self) -> None:
        manifest_path = BRIDGE_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.costruiamo-ponti")

        it_json = json.loads((BRIDGE_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("btn.cross", it_json["strings"])

    def test_bridge_blocks_and_audio(self) -> None:
        self.assertEqual(len(BLOCK_TYPES), 4)
        self.assertEqual(len(LEVELS), 3)
        audio = BridgeAudio()
        self.assertIsNotNone(audio)

    def test_clinic_manifest_and_locales(self) -> None:
        manifest_path = CLINIC_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.clinica-cuccioli")

        it_json = json.loads((CLINIC_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("tool.stetho", it_json["strings"])

    def test_clinic_patients_tools_and_audio(self) -> None:
        self.assertEqual(len(PATIENTS), 4)
        self.assertEqual(len(TOOLS), 5)
        audio = VetAudio()
        self.assertIsNotNone(audio)


if __name__ == "__main__":
    unittest.main()
