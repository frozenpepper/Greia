from __future__ import annotations

from pathlib import Path
import random
import sys
import unittest

import pygame

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "festa_delle_rime"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from rhyme_content import RhymeMode  # noqa: E402
from rhyme_model import (  # noqa: E402
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    RhymeRoundFactory,
    RhymeSession,
    adapt_level,
)
from rhyme_services import GreiaRhymeProgress, RhymeProgress  # noqa: E402


class RhymeRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic(self) -> None:
        first = RhymeRoundFactory(random.Random(12345), locale="it").build_set(1)
        second = RhymeRoundFactory(random.Random(12345), locale="it").build_set(1)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

    def test_level_modes_and_choice_counts(self) -> None:
        expected = {
            1: (RhymeMode.RHYME_MATCH, 2),
            2: (RhymeMode.RHYME_MATCH, 3),
            3: (RhymeMode.RHYME_ODD, 3),
            4: (RhymeMode.ALLITERATION, 3),
        }
        for locale in ("it", "en"):
            factory = RhymeRoundFactory(random.Random(42), locale=locale)
            for level, (mode, count) in expected.items():
                challenges = factory.build_set(level)
                self.assertTrue(all(challenge.mode == mode for challenge in challenges))
                self.assertTrue(all(len(challenge.choices) == count for challenge in challenges))


class _MockAudio:
    def __init__(self) -> None:
        self.played = []
        self.stopped = 0

    def play(self, cue_id: str) -> None:
        self.played.append(cue_id)

    def play_speech(self, cue_id: str) -> None:
        self.played.append(cue_id)

    def play_feedback(self, correct: bool) -> None:
        self.played.append("correct" if correct else "retry")

    def play_sfx(self, cue: str) -> None:
        self.played.append(cue)

    def stop_speech(self) -> None:
        self.stopped += 1

    def is_speech_busy(self) -> bool:
        return False


class SpeechQueueTests(unittest.TestCase):
    def test_queue_is_bounded_and_cancels(self) -> None:
        from rhyme_audio import SpeechQueue

        audio = _MockAudio()
        queue = SpeechQueue(audio)
        for cue in ("cue1", "cue2", "cue3", "cue4", "cue5"):
            queue.enqueue(cue, delay_after=0.1)
        queue.update(0.01)
        self.assertEqual(audio.played, ["cue1"])
        queue.clear()
        self.assertEqual(audio.stopped, 1)


class RhymeSessionTests(unittest.TestCase):
    def test_wrong_then_correct_choice(self) -> None:
        session = RhymeSession(
            RhymeRoundFactory(random.Random(42), locale="it").build_set(1),
            level=1,
        )
        challenge = session.current_challenge
        assert challenge is not None
        wrong_index = 1 if challenge.correct_index == 0 else 0
        self.assertFalse(session.select_choice(wrong_index).correct)
        self.assertEqual(session.challenge_index, 0)
        self.assertTrue(session.select_choice(challenge.correct_index).correct)
        self.assertEqual(session.challenge_index, 1)
        self.assertIsNotNone(session.consume_milestone())

    def test_completion_payload_is_one_shot(self) -> None:
        session = RhymeSession(
            RhymeRoundFactory(random.Random(42), locale="it").build_set(1),
            level=1,
        )
        while not session.is_complete:
            challenge = session.current_challenge
            assert challenge is not None
            session.select_choice(challenge.correct_index)
        self.assertIsNotNone(session.consume_completion())
        self.assertIsNone(session.consume_completion())


class AdaptationTests(unittest.TestCase):
    def test_adaptation_respects_bounds(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        struggling = [AttemptSummary(False, 2, True) for _ in range(3)]
        self.assertEqual(adapt_level(1, strong), 2)
        self.assertEqual(adapt_level(4, strong), 4)
        self.assertEqual(adapt_level(3, struggling), 2)
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
        repo = GreiaRhymeProgress(storage)
        self.assertEqual(repo.load(), RhymeProgress())
        history = [AttemptSummary(True, 0, False) for _ in range(20)]
        repo.save(2, history)
        self.assertEqual(storage.saved["level"], 2)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class _MockEvents:
    def __init__(self) -> None:
        self.milestones = []
        self.completions = []

    def match_completed(self, session_id, payload) -> None:
        self.milestones.append(payload)

    def festival_completed(self, session_id, payload) -> None:
        self.completions.append(payload)


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def test_full_session_completes_and_restarts_without_real_audio(self) -> None:
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from rhyme_app import AppState, RhymeActivity
        from rhyme_art import RhymeArt
        from rhyme_audio import SpeechQueue
        from rhyme_renderer import RhymeRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        renderer = RhymeRenderer(RhymeArt(1024, 600, typography), typography, resources)
        storage = _Storage({"schema_version": 1, "level": 1, "history": []})
        events = _MockEvents()
        audio = _MockAudio()
        speech_queue = SpeechQueue(audio)
        rng = random.Random(99)
        factory = RhymeRoundFactory(rng, locale="it")
        session = RhymeSession(factory.build_set(1), level=1)
        simulated_time = [100.0]
        app = RhymeActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=session,
            factory=factory,
            renderer=renderer,
            typography=typography,
            resources=resources,
            progress=GreiaRhymeProgress(storage),
            events=events,
            audio=audio,
            speech_queue=speech_queue,
            rng=rng,
            session_id="rhyme-session-1",
            clock=lambda: simulated_time[0],
        )

        for _ in range(8):
            challenge = app.session.current_challenge
            assert challenge is not None
            rect = app.renderer.choice_rect_at(challenge, challenge.correct_index)
            app._handle_pointer((rect.centerx, rect.centery))
            simulated_time[0] += 1.0
            app._advance_state()

        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.completions), 1)
        self.assertEqual(len(events.milestones), 8)
        handled = app._handle_terminal_pointer(
            (app.completion._primary_rect.centerx, app.completion._primary_rect.centery)
        )
        self.assertTrue(handled)
        self.assertEqual(app.state, AppState.PLAYING)


if __name__ == "__main__":
    unittest.main()
