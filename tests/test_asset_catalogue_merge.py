from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.assets import AssetCatalogue, AssetCatalogueError


class AssetCatalogueMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.assets = Path(self.temporary.name) / "assets"
        self.catalog = self.assets / "catalog"
        self.icons = self.assets / "icons"
        self.visual = self.assets / "visual"
        self.catalog.mkdir(parents=True)
        self.icons.mkdir()
        self.visual.mkdir()

    def write_icon_catalogue(self, filename: str = "icons.toml", asset_id: str = "home") -> Path:
        for size in (64, 128, 256):
            (self.icons / f"home-{size}.png").write_bytes(b"png")
        path = self.catalog / filename
        path.write_text(
            f"""
[[icons]]
id = "{asset_id}"
category = "system"
alt_key = "asset.home"
path_64 = "icons/home-64.png"
path_128 = "icons/home-128.png"
path_256 = "icons/home-256.png"
""".lstrip(),
            encoding="utf-8",
        )
        return path

    def write_visual_catalogue(
        self,
        filename: str = "visuals.toml",
        asset_id: str = "ui.shadow.soft",
    ) -> Path:
        (self.visual / "shadow.png").write_bytes(b"png")
        path = self.catalog / filename
        path.write_text(
            f"""
[[visuals]]
id = "{asset_id}"
kind = "shadow"
role = "grounding"

[visuals.variants]
default = "visual/shadow.png"
""".lstrip(),
            encoding="utf-8",
        )
        return path

    def test_merges_icon_and_visual_manifests_under_one_namespace(self) -> None:
        icons = AssetCatalogue.load(self.write_icon_catalogue())
        visuals = AssetCatalogue.load(self.write_visual_catalogue())

        merged = icons.merged(visuals)

        self.assertEqual(merged.root, self.assets.resolve())
        self.assertEqual(merged.get("home").asset_id, "home")
        self.assertEqual(merged.get_visual("ui.shadow.soft").role, "grounding")
        self.assertEqual(len(merged.all_icons()), 1)
        self.assertEqual(len(merged.all_visuals()), 1)

    def test_duplicate_id_across_catalogues_is_rejected(self) -> None:
        icons = AssetCatalogue.load(self.write_icon_catalogue(asset_id="shared"))
        visuals = AssetCatalogue.load(self.write_visual_catalogue(asset_id="shared"))

        with self.assertRaisesRegex(AssetCatalogueError, "duplicate asset id: shared"):
            icons.merged(visuals)

    def test_different_asset_roots_are_rejected(self) -> None:
        icons = AssetCatalogue.load(self.write_icon_catalogue())
        other_root = Path(self.temporary.name) / "other" / "assets"
        other_catalog = other_root / "catalog"
        other_visual = other_root / "visual"
        other_catalog.mkdir(parents=True)
        other_visual.mkdir()
        (other_visual / "shadow.png").write_bytes(b"png")
        manifest = other_catalog / "visuals.toml"
        manifest.write_text(
            """
[[visuals]]
id = "ui.shadow.soft"
kind = "shadow"
role = "grounding"

[visuals.variants]
default = "visual/shadow.png"
""".lstrip(),
            encoding="utf-8",
        )
        visuals = AssetCatalogue.load(manifest)

        with self.assertRaisesRegex(AssetCatalogueError, "different roots"):
            icons.merged(visuals)

    def test_constructor_rejects_icon_visual_overlap(self) -> None:
        icons = AssetCatalogue.load(self.write_icon_catalogue(asset_id="shared"))
        visual_catalogue = AssetCatalogue.load(
            self.write_visual_catalogue(asset_id="visual-only")
        )

        with self.assertRaisesRegex(AssetCatalogueError, "duplicate asset id"):
            AssetCatalogue(
                icons.root,
                {"shared": icons.get("shared")},
                {"shared": visual_catalogue.get_visual("visual-only")},
            )


if __name__ == "__main__":
    unittest.main()
