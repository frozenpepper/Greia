from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.assets import AssetCatalogue, AssetCatalogueError
from greia_platform.pygame_visual_assets import (
    PygameVisualSurfaceCache,
    VisualSurfaceCacheError,
)


class PygameVisualSurfaceCacheTests(unittest.TestCase):
    def make_catalogue(
        self,
        *,
        default_suffix: str = ".png",
    ) -> tuple[tempfile.TemporaryDirectory[str], AssetCatalogue, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "assets"
        catalog = root / "catalog"
        visual = root / "visual"
        catalog.mkdir(parents=True)
        visual.mkdir()
        default = visual / f"panel{default_suffix}"
        focused = visual / "panel-focused.png"
        default.write_bytes(b"default")
        focused.write_bytes(b"focused")
        manifest = catalog / "visuals.toml"
        manifest.write_text(
            f"""
[[visuals]]
id = "ui.panel.base"
kind = "ui"
role = "panel"

[visuals.variants]
default = "visual/{default.name}"
focused = "visual/{focused.name}"
""".lstrip(),
            encoding="utf-8",
        )
        return temporary, AssetCatalogue.load(manifest), default, focused

    def test_same_key_loads_once_and_returns_same_surface(self) -> None:
        temporary, catalogue, default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        calls: list[Path] = []

        def load(path: Path) -> object:
            calls.append(path)
            return object()

        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=load,
            image_scaler=lambda surface, size: surface,
        )
        first = cache.get("ui.panel.base", size=(320, 210))
        second = cache.get("ui.panel.base", size=(320, 210))

        self.assertIs(first, second)
        self.assertEqual(calls, [default.resolve()])
        self.assertEqual(len(cache), 1)

    def test_size_is_part_of_key_and_scaling_is_cached(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        loads: list[Path] = []
        scales: list[tuple[object, tuple[int, int]]] = []

        def load(path: Path) -> object:
            loads.append(path)
            return ("loaded", len(loads))

        def scale(surface: object, size: tuple[int, int]) -> object:
            scales.append((surface, size))
            return ("scaled", surface, size)

        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=load,
            image_scaler=scale,
        )
        first = cache.get("ui.panel.base", size=(320, 210))
        second = cache.get("ui.panel.base", size=(320, 210))
        third = cache.get("ui.panel.base", size=(160, 105))

        self.assertIs(first, second)
        self.assertNotEqual(first, third)
        self.assertEqual(len(loads), 2)
        self.assertEqual(
            [entry[1] for entry in scales],
            [(320, 210), (160, 105)],
        )

    def test_variant_selects_explicit_variant_path(self) -> None:
        temporary, catalogue, _default, focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        calls: list[Path] = []
        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: calls.append(path) or path.name,
            image_scaler=lambda surface, size: surface,
        )

        self.assertEqual(
            cache.get("ui.panel.base", variant="focused", size=(320, 210)),
            focused.name,
        )
        self.assertEqual(calls, [focused.resolve()])

    def test_lru_bound_evicts_and_reloads_oldest_surface(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        loads: list[Path] = []
        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: loads.append(path) or (path.name, len(loads)),
            image_scaler=lambda surface, size: (surface, size),
            max_entries=2,
        )

        cache.get("ui.panel.base", size=(100, 100))
        cache.get("ui.panel.base", variant="focused", size=(100, 100))
        cache.get("ui.panel.base", size=(120, 120))
        self.assertEqual(len(cache), 2)
        cache.get("ui.panel.base", size=(100, 100))

        self.assertEqual(len(loads), 4)

    def test_clear_causes_next_request_to_reload(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        loads: list[Path] = []
        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: loads.append(path) or object(),
            image_scaler=lambda surface, size: surface,
        )

        cache.get("ui.panel.base", size=(320, 210))
        cache.clear()
        self.assertEqual(len(cache), 0)
        cache.get("ui.panel.base", size=(320, 210))

        self.assertEqual(len(loads), 2)

    def test_invalid_sizes_fail_before_loading(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: self.fail("loader should not run"),
            image_scaler=lambda surface, size: surface,
        )

        invalid = ((0, 100), (100, 0), (2049, 100), (100, 2049), (True, 100))
        for size in invalid:
            with self.subTest(size=size), self.assertRaises(VisualSurfaceCacheError):
                cache.get("ui.panel.base", size=size)  # type: ignore[arg-type]

    def test_surface_pixel_budget_is_bounded(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: self.fail("loader should not run"),
            image_scaler=lambda surface, size: surface,
            max_surface_pixels=10_000,
        )

        with self.assertRaisesRegex(VisualSurfaceCacheError, "too large"):
            cache.get("ui.panel.base", size=(101, 100))

    def test_total_pixel_budget_evicts_least_recent_renditions(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        loads: list[Path] = []
        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: loads.append(path) or object(),
            image_scaler=lambda surface, size: surface,
            max_entries=50,
            max_surface_pixels=10_000,
            max_total_pixels=25_000,
        )

        cache.get("ui.panel.base", size=(100, 100))
        cache.get("ui.panel.base", variant="focused", size=(100, 100))
        cache.get("ui.panel.base", size=(100, 100))  # refresh LRU position
        self.assertEqual(cache.cached_pixels, 20_000)
        cache.get("ui.panel.base", size=(100, 90))  # 29,000 > budget
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache.cached_pixels, 19_000)
        cache.get("ui.panel.base", size=(100, 100))  # recent: still cached
        self.assertEqual(len(loads), 3)
        cache.get("ui.panel.base", variant="focused", size=(100, 100))
        self.assertEqual(len(loads), 4)  # the least recent one was evicted
        cache.clear()
        self.assertEqual(cache.cached_pixels, 0)

    def test_total_pixel_budget_must_fit_one_maximal_surface(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(ValueError):
            PygameVisualSurfaceCache(
                catalogue,
                image_loader=lambda path: object(),
                image_scaler=lambda surface, size: surface,
                max_surface_pixels=10_000,
                max_total_pixels=9_999,
            )

    def test_runtime_rejects_svg_catalogue_paths(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue(
            default_suffix=".svg"
        )
        self.addCleanup(temporary.cleanup)
        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: self.fail("SVG must not reach runtime loader"),
            image_scaler=lambda surface, size: surface,
        )

        with self.assertRaisesRegex(VisualSurfaceCacheError, "PNG rendition"):
            cache.get("ui.panel.base", size=(320, 210))

    def test_unknown_asset_and_variant_remain_catalogue_errors(self) -> None:
        temporary, catalogue, _default, _focused = self.make_catalogue()
        self.addCleanup(temporary.cleanup)
        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: object(),
            image_scaler=lambda surface, size: surface,
        )

        with self.assertRaises(AssetCatalogueError):
            cache.get("unknown", size=(100, 100))
        with self.assertRaises(AssetCatalogueError):
            cache.get("ui.panel.base", variant="missing", size=(100, 100))


if __name__ == "__main__":
    unittest.main()
