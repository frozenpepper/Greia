from __future__ import annotations

import os
from pathlib import Path
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "festa_delle_rime"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from rhyme_content import PICTURE_PENDING, RhymeMode, get_corpus  # noqa: E402
from rhyme_model import (  # noqa: E402
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    RhymeRoundFactory,
    RhymeSession,
    adapt_level,
)
from rhyme_services import GreiaRhymeProgress, RhymeProgress  # noqa: E402


def _group_index(locale: str) -> dict[str, int]:
    groups, _ = get_corpus(locale)
    return {item.item_id: index for index, group in enumerate(groups) for item in group}


class RhymeContentTests(unittest.TestCase):
    def test_en_it_words_have_approved_audio_and_library_pictures(self) -> None:
        from rhyme_art import resolve_picture

        for locale in ("en", "it"):
            groups, families = get_corpus(locale)
            for group in (*groups, *families):
                for item in group:
                    with self.subTest(locale=locale, word=item.item_id):
                        self.assertTrue((ACTIVITY_ROOT / "assets" / "audio" / locale / f"{item.item_id}.wav").is_file())
                        self.assertNotEqual(item.picture, PICTURE_PENDING)
                        self.assertFalse(item.picture.startswith(("🐱", "emoji")))
                        self.assertTrue(resolve_picture(item.picture).is_file(), item.picture)

    def test_rhyme_sets_stay_language_specific(self) -> None:
        en_words = {item.item_id for group in get_corpus("en")[0] for item in group}
        it_words = {item.item_id for group in get_corpus("it")[0] for item in group}
        self.assertFalse(en_words & it_words)
        self.assertGreaterEqual(len(get_corpus("en")[0]), 9)
        self.assertGreaterEqual(len(get_corpus("it")[0]), 8)

    def test_prompts_and_praise_use_existing_recordings(self) -> None:
        for locale in ("en", "it"):
            for cue in ("prompt_rhyme", "prompt_odd", "prompt_find_rhyme", "praise_rhyme"):
                self.assertTrue((ACTIVITY_ROOT / "assets" / "audio" / locale / f"{cue}.wav").is_file())


class RhymeRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic(self) -> None:
        first = RhymeRoundFactory(random.Random(12345), locale="it").build_set(1)
        second = RhymeRoundFactory(random.Random(12345), locale="it").build_set(1)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

    def test_stage_modes_and_choice_counts(self) -> None:
        expected = {
            1: (RhymeMode.RHYME_MATCH, 2),
            2: (RhymeMode.RHYME_MATCH, 3),
            3: (RhymeMode.RHYME_MATCH, 3),
            4: (RhymeMode.RHYME_ODD, 3),
        }
        for locale in ("it", "en"):
            factory = RhymeRoundFactory(random.Random(42), locale=locale)
            for level, (mode, count) in expected.items():
                challenges = factory.build_set(level)
                self.assertTrue(all(challenge.mode == mode for challenge in challenges))
                self.assertTrue(all(len(challenge.choices) == count for challenge in challenges))

    def test_only_the_answer_rhymes_and_pictures_never_repeat(self) -> None:
        for locale in ("it", "en"):
            group_of = _group_index(locale)
            for level in range(1, 5):
                for seed in range(60):
                    challenges = RhymeRoundFactory(random.Random(seed), locale).build_set(level)
                    slots = [c.correct_index for c in challenges]
                    self.assertTrue(all(a != b for a, b in zip(slots, slots[1:])), "answer slot repeats")
                    for c in challenges:
                        pictures = [item.picture for item in c.choices]
                        if c.target_item is not None:
                            pictures.append(c.target_item.picture)
                        self.assertEqual(len(pictures), len(set(pictures)))
                        if c.mode is RhymeMode.RHYME_ODD:
                            first, second = c.rhyme_words
                            self.assertEqual(group_of[first.item_id], group_of[second.item_id])
                            self.assertNotEqual(group_of[c.answer.item_id], group_of[first.item_id])
                            continue
                        target_group = group_of[c.target_item.item_id]
                        for index, item in enumerate(c.choices):
                            rhymes = group_of.get(item.item_id) == target_group
                            self.assertEqual(rhymes, index == c.correct_index, (locale, level, c))

    def test_tricky_stage_uses_same_start_lures(self) -> None:
        _, families = get_corpus("en")
        family_of = {item.item_id: index for index, family in enumerate(families) for item in family}
        challenges = RhymeRoundFactory(random.Random(3), "en").build_set(3)
        lured = 0
        for c in challenges:
            target_family = family_of.get(c.target_item.item_id)
            lured += sum(
                1 for i, item in enumerate(c.choices)
                if i != c.correct_index and family_of.get(item.item_id) == target_family
            )
        self.assertGreaterEqual(lured, CHALLENGE_COUNT)


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.stopped = 0

    def play_speech(self, cue_id: str) -> float | None:
        self.played.append(cue_id)
        return None

    def play_sfx(self, cue: str) -> None:
        self.played.append(cue)

    def stop_speech(self) -> None:
        self.stopped += 1


class SpeechQueueTests(unittest.TestCase):
    def test_queue_is_bounded_sequenced_and_cancels(self) -> None:
        from rhyme_audio import MAX_QUEUE_LEN, SILENT_CUE_SECONDS, SpeechQueue

        audio = _MockAudio()
        queue = SpeechQueue(audio)
        for index in range(MAX_QUEUE_LEN + 3):
            queue.enqueue(f"cue{index}", tag=f"t{index}", gap=0.1)
        self.assertTrue(queue.update(0.01))
        self.assertEqual(audio.played, ["cue0"])
        self.assertEqual(queue.current_tag, "t0")
        queue.update(SILENT_CUE_SECONDS + 0.11)
        self.assertEqual(audio.played, ["cue0", "cue1"])
        queue.clear()
        self.assertEqual(audio.stopped, 1)
        self.assertFalse(queue.busy)
        self.assertIsNone(queue.current_tag)


class RhymeSessionTests(unittest.TestCase):
    def test_wrong_then_correct_choice(self) -> None:
        session = RhymeSession(RhymeRoundFactory(random.Random(42), locale="it").build_set(2), level=2)
        challenge = session.current_challenge
        assert challenge is not None
        wrong_index = 1 if challenge.correct_index == 0 else 0
        result = session.select_choice(wrong_index)
        self.assertFalse(result.correct)
        self.assertEqual(result.errors, 1)
        self.assertEqual(session.eliminated, frozenset({wrong_index}))
        self.assertEqual(session.challenge_index, 0)
        self.assertTrue(session.select_choice(challenge.correct_index).correct)
        self.assertEqual(session.challenge_index, 1)
        self.assertEqual(session.found, (challenge.answer,))
        self.assertEqual(session.previous_challenge, challenge)
        self.assertEqual(session.eliminated, frozenset())
        self.assertIsNotNone(session.consume_milestone())
        self.assertFalse(session.history[-1].first_attempt_success)

    def test_idle_hint_counts_but_first_attempt_stays(self) -> None:
        session = RhymeSession(RhymeRoundFactory(random.Random(7), locale="en").build_set(1), level=1)
        session.record_hint()
        challenge = session.current_challenge
        session.select_choice(challenge.correct_index)
        self.assertEqual(session.history[-1], AttemptSummary(True, 1, False))

    def test_completion_payload_is_one_shot(self) -> None:
        session = RhymeSession(RhymeRoundFactory(random.Random(42), locale="it").build_set(1), level=1)
        while not session.is_complete:
            challenge = session.current_challenge
            assert challenge is not None
            session.select_choice(challenge.correct_index)
        self.assertEqual(len(session.found), CHALLENGE_COUNT)
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

    def test_existing_v1_save_still_loads(self) -> None:
        saved = {
            "schema_version": 1,
            "level": 4,
            "history": [{"first_attempt_success": True, "hints_used": 0, "used_retry": False}],
        }
        progress = GreiaRhymeProgress(_Storage(saved)).load()
        self.assertEqual(progress.level, 4)
        self.assertEqual(progress.history, (AttemptSummary(True, 0, False),))
        # Every saved stage still builds a playable festival.
        RhymeSession(RhymeRoundFactory(random.Random(1), "it").build_set(progress.level), level=progress.level)


class _MockEvents:
    def __init__(self) -> None:
        self.milestones = []
        self.completions = []

    def match_completed(self, session_id, payload) -> None:
        self.milestones.append(payload)

    def festival_completed(self, session_id, payload) -> None:
        self.completions.append(payload)


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _app(self, locale: str = "it", level: int = 1, *, size=(1024, 600)):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from rhyme_app import RhymeActivity
        from rhyme_art import RhymeArt
        from rhyme_audio import SpeechQueue
        from rhyme_renderer import RhymeRenderer

        screen = pygame.display.set_mode(size)
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale(locale, support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        self.storage = _Storage({"schema_version": 1, "level": level, "history": []})
        self.events = _MockEvents()
        self.audio = _MockAudio()
        rng = random.Random(99)
        factory = RhymeRoundFactory(rng, locale=locale)
        self.now = [100.0]
        app = RhymeActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=RhymeSession(factory.build_set(level), level=level),
            factory=factory,
            renderer=RhymeRenderer(RhymeArt(1024, 600)),
            typography=typography,
            resources=resources,
            progress=GreiaRhymeProgress(self.storage),
            events=self.events,
            audio=self.audio,
            speech_queue=SpeechQueue(self.audio),
            rng=rng,
            session_id="rhyme-session-1",
            clock=lambda: self.now[0],
        )
        return app

    def _run(self, app, seconds: float, step: float = 0.1) -> None:
        for _ in range(int(seconds / step)):
            self.now[0] += step
            app.tick()
            app._render()

    def _tap_choice(self, app, index: int) -> bool:
        center = app.controls.choice_center(index)
        physical = app.canvas.mapper.transform.logical_to_physical(center)
        return app._handle_pointer((int(physical[0]), int(physical[1])))

    def test_full_round_plays_to_completion_with_feedback_grammar(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from rhyme_app import AppState

        app = self._app("it", level=1)
        self._run(app, 0.6)
        self.assertIn("leo.ready", self.audio.played)
        self.assertIn("prompt_rhyme", self.audio.played)
        self._run(app, 4.0)

        # Idle hint: Leo points and the words are replayed.
        self._run(app, 6.5)
        self.assertTrue(app.scene_state().leo_pointing)
        self.assertIn("prompt_find_rhyme", self.audio.played)

        # A wrong pick: think pose, the tile is retired, unlimited retry.
        challenge = app.session.current_challenge
        wrong = 1 - challenge.correct_index
        self.assertTrue(self._tap_choice(app, wrong))
        self.assertEqual(app.state, AppState.TRY_AGAIN)
        self.assertEqual(app.renderer.cast.pose, CastPose.THINK)
        self._run(app, 0.1)
        self.assertIn("leo.retry", self.audio.played)
        self.assertFalse(app.controls.choices[wrong].enabled)
        self._run(app, 0.6)
        self.assertEqual(app.state, AppState.PLAYING)

        for _ in range(CHALLENGE_COUNT):
            challenge = app.session.current_challenge
            self.assertIsNotNone(challenge)
            self.assertTrue(self._tap_choice(app, challenge.correct_index))
            self.assertEqual(app.state, AppState.CELEBRATE)
            self.assertEqual(app.renderer.cast.pose, CastPose.CHEER)
            self._run(app, 0.5)
            self.assertIsNotNone(app.scene_state().flight)
            for _ in range(60):
                if app.state is not AppState.CELEBRATE:
                    break
                self._run(app, 0.1)
            if app.session.is_complete:
                break
            self.assertEqual(app.state, AppState.PLAYING)

        self.assertEqual(app.state, AppState.FINALE)
        self.assertIn("praise_rhyme", self.audio.played)
        self.assertEqual(len(self.events.milestones), CHALLENGE_COUNT)
        self.assertEqual(len(self.events.completions), 1)
        self.assertIsNotNone(self.storage.saved)
        self._run(app, 3.0)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertIn("leo.celebrate", self.audio.played)

        primary = app.completion.primary_rect
        physical = app.canvas.mapper.transform.logical_to_physical(primary.center)
        self.assertTrue(app._handle_terminal_pointer((int(physical[0]), int(physical[1]))))
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.session.challenge_index, 0)

    def test_keyboard_and_controller_navigation_choose_a_picture(self) -> None:
        from rhyme_app import AppState

        app = self._app("en", level=2)
        challenge = app.session.current_challenge
        self.assertEqual(app.controls.layer.focused_id, "choice.0")
        for _ in range(challenge.correct_index):
            self.assertTrue(app._handle_keyboard(pygame.K_RIGHT))
        self.assertEqual(app.controls.layer.focused_id, f"choice.{challenge.correct_index}")
        self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
        self.assertEqual(app.state, AppState.CELEBRATE)

    def test_replay_key_and_listen_button_repeat_the_words(self) -> None:
        app = self._app("en", level=1)
        self._run(app, 8.0)
        self.audio.played.clear()
        self.assertTrue(app._handle_keyboard(pygame.K_r))
        app.tick()
        self.assertEqual(self.audio.played[:1], [app.session.current_challenge.target_item.item_id])
        self._run(app, 5.0)
        self.audio.played.clear()
        listen = app.controls.listen.rect.center
        physical = app.canvas.mapper.transform.logical_to_physical(listen)
        self.assertTrue(app._handle_pointer((int(physical[0]), int(physical[1]))))

    def test_odd_one_out_stage_and_protected_chrome(self) -> None:
        from rhyme_app import AppState

        app = self._app("en", level=4)
        self._run(app, 0.6)
        self.assertIn("prompt_odd", self.audio.played)
        self.assertFalse(app._handle_pointer((10, 10)))  # Home/Back region never reaches the Activity
        challenge = app.session.current_challenge
        self.assertTrue(self._tap_choice(app, challenge.correct_index))
        self.assertEqual(app.state, AppState.CELEBRATE)

    def test_small_screens_keep_controls_clear_of_home(self) -> None:
        for size in ((800, 480), (480, 320)):
            with self.subTest(size=size):
                app = self._app("it", level=2, size=size)
                protected = app.controls.layer.target("listen").rect
                from greia_platform.activity_controls import ControlLayout

                layout = ControlLayout.for_canvas(app.canvas, size)
                self.assertFalse(protected.colliderect(layout.protected))
                for slot in app.controls.geometry.slots:
                    self.assertFalse(slot.colliderect(layout.protected))
                self._run(app, 1.0)


if __name__ == "__main__":
    unittest.main()
