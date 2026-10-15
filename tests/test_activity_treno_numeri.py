"""Tests for Treno Numeri / Number Express (manifest, model, saves, app loop)."""

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
ACTIVITY_ROOT = ROOT / "activities" / "treno_numeri"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import tomllib  # noqa: E402

from treno_content import (  # noqa: E402
    GO_CENTER,
    PLATFORM_TOP,
    CargoKind,
    field_cells,
    sign_face_rect,
    slot_position,
    wagon_rect,
)
from treno_model import (  # noqa: E402
    MAX_STAGE,
    SLOTS,
    STAGES,
    STATIONS_PER_JOURNEY,
    GoResult,
    Journey,
    MoveResult,
    Phase,
    StationFactory,
    StationSummary,
    TaskKind,
    TrainProgress,
)
from treno_services import (  # noqa: E402
    SCHEMA_VERSION,
    STORAGE_KEY,
    GreiaTrainProgress,
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


def _loading(stage: int, **kwargs):
    station = StationFactory(random.Random(kwargs.pop("seed", 1))).build(stage, **kwargs)
    station.arrived()
    return station


def _load(station, count: int) -> None:
    for _ in range(count):
        waiting = station.platform_items()
        assert station.load(waiting[0].item_id).result is MoveResult.MOVED


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_the_count_out_rung(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        act = data["activity"]
        self.assertEqual(act["id"], "org.greia.treno-numeri")
        self.assertEqual(act["languages"], ["it", "en"])  # ES/FR stay staged
        edu = data["education"]
        self.assertEqual((edu["recommended_age_min"], edu["recommended_age_max"]), (4, 5))
        self.assertEqual((edu["difficulty_min"], edu["difficulty_max"]), (1, MAX_STAGE))
        self.assertTrue(edu["adaptive_difficulty"])
        skills = {skill["id"] for skill in edu["skills"]}
        self.assertTrue({"math.counting.cardinality", "math.quantity.numeral_match", "math.comparison.quantity"} <= skills)
        self.assertNotIn("math.operations.addition", skills)  # Casa del dieci owns part-whole
        self.assertEqual(
            {event["id"]: event["kind"] for event in edu["events"]},
            {"train.station_completed": "milestone", "train.journey_completed": "completion"},
        )
        self.assertEqual(data["input"]["profile"], "hybrid")
        # The platform storage schema stays 1: the payload migrates itself.
        self.assertEqual(data["storage"]["schema_version"], 1)

    def test_locale_bundles_share_keys_without_emoji_or_dormant_copy(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"])
        self.assertEqual(keys, {"activity.title", "victory.title", "button.play_again"})
        for locale, strings in bundles.items():
            self.assertEqual(set(strings), keys, locale)
            for value in strings.values():
                self.assertTrue(value.strip())
                self.assertTrue(all(ord(ch) < 0x2190 for ch in value), (locale, value))

    def test_private_art_has_source_and_rendition_and_no_cast_redraw(self) -> None:
        names = (
            "locomotive", "wheel", "station", "station_sign",
            "wagon_back_orange", "wagon_front_orange", "wagon_back_leaf", "wagon_front_leaf",
        )
        for name in names:
            self.assertTrue((ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg").is_file(), name)
            self.assertTrue((ACTIVITY_ROOT / "assets" / "runtime" / f"{name}.png").is_file(), name)
        leftovers = {path.stem for path in (ACTIVITY_ROOT / "assets" / "runtime").glob("*.png")} - set(names)
        self.assertEqual(leftovers, set())  # no private Dani, fruit or crate redraws
        lint = ("<image", "data:", "<text", "<filter", "<mask", "<style", "<script")
        for svg in (ACTIVITY_ROOT / "assets" / "source").glob("*.svg"):
            if svg.stem == "icon":
                continue
            source = svg.read_text(encoding="utf-8")
            self.assertFalse([token for token in lint if token in source], svg.name)

    def test_cargo_is_shared_library_art(self) -> None:
        from greia_platform.activity_api import get_shared_visual_path

        for kind in CargoKind:
            self.assertTrue(get_shared_visual_path(kind.asset_id).is_file(), kind)


class GeometryTests(unittest.TestCase):
    def test_slots_form_a_ten_frame_inside_the_wagons(self) -> None:
        for slot in range(SLOTS):
            x, y = slot_position(slot)
            left, top, width, height = wagon_rect(slot // 5)
            self.assertTrue(left < x < left + width and top < y < top + height, slot)
        self.assertLess(slot_position(4)[0], slot_position(5)[0])

    def test_platform_cargo_board_and_go_stay_clear_of_chrome(self) -> None:
        cells = field_cells()
        self.assertEqual(len(cells), 10)
        self.assertTrue(all(y > PLATFORM_TOP for _, y in cells))
        # Logical protected region on the smallest supported screen (480x320).
        x, y, w, h = sign_face_rect()
        self.assertGreater(y - 16, 128)
        self.assertGreater(GO_CENTER[0] - 56, max(x for x, _ in cells) + 46)


class ModelTests(unittest.TestCase):
    def test_loading_is_never_capped_at_the_order(self) -> None:
        station = _loading(1, order=2)
        self.assertEqual((station.task, station.order, station.loaded), (TaskKind.COUNT_OUT, 2, 0))
        self.assertIs(station.go(), GoResult.IGNORED)  # nothing loaded yet
        _load(station, 4)
        self.assertEqual(station.loaded, 4)
        self.assertEqual(station.filled_slots(), [0, 1, 2, 3])
        self.assertEqual(station.extra_slots(), [2, 3])
        self.assertIs(station.go(), GoResult.TOO_MANY)
        self.assertIs(station.phase, Phase.DEMONSTRATING)
        self.assertIs(station.unload(0).result, MoveResult.IGNORED)  # not during the demo
        station.finish_demonstration()
        self.assertIs(station.unload(0).result, MoveResult.MOVED)
        self.assertIs(station.unload(0).result, MoveResult.MOVED)
        self.assertEqual(station.loaded, 2)
        self.assertIs(station.go(), GoResult.CORRECT)
        self.assertIs(station.phase, Phase.DEPARTING)
        self.assertFalse(station.clean)

    def test_too_few_shows_where_the_missing_cargo_goes(self) -> None:
        station = _loading(3, order=7)
        _load(station, 5)
        self.assertEqual(station.missing_slots(), [5, 6])
        self.assertIs(station.go(), GoResult.TOO_FEW)
        station.finish_demonstration()
        _load(station, 2)
        self.assertIs(station.go(), GoResult.CORRECT)

    def test_unloaded_cargo_returns_home_and_slots_refill_in_order(self) -> None:
        station = _loading(2, order=4)
        first = station.platform_items()[0]
        home = (first.x, first.y)
        station.load(first.item_id)
        _load(station, 2)
        station.unload(0)  # the last cargo of the first wagon (slot 2)
        self.assertEqual(station.filled_slots(), [0, 1])
        self.assertTrue(station.item(first.item_id).slot == 0 and (first.x, first.y) == home)
        _load(station, 1)
        self.assertEqual(station.filled_slots(), [0, 1, 2])

    def test_same_stage_order_is_the_first_wagon(self) -> None:
        station = _loading(4, order=3)
        self.assertIs(station.task, TaskKind.SAME)
        self.assertEqual(station.sample_slots(), [0, 1, 2])
        self.assertEqual(station.loaded, 0)
        self.assertFalse(station.wagon_has_cargo(0))  # the order wagon is locked
        _load(station, 3)
        self.assertEqual(station.filled_slots(), [5, 6, 7])
        self.assertIs(station.go(), GoResult.CORRECT)

    def test_fix_stage_preloads_more_or_fewer_never_the_same(self) -> None:
        factory = StationFactory(random.Random(3))
        for _ in range(60):
            station = factory.build(5)
            station.arrived()
            self.assertNotEqual(station.loaded, station.order)
            self.assertTrue(1 <= station.loaded <= 5)
            self.assertGreaterEqual(len(station.platform_items()) + station.loaded, station.order + 1)
        station = _loading(5, order=3, preload=5)
        self.assertIs(station.go(), GoResult.TOO_MANY)
        station.finish_demonstration()
        station.unload(1)
        station.unload(1)
        self.assertIs(station.go(), GoResult.CORRECT)

    def test_every_stage_leaves_room_to_overshoot(self) -> None:
        factory = StationFactory(random.Random(4))
        for stage, spec in STAGES.items():
            for _ in range(40):
                station = factory.build(stage)
                self.assertIn(station.order, spec.orders)
                room = len(station.free_slots())
                cargo = len(station.platform_items())
                self.assertGreater(min(room, cargo + station.loaded), station.order - station.loaded, stage)
                cells = {item.home for item in station.items if not item.locked}
                self.assertEqual(len(cells), len([item for item in station.items if not item.locked]))

    def test_adaptive_ladder_promotes_and_steps_back(self) -> None:
        progress = TrainProgress(stage=1)
        for _ in range(3):
            progress.record(StationSummary(2, 1, True, 0))
        self.assertEqual(progress.stage, 2)
        progress.record(StationSummary(3, 2, False, 1))
        progress.record(StationSummary(4, 2, False, 2))
        self.assertEqual(progress.stage, 1)
        progress.stage = MAX_STAGE
        for _ in range(5):
            progress.record(StationSummary(3, MAX_STAGE, True, 0))
        self.assertEqual(progress.stage, MAX_STAGE)

    def test_journey_has_a_real_end(self) -> None:
        journey = Journey(StationFactory(random.Random(6)))
        for _ in range(STATIONS_PER_JOURNEY):
            self.assertFalse(journey.complete)
            journey.finish_station()
            if not journey.complete:
                journey.next_station()
        self.assertTrue(journey.complete)
        journey.restart()
        self.assertEqual(journey.completed, 0)


class SaveTests(unittest.TestCase):
    def test_first_release_star_saves_migrate_without_losing_totals(self) -> None:
        storage = _Storage({"stars": 23})
        progress = GreiaTrainProgress(storage).load()
        self.assertEqual((progress.stations_completed, progress.stage), (23, 2))
        GreiaTrainProgress(storage).save(progress)
        saved = storage.values[STORAGE_KEY]
        self.assertEqual(saved["schema_version"], SCHEMA_VERSION)
        self.assertEqual((saved["stations_completed"], saved["stars"]), (23, 23))
        self.assertEqual(progress_from_payload(saved).stage, 2)
        self.assertEqual(progress_from_payload({"stars": 3}).stage, 1)

    def test_new_and_garbage_saves_are_safe(self) -> None:
        self.assertEqual(progress_from_payload({}).stage, 1)
        self.assertEqual(progress_from_payload("junk").stage, 1)
        bad = progress_from_payload({"schema_version": 2, "stage": 99, "stations_completed": -5, "clean_streak": "x"})
        self.assertEqual((bad.stage, bad.stations_completed, bad.clean_streak), (MAX_STAGE, 0, 0))
        payload = progress_payload(TrainProgress(stage=4, clean_streak=2, stations_completed=12))
        self.assertEqual((progress_from_payload(payload).stage, progress_from_payload(payload).clean_streak), (4, 2))


class MotionBoundsTests(unittest.TestCase):
    def test_fx_and_smoke_stay_bounded_on_the_acer_floor(self) -> None:
        from treno_renderer import MAX_FX, MAX_PUFFS, SceneMotion

        motion = SceneMotion()
        for index in range(200):
            motion.add_fx("confetti", (index, index), 1.0)
            motion.add_puff(1.0, float(index), 0.0)
        self.assertLessEqual(len(motion.fx), MAX_FX)
        self.assertLessEqual(len(motion.puffs), MAX_PUFFS)
        motion.prune(10.0)
        self.assertEqual((motion.fx, motion.puffs), ([], []))


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.played: list[str] = []

    def say(self, cue: str, then: str | None = None) -> None:
        self.spoken.append(cue)

    def say_number(self, number: int) -> None:
        self.spoken.append(f"count_{number}")

    def has_speech(self, cue: str) -> bool:
        return False

    def play(self, name: str) -> None:
        self.played.append(name)

    def chime(self, number: int) -> None:
        self.played.append(f"chime_{number}")


class _Events:
    def __init__(self) -> None:
        self.stations: list[tuple] = []
        self.journeys: list[tuple] = []

    def station_completed(self, journey_id, index, summary) -> None:
        self.stations.append((journey_id, index, summary))

    def journey_completed(self, journey_id, stations, stage) -> None:
        self.journeys.append((journey_id, stations, stage))


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def _app(self, stage: int = 1, size: tuple[int, int] = (1024, 600), seed: int = 11):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from treno_app import TrenoApp

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = _Storage()
        app = TrenoApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            journey=Journey(StationFactory(random.Random(seed)), TrainProgress(stage=stage)),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_ROOT, requested_locale="en"),
            audio=_Audio(),
            progress=GreiaTrainProgress(storage),
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

    def _arrive(self, app, now) -> None:
        self._advance(app, now, 1.9)
        self.assertIs(app.station.phase, Phase.LOADING)

    def _load_taps(self, app, now, count: int) -> None:
        for _ in range(count):
            waiting = app.station.next_platform_item()
            self.assertTrue(self._tap_logical(app, waiting.x, waiting.y))
            self._advance(app, now, 0.2)
        self._advance(app, now, 0.4)

    def test_plays_a_whole_journey_to_the_completion_scene(self) -> None:
        from treno_app import AppState

        app, now, storage = self._app(stage=1)
        for index in range(STATIONS_PER_JOURNEY):
            self._arrive(app, now)
            station = app.station
            self._load_taps(app, now, station.order)
            self.assertIn(f"count_{station.order}", app.audio.spoken)
            self.assertTrue(self._tap_logical(app, *GO_CENTER))
            self.assertIs(station.phase, Phase.DEPARTING)
            self._advance(app, now, 0.6 + 0.26 * station.order + 1.8)
            self.assertEqual(app.journey.completed, index + 1)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertEqual(len(app.events.stations), STATIONS_PER_JOURNEY)
        self.assertEqual(len(app.events.journeys), 1)
        self.assertEqual(app.audio.spoken[-1], "celebrate")
        saved = storage.values[STORAGE_KEY]
        self.assertEqual((saved["stations_completed"], saved["journeys_completed"]), (STATIONS_PER_JOURNEY, 1))
        app.render()
        first_journey = app.events.stations[0][0]
        self.assertTrue(self._tap_logical(app, *app.completion.primary_rect.center))
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.journey.completed, 0)
        # A replayed journey publishes under a fresh idempotency scope.
        self._arrive(app, now)
        self._load_taps(app, now, app.station.order)
        self._tap_logical(app, *GO_CENTER)
        self._advance(app, now, 4.5)
        self.assertNotEqual(app.events.stations[-1][0], first_journey)

    def test_too_many_gets_think_pose_recount_and_kind_retry(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, now, _ = self._app(stage=1)
        self._arrive(app, now)
        station = app.station
        self._load_taps(app, now, station.order + 2)
        app.audio.spoken.clear()
        self.assertTrue(self._tap_logical(app, *GO_CENTER))
        self.assertIs(app.cast.feedback.pose, CastPose.THINK)
        self.assertEqual(app.audio.spoken[0], "retry")
        self.assertFalse(app.controls.go.enabled)
        self._advance(app, now, 1.3 + 0.55 * (station.order + 2) + 0.3)
        self.assertEqual(app.audio.spoken[1:], [f"count_{n}" for n in range(1, station.order + 3)])
        self.assertEqual(app.motion.extra_slots, tuple(station.extra_slots()))
        self._advance(app, now, 1.5)
        self.assertIs(station.phase, Phase.LOADING)
        # Send the extra cargo back by tapping its wagon, then go again.
        for _ in range(2):
            self.assertTrue(self._tap_logical(app, *pygame.Rect(wagon_rect(0)).center))
            self._advance(app, now, 0.5)
        self.assertEqual(station.loaded, station.order)
        self.assertTrue(self._tap_logical(app, *GO_CENTER))
        self.assertIs(app.cast.feedback.pose, CastPose.CHEER)

    def test_same_stage_demonstrates_one_to_one(self) -> None:
        app, now, _ = self._app(stage=4)
        self._arrive(app, now)
        station = app.station
        self.assertIs(station.task, TaskKind.SAME)
        self._load_taps(app, now, station.order - 1)
        self.assertTrue(self._tap_logical(app, *GO_CENTER))
        self._advance(app, now, 1.3 + 0.55 * station.order + 0.3)
        self.assertEqual(app.motion.pairs, station.order - 1)
        self.assertEqual(app.motion.missing_slots, (5 + station.order - 1,))
        app.render()

    def test_keyboard_alone_completes_a_journey(self) -> None:
        from treno_app import AppState

        app, now, _ = self._app(stage=2, seed=21)
        for _ in range(STATIONS_PER_JOURNEY):
            self._arrive(app, now)
            station = app.station
            for _ in range(station.order):
                self.assertTrue(app.press(pygame.K_SPACE))
                self._advance(app, now, 0.2)
            self.assertEqual(station.loaded, station.order)
            for _ in range(8):  # arrow right along the platform reaches GO
                if app.controls.layer.focused_id == "go":
                    break
                app.press(pygame.K_RIGHT)
            self.assertEqual(app.controls.layer.focused_id, "go")
            self.assertTrue(app.press(pygame.K_RETURN))
            self._advance(app, now, 0.6 + 0.26 * station.order + 1.8)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertIs(app.state, AppState.PLAYING)

    def test_idle_hint_points_at_the_order_without_revealing(self) -> None:
        app, now, _ = self._app(stage=1)
        self._arrive(app, now)
        self._advance(app, now, 3.0)
        self.assertFalse(app.cast.pointing)
        app.audio.played.clear()
        self._advance(app, now, 3.3)
        station = app.station
        self.assertTrue(app.cast.pointing)
        self.assertEqual(station.hints, 1)
        self._advance(app, now, 0.4 + 0.34 * station.order)
        self.assertEqual([name for name in app.audio.played if name.startswith("chime")],
                         [f"chime_{n}" for n in range(1, station.order + 1)])
        self.assertFalse(app.motion.badges)  # the hint never prints a count

    def test_board_tap_replays_the_order_and_full_wagon_creaks(self) -> None:
        app, now, _ = self._app(stage=4)
        self._arrive(app, now)
        self._advance(app, now, 2.0)
        station = app.station
        app.audio.played.clear()
        x, y, w, h = sign_face_rect()
        self.assertTrue(self._tap_logical(app, x + w // 2, y + h // 2))
        self._advance(app, now, 0.4 + 0.34 * station.order)
        self.assertEqual(sum(1 for name in app.audio.played if name.startswith("chime")), station.order)
        self._load_taps(app, now, 5)  # the child's wagon holds five
        waiting = station.next_platform_item()
        self.assertTrue(self._tap_logical(app, waiting.x, waiting.y))
        self.assertIn("creak", app.audio.played)
        self.assertTrue(waiting.on_platform)

    def test_home_region_is_protected_and_small_screens_render(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320)):
            app, now, _ = self._app(stage=1, size=size)
            self.assertFalse(app.tap((5, 5)))
            self._arrive(app, now)
            self._load_taps(app, now, 1)
            app.render()
            protected = ControlLayout.for_canvas(app.canvas, size).protected
            for target in app.controls.layer.targets:
                self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))


if __name__ == "__main__":
    unittest.main()
