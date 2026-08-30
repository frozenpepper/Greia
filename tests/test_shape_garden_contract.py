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
        combined = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ACTIVITY.glob("*.py")))
        self.assertIn("PygameReferenceCanvas", combined)
        self.assertIn("activity_viewport_for_surface", combined)
        # Pointer mapping stays platform-owned via PygameReferenceCanvas
        self.assertIn("canvas.pointer", combined)
        self.assertIn("ChildUiMetrics.for_size", combined)
        self.assertIn("get_theme()", combined)
        self.assertIn("activity_stop_requested()", combined)
        self.assertNotIn('get_icon_path("close_button"', combined)
        self.assertNotIn('"close_button"', combined)
        self.assertNotIn("(x - 48) ** 2", combined)

    def test_reference_geometry_is_semantic_and_render_work_stays_bounded(self) -> None:
        combined = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ACTIVITY.glob("*.py")))
        # Reference geometry kept semantics after decomposition
        self.assertIn("REFERENCE_WIDTH", combined)
        self.assertIn("1024", combined)
        self.assertIn("REFERENCE_HEIGHT", combined)
        self.assertIn("600", combined)
        self.assertIn("SOIL_TOP", combined)
        self.assertIn("530", combined)
        # Bounded window for shapes/particles — either literal slice or MAX_SHAPES constant
        self.assertTrue(
            "shapes[-120:]" in combined
            or "MAX_SHAPES" in combined
            or "active_shapes" in combined,
            "bounded shape window not found",
        )
        self.assertIn("present(clear=", combined)
        self.assertIn("theme.background", combined)
        self.assertNotIn("smooth=True", combined)
        self.assertNotIn("screen.get_height() - 70", combined)
        self.assertNotIn("screen.get_width(), 70", combined)


if __name__ == "__main__":
    unittest.main()
