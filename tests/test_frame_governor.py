"""Frame governance: present only on change, cap animation, throttle ambient."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.frame_governor import FrameGovernor, FrameKind, FramePolicy
from greia_platform.pygame_canvas import PygameReferenceCanvas


class FakeTime:
    def __init__(self) -> None:
        self.now = 100.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


POLICY = FramePolicy(animation_fps=20.0, ambient_fps=5.0, ambient_after_seconds=2.0, idle_poll_seconds=0.05)


def governor(fake: FakeTime) -> FrameGovernor:
    return FrameGovernor(POLICY, clock=fake.clock, sleep=fake.sleep)


def motion(pos=(50, 50)) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(1, 1), buttons=(0, 0, 0))


class FramePolicyTests(unittest.TestCase):
    def test_profiles_and_environment_selection(self) -> None:
        self.assertEqual(FramePolicy.for_profile("standard"), FramePolicy())
        self.assertEqual(FramePolicy.for_profile("reference-floor"), FramePolicy.reference_floor())
        floor = FramePolicy.from_environment({}, cpu_count=2)
        self.assertEqual(floor, FramePolicy.reference_floor())
        self.assertEqual(FramePolicy.from_environment({}, cpu_count=8), FramePolicy.standard())
        forced = FramePolicy.from_environment({"GREIA_FRAME_PROFILE": "standard"}, cpu_count=2)
        self.assertEqual(forced, FramePolicy.standard())
        # An unknown value never breaks an Activity: fall back to detection.
        self.assertEqual(
            FramePolicy.from_environment({"GREIA_FRAME_PROFILE": "turbo"}, cpu_count=1),
            FramePolicy.reference_floor(),
        )

    def test_policy_bounds(self) -> None:
        with self.assertRaises(ValueError):
            FramePolicy(animation_fps=0.5)
        with self.assertRaises(ValueError):
            FramePolicy(animation_fps=20.0, ambient_fps=30.0)
        with self.assertRaises(ValueError):
            FramePolicy(idle_poll_seconds=2.0)


class FrameGovernorTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()

    def test_first_frame_full_then_static_screen_skips_and_sleeps(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        self.assertIs(frames.frame(), FrameKind.FULL)
        fake.now += 1.0
        presented = frames.frames_presented
        for _ in range(100):
            self.assertIs(frames.frame(), FrameKind.SKIP)
            frames.wait()
        self.assertEqual(frames.frames_presented, presented)
        # A static loop only polls: every sleep is the bounded idle poll.
        self.assertTrue(all(abs(s - POLICY.idle_poll_seconds) < 1e-9 for s in fake.slept[-100:]))

    def test_dirty_presents_once_and_is_capped(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        frames.frame()
        fake.now += 0.01  # sooner than one 20 fps period
        self.assertIs(frames.frame(dirty=True), FrameKind.SKIP)
        frames.wait()
        self.assertAlmostEqual(fake.slept[-1], 0.04, places=6)
        self.assertIs(frames.frame(dirty=True), FrameKind.FULL)
        fake.now += 1.0
        self.assertIs(frames.frame(), FrameKind.SKIP)

    def test_invalidate_requests_one_frame(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        frames.frame()
        fake.now += 1.0
        frames.invalidate()
        self.assertIs(frames.frame(), FrameKind.FULL)
        fake.now += 1.0
        self.assertIs(frames.frame(), FrameKind.SKIP)

    def test_animation_runs_at_capped_rate(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        start = fake.now
        while fake.now - start < 1.0:
            frames.frame(animating=True)
            frames.wait()
        self.assertIn(frames.frames_presented, range(19, 22))

    def test_animate_for_window_expires(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        frames.frame()
        frames.animate_for(0.5)
        start = fake.now
        while fake.now - start < 2.0:
            frames.frame()
            frames.wait()
        self.assertIn(frames.frames_presented, range(10, 14))

    def test_ambient_drops_to_reduced_rate_after_idle_and_recovers_on_input(self) -> None:
        fake = FakeTime()
        frames = governor(fake)

        def count(seconds: float) -> int:
            before = frames.frames_presented
            end = fake.now + seconds
            while fake.now < end:
                frames.frame(ambient=True)
                frames.wait()
            return frames.frames_presented - before

        self.assertGreaterEqual(count(1.0), 19)  # child just arrived: full rate
        fake.now += 2.0
        self.assertTrue(frames.ambient_throttled)
        self.assertIn(count(2.0), range(9, 12))  # 5 fps
        frames.note_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
        self.assertFalse(frames.ambient_throttled)
        self.assertGreaterEqual(count(1.0), 19)

    def test_essential_animation_is_never_throttled(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        fake.now += 10.0
        before = frames.frames_presented
        end = fake.now + 1.0
        while fake.now < end:
            frames.frame(animating=True, ambient=True)
            frames.wait()
        self.assertGreaterEqual(frames.frames_presented - before, 19)

    def test_pointer_motion_yields_pointer_frames_promptly(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        frames.frame()
        fake.now += 1.0
        frames.note_event(motion())
        self.assertIs(frames.frame(), FrameKind.POINTER)
        # Continuous motion keeps the loop at frame cadence, not idle polling.
        frames.note_event(motion((60, 60)))
        frames.wait()
        self.assertAlmostEqual(fake.slept[-1], 0.05, places=6)
        self.assertIs(frames.frame(), FrameKind.POINTER)
        # Dirty state wins over pointer-only.
        fake.now += 0.1
        frames.note_event(motion((70, 70)))
        self.assertIs(frames.frame(dirty=True), FrameKind.FULL)

    def test_events_drains_queue_and_notes_input(self) -> None:
        pygame.display.set_mode((64, 64))
        fake = FakeTime()
        frames = governor(fake)
        frames.frame()
        fake.now += 5.0
        pygame.event.clear()
        pygame.event.post(motion((10, 10)))
        events = frames.events()
        self.assertTrue(any(e.type == pygame.MOUSEMOTION for e in events))
        self.assertFalse(frames.ambient_throttled)
        self.assertIs(frames.frame(), FrameKind.POINTER)

    def test_polling_keeps_frame_cadence_without_presenting(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        frames.frame()
        fake.now += 1.0
        frames.frame()
        frames.wait(polling=True)
        self.assertAlmostEqual(fake.slept[-1], POLICY.frame_period, places=6)

    def test_redraw_on_input_invalidates_on_input_and_drags_only(self) -> None:
        fake = FakeTime()
        frames = FrameGovernor(POLICY, redraw_on_input=True, clock=fake.clock, sleep=fake.sleep)
        frames.frame()
        fake.now += 1.0
        frames.note_event(motion())  # hover: pointer only
        self.assertIs(frames.frame(), FrameKind.POINTER)
        fake.now += 1.0
        drag = pygame.event.Event(pygame.MOUSEMOTION, pos=(9, 9), rel=(1, 0), buttons=(1, 0, 0))
        frames.note_event(drag)
        self.assertIs(frames.frame(), FrameKind.FULL)
        fake.now += 1.0
        frames.note_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertIs(frames.frame(), FrameKind.FULL)

    def test_keepalive_bounds_staleness(self) -> None:
        fake = FakeTime()
        frames = FrameGovernor(POLICY, keepalive_seconds=1.0, clock=fake.clock, sleep=fake.sleep)
        frames.frame()
        start = fake.now
        while fake.now - start < 5.0:
            frames.frame()
            frames.wait()
        self.assertIn(frames.frames_presented, range(5, 8))
        with self.assertRaises(ValueError):
            FrameGovernor(POLICY, keepalive_seconds=0.0)

    def test_polling_cadence_tracks_previous_wake_like_clock_tick(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        frames.frame()
        start = fake.now
        steps = 0
        while fake.now - start < 1.0:
            fake.now += 0.01  # simulated work per step
            frames.wait(polling=True)
            steps += 1
        self.assertIn(steps, range(19, 22))


class CanvasPointerRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1024, 600))

    def test_pointer_refresh_repairs_old_area_without_rerender(self) -> None:
        canvas = PygameReferenceCanvas(self.screen)
        canvas.surface.fill((10, 20, 30))
        draws: list[tuple[int, int]] = []
        import greia_platform.activity_ui as activity_ui

        original = activity_ui.draw_activity_pointer

        def fake_pointer(surface, pos=None, **kwargs):
            position = (200, 200) if not draws else (400, 300)
            draws.append(position)
            return original(surface, position, **kwargs)

        activity_ui.draw_activity_pointer = fake_pointer
        try:
            canvas.present(clear=(0, 0, 0))
            self.assertNotEqual(tuple(self.screen.get_at((200, 200)))[:3], (10, 20, 30))
            # The scene changes on the logical surface but is NOT re-presented:
            # pointer refresh only repairs the old pointer rectangle.
            canvas.surface.fill((99, 99, 99), pygame.Rect(600, 500, 10, 10))
            self.assertTrue(canvas.present_pointer())
        finally:
            activity_ui.draw_activity_pointer = original
        self.assertEqual(tuple(self.screen.get_at((200, 200)))[:3], (10, 20, 30))
        self.assertNotEqual(tuple(self.screen.get_at((400, 300)))[:3], (10, 20, 30))
        self.assertEqual(tuple(self.screen.get_at((605, 505)))[:3], (10, 20, 30))


if __name__ == "__main__":
    unittest.main()
