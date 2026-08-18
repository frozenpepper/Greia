from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "shape_garden"


class ShapeGardenContractTests(unittest.TestCase):
    def test_manifest_declares_pointer_interaction_without_extra_authority(self) -> None:
        with (ACTIVITY / "activity.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        self.assertEqual(raw["activity"]["id"], "org.greia.shape-garden")
        self.assertEqual(raw["activity"]["languages"], ["*"])
        self.assertEqual(raw["input"]["profile"], "pointer")
        self.assertEqual(raw["requirements"]["required_capabilities"], ["display", "pointer"])
        self.assertEqual(raw["permissions"]["requested"], [])

    def test_activity_uses_shared_logical_canvas_and_platform_navigation(self) -> None:
        source = (ACTIVITY / "main.py").read_text(encoding="utf-8")
        self.assertIn("PygameReferenceCanvas", source)
        self.assertIn("activity_viewport_for_surface", source)
        self.assertIn("canvas.pointer(event.pos)", source)
        self.assertIn("ChildUiMetrics.for_size", source)
        self.assertIn("get_theme()", source)
        self.assertIn("activity_stop_requested()", source)
        self.assertNotIn('get_icon_path("close_button"', source)
        self.assertNotIn('"close_button"', source)
        self.assertNotIn("(x - 48) ** 2", source)

    def test_reference_geometry_is_semantic_and_render_work_stays_bounded(self) -> None:
        source = (ACTIVITY / "main.py").read_text(encoding="utf-8")
        self.assertIn("REFERENCE_WIDTH = 1024", source)
        self.assertIn("REFERENCE_HEIGHT = 600", source)
        self.assertIn("SOIL_TOP = 530", source)
        self.assertIn("shapes[-120:]", source)
        self.assertIn("canvas.present(clear=theme.background)", source)
        self.assertNotIn("smooth=True", source)
        self.assertNotIn("screen.get_height() - 70", source)
        self.assertNotIn("screen.get_width(), 70", source)


if __name__ == "__main__":
    unittest.main()
