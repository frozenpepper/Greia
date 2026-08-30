from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "enciclopedia_greia"
PRESENTATION = ACTIVITY / "enciclopedia_presentation.py"
SERVICES = ACTIVITY / "enciclopedia_services.py"
EARTH = ACTIVITY / "pages" / "earth.py"
BUILD_TOOL = ROOT / "tools" / "build_encyclopedia_visual_assets.py"
RUNTIME = ACTIVITY / "assets" / "runtime"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_COLOR_TYPE_RGB = 2


class EncyclopediaFocusTreatmentTests(unittest.TestCase):
    @staticmethod
    def _function_source(path: Path, function_name: str) -> str:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                lines = source.splitlines()
                return "\n".join(lines[node.lineno - 1 : node.end_lineno])
        raise AssertionError(f"missing function {function_name!r} in {path}")

    def test_authored_focus_patch_is_outline_only_and_non_occluding(self) -> None:
        function = self._function_source(PRESENTATION, "draw_focus_patch")
        self.assertIn("pygame.draw.ellipse", function)
        self.assertIn("width=outer_width", function)
        self.assertIn("width=3", function)
        self.assertNotIn("pygame.draw.rect", function)
        self.assertNotIn("(255, 216, 83, 46)", function)
        self.assertIn("non-occluding", function)

    def test_earth_authored_focus_has_no_floating_corner_dot(self) -> None:
        draw = self._function_source(EARTH, "draw")
        self.assertIn("draw_focus_patch", draw)
        self.assertNotIn("item.rect.right - 14", draw)
        self.assertNotIn("item.rect.top + 14", draw)
        self.assertNotIn("pygame.draw.circle", draw)

    def test_full_screen_authored_scenes_use_opaque_display_surfaces(self) -> None:
        art = self._function_source(SERVICES, "art")
        character = self._function_source(SERVICES, "_shared_character")
        self.assertIn(".convert()", art)
        self.assertNotIn(".convert_alpha()", art)
        self.assertIn(".convert_alpha()", character)

    def test_builder_enforces_opaque_rgb_scene_renditions(self) -> None:
        source = BUILD_TOOL.read_text(encoding="utf-8")
        self.assertIn("PNG_COLOR_TYPE_RGB = 2", source)
        self.assertIn("def _validate_runtime_png", source)
        self.assertIn("color_type != PNG_COLOR_TYPE_RGB", source)
        self.assertIn("_validate_runtime_png(target)", source)
        self.assertIn("_validate_runtime_png(committed)", source)

    def test_existing_runtime_scene_pngs_are_opaque_rgb(self) -> None:
        if not RUNTIME.exists():
            return
        # Planet sprites are small transparent assets, not full-screen opaque scenes.
        planet_sprites = {"earth_planet_sprite.png"}
        # Also consider any future planet sprites registered in VisualLibrary.PLANET_ASSETS
        try:
            from activities.enciclopedia_greia.enciclopedia_services import VisualLibrary

            planet_sprites.update(VisualLibrary.PLANET_ASSETS.values())
        except Exception:
            pass
        for path in sorted(RUNTIME.glob("*.png")):
            data = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertGreaterEqual(len(data), 26)
                self.assertTrue(data.startswith(PNG_SIGNATURE))
                if path.name in planet_sprites:
                    # Transparent small sprite must be RGBA (color type 6)
                    self.assertEqual(data[25], 6)
                else:
                    self.assertEqual(data[25], PNG_COLOR_TYPE_RGB)


if __name__ == "__main__":
    unittest.main()
