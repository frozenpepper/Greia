from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from activities.acquario_magico.main import SPECIES, AquariumAudio

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "acquario_magico"
RUNTIME_ASSETS = ACTIVITY_DIR / "assets" / "runtime"


class AcquarioMagicoContractTests(unittest.TestCase):
    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.acquario-magico")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])

    def test_species_metadata(self) -> None:
        self.assertGreaterEqual(len(SPECIES), 5)
        for sp in SPECIES:
            self.assertIn("id", sp)
            self.assertIn("name_it", sp)
            self.assertIn("color", sp)
            self.assertIn("size", sp)

    def test_audio_synthesizer_initializes(self) -> None:
        audio = AquariumAudio()
        self.assertIsNotNone(audio)

    def test_baked_runtime_assets_exist(self) -> None:
        required_assets = [
            "clownfish.png",
            "turtle.png",
            "octopus.png",
            "dolphin.png",
            "puffer.png",
            "coral_reef.png",
        ]
        for name in required_assets:
            p = RUNTIME_ASSETS / name
            self.assertTrue(p.exists(), f"Missing runtime asset: {name}")
            self.assertGreater(p.stat().st_size, 100, f"Asset too small: {name}")
            with p.open("rb") as f:
                header = f.read(8)
                self.assertEqual(header, b"\x89PNG\r\n\x1a\n", f"Invalid PNG: {name}")


if __name__ == "__main__":
    unittest.main()
