from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib
import unittest

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from activities.acquario_magico.main import (
    SPECIES,
    AquariumAudio,
    _get_cached_background,
    _get_scaled_asset,
)

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "acquario_magico"
RUNTIME_ASSETS = ACTIVITY_DIR / "assets" / "runtime"


class AcquarioMagicoContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

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
        self.assertGreaterEqual(len(SPECIES), 8)
        species_ids = [sp["id"] for sp in SPECIES]
        self.assertIn("clownfish", species_ids)
        self.assertIn("turtle", species_ids)
        self.assertIn("octopus", species_ids)
        self.assertIn("dolphin", species_ids)
        self.assertIn("puffer", species_ids)
        self.assertIn("seahorse", species_ids)
        self.assertIn("jellyfish", species_ids)
        self.assertIn("starfish", species_ids)

        for sp in SPECIES:
            self.assertIn("id", sp)
            self.assertIn("name_it", sp)
            self.assertIn("color", sp)
            self.assertIn("size", sp)
            self.assertIn("speed", sp)
            self.assertIn("behavior", sp)

    def test_audio_synthesizer_initializes_all_sounds(self) -> None:
        audio = AquariumAudio()
        self.assertIsNotNone(audio)
        self.assertIn("bubble", audio._sounds)
        self.assertIn("nibble", audio._sounds)
        self.assertIn("glow", audio._sounds)
        self.assertIn("chest", audio._sounds)
        self.assertIn("splash", audio._sounds)

    def test_baked_runtime_assets_exist(self) -> None:
        required_assets = [
            "clownfish.png",
            "turtle.png",
            "octopus.png",
            "dolphin.png",
            "puffer.png",
            "seahorse.png",
            "jellyfish.png",
            "starfish.png",
            "chest.png",
            "coral_reef.png",
        ]
        for name in required_assets:
            p = RUNTIME_ASSETS / name
            self.assertTrue(p.exists(), f"Missing runtime asset: {name}")
            self.assertGreater(p.stat().st_size, 100, f"Asset too small: {name}")
            with p.open("rb") as f:
                header = f.read(8)
                self.assertEqual(header, b"\x89PNG\r\n\x1a\n", f"Invalid PNG: {name}")

    def test_cached_backgrounds_render_fast(self) -> None:
        day_bg = _get_cached_background(glow_mode=False)
        self.assertEqual(day_bg.get_size(), (1024, 600))

        night_bg = _get_cached_background(glow_mode=True)
        self.assertEqual(night_bg.get_size(), (1024, 600))

    def test_scaled_asset_caching_and_facing(self) -> None:
        surf_r = _get_scaled_asset("clownfish.png", 72, 54, facing_right=True)
        self.assertIsNotNone(surf_r)
        self.assertEqual(surf_r.get_size(), (72, 54))

        surf_l = _get_scaled_asset("clownfish.png", 72, 54, facing_right=False)
        self.assertIsNotNone(surf_l)
        self.assertEqual(surf_l.get_size(), (72, 54))


if __name__ == "__main__":
    unittest.main()
