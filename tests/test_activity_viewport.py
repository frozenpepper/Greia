from __future__ import annotations

import math
import random
import unittest

from greia_platform.activity_viewport import (
    ActivitySpatialModel,
    ActivityViewport,
    CanvasFitMode,
    CanvasTransform,
    LogicalRect,
    ReferenceCanvasSpec,
)
from greia_platform.responsive_layout import UiRect


class ActivityViewportTests(unittest.TestCase):
    def test_safe_ui_rect_avoids_corner_system_chrome_without_device_rules(self) -> None:
        viewport = ActivityViewport.for_size(
            1024,
            600,
            protected_regions=(UiRect(0, 0, 150, 80),),
        )
        safe = viewport.safe_ui_rect()
        self.assertFalse(_overlaps(safe, UiRect(0, 0, 150, 80)))
        self.assertTrue(viewport.surface.contains(safe))
        # The largest region for this geometry preserves full horizontal width
        # below the corner chrome instead of hard-coding an Acer-specific inset.
        self.assertEqual(safe, UiRect(0, 80, 1024, 520))

    def test_multiple_protected_regions_still_produce_contained_safe_area(self) -> None:
        viewport = ActivityViewport.for_size(
            800,
            600,
            protected_regions=(
                UiRect(0, 0, 130, 70),
                UiRect(680, 0, 120, 70),
            ),
        )
        safe = viewport.safe_ui_rect(margin=8)
        self.assertTrue(viewport.surface.contains(safe))
        for protected in viewport.protected_regions:
            self.assertFalse(_overlaps(safe, protected))

    def test_reference_canvas_defaults_to_netbook_authoring_space(self) -> None:
        spec = ReferenceCanvasSpec()
        self.assertEqual((spec.width, spec.height), (1024, 600))
        self.assertEqual(spec.fit, CanvasFitMode.CONTAIN)
        self.assertEqual(ActivitySpatialModel.REFERENCE_CANVAS.value, "reference_canvas")


class CanvasTransformTests(unittest.TestCase):
    def test_contain_keeps_entire_reference_canvas_and_letterboxes(self) -> None:
        target = UiRect(0, 0, 800, 600)
        transform = CanvasTransform.for_reference(target, ReferenceCanvasSpec())
        self.assertEqual(transform.logical_view, LogicalRect(0.0, 0.0, 1024.0, 600.0))
        self.assertAlmostEqual(transform.scale, 800 / 1024)
        self.assertLess(transform.physical_view.height, 600)
        self.assertAlmostEqual(transform.physical_view.width, 800.0)
        self.assertAlmostEqual(transform.physical_view.y, (600 - 600 * (800 / 1024)) / 2)

    def test_cover_fills_target_and_crops_logical_edges(self) -> None:
        target = UiRect(0, 0, 800, 600)
        transform = CanvasTransform.for_reference(
            target,
            ReferenceCanvasSpec(fit=CanvasFitMode.COVER),
        )
        self.assertAlmostEqual(transform.physical_view.width, 800)
        self.assertAlmostEqual(transform.physical_view.height, 600)
        self.assertLess(transform.logical_view.width, 1024)
        self.assertAlmostEqual(transform.logical_view.height, 600)

    def test_expand_shows_more_world_instead_of_bars_or_crop(self) -> None:
        target = UiRect(0, 0, 1920, 1080)
        transform = CanvasTransform.for_camera(
            target,
            center=(5000, 250),
            reference_size=(1024, 600),
            fit=CanvasFitMode.EXPAND,
        )
        self.assertEqual(transform.physical_view.rounded_out(), target)
        self.assertGreater(transform.logical_view.width, 1024)
        self.assertAlmostEqual(transform.logical_view.height, 600)
        self.assertAlmostEqual(transform.logical_view.center[0], 5000)
        self.assertAlmostEqual(transform.logical_view.center[1], 250)

    def test_expand_on_four_three_reveals_more_vertical_world(self) -> None:
        transform = CanvasTransform.for_camera(
            UiRect(0, 0, 800, 600),
            center=(0, 0),
            reference_size=(1024, 600),
            fit=CanvasFitMode.EXPAND,
        )
        self.assertAlmostEqual(transform.logical_view.width, 1024)
        self.assertGreater(transform.logical_view.height, 600)

    def test_draw_and_input_transform_are_exact_inverses(self) -> None:
        rng = random.Random(0xCA6A5)
        for fit in CanvasFitMode:
            for _ in range(300):
                width = rng.randint(320, 3840)
                height = rng.randint(240, 2160)
                transform = CanvasTransform.for_camera(
                    UiRect(0, 0, width, height),
                    center=(rng.uniform(-5000, 5000), rng.uniform(-5000, 5000)),
                    reference_size=(1024, 600),
                    fit=fit,
                )
                logical_x = rng.uniform(
                    transform.logical_view.x,
                    transform.logical_view.right,
                )
                logical_y = rng.uniform(
                    transform.logical_view.y,
                    transform.logical_view.bottom,
                )
                physical = transform.logical_to_physical((logical_x, logical_y))
                roundtrip = transform.physical_to_logical(physical)
                self.assertIsNotNone(roundtrip)
                assert roundtrip is not None
                self.assertTrue(math.isclose(roundtrip[0], logical_x, abs_tol=1e-7))
                self.assertTrue(math.isclose(roundtrip[1], logical_y, abs_tol=1e-7))

    def test_contain_rejects_pointer_in_letterbox(self) -> None:
        transform = CanvasTransform.for_reference(UiRect(0, 0, 800, 600))
        self.assertIsNone(transform.physical_to_logical((400, 5)))
        self.assertIsNotNone(
            transform.physical_to_logical(
                (transform.physical_view.x + 1, transform.physical_view.y + 1)
            )
        )

    def test_reference_and_world_camera_can_choose_safe_or_full_surface(self) -> None:
        viewport = ActivityViewport.for_size(
            1024,
            600,
            protected_regions=(UiRect(0, 0, 150, 80),),
        )
        ui = viewport.reference_transform(safe_ui=True)
        world = viewport.world_camera((512, 300), safe_ui=False)
        self.assertNotEqual(ui.target, viewport.surface)
        self.assertEqual(world.target, viewport.surface)


def _overlaps(a: UiRect, b: UiRect) -> bool:
    return not (
        a.right <= b.x
        or b.right <= a.x
        or a.bottom <= b.y
        or b.bottom <= a.y
    )


if __name__ == "__main__":
    unittest.main()
