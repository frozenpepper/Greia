from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.assets import AssetCatalogue, AssetCatalogueError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG = PROJECT_ROOT / "assets" / "catalog" / "core_icons_v1.toml"


class AssetCatalogueTests(unittest.TestCase):
    def test_catalogue_loads_expected_core_icons(self) -> None:
        catalogue = AssetCatalogue.load(CATALOG)
        icons = catalogue.all_icons()
        self.assertEqual(len(icons), 39)
        self.assertEqual(catalogue.get("unicorn").category, "characters")
        self.assertTrue(catalogue.get("palette").path_128.is_file())
        self.assertTrue(catalogue.get("close_button").path_64.is_file())

    def test_unknown_icon_fails(self) -> None:
        catalogue = AssetCatalogue.load(CATALOG)
        with self.assertRaises(AssetCatalogueError):
            catalogue.get("not-real")

    def test_duplicate_icon_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            catalog_dir = assets / "catalog"
            icon_dir = assets / "icons"
            catalog_dir.mkdir(parents=True)
            icon_dir.mkdir()
            icon = icon_dir / "x.png"
            icon.write_bytes(b"x")
            manifest = catalog_dir / "icons.toml"
            manifest.write_text(
                """
[[icons]]
id = "x"
category = "test"
alt_key = "asset.x"
path_64 = "icons/x.png"
path_128 = "icons/x.png"
path_256 = "icons/x.png"

[[icons]]
id = "x"
category = "test"
alt_key = "asset.x2"
path_64 = "icons/x.png"
path_128 = "icons/x.png"
path_256 = "icons/x.png"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(AssetCatalogueError):
                AssetCatalogue.load(manifest)


if __name__ == "__main__":
    unittest.main()
