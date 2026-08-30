from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES = ROOT / "activities"


class CoreActivitySystemSafeUiTests(unittest.TestCase):
    def test_painting_and_writing_use_shared_activity_safe_geometry(self) -> None:
        for activity in ("painting", "writing"):
            with self.subTest(activity=activity):
                # For decomposed Activities the geometry may live in app/renderer modules;
                # inspect the whole package so the test validates the contract not the file layout.
                pkg_sources = "".join(
                    p.read_text(encoding="utf-8")
                    for p in sorted((ACTIVITIES / activity).glob("*.py"))
                )
                # Keep legacy main.py check for historical Activities, but allow app-owned geometry.
                legacy_source = (ACTIVITIES / activity / "main.py").read_text(encoding="utf-8")
                combined = legacy_source + pkg_sources
                self.assertIn("activity_toolbar_button", combined)
                self.assertIn("activity_content_rect", combined)
                self.assertNotIn(".toolbar_button(", combined)
                self.assertNotIn('"close_button"', combined)
                self.assertIn("activity_stop_requested()", combined)

    def test_painting_palette_is_anchored_to_activity_safe_rect(self) -> None:
        source = (ACTIVITIES / "painting" / "main.py").read_text(encoding="utf-8")
        self.assertIn("self.metrics.activity_safe_rect()", source)
        self.assertIn("bottom_reserve=self.palette_height", source)
        self.assertNotIn("self.screen.get_height() - self.metrics.margin - self.palette_height", source)

    def test_writing_editor_is_owned_by_shared_activity_content_geometry(self) -> None:
        # Geometry may live in writing_app after decomposition; scan the package.
        pkg_sources = "".join(
            p.read_text(encoding="utf-8") for p in sorted((ACTIVITIES / "writing").glob("*.py"))
        )
        self.assertIn("return self.metrics.activity_content_rect(top_gap=6)", pkg_sources)
        self.assertNotIn("self.screen.get_width() - self.metrics.margin * 2", pkg_sources)


if __name__ == "__main__":
    unittest.main()
