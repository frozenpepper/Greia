from __future__ import annotations

import os
import unittest
from unittest import mock

from greia_platform import activity_ui, pygame_ui
from greia_platform.activity_ui import ChildUiMetrics, mix
from greia_platform.system_chrome import ActivitySystemChromeLayout


class ChildUiMetricsTests(unittest.TestCase):
    def test_platform_pygame_import_reexports_existing_helpers(self) -> None:
        for name in (
            "ChildUiMetrics",
            "clear_icon_cache",
            "draw_back_symbol",
            "draw_eraser_symbol",
            "draw_grid_symbol",
            "draw_home_symbol",
            "draw_icon_button",
            "draw_plus_symbol",
            "draw_undo_symbol",
            "load_icon",
            "mix",
        ):
            with self.subTest(name=name):
                self.assertIs(getattr(pygame_ui, name), getattr(activity_ui, name))

    def test_reference_geometry_keeps_large_child_controls(self) -> None:
        with mock.patch.dict(os.environ, {"GREIA_INTERFACE_SIZE": "normal"}):
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

    def test_activity_geometry_stays_outside_platform_system_chrome(self) -> None:
        for interface_size in ("compact", "normal", "large"):
            for width, height in (
                (640, 480),
                (800, 600),
                (1024, 600),
                (1366, 768),
                (1920, 1080),
                (720, 1280),
                (3840, 2160),
            ):
                with self.subTest(
                    interface_size=interface_size,
                    size=(width, height),
                ):
                    with mock.patch.dict(
                        os.environ,
                        {"GREIA_INTERFACE_SIZE": interface_size},
                    ):
                        metrics = ChildUiMetrics.for_size(width, height)
                    chrome = ActivitySystemChromeLayout.for_surface(width, height)
                    protected = chrome.protected_region
                    safe = metrics.activity_safe_rect()
                    left = metrics.activity_toolbar_button(0, side="left")
                    right = metrics.activity_toolbar_button(0, side="right")
                    content = metrics.activity_content_rect()

                    for rect in (safe, left, right, content):
                        self.assertGreaterEqual(rect.left, 0)
                        self.assertGreaterEqual(rect.top, 0)
                        self.assertLessEqual(rect.right, width)
                        self.assertLessEqual(rect.bottom, height)
                    for rect in (left, right, content):
                        overlaps = not (
                            rect.right <= protected.x
                            or protected.right <= rect.left
                            or rect.bottom <= protected.y
                            or protected.bottom <= rect.top
                        )
                        self.assertFalse(overlaps)

    def test_activity_content_rejects_impossible_bottom_reserve(self) -> None:
        with mock.patch.dict(os.environ, {"GREIA_INTERFACE_SIZE": "normal"}):
            metrics = ChildUiMetrics.for_size(640, 480)
        with self.assertRaises(ValueError):
            metrics.activity_content_rect(bottom_reserve=10_000)

    def test_small_surface_scale_has_a_readability_floor(self) -> None:
        with mock.patch.dict(os.environ, {"GREIA_INTERFACE_SIZE": "normal"}):
            metrics = ChildUiMetrics.for_size(512, 300)
        self.assertEqual(metrics.scale, 0.5)
        self.assertGreaterEqual(metrics.button_size, 29)

    def test_large_surface_does_not_make_controls_gigantic(self) -> None:
        with mock.patch.dict(os.environ, {"GREIA_INTERFACE_SIZE": "normal"}):
            metrics = ChildUiMetrics.for_size(4096, 2160)
        self.assertLessEqual(metrics.scale, 1.9)
        self.assertEqual(
            metrics.toolbar_button(0).size,
            (metrics.button_size, metrics.button_size),
        )

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