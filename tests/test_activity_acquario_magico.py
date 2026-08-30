from __future__ import annotations

from pathlib import Path
import sys
import unittest

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from activities.acquario_magico.main import (
    _get_cached_background,
    _get_scaled_asset,
)

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

    def test_cached_backgrounds_have_reference_size(self) -> None:
        self.assertEqual(
            _get_cached_background(glow_mode=False).get_size(),
            (1024, 600),
        )
        self.assertEqual(
            _get_cached_background(glow_mode=True).get_size(),
            (1024, 600),
        )

    def test_scaled_asset_cache_supports_both_facings(self) -> None:
        right = _get_scaled_asset("clownfish.png", 72, 54, facing_right=True)
        left = _get_scaled_asset("clownfish.png", 72, 54, facing_right=False)
        self.assertEqual(right.get_size(), (72, 54))
        self.assertEqual(left.get_size(), (72, 54))


if __name__ == "__main__":
    unittest.main()
