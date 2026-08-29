from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "enciclopedia_greia"
PRESENTATION = ACTIVITY / "enciclopedia_presentation.py"
EARTH = ACTIVITY / "pages" / "earth.py"


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


if __name__ == "__main__":
    unittest.main()
