"""Tests for Colline Allegre (Bumpy Hills): finite courses, ladder, physics and app loop."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import tomllib
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from activities.colline_allegre.colline_app import AppState, CollineActivity
from activities.colline_allegre.colline_art import CollineArt
from activities.colline_allegre.colline_audio import CollineAudio
from activities.colline_allegre.colline_content import (
    COURSES,
    COURSES_PER_SET,
    FIXED_DT,
    MAX_RUNG,
    MIN_RUNG,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    STARS_PER_COURSE,
    FeatureKind,
    Surface,
)
from activities.colline_allegre.colline_input import DriveInput
from activities.colline_allegre.colline_layout import BRAKE_RECT, GO_RECT
from activities.colline_allegre.colline_model import (
    Controls,
    CourseLayout,
    CourseRun,
    CourseSet,
    RunEvent,
    adapt_rung,
    bounded_history,
)
from activities.colline_allegre.colline_services import (
    SCHEMA_VERSION,
    STORAGE_KEY,
    CollineProgress,
    GreiaCollineProgress,
    parse_progress,
    serialize_progress,
)
from greia_platform.activity_controls import ControlLayout
from greia_platform.input_core import SemanticAction
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "colline_allegre"
LOCALES = ("en", "it", "es", "fr")
FORBIDDEN_SVG = re.compile(
    r'<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script|foreignObject|<animate|blend-mode|skew|href="[^#]|xlink:href="[^#]|sodipodi|inkscape:'
)


def drive_course(run: CourseRun, *, smart: bool, seconds: float = 90.0) -> list[RunEvent]:
    """Drive a run with a scripted child: hold GO; ``smart`` brakes at snail signs."""

    events: list[RunEvent] = []
    tumble_clock = 0.0
    for _ in range(int(seconds / FIXED_DT)):
        if run.tumbling:
            tumble_clock += FIXED_DT
            if tumble_clock >= 1.2:
                run.respawn()
                tumble_clock = 0.0
        veh = run.vehicle
        brake = smart and any(d.sign_x - 250 <= veh.x <= d.edge_x and veh.vx > 120 for d in run.layout.drops)
        events.extend(run.step(Controls(go=not brake, brake=brake)))
        if run.finished and run.vehicle.speed < 5:
            break
    return events


class _MemoryProgress:
    def __init__(self, progress: CollineProgress | None = None) -> None:
        self.progress = progress or CollineProgress()
        self.saves = 0

    def load(self) -> CollineProgress:
        return self.progress

    def save(self, progress: CollineProgress) -> None:
        self.progress = progress
        self.saves += 1


class _Events:
    def __init__(self) -> None:
        self.log: list[tuple[str, str, dict]] = []

    def course_finished(self, session_id: str, payload: dict) -> None:
        self.log.append(("course", session_id, payload))

    def set_completed(self, session_id: str, payload: dict) -> None:
        self.log.append(("set", session_id, payload))


class _Storage:
    def __init__(self, data: dict | None = None, *, fail: bool = False) -> None:
        self.data = dict(data or {})
        self.fail = fail

    def kv_get(self, key, default=None):
        if self.fail:
            raise OSError("volume budget")
        return self.data.get(key, default)

    def kv_set(self, key, value) -> None:
        if self.fail:
            raise OSError("volume budget")
        self.data[key] = value


class CollineBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))


class ManifestAndPackageTests(CollineBase):
    def test_real_script_entrypoint_imports_in_non_package_context(self) -> None:
        """The supervisor executes main.py as a script, not as a package."""

        import runpy

        source_root = str(ACTIVITY_DIR)
        sys.path.insert(0, source_root)
        try:
            namespace = runpy.run_path(str(ACTIVITY_DIR / "main.py"), run_name="greia_script_import_smoke")
        finally:
            sys.path.remove(source_root)
        self.assertTrue(callable(namespace["main"]))

    def test_manifest_is_honest_about_the_course_ladder(self) -> None:
        data = tomllib.loads((ACTIVITY_DIR / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.colline-allegre")
        self.assertEqual(data["activity"]["version"], "0.2.0")
        self.assertEqual(data["activity"]["languages"], ["it", "en"])
        self.assertEqual(data["input"]["profile"], "game")
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 7))
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, len(COURSES)))
        self.assertTrue(education["adaptive_difficulty"])
        events = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(events, {"colline.course_finished": "milestone", "colline.set_completed": "completion"})

    def test_four_locale_key_parity_and_title_audio(self) -> None:
        keys = None
        for locale in LOCALES:
            bundle = json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            strings = bundle["strings"]
            self.assertTrue(all(isinstance(v, str) and v.strip() for v in strings.values()), locale)
            keys = keys or set(strings)
            self.assertEqual(set(strings), keys, locale)
        self.assertTrue({"victory.title", "victory.subtitle", "button.play_again"} <= keys)
        for locale in ("en", "it"):
            audio = ACTIVITY_DIR / "locales" / locale / "audio" / "activity-title.wav"
            self.assertTrue(audio.is_file())
            self.assertTrue(audio.with_name("activity-title.wav.receipt.json").is_file())

    def test_private_art_follows_the_svg_recipe_and_is_rendered(self) -> None:
        sources = sorted((ACTIVITY_DIR / "assets" / "source").glob("*.svg"))
        self.assertGreaterEqual(len(sources), 9)
        for source in sources:
            text = source.read_text(encoding="utf-8")
            self.assertIsNone(FORBIDDEN_SVG.search(text), source.name)
            self.assertLessEqual(len(text.encode()), 6 * 1024, source.name)
            if source.stem != "icon":
                self.assertTrue((ACTIVITY_DIR / "assets" / "runtime" / f"{source.stem}.png").is_file(), source.name)
        icon = pygame.image.load(str(ACTIVITY_DIR / "assets" / "icon.png"))
        self.assertEqual(icon.get_size(), (256, 256))

    def test_no_surface_alpha_none_reset(self) -> None:
        """set_alpha(None) would turn per-pixel transparency off for later blits."""

        for module in ACTIVITY_DIR.glob("*.py"):
            self.assertNotIn("set_alpha(None)", module.read_text(encoding="utf-8"), module.name)


class CourseLayoutTests(unittest.TestCase):
    def test_five_finite_courses_in_distinct_biomes(self) -> None:
        self.assertEqual(len(COURSES), COURSES_PER_SET)
        self.assertEqual(len({course.biome for course in COURSES}), COURSES_PER_SET)
        self.assertEqual(len({course.friend for course in COURSES}), COURSES_PER_SET)
        for course in COURSES:
            layout = CourseLayout(course, 2)
            self.assertLess(layout.finish_x, layout.length)
            self.assertEqual(len(layout.star_spots), STARS_PER_COURSE)
            self.assertEqual(list(layout.checkpoints), sorted(layout.checkpoints))
            self.assertLess(layout.checkpoints[-1], layout.finish_x)

    def test_ground_is_continuous(self) -> None:
        for course in COURSES:
            layout = CourseLayout(course, MAX_RUNG)
            previous = layout.height(0.0)
            for x in range(4, int(layout.length), 4):
                height = layout.height(float(x))
                self.assertLess(abs(height - previous), 9.0, f"{course.course_id} jump at {x}")
                previous = height

    def test_ladder_rises_through_the_set_and_with_the_rung(self) -> None:
        kinds = [{feature.kind for feature in course.features} for course in COURSES]
        self.assertNotIn(FeatureKind.DROP, kinds[0] | kinds[1] | kinds[2])
        self.assertIn(FeatureKind.BRIDGE, kinds[1])
        self.assertIn(FeatureKind.MUD, kinds[2])
        self.assertIn(FeatureKind.DROP, kinds[3])
        self.assertTrue({FeatureKind.DROP, FeatureKind.MUSHROOM} <= kinds[4])
        relief = [CourseLayout(course, 2) for course in COURSES]
        self.assertLess(relief[0].scale * max(f.height for f in COURSES[0].features), max(f.height for f in COURSES[4].features))
        gentle, wild = CourseLayout(COURSES[3], MIN_RUNG), CourseLayout(COURSES[3], MAX_RUNG)
        self.assertLess(wild.min_y, gentle.min_y)

    def test_surfaces_mark_bridge_mud_and_mushroom(self) -> None:
        pond = CourseLayout(COURSES[1], 2)
        bridge = next(span for span in pond.spans if span.feature.kind is FeatureKind.BRIDGE)
        self.assertIs(pond.surface(bridge.at(0.5)), Surface.BRIDGE)
        autumn = CourseLayout(COURSES[2], 2)
        mud = next(span for span in autumn.spans if span.feature.kind is FeatureKind.MUD)
        self.assertIs(autumn.surface(mud.at(0.5)), Surface.MUD)
        sky = CourseLayout(COURSES[4], 2)
        self.assertIs(sky.surface(sky.pads[0]), Surface.MUSHROOM)
        self.assertIs(sky.surface(10.0), Surface.GRASS)


class PhysicsTests(unittest.TestCase):
    def test_fixed_step_is_deterministic(self) -> None:
        def trace() -> tuple[float, float, float]:
            run = CourseRun(CourseLayout(COURSES[0], 2))
            for index in range(600):
                run.step(Controls(go=index % 90 < 70, brake=index % 90 >= 80))
            veh = run.vehicle
            return (veh.x, veh.y, veh.angle)

        self.assertEqual(trace(), trace())

    def test_holding_go_finishes_the_first_course_once(self) -> None:
        run = CourseRun(CourseLayout(COURSES[0], 1))
        events = drive_course(run, smart=False)
        self.assertTrue(run.finished)
        self.assertEqual(events.count(RunEvent.FINISH), 1)
        self.assertEqual(run.stars_collected, STARS_PER_COURSE)
        self.assertLess(run.elapsed, 40.0)
        self.assertGreater(run.elapsed, 12.0)
        # After the finish the buggy rolls to a stop near the picnic.
        self.assertLess(run.vehicle.speed, 5.0)

    def test_every_course_is_finishable_at_every_rung(self) -> None:
        for rung in range(MIN_RUNG, MAX_RUNG + 1):
            for course in COURSES:
                for smart in (True, False):
                    run = CourseRun(CourseLayout(course, rung), assist=rung == MIN_RUNG)
                    drive_course(run, smart=smart, seconds=120.0)
                    self.assertTrue(run.finished, f"{course.course_id} rung {rung} smart={smart}")
                    self.assertLess(run.elapsed, 60.0)

    def test_brake_slows_the_buggy(self) -> None:
        run = CourseRun(CourseLayout(COURSES[0], 2))
        for _ in range(150):
            run.step(Controls(go=True))
        speed = run.vehicle.vx
        for _ in range(60):
            run.step(Controls(brake=True))
        self.assertLess(run.vehicle.vx, speed * 0.5)

    def test_too_fast_over_a_drop_tumbles_and_respawns_on_the_flag(self) -> None:
        run = CourseRun(CourseLayout(COURSES[3], 2))
        events: list[RunEvent] = []
        for _ in range(int(20 / FIXED_DT)):
            events.extend(run.step(Controls(go=True)))
            if run.tumbling:
                break
        self.assertIn(RunEvent.DROP_TOO_FAST, events)
        self.assertIn(RunEvent.TUMBLE, events)
        self.assertEqual(run.tumbles, 1)
        self.assertEqual(run.drop_hints, {0})
        flag = run.checkpoint_x
        run.respawn()
        self.assertFalse(run.tumbling)
        self.assertEqual(run.vehicle.x, flag)
        self.assertEqual(run.vehicle.vx, 0.0)
        self.assertLess(abs(run.vehicle.angle), 0.1)  # level ground at the flag

    def test_slowing_down_crosses_the_drop_safely(self) -> None:
        run = CourseRun(CourseLayout(COURSES[3], 2))
        events = drive_course(run, smart=True)
        self.assertIn(RunEvent.DROP_SAFE, events)
        self.assertNotIn(RunEvent.TUMBLE, events)
        self.assertTrue(run.finished)

    def test_two_tumbles_switch_on_the_kind_assist(self) -> None:
        run = CourseRun(CourseLayout(COURSES[3], 2))
        self.assertFalse(run.drop_assist)
        events = drive_course(run, smart=False)
        self.assertEqual(run.tumbles, 2)
        self.assertTrue(run.drop_assist and run.air_assist)
        self.assertTrue(run.finished)
        self.assertEqual(events.count(RunEvent.TUMBLE), 2)

    def test_gentle_courses_right_the_buggy_in_the_air(self) -> None:
        self.assertTrue(CourseRun(CourseLayout(COURSES[0], 2)).air_assist)
        self.assertFalse(CourseRun(CourseLayout(COURSES[3], 2)).air_assist)
        self.assertTrue(CourseRun(CourseLayout(COURSES[3], 2), assist=True).air_assist)

    def test_mid_air_tilt(self) -> None:
        run = CourseRun(CourseLayout(COURSES[3], 2))
        run.vehicle.y = 100.0
        run.step(Controls(tilt=1.0))
        self.assertTrue(run.vehicle.airborne)
        self.assertGreater(run.vehicle.angular_velocity, 0.0)

    def test_star_pickup_and_mushroom_bounce_once_per_contact(self) -> None:
        run = CourseRun(CourseLayout(COURSES[4], 2))
        events = drive_course(run, smart=True)
        self.assertEqual(run.stars_collected, STARS_PER_COURSE)
        self.assertEqual(events.count(RunEvent.STAR), STARS_PER_COURSE)
        self.assertGreaterEqual(events.count(RunEvent.BOUNCE), 2)
        self.assertLessEqual(events.count(RunEvent.BOUNCE), 4)

    def test_checkpoints_are_passed_in_order(self) -> None:
        run = CourseRun(CourseLayout(COURSES[1], 2))
        events = drive_course(run, smart=True)
        self.assertEqual(events.count(RunEvent.CHECKPOINT), len(run.layout.checkpoints) - 1)
        self.assertEqual(run.checkpoint_x, run.layout.checkpoints[-1])


class LadderTests(unittest.TestCase):
    def test_course_set_plays_five_courses(self) -> None:
        course_set = CourseSet(2)
        seen = []
        while not course_set.complete:
            run = course_set.build_run()
            seen.append(run.layout.spec.course_id)
            drive_course(run, smart=True)
            course_set.record(run)
        self.assertEqual(seen, [course.course_id for course in COURSES])
        self.assertEqual(course_set.total_stars, COURSES_PER_SET * STARS_PER_COURSE)
        self.assertEqual(course_set.total_tumbles, 0)

    def test_rung_adapts_and_is_bounded(self) -> None:
        self.assertEqual(adapt_rung(1, 0), 2)
        self.assertEqual(adapt_rung(2, 4), 2)
        self.assertEqual(adapt_rung(2, 9), 1)
        self.assertEqual(adapt_rung(MAX_RUNG, 0), MAX_RUNG)
        self.assertEqual(adapt_rung(MIN_RUNG, 20), MIN_RUNG)
        self.assertEqual(bounded_history(range(10), 3)[-1], 3)
        self.assertLessEqual(len(bounded_history(range(10), 3)), 6)


class ServicesTests(unittest.TestCase):
    def test_schema_one_distance_save_is_carried_forward(self) -> None:
        old = {"best_distance": 712.4, "total_stars": 22, "timestamp": 1.0}
        progress = parse_progress(old)
        self.assertEqual(progress.total_stars, 22)
        self.assertAlmostEqual(progress.best_distance, 712.4)
        self.assertEqual(progress.rung, MIN_RUNG)
        storage = _Storage({STORAGE_KEY: old})
        port = GreiaCollineProgress(storage)
        port.save(port.load())
        saved = storage.data[STORAGE_KEY]
        self.assertEqual(saved["schema_version"], SCHEMA_VERSION)
        self.assertEqual(saved["total_stars"], 22)
        self.assertAlmostEqual(saved["best_distance"], 712.4)

    def test_schema_two_round_trip_and_junk_recovery(self) -> None:
        progress = CollineProgress(3, (1, 2, 9), 4, 21, 60, 10.0)
        self.assertEqual(parse_progress(serialize_progress(progress)), progress)
        junk = {"schema_version": SCHEMA_VERSION, "rung": 99, "history": ["x", -1, 2, True], "sets": -3, "total_stars": "a"}
        self.assertEqual(parse_progress(junk), CollineProgress(history=(2,)))
        self.assertEqual(parse_progress(None), CollineProgress())
        self.assertEqual(parse_progress({"best_distance": float("nan")}).best_distance, 0.0)

    def test_storage_failures_are_soft(self) -> None:
        port = GreiaCollineProgress(_Storage(fail=True))
        self.assertEqual(port.load(), CollineProgress())
        port.save(CollineProgress(rung=2))


class InputTests(CollineBase):
    def test_game_profile_keys_drive_the_pedals(self) -> None:
        drive = DriveInput()
        self.assertEqual(drive.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)), SemanticAction.MOVE_RIGHT)
        self.assertTrue(drive.go)
        self.assertEqual(drive.controls().tilt, 1.0)
        drive.handle(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))
        self.assertFalse(drive.go)
        drive.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(drive.go)
        self.assertEqual(drive.controls().tilt, 0.0)
        drive.handle(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE))
        drive.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
        self.assertTrue(drive.brake)
        self.assertTrue(drive.controls().brake)
        self.assertEqual(drive.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)), "listen")
        self.assertIs(drive.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)), SemanticAction.CANCEL)
        drive.release_all()
        self.assertFalse(drive.go or drive.brake)


class AppLoopTests(CollineBase):
    def make_app(self, size=(REFERENCE_WIDTH, REFERENCE_HEIGHT), locale="en", progress=None):
        screen = pygame.display.set_mode(size)
        self.now = [100.0]
        resources = activity_resources(ACTIVITY_DIR, requested_locale=locale)
        self.store = _MemoryProgress(progress)
        self.events = _Events()
        app = CollineActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            typography=GreiaTypography(),
            resources=resources,
            audio=CollineAudio(locale=locale),
            progress=self.store,
            events=self.events,
            clock=lambda: self.now[0],
            session_prefix="test",
        )
        return app

    def advance(self, app: CollineActivity, seconds: float, *, render: bool = False) -> None:
        for _ in range(int(seconds * 30)):
            self.now[0] += 1 / 30
            app.step()
            if render:
                app.render()

    def drive_smartly(self, app: CollineActivity, seconds: float) -> None:
        for _ in range(int(seconds * 30)):
            ride = app.ride
            if app.state in (AppState.READY, AppState.DRIVING) and ride is not None:
                veh = ride.vehicle
                brake = any(d.sign_x - 250 <= veh.x <= d.edge_x and veh.vx > 120 for d in ride.layout.drops)
                app.hold(go=not brake, brake=brake)
            self.now[0] += 1 / 30
            app.step()
            if app.state is AppState.TERMINAL:
                return

    def test_frame_uses_rle_layers_and_a_cached_hud_overlay(self) -> None:
        from greia_platform.pygame_blit import is_rle

        app = self.make_app()
        app.render()
        hud = app.controls.hud
        composed = hud.compositions
        self.now[0] += 0.05
        app.step()
        app.render()
        self.assertEqual(hud.compositions, composed, "a still HUD is not re-composed every frame")
        app.hold(go=True)
        self.advance(app, 0.2)
        app.render()
        self.assertGreater(hud.compositions, composed, "a held pedal re-composes the HUD")
        ride = app.ride
        assert ride is not None
        backdrop = app.art.backdrop(ride.layout.spec.biome)
        for layer in (backdrop.far, backdrop.mid):
            if layer is not None:
                self.assertTrue(is_rle(layer[0]))
        self.assertTrue(is_rle(app.art.chunk(ride.layout, 0).surface))
        self.assertTrue(is_rle(app.art.vehicle("happy", 0.2)))
        app.controls.place(ControlLayout.for_canvas(app.canvas, app.screen.get_size()))
        before = hud.compositions
        app.render()
        self.assertGreater(hud.compositions, before, "a re-layout invalidates the cached HUD")

    def test_app_plays_a_whole_set_to_the_completion_scene_and_restarts(self) -> None:
        app = self.make_app()
        self.assertIs(app.state, AppState.READY)
        app.render()
        self.drive_smartly(app, 300.0)
        self.assertIs(app.state, AppState.TERMINAL)
        courses = [entry for entry in self.events.log if entry[0] == "course"]
        sets = [entry for entry in self.events.log if entry[0] == "set"]
        self.assertEqual([entry[2]["course"] for entry in courses], [1, 2, 3, 4, 5])
        self.assertEqual(len(sets), 1)
        self.assertEqual(sets[0][2]["courses"], COURSES_PER_SET)
        saved = self.store.progress
        self.assertEqual((saved.sets, saved.courses), (1, COURSES_PER_SET))
        self.assertEqual(saved.total_stars, COURSES_PER_SET * STARS_PER_COURSE)
        self.assertEqual(saved.rung, 2)  # a smooth set climbs one rung
        app.render()
        # The completion overlay takes Enter (kit focus) and starts a new set.
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        app.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))
        self.assertIs(app.state, AppState.READY)
        self.assertEqual(app.course_set.index, 0)
        self.assertEqual(app.course_set.rung, 2)

    def test_tumble_is_kind_and_demonstrates_the_brake(self) -> None:
        app = self.make_app()
        app.course_set.index = 3
        app._begin_course()
        app.hold(go=True)
        for _ in range(30 * 20):
            self.advance(app, 1 / 30)
            if app.state is AppState.TUMBLE:
                break
        self.assertIs(app.state, AppState.TUMBLE)
        self.assertEqual(app.driver.feedback.pose.value, "think")
        self.assertEqual(app.audio.last_effect, "boing")
        self.advance(app, 1.6, render=True)
        self.assertIs(app.state, AppState.DRIVING)
        self.assertEqual(app._hinted_drop, 0)
        self.assertIsNotNone(app.motion.sign_hint)
        self.assertGreater(app._brake_hint(self.now[0]), 0.0)
        self.assertFalse(app.drive.go)  # the child presses GO again

    def test_pointer_holds_pedals_and_ignores_the_protected_region(self) -> None:
        app = self.make_app()
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(8, 8)))
        self.assertIs(app.state, AppState.READY)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=GO_RECT.center))
        self.assertTrue(app.drive.go)
        self.assertIs(app.state, AppState.DRIVING)
        self.advance(app, 1.0)
        self.assertGreater(app.ride.vehicle.vx, 100.0)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=GO_RECT.center))
        self.assertFalse(app.drive.go)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=BRAKE_RECT.center))
        self.assertTrue(app.drive.brake)

    def test_keyboard_starts_and_idle_hint_points(self) -> None:
        app = self.make_app()
        self.advance(app, 6.5)
        self.assertTrue(app.driver.pointing)
        self.assertGreater(app._go_hint(self.now[0]), 0.0)
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertIs(app.state, AppState.DRIVING)

    def test_controls_stay_clear_of_protected_chrome_at_every_size(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            app = self.make_app(size)
            layout = ControlLayout.for_canvas(app.canvas, size)
            controls = app.controls
            for control in (controls.progress, controls.road, controls.stars, controls.listen, controls.go, controls.brake):
                self.assertFalse(layout.overlaps_chrome(control.rect), f"{control.control_id} at {size}")
                self.assertTrue(pygame.Rect(0, 0, REFERENCE_WIDTH, REFERENCE_HEIGHT).contains(control.rect))
            app.render()
            app.canvas.present()

    def test_caches_stay_bounded_through_a_course(self) -> None:
        art = CollineArt()
        app = self.make_app()
        app.art = art
        app.renderer._art = art
        art.begin_course(app.ride.layout)
        app.hold(go=True)
        for _ in range(30 * 25):
            self.advance(app, 1 / 30)
            app.render()
        self.assertLessEqual(len(art._chunks), 10)
        self.assertLessEqual(len(art._rotated), 48)
        self.assertLessEqual(len(app.motion.fx), 16)

    def test_existing_distance_save_loads_and_is_kept(self) -> None:
        legacy = parse_progress({"best_distance": 512.0, "total_stars": 7, "timestamp": 3.0})
        app = self.make_app(progress=legacy)
        self.drive_smartly(app, 40.0)
        self.assertGreaterEqual(self.store.progress.total_stars, 7 + STARS_PER_COURSE)
        self.assertAlmostEqual(self.store.progress.best_distance, 512.0)


class AudioTests(unittest.TestCase):
    def test_audio_is_fail_soft_and_uses_titos_approved_cues(self) -> None:
        audio = CollineAudio(locale="it")
        self.assertIn("ready.go", audio.cues)
        for effect in ("star", "flag", "boing", "whoosh", "thump", "fanfare", "sparkle", "missing"):
            audio.play(effect)
        audio.say("ready.go")
        audio.say("no.such.cue")
        audio.stop_all()


if __name__ == "__main__":
    unittest.main()
