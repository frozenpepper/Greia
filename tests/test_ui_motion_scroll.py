from __future__ import annotations

import unittest

from greia_platform.ui_motion import HoverMotion, InteractionVisualState, LaunchMotion, MotionSample
from greia_platform.ui_scroll import ScrollModel


class LaunchMotionTests(unittest.TestCase):
    def test_launch_motion_is_bounded_and_settles_exactly(self) -> None:
        motion = LaunchMotion(duration_seconds=0.4, wiggle_pixels=8, bounce_pixels=10)
        for elapsed in (0.0, 0.05, 0.1, 0.2, 0.35):
            sample = motion.sample(elapsed)
            self.assertGreaterEqual(sample.scale, 1.0)
            self.assertLessEqual(abs(sample.offset_x), 8.0)
            self.assertGreaterEqual(sample.offset_y, -10.0)
            self.assertLessEqual(sample.offset_y, 0.0)
        self.assertEqual(motion.sample(0.4), MotionSample())
        self.assertEqual(motion.sample(4.0), MotionSample())

    def test_hover_motion_changes_only_emphasized_controls(self) -> None:
        hover = HoverMotion()
        self.assertEqual(hover.sample(InteractionVisualState()), MotionSample())
        emphasized = hover.sample(InteractionVisualState(hovered=True))
        self.assertGreater(emphasized.scale, 1.0)
        self.assertLess(emphasized.offset_y, 0.0)


class ScrollModelTests(unittest.TestCase):
    def test_selection_is_kept_inside_visible_window(self) -> None:
        model = ScrollModel(capacity=6, step=3)
        window = model.window(total=15, selected=8, start=0)
        self.assertEqual((window.start, window.stop), (3, 9))
        self.assertEqual(window.selected, 8)
        self.assertTrue(window.can_scroll_backward)
        self.assertTrue(window.can_scroll_forward)

    def test_wheel_step_is_bounded_at_both_ends(self) -> None:
        model = ScrollModel(capacity=6, step=3)
        first = model.window(total=14, selected=0, start=0)
        self.assertEqual(model.move_start(first, -1), 0)
        middle_start = model.move_start(first, 1)
        self.assertEqual(middle_start, 3)
        last = model.window(total=14, selected=13, start=middle_start)
        self.assertEqual(last.start, 8)
        self.assertEqual(model.move_start(last, 1), 8)

    def test_small_or_empty_collections_do_not_scroll(self) -> None:
        model = ScrollModel(capacity=6, step=3)
        self.assertTrue(model.window(0).empty)
        small = model.window(3, selected=2, start=99)
        self.assertEqual((small.start, small.stop), (0, 3))
        self.assertEqual(model.move_start(small, 1), 0)


if __name__ == "__main__":
    unittest.main()
