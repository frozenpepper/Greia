from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES = ROOT / "activities"


class CoreActivitySystemSafeUiTests(unittest.TestCase):
    def test_painting_and_writing_use_shared_activity_safe_geometry(self) -> None:
        for activity in ("painting", "writing"):
            with self.subTest(activity=activity):
                source = (ACTIVITIES / activity / "main.py").read_text(encoding="utf-8")
                self.assertIn("activity_toolbar_button", source)
                self.assertIn("activity_content_rect", source)
                self.assertNotIn(".toolbar_button(", source)
                self.assertNotIn('"close_button"', source)
                self.assertIn("activity_stop_requested()", source)

    def test_painting_palette_is_anchored_to_activity_safe_rect(self) -> None:
        source = (ACTIVITIES / "painting" / "main.py").read_text(encoding="utf-8")
        self.assertIn("self.metrics.activity_safe_rect()", source)
        self.assertIn("bottom_reserve=self.palette_height", source)
        self.assertNotIn("self.screen.get_height() - self.metrics.margin - self.palette_height", source)

    def test_writing_editor_is_owned_by_shared_activity_content_geometry(self) -> None:
        source = (ACTIVITIES / "writing" / "main.py").read_text(encoding="utf-8")
        self.assertIn("return self.metrics.activity_content_rect(top_gap=6)", source)
        self.assertNotIn("self.screen.get_width() - self.metrics.margin * 2", source)


if __name__ == "__main__":
    unittest.main()
