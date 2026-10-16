"""Idle-hint back-off schedule (ADR 0037 section 6b)."""

from __future__ import annotations

import unittest

from greia_platform.activity_feedback import IdleHintScheduler
from greia_platform.frame_governor import FramePolicy


def _fire_times(scheduler: IdleHintScheduler, end: float, step: float = 0.5) -> list[tuple[float, int]]:
    fired: list[tuple[float, int]] = []
    now = 0.0
    while now <= end:
        number = scheduler.poll(now)
        if number:
            fired.append((now, number))
        now += step
    return fired


class IdleHintSchedulerTests(unittest.TestCase):
    def make(self, **kwargs) -> IdleHintScheduler:
        return IdleHintScheduler(policy=FramePolicy.standard(), **kwargs)

    def test_back_off_six_then_twelve_then_twenty_four_then_silence(self) -> None:
        scheduler = self.make()
        self.assertEqual(_fire_times(scheduler, 600.0), [(6.0, 1), (18.0, 2), (42.0, 3)])
        self.assertTrue(scheduler.exhausted)
        self.assertEqual(scheduler.count, 3)

    def test_input_restarts_the_whole_schedule(self) -> None:
        scheduler = self.make()
        self.assertEqual(scheduler.poll(6.0), 1)
        self.assertEqual(scheduler.poll(18.0), 2)
        scheduler.reset(20.0)
        self.assertEqual(scheduler.count, 0)
        self.assertEqual(scheduler.poll(25.9), 0)
        self.assertEqual(scheduler.poll(26.0), 1)

    def test_input_after_exhaustion_wakes_hints_again(self) -> None:
        scheduler = self.make()
        _fire_times(scheduler, 100.0)
        self.assertEqual(scheduler.poll(1000.0), 0)
        scheduler.reset(1000.0)
        self.assertEqual(scheduler.poll(1006.0), 1)

    def test_since_delays_without_restarting_the_schedule(self) -> None:
        scheduler = self.make()
        self.assertEqual(scheduler.poll(6.0), 1)
        # Speech ended at t=20: hint 2 now waits 12 s from there, not from 6.
        self.assertEqual(scheduler.poll(30.0, since=20.0), 0)
        self.assertEqual(scheduler.poll(32.0, since=20.0), 2)
        self.assertEqual(scheduler.count, 2)

    def test_one_step_per_poll_even_after_a_long_stall(self) -> None:
        scheduler = self.make()
        self.assertEqual(scheduler.poll(500.0), 1)
        self.assertEqual(scheduler.poll(500.0), 0)

    def test_is_due_does_not_consume_a_step(self) -> None:
        scheduler = self.make()
        self.assertFalse(scheduler.is_due(5.9))
        self.assertTrue(scheduler.is_due(6.0))
        self.assertTrue(scheduler.is_due(6.0))
        self.assertEqual(scheduler.count, 0)
        self.assertEqual(scheduler.fire(6.0), 1)
        self.assertFalse(scheduler.is_due(17.9))
        self.assertTrue(scheduler.is_due(18.0))

    def test_fire_after_exhaustion_is_an_error(self) -> None:
        scheduler = IdleHintScheduler((1.0,), policy=FramePolicy.standard())
        scheduler.fire(1.0)
        with self.assertRaises(RuntimeError):
            scheduler.fire(2.0)

    def test_shorter_gap_tuple_gives_fewer_hints(self) -> None:
        scheduler = IdleHintScheduler(IdleHintScheduler.DEFAULT_GAPS[:2], policy=FramePolicy.standard())
        self.assertEqual(_fire_times(scheduler, 600.0), [(6.0, 1), (18.0, 2)])

    def test_patience_stretches_every_gap(self) -> None:
        scheduler = self.make()
        self.assertEqual(scheduler.poll(8.9, patience=1.5), 0)
        self.assertEqual(scheduler.poll(9.0, patience=1.5), 1)
        self.assertEqual(scheduler.poll(26.9, patience=1.5), 0)
        self.assertEqual(scheduler.poll(27.0, patience=1.5), 2)

    def test_rejects_bad_gaps(self) -> None:
        with self.assertRaises(ValueError):
            IdleHintScheduler(())
        with self.assertRaises(ValueError):
            IdleHintScheduler((6.0, 0.0))

    def test_animation_seconds_follow_the_frame_profile(self) -> None:
        low = IdleHintScheduler(policy=FramePolicy.reference_floor())
        high = IdleHintScheduler(policy=FramePolicy.standard())
        self.assertEqual(low.animation_seconds(1.8), 1.5)
        self.assertEqual(low.animation_seconds(1.0), 1.0)
        self.assertEqual(high.animation_seconds(1.8), 1.8)


if __name__ == "__main__":
    unittest.main()
