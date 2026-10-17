"""Tests for Mondo Contrari — Flash's Opposite Game (org.greia.mondo-contrari)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import tomllib
import unittest

import pygame

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "mondo_contrari"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from contrari_model import (  # noqa: E402
    PAIR_KIND,
    PAIR_POLES,
    Ask,
    AttemptSummary,
    ContrariRoundFactory,
    ContrariSession,
    HISTORY_LIMIT,
    OppositeCategory,
    PairRound,
    Phase,
    Pole,
    TaskKind,
    adapt_level,
    opposite,
    visit_size,
)
from contrari_services import ContrariProgress, GreiaContrariProgress  # noqa: E402

STATES = ("up", "down", "big", "small", "in", "out", "open", "closed", "fast", "slow")


def _round(category: OppositeCategory, first: Pole | None = None, count: int = 2) -> PairRound:
    poles = PAIR_POLES[category]
    first = first or poles[0]
    words = [first, opposite(first)] + ([first] if count == 3 else [])
    return PairRound(category, tuple(Ask(word, poles) for word in words), None)


class RoundFactoryTests(unittest.TestCase):
    def test_visits_are_finite_and_seed_deterministic(self) -> None:
        for level in (1, 2, 3):
            first = ContrariRoundFactory(random.Random(9)).build_visit(level)
            second = ContrariRoundFactory(random.Random(9)).build_visit(level)
            self.assertEqual(first, second)
            pairs, asks = visit_size(level)
            self.assertEqual(len(first), pairs)
            self.assertTrue(all(len(item.asks) == asks for item in first))
            self.assertEqual(first[0].category, OppositeCategory.UP_DOWN, "the balloon is the warm-up")
            self.assertEqual(len({item.category for item in first}), pairs, "no pair repeats in a visit")

    def test_every_pair_asks_a_word_then_its_opposite(self) -> None:
        for seed in range(40):
            for level in (1, 2, 3):
                for item in ContrariRoundFactory(random.Random(seed)).build_visit(level):
                    self.assertIs(item.asks[1].pole, opposite(item.asks[0].pole))
                    for ask in item.asks:
                        self.assertEqual(set(ask.sides), set(PAIR_POLES[item.category]))
                    if item.category is OppositeCategory.UP_DOWN:
                        self.assertTrue(all(ask.sides == (Pole.UP, Pole.DOWN) for ask in item.asks))
                    if item.kind is TaskKind.MAKE:
                        self.assertEqual(len({ask.sides for ask in item.asks}), 1)
                    if item.category in (OppositeCategory.BIG_SMALL, OppositeCategory.FAST_SLOW):
                        self.assertIsNotNone(item.subject)

    def test_level_one_never_swaps_pictures_and_level_three_reshuffles(self) -> None:
        swapped_at_three = False
        for seed in range(30):
            for item in ContrariRoundFactory(random.Random(seed)).build_visit(1):
                self.assertEqual(len({ask.sides for ask in item.asks}), 1)
            for item in ContrariRoundFactory(random.Random(seed)).build_visit(3):
                if item.kind is TaskKind.FIND:
                    self.assertNotEqual(item.asks[1].sides, item.asks[2].sides)
                    swapped_at_three = True
        self.assertTrue(swapped_at_three)

    def test_both_kinds_of_task_exist(self) -> None:
        self.assertEqual(
            {TaskKind.MAKE, TaskKind.FIND},
            set(PAIR_KIND.values()),
        )

    def test_round_rejects_a_second_word_that_is_not_the_opposite(self) -> None:
        poles = PAIR_POLES[OppositeCategory.BIG_SMALL]
        with self.assertRaises(ValueError):
            PairRound(OppositeCategory.BIG_SMALL, (Ask(Pole.BIG, poles), Ask(Pole.BIG, poles)))
        with self.assertRaises(ValueError):
            Ask(Pole.UP, (Pole.BIG, Pole.SMALL))


class SessionTests(unittest.TestCase):
    def test_wrong_then_right_keeps_retry_evidence(self) -> None:
        session = ContrariSession([_round(OppositeCategory.UP_DOWN)], level=1)
        self.assertFalse(session.choose(Pole.DOWN).correct)
        self.assertEqual(session.phase, Phase.ASKING, "unlimited kind retries")
        self.assertIn(Pole.DOWN, session.rejected)
        self.assertTrue(session.choose(Pole.UP).correct)
        self.assertTrue(session.advance())
        self.assertEqual(session.current_ask.pole, Pole.DOWN)
        result = session.choose(Pole.DOWN)
        self.assertTrue(result.round_complete and result.visit_complete)
        self.assertEqual(session.history[-1], AttemptSummary(False, 0, True))
        self.assertEqual(session.consume_milestone(), OppositeCategory.UP_DOWN)
        self.assertIsNone(session.consume_milestone())
        payload = session.consume_completion()
        self.assertEqual(payload, {"pairs": 1, "level": 1, "first_try_pairs": 0})
        self.assertIsNone(session.consume_completion())
        self.assertFalse(session.advance())
        self.assertEqual(session.phase, Phase.DONE)

    def test_answers_are_ignored_while_not_asking(self) -> None:
        session = ContrariSession([_round(OppositeCategory.IN_OUT), _round(OppositeCategory.FAST_SLOW)])
        self.assertTrue(session.choose(Pole.IN).correct)
        self.assertFalse(session.choose(Pole.OUT).correct, "a solved ask waits for advance()")
        session.advance()
        self.assertTrue(session.choose(Pole.OUT).round_complete)
        session.advance()
        self.assertEqual(session.current_round.category, OppositeCategory.FAST_SLOW)
        self.assertEqual(session.completed_rounds, 1)

    def test_history_is_bounded(self) -> None:
        history = [AttemptSummary(True, 0, False)] * (HISTORY_LIMIT + 5)
        session = ContrariSession([_round(OppositeCategory.UP_DOWN)], history=history)
        self.assertEqual(len(session.history), HISTORY_LIMIT)


class AdaptationTests(unittest.TestCase):
    def test_level_rises_after_clean_pairs_and_falls_after_retries(self) -> None:
        clean = [AttemptSummary(True, 0, False)] * 4
        self.assertEqual(adapt_level(1, clean), 2)
        self.assertEqual(adapt_level(3, clean), 3)
        shaky = [AttemptSummary(False, 1, True)] * 3
        self.assertEqual(adapt_level(2, shaky), 1)
        self.assertEqual(adapt_level(1, shaky), 1)
        self.assertEqual(adapt_level(2, [AttemptSummary(True, 1, False)] * 4), 2)


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        self.saved = value


class ProgressTests(unittest.TestCase):
    def test_missing_or_malformed_storage_recovers(self) -> None:
        self.assertEqual(GreiaContrariProgress(_Storage(None)).load(), ContrariProgress())
        storage = _Storage({"schema_version": 1, "level": 99, "history": "corrupt"})
        self.assertEqual(GreiaContrariProgress(storage).load(), ContrariProgress())
        storage = _Storage({"schema_version": 1, "level": True, "history": [{"first_attempt_success": 1}]})
        self.assertEqual(GreiaContrariProgress(storage).load(), ContrariProgress())

    def test_round_trip_is_bounded(self) -> None:
        storage = _Storage()
        repo = GreiaContrariProgress(storage)
        repo.save(3, [AttemptSummary(True, 0, False)] * 20)
        self.assertEqual(storage.saved["schema_version"], 1)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)
        storage.value = storage.saved
        loaded = repo.load()
        self.assertEqual(loaded.level, 3)
        self.assertEqual(len(loaded.history), HISTORY_LIMIT)


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_real_gameplay(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.mondo-contrari")
        self.assertEqual(manifest["activity"]["legacy_ids"], ["mondo_contrari"])
        self.assertEqual(set(manifest["activity"]["languages"]), {"it", "en", "es", "fr"})
        education = manifest["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (3, 5))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, 3))
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertEqual(
            {event["id"] for event in education["events"]},
            {"mondo_contrari.opposite_explored", "mondo_contrari.all_opposites_completed"},
        )

    def test_four_locales_keep_key_parity_and_every_concept_word(self) -> None:
        bundles = {
            language: json.loads((ACTIVITY_ROOT / "locales" / f"{language}.json").read_text(encoding="utf-8"))["strings"]
            for language in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"])
        for language, strings in bundles.items():
            with self.subTest(language=language):
                self.assertEqual(set(strings), keys)
                self.assertTrue(all(strings[f"opposite.{state}"].strip() for state in STATES))
                self.assertTrue(strings["victory.title"].strip() and strings["button.play_again"].strip())

    def test_every_concept_word_has_an_approved_clip(self) -> None:
        for language in ("en", "it"):
            folder = ACTIVITY_ROOT / "locales" / language / "audio"
            for cue in (*STATES, "welcome", "praise_1", "praise_2", "praise_3"):
                with self.subTest(language=language, cue=cue):
                    self.assertTrue((folder / f"{cue}.wav").is_file())

    def test_private_art_has_source_and_rendition(self) -> None:
        from contrari_art import PRIVATE_ART

        for name in PRIVATE_ART:
            with self.subTest(name=name):
                source = (ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg").read_text(encoding="utf-8")
                self.assertTrue((ACTIVITY_ROOT / "assets" / "runtime" / f"{name}.png").is_file())
                for forbidden in ("<image", "<text", "<filter", "<style", "<script", "<mask"):
                    self.assertNotIn(forbidden, source)


class _MockEvents:
    def __init__(self) -> None:
        self.milestones: list[str] = []
        self.completions: list[dict] = []

    def opposite_explored(self, session_id, category) -> None:
        self.milestones.append(category.value)

    def all_opposites_completed(self, session_id, payload) -> None:
        self.completions.append(payload)


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.spoken: list[str] = []

    def play(self, cue: str) -> None:
        self.played.append(cue)

    def say(self, cue: str) -> None:
        self.spoken.append(cue)

    def queue(self, cue: str) -> None:
        self.spoken.append(cue)

    def update(self) -> None:
        pass

    def length(self, cue: str) -> float:
        return 2.0

    def praise(self) -> None:
        self.spoken.append("praise")

    def encourage(self) -> None:
        self.spoken.append("retry")

    def celebrate(self) -> None:
        self.spoken.append("complete")

    def stop_speech(self) -> None:
        pass


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, level: int = 1, *, seed: int = 11, locale: str = "it"):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from contrari_app import ContrariActivity

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale(locale, support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(seed)
        factory = ContrariRoundFactory(rng)
        session = ContrariSession(factory.build_visit(level), level=level)
        clock = [100.0]
        app = ContrariActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=session,
            factory=factory,
            typography=GreiaTypography(),
            resources=resources,
            progress=GreiaContrariProgress(storage),
            events=events,
            audio=audio,
            rng=rng,
            session_id="contrari-test",
            clock=lambda: clock[0],
        )
        self._clock = clock
        self._app = app
        self._storage = storage
        return app, events, audio

    def _advance(self, seconds: float, step: float = 0.05) -> None:
        end = self._clock[0] + seconds
        while self._clock[0] < end:
            self._clock[0] += step
            self._app.step()

    def _tap_logical(self, rect: pygame.Rect) -> bool:
        return self._app.tap(rect.center)  # the test display is 1024x600: logical == physical

    def _answer(self, correct: bool = True) -> bool:
        app = self._app
        ask = app.session.current_ask
        pole = ask.pole if correct else opposite(ask.pole)
        index = app.scene.index_of(pole)
        return self._tap_logical(app.controls.choices[index].rect)

    def test_play_screen_has_no_tabs_text_or_answer_reveal(self) -> None:
        from greia_platform.activity_controls import PillButton, ToolSlot

        app, _, audio = self._build_app()
        self.assertFalse(any(isinstance(t, (PillButton, ToolSlot)) for t in app.controls.layer.targets))
        self.assertFalse(app.controls.caption.visible, "no word is printed before the child acts")
        self.assertEqual(audio.spoken[0], "welcome")
        self._advance(3.0)
        self.assertEqual(audio.spoken[-1], app.session.current_ask.pole.value)
        self.assertTrue(app.cast.pointing)
        app.render()

    def test_correct_make_moves_the_balloon_cheers_and_then_asks_the_opposite(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, _, audio = self._build_app()
        self._advance(3.0)
        first = app.session.current_ask.pole
        self.assertTrue(self._answer())
        self.assertEqual(app.scene.state, first)
        self._advance(0.9)
        self.assertEqual(app.cast.pose, CastPose.CHEER)
        self.assertIn("praise", audio.spoken)
        self.assertTrue(app.controls.caption.visible)
        self.assertEqual(app.controls.caption.text, app.resources.text(first.text_key))
        self._advance(2.5)
        self.assertIs(app.session.current_ask.pole, opposite(first))
        self.assertEqual(audio.spoken[-1], opposite(first).value)
        self.assertFalse(app.controls.caption.visible)

    def test_wrong_answer_thinks_demonstrates_and_allows_retry(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, _, audio = self._build_app()
        self._advance(3.0)
        asked = app.session.current_ask.pole
        self.assertTrue(self._answer(correct=False))
        self.assertEqual(app.cast.pose, CastPose.THINK)
        self.assertIn("retry", audio.spoken)
        self.assertIsNone(app.scene.state, "a wrong tap does not move the balloon")
        self.assertFalse(self._answer(), "input is locked during the demonstration")
        self._advance(1.5)
        self.assertEqual(audio.spoken[-1], asked.value, "the asked word is repeated with the demo")
        self._advance(3.0)
        self.assertTrue(self._answer())
        self.assertEqual(app.scene.state, asked)
        self.assertEqual(app.session.phase, Phase.SOLVED)

    def test_balloon_can_be_dragged_up(self) -> None:
        app, _, _ = self._build_app()
        self._advance(3.0)
        ask = app.session.current_ask
        handle = app.scene.drag_handle()
        target = (handle.centerx, handle.centery - 160 if ask.pole is Pole.UP else handle.centery + 200)
        self.assertTrue(app.drag(handle.center, target))
        self.assertEqual(app.scene.state, ask.pole)

    def test_keyboard_and_controller_reach_choices_and_listen(self) -> None:
        from greia_platform import pygame_input

        app, _, audio = self._build_app()
        self._advance(3.0)
        layer = app.controls.layer
        self.assertEqual(layer.focused_id, "choice.0")
        for _ in range(4):
            app.press(pygame.K_RIGHT)
        for _ in range(3):
            app.press(pygame.K_UP)
        self.assertEqual(layer.focused_id, "listen")
        app.press(pygame.K_SPACE)
        self.assertEqual(audio.spoken[-1], app.session.current_ask.pole.value)
        for _ in range(3):
            app.press(pygame.K_DOWN)
        self.assertTrue(layer.focused_id.startswith("choice."))
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertTrue(app.session.phase is Phase.SOLVED or "retry" in audio.spoken)
        if pygame_input.sdl_controller is not None and pygame_input._CONTROLLER_BUTTON_DOWN >= 0:
            self._advance(6.0)
            press = pygame_input._CONTROLLER_BUTTON_DOWN
            app._handle_event(pygame.event.Event(press, button=pygame_input.CONTROLLER_BUTTON_DPAD_DOWN))
            self.assertTrue(layer.focused_id.startswith("choice."))

    def test_idle_hint_points_and_glows_both_choices(self) -> None:
        app, _, audio = self._build_app()
        self._advance(3.0)
        spoken = len(audio.spoken)
        self._advance(6.5)
        self.assertTrue(app.cast.pointing)
        self.assertEqual(set(app.scene._halos), {0, 1}, "a hint never singles out the answer")
        self.assertEqual(len(audio.spoken), spoken, "first hint is silent")
        self._advance(6.5)
        self.assertEqual(audio.spoken[-1], app.session.current_ask.pole.value)

    def test_protected_chrome_region_is_ignored(self) -> None:
        app, _, _ = self._build_app()
        self._advance(3.0)
        self.assertFalse(app.tap((4, 4)))
        self.assertEqual(app.session.phase, Phase.ASKING)

    def test_targets_and_bar_stay_clear_of_chrome_and_inside_the_stage(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        app, _, _ = self._build_app(level=3)
        layout = ControlLayout.for_canvas(app.canvas, app.screen.get_size())
        for scene in app.scenes.values():
            for rect in scene.target_rects():
                self.assertFalse(layout.overlaps_chrome(rect))
                self.assertGreaterEqual(rect.left, 240)
                self.assertGreater(rect.top, app.controls.listen.rect.bottom)
            first, second = scene.target_rects()
            self.assertFalse(first.colliderect(second))
        for control in (app.controls.listen, app.controls.progress, app.controls.caption):
            self.assertFalse(layout.overlaps_chrome(control.rect))

    def test_every_scene_renders_each_moment(self) -> None:
        app, _, _ = self._build_app(level=3, seed=4)
        surface = pygame.Surface((1024, 600))
        for category, scene in app.scenes.items():
            poles = PAIR_POLES[category]
            round_ = _round(category, count=3)
            now = self._clock[0]
            scene.begin_round(round_, now)
            scene.present_ask(round_.asks[0], 0, now)
            scene.draw(surface, now)
            scene.perform(poles[0], now)
            scene.draw(surface, now + 0.3)
            scene.demonstrate(poles[1], now + 1.0)
            scene.draw(surface, now + 1.4)
            scene.pulse(now + 3.0)
            scene.draw(surface, now + 3.2)
            scene.present_ask(Ask(poles[0], (poles[1], poles[0])), 2, now + 4.0)
            scene.draw(surface, now + 4.3)

    def test_full_visit_plays_to_completion_and_restarts(self) -> None:
        from contrari_app import AppState

        app, events, audio = self._build_app(level=2, seed=5)
        pairs = len(app.session.rounds)
        self._advance(3.0)
        answered = 0
        while app.state is AppState.PLAYING and answered < 40:
            self.assertTrue(self._answer(), f"answer {answered} was not accepted")
            answered += 1
            self._advance(4.5)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(answered, pairs * 2)
        self.assertEqual(len(events.milestones), pairs)
        self.assertEqual(len(set(events.milestones)), pairs)
        self.assertEqual(len(events.completions), 1)
        self.assertIn("complete", audio.spoken)
        self.assertEqual(self._storage.saved["level"], 3, "a clean level-2 visit moves up")
        app.render()
        self.assertTrue(app.tap(app.completion.primary_rect.center))
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.session.level, 3)
        self.assertEqual(len(app.session.rounds[0].asks), 3)

    def test_level_three_visit_with_mistakes_completes(self) -> None:
        from contrari_app import AppState

        app, events, _ = self._build_app(level=3, seed=8)
        self._advance(3.0)
        steps = 0
        while app.state is AppState.PLAYING and steps < 80:
            steps += 1
            if app.session.ask_index == 0:
                self.assertTrue(self._answer(correct=False))
                self._advance(5.0)
            self.assertTrue(self._answer())
            self._advance(4.5)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.completions), 1)
        self.assertEqual(self._storage.saved["level"], 2, "retries in most pairs ease the next visit")


if __name__ == "__main__":
    unittest.main()
