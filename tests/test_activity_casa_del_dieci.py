from __future__ import annotations

from pathlib import Path
import random
import sys
import unittest

import pygame

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "casa_del_dieci"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from ten_house_model import (  # noqa: E402
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    OperationMode,
    TenHouseChallenge,
    TenHouseRoundFactory,
    TenHouseSession,
    adapt_level,
)
from ten_house_services import GreiaTenHouseProgress, TenHouseProgress  # noqa: E402


class TenHouseRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_challenges_stay_in_range(self) -> None:
        first = TenHouseRoundFactory(random.Random(12345)).build_set(3)
        second = TenHouseRoundFactory(random.Random(12345)).build_set(3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)
        for challenge in first:
            self.assertTrue(0 <= challenge.answer <= 10)
            self.assertIn(challenge.answer, challenge.choice_values)
            self.assertEqual(len(set(challenge.choice_values)), 3)

    def test_arithmetic_invariants_hold_across_levels(self) -> None:
        factory = TenHouseRoundFactory(random.Random(999))
        for level in range(1, 6):
            for challenge in factory.build_set(level, count=12):
                if challenge.mode == OperationMode.ADD:
                    self.assertEqual(challenge.starting_lit + challenge.delta, challenge.answer)
                elif challenge.mode == OperationMode.TAKE_AWAY:
                    self.assertEqual(challenge.starting_lit - challenge.delta, challenge.answer)
                elif challenge.mode == OperationMode.MISSING_PART:
                    self.assertEqual(challenge.starting_lit + challenge.answer, challenge.target)


class TenHouseSessionTests(unittest.TestCase):
    def test_compose_mode_toggle_and_confirm(self) -> None:
        challenge = TenHouseChallenge(
            challenge_id="test-1",
            mode=OperationMode.COMPOSE,
            target=4,
            starting_lit=1,
            delta=0,
            answer=4,
            choice_values=(4, 2, 5),
        )
        session = TenHouseSession([challenge] * 6, level=1)
        for room in (1, 2, 3):
            session.toggle_room(room)
        result = session.confirm_compose()
        self.assertTrue(result.correct)
        self.assertEqual(session.challenge_index, 1)
        self.assertIsNotNone(session.consume_milestone())

    def test_wrong_choice_then_retry(self) -> None:
        challenge = TenHouseChallenge(
            challenge_id="test-2",
            mode=OperationMode.ADD,
            target=5,
            starting_lit=3,
            delta=2,
            answer=5,
            choice_values=(5, 4, 6),
        )
        session = TenHouseSession([challenge] * 6, level=3)
        wrong = session.choose(4)
        self.assertFalse(wrong.correct)
        self.assertEqual(session.challenge_index, 0)
        correct = session.choose(5)
        self.assertTrue(correct.correct)
        self.assertTrue(correct.used_retry)
        self.assertEqual(session.challenge_index, 1)

    def test_completion_payload_is_one_shot(self) -> None:
        session = TenHouseSession(TenHouseRoundFactory(random.Random(42)).build_set(2), level=2)
        while not session.is_complete:
            current = session.current_challenge
            assert current is not None
            if current.mode == OperationMode.COMPOSE:
                session.room_states = [False] * 10
                for index in range(current.target):
                    session.room_states[index] = True
                session.confirm_compose()
            else:
                session.choose(current.answer)
        payload = session.consume_completion()
        self.assertIsNotNone(payload)
        self.assertIsNone(session.consume_completion())


class AdaptationTests(unittest.TestCase):
    def test_adaptation_respects_level_bounds(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        struggling = [AttemptSummary(False, 2, True) for _ in range(3)]
        self.assertEqual(adapt_level(1, strong), 2)
        self.assertEqual(adapt_level(5, strong), 5)
        self.assertEqual(adapt_level(4, struggling), 3)
        self.assertEqual(adapt_level(1, struggling), 1)


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        self.saved = value


class ProgressTests(unittest.TestCase):
    def test_malformed_storage_recovers_and_save_is_bounded(self) -> None:
        storage = _Storage({"schema_version": 1, "level": 99, "history": "corrupt"})
        repo = GreiaTenHouseProgress(storage)
        self.assertEqual(repo.load(), TenHouseProgress())
        history = [AttemptSummary(True, 0, False) for _ in range(20)]
        repo.save(3, history)
        self.assertEqual(storage.saved["level"], 3)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class _MockEvents:
    def __init__(self) -> None:
        self.milestones = []
        self.completions = []

    def room_completed(self, session_id, payload) -> None:
        self.milestones.append(payload)

    def house_completed(self, session_id, payload) -> None:
        self.completions.append(payload)


class _MockAudio:
    def __init__(self) -> None:
        self.played = []

    def play(self, cue: str) -> None:
        self.played.append(cue)

    def play_speech(self, cue: str) -> None:
        pass

    def play_feedback(self, correct: bool) -> None:
        self.played.append("correct" if correct else "retry")

    def stop_speech(self) -> None:
        pass

    def is_speech_busy(self) -> bool:
        return False


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, level: int):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from ten_house_app import TenHouseActivity
        from ten_house_art import TenHouseArt
        from ten_house_renderer import TenHouseRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        renderer = TenHouseRenderer(TenHouseArt(1024, 600), typography, resources)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(77)
        factory = TenHouseRoundFactory(rng)
        session = TenHouseSession(factory.build_set(level), level=level)
        simulated_time = [100.0]

        app = TenHouseActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=session,
            factory=factory,
            renderer=renderer,
            typography=typography,
            resources=resources,
            progress=GreiaTenHouseProgress(storage),
            events=events,
            audio=audio,
            rng=rng,
            session_id="casa-session-1",
            clock=lambda: simulated_time[0],
        )
        return app, simulated_time, events, audio

    def test_keyboard_navigation_and_toggle(self) -> None:
        app, _, _, audio = self._build_app(level=1)
        app._handle_keyboard(pygame.K_RIGHT)
        self.assertEqual(app.session.focused_room, 1)
        app._handle_keyboard(pygame.K_SPACE)
        self.assertIn("toggle", audio.played)

    def test_controller_and_keyboard_reach_kit_controls(self) -> None:
        from greia_platform import pygame_input

        app, _, _, audio = self._build_app(level=3)
        layer = app.controls.layer
        self.assertEqual(layer.focused_id, "choice.1")
        app._handle_keyboard(pygame.K_UP)
        self.assertEqual(layer.focused_id, "prompt.replay")
        app._handle_keyboard(pygame.K_DOWN)
        self.assertTrue(layer.focused_id.startswith("choice."))
        if pygame_input.sdl_controller is not None and pygame_input._CONTROLLER_BUTTON_DOWN >= 0:
            press = pygame_input._CONTROLLER_BUTTON_DOWN
            for _ in range(3):
                app._handle_event(pygame.event.Event(press, button=pygame_input.CONTROLLER_BUTTON_DPAD_LEFT))
            self.assertEqual(layer.focused_id, "choice.0")
            self.assertTrue(app.session.focus_in_choices)
            self.assertEqual(app.session.focused_choice, 0)
            app._handle_event(pygame.event.Event(press, button=pygame_input.CONTROLLER_BUTTON_A))
            self.assertTrue("retry" in audio.played or "correct" in audio.played)

    def test_wrong_answer_shows_think_pose_and_keeps_retry(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, _, _, audio = self._build_app(level=3)
        current = app.session.current_challenge
        wrong = next(value for value in current.choice_values if value != current.answer)
        app._perform_choice(wrong)
        self.assertEqual(app.renderer.cast.pose, CastPose.THINK)
        self.assertIn("retry", audio.played)
        self.assertEqual(app.session.challenge_index, 0)

    def test_full_session_completes_and_restarts(self) -> None:
        from ten_house_app import AppState
        from ten_house_renderer import CHOICE_RECTS

        app, simulated_time, events, _ = self._build_app(level=3)
        for _ in range(6):
            current = app.session.current_challenge
            assert current is not None
            choice_idx = next(i for i, value in enumerate(current.choice_values) if value == current.answer)
            rect = CHOICE_RECTS[choice_idx]
            app._handle_pointer((rect.centerx, rect.centery))
            simulated_time[0] += 0.6
            app._advance_state()
            simulated_time[0] += 0.3
            app._advance_state()

        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.completions), 1)
        handled = app._handle_terminal_pointer(
            (app.completion._primary_rect.centerx, app.completion._primary_rect.centery)
        )
        self.assertTrue(handled)
        self.assertEqual(app.state, AppState.PLAYING)


if __name__ == "__main__":
    unittest.main()
