"""Tests for Il Volo del Draghetto (Little Dragon's Flight): finite sky courses."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import random
import sys
import tomllib
import unittest
import wave

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for entry in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from activities.volo_draghetto.dragon_app import AppState, DragonFlightActivity
from activities.volo_draghetto.dragon_art import DragonArt, _cut_sprites
from activities.volo_draghetto.dragon_audio import DragonAudio, synth_effects, voice_takes
from activities.volo_draghetto.dragon_controls import course_id_for, look_control_id
from activities.volo_draghetto.dragon_courses import COURSES, LOOKS, course_by_id
from activities.volo_draghetto.dragon_model import (
    CENTER_Y,
    MAX_Y,
    MIN_Y,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    CourseBuilder,
    DragonFlier,
    FlightEventKind,
    FlightInput,
    FlightPhase,
    FlightResult,
    FlightRun,
    RingState,
)
from activities.volo_draghetto.dragon_services import (
    SCHEMA_VERSION,
    STORAGE_KEY,
    FlightProgress,
    GreiaFlightProgress,
    parse_progress,
)
from greia_platform.activity_controls import ControlArt
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "volo_draghetto"
STEP = 1.0 / 30.0


class FakeClock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


class MemoryKV:
    def __init__(self, data: dict | None = None) -> None:
        self.data = dict(data or {})

    def kv_get(self, key, default=None):
        return self.data.get(key, default)

    def kv_set(self, key, value) -> None:
        json.dumps(value)
        self.data[key] = value


class RecordingEvents:
    def __init__(self) -> None:
        self.rings: list[tuple[str, int]] = []
        self.completed: list[tuple[str, dict]] = []

    def ring_passed(self, session_id, course_id, checkpoint) -> None:
        self.rings.append((course_id, checkpoint))

    def course_completed(self, session_id, course_id, payload) -> None:
        self.completed.append((course_id, payload))


def _fly_course(run: FlightRun, *, steer_to_rings: bool, limit_seconds: float = 400.0) -> list:
    events = []
    elapsed = 0.0
    while run.phase is not FlightPhase.DONE and elapsed < limit_seconds:
        steer = FlightInput()
        ring = run.next_ring
        if steer_to_rings and ring is not None:
            steer.drag_y = ring.y
        events.extend(run.update(STEP, steer))
        elapsed += STEP
    return events


class VoloModelTests(unittest.TestCase):
    def test_flier_glides_down_flaps_up_and_stays_in_the_sky(self) -> None:
        flier = DragonFlier(y=CENTER_Y)
        for _ in range(30):
            flier.update(STEP, FlightInput())
        self.assertGreater(flier.y, CENTER_Y)  # gentle glide down
        low = flier.y
        flier.flap()
        for _ in range(20):
            flier.update(STEP, FlightInput())
        self.assertLess(flier.y, low - 30)  # one flap climbs clearly
        for _ in range(300):
            flier.update(STEP, FlightInput(vertical=-1.0))
        self.assertEqual(flier.y, MIN_Y)
        for _ in range(300):
            flier.update(STEP, FlightInput(vertical=1.0))
        self.assertLessEqual(flier.y, MAX_Y)
        self.assertGreater(flier.speed_factor(1.0), 1.0)
        self.assertLess(flier.speed_factor(-1.0), 1.0)

    def test_builder_is_finite_and_seeded(self) -> None:
        spec = COURSES[0]
        first = CourseBuilder(random.Random(4)).build(spec)
        second = CourseBuilder(random.Random(4)).build(spec)
        self.assertEqual(len(first.rings), spec.rings)
        self.assertEqual([(r.x, r.y) for r in first.rings], [(r.x, r.y) for r in second.rings])
        self.assertGreater(first.finish_x, first.rings[-1].x)
        self.assertEqual(first.gems_total, 0)
        islands = CourseBuilder(random.Random(4)).build(course_by_id("islands"))
        self.assertGreater(islands.gems_total, 0)
        for ring in islands.rings:
            self.assertTrue(MIN_Y <= ring.y <= MAX_Y)

    def test_every_course_lasts_about_a_minute_and_ends(self) -> None:
        for spec in COURSES:
            with self.subTest(course=spec.course_id):
                run = FlightRun(CourseBuilder(random.Random(9)).build(spec))
                events = _fly_course(run, steer_to_rings=True)
                self.assertIs(run.phase, FlightPhase.DONE)
                self.assertTrue(45.0 <= run.time <= 100.0, run.time)
                kinds = [e.kind for e in events]
                self.assertEqual(kinds.count(FlightEventKind.RING_PASSED), spec.rings)
                self.assertEqual(kinds.count(FlightEventKind.FINISH), 1)
                self.assertEqual(kinds.count(FlightEventKind.HALFWAY), 1)

    def test_idle_child_still_reaches_the_finish_no_soft_lock(self) -> None:
        run = FlightRun(CourseBuilder(random.Random(2)).build(COURSES[3]))
        events = _fly_course(run, steer_to_rings=False)
        self.assertIs(run.phase, FlightPhase.DONE)
        self.assertEqual(run.rings_passed, COURSES[3].rings)
        self.assertGreaterEqual(run.result.earned, 1)
        self.assertIn(FlightEventKind.RING_MISSED, [e.kind for e in events])

    def test_missed_ring_hops_ahead_nearer_and_wider_with_a_star_trail(self) -> None:
        course = CourseBuilder(random.Random(1)).build(COURSES[1])
        run = FlightRun(course)
        ring = course.rings[0]
        ring.y = MIN_Y + 40
        run.flier.y = MAX_Y
        old_x, old_open = ring.x, ring.half_open
        later_cloud_x = [c.x for c in course.clouds if c.x > old_x]
        finish = course.finish_x
        pickups_before = len(course.pickups)
        run.distance = old_x - 2.0
        missed = []
        for _ in range(10):
            missed += [e for e in run.update(STEP, FlightInput(vertical=1.0)) if e.kind is FlightEventKind.RING_MISSED]
            if missed:
                break
        self.assertEqual(len(missed), 1)
        self.assertIs(ring.state, RingState.WAITING)
        self.assertGreater(ring.x, old_x)
        self.assertGreater(ring.y, MIN_Y + 40)  # moved towards the dragon
        self.assertGreater(ring.half_open, old_open)
        self.assertGreater(course.finish_x, finish)
        self.assertEqual([c.x for c in course.clouds if c.x > ring.x - 1000], [x + (ring.x - old_x) for x in later_cloud_x])
        self.assertEqual(len(course.pickups), pickups_before + 4)
        self.assertEqual(run.misses, 1)

    def test_clouds_bounce_and_never_end_the_flight(self) -> None:
        course = CourseBuilder(random.Random(3)).build(COURSES[2])
        run = FlightRun(course)
        cloud = course.clouds[0]
        run.distance = cloud.x - 1.0
        run.flier.y = cloud.y - 5.0
        events = run.update(STEP, FlightInput())
        self.assertIn(FlightEventKind.BUMP, [e.kind for e in events])
        self.assertLess(run.flier.vy, 0.0)  # pushed up, away from the cloud
        self.assertIs(run.phase, FlightPhase.FLYING)

    def test_result_stars(self) -> None:
        self.assertEqual(FlightResult("x", 10, 10, 2, 2, 0).earned, 3)
        self.assertEqual(FlightResult("x", 8, 10, 1, 2, 0).earned, 2)
        self.assertEqual(FlightResult("x", 0, 10, 0, 2, 3).earned, 1)


class VoloServicesTests(unittest.TestCase):
    def test_endless_flight_save_migrates_without_losing_stars(self) -> None:
        store = MemoryKV({STORAGE_KEY: {"score": 420, "stars": 37, "timestamp": 1.0}})
        port = GreiaFlightProgress(store)
        progress = port.load()
        self.assertEqual(progress.lifetime_stars, 37)
        self.assertEqual(progress.legacy_score, 420)
        self.assertEqual(progress.best, {})
        port.save(progress)
        saved = store.data[STORAGE_KEY]
        self.assertEqual(saved["schema_version"], SCHEMA_VERSION)
        self.assertEqual(saved["lifetime_stars"], 37)
        self.assertEqual(saved["legacy_score"], 420)

    def test_progress_round_trip_unlocks_and_sanitises(self) -> None:
        progress = FlightProgress()
        self.assertTrue(progress.is_unlocked(0))
        self.assertFalse(progress.is_unlocked(1))
        self.assertFalse(progress.look_unlocked("crown"))
        self.assertTrue(progress.record("morning", 2, 30, 0))
        self.assertTrue(progress.is_unlocked(1))
        self.assertTrue(progress.look_unlocked("crown"))
        self.assertEqual(progress.first_open_course(), 1)
        progress.look = "crown"
        again = parse_progress(json.loads(json.dumps(progress.to_payload())))
        self.assertEqual(again.best, {"morning": 2})
        self.assertEqual(again.look, "crown")
        bad = parse_progress({"schema_version": 3, "best": {"morning": 9, "nope": 1}, "look": "top_hat", "lifetime_stars": -4})
        self.assertEqual(bad.best, {})
        self.assertEqual(bad.look, "none")  # locked looks fall back
        self.assertEqual(bad.lifetime_stars, 0)
        self.assertEqual(parse_progress("garbage").best, {})


class VoloAssetsAndLocaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def test_manifest_matches_the_finite_directional_game(self) -> None:
        data = tomllib.loads((ACTIVITY_DIR / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.volo-draghetto")
        self.assertEqual(data["input"]["profile"], "directional")
        self.assertEqual((data["education"]["recommended_age_min"], data["education"]["recommended_age_max"]), (4, 7))
        self.assertEqual(
            {(e["id"], e["kind"]) for e in data["education"]["events"]},
            {("flight.ring_passed", "milestone"), ("flight.course_completed", "completion")},
        )
        self.assertEqual(set(data["activity"]["languages"]), {"it", "en"})

    def test_four_locales_share_keys_used_by_the_app(self) -> None:
        used = {"activity.title", "victory.title", "victory.subtitle", "victory.new_look", "button.fly_again", "button.next"}
        for locale in ("en", "it", "es", "fr"):
            with self.subTest(locale=locale):
                strings = json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
                self.assertEqual(set(strings), used)
                self.assertTrue(all(value.strip() for value in strings.values()))

    def test_private_renditions_exist_beside_their_sources(self) -> None:
        for name in ("dragon_fly_up", "dragon_fly_mid", "dragon_fly_down", "ring_back", "ring_front", "sky_island"):
            self.assertTrue((ACTIVITY_DIR / "assets" / "source" / f"{name}.svg").is_file(), name)
            self.assertTrue((ACTIVITY_DIR / "assets" / "runtime" / f"{name}.png").is_file(), name)

    def test_art_is_cached_and_sized(self) -> None:
        art = DragonArt(ControlArt())
        frames = art.dragon_frames("crown", 150)
        self.assertEqual(len(frames), 3)
        self.assertTrue(all(frame.get_size() == (150, 150) for frame in frames))
        self.assertIs(art.dragon_frames("crown", 150), frames)
        back, front = art.ring(84.0)
        self.assertEqual(back.get_size(), front.get_size())
        self.assertGreater(back.get_height(), 2 * 84)
        for spec in COURSES:
            self.assertEqual(art.backdrop(spec).get_size(), (REFERENCE_WIDTH, REFERENCE_HEIGHT))
        for look in LOOKS:
            self.assertIsNotNone(art.look_icon(look.look_id, 56), look.look_id)
        self.assertIsNotNone(art.star())
        self.assertIsNotNone(art.gem())

    def test_parallax_sprites_skip_clouds_cut_by_the_edge(self) -> None:
        layer = pygame.Surface((200, 100), pygame.SRCALPHA)
        pygame.draw.circle(layer, (255, 255, 255, 255), (100, 50), 20)
        pygame.draw.circle(layer, (255, 255, 255, 255), (0, 50), 20)
        sprites = _cut_sprites(layer)
        self.assertEqual(len(sprites), 1)
        self.assertEqual(sprites[0][1], 80)

    def test_sounds_and_approved_voice_takes(self) -> None:
        for name, data in synth_effects().items():
            with wave.open(io.BytesIO(data)) as handle:
                self.assertGreater(handle.getnframes(), 0, name)
        for locale in ("en", "it"):
            takes = voice_takes(PROJECT_ROOT, "celebrate.success", locale)
            self.assertTrue(takes, locale)
            self.assertTrue(all(f"__{locale}__" in path.name for path in takes))
        audio = DragonAudio("en")
        audio.play("flap")
        audio.say("ready.go")
        self.assertEqual(audio.last_speech, "ready.go")


class VoloAppLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        self.clock = FakeClock()
        self.store = MemoryKV()
        self.events = RecordingEvents()
        self.app = self._make()

    def _make(self) -> DragonFlightActivity:
        return DragonFlightActivity(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_DIR, requested_locale="en"),
            progress=GreiaFlightProgress(self.store),
            events=self.events,
            audio=DragonAudio("en"),
            rng=random.Random(11),
            session_id="test-1",
            clock=self.clock,
        )

    def _key(self, key: int, down: bool) -> None:
        kind = pygame.KEYDOWN if down else pygame.KEYUP
        self.app.handle_event(pygame.event.Event(kind, key=key, mod=0, unicode=""))

    def _tick(self) -> None:
        self.clock.t += STEP
        self.app.step(STEP)

    def test_map_starts_only_unlocked_courses(self) -> None:
        app = self.app
        self.assertIs(app.state, AppState.MAP)
        locked = app.map.layer.target(course_id_for(1))
        self.assertFalse(locked.enabled)
        app._on_course(1)
        self.assertIs(app.state, AppState.MAP)
        self.assertFalse(app.map.layer.target(look_control_id("crown")).enabled)
        # Keyboard: the first open course has focus; Space starts it.
        self.assertTrue(app.press(pygame.K_SPACE))
        self.assertIs(app.state, AppState.FLIGHT)
        self.assertEqual(app.course_index, 0)

    def test_tapping_a_course_card_starts_it_and_protected_corner_is_ignored(self) -> None:
        app = self.app
        self.assertFalse(app.tap((20, 20)))  # Home/Back region
        self.assertIs(app.state, AppState.MAP)
        card = app.map.courses[0].rect
        self.assertTrue(app.tap(card.center))
        self.assertIs(app.state, AppState.FLIGHT)

    def test_hover_never_moves_the_dragon_tap_flaps(self) -> None:
        app = self.app
        app.start_course(0)
        y0 = app.run.flier.y
        app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(600, 120), rel=(0, 0), buttons=(0, 0, 0)))
        self.assertIsNone(app._steer().drag_y)
        self.assertTrue(app.tap((600, 400)))
        for _ in range(10):
            self._tick()
        self.assertLess(app.run.flier.y, y0)
        self.assertFalse(app.tap((20, 20)))  # never gameplay in the chrome corner

    def test_play_a_course_to_the_completion_scene_with_the_keyboard(self) -> None:
        app = self.app
        self.assertTrue(app.press(pygame.K_SPACE))  # start course 1 from the map
        held: int | None = None
        for _ in range(int(150 / STEP)):
            if app.state is not AppState.FLIGHT:
                break
            ring = app.run.next_ring
            want = None
            if ring is not None and abs(app.run.flier.y - ring.y) > 18:
                want = pygame.K_UP if ring.y < app.run.flier.y else pygame.K_DOWN
            if want != held:
                if held is not None:
                    self._key(held, False)
                if want is not None:
                    self._key(want, True)
                held = want
            self._tick()
            app.render()
        self.assertIs(app.state, AppState.COMPLETE)
        self.assertEqual(len(self.events.rings), COURSES[0].rings)
        self.assertEqual(self.events.completed[0][0], "morning")
        saved = self.store.data[STORAGE_KEY]
        self.assertGreaterEqual(saved["best"]["morning"], 1)
        self.assertTrue(app.completion.is_prepared)
        app.render()
        # The shared completion scene: Next goes back to the map with course 2 open.
        app.press(pygame.K_RIGHT)
        self.assertTrue(app.press(pygame.K_SPACE))
        self.assertIs(app.state, AppState.MAP)
        self.assertTrue(app.map.layer.target(course_id_for(1)).enabled)
        self.assertTrue(app.map.layer.target(look_control_id("crown")).enabled)
        app._on_look("crown")
        self.assertEqual(self.store.data[STORAGE_KEY]["look"], "crown")

    def test_keyboard_hint_sits_under_the_flight_band_and_lights_the_pressed_key(self) -> None:
        from greia_platform.activity_controls import ControlLayout
        from greia_platform.activity_keyboard_hint import KeyCap

        try:
            from dragon_model import MAX_Y
        except ImportError:  # pragma: no cover - package import path
            from activities.volo_draghetto.dragon_model import MAX_Y

        app = self.app
        app.start_course(0)
        keys = app.hud.keys
        self.assertTrue(keys.visible, "shown at the start of a flight")
        self.assertEqual(keys.active, {KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
        self.assertGreater(keys.rect.top, MAX_Y + 16, "below every pickup and the dragon's path")
        self.assertGreater(keys.rect.left, REFERENCE_WIDTH // 2, "bottom-right corner")
        self.assertFalse(keys.rect.colliderect(ControlLayout.for_canvas(app.canvas, self.screen.get_size()).protected))
        self.assertGreaterEqual(min(r.height for r in keys.key_rects().values()), 30, "legible keycaps")
        self._key(pygame.K_SPACE, True)
        self.assertIn(KeyCap.SPACE, keys.lit)
        app.render()
        self._key(pygame.K_SPACE, False)
        for _ in range(int(0.5 / STEP)):
            self._tick()
        self.assertNotIn(KeyCap.SPACE, keys.lit)
        keys.hide()
        for _ in range(int(7 / STEP)):
            self._tick()
        self.assertTrue(keys.visible, "the idle hint shows the keys again")
        app.render()

    def test_controller_flap_and_hint_after_idle(self) -> None:
        app = self.app
        app.start_course(0)
        button = getattr(pygame, "CONTROLLERBUTTONDOWN", None)
        if button is not None:
            y0 = app.run.flier.y
            app.handle_event(pygame.event.Event(button, button=getattr(pygame, "CONTROLLER_BUTTON_A", 0), instance_id=0))
            for _ in range(8):
                self._tick()
            self.assertLess(app.run.flier.y, y0)
        for _ in range(int(19 / STEP)):  # back-off: hints at 6 s and 18 s
            self._tick()
        self.assertTrue(app.motion.hint_glyphs)
        self.assertEqual(app.cast.mode, "point")

    def test_idle_hint_reveals_keys_without_lighting_unpressed_ones(self) -> None:
        app = self.app
        app.start_course(0)
        keys = app.hud.keys
        seen_visible = False
        for _ in range(int(19 / STEP)):  # both idle hints fire in this window
            self._tick()
            self.assertEqual(keys.lit, frozenset(), "only keys that are really held light up")
            seen_visible = seen_visible or keys.visible
        self.assertGreaterEqual(app._hints.count, 2)
        self.assertTrue(seen_visible)
        self._key(pygame.K_DOWN, True)
        from greia_platform.activity_keyboard_hint import KeyCap

        self.assertEqual(keys.lit, {KeyCap.DOWN})

    def test_holding_a_steering_key_is_play_not_idleness(self) -> None:
        app = self.app
        app.start_course(0)
        self._key(pygame.K_UP, True)
        for _ in range(int(30 / STEP)):
            self._tick()
        self.assertEqual(app._hints.count, 0, "no idle hint while the child steers")
        self.assertFalse(app.resting)

    def test_dragon_rests_when_the_child_stops_and_flies_on_with_any_input(self) -> None:
        try:
            from dragon_app import REST_AFTER_SECONDS, REST_EASE_SECONDS
        except ImportError:  # pragma: no cover - package import path
            from activities.volo_draghetto.dragon_app import REST_AFTER_SECONDS, REST_EASE_SECONDS

        app = self.app
        app.start_course(0)
        for _ in range(int((REST_AFTER_SECONDS + REST_EASE_SECONDS + 4.0) / STEP)):
            self._tick()
        self.assertTrue(app.resting)
        self.assertFalse(app.flight_moving, "a resting scene lets the frame governor freeze")
        self.assertIs(app.run.phase, FlightPhase.FLYING)
        self.assertTrue(app.hud.keys.visible, "the keycaps show how to fly on")
        distance, misses = app.run.distance, app.run.misses
        pickups = len(app.run.course.pickups)
        for _ in range(int(30 / STEP)):
            self._tick()
        self.assertEqual(app.run.distance, distance)
        self.assertEqual((app.run.misses, len(app.run.course.pickups)), (misses, pickups), "no endless ring retries")
        app.render()
        self._key(pygame.K_SPACE, True)
        self.assertFalse(app.resting)
        self.assertTrue(app.flight_moving)
        self._key(pygame.K_SPACE, False)
        for _ in range(10):
            self._tick()
        self.assertGreater(app.run.distance, distance)

    def test_flight_sprites_are_blitted_from_rle_copies(self) -> None:
        from greia_platform.pygame_blit import is_rle

        app = self.app
        app.start_course(0)
        app.render()
        fast = app.flight_renderer.fast
        self.assertGreater(len(fast), 3)
        finish = app.art.finish_rainbow(900)
        self.assertTrue(is_rle(fast(finish)), "the 900 px finish rainbow is encoded before it scrolls in")
        frames = app.art.dragon_frames(app.progress.look)
        self.assertTrue(is_rle(fast(frames[0])))
        self.assertFalse(is_rle(frames[0]), "the cached source stays drawable")


if __name__ == "__main__":
    unittest.main()
