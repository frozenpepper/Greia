from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from greia_platform.display_metrics import (
    DisplayMetrics,
    DisplayMetricsSource,
    metrics_for_output,
    metrics_from_mode,
    sanitize_display_metrics,
)
from greia_platform.hardware import DisplayMode


def _mode(width: int, height: int, *, current: bool = False) -> DisplayMode:
    return DisplayMode(width=width, height=height, current=current)


class SanitizeValidPanelsTests(unittest.TestCase):
    def test_first_reference_panel_reports_derived_density(self) -> None:
        metrics = sanitize_display_metrics(
            1024,
            600,
            222.0,
            130.0,
            DisplayMetricsSource.XRANDR_PHYSICAL_SIZE,
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertTrue(metrics.physical_size_known)
        self.assertEqual(metrics.orientation, "landscape")
        self.assertAlmostEqual(metrics.aspect_ratio, 1024 / 600)
        # Derived density is computed from the reported facts, never assumed.
        self.assertAlmostEqual(metrics.pixels_per_mm_x, 1024 / 222.0)
        self.assertAlmostEqual(metrics.pixels_per_mm_y, 600 / 130.0)
        assert metrics.effective_dpi_x is not None
        assert metrics.effective_dpi_y is not None
        self.assertAlmostEqual(metrics.effective_dpi_x, 1024 / 222.0 * 25.4)
        self.assertAlmostEqual(metrics.effective_dpi_y, 600 / 130.0 * 25.4)
        self.assertNotAlmostEqual(metrics.effective_dpi_x, 96.0, delta=20.0)
        assert metrics.diagonal_inches is not None
        self.assertGreater(metrics.diagonal_inches, 5.0)
        self.assertLess(metrics.diagonal_inches, 20.0)

    def test_second_reference_panel_reports_derived_density(self) -> None:
        metrics = sanitize_display_metrics(
            1366,
            768,
            344.0,
            194.0,
            DisplayMetricsSource.XRANDR_PHYSICAL_SIZE,
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertTrue(metrics.physical_size_known)
        assert metrics.effective_dpi_x is not None
        assert metrics.effective_dpi_y is not None
        self.assertAlmostEqual(metrics.effective_dpi_x, 1366 / 344.0 * 25.4)
        self.assertAlmostEqual(metrics.effective_dpi_y, 768 / 194.0 * 25.4)

    def test_third_reference_panel_reports_derived_density(self) -> None:
        metrics = sanitize_display_metrics(
            1920,
            1080,
            531.0,
            299.0,
            DisplayMetricsSource.MANUAL_OVERRIDE,
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertTrue(metrics.physical_size_known)
        self.assertEqual(metrics.source, DisplayMetricsSource.MANUAL_OVERRIDE)
        assert metrics.effective_dpi_x is not None
        self.assertAlmostEqual(metrics.effective_dpi_x, 1920 / 531.0 * 25.4)


class SanitizeImplausiblePanelsTests(unittest.TestCase):
    def test_missing_physical_size_never_invents_dimensions(self) -> None:
        metrics = sanitize_display_metrics(1024, 600)
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertFalse(metrics.physical_size_known)
        self.assertEqual(metrics.source, DisplayMetricsSource.UNKNOWN)
        self.assertIsNone(metrics.pixels_per_mm_x)
        self.assertIsNone(metrics.pixels_per_mm_y)
        self.assertIsNone(metrics.effective_dpi_x)
        self.assertIsNone(metrics.effective_dpi_y)
        self.assertIsNone(metrics.diagonal_inches)

    def test_zero_physical_size_yields_unknown(self) -> None:
        metrics = sanitize_display_metrics(
            1024, 600, 0.0, 0.0, DisplayMetricsSource.XRANDR_PHYSICAL_SIZE
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertFalse(metrics.physical_size_known)
        self.assertIsNone(metrics.effective_dpi_x)

    def test_tiny_physical_size_yields_unknown(self) -> None:
        metrics = sanitize_display_metrics(
            1024, 600, 2.0, 1.0, DisplayMetricsSource.XRANDR_PHYSICAL_SIZE
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertFalse(metrics.physical_size_known)
        self.assertIsNone(metrics.effective_dpi_x)

    def test_huge_physical_size_yields_unknown(self) -> None:
        metrics = sanitize_display_metrics(
            1920, 1080, 10000.0, 8000.0, DisplayMetricsSource.XRANDR_PHYSICAL_SIZE
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertFalse(metrics.physical_size_known)
        self.assertIsNone(metrics.effective_dpi_x)

    def test_implausible_density_yields_unknown(self) -> None:
        metrics = sanitize_display_metrics(
            1920, 1080, 40.0, 25.0, DisplayMetricsSource.XRANDR_PHYSICAL_SIZE
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertFalse(metrics.physical_size_known)
        self.assertIsNone(metrics.effective_dpi_x)

    def test_non_positive_pixels_yield_no_metrics(self) -> None:
        self.assertIsNone(sanitize_display_metrics(0, 600, 222.0, 130.0))
        self.assertIsNone(sanitize_display_metrics(1024, -1, 222.0, 130.0))
        self.assertIsNone(sanitize_display_metrics("1024", 600, 222.0, 130.0))


class ProbeHelperTests(unittest.TestCase):
    def test_portrait_panel_keeps_orientation_and_density(self) -> None:
        metrics = sanitize_display_metrics(
            600, 1024, 130.0, 222.0, DisplayMetricsSource.XRANDR_PHYSICAL_SIZE
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertEqual(metrics.orientation, "portrait")
        self.assertTrue(metrics.physical_size_known)
        assert metrics.effective_dpi_x is not None
        self.assertAlmostEqual(metrics.effective_dpi_x, 600 / 130.0 * 25.4)

    def test_no_current_mode_yields_no_metrics(self) -> None:
        modes = [_mode(1024, 600), _mode(800, 600)]
        self.assertIsNone(
            metrics_from_mode(
                next((mode for mode in modes if mode.current), None),
                physical_width_mm=222.0,
                physical_height_mm=130.0,
                source=DisplayMetricsSource.XRANDR_PHYSICAL_SIZE,
            )
        )
        self.assertIsNone(
            metrics_for_output(
                "OUTPUT-1",
                modes,
                physical_width_mm=222.0,
                physical_height_mm=130.0,
                source=DisplayMetricsSource.XRANDR_PHYSICAL_SIZE,
            )
        )

    def test_no_output_yields_no_metrics(self) -> None:
        modes = [_mode(1024, 600, current=True)]
        self.assertIsNone(
            metrics_for_output(
                None,
                modes,
                physical_width_mm=222.0,
                physical_height_mm=130.0,
                source=DisplayMetricsSource.XRANDR_PHYSICAL_SIZE,
            )
        )
        self.assertIsNone(metrics_for_output("", modes))

    def test_current_mode_selects_flagged_mode(self) -> None:
        modes = [_mode(800, 600), _mode(1024, 600, current=True)]
        metrics = metrics_for_output(
            "OUTPUT-1",
            modes,
            physical_width_mm=222.0,
            physical_height_mm=130.0,
            source=DisplayMetricsSource.XRANDR_PHYSICAL_SIZE,
        )
        self.assertIsNotNone(metrics)
        assert metrics is not None
        self.assertEqual((metrics.pixel_width, metrics.pixel_height), (1024, 600))
        self.assertTrue(metrics.physical_size_known)


class ValueObjectTests(unittest.TestCase):
    def test_metrics_are_immutable(self) -> None:
        metrics = DisplayMetrics(1024, 600)
        with self.assertRaises(FrozenInstanceError):
            metrics.pixel_width = 800  # type: ignore[misc]

    def test_stores_only_raw_facts(self) -> None:
        metrics = DisplayMetrics(
            1024,
            600,
            physical_width_mm=222.0,
            physical_height_mm=130.0,
            source=DisplayMetricsSource.MANUAL_OVERRIDE,
        )
        field_names = {name for name, _ in metrics.__dataclass_fields__.items()}
        self.assertEqual(
            field_names,
            {
                "pixel_width",
                "pixel_height",
                "physical_width_mm",
                "physical_height_mm",
                "source",
            },
        )
        self.assertEqual(metrics.orientation, "landscape")
        self.assertEqual(DisplayMetrics(600, 600).orientation, "square")


if __name__ == "__main__":
    unittest.main()
