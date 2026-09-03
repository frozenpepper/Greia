from __future__ import annotations

import math
import unittest

from greia_platform.display_metrics import (
    DisplayMetrics,
    DisplayMetricsSource,
    DisplayPolicy,
    DisplaySuitability,
    PhysicalUiPolicy,
    filter_supported_modes,
    sanitize_display_metrics,
)
from greia_platform.hardware import DisplayMode
from greia_platform.responsive_layout import Viewport


def _known(
    width: int,
    height: int,
    width_mm: float = 222.0,
    height_mm: float = 130.0,
) -> DisplayMetrics:
    metrics = sanitize_display_metrics(
        width, height, width_mm, height_mm, DisplayMetricsSource.MANUAL_OVERRIDE
    )
    assert metrics is not None
    assert metrics.physical_size_known
    return metrics


class SupportedTests(unittest.TestCase):
    def test_full_floor_panel_is_supported(self) -> None:
        policy = DisplayPolicy.phase0()
        self.assertEqual(
            policy.evaluate(_known(1920, 1080, 531.0, 299.0)),
            DisplaySuitability.SUPPORTED,
        )

    def test_constrained_panel_is_supported_with_reflow(self) -> None:
        policy = DisplayPolicy.phase0()
        self.assertEqual(
            policy.evaluate(_known(800, 480, 160.0, 100.0)),
            DisplaySuitability.SUPPORTED_WITH_REFLOW,
        )


class FallbackAndRejectionTests(unittest.TestCase):
    def test_unknown_physical_size_falls_back(self) -> None:
        policy = DisplayPolicy.phase0()
        metrics = sanitize_display_metrics(1024, 600)
        assert metrics is not None
        self.assertEqual(
            policy.evaluate(metrics), DisplaySuitability.UNKNOWN_PHYSICAL_SIZE
        )

    def test_below_pixel_envelope_is_unsupported(self) -> None:
        policy = DisplayPolicy.phase0()
        self.assertEqual(
            policy.evaluate(_known(640, 480, 160.0, 120.0)),
            DisplaySuitability.UNSUPPORTED_PIXEL_ENVELOPE,
        )

    def test_portrait_rejected_by_product_policy(self) -> None:
        policy = DisplayPolicy.phase0()
        self.assertEqual(
            policy.evaluate(_known(800, 1280, 170.0, 270.0)),
            DisplaySuitability.UNSUPPORTED_ORIENTATION,
        )

    def test_geometry_layer_still_accepts_portrait_input(self) -> None:
        viewport = Viewport(600, 1024)
        self.assertEqual(viewport.short_axis, 600)
        self.assertGreater(viewport.bounded_px(24, minimum=8, maximum=64), 0)

    def test_outside_physical_envelope_is_unsupported(self) -> None:
        policy = DisplayPolicy.phase0()
        oversized = DisplayMetrics(
            1920,
            1080,
            physical_width_mm=3200.0,
            physical_height_mm=2000.0,
            source=DisplayMetricsSource.MANUAL_OVERRIDE,
        )
        self.assertEqual(
            policy.evaluate(oversized), DisplaySuitability.UNSUPPORTED_PHYSICAL_SIZE
        )


class BoundaryTests(unittest.TestCase):
    def test_envelope_boundaries_behave_exactly(self) -> None:
        policy = DisplayPolicy(
            min_pixel_width=800,
            min_pixel_height=480,
            preferred_pixel_width=1024,
            preferred_pixel_height=600,
        )
        self.assertEqual(
            policy.evaluate(_known(800, 480)), DisplaySuitability.SUPPORTED_WITH_REFLOW
        )
        self.assertEqual(
            policy.evaluate(_known(799, 480)), DisplaySuitability.UNSUPPORTED_PIXEL_ENVELOPE
        )
        self.assertEqual(
            policy.evaluate(_known(800, 479)), DisplaySuitability.UNSUPPORTED_PIXEL_ENVELOPE
        )
        self.assertEqual(
            policy.evaluate(_known(1024, 600)), DisplaySuitability.SUPPORTED
        )
        self.assertEqual(
            policy.evaluate(_known(1024, 599)), DisplaySuitability.SUPPORTED_WITH_REFLOW
        )

    def test_physical_boundaries_behave_exactly(self) -> None:
        policy = DisplayPolicy(
            min_physical_width_mm=100.0,
            min_physical_height_mm=60.0,
            max_physical_width_mm=500.0,
            max_physical_height_mm=300.0,
        )
        self.assertEqual(
            policy.evaluate(_known(1280, 800, 100.0, 60.0)),
            DisplaySuitability.SUPPORTED,
        )
        self.assertEqual(
            policy.evaluate(_known(1280, 800, 500.0, 300.0)),
            DisplaySuitability.SUPPORTED,
        )
        self.assertEqual(
            policy.evaluate(_known(1280, 800, 99.0, 60.0)),
            DisplaySuitability.UNSUPPORTED_PHYSICAL_SIZE,
        )
        self.assertEqual(
            policy.evaluate(_known(1280, 800, 500.0, 301.0)),
            DisplaySuitability.UNSUPPORTED_PHYSICAL_SIZE,
        )

    def test_evaluate_rejects_missing_metrics(self) -> None:
        with self.assertRaises(TypeError):
            DisplayPolicy.phase0().evaluate(None)  # type: ignore[arg-type]


class ModeFilterTests(unittest.TestCase):
    def test_filter_keeps_suitable_modes_and_drops_proven_bad(self) -> None:
        policy = DisplayPolicy.phase0()
        modes = [
            DisplayMode(width=1920, height=1080),
            DisplayMode(width=1024, height=600),
            DisplayMode(width=640, height=480),
            DisplayMode(width=800, height=1280),
        ]
        kept = filter_supported_modes(
            modes,
            physical_width_mm=531.0,
            physical_height_mm=299.0,
            source=DisplayMetricsSource.MANUAL_OVERRIDE,
            policy=policy,
        )
        kept_ids = {mode.mode_id for mode in kept}
        self.assertIn("1920x1080", kept_ids)
        self.assertIn("1024x600", kept_ids)
        self.assertNotIn("640x480", kept_ids)
        self.assertNotIn("800x1280", kept_ids)

    def test_arbitrary_nearby_modes_behave_by_policy(self) -> None:
        policy = DisplayPolicy.phase0()
        modes = [
            DisplayMode(width=1000, height=580),
            DisplayMode(width=1280, height=720),
        ]
        kept = filter_supported_modes(
            modes,
            physical_width_mm=300.0,
            physical_height_mm=180.0,
            source=DisplayMetricsSource.MANUAL_OVERRIDE,
            policy=policy,
        )
        self.assertEqual({mode.mode_id for mode in kept}, {"1000x580", "1280x720"})
        for mode in modes:
            metrics = sanitize_display_metrics(
                mode.width,
                mode.height,
                300.0,
                180.0,
                DisplayMetricsSource.MANUAL_OVERRIDE,
            )
            assert metrics is not None
            self.assertIn(
                policy.evaluate(metrics),
                (
                    DisplaySuitability.SUPPORTED,
                    DisplaySuitability.SUPPORTED_WITH_REFLOW,
                ),
            )


class PhysicalSizingTests(unittest.TestCase):
    def test_known_metrics_convert_physical_floor(self) -> None:
        metrics = _known(1024, 600)
        expected = math.floor(10.0 * min(1024 / 222.0, 600 / 130.0))
        self.assertEqual(
            PhysicalUiPolicy.minimum_pixels(10.0, fallback_px=48, metrics=metrics),
            expected,
        )

    def test_unknown_metrics_use_fallback(self) -> None:
        metrics = sanitize_display_metrics(1024, 600)
        assert metrics is not None
        self.assertEqual(
            PhysicalUiPolicy.minimum_pixels(10.0, fallback_px=48, metrics=metrics),
            48,
        )
        self.assertEqual(
            PhysicalUiPolicy.minimum_pixels(10.0, fallback_px=48, metrics=None),
            48,
        )

    def test_result_is_bounded(self) -> None:
        metrics = _known(1920, 1080, 531.0, 299.0)
        self.assertLessEqual(
            PhysicalUiPolicy.minimum_pixels(5000.0, fallback_px=48, metrics=metrics),
            320,
        )
        self.assertGreaterEqual(
            PhysicalUiPolicy.minimum_pixels(0.1, fallback_px=48, metrics=metrics),
            8,
        )
        self.assertLessEqual(
            PhysicalUiPolicy.minimum_pixels(10.0, fallback_px=10000, metrics=None),
            320,
        )

    def test_high_density_enlarges_minimum_without_scaling_layout(self) -> None:
        standard = _known(1024, 600, 222.0, 130.0)
        dense = _known(2048, 1200, 222.0, 130.0)
        standard_px = PhysicalUiPolicy.minimum_pixels(
            10.0, fallback_px=24, metrics=standard
        )
        dense_px = PhysicalUiPolicy.minimum_pixels(
            10.0, fallback_px=24, metrics=dense
        )
        self.assertGreater(dense_px, standard_px)
        # Only the shared minimum grows; the call returns a single floor value.
        self.assertIsInstance(dense_px, int)


if __name__ == "__main__":
    unittest.main()
