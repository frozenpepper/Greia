from __future__ import annotations

import unittest
from pathlib import Path

from greia_platform.assets import AssetCatalogue, AssetCatalogueError


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AssetCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalogue = AssetCatalogue.load(
            PROJECT_ROOT / "assets" / "catalog" / "core_icons_v1.toml"
        )

    def test_individual_pngs_exist(self) -> None:
        icons = self.catalogue.all_icons()
        self.assertGreaterEqual(len(icons), 35)
        for icon in icons:
            self.assertTrue(icon.path_64.is_file())
            self.assertTrue(icon.path_128.is_file())
            self.assertTrue(icon.path_256.is_file())

    def test_core_launcher_icons_exist(self) -> None:
        for asset_id in ("robot", "garden", "close_button", "book", "abc_board"):
            self.assertEqual(self.catalogue.get(asset_id).asset_id, asset_id)

    def test_unknown_icon_fails(self) -> None:
        with self.assertRaises(AssetCatalogueError):
            self.catalogue.get("does_not_exist")


if __name__ == "__main__":
    unittest.main()
