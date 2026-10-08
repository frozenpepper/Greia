"""Time-tool domain behavior is deterministic and hardware independent."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import unittest

from activities.tempo_di_greia.time_model import (
    CountdownTimer, ElapsedStopwatch, TimeExperience, TimeMode,
    analog_hand_angles, display_duration,
)


class FakeClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class TimeToolModelTests(unittest.TestCase):
    def test_stopwatch_pause_resume_and_idempotent_start(self) -> None:
        clock = FakeClock()
        watch = ElapsedStopwatch(clock)
        watch.start()
        watch.start()
        clock.value += 10
        self.assertEqual(watch.seconds(), 10.0)
        watch.pause()
        clock.value += 1000
        self.assertEqual(watch.seconds(), 10.0)
        watch.start()
        clock.value += 5
        self.assertEqual(watch.seconds(), 15.0)
        watch.reset()
        self.assertFalse(watch.running)
        self.assertEqual(watch.seconds(), 0.0)

    def test_timer_reset_pause_and_finish_are_one_shot(self) -> None:
        clock = FakeClock()
        timer = CountdownTimer(clock, 60)
        timer.start()
        clock.value += 23
        self.assertEqual(timer.remaining(), 37.0)
        timer.pause()
        clock.value += 200
        self.assertEqual(timer.remaining(), 37.0)
        timer.start()
        clock.value += 42
        self.assertEqual(timer.remaining(), 0.0)
        self.assertTrue(timer.completion_pending)
        self.assertTrue(timer.consume_completion())
        self.assertFalse(timer.consume_completion())
        self.assertFalse(timer.running)
        timer.reset()
        self.assertEqual(timer.remaining(), 60.0)
        self.assertFalse(timer.completion_pending)

    def test_timer_duration_bounds(self) -> None:
        for invalid in (0, -1, 3601, True, 30.5):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                CountdownTimer(FakeClock(), invalid)

    def test_practice_clock_never_changes_real_wall_time(self) -> None:
        clock = FakeClock()
        wall = datetime(2026, 10, 8, 23, 45, 35, tzinfo=timezone.utc)
        state = TimeExperience(wall_now=lambda: wall, monotonic=clock)
        self.assertEqual(state.shown_time(), wall)
        state.set_practice(True)
        state.nudge_practice(30)
        self.assertEqual((state.shown_time().hour, state.shown_time().minute), (0, 15))
        self.assertEqual((wall.hour, wall.minute), (23, 45))
        state.set_practice(False)
        self.assertEqual(state.shown_time(), wall)

    def test_time_source_separates_wall_clock_jump_from_stopwatch(self) -> None:
        clock = FakeClock()
        wall = [datetime(2026, 1, 1, 12, tzinfo=timezone.utc)]
        state = TimeExperience(wall_now=lambda: wall[0], monotonic=clock)
        state.stopwatch.start()
        wall[0] = datetime(2027, 1, 1, 12, tzinfo=timezone.utc)
        clock.value += 5
        self.assertEqual(state.stopwatch.seconds(), 5)
        self.assertEqual(state.shown_time().year, 2027)

    def test_angles_and_visual_counter_rounding(self) -> None:
        shown = datetime(2026, 1, 1, 3, 30, 0, tzinfo=timezone.utc)
        self.assertEqual(analog_hand_angles(shown), (105, 180, 0))
        self.assertEqual(display_duration(60.1), "01:00")
        self.assertEqual(display_duration(60.1, round_up=True), "01:01")
        self.assertEqual(display_duration(-6), "00:00")
        with self.assertRaises(ValueError):
            display_duration(math.inf)

    def test_mode_is_semantic_and_timer_not_screen_time(self) -> None:
        state = TimeExperience(monotonic=FakeClock())
        state.mode = TimeMode.TIMER
        state.timer.set_duration(180)
        self.assertEqual(state.timer.duration_seconds, 180)
        self.assertEqual(state.stopwatch.seconds(), 0.0)


if __name__ == "__main__":
    unittest.main()
