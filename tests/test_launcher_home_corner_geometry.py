"""Top-right Home corner: the time-left pill never sits under the badge star.

Regression for the Acer sweep (2026-10-16_ACER_ACTIVITY_SWEEP.md (archived; see git history)
P3): the star was drawn over the right end of the pill, hiding "OGGI".
"""
import unittest

from greia_launcher.home_layout import (
    CollectionHomeLayout,
    achievement_button_rect,
    usage_pill_band,
    usage_pill_rect,
)
from greia_platform.responsive_layout import UiRect

SIZES = ((1024, 600), (800, 480), (1280, 800), (1366, 768), (640, 480), (480, 320))


def overlaps(a: UiRect, b: UiRect) -> bool:
    return a.x < b.x + b.width and b.x < a.x + a.width and a.y < b.y + b.height and b.y < a.y + a.height


def badge_size(height: int) -> int:
    return max(62, min(86, height // 7))


class HomeCornerGeometryTests(unittest.TestCase):
    def test_pill_is_left_of_star_and_right_of_profile_badge(self):
        for width, height in SIZES:
            star = achievement_button_rect(width, height)
            badge = UiRect(14, 10, badge_size(height), badge_size(height))
            for content in (140, 260, 420, 2000):  # short, typical, long, absurd
                pill = usage_pill_rect(width, height, content, 42, left_limit=14 + badge_size(height))
                with self.subTest(size=(width, height), content=content):
                    self.assertFalse(overlaps(pill, star))
                    self.assertLessEqual(pill.x + pill.width, star.x)
                    if width >= 640:
                        self.assertFalse(overlaps(pill, badge))

    def test_reference_sizes_keep_their_portal_grid(self):
        # The pill must not push the grid down where it already fits (1024x600: y=71).
        star = achievement_button_rect(1024, 600)
        reserved = (UiRect(14, 10, 85, 85), UiRect(star.x, star.y, star.width + 4, star.height + 4))
        layout = CollectionHomeLayout.compute(1024, 600, 6, 3, reserved=reserved)
        band = usage_pill_band(1024, 600, left_limit=14 + 85)
        self.assertFalse(any(overlaps(band, hit) for hit in layout.hits))
        self.assertEqual(layout.portals[0].y, 71)

    def test_pill_does_not_cover_portals(self):
        for width, height in SIZES:
            star = achievement_button_rect(width, height)
            badge = badge_size(height)
            reserved = (UiRect(14, 10, badge, badge), UiRect(star.x, star.y, star.width + 4, star.height + 4))
            columns = 3 if width >= height else 2
            # Mirrors CollectionFirstHomeMixin._render_collection_home's two-pass rule.
            band = usage_pill_band(width, height, left_limit=14 + badge)
            layout = CollectionHomeLayout.compute(width, height, 6, columns, reserved=reserved)
            if any(overlaps(band, hit) for hit in layout.hits):
                layout = CollectionHomeLayout.compute(width, height, 6, columns, reserved=(*reserved, band))
            pill = band
            for hit in layout.hits:
                with self.subTest(size=(width, height), hit=hit):
                    self.assertFalse(overlaps(pill, hit))


if __name__ == "__main__":
    unittest.main()
