from __future__ import annotations

import random
import unittest

from greia_launcher.system_chrome import collection_policy_for_metrics
from greia_platform.display_metrics import (
    DisplayMetricsSource,
    sanitize_display_metrics,
)
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


class PhysicalCollectionMinimumTests(unittest.TestCase):
    """DisplayMetrics → PhysicalUiPolicy → pixel minimum → AdaptiveGridPolicy."""

    def _dense(self):  # ~234 DPI panel: 10mm floor is 92px.
        metrics = sanitize_display_metrics(
            2048, 1200, 222.0, 130.0, DisplayMetricsSource.MANUAL_OVERRIDE
        )
        assert metrics is not None
        return metrics

    def test_unknown_metrics_keep_base_minimum(self) -> None:
        for metrics in (None, sanitize_display_metrics(1024, 600)):
            with self.subTest(metrics=repr(metrics)):
                policy = collection_policy_for_metrics(metrics)
                self.assertEqual(policy.minimum_item_px, 72)
                self.assertEqual(policy.preferred_item_px, 160)
                self.assertEqual(policy.maximum_item_px, 220)

    def test_high_density_raises_only_the_minimum(self) -> None:
        grown = collection_policy_for_metrics(self._dense())
        self.assertEqual(grown.minimum_item_px, 92)
        self.assertEqual(grown.preferred_item_px, 160)
        self.assertEqual(grown.maximum_item_px, 220)
        self.assertEqual(grown.minimum_gap_px, 6)
        self.assertEqual(grown.maximum_gap_px, 24)
        self.assertEqual(grown.maximum_columns, 6)
        self.assertEqual(grown.maximum_rows, 3)

    def test_malformed_metrics_yield_base_policy(self) -> None:
        self.assertEqual(
            collection_policy_for_metrics("bogus"),
            collection_policy_for_metrics(None),
        )

    def test_extreme_density_caps_floor_at_preferred(self) -> None:
        # ~690 DPI: the raw 10mm floor (~270px) exceeds the preferred tile, so
        # the policy stays valid and the grid degrades through its own path.
        metrics = sanitize_display_metrics(
            1920, 1080, 70.0, 40.0, DisplayMetricsSource.MANUAL_OVERRIDE
        )
        assert metrics is not None
        policy = collection_policy_for_metrics(metrics)
        self.assertEqual(policy.minimum_item_px, policy.preferred_item_px)

    def test_floored_policy_preserves_containment_and_stress(self) -> None:
        policy = collection_policy_for_metrics(self._dense())
        for width, height in REPRESENTATIVE_VIEWPORTS:
            with self.subTest(width=width, height=height):
                content = UiRect(8, 86, max(1, width - 16), max(1, height - 94))
                layout = policy.layout(content, 50)
                self.assertGreaterEqual(layout.capacity, 1)
                for index in range(layout.capacity):
                    self.assertTrue(content.contains(layout.cell(index)))
        rng = random.Random(0x6A7E1A)
        for _ in range(500):
            width = rng.randint(240, 4096)
            height = rng.randint(200, 2160)
            content = UiRect(0, 0, width, height)
            layout = policy.layout(content, rng.randint(1, 80))
            for index in range(layout.capacity):
                self.assertTrue(content.contains(layout.cell(index)))


if __name__ == "__main__":
    unittest.main()
