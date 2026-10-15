from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "shape_garden"


def _source() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(ACTIVITY.glob("*.py")))


class ShapeGardenContractTests(unittest.TestCase):
    def test_manifest_declares_pointer_interaction_without_extra_authority(self) -> None:
        with (ACTIVITY / "activity.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        self.assertEqual(raw["activity"]["id"], "org.greia.shape-garden")
        self.assertEqual(raw["activity"]["legacy_ids"], ["shape_garden"])
        self.assertEqual(raw["activity"]["languages"], ["*"])
        self.assertEqual(raw["input"]["profile"], "pointer")
        self.assertEqual(raw["requirements"]["required_capabilities"], ["display", "pointer"])
        self.assertEqual(raw["permissions"]["requested"], [])
        self.assertEqual(raw["storage"]["schema_version"], 1)  # migration is additive, in-app
        self.assertEqual(raw["creations"], {"produces": ["image/png"], "consumes": ["image/png"]})
        skills = {skill["id"] for skill in raw["education"]["skills"]}
        self.assertIn("math.geometry.shape_recognition", skills)
        self.assertIn("creativity.visual_composition", skills)

    def test_platform_canvas_kit_navigation_and_pointer(self) -> None:
        combined = _source()
        for needle in (
            "PygameReferenceCanvas",
            "activity_viewport_for_surface",
            "canvas.pointer",
            "ControlLayout.for_canvas",
            "ControlKit(",
            "PygameControlInput(",
            "SurfaceNavigator(",
            "CastFeedback(",
            "self.canvas.present(clear=self.theme.background",
            "activity_stop_requested()",
            "mark_activity_ready()",
        ):
            self.assertIn(needle, combined, needle)
        # The platform pointer is never switched off; only the controller's
        # virtual pointer replaces it while the stick drives.
        self.assertNotIn("pointer=False", combined)
        self.assertNotIn('"close_button"', combined)
        self.assertNotIn("set_visible(True)", combined)

    def test_art_is_shared_library_by_semantic_id(self) -> None:
        combined = _source()
        self.assertIn('f"prop.shape.{kind}"', combined)
        self.assertIn('"character.dani"', combined)
        content = (ACTIVITY / "garden_content.py").read_text(encoding="utf-8")
        self.assertTrue(re.search(r'f"bg\.meadow_day\.\{n\}"', content))
        for glyph in ("undo", "share", "new", "rotate", "trash", "import", "drag_hint"):
            self.assertIn(f'"{glyph}"', combined, glyph)
        for name in ("tool_gallery", "tool_ghost", "tool_grow", "tool_shrink", "tool_back"):
            self.assertTrue((ACTIVITY / "assets" / "runtime" / f"{name}.png").is_file(), name)
            self.assertTrue((ACTIVITY / "assets" / "source" / f"{name}.svg").is_file(), name)
        self.assertTrue((ACTIVITY / "assets" / "source" / "icon.svg").is_file())

    def test_private_svg_sources_follow_the_forbidden_construct_lint(self) -> None:
        forbidden = re.compile(
            r'<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script|foreignObject'
            r'|<animate|blend-mode|skew|href="[^#]|xlink:href="[^#]|sodipodi|inkscape:'
        )
        for svg in sorted((ACTIVITY / "assets" / "source").glob("*.svg")):
            text = svg.read_text(encoding="utf-8")
            self.assertIsNone(forbidden.search(text), svg.name)
            self.assertLessEqual(len(text.encode()), 6 * 1024, svg.name)

    def test_locale_bundles_keep_key_parity_and_name_every_shape(self) -> None:
        from activities.shape_garden.garden_content import SHAPE_KINDS

        bundles = {
            locale: json.loads((ACTIVITY / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            self.assertEqual(set(bundle["strings"]), keys, locale)
        for kind in SHAPE_KINDS:
            self.assertIn(f"shape.{kind}", keys)

    def test_bounded_state_and_caches(self) -> None:
        from activities.shape_garden.garden_content import MAX_GARDENS, MAX_SHAPES, MAX_UNDO

        self.assertEqual((MAX_SHAPES, MAX_GARDENS, MAX_UNDO), (120, 24, 24))
        combined = _source()
        self.assertIn("BoundedCache(", combined)
        self.assertIn("THUMBNAIL_LIMIT", combined)


if __name__ == "__main__":
    unittest.main()
