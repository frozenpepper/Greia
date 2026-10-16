"""Frame governance: present only on change, cap animation, throttle ambient."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.frame_governor import FrameGovernor, FrameKind, FramePolicy
from greia_platform.pygame_canvas import PygamePointerSprite, PygameReferenceCanvas, merge_regions


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

    def test_hint_animation_is_capped_on_the_reference_floor_only(self) -> None:
        floor = FramePolicy.reference_floor()
        self.assertEqual(floor.hint_animation_seconds(2.6), 1.5)
        self.assertEqual(floor.hint_animation_seconds(1.0), 1.0)
        self.assertEqual(FramePolicy.standard().hint_animation_seconds(2.6), 2.6)
        with self.assertRaises(ValueError):
            FramePolicy(hint_animation_cap_seconds=0.0)

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

    def test_static_ambient_policy_freezes_decoration_and_resumes_instantly(self) -> None:
        fake = FakeTime()
        static = FramePolicy(animation_fps=20.0, ambient_fps=0.0, ambient_after_seconds=2.0)
        self.assertTrue(static.ambient_static)
        frames = FrameGovernor(static, clock=fake.clock, sleep=fake.sleep)

        def count(seconds: float) -> int:
            before = frames.frames_presented
            end = fake.now + seconds
            while fake.now < end:
                frames.frame(ambient=True)
                frames.wait()
            return frames.frames_presented - before

        self.assertGreaterEqual(count(1.9), 35)  # decorative window: full rate
        fake.now += 0.2
        self.assertTrue(frames.ambient_throttled)
        slept = len(fake.slept)
        self.assertEqual(count(10.0), 0)  # static frame: nothing presented
        # ...and the loop only idles: every sleep is the bounded idle poll.
        self.assertTrue(all(abs(s - static.idle_poll_seconds) < 1e-9 for s in fake.slept[slept:]))
        # Pointer motion still moves Greia's pointer without waking the scene.
        frames.note_event(motion())
        self.assertIs(frames.frame(ambient=True), FrameKind.FULL)  # input resets the window
        fake.now += 3.0
        frames.note_input()
        # Any input resumes decoration at full rate immediately.
        self.assertIs(frames.frame(ambient=True), FrameKind.FULL)
        self.assertGreaterEqual(count(1.0), 19)
        # Essential motion and dirty frames are never frozen by the policy.
        fake.now += 5.0
        self.assertTrue(frames.ambient_throttled)
        self.assertIs(frames.frame(dirty=True, ambient=True), FrameKind.FULL)
        fake.now += 0.1
        self.assertIs(frames.frame(animating=True, ambient=True), FrameKind.FULL)

    def test_reference_floor_policy_is_static_after_window(self) -> None:
        floor = FramePolicy.reference_floor()
        self.assertEqual(floor.ambient_fps, 0.0)
        self.assertTrue(floor.ambient_static)
        self.assertEqual(floor.ambient_period, float("inf"))
        self.assertFalse(FramePolicy.standard().ambient_static)
        with self.assertRaises(ValueError):
            FramePolicy(ambient_fps=0.5)

    def test_wait_never_spins_when_nothing_is_presented(self) -> None:
        fake = FakeTime()
        frames = governor(fake)
        frames.frame()
        # A loop that keeps a pending frame which is never due must still sleep.
        for _ in range(50):
            frames.frame(dirty=True)  # capped: SKIP until the period elapses
            fake.now += 0.0  # no work time passes
            frames.wait()
        self.assertTrue(all(s > 0.0 for s in fake.slept))
        # Static screen: each iteration sleeps the idle poll, never zero.
        fake.slept.clear()
        for _ in range(20):
            self.assertIs(frames.frame(), FrameKind.SKIP)
            frames.wait()
        self.assertTrue(all(s >= 0.002 for s in fake.slept))

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


    def test_pointer_sprite_saves_under_and_restores_exactly(self) -> None:
        self.screen.fill((10, 20, 30))
        self.screen.fill((200, 0, 0), pygame.Rect(390, 290, 20, 20))
        before = self.screen.copy()
        sprite = PygamePointerSprite()
        first = sprite.draw(self.screen, (400, 300))
        self.assertIsNotNone(first)
        self.assertNotEqual(self.screen.get_at((407, 300)), before.get_at((407, 300)))
        rects = sprite.refresh(self.screen, (600, 400))
        self.assertEqual(len(rects), 2)
        # The red patch under the old pointer is back pixel for pixel.
        for x in range(first.left, first.right):
            for y in range(first.top, first.bottom):
                self.assertEqual(self.screen.get_at((x, y)), before.get_at((x, y)))
        # A partial update under the pointer: erase, repaint, refresh.
        sprite.erase(self.screen)
        self.screen.fill((0, 200, 0), pygame.Rect(590, 390, 30, 30))
        rects = sprite.refresh(self.screen, (600, 400), extra=(pygame.Rect(590, 390, 30, 30),))
        self.assertEqual(len(rects), 3)
        sprite.erase(self.screen)
        self.assertEqual(tuple(self.screen.get_at((600, 400)))[:3], (0, 200, 0))

    def test_region_plan_merges_bounds_and_refuses_big_frames(self) -> None:
        canvas = PygameReferenceCanvas(self.screen)
        small = [pygame.Rect(10, 10, 40, 40), pygame.Rect(30, 30, 40, 40), pygame.Rect(500, 300, 20, 20),
                 pygame.Rect(900, 500, 20, 20)]
        plan = canvas.plan_regions(small, max_passes=2)
        self.assertIsNotNone(plan)
        self.assertLessEqual(len(plan), 2)
        for rect in small:
            self.assertTrue(any(region.contains(rect) for region in plan))
        self.assertIsNone(canvas.plan_regions([pygame.Rect(0, 0, 1024, 400)]))
        self.assertEqual(merge_regions([pygame.Rect(-50, -50, 10, 10)], self.screen.get_rect()), [])

    def test_region_frame_updates_only_its_rectangles(self) -> None:
        canvas = PygameReferenceCanvas(self.screen)
        canvas.surface.fill((5, 5, 5))
        canvas.present(clear=(0, 0, 0), pointer=False)
        canvas.surface.fill((250, 250, 250))  # whole scene "changed" ...
        region = pygame.Rect(100, 100, 50, 50)
        draws: list[pygame.Rect] = []
        canvas.render_regions([region], lambda: draws.append(canvas.surface.get_clip()))
        self.assertEqual(draws, [region])
        self.assertEqual(canvas.surface.get_clip(), canvas.surface.get_rect())
        updates: list[list[pygame.Rect]] = []
        real = pygame.display.update
        pygame.display.update = lambda rects=None: updates.append(list(rects or []))
        try:
            self.assertTrue(canvas.present_regions([region]))
        finally:
            pygame.display.update = real
        # ... but only the region reached the target and the display update.
        self.assertEqual(tuple(self.screen.get_at((120, 120)))[:3], (250, 250, 250))
        self.assertEqual(tuple(self.screen.get_at((300, 300)))[:3], (5, 5, 5))
        self.assertEqual(updates and updates[0][0], region)


if __name__ == "__main__":
    unittest.main()
