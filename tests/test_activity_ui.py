from __future__ import annotations

import unittest

from greia_platform.activity_ui import ChildUiMetrics, mix


class ChildUiMetricsTests(unittest.TestCase):
    def test_reference_geometry_keeps_large_child_controls(self) -> None:
        metrics = ChildUiMetrics.for_size(1024, 600)
        self.assertEqual(metrics.scale, 1.0)
        self.assertEqual(metrics.button_size, 58)
        self.assertEqual(metrics.toolbar_height, 78)
        first = metrics.toolbar_button(0)
        second = metrics.toolbar_button(1)
        right = metrics.toolbar_button(0, side="right")
        self.assertGreaterEqual(first.width, 56)
        self.assertGreater(second.left, first.right)
        self.assertEqual(right.right, 1024 - metrics.margin)

    def test_small_surface_scale_has_a_readability_floor(self) -> None:
        metrics = ChildUiMetrics.for_size(512, 300)
        self.assertEqual(metrics.scale, 0.5)
        self.assertGreaterEqual(metrics.button_size, 29)

    def test_large_surface_does_not_make_controls_gigantic(self) -> None:
        metrics = ChildUiMetrics.for_size(4096, 2160)
        self.assertLessEqual(metrics.scale, 3.6)
        self.assertEqual(metrics.toolbar_button(0).size, (metrics.button_size, metrics.button_size))

    def test_invalid_surface_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ChildUiMetrics.for_size(0, 600)
        with self.assertRaises(ValueError):
            ChildUiMetrics.for_size(1024, -1)

    def test_mix_is_bounded(self) -> None:
        self.assertEqual(mix((0, 10, 20), (100, 110, 120), 0.5), (50, 60, 70))
        self.assertEqual(mix((1, 2, 3), (9, 9, 9), -5), (1, 2, 3))
        self.assertEqual(mix((1, 2, 3), (9, 9, 9), 5), (9, 9, 9))


if __name__ == "__main__":
    unittest.main()
