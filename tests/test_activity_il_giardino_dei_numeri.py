"""Tests for Il Giardino dei Numeri (manifest, model, saves, app loop)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "il_giardino_dei_numeri"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import tomllib  # noqa: E402

from giardino_model import (  # noqa: E402
    MAX_STAGE,
    ROUNDS_PER_SESSION,
    STAGES,
    ChoiceResult,
    GardenProgress,
    GardenSession,
    ItemKind,
    Phase,
    RoundFactory,
    RoundSummary,
    TapResult,
    crate_rect,
    field_cells,
    well_position,
)
from giardino_services import (  # noqa: E402
    SCHEMA_VERSION,
    STORAGE_KEY,
    GreiaGardenProgress,
    progress_from_payload,
    progress_payload,
)


class _Storage:
    def __init__(self, value=None) -> None:
        self.values = {} if value is None else {STORAGE_KEY: value}

    def kv_get(self, key, default=None):
        return self.values.get(key, default)

    def kv_set(self, key, value) -> None:
        self.values[key] = json.loads(json.dumps(value))


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_the_first_numbers_rung(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        act = data["activity"]
        self.assertEqual(act["id"], "org.greia.il-giardino-dei-numeri")
        self.assertEqual(act["title_key"], "activity.il_giardino_dei_numeri.title")
        self.assertEqual(act["languages"], ["it", "en", "es", "fr"])  # four released languages (owner 2026-10-17)
        edu = data["education"]
        self.assertEqual((edu["recommended_age_min"], edu["recommended_age_max"]), (2, 5))
        self.assertEqual((edu["difficulty_min"], edu["difficulty_max"]), (1, MAX_STAGE))
        self.assertTrue(edu["adaptive_difficulty"])
        skills = {skill["id"] for skill in edu["skills"]}
        self.assertIn("math.counting.one_to_one", skills)
        self.assertIn("math.counting.cardinality", skills)
        self.assertNotIn("math.quantity.subitizing", skills)
        self.assertEqual(
            {event["id"]: event["kind"] for event in edu["events"]},
            {"garden.set_counted": "milestone", "garden.basket_filled": "completion"},
        )
        self.assertEqual(data["input"]["profile"], "hybrid")

    def test_locale_bundles_share_keys_and_cover_runtime_text(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"])
        for locale, strings in bundles.items():
            self.assertEqual(set(strings), keys, locale)
            self.assertTrue(all(value.strip() for value in strings.values()), locale)
        self.assertTrue({"victory.title", "button.play_again"} <= keys)

    def test_private_crate_art_has_source_and_rendition(self) -> None:
        for name in ("crate_back", "crate_front"):
            self.assertTrue((ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg").is_file())
            self.assertTrue((ACTIVITY_ROOT / "assets" / "runtime" / f"{name}.png").is_file())

    def test_objects_are_shared_library_art_not_emoji(self) -> None:
        from greia_platform.activity_api import get_shared_visual_path

        for kind in ItemKind:
            self.assertTrue(get_shared_visual_path(kind.asset_id).is_file(), kind)


class ModelTests(unittest.TestCase):
    def test_counting_is_one_to_one_and_ends_in_the_question(self) -> None:
        round_ = RoundFactory(random.Random(1)).build(2, count=3)
        self.assertEqual(round_.target, 3)
        self.assertIn(3, round_.choices)
        first = round_.tap_item(0)
        self.assertEqual((first.result, first.number, first.finished_counting), (TapResult.COUNTED, 1, False))
        self.assertEqual(round_.tap_item(0).result, TapResult.ALREADY_COUNTED)
        self.assertEqual(round_.counted, 1)
        round_.tap_item(1)
        last = round_.tap_item(2)
        self.assertTrue(last.finished_counting)
        self.assertEqual([item.order for item in round_.items], [1, 2, 3])
        round_.finish_counting()
        self.assertIs(round_.phase, Phase.ASKING)

    def test_stage_one_shows_cardinality_without_a_question(self) -> None:
        round_ = RoundFactory(random.Random(2)).build(1, count=2)
        self.assertEqual(round_.choices, ())
        for item in round_.items:
            round_.tap_item(item.item_id)
        round_.finish_counting()
        self.assertIs(round_.phase, Phase.CLOSING)

    def test_wrong_answer_demonstrates_then_allows_kind_retry(self) -> None:
        round_ = RoundFactory(random.Random(3)).build(3, count=4)
        for item in round_.items:
            round_.tap_item(item.item_id)
        round_.finish_counting()
        wrong = next(value for value in round_.choices if value != 4)
        self.assertIs(round_.choose(wrong), ChoiceResult.TRY_AGAIN)
        self.assertIs(round_.phase, Phase.DEMONSTRATING)
        self.assertIs(round_.choose(4), ChoiceResult.IGNORED)  # not during the demo
        round_.finish_demonstration()
        self.assertIs(round_.choose(wrong), ChoiceResult.IGNORED)  # rejected card stays out
        self.assertIs(round_.choose(4), ChoiceResult.CORRECT)
        self.assertFalse(round_.clean)

    def test_choices_are_close_distractors_inside_one_to_ten(self) -> None:
        factory = RoundFactory(random.Random(4))
        for stage, spec in STAGES.items():
            for _ in range(40):
                round_ = factory.build(stage)
                self.assertIn(round_.target, spec.counts)
                self.assertEqual(len(round_.choices), spec.choices)
                if round_.choices:
                    self.assertIn(round_.target, round_.choices)
                    self.assertEqual(len(set(round_.choices)), len(round_.choices))
                    self.assertTrue(all(1 <= value <= 10 for value in round_.choices))
                    self.assertTrue(all(abs(value - round_.target) <= 2 for value in round_.choices))

    def test_objects_never_overlap_dani_or_the_crate(self) -> None:
        factory = RoundFactory(random.Random(5))
        for stage, spec in STAGES.items():
            self.assertGreaterEqual(len(field_cells(spec.wells)), max(spec.counts))
            left, top, width, height = crate_rect(spec.wells)
            for _ in range(20):
                for item in factory.build(stage).items:
                    self.assertGreaterEqual(item.x, 230)
                    self.assertGreaterEqual(item.y, 230)
                    inside = left <= item.x <= left + width and top + 12 <= item.y <= top + height
                    self.assertFalse(inside, (stage, item))
        self.assertEqual(well_position(9, 10)[0], well_position(4, 10)[0])

    def test_adaptive_ladder_promotes_and_steps_back(self) -> None:
        progress = GardenProgress(stage=1)
        for _ in range(3):
            progress.record(RoundSummary(3, 1, True, 0))
        self.assertEqual(progress.stage, 2)
        progress.record(RoundSummary(3, 2, False, 1))
        progress.record(RoundSummary(4, 2, False, 2))
        self.assertEqual(progress.stage, 1)
        progress.stage = MAX_STAGE
        for _ in range(5):
            progress.record(RoundSummary(8, MAX_STAGE, True, 0))
        self.assertEqual(progress.stage, MAX_STAGE)

    def test_session_has_a_real_end(self) -> None:
        session = GardenSession(RoundFactory(random.Random(6)))
        for _ in range(ROUNDS_PER_SESSION):
            self.assertFalse(session.complete)
            session.finish_round()
            if not session.complete:
                session.next_round()
        self.assertTrue(session.complete)
        session.restart()
        self.assertEqual(session.completed_rounds, 0)


class SaveTests(unittest.TestCase):
    def test_schema_one_saves_migrate_without_losing_totals(self) -> None:
        legacy = {"total_counted": 41, "baskets_filled": 9, "highest_count": 5}
        storage = _Storage(legacy)
        progress = GreiaGardenProgress(storage).load()
        self.assertEqual((progress.total_counted, progress.baskets_filled, progress.highest_count), (41, 9, 5))
        self.assertEqual(progress.stage, 2)
        GreiaGardenProgress(storage).save(progress)
        saved = storage.values[STORAGE_KEY]
        self.assertEqual(saved["schema_version"], SCHEMA_VERSION)
        self.assertEqual(saved["total_counted"], 41)
        self.assertEqual(progress_from_payload(saved).stage, 2)

    def test_new_and_garbage_saves_are_safe(self) -> None:
        self.assertEqual(progress_from_payload({}).stage, 1)
        self.assertEqual(progress_from_payload("junk").stage, 1)
        bad = progress_from_payload({"schema_version": 2, "stage": 99, "total_counted": -5, "clean_streak": "x"})
        self.assertEqual((bad.stage, bad.total_counted, bad.clean_streak), (MAX_STAGE, 0, 0))
        payload = progress_payload(GardenProgress(stage=3, clean_streak=2, total_counted=12))
        self.assertEqual(progress_from_payload(payload).stage, 3)
        self.assertEqual(progress_from_payload(payload).clean_streak, 2)


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.played: list[str] = []

    def say(self, cue: str, then: str | None = None) -> None:
        self.spoken.append(cue)
        if then:
            self.spoken.append(then)

    def say_number(self, number: int, then: str | None = None) -> None:
        self.say(f"count_{number}", then)

    def has_speech(self, cue: str) -> bool:
        return False

    def play(self, name: str) -> None:
        self.played.append(name)

    def chime(self, number: int) -> None:
        self.played.append(f"chime_{number}")


class _Events:
    def __init__(self) -> None:
        self.counted: list[tuple] = []
        self.completed: list[tuple] = []

    def set_counted(self, session_id, index, summary) -> None:
        self.counted.append((session_id, index, summary))

    def basket_filled(self, session_id, rounds, stage) -> None:
        self.completed.append((session_id, rounds, stage))


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.screen = pygame.display.set_mode((1024, 600))

    def _app(self, stage: int = 1, size: tuple[int, int] = (1024, 600)):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from giardino_app import GiardinoApp

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = _Storage()
        app = GiardinoApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=GardenSession(RoundFactory(random.Random(11)), GardenProgress(stage=stage)),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_ROOT, requested_locale="en"),
            audio=_Audio(),
            progress=GreiaGardenProgress(storage),
            events=_Events(),
            rng=random.Random(12),
            clock=lambda: now[0],
        )
        return app, now, storage

    @staticmethod
    def _advance(app, now, seconds: float, step: float = 1 / 30) -> None:
        for _ in range(int(seconds / step)):
            now[0] += step
            app.step()

    def _tap_logical(self, app, x: float, y: float) -> bool:
        return app.tap(app.canvas.mapper.point(x, y))

    def _count_all(self, app, now) -> None:
        for item in app.session.current.items:
            self.assertTrue(self._tap_logical(app, item.x, item.y))
            self._advance(app, now, 0.2)
        self._advance(app, now, 1.3)

    def _answer(self, app, value: int) -> bool:
        for index, button in enumerate(app.controls.choices):
            if app.controls.choice_value(index) == value:
                return self._tap_logical(app, *button.rect.center)
        return False

    def test_plays_a_whole_visit_to_the_completion_scene(self) -> None:
        from giardino_app import AppState

        app, now, storage = self._app(stage=2)
        self._advance(app, now, 1.0)
        self.assertEqual(app.audio.spoken[0], "intro")
        for round_index in range(ROUNDS_PER_SESSION):
            current = app.session.current
            self._count_all(app, now)
            if current.choices:
                self.assertIs(current.phase, Phase.ASKING)
                self.assertTrue(self._answer(app, current.target))
            self._advance(app, now, 0.3 * current.target + 3.5)
            self.assertEqual(app.session.completed_rounds, round_index + 1)
            self.assertIn(f"count_{current.target}", app.audio.spoken)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertEqual(len(app.events.counted), ROUNDS_PER_SESSION)
        self.assertEqual(len(app.events.completed), 1)
        self.assertEqual(app.audio.spoken[-1], "basket_full")
        saved = storage.values[STORAGE_KEY]
        self.assertEqual(saved["baskets_filled"], ROUNDS_PER_SESSION)
        self.assertEqual(saved["sessions_completed"], 1)
        app.render()
        # Replay from the completion scene starts a fresh visit.
        self.assertTrue(self._tap_logical(app, *app.completion.primary_rect.center))
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.session.completed_rounds, 0)

    def test_wrong_answer_gets_think_pose_and_voiced_recount(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, now, _ = self._app(stage=3)
        self._advance(app, now, 0.8)
        current = app.session.current
        self._count_all(app, now)
        app.audio.spoken.clear()
        wrong = next(value for value in current.choices if value != current.target)
        self.assertTrue(self._answer(app, wrong))
        self.assertIs(app.cast.feedback.pose, CastPose.THINK)
        self.assertEqual(app.audio.spoken[0], "retry")
        self._advance(app, now, 1.4 + 0.62 * current.target + 0.5)
        self.assertEqual(app.audio.spoken[1:], [f"count_{n}" for n in range(1, current.target + 1)])
        self.assertIs(current.phase, Phase.ASKING)
        self.assertFalse(self._answer(app, wrong))  # rejected card is disabled
        self.assertTrue(self._answer(app, current.target))
        self.assertIs(app.cast.feedback.pose, CastPose.IDLE)
        self._advance(app, now, 0.3 * current.target + 0.6)
        self.assertIs(app.cast.feedback.pose, CastPose.CHEER)

    def test_keyboard_alone_counts_and_answers(self) -> None:
        app, now, _ = self._app(stage=2)
        current = app.session.current
        for _ in range(current.target):
            self.assertTrue(app.press(pygame.K_SPACE))
            self._advance(app, now, 0.2)
        self.assertEqual(current.counted, current.target)
        self._advance(app, now, 1.3)
        self.assertIs(current.phase, Phase.ASKING)
        layer = app.controls.layer
        for _ in range(len(current.choices)):
            if app.controls.choice_value(int(layer.focused_id.split(".")[1])) == current.target:
                break
            app.press(pygame.K_RIGHT)
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertIs(current.phase, Phase.CLOSING)

    def test_idle_hint_points_and_pulses_without_revealing(self) -> None:
        app, now, _ = self._app(stage=1)
        self._advance(app, now, 2.5)
        self.assertFalse(app.cast.pointing)
        self._advance(app, now, 3.7)
        current = app.session.current
        self.assertTrue(app.cast.pointing)
        self.assertEqual(current.hints, 1)
        self.assertIn(current.next_uncounted().item_id, app.motion.pops)

    def test_grass_tap_is_a_soft_miss_and_home_region_is_protected(self) -> None:
        app, now, _ = self._app(stage=1)
        self._advance(app, now, 0.5)
        self.assertFalse(self._tap_logical(app, 420, 520))
        self.assertIn("ripple", app.audio.played)
        self.assertEqual(app.session.current.counted, 0)
        self.assertFalse(app.tap((5, 5)))

    def test_small_screens_render_every_state(self) -> None:
        for size in ((800, 480), (480, 320)):
            app, now, _ = self._app(stage=4, size=size)
            self._advance(app, now, 0.6)
            app.render()
            self._count_all(app, now)
            app.render()
            self.assertIs(app.session.current.phase, Phase.ASKING)
            from greia_platform.activity_controls import ControlLayout

            protected = ControlLayout.for_canvas(app.canvas, size).protected
            for control in (app.controls.listen, app.controls.progress, *app.controls.choices):
                self.assertFalse(control.rect.colliderect(protected), (size, control.control_id))


if __name__ == "__main__":
    unittest.main()
