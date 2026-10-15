"""Contract and app-loop tests for Stelle Incantate (org.greia.stelle-incantate).

Source/interaction tests with a dummy SDL display and a fake clock; they do not
claim VM or physical-hardware behaviour.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import random
import re
import tomllib
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from activities.stelle_incantate.sky_content import (  # noqa: E402
    ALL_FIGURES,
    CARD_CENTER,
    CARD_SIZE,
    FIGURES_BY_ID,
    LEO_HEIGHT,
    LEO_MIDBOTTOM,
    MEDIUM,
    MIN_STAR_SPACING,
    SKY_SIZE,
    SMALL,
    STAR_TARGET,
    STORAGE_KEY,
    TEEN,
    sky_point,
)
from activities.stelle_incantate.sky_model import (  # noqa: E402
    FIGURES_PER_NIGHT,
    MAX_STAGE,
    STAGES,
    ChoiceResult,
    Night,
    Phase,
    RoundFactory,
    SkyProgress,
    TapResult,
    TaskKind,
)
from activities.stelle_incantate.sky_services import (  # noqa: E402
    SCHEMA_VERSION,
    GreiaSkyEvents,
    GreiaSkyProgress,
    progress_from_payload,
    progress_payload,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "activities" / "stelle_incantate"
LOCALES = ("en", "it", "es", "fr")
FORBIDDEN_SVG = re.compile(
    r'<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script|foreignObject|<animate|'
    r'blend-mode|skew|href="[^#]|sodipodi|inkscape:'
)


class _Storage:
    def __init__(self, value=None) -> None:
        self.values = {} if value is None else {STORAGE_KEY: value}

    def kv_get(self, key, default=None):
        return self.values.get(key, default)

    def kv_set(self, key, value) -> None:
        self.values[key] = json.loads(json.dumps(value))


def _round(stage: int, seed: int = 1):
    return RoundFactory(random.Random(seed)).build(stage)


def _finish(round_) -> None:
    while round_.phase is not Phase.REVEALED:
        index = round_.next_index
        if round_.tap(index) is TapResult.ASK:
            round_.choose(round_.numbers[index])


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_numbers_rung(self) -> None:
        manifest = tomllib.loads((PACKAGE / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.stelle-incantate")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        education = manifest["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 6))
        self.assertEqual(education["difficulty_max"], MAX_STAGE)
        skills = {skill["id"] for skill in education["skills"]}
        self.assertTrue({"math.number_order", "math.counting.count_on", "math.counting.count_back"} <= skills)
        self.assertNotIn("cognitive.shape_completion", skills)
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertEqual(manifest["presentation"]["categories"][0], "learn")
        self.assertEqual(manifest["storage"]["schema_version"], 1)  # payload versions itself

    def test_four_locales_share_keys_and_name_every_figure(self) -> None:
        bundles = {
            locale: json.loads((PACKAGE / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in LOCALES
        }
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(bundle["strings"]), keys)
                for figure in ALL_FIGURES:
                    self.assertTrue(bundle["strings"][figure.name_key].strip())
                    if figure.real:
                        self.assertTrue(bundle["strings"][figure.fact_key].strip())
                for key in ("victory.title", "victory.subtitle", "button.play_again"):
                    self.assertTrue(bundle["strings"][key].strip())
        self.assertEqual(bundles["es"]["audio"], {})
        self.assertEqual(bundles["fr"]["audio"], {})

    def test_real_constellation_facts_keep_their_voice_in_en_and_it(self) -> None:
        for locale in ("en", "it"):
            audio = json.loads((PACKAGE / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["audio"]
            for figure in ALL_FIGURES:
                if not figure.real:
                    continue
                with self.subTest(locale=locale, figure=figure.figure_id):
                    relative = audio[figure.fact_key]["path"]
                    self.assertNotIn("..", relative)
                    self.assertIn(f"/{locale}/", relative)
                    self.assertTrue((PACKAGE / relative).is_file(), relative)


class FigureCatalogueTests(unittest.TestCase):
    def test_pools_have_the_stage_sizes(self) -> None:
        self.assertTrue(all(FIGURES_BY_ID[f].star_count == 5 for f in SMALL))
        self.assertTrue(all(7 <= FIGURES_BY_ID[f].star_count <= 10 for f in MEDIUM))
        self.assertTrue(all(FIGURES_BY_ID[f].star_count == 11 for f in TEEN))
        self.assertEqual(max(FIGURES_BY_ID[f].star_count for f in MEDIUM), 10)
        self.assertEqual({f.figure_id for f in ALL_FIGURES}, set(SMALL + MEDIUM + TEEN))

    def test_every_figure_is_one_unambiguous_counting_path(self) -> None:
        for figure in ALL_FIGURES:
            with self.subTest(figure=figure.figure_id):
                for index in range(1, figure.star_count):
                    self.assertTrue(
                        any(index in edge and min(edge) < index for edge in figure.edges),
                        "each new star links to an already lit one",
                    )
                for a, b in figure.edges:
                    self.assertNotEqual(a, b)
                    self.assertLess(max(a, b), figure.star_count)

    def test_stars_are_tappable_and_clear_of_leo_cards_and_moon(self) -> None:
        leo = pygame.Rect(0, 0, 190, LEO_HEIGHT)
        leo.midbottom = LEO_MIDBOTTOM
        cards_top = CARD_CENTER[1] - CARD_SIZE[1] // 2
        half = STAR_TARGET // 2
        for figure in ALL_FIGURES:
            with self.subTest(figure=figure.figure_id):
                for i, a in enumerate(figure.stars):
                    for b in figure.stars[i + 1:]:
                        self.assertGreaterEqual(math.dist(a, b), MIN_STAR_SPACING)
                    x, y = sky_point(a)
                    target = pygame.Rect(x - half, y - half, STAR_TARGET, STAR_TARGET)
                    self.assertFalse(target.colliderect(leo))
                    self.assertLess(target.bottom - 8, cards_top)
                    self.assertGreaterEqual(target.top, 76)  # below the top bar
                    self.assertFalse(x > 800 and y < 200, "the moon corner stays calm")

    def test_every_figure_has_lint_clean_svg_and_matching_picture(self) -> None:
        for figure in ALL_FIGURES:
            with self.subTest(figure=figure.figure_id):
                svg = (PACKAGE / "assets" / "source" / "figures" / f"{figure.figure_id}.svg").read_text()
                self.assertIsNone(FORBIDDEN_SVG.search(svg))
                self.assertIn(f'viewBox="0 0 {SKY_SIZE[0]} {SKY_SIZE[1]}"', svg)
                self.assertLessEqual(len(svg.encode()), 6 * 1024)
                self.assertLessEqual(svg.count("<path"), 50)
                picture = pygame.image.load(str(PACKAGE / "assets" / "runtime" / "figures" / figure.picture))
                self.assertEqual(picture.get_size(), SKY_SIZE)


class ModelTests(unittest.TestCase):
    def test_order_stage_counts_from_one_and_nothing_is_given(self) -> None:
        round_ = _round(1)
        self.assertIs(round_.task, TaskKind.ORDER)
        self.assertEqual(round_.numbers, tuple(range(1, round_.star_count + 1)))
        self.assertIsNone(round_.given)
        self.assertEqual(round_.lit_count, 0)
        self.assertIs(round_.tap(2), TapResult.WRONG)
        self.assertEqual((round_.mistakes, round_.step_mistakes), (1, 1))
        self.assertIs(round_.tap(0), TapResult.LIT)
        self.assertEqual(round_.step_mistakes, 0)
        self.assertIs(round_.tap(0), TapResult.AGAIN)  # a lit star is never a mistake
        self.assertEqual(round_.mistakes, 1)
        _finish(round_)
        self.assertTrue(round_.complete)
        self.assertEqual(round_.lit_edges(), round_.figure.edges)
        self.assertIs(round_.tap(0), TapResult.IGNORED)

    def test_count_on_gives_the_first_star_and_stays_within_ten(self) -> None:
        for seed in range(30):
            round_ = _round(3, seed)
            self.assertIs(round_.task, TaskKind.COUNT_ON)
            self.assertEqual(round_.given, 0)
            self.assertTrue(round_.is_lit(0))
            self.assertGreaterEqual(round_.numbers[0], 3)
            self.assertLessEqual(round_.numbers[-1], 10)
            self.assertEqual(round_.next_number, round_.numbers[0] + 1)

    def test_count_back_runs_down_to_one(self) -> None:
        round_ = _round(4)
        self.assertTrue(round_.descending)
        self.assertEqual(round_.numbers, tuple(range(round_.star_count, 0, -1)))
        self.assertTrue(round_.is_lit(0))
        self.assertEqual(round_.next_number, round_.star_count - 1)

    def test_teens_continue_from_ten_to_twenty(self) -> None:
        round_ = _round(6)
        self.assertEqual(round_.numbers, tuple(range(10, 21)))
        self.assertTrue(round_.is_lit(0))

    def test_missing_number_asks_at_its_turn_and_rejects_wrong_cards(self) -> None:
        for seed in range(25):
            round_ = _round(5, seed)
            blank = round_.blank
            self.assertIsNotNone(blank)
            self.assertTrue(3 <= blank <= round_.star_count - 2)
            answer = round_.numbers[blank]
            self.assertIn(answer, round_.choices)
            self.assertEqual(len(set(round_.choices)), 3)
            self.assertTrue(all(value >= 1 for value in round_.choices))
            self.assertIsNone(round_.label(blank))
        round_ = _round(5, 4)
        blank = round_.blank
        self.assertIs(round_.tap(blank), TapResult.WRONG)  # not its turn yet
        for index in range(blank):
            self.assertIs(round_.tap(index), TapResult.LIT)
        self.assertIs(round_.tap(blank), TapResult.ASK)
        self.assertIs(round_.phase, Phase.CHOOSING)
        self.assertIs(round_.tap(blank + 1), TapResult.IGNORED)
        wrong = next(value for value in round_.choices if value != round_.numbers[blank])
        self.assertIs(round_.choose(wrong), ChoiceResult.WRONG)
        self.assertIs(round_.choose(wrong), ChoiceResult.IGNORED)
        self.assertIs(round_.choose(round_.numbers[blank]), ChoiceResult.CORRECT)
        self.assertEqual(round_.label(blank), round_.numbers[blank])
        self.assertTrue(round_.is_lit(blank))

    def test_answer_is_not_always_the_middle_card(self) -> None:
        middles = set()
        for seed in range(60):
            round_ = _round(5, seed)
            middles.add(sorted(round_.choices)[1] == round_.numbers[round_.blank])
        self.assertEqual(middles, {True, False})

    def test_night_has_four_different_figures_and_adapts(self) -> None:
        night = Night(RoundFactory(random.Random(3)), SkyProgress(stage=1))
        seen = []
        for _ in range(FIGURES_PER_NIGHT):
            seen.append(night.round.figure.figure_id)
            _finish(night.round)
            night.finish_figure()
            if not night.complete:
                night.next_figure()
        self.assertTrue(night.complete)
        self.assertEqual(len(set(seen)), FIGURES_PER_NIGHT)
        self.assertEqual(night.progress.nights_completed, 1)
        self.assertGreater(night.stage, 1)  # clean figures climb
        self.assertEqual(night.progress.revealed, set(seen))

        night = Night(RoundFactory(random.Random(3)), SkyProgress(stage=4))
        for _ in range(2):
            round_ = night.round
            for _ in range(3):
                wrong = next(i for i in range(round_.star_count) if i != round_.next_index and not round_.is_lit(i))
                round_.tap(wrong)
            _finish(round_)
            night.finish_figure()
            night.next_figure()
        self.assertEqual(night.stage, 3)  # two struggling figures step back

    def test_every_stage_builds_a_valid_round(self) -> None:
        for stage, spec in STAGES.items():
            for seed in range(10):
                round_ = _round(stage, seed)
                self.assertIn(round_.figure.figure_id, spec.pool)
                self.assertEqual(len(round_.numbers), round_.star_count)
                self.assertTrue(all(1 <= number <= 20 for number in round_.numbers))


class SaveTests(unittest.TestCase):
    def test_first_release_string_save_migrates_forward(self) -> None:
        legacy = json.dumps({"completed_ids": ["triangolo", "cassiopea", "cigno", "carro", "junk"]})
        progress = GreiaSkyProgress(_Storage(legacy)).load()
        self.assertEqual(progress.stage, 2)
        self.assertEqual(progress.revealed, {"cassiopea", "cigno", "carro"})
        self.assertEqual(progress_from_payload({"completed_ids": ["triangolo"]}).stage, 1)

    def test_round_trip_is_bounded_and_garbage_is_safe(self) -> None:
        storage = _Storage()
        adapter = GreiaSkyProgress(storage)
        adapter.save(SkyProgress(stage=99, clean_streak=7, figures_completed=-4, revealed={"leone", "nope"}))
        payload = storage.values[STORAGE_KEY]
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["stage"], MAX_STAGE)
        self.assertEqual(payload["clean_streak"], 3)
        self.assertEqual(payload["figures_completed"], 0)
        self.assertEqual(payload["completed_ids"], ["leone"])
        loaded = adapter.load()
        self.assertEqual((loaded.stage, loaded.revealed), (MAX_STAGE, {"leone"}))
        for junk in ("not json", 7, None, ["x"], {"schema_version": 2, "stage": "high"}):
            self.assertEqual(progress_from_payload(junk).stage, 1)
        self.assertEqual(progress_payload(SkyProgress())["completed_ids"], [])

    def test_storage_failures_never_reach_the_game(self) -> None:
        class Broken:
            def kv_get(self, *args):
                raise RuntimeError("down")

            def kv_set(self, *args):
                raise RuntimeError("down")

        adapter = GreiaSkyProgress(Broken())
        self.assertEqual(adapter.load().stage, 1)
        adapter.save(SkyProgress())

    def test_events_are_scoped_per_night(self) -> None:
        from unittest.mock import patch

        with patch("activities.stelle_incantate.sky_services.emit_activity_event") as emit:
            events = GreiaSkyEvents()
            night = Night(RoundFactory(random.Random(1)))
            _finish(night.round)
            summary = night.finish_figure()
            events.constellation_completed("a", 1, summary)
            events.constellation_completed("b", 1, summary)
            events.fact_opened("a", "leone")
        keys = [call.kwargs["idempotency_key"] for call in emit.call_args_list]
        self.assertEqual(len(set(keys)), 3)
        self.assertEqual(emit.call_args_list[0].args[0], "constellation.completed")
        self.assertEqual(emit.call_args_list[2].args[0], "curiosity.fact_opened")


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.played: list[str] = []
        self.voices: list[str] = []

    def say(self, cue: str) -> None:
        self.spoken.append(cue)

    def say_number(self, number: int) -> None:
        self.spoken.append(f"count_{number}")

    def has_speech(self, cue: str) -> bool:
        return False

    def play(self, name: str) -> None:
        self.played.append(name)

    def chime(self, number: int) -> None:
        self.played.append(f"chime_{number}")

    def prepare_numbers(self, numbers) -> None:
        return None

    def play_voice(self, path) -> bool:
        self.voices.append(str(path))
        return True


class _Events:
    def __init__(self) -> None:
        self.figures: list[tuple] = []
        self.facts: list[tuple] = []

    def constellation_completed(self, night_id, index, summary) -> None:
        self.figures.append((night_id, index, summary))

    def fact_opened(self, night_id, figure_id) -> None:
        self.facts.append((night_id, figure_id))


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def _app(self, stage: int = 1, size: tuple[int, int] = (1024, 600), seed: int = 11, locale: str = "en"):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography

        from activities.stelle_incantate.sky_app import SkyActivity

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = _Storage()
        app = SkyActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            night=Night(RoundFactory(random.Random(seed)), SkyProgress(stage=stage)),
            typography=GreiaTypography(),
            resources=activity_resources(PACKAGE, requested_locale=locale),
            audio=_Audio(),
            progress=GreiaSkyProgress(storage),
            events=_Events(),
            clock=lambda: now[0],
        )
        return app, now, storage

    @staticmethod
    def _advance(app, now, seconds: float, step: float = 1 / 30) -> None:
        for _ in range(int(seconds / step)):
            now[0] += step
            app.step()

    @staticmethod
    def _tap_logical(app, point) -> bool:
        return app.tap(app.canvas.mapper.point(*point))

    def _tap_star(self, app, index: int) -> bool:
        return self._tap_logical(app, sky_point(app.round.figure.stars[index]))

    def _solve(self, app, now) -> None:
        round_ = app.round
        while round_.phase is not Phase.REVEALED:
            index = round_.next_index
            self.assertTrue(self._tap_star(app, index))
            if round_.phase is Phase.CHOOSING:
                self._advance(app, now, 0.2)
                card = round_.choices.index(round_.numbers[index])
                self.assertTrue(self._tap_logical(app, app.controls.cards[card].rect.center))
            self._advance(app, now, 0.2)
        self._advance(app, now, 0.6)

    def test_plays_a_whole_night_to_the_completion_scene(self) -> None:
        from activities.stelle_incantate.sky_app import AppState

        app, now, storage = self._app(stage=1)
        for figure in range(FIGURES_PER_NIGHT):
            self._advance(app, now, 1.5)
            round_ = app.round
            self.assertFalse(app.controls.next.visible)
            self._solve(app, now)
            self.assertIsNotNone(app.motion.reveal_started)
            self.assertTrue(app.controls.next.visible)
            self.assertIn(app.audio.spoken[-1], ("praise", "celebrate"))
            self.assertEqual(app.band.name, app.resources.text(round_.figure.name_key))
            self.assertIn(f"chime_{round_.numbers[-1]}", app.audio.played)
            app.render()
            self.assertTrue(self._tap_logical(app, app.controls.next.rect.center))
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertEqual(len(app.events.figures), FIGURES_PER_NIGHT)
        self.assertEqual(storage.values[STORAGE_KEY]["figures_completed"], FIGURES_PER_NIGHT)
        self.assertEqual(storage.values[STORAGE_KEY]["nights_completed"], 1)
        app.render()
        self.assertTrue(app.press(pygame.K_RETURN))  # replay from the completion scene
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.night.completed, 0)

    def test_focus_never_jumps_to_the_next_star(self) -> None:
        from activities.stelle_incantate.sky_controls import star_id

        app, now, _ = self._app(stage=2)
        self._advance(app, now, 2.0)
        round_ = app.round
        self.assertEqual(app.controls.layer.focused_id, "goal.replay")
        self.assertTrue(self._tap_star(app, 0))
        self.assertEqual(app.controls.layer.focused_id, star_id(0))
        self.assertTrue(app.press(pygame.K_RETURN))  # re-activating a lit star is harmless
        self.assertEqual((round_.lit_count, round_.mistakes), (1, 0))
        self.assertNotEqual(app.controls.layer.focused_id, star_id(round_.next_index))

    def test_keyboard_alone_lights_a_figure_by_spatial_navigation(self) -> None:
        from activities.stelle_incantate.sky_controls import star_id

        app, now, _ = self._app(stage=1, seed=5)
        self._advance(app, now, 2.0)
        round_ = app.round
        layer = app.controls.layer
        for _ in range(round_.star_count):
            goal = round_.next_index
            target = pygame.Rect(layer.target(star_id(goal)).rect)
            for _ in range(20):
                if layer.focused_id == star_id(goal):
                    break
                current = pygame.Rect(layer.target(layer.focused_id).rect)
                dx, dy = target.centerx - current.centerx, target.centery - current.centery
                if abs(dx) >= abs(dy):
                    key = pygame.K_RIGHT if dx > 0 else pygame.K_LEFT
                else:
                    key = pygame.K_DOWN if dy > 0 else pygame.K_UP
                before = layer.focused_id
                app.press(key)
                if layer.focused_id == before:  # blocked: try the other axis
                    alt = (pygame.K_DOWN if dy > 0 else pygame.K_UP) if abs(dx) >= abs(dy) else (
                        pygame.K_RIGHT if dx > 0 else pygame.K_LEFT)
                    app.press(alt)
            self.assertEqual(layer.focused_id, star_id(goal))
            self.assertTrue(app.press(pygame.K_SPACE))
            self._advance(app, now, 0.2)
        self._advance(app, now, 0.6)
        self.assertIs(round_.phase, Phase.REVEALED)
        self.assertEqual(round_.mistakes, 0)
        self.assertEqual(layer.focused_id, "next")
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertEqual(app.night.completed, 1)

    def test_mistakes_get_think_then_anchor_then_demonstration(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, now, _ = self._app(stage=2)
        self._advance(app, now, 2.0)
        round_ = app.round
        self.assertTrue(self._tap_star(app, 0))
        self.assertTrue(self._tap_star(app, 1))
        wrong = round_.star_count - 1
        self.assertTrue(self._tap_star(app, wrong))
        self.assertIs(app.cast.feedback.pose, CastPose.THINK)
        self.assertEqual(app.motion.wobble[0], wrong)
        self.assertEqual(app.audio.spoken.count("retry"), 1)
        self._advance(app, now, 0.7)
        self.assertIn(1, app.motion.pulses)  # the last lit star shows where we are
        self.assertIsNone(app.motion.trail)
        self.assertTrue(self._tap_star(app, wrong))
        self.assertEqual(app.audio.spoken.count("retry"), 1)  # said once per figure
        self.assertEqual(app.motion.trail[:2], (1, 2))
        self.assertTrue(round_.demonstrated)
        app.render()
        self.assertTrue(self._tap_star(app, 2))
        self.assertIsNone(app.motion.trail)

    def test_idle_hints_are_graduated_and_do_not_count_as_struggle(self) -> None:
        app, now, _ = self._app(stage=2)
        self._advance(app, now, 2.0)
        round_ = app.round
        self.assertTrue(self._tap_star(app, 0))
        self._advance(app, now, 5.0)
        self.assertFalse(app.motion.pulses)
        self._advance(app, now, 1.3)
        self.assertEqual(round_.hints, 1)
        self.assertTrue(app.cast.pointing)
        self.assertIn(0, app.motion.pulses)  # first: where we are
        self.assertIsNone(app.motion.trail)
        self._advance(app, now, 6.2)
        self.assertEqual(round_.hints, 2)
        self.assertEqual(app.motion.trail[:2], (0, 1))  # then: the way
        self.assertFalse(round_.demonstrated)

    def test_missing_number_cards_through_the_app(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, now, _ = self._app(stage=5, seed=8)
        self._advance(app, now, 2.0)
        round_ = app.round
        blank = round_.blank
        for index in range(blank):
            self.assertTrue(self._tap_star(app, index))
        self.assertFalse(any(card.visible for card in app.controls.cards))
        self.assertTrue(self._tap_star(app, blank))
        self.assertTrue(all(card.visible for card in app.controls.cards))
        self.assertTrue(app.controls.layer.focused_id.startswith("card."))
        wrong = next(i for i, value in enumerate(round_.choices) if value != round_.numbers[blank])
        self.assertTrue(self._tap_logical(app, app.controls.cards[wrong].rect.center))
        self.assertIs(app.cast.feedback.pose, CastPose.THINK)
        self.assertFalse(app.controls.cards[wrong].enabled)
        app.render()
        right = round_.choices.index(round_.numbers[blank])
        self.assertTrue(self._tap_logical(app, app.controls.cards[right].rect.center))
        self.assertIs(app.cast.feedback.pose, CastPose.CHEER)
        self.assertTrue(round_.is_lit(blank))
        self.assertFalse(any(card.visible for card in app.controls.cards))

    def test_fact_is_voiced_for_real_constellations_only(self) -> None:
        app, now, _ = self._app(stage=1, seed=2)
        voiced = 0
        for _ in range(FIGURES_PER_NIGHT):
            self._advance(app, now, 1.5)
            figure = app.round.figure
            self._solve(app, now)
            self.assertEqual(app.controls.fact.visible, figure.real)
            if figure.real:
                self.assertTrue(self._tap_logical(app, app.controls.fact.rect.center))
                self.assertTrue(self._tap_logical(app, app.controls.fact.rect.center))
                self.assertTrue(app.audio.voices[-1].endswith(".ogg"))
                self.assertEqual(app.band.fact, app.resources.text(figure.fact_key))
                voiced += 1
                app.render()
            self.assertTrue(self._tap_logical(app, app.controls.next.rect.center))
        self.assertGreater(voiced, 0)
        self.assertEqual(len(app.events.facts), voiced)  # once per figure

    def test_home_region_is_protected_and_small_screens_render(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320)):
            for stage in (1, 5, 6):
                app, now, _ = self._app(stage=stage, size=size, locale="it")
                self.assertFalse(app.tap((5, 5)))
                self._advance(app, now, 1.5)
                self._solve(app, now)
                app.render()
                protected = ControlLayout.for_canvas(app.canvas, size).protected
                for target in app.controls.layer.targets:
                    self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))

    def test_old_save_is_loaded_by_the_composition_root_adapter(self) -> None:
        legacy = json.dumps({"completed_ids": ["cassiopea", "cigno", "carro", "leone"]})
        progress = GreiaSkyProgress(_Storage(legacy)).load()
        night = Night(RoundFactory(random.Random(1)), progress)
        self.assertEqual(night.stage, 2)
        self.assertIn(night.round.figure.figure_id, MEDIUM)


if __name__ == "__main__":
    unittest.main()
