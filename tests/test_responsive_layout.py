from __future__ import annotations

import random
import unittest

from greia_platform.responsive_layout import AdaptiveGridPolicy, UiRect, Viewport


REPRESENTATIVE_VIEWPORTS = (
    (640, 480),
    (800, 600),
    (1024, 600),
    (1024, 768),
    (1280, 720),
    (1366, 768),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
    (720, 1280),
)


class ViewportTests(unittest.TestCase):
    def test_viewport_has_no_hardware_identity_and_scales_local_measures(self) -> None:
        small = Viewport(640, 480)
        reference = Viewport(1024, 600)
        large = Viewport(3840, 2160)

        self.assertLess(
            small.bounded_px(24, minimum=8, maximum=40),
            reference.bounded_px(24, minimum=8, maximum=40),
        )
        self.assertEqual(large.bounded_px(24, minimum=8, maximum=40), 40)
        self.assertAlmostEqual(reference.aspect_ratio, 1024 / 600)

    def test_inset_never_produces_negative_geometry(self) -> None:
        rect = UiRect(0, 0, 20, 10).inset(100, 100)
        self.assertGreaterEqual(rect.width, 0)
        self.assertGreaterEqual(rect.height, 0)


class AdaptiveGridTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = AdaptiveGridPolicy(
            minimum_item_px=72,
            preferred_item_px=160,
            maximum_item_px=220,
            minimum_gap_px=6,
            maximum_gap_px=24,
            maximum_columns=6,
            maximum_rows=3,
        )

    def test_representative_resolutions_keep_every_visible_cell_inside_content(self) -> None:
        for width, height in REPRESENTATIVE_VIEWPORTS:
            with self.subTest(width=width, height=height):
                viewport = Viewport(width, height)
                header = viewport.bounded_px(86, minimum=56, maximum=120)
                margin = viewport.bounded_px(20, minimum=8, maximum=36)
                content = UiRect(
                    margin,
                    header,
                    max(1, width - margin * 2),
                    max(1, height - header - margin),
                )
                layout = self.policy.layout(content, 50)
                self.assertGreaterEqual(layout.capacity, 1)
                self.assertLessEqual(layout.capacity, 18)
                for index in range(layout.capacity):
                    self.assertTrue(content.contains(layout.cell(index)))

    def test_layout_reflows_instead_of_using_one_resolution_breakpoint(self) -> None:
        narrow = self.policy.layout(UiRect(0, 0, 420, 700), 30)
        wide = self.policy.layout(UiRect(0, 0, 1600, 700), 30)

        self.assertLess(narrow.columns, wide.columns)
        self.assertGreaterEqual(narrow.rows, 1)
        self.assertGreaterEqual(wide.rows, 1)

    def test_tiny_content_fails_contained_not_offscreen(self) -> None:
        content = UiRect(10, 10, 40, 35)
        layout = self.policy.layout(content, 8)
        self.assertTrue(layout.constrained)
        self.assertEqual(layout.capacity, 1)
        self.assertTrue(content.contains(layout.cell(0)))

    def test_empty_collection_has_no_cells(self) -> None:
        layout = self.policy.layout(UiRect(0, 0, 800, 600), 0)
        self.assertEqual(layout.capacity, 0)
        with self.assertRaises(IndexError):
            layout.cell(0)

    def test_many_generated_viewports_preserve_containment(self) -> None:
        # Deterministic stress probe: the representative matrix is not a whitelist.
        rng = random.Random(0x6A7E1A)
        for _ in range(2000):
            width = rng.randint(240, 4096)
            height = rng.randint(200, 2160)
            left = rng.randint(0, min(80, width - 1))
            top = rng.randint(0, min(120, height - 1))
            content = UiRect(
                left,
                top,
                max(1, width - left - rng.randint(0, min(80, width - left - 1))),
                max(1, height - top - rng.randint(0, min(80, height - top - 1))),
            )
            layout = self.policy.layout(content, rng.randint(1, 80))
            self.assertGreaterEqual(layout.capacity, 1)
            for index in range(layout.capacity):
                self.assertTrue(content.contains(layout.cell(index)))

    def test_invalid_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AdaptiveGridPolicy(minimum_item_px=200, preferred_item_px=100)


if __name__ == "__main__":
    unittest.main()
