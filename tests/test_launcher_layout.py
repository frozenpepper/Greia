from __future__ import annotations

import unittest
from pathlib import Path

from greia_launcher.main import calculate_grid_page


class LauncherLayoutTests(unittest.TestCase):
    def test_activity_page_contains_selected_item_and_stays_bounded(self) -> None:
        first = calculate_grid_page(17, 0, columns=3, max_rows=2)
        self.assertEqual((first.start, first.stop, first.rows), (0, 6, 2))
        self.assertEqual(first.page_count, 3)

        middle = calculate_grid_page(17, 7, columns=3, max_rows=2)
        self.assertEqual((middle.start, middle.stop), (6, 12))
        self.assertLessEqual(middle.stop - middle.start, 6)

        last = calculate_grid_page(17, 16, columns=3, max_rows=2)
        self.assertEqual((last.start, last.stop, last.rows), (12, 17, 2))

    def test_profile_pages_fit_two_rows_on_low_resolution(self) -> None:
        first = calculate_grid_page(8, 0, columns=3, max_rows=2)
        second = calculate_grid_page(8, 7, columns=3, max_rows=2)
        self.assertEqual((first.start, first.stop, first.rows), (0, 6, 2))
        self.assertEqual((second.start, second.stop, second.rows), (6, 8, 1))

    def test_launcher_observes_display_surface_size_changes(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "src/greia_launcher/main.py"
        ).read_text()
        self.assertIn("pygame.display.get_surface()", source)
        self.assertIn("self._icon_cache.clear()", source)


if __name__ == "__main__":
    unittest.main()
