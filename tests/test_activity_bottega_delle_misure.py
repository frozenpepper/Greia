from __future__ import annotations

from pathlib import Path
import random
import sys
import unittest

import pygame

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "bottega_delle_misure"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from measure_model import (  # noqa: E402
    Attribute,
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    MeasureChallenge,
    MeasureItem,
    MeasureMode,
    MeasureRoundFactory,
    MeasureSession,
    adapt_level,
)
from measure_services import GreiaMeasureProgress, MeasureProgress  # noqa: E402


class MeasureRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_challenges_stay_in_range(self) -> None:
        first = MeasureRoundFactory(random.Random(12345)).build_set(3)
        second = MeasureRoundFactory(random.Random(12345)).build_set(3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)
        for challenge in first:
            self.assertTrue(1 <= challenge.target_units <= 8)
            self.assertTrue(challenge.items)
            self.assertTrue(all(1 <= item.units <= 8 for item in challenge.items))

    def test_level_modes_follow_progression(self) -> None:
        factory = MeasureRoundFactory(random.Random(999))
        expected = {
            1: MeasureMode.COMPARE,
            2: MeasureMode.ORDER,
            3: MeasureMode.MEASURE,
            4: MeasureMode.SHELF,
        }
        for level, mode in expected.items():
            challenges = factory.build_set(level, count=10)
            self.assertTrue(all(challenge.mode == mode for challenge in challenges))


class MeasureSessionTests(unittest.TestCase):
    def test_compare_mode_wrong_then_correct(self) -> None:
        item_a = MeasureItem("item_a", 2, Attribute.LENGTH, 0)
        item_b = MeasureItem("item_b", 4, Attribute.LENGTH, 1)
        challenge = MeasureChallenge(
            challenge_id="test-c1",
            mode=MeasureMode.COMPARE,
            attribute=Attribute.LENGTH,
            items=(item_a, item_b),
            target_id="item_b",
            target_units=4,
            unit_capacity=0,
            choice_values=(4, 5, 6),
            prompt_key="prompt.compare_longer",
        )
        session = MeasureSession([challenge] * 5, level=1)
        wrong = session.select_item("item_a")
        assert wrong is not None
        self.assertFalse(wrong.correct)
        self.assertEqual(session.challenge_index, 0)
        correct = session.select_item("item_b")
        assert correct is not None
        self.assertTrue(correct.correct)
        self.assertEqual(session.challenge_index, 1)
        self.assertIsNotNone(session.consume_milestone())

    def test_order_mode_seriation(self) -> None:
        items = (
            MeasureItem("i2", 3, Attribute.HEIGHT, 1),
            MeasureItem("i1", 1, Attribute.HEIGHT, 0),
            MeasureItem("i3", 5, Attribute.HEIGHT, 2),
        )
        challenge = MeasureChallenge(
            challenge_id="test-c2",
            mode=MeasureMode.ORDER,
            attribute=Attribute.HEIGHT,
            items=items,
            target_id="ordered",
            target_units=3,
            unit_capacity=0,
            choice_values=(1, 2, 3),
            prompt_key="prompt.order_height",
        )
        session = MeasureSession([challenge] * 5, level=2)
        session.select_item("i2")
        session.select_item("i1")
        wrong = session.select_item("i3")
        assert wrong is not None
        self.assertFalse(wrong.correct)
        session.select_item("i1")
        session.select_item("i2")
        correct = session.select_item("i3")
        assert correct is not None
        self.assertTrue(correct.correct)

    def test_completion_payload_is_one_shot(self) -> None:
        session = MeasureSession(MeasureRoundFactory(random.Random(42)).build_set(3), level=3)
        while not session.is_complete:
            current = session.current_challenge
            assert current is not None
            session.select_answer_value(current.target_units)
        self.assertIsNotNone(session.consume_completion())
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
        repo = GreiaMeasureProgress(storage)
        self.assertEqual(repo.load(), MeasureProgress())
        history = [AttemptSummary(True, 0, False) for _ in range(20)]
        repo.save(3, history)
        self.assertEqual(storage.saved["level"], 3)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class _MockEvents:
    def __init__(self) -> None:
        self.milestones = []
        self.completions = []

    def parcel_completed(self, session_id, payload) -> None:
        self.milestones.append(payload)

    def delivery_completed(self, session_id, payload) -> None:
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

    def test_full_session_completes_and_restarts(self) -> None:
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from measure_app import AppState, BottegaActivity
        from measure_art import MeasureArt
        from measure_renderer import CHOICE_RECTS, MeasureRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        renderer = MeasureRenderer(MeasureArt(1024, 600), typography, resources)
        storage = _Storage({"schema_version": 1, "level": 3, "history": []})
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(88)
        factory = MeasureRoundFactory(rng)
        session = MeasureSession(factory.build_set(3), level=3)
        simulated_time = [100.0]
        app = BottegaActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=session,
            factory=factory,
            renderer=renderer,
            typography=typography,
            resources=resources,
            progress=GreiaMeasureProgress(storage),
            events=events,
            audio=audio,
            rng=rng,
            session_id="bottega-session-1",
            clock=lambda: simulated_time[0],
        )

        for _ in range(5):
            current = app.session.current_challenge
            assert current is not None
            choice_idx = next(i for i, value in enumerate(current.choice_values) if value == current.target_units)
            rect = CHOICE_RECTS[choice_idx]
            app._handle_pointer((rect.centerx, rect.centery))
            simulated_time[0] += 0.6
            app._advance_state()
            simulated_time[0] += 0.3
            app._advance_state()

        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.completions), 1)
        self.assertEqual(len(events.milestones), 5)
        handled = app._handle_terminal_pointer(
            (app.completion._primary_rect.centerx, app.completion._primary_rect.centery)
        )
        self.assertTrue(handled)
        self.assertEqual(app.state, AppState.PLAYING)


if __name__ == "__main__":
    unittest.main()
