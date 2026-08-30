from __future__ import annotations

from pathlib import Path
import sys
import unittest

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from activities.acquario_magico.acquarium_assets import AquariumAssetCache

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "acquario_magico"
RUNTIME_ASSETS = ACTIVITY_DIR / "assets" / "runtime"


class AcquarioMagicoRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

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
            path = RUNTIME_ASSETS / name
            self.assertTrue(path.exists(), f"Missing runtime asset: {name}")
            self.assertGreater(path.stat().st_size, 100, f"Asset too small: {name}")
            with path.open("rb") as handle:
                self.assertEqual(
                    handle.read(8),
                    b"\x89PNG\r\n\x1a\n",
                    f"Invalid PNG: {name}",
                )

    def test_background_cache_has_reference_size_and_reuses_surface(self) -> None:
        cache = AquariumAssetCache()
        day = cache.background(glow_mode=False)
        night = cache.background(glow_mode=True)
        self.assertEqual(day.get_size(), (1024, 600))
        self.assertEqual(night.get_size(), (1024, 600))
        self.assertIs(cache.background(glow_mode=False), day)

    def test_scaled_asset_cache_supports_both_facings_and_reuses_surface(self) -> None:
        cache = AquariumAssetCache()
        right = cache.scaled("clownfish.png", 72, 54, facing_right=True)
        left = cache.scaled("clownfish.png", 72, 54, facing_right=False)
        self.assertIsNotNone(right)
        self.assertIsNotNone(left)
        assert right is not None and left is not None
        self.assertEqual(right.get_size(), (72, 54))
        self.assertEqual(left.get_size(), (72, 54))
        self.assertIs(cache.scaled("clownfish.png", 72, 54, facing_right=True), right)


if __name__ == "__main__":
    unittest.main()
