"""Time-tool domain behavior is deterministic and hardware independent."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import unittest

from activity_incubator.tempo_di_greia.time_model import (
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

    def test_practice_touch_sets_quarter_minutes_without_changing_real_clock(self) -> None:
        from activity_incubator.tempo_di_greia.time_interaction import (
            DIAL_CENTER, practice_quarter_at_point,
        )
        cx, cy = DIAL_CENTER
        for point, minute in (
            ((cx, cy - 150), 0), ((cx + 150, cy), 15),
            ((cx, cy + 150), 30), ((cx - 150, cy), 45),
        ):
            with self.subTest(point=point):
                self.assertEqual(practice_quarter_at_point(point), minute)
        self.assertIsNone(practice_quarter_at_point((cx, cy)))
        self.assertIsNone(practice_quarter_at_point((cx + 225, cy)))

        wall = datetime(2026, 10, 8, 23, 45, tzinfo=timezone.utc)
        state = TimeExperience(wall_now=lambda: wall, monotonic=FakeClock())
        state.set_practice_minute(0)
        self.assertEqual(state.shown_time(), wall)
        state.set_practice(True)
        state.set_practice_minute(15)
        self.assertEqual((state.shown_time().hour, state.shown_time().minute), (23, 15))
        self.assertEqual(wall.minute, 45)
        with self.assertRaises(ValueError):
            state.set_practice_minute(16)

    def test_inner_hour_and_outer_quarter_regions_are_disjoint(self) -> None:
        from activity_incubator.tempo_di_greia.time_interaction import (
            DIAL_CENTER, practice_hour_at_point, practice_quarter_at_point,
        )
        x, y = DIAL_CENTER
        for point, hour in (
            ((x, y - 87), 12), ((x + 87, y), 3),
            ((x, y + 87), 6), ((x - 87, y), 9),
        ):
            with self.subTest(point=point):
                self.assertEqual(practice_hour_at_point(point), hour)
                self.assertIsNone(practice_quarter_at_point(point))
        self.assertEqual(practice_hour_at_point((x + 111, y)), 3)
        for point in ((x, y), (x + 120, y), (x + 150, y)):
            self.assertIsNone(practice_hour_at_point(point))
        self.assertIsNone(practice_quarter_at_point((x + 120, y)))
        self.assertEqual(practice_quarter_at_point((x + 150, y)), 15)

    def test_touching_hours_changes_only_imagined_time_and_not_counters(self) -> None:
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame
        from activity_incubator.tempo_di_greia.time_app import TimeActivity
        from activity_incubator.tempo_di_greia.time_renderer import WORD_KEYS
        from activity_incubator.tempo_di_greia.time_interaction import DIAL_CENTER
        pygame.init()
        try:
            wall = datetime(2026, 10, 8, 23, 45, tzinfo=timezone.utc)
            monotonic = FakeClock()
            state = TimeExperience(wall_now=lambda: wall, monotonic=monotonic)
            state.timer.set_duration(180)
            state.timer.start()
            state.stopwatch.start()
            app = TimeActivity(pygame.Surface((1024, 600)), "it",
                               {key: key for key in WORD_KEYS}, state)
            x, y = DIAL_CENTER
            app.press((x + 87, y))
            self.assertEqual(state.shown_time(), wall)
            state.set_practice(True)
            app.press((x + 87, y))
            self.assertEqual((state.shown_time().hour, state.shown_time().minute), (15, 45))
            app.press((x + 150, y))
            self.assertEqual((state.shown_time().hour, state.shown_time().minute), (15, 15))
            app.press((x + 111, y))  # visible hour numeral is also touchable
            self.assertEqual((state.shown_time().hour, state.shown_time().minute), (15, 15))
            app.press((x + 120, y))  # intentional radial gap
            self.assertEqual((state.shown_time().hour, state.shown_time().minute), (15, 15))
            state.set_practice_hour(12)
            self.assertEqual(state.shown_time().hour, 12)
            for invalid in (True, 0, 13, 2.5):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    state.set_practice_hour(invalid)
            monotonic.value += 20
            self.assertEqual(state.timer.remaining(), 160)
            self.assertEqual(state.stopwatch.seconds(), 20)
            state.set_practice(False)
            self.assertEqual(state.shown_time(), wall)
            app.renderer.draw(app.canvas.surface, state)
            app.renderer.fonts.clear()
        finally:
            pygame.quit()

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

    def test_bilingual_renderer_key_contract_is_complete(self) -> None:
        import json
        from pathlib import Path
        from activity_incubator.tempo_di_greia.time_renderer import WORD_KEYS
        root = Path(__file__).resolve().parents[1] / "activity_incubator" / "tempo_di_greia"
        for locale in ("it", "en"):
            data = json.loads((root / "locales" / (locale + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(set(WORD_KEYS), set(data["strings"]) - {"activity.title"})
            self.assertEqual(data["audio"], {})


    def test_composition_root_uses_platform_localized_text_api(self) -> None:
        """Actually enter main(): model-only tests must not mask a broken launch path."""
        import os
        from unittest.mock import patch

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

        import pygame
        from activity_incubator.tempo_di_greia import main as entrypoint
        from activity_incubator.tempo_di_greia.time_renderer import WORD_KEYS

        launches: list[tuple[str, dict[str, str]]] = []

        class FakeTimeActivity:
            def __init__(self, screen, locale, words) -> None:
                self.screen = screen
                launches.append((locale, words))

            def run(self) -> int:
                return 0

        try:
            for locale in ("it", "en"):
                with self.subTest(locale=locale):
                    with (
                        patch.object(entrypoint, "get_profile_locale", return_value=locale),
                        patch.object(entrypoint, "TimeActivity", FakeTimeActivity),
                    ):
                        self.assertEqual(entrypoint.main(), 0)
                    selected, words = launches[-1]
                    self.assertEqual(selected, locale)
                    self.assertEqual(set(words), set(WORD_KEYS))
                    self.assertTrue(all(isinstance(value, str) and value for value in words.values()))
        finally:
            pygame.quit()

    def test_safe_pointer_excludes_trusted_home_at_both_screen_sizes(self) -> None:
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame
        from greia_platform.pygame_canvas import activity_viewport_for_surface
        from activity_incubator.tempo_di_greia.time_app import TimeActivity
        from activity_incubator.tempo_di_greia.time_renderer import WORD_KEYS

        pygame.init()
        try:
            for size in ((1024, 600), (800, 480)):
                with self.subTest(size=size):
                    screen = pygame.Surface(size)
                    state = TimeExperience(
                        wall_now=lambda: datetime(2026, 10, 8, 9, 30, tzinfo=timezone.utc),
                        monotonic=FakeClock(),
                    )
                    app = TimeActivity(screen, "it", {key: key for key in WORD_KEYS}, state)
                    protected = activity_viewport_for_surface(screen).protected_regions[0]
                    self.assertIsNone(app._logical_point(
                        (int(protected.x) + 1, int(protected.y) + 1)))
                    self.assertIsNone(app._logical_point((-1, -1)))
                    app.press((500, 45))  # Clock top-tab is not trusted Home.
                    self.assertEqual(state.mode, TimeMode.CLOCK)
                    app.renderer.fonts.clear()
        finally:
            pygame.quit()

    def test_practice_dial_click_updates_only_simulated_minute(self) -> None:
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from activity_incubator.tempo_di_greia.time_app import TimeActivity
        from activity_incubator.tempo_di_greia.time_renderer import WORD_KEYS
        from activity_incubator.tempo_di_greia.time_interaction import DIAL_CENTER
        pygame.init()
        try:
            screen = pygame.Surface((1024, 600))
            wall = datetime(2026, 10, 8, 12, 13, tzinfo=timezone.utc)
            state = TimeExperience(wall_now=lambda: wall, monotonic=FakeClock())
            app = TimeActivity(screen, "it", {key: key for key in WORD_KEYS}, state)
            cx, cy = DIAL_CENTER
            # The actual clock is read-only even if a child taps its dial.
            app.press((cx + 150, cy))
            self.assertEqual(state.shown_time(), wall)
            state.set_practice(True)
            app.press((cx + 150, cy))
            self.assertEqual(state.shown_time().minute, 15)
            app.press((cx, cy + 150))
            self.assertEqual(state.shown_time().minute, 30)
            app.press((cx, cy))  # center is not a touch stop
            self.assertEqual(state.shown_time().minute, 30)
            self.assertEqual(wall.minute, 13)
            app.renderer.draw(app.canvas.surface, state)  # real paint path
            app.renderer.fonts.clear()
        finally:
            pygame.quit()

    def test_keyboard_focus_can_use_visible_controls_without_text_commands(self) -> None:
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame
        from activity_incubator.tempo_di_greia.time_app import TimeActivity
        from activity_incubator.tempo_di_greia.time_renderer import WORD_KEYS
        pygame.init()
        try:
            model = TimeExperience(
                wall_now=lambda: datetime(2026, 10, 8, 9, tzinfo=timezone.utc),
                monotonic=FakeClock(),
            )
            app = TimeActivity(pygame.Surface((1024, 600)), "it",
                               {key: key for key in WORD_KEYS}, model)
            move = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
            activate = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
            app.handle_event(move)
            self.assertEqual(app.focus_id, "mode.clock")
            app.handle_event(move)
            self.assertEqual(app.focus_id, "mode.stopwatch")
            app.handle_event(activate)
            self.assertIs(model.mode, TimeMode.STOPWATCH)
            app.handle_event(move)
            self.assertEqual(app.focus_id, "mode.timer")
            app.handle_event(activate)
            self.assertIs(model.mode, TimeMode.TIMER)
            app._focus_move(1)
            self.assertEqual(app.focus_id, "primary")
            app.handle_event(activate)
            self.assertTrue(model.timer.running)
            app.handle_event(activate)
            self.assertFalse(model.timer.running)
            app.renderer.draw(app.canvas.surface, model,
                              focus_rect=app._targets()[3][1])
            app.renderer.fonts.clear()
        finally:
            pygame.quit()

    def test_mode_is_semantic_and_timer_not_screen_time(self) -> None:
        state = TimeExperience(monotonic=FakeClock())
        state.mode = TimeMode.TIMER
        state.timer.set_duration(180)
        self.assertEqual(state.timer.duration_seconds, 180)
        self.assertEqual(state.stopwatch.seconds(), 0.0)


if __name__ == "__main__":
    unittest.main()
