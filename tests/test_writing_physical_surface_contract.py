from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WRITING_MAIN = ROOT / "activities" / "writing" / "main.py"


class WritingPhysicalSurfaceContractTests(unittest.TestCase):
    """Prevent the Acer blank-frame failure caused by mixed canvas ownership."""

    def test_production_composition_does_not_create_reference_canvas(self) -> None:
        source = WRITING_MAIN.read_text(encoding="utf-8")
        self.assertNotIn(
            "from greia_platform.pygame_canvas import PygameReferenceCanvas",
            source,
        )
        self.assertNotIn("PygameReferenceCanvas(", source)

    def test_production_writing_app_disables_legacy_optional_canvas_seam(self) -> None:
        tree = ast.parse(WRITING_MAIN.read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "WritingApp"
        ]
        self.assertEqual(len(calls), 1)
        canvas_keywords = [keyword for keyword in calls[0].keywords if keyword.arg == "canvas"]
        self.assertEqual(len(canvas_keywords), 1)
        self.assertIsInstance(canvas_keywords[0].value, ast.Constant)
        self.assertIsNone(canvas_keywords[0].value.value)


if __name__ == "__main__":
    unittest.main()
