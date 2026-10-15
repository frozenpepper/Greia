from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "painting"


def _load_painting_module():
    # Prefer package import for decomposed Activities so sibling modules
    # resolve via relative imports (mirrors test_core_creation_activities).
    try:
        import importlib

        mod = importlib.import_module("activities.painting.main")
        sys.modules["painting_test_mod"] = mod
        return mod
    except Exception:
        pass
    spec = importlib.util.spec_from_file_location(
        "activities.painting.main",
        ACTIVITY_ROOT / "main.py",
        submodule_search_locations=[str(ACTIVITY_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load painting main.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["painting_test_mod"] = mod
    sys.modules["activities.painting.main"] = mod
    if "activities.painting" not in sys.modules:
        import types

        pkg_mod = types.ModuleType("activities.painting")
        pkg_mod.__path__ = [str(ACTIVITY_ROOT)]  # type: ignore[attr-defined]
        sys.modules["activities.painting"] = pkg_mod
    spec.loader.exec_module(mod)
    return mod


class PaintingContractTests(unittest.TestCase):

    def test_studio_ui_is_word_free_and_status_is_pictorial(self) -> None:
        # Superseded policy: the save badge used to render localized words
        # ("SAVED"/"SALVATO"). Painting is now word-free for pre-readers: the
        # status is a pictogram (tick / dots / "!") and every control is an icon.
        import json

        renderer_source = (ACTIVITY_ROOT / "painting_renderer.py").read_text(encoding="utf-8")
        controls_source = (ACTIVITY_ROOT / "painting_controls.py").read_text(encoding="utf-8")
        app_source = (ACTIVITY_ROOT / "painting_app.py").read_text(encoding="utf-8")
        for source in (renderer_source, controls_source, app_source):
            self.assertNotIn("typography.render(", source)
            self.assertNotIn("label=", source)
            self.assertNotIn("caption=", source)
        self.assertIn('"saved", "saving", "error"', renderer_source)
        # Locale bundles stay in four-locale key parity for the title and
        # retained keys even though the studio draws no words.
        keys = None
        for language in ("en", "it", "es", "fr"):
            with self.subTest(language=language):
                bundle = json.loads((ACTIVITY_ROOT / "locales" / f"{language}.json").read_text(encoding="utf-8"))
                self.assertTrue(bundle["strings"]["activity.painting.title"])
                keys = keys or set(bundle["strings"])
                self.assertEqual(set(bundle["strings"]), keys)

    def test_controls_use_the_shared_kit(self) -> None:
        app_source = (ACTIVITY_ROOT / "painting_app.py").read_text(encoding="utf-8")
        controls_source = (ACTIVITY_ROOT / "painting_controls.py").read_text(encoding="utf-8")
        self.assertIn("ControlKit", app_source)
        self.assertIn("CastFeedback", app_source)
        self.assertIn("PygameControlInput", app_source)
        self.assertIn("SurfaceNavigator", app_source)
        self.assertIn("kit.icon_button(", controls_source)
        self.assertIn("kit.tool_strip(", controls_source)
        self.assertNotIn("_draw_tactile_button", app_source + controls_source)

    def test_painting_manifest_contract(self) -> None:
        manifest_path = ACTIVITY_ROOT / "activity.toml"
        self.assertTrue(manifest_path.exists(), "activity.toml must exist")
        text = manifest_path.read_text(encoding="utf-8")
        self.assertIn('id = "org.greia.painting"', text)
        self.assertIn('entrypoint = "main.py"', text)
        self.assertIn('profile = "pointer"', text)

    def test_forbidden_imports_absent_from_activity(self) -> None:
        main_path = ACTIVITY_ROOT / "main.py"
        self.assertTrue(main_path.exists(), "main.py must exist")
        tree = ast.parse(main_path.read_text(encoding="utf-8"), filename=str(main_path))
        forbidden = {"os", "sys"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], forbidden, f"Forbidden import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertNotIn(node.module.split(".")[0], forbidden, f"Forbidden import from: {node.module}")

    def test_runtime_assets_exist(self) -> None:
        runtime_dir = ACTIVITY_ROOT / "assets" / "runtime"
        self.assertTrue(runtime_dir.exists(), "assets/runtime directory must exist")
        # Undo/new/eraser/share/import/trash/arrows are shared icon.hud.*
        # glyphs; only Painting-specific art stays private.
        required_assets = [
            "tool_gallery.png",
            "tool_colouring.png",
            "color_well_dish.png",
            "colouring_garden.png",
            "colouring_sea.png",
            "colouring_pets.png",
        ]
        for asset_name in required_assets:
            p = runtime_dir / asset_name
            self.assertTrue(p.exists(), f"Runtime asset missing: {asset_name}")
            self.assertGreater(p.stat().st_size, 0, f"Runtime asset is empty: {asset_name}")

    def test_color_and_brush_definitions(self) -> None:
        mod = _load_painting_module()
        self.assertEqual(len(mod.COLORS), 10, "Painting must have 10 standard child colors")
        self.assertEqual(len(mod.BRUSH_SIZES), 3, "Painting must have 3 standard brush sizes")
        self.assertEqual(mod.MAX_UNDO_STROKES, 24, "Painting must support 24 undo strokes")
        self.assertEqual(mod.MAX_PAINTINGS, 48, "Painting must support up to 48 paintings")


class PaintingSwatchGeometryTests(unittest.TestCase):
    """Pin 46px swatch hit targets through the real renderer geometry."""

    def test_swatches_measure_46px_with_no_palette_overlap_at_reference(self) -> None:
        import os

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame

        try:
            pygame.init()
        except Exception:
            pass
        try:
            from greia_platform.activity_ui import ChildUiMetrics

            mod = _load_painting_module()
            metrics = ChildUiMetrics.for_size(1024, 600)
            pygame.display.set_mode((1024, 600))
            screen = pygame.Surface((1024, 600))
            renderer = mod.PaintingRenderer(metrics, None, screen)

            swatches = renderer._color_buttons()
            self.assertEqual(len(swatches), 10, "Palette must expose 10 swatches")
            for rect, _index in swatches:
                self.assertGreaterEqual(rect.width, 46, f"Swatch too narrow: {rect}")
                self.assertGreaterEqual(rect.height, 46, f"Swatch too short: {rect}")

            sizes = renderer._size_buttons()
            self.assertEqual(len(sizes), 3, "Palette must expose 3 brush size buttons")
            self.assertEqual([index for _rect, index in sizes], [0, 1, 2], "sizes run small to large")
            tools = list(renderer.tool_buttons())

            # No pairwise overlap between swatches.
            rects = [rect for rect, _index in swatches]
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    self.assertFalse(
                        rects[i].colliderect(rects[j]),
                        f"Swatches {i} and {j} overlap: {rects[i]} vs {rects[j]}",
                    )

            # No overlap between swatches, brush sizes and the eraser/stamp tiles.
            others = [rect for rect, _index in sizes] + tools
            for i, swatch in enumerate(rects):
                for j, other in enumerate(others):
                    self.assertFalse(swatch.colliderect(other), f"Swatch {i} overlaps tool {j}")
            for i in range(len(others)):
                for j in range(i + 1, len(others)):
                    self.assertFalse(others[i].colliderect(others[j]), f"Tools {i} and {j} overlap")

            # Separator sits between the brush sizes and the eraser/stamp tiles.
            sep_x = renderer.separator_x()
            self.assertGreater(sep_x, max(rect.right for rect, _ in sizes))
            self.assertLess(sep_x, min(rect.left for rect in tools))
            tray = renderer.tray_rect()
            for rect in rects + others:
                self.assertTrue(tray.contains(rect), f"{rect} leaves the tray {tray}")

            # Dish blit stays keyed to the 46px swatch diameter.
            if renderer._scaled_dish is not None:
                expected = metrics.px(46) + metrics.px(6)
                self.assertEqual(renderer._scaled_dish.get_size(), (expected, expected))
        finally:
            try:
                pygame.quit()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
