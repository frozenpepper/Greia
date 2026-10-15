"""Core icons build only from catalogued flat SVG masters (tools/build_core_icons.py)."""

from __future__ import annotations

import importlib.util
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "build_core_icons.py"
spec = importlib.util.spec_from_file_location("build_core_icons", TOOL_PATH)
assert spec is not None and spec.loader is not None
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)

ASSETS = PROJECT_ROOT / "assets"
CATALOG = ASSETS / "catalog" / "core_icons_v1.toml"
_ENTRY = """
[[icons]]
id = "{id}"
category = "test"
alt_key = "asset.{id}"
path_64 = "icons/core/v1/64/{id}.png"
path_128 = "icons/core/v1/128/{id}.png"
path_256 = "icons/core/v1/256/{id}.png"
source_svg = "source/icons/core/v1/{id}.svg"
"""
_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256"/>'


def _png_header(size: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + struct.pack(">II", size, size)


class RepositoryCoreIconInventoryTests(unittest.TestCase):
    def test_every_icon_has_a_linted_master_and_no_orphans(self) -> None:
        specs = builder.load_specs(CATALOG, ASSETS)
        builder.verify_inventory(specs, ASSETS)
        self.assertEqual(len(specs), 29)

    def test_retired_glossy_route_is_gone(self) -> None:
        self.assertFalse((PROJECT_ROOT / "tools" / "extract_core_icons.py").exists())
        self.assertFalse((ASSETS / "source" / "core_icons_v1_source.png").exists())
        makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("tools/build_core_icons.py --check", makefile)
        self.assertNotIn("extract_core_icons", makefile)

    def test_committed_renditions_have_contract_dimensions(self) -> None:
        for icon in builder.load_specs(CATALOG, ASSETS):
            for rendition in icon.renditions:
                builder._verify_png(rendition.output, rendition.size)

    @unittest.skipUnless(shutil.which("rsvg-convert"), "rsvg-convert not on this host")
    def test_committed_pngs_match_a_fresh_render(self) -> None:
        specs = builder.load_specs(CATALOG, ASSETS)
        rasterizer = builder._resolve_rasterizer("rsvg-convert")
        self.assertEqual(builder.check_all(specs, rasterizer, tolerance=2), [])


class CoreIconInventoryGuardTests(unittest.TestCase):
    def make_tree(self, ids: tuple[str, ...]) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        assets = Path(temporary.name) / "assets"
        (assets / "catalog").mkdir(parents=True)
        (assets / "source/icons/core/v1").mkdir(parents=True)
        for size in builder.SIZES:
            (assets / f"icons/core/v1/{size}").mkdir(parents=True)
        for asset_id in ids:
            (assets / f"source/icons/core/v1/{asset_id}.svg").write_text(_SVG, encoding="utf-8")
            for size in builder.SIZES:
                (assets / f"icons/core/v1/{size}/{asset_id}.png").write_bytes(_png_header(size))
        (assets / "catalog/core.toml").write_text(
            "".join(_ENTRY.format(id=asset_id) for asset_id in ids), encoding="utf-8"
        )
        return temporary, assets

    def test_valid_tree_passes(self) -> None:
        temporary, assets = self.make_tree(("star",))
        with temporary:
            specs = builder.load_specs(assets / "catalog/core.toml", assets)
            builder.verify_inventory(specs, assets)

    def test_entry_without_master_is_rejected(self) -> None:
        temporary, assets = self.make_tree(("star",))
        with temporary:
            catalog = assets / "catalog/core.toml"
            catalog.write_text(
                catalog.read_text(encoding="utf-8").replace('source_svg = "source/icons/core/v1/star.svg"\n', ""),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(builder.CoreIconBuildError, "no source_svg"):
                builder.load_specs(catalog, assets)

    def test_uncatalogued_png_is_rejected(self) -> None:
        temporary, assets = self.make_tree(("star",))
        with temporary:
            (assets / "icons/core/v1/64/retired.png").write_bytes(_png_header(64))
            specs = builder.load_specs(assets / "catalog/core.toml", assets)
            with self.assertRaisesRegex(builder.CoreIconBuildError, "uncatalogued core icon PNG"):
                builder.verify_inventory(specs, assets)

    def test_uncatalogued_master_is_rejected(self) -> None:
        temporary, assets = self.make_tree(("star",))
        with temporary:
            (assets / "source/icons/core/v1/extra.svg").write_text(_SVG, encoding="utf-8")
            specs = builder.load_specs(assets / "catalog/core.toml", assets)
            with self.assertRaisesRegex(builder.CoreIconBuildError, "uncatalogued core icon master"):
                builder.verify_inventory(specs, assets)

    def test_forbidden_svg_construct_is_rejected(self) -> None:
        temporary, assets = self.make_tree(("star",))
        with temporary:
            (assets / "source/icons/core/v1/star.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><filter id="f"/></svg>', encoding="utf-8"
            )
            specs = builder.load_specs(assets / "catalog/core.toml", assets)
            with self.assertRaisesRegex(builder.CoreIconBuildError, "forbidden SVG construct"):
                builder.verify_inventory(specs, assets)

    def test_output_outside_size_directory_is_rejected(self) -> None:
        temporary, assets = self.make_tree(("star",))
        with temporary:
            catalog = assets / "catalog/core.toml"
            catalog.write_text(
                catalog.read_text(encoding="utf-8").replace(
                    'path_64 = "icons/core/v1/64/star.png"', 'path_64 = "icons/core/v1/128/star.png"'
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(builder.CoreIconBuildError, "path_64 must live"):
                builder.load_specs(catalog, assets)


if __name__ == "__main__":
    unittest.main()
