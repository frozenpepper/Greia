from __future__ import annotations

import tempfile
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
        self.assertGreaterEqual(len(icons), 29)
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

    def test_visual_only_catalogue_loads_explicit_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "assets"
            catalog = root / "catalog"
            visual = root / "visual" / "ui"
            catalog.mkdir(parents=True)
            visual.mkdir(parents=True)
            default = visual / "panel.png"
            focused = visual / "panel-focused.png"
            default.write_bytes(b"default")
            focused.write_bytes(b"focused")
            manifest = catalog / "shared_visuals.toml"
            manifest.write_text(
                """
[[visuals]]
id = "ui.panel.base"
kind = "ui"
role = "panel"

[visuals.variants]
default = "visual/ui/panel.png"
focused = "visual/ui/panel-focused.png"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            catalogue = AssetCatalogue.load(manifest)
            asset = catalogue.get_visual("ui.panel.base")

            self.assertEqual(asset.kind, "ui")
            self.assertEqual(asset.role, "panel")
            self.assertEqual(asset.variant_names(), ("default", "focused"))
            self.assertEqual(asset.path_for(), default.resolve())
            self.assertEqual(asset.path_for("focused"), focused.resolve())
            self.assertEqual(catalogue.all_icons(), ())
            self.assertEqual(catalogue.all_visuals(), (asset,))

    def test_visual_variant_must_have_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "assets"
            catalog = root / "catalog"
            visual = root / "visual"
            catalog.mkdir(parents=True)
            visual.mkdir()
            (visual / "hover.png").write_bytes(b"hover")
            manifest = catalog / "bad.toml"
            manifest.write_text(
                """
[[visuals]]
id = "ui.button.primary"
kind = "ui"
role = "button"

[visuals.variants]
hover = "visual/hover.png"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                AssetCatalogueError, "visual variants must define default"
            ):
                AssetCatalogue.load(manifest)

    def test_visual_kind_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "assets"
            catalog = root / "catalog"
            visual = root / "visual"
            catalog.mkdir(parents=True)
            visual.mkdir()
            (visual / "thing.png").write_bytes(b"thing")
            manifest = catalog / "bad.toml"
            manifest.write_text(
                """
[[visuals]]
id = "mystery.thing"
kind = "executable"
role = "thing"

[visuals.variants]
default = "visual/thing.png"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(AssetCatalogueError, "unsupported visual kind"):
                AssetCatalogue.load(manifest)

    def test_visual_paths_cannot_escape_asset_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = temp / "assets"
            catalog = root / "catalog"
            catalog.mkdir(parents=True)
            (temp / "outside.png").write_bytes(b"outside")
            manifest = catalog / "bad.toml"
            manifest.write_text(
                """
[[visuals]]
id = "ui.escape"
kind = "ui"
role = "panel"

[visuals.variants]
default = "../outside.png"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                AssetCatalogueError, "asset path escapes library"
            ):
                AssetCatalogue.load(manifest)

    def test_missing_visual_path_is_catalogue_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "assets"
            catalog = root / "catalog"
            catalog.mkdir(parents=True)
            manifest = catalog / "bad.toml"
            manifest.write_text(
                """
[[visuals]]
id = "ui.missing"
kind = "ui"
role = "panel"

[visuals.variants]
default = "visual/missing.png"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                AssetCatalogueError, "asset path does not resolve"
            ):
                AssetCatalogue.load(manifest)

    def test_icon_and_visual_ids_share_one_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "assets"
            catalog = root / "catalog"
            icons = root / "icons"
            visual = root / "visual"
            catalog.mkdir(parents=True)
            icons.mkdir()
            visual.mkdir()
            for size in (64, 128, 256):
                (icons / f"same-{size}.png").write_bytes(b"icon")
            (visual / "same.png").write_bytes(b"visual")
            manifest = catalog / "duplicate.toml"
            manifest.write_text(
                """
[[icons]]
id = "same"
category = "test"
alt_key = "asset.same"
path_64 = "icons/same-64.png"
path_128 = "icons/same-128.png"
path_256 = "icons/same-256.png"

[[visuals]]
id = "same"
kind = "ui"
role = "panel"

[visuals.variants]
default = "visual/same.png"
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(AssetCatalogueError, "duplicate asset id"):
                AssetCatalogue.load(manifest)

    def test_unknown_visual_variant_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "assets"
            catalog = root / "catalog"
            visual = root / "visual"
            catalog.mkdir(parents=True)
            visual.mkdir()
            (visual / "panel.png").write_bytes(b"panel")
            manifest = catalog / "visuals.toml"
            manifest.write_text(
                """
[[visuals]]
id = "ui.panel.base"
kind = "ui"
role = "panel"

[visuals.variants]
default = "visual/panel.png"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            asset = AssetCatalogue.load(manifest).get_visual("ui.panel.base")
            with self.assertRaisesRegex(AssetCatalogueError, "has no variant"):
                asset.path_for("hover")


if __name__ == "__main__":
    unittest.main()
