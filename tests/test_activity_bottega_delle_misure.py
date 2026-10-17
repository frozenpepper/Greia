"""Tests for La Bottega delle Misure (manifest, model, saves, app loop)."""

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
ACTIVITY_ROOT = ROOT / "activities" / "bottega_delle_misure"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import tomllib  # noqa: E402

from measure_content import BOARD_UNITS, COMPARE_ROWS, MEASURE_ROW, UNIT, twin_rows  # noqa: E402
from measure_model import (  # noqa: E402
    JOBS_PER_DELIVERY,
    MAX_STAGE,
    STAGES,
    Answer,
    Delivery,
    Goal,
    JobSummary,
    Phase,
    RowFit,
    TaskFactory,
    TaskKind,
    WorkshopProgress,
)
from measure_services import (  # noqa: E402
    SCHEMA_VERSION,
    STORAGE_KEY,
    GreiaMeasureProgress,
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


def _job(stage: int, kind: TaskKind, goal: Goal = Goal.MORE, seed: int = 1):
    task = TaskFactory(random.Random(seed)).build(stage, kind=kind, goal=goal)
    task.arrived()
    return task


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_the_measurement_rung(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        act = data["activity"]
        self.assertEqual(act["id"], "org.greia.bottega-delle-misure")
        self.assertEqual(act["languages"], ["it", "en", "es", "fr"])  # four released languages (owner 2026-10-17)
        edu = data["education"]
        self.assertEqual((edu["recommended_age_min"], edu["recommended_age_max"]), (5, 7))
        self.assertEqual((edu["difficulty_min"], edu["difficulty_max"]), (1, MAX_STAGE))
        self.assertTrue(edu["adaptive_difficulty"])
        skills = {skill["id"] for skill in edu["skills"]}
        self.assertTrue(
            {"math.measurement.non_standard_units", "math.comparison.length_height", "math.comparison.weight"} <= skills
        )
        self.assertNotIn("math.ordering.seriation", skills)  # no ordering jobs any more
        self.assertEqual(
            {event["id"]: event["kind"] for event in edu["events"]},
            {"measure.parcel_completed": "milestone", "measure.delivery_completed": "completion"},
        )
        self.assertEqual(data["input"]["profile"], "hybrid")
        self.assertEqual(data["storage"]["schema_version"], 1)  # the payload migrates itself

    def test_locale_bundles_share_keys_without_emoji_or_dormant_copy(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"])
        self.assertTrue({"victory.title", "button.play_again", "prompt.measure"} <= keys)
        self.assertFalse({key for key in keys if key.startswith(("goal.", "hud.", "prompt.order", "prompt.shelf"))})
        for locale, strings in bundles.items():
            self.assertEqual(set(strings), keys, locale)
            for value in strings.values():
                self.assertTrue(value.strip())
                self.assertTrue(all(ord(ch) < 0x2190 for ch in value), (locale, value))

    def test_every_spoken_prompt_is_a_recorded_clip(self) -> None:
        from measure_app import prompt_cue

        recorded = {path.stem for path in (ACTIVITY_ROOT / "assets" / "audio" / "en").glob("*.wav")}
        for stage in STAGES:
            for kind in TaskKind:
                for goal in Goal:
                    task = _job(stage, kind, goal)
                    cue = prompt_cue(task)
                    if kind is TaskKind.WEIGH:
                        self.assertIsNone(cue)  # pictorial until a line is recorded
                    else:
                        self.assertIn(cue, recorded)

    def test_private_art_has_source_and_rendition_and_no_cast_redraw(self) -> None:
        names = (
            "bench",
            "board",
            "shelf",
            "stop",
            "crate",
            "unit_block",
            "sign",
            "balance_stand",
            "balance_beam",
            "balance_pan",
        )
        for name in names:
            self.assertTrue((ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg").is_file(), name)
            self.assertTrue((ACTIVITY_ROOT / "assets" / "runtime" / f"{name}.png").is_file(), name)
        leftovers = {path.stem for path in (ACTIVITY_ROOT / "assets" / "runtime").glob("*.png")} - set(names)
        self.assertEqual(leftovers, set())  # no private Dani redraws
        lint = ("<image", "data:", "<text", "<filter", "<mask", "<style", "<script", "#000000")
        for svg in (ACTIVITY_ROOT / "assets" / "source").glob("*.svg"):
            source = svg.read_text(encoding="utf-8")
            self.assertFalse([token for token in lint if token in source], svg.name)


class GeometryTests(unittest.TestCase):
    def test_blocks_and_parcels_share_the_start_line_and_unit(self) -> None:
        for row in (MEASURE_ROW, *COMPARE_ROWS, *twin_rows(0), *twin_rows(1)):
            self.assertEqual(row.block_rect(0)[0], row.stop_x)
            self.assertEqual(row.parcel_rect(4, 60)[0], row.stop_x)
            self.assertEqual(row.parcel_rect(4, 60)[2], 4 * UNIT)
            self.assertEqual(row.block_rect(3)[0] + UNIT, row.stop_x + 4 * UNIT)
            board_x, _, board_w, _ = row.board_rect
            self.assertLessEqual(row.block_rect(BOARD_UNITS - 1)[0] + UNIT, board_x + board_w)

    def test_twin_boards_start_in_different_places(self) -> None:
        for stagger in (0, 1):
            first, second = twin_rows(stagger)
            self.assertNotEqual(first.stop_x, second.stop_x)
        self.assertEqual(COMPARE_ROWS[0].stop_x, COMPARE_ROWS[1].stop_x)  # lining up uses one start


class ModelTests(unittest.TestCase):
    def test_no_two_stages_are_the_same_job(self) -> None:
        signatures = {(spec.kinds, spec.units, spec.difference, spec.goals) for spec in STAGES.values()}
        self.assertEqual(len(signatures), len(STAGES))
        kinds = {stage: set(spec.kinds) for stage, spec in STAGES.items()}
        self.assertEqual(kinds[1], {TaskKind.COMPARE_LENGTH, TaskKind.COMPARE_HEIGHT})
        self.assertIn(TaskKind.WEIGH, kinds[2])
        self.assertEqual(kinds[3], {TaskKind.MEASURE})
        self.assertIn(TaskKind.MEASURE_COMPARE, kinds[4])
        self.assertIn(TaskKind.MEASURE_COMPARE, kinds[5])
        self.assertLess(STAGES[5].difference[1], STAGES[4].difference[1])  # closer lengths at the top

    def test_seeded_factory_is_deterministic(self) -> None:
        first = [TaskFactory(random.Random(7)).build(stage) for stage in range(1, 6)]
        second = [TaskFactory(random.Random(7)).build(stage) for stage in range(1, 6)]
        self.assertEqual(
            [(t.kind, t.goal, t.parcels, t.choices) for t in first],
            [(t.kind, t.goal, t.parcels, t.choices) for t in second],
        )

    def test_comparison_target_follows_the_goal(self) -> None:
        for goal in Goal:
            task = _job(2, TaskKind.COMPARE_LENGTH, goal, seed=3)
            values = {p.parcel_id: p.units for p in task.parcels}
            expected = max(values, key=values.get) if goal is Goal.MORE else min(values, key=values.get)
            self.assertEqual(task.target_id, expected)
            self.assertNotEqual(*values.values())

    def test_child_lays_the_blocks_and_they_are_never_capped(self) -> None:
        task = _job(3, TaskKind.MEASURE)
        self.assertIs(task.phase, Phase.LAYING)
        self.assertEqual(task.rows, [0])  # nothing is pre-placed
        self.assertIs(task.check(), Answer.IGNORED)  # an empty row is not an answer
        for _ in range(task.answer + 1):
            self.assertTrue(task.add_block(0))
        self.assertIs(task.fit(0), RowFit.LONG)
        self.assertEqual(list(task.extra(0)), [task.answer])
        self.assertIs(task.check(), Answer.WRONG)
        self.assertIs(task.phase, Phase.DEMONSTRATING)
        self.assertFalse(task.add_block(0))  # no input while demonstrating
        task.finish_demonstration()
        self.assertIs(task.phase, Phase.LAYING)
        self.assertTrue(task.take_block(0))
        self.assertTrue(task.take_block(0))
        self.assertIs(task.fit(0), RowFit.SHORT)
        self.assertEqual(list(task.missing(0)), [task.answer - 1])
        self.assertTrue(task.add_block(0))
        self.assertIs(task.check(), Answer.CORRECT)
        self.assertIs(task.phase, Phase.COUNTING)
        self.assertEqual(task.mistakes, 1)

    def test_board_holds_one_overhanging_block_at_most(self) -> None:
        task = _job(3, TaskKind.MEASURE)
        for _ in range(BOARD_UNITS):
            self.assertTrue(task.add_block(0))
        self.assertFalse(task.add_block(0))

    def test_counting_choices_hide_the_answer_position(self) -> None:
        positions = set()
        for seed in range(80):
            task = TaskFactory(random.Random(seed)).build(4, kind=TaskKind.MEASURE)
            low, mid, high = task.choices
            self.assertEqual((mid - low, high - mid), (1, 1))  # near misses only
            self.assertIn(task.answer, task.choices)
            self.assertGreaterEqual(low, 1)
            positions.add(task.choices.index(task.answer))
        self.assertEqual(positions, {0, 1, 2})

    def test_wrong_count_is_rejected_then_right_count_finishes(self) -> None:
        task = _job(3, TaskKind.MEASURE)
        for _ in range(task.answer):
            task.add_block(0)
        task.check()
        wrong = next(value for value in task.choices if value != task.answer)
        self.assertIs(task.choose_count(wrong), Answer.WRONG)
        task.finish_demonstration()
        self.assertIs(task.choose_count(wrong), Answer.IGNORED)
        self.assertIs(task.choose_count(task.answer), Answer.CORRECT)
        self.assertIs(task.phase, Phase.DONE)
        self.assertFalse(task.clean)

    def test_weighing_needs_both_parcels_on_the_balance(self) -> None:
        task = _job(2, TaskKind.WEIGH, Goal.MORE, seed=4)
        self.assertIs(task.phase, Phase.LOADING)
        self.assertIs(task.pick(task.target_id), Answer.IGNORED)
        self.assertTrue(task.load(0))
        self.assertEqual(task.tilt(), -1)  # one parcel: its pan goes down
        self.assertFalse(task.load(0))
        self.assertTrue(task.load(1))
        self.assertIs(task.phase, Phase.PICKING)
        heavier = max(task.parcels, key=lambda parcel: parcel.weight)
        self.assertEqual(task.tilt(), -1 if heavier.parcel_id == 0 else 1)
        self.assertEqual(task.target_id, heavier.parcel_id)
        self.assertIs(task.pick(heavier.parcel_id), Answer.CORRECT)

    def test_size_does_not_predict_weight(self) -> None:
        surprises = ordinary = 0
        for seed in range(60):
            task = TaskFactory(random.Random(seed)).build(2, kind=TaskKind.WEIGH)
            heavy = max(task.parcels, key=lambda parcel: parcel.weight)
            light = min(task.parcels, key=lambda parcel: parcel.weight)
            self.assertNotEqual(heavy.weight, light.weight)
            if heavy.size < light.size:
                surprises += 1
            else:
                ordinary += 1
        self.assertGreater(surprises, 10)
        self.assertGreater(ordinary, 10)

    def test_measure_and_compare_measures_both_then_picks(self) -> None:
        task = _job(5, TaskKind.MEASURE_COMPARE, Goal.LESS, seed=6)
        self.assertEqual(task.rows, [0, 0])
        for _ in range(task.parcels[0].units):
            task.add_block(0)
        self.assertIs(task.check(), Answer.IGNORED)  # the second parcel is not measured yet
        for _ in range(task.parcels[1].units):
            task.add_block(1)
        self.assertIs(task.check(), Answer.CORRECT)
        self.assertIs(task.phase, Phase.PICKING)
        shorter = min(task.parcels, key=lambda parcel: parcel.units)
        self.assertEqual(abs(task.parcels[0].units - task.parcels[1].units), 1)
        self.assertIs(task.pick(1 - shorter.parcel_id), Answer.WRONG)
        task.finish_demonstration()
        self.assertIs(task.pick(shorter.parcel_id), Answer.CORRECT)
        staggers = {
            TaskFactory(random.Random(seed)).build(5, kind=TaskKind.MEASURE_COMPARE).stagger for seed in range(20)
        }
        self.assertEqual(staggers, {0, 1})

    def test_adaptive_ladder_promotes_and_steps_back(self) -> None:
        progress = WorkshopProgress(stage=2)
        for _ in range(3):
            progress.record(JobSummary(TaskKind.WEIGH, 2, True, 0))
        self.assertEqual(progress.stage, 3)
        for _ in range(2):
            progress.record(JobSummary(TaskKind.MEASURE, 3, False, 2))
        self.assertEqual(progress.stage, 2)
        top = WorkshopProgress(stage=MAX_STAGE)
        for _ in range(9):
            top.record(JobSummary(TaskKind.MEASURE_COMPARE, MAX_STAGE, True, 0))
        self.assertEqual(top.stage, MAX_STAGE)

    def test_delivery_has_a_real_end(self) -> None:
        delivery = Delivery(TaskFactory(random.Random(2)))
        for _ in range(JOBS_PER_DELIVERY):
            self.assertFalse(delivery.complete)
            delivery.finish_job()
            if not delivery.complete:
                delivery.next_job()
        self.assertTrue(delivery.complete)
        delivery.restart()
        self.assertEqual(delivery.completed, 0)


class SaveTests(unittest.TestCase):
    def test_first_release_levels_migrate_without_the_duplicate(self) -> None:
        for level, stage in ((1, 1), (2, 2), (3, 3), (4, 3), (5, 4)):
            legacy = {
                "schema_version": 1,
                "level": level,
                "history": [{"first_attempt_success": True, "hints_used": 0, "used_retry": False}] * 3,
            }
            storage = _Storage(legacy)
            progress = GreiaMeasureProgress(storage).load()
            self.assertEqual(progress.stage, stage, level)
            self.assertEqual(progress.jobs_completed, 3)
            GreiaMeasureProgress(storage).save(progress)
            saved = storage.values[STORAGE_KEY]
            self.assertEqual(saved["schema_version"], SCHEMA_VERSION)
            self.assertEqual(saved["level"], stage)  # older readers still see a level

    def test_new_and_garbage_saves_are_safe(self) -> None:
        for raw in (
            None,
            [],
            "x",
            {"schema_version": 9},
            {"schema_version": 1, "level": "high"},
            {"schema_version": 2, "stage": 99, "clean_streak": -4, "jobs_completed": True},
        ):
            progress = progress_from_payload(raw)
            self.assertTrue(1 <= progress.stage <= MAX_STAGE)
            self.assertGreaterEqual(progress.clean_streak, 0)
        payload = progress_payload(WorkshopProgress(stage=4, clean_streak=2, jobs_completed=12, deliveries_completed=2))
        self.assertEqual(progress_from_payload(payload), WorkshopProgress(4, 2, 0, 12, 2))

    def test_broken_storage_never_raises_into_the_game(self) -> None:
        class Broken:
            def kv_get(self, *args):
                raise OSError("disk")

            def kv_set(self, *args):
                raise OSError("disk")

        adapter = GreiaMeasureProgress(Broken())
        self.assertEqual(adapter.load(), WorkshopProgress())
        adapter.save(WorkshopProgress(stage=3))


class MotionBoundsTests(unittest.TestCase):
    def test_fx_stay_bounded_on_the_acer_floor(self) -> None:
        from measure_renderer import MAX_FX, SceneMotion

        motion = SceneMotion()
        for index in range(200):
            motion.add_fx("confetti", (index, index), 1.0)
        self.assertLessEqual(len(motion.fx), MAX_FX)
        motion.badges[(0, 0)] = (1.0, 1)
        motion.prune(10.0)
        self.assertEqual((motion.fx, motion.badges), ([], {}))


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.played: list[str] = []

    def say(self, cue: str | None) -> None:
        if cue is not None:
            self.spoken.append(cue)

    def praise(self) -> None:
        self.spoken.append("praise")

    def encourage(self) -> None:
        self.spoken.append("retry")

    def has_speech(self, cue: str) -> bool:
        return False

    def play(self, name: str) -> None:
        self.played.append(name)

    def chime(self, number: int) -> None:
        self.played.append(f"chime_{number}")


class _Events:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []
        self.deliveries: list[tuple] = []

    def parcel_completed(self, delivery_id, index, summary) -> None:
        self.jobs.append((delivery_id, index, summary))

    def delivery_completed(self, delivery_id, jobs, stage) -> None:
        self.deliveries.append((delivery_id, jobs, stage))


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def _app(self, stage: int = 1, size: tuple[int, int] = (1024, 600), seed: int = 11, kind=None, goal=None):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from measure_app import BottegaActivity

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = _Storage()
        factory = TaskFactory(random.Random(seed))
        delivery = Delivery(factory, WorkshopProgress(stage=stage))
        if kind is not None:
            delivery.current = factory.build(stage, kind=kind, goal=goal)
        app = BottegaActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            delivery=delivery,
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_ROOT, requested_locale="en"),
            audio=_Audio(),
            progress=GreiaMeasureProgress(storage),
            events=_Events(),
            clock=lambda: now[0],
        )
        return app, now, storage

    @staticmethod
    def _advance(app, now, seconds: float, step: float = 1 / 30) -> None:
        for _ in range(int(seconds / step)):
            now[0] += step
            app.step()

    def _tap(self, app, control_id: str) -> bool:
        x, y = app.controls.layer.target(control_id).rect.center
        return app.tap(app.canvas.mapper.point(x, y))

    def _solve(self, app, now) -> None:
        """Play the current job right first time through pointer taps."""

        task = app.task
        self._advance(app, now, 0.7)
        if task.kind is TaskKind.WEIGH:
            for parcel in (0, 1):
                self.assertTrue(self._tap(app, f"parcel.{parcel}"))
                self._advance(app, now, 0.6)
        if task.kind.lays_blocks:
            for row, parcel in enumerate(task.parcels):
                for _ in range(parcel.units):
                    self.assertTrue(self._tap(app, f"crate.{row}"))
                    self._advance(app, now, 0.1)
            self._advance(app, now, 0.4)
            self.assertTrue(self._tap(app, "check"))
            self._advance(app, now, 0.8)
        if task.kind is TaskKind.MEASURE:
            self.assertTrue(self._tap(app, f"count.{task.choices.index(task.answer)}"))
        else:
            self.assertTrue(self._tap(app, f"parcel.{task.target_id}"))
        self.assertIs(task.phase, Phase.DONE)
        self._advance(app, now, 2.0)

    def test_plays_whole_deliveries_to_the_completion_scene(self) -> None:
        from measure_app import AppState

        for stage in (1, 3, 5):
            app, now, storage = self._app(stage=stage)
            for index in range(JOBS_PER_DELIVERY):
                self._solve(app, now)
                self.assertEqual(app.delivery.completed, index + 1)
            self.assertIs(app.state, AppState.TERMINAL)
            self.assertEqual(len(app.events.jobs), JOBS_PER_DELIVERY)
            self.assertEqual(len(app.events.deliveries), 1)
            saved = storage.values[STORAGE_KEY]
            self.assertEqual((saved["jobs_completed"], saved["deliveries_completed"]), (JOBS_PER_DELIVERY, 1))
            self.assertGreaterEqual(saved["stage"], stage)
            app.render()
            first = app.events.jobs[0][0]
            self.assertTrue(app.tap(app.canvas.mapper.point(*app.completion.primary_rect.center)))
            self.assertIs(app.state, AppState.PLAYING)
            self.assertEqual(app.delivery.completed, 0)
            self._solve(app, now)
            self.assertNotEqual(app.events.jobs[-1][0], first)  # fresh idempotency scope

    def test_overhang_gets_think_pose_marks_and_kind_retry(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, now, _ = self._app(stage=3, kind=TaskKind.MEASURE)
        task = app.task
        self._advance(app, now, 0.7)
        self.assertIn("prompt_measure", app.audio.spoken)
        for _ in range(task.answer + 1):
            self.assertTrue(self._tap(app, "crate.0"))
            self._advance(app, now, 0.4)
        app.audio.spoken.clear()
        self.assertTrue(self._tap(app, "check"))
        self.assertIs(app.cast.feedback.pose, CastPose.THINK)
        self.assertEqual(app.audio.spoken, ["retry"])
        self.assertFalse(app.controls.check.enabled)
        self._advance(app, now, 1.0)
        self.assertEqual(list(app.motion.extra[0]), [task.answer])
        self.assertEqual(app.motion.guide_x, MEASURE_ROW.stop_x + task.answer * UNIT)
        app.render()
        self._advance(app, now, 1.6)
        self.assertIs(task.phase, Phase.LAYING)
        self.assertTrue(self._tap(app, "row.0"))  # one block back to the crate
        self._advance(app, now, 0.5)
        self.assertEqual(task.rows, [task.answer])
        self.assertTrue(self._tap(app, "check"))
        self.assertIs(app.cast.feedback.pose, CastPose.CHEER)
        self._advance(app, now, 0.8)
        self.assertIs(task.phase, Phase.COUNTING)
        self.assertTrue(all(button.visible for button in app.controls.counts))
        self.assertFalse(app.controls.check.visible)
        # A wrong count: the blocks are counted out, the final number is held.
        wrong = next(i for i, value in enumerate(task.choices) if value != task.answer)
        self.assertTrue(self._tap(app, f"count.{wrong}"))
        self._advance(app, now, 0.9 + 0.5 * task.answer + 0.1)
        self.assertIn((0, task.answer - 1), app.motion.badges)
        self.assertEqual(app.motion.badges[(0, task.answer - 1)][1], task.answer)
        self._advance(app, now, 0.5)
        self.assertFalse(app.controls.counts[wrong].enabled)  # the rejected numeral greys out
        self.assertTrue(self._tap(app, f"count.{task.choices.index(task.answer)}"))
        self.assertIs(task.phase, Phase.DONE)

    def test_the_guide_is_leo_whose_voice_the_clips_use(self) -> None:
        app, _, _ = self._app(stage=1)
        self.assertEqual(app.cast.feedback.character, "leo")
        self.assertTrue(app.cast.feedback.available)
        self.assertEqual(app.completion._scene.character, "leo")  # noqa: SLF001

    def test_balance_job_weighs_first_and_demonstrates_the_swing(self) -> None:
        app, now, _ = self._app(stage=2, kind=TaskKind.WEIGH, goal=Goal.LESS)
        task = app.task
        self._advance(app, now, 0.7)
        self.assertEqual(app.audio.spoken, [])  # no recorded line: the job card shows it
        lighter = min(task.parcels, key=lambda parcel: parcel.weight).parcel_id
        self.assertTrue(self._tap(app, f"parcel.{lighter}"))  # first tap only loads it
        self.assertIs(task.phase, Phase.LOADING)
        self._advance(app, now, 0.6)
        self.assertTrue(self._tap(app, f"parcel.{1 - lighter}"))
        self._advance(app, now, 2.0)
        self.assertAlmostEqual(app.motion.angle(now[0]), task.tilt() * 11.0, places=3)
        self.assertTrue(self._tap(app, f"parcel.{1 - lighter}"))  # the heavier one: try again
        self.assertIs(task.phase, Phase.DEMONSTRATING)
        self._advance(app, now, 1.0)
        app.render()
        self._advance(app, now, 1.6)
        self.assertTrue(self._tap(app, f"parcel.{lighter}"))
        self.assertIs(task.phase, Phase.DONE)

    def test_keyboard_alone_measures_and_counts(self) -> None:
        app, now, _ = self._app(stage=3, kind=TaskKind.MEASURE, seed=4)
        task = app.task
        self._advance(app, now, 0.7)
        self.assertEqual(app.controls.layer.focused_id, "crate.0")
        for _ in range(task.answer):
            self.assertTrue(app.press(pygame.K_SPACE))
            self._advance(app, now, 0.4)
        self.assertEqual(task.rows, [task.answer])
        for _ in range(8):
            if app.controls.layer.focused_id == "check":
                break
            app.press(pygame.K_RIGHT if app.controls.layer.focused_id != "row.0" else pygame.K_DOWN)
        self.assertEqual(app.controls.layer.focused_id, "check")
        self.assertTrue(app.press(pygame.K_RETURN))
        self._advance(app, now, 0.8)
        self.assertTrue(app.controls.layer.focused_id.startswith("count."))
        target = f"count.{task.choices.index(task.answer)}"
        for _ in range(4):
            if app.controls.layer.focused_id == target:
                break
            app.press(pygame.K_RIGHT)
        self.assertEqual(app.controls.layer.focused_id, target)
        self.assertTrue(app.press(pygame.K_SPACE))
        self.assertIs(task.phase, Phase.DONE)

    def test_idle_hint_replays_the_goal_without_revealing(self) -> None:
        app, now, _ = self._app(stage=1, kind=TaskKind.COMPARE_LENGTH, goal=Goal.MORE)
        self._advance(app, now, 0.7)
        app.audio.spoken.clear()
        self._advance(app, now, 5.0)
        self.assertFalse(app.cast.pointing)
        self._advance(app, now, 1.5)
        self.assertTrue(app.cast.pointing)
        self.assertEqual(app.audio.spoken, ["prompt_compare_longer"])
        self.assertEqual(app.task.hints, 1)
        for _ in range(450):  # back-off: the second hint comes about twelve seconds later
            self._advance(app, now, 1 / 30)
            if app.motion.pulses:
                break
        # The second hint pulses both parcels alike: never only the answer.
        self.assertEqual(set(app.motion.pulses), {0, 1})
        self.assertIsNone(app.motion.lit)

    def test_home_region_is_protected_and_small_screens_render(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320)):
            for kind, stage in ((TaskKind.MEASURE_COMPARE, 5), (TaskKind.WEIGH, 2), (TaskKind.COMPARE_HEIGHT, 1)):
                for seed in (1, 2):
                    app, now, _ = self._app(stage=stage, size=size, kind=kind, seed=seed)
                    self.assertFalse(app.tap((5, 5)))
                    self._advance(app, now, 0.7)
                    app.render()
                    protected = ControlLayout.for_canvas(app.canvas, size).protected
                    for target in app.controls.layer.targets:
                        self.assertFalse(target.rect.colliderect(protected), (size, kind, target.control_id))


if __name__ == "__main__":
    unittest.main()
