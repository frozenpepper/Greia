"""Tests for La Corsa delle Bacche (manifest, garden rules, saves, app loop)."""

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
ACTIVITY_ROOT = ROOT / "activities" / "corsa_bacche"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import tomllib  # noqa: E402

from corsa_content import (  # noqa: E402
    GARDENS_PER_VISIT,
    MAX_LEVEL,
    RUNGS,
    CritterKind,
    CritterSpec,
    RungSpec,
)
from corsa_model import (  # noqa: E402
    DOWN,
    LEFT,
    RIGHT,
    UP,
    CorsaProgress,
    Garden,
    GardenEventKind,
    GardenLayout,
    GardenSummary,
    StepResult,
    Visit,
    bfs_path,
    distances,
    next_level,
)
from corsa_services import (  # noqa: E402
    SCHEMA_VERSION,
    STORAGE_KEY,
    GreiaCorsaEvents,
    GreiaCorsaProgress,
    progress_from_payload,
    progress_payload,
)

LOCALES = ("en", "it", "es", "fr")
_KEYS = {UP: pygame.K_UP, DOWN: pygame.K_DOWN, LEFT: pygame.K_LEFT, RIGHT: pygame.K_RIGHT}

# 3x2 garden with a junction at (0,1) and (1,1) and dead ends at the right.
JUNCTION = (
    "#######",
    "#M . .#",
    "# # ###",
    "#. . .#",
    "#######",
)
# 2x2 garden that is one bent corridor (no junction).
BEND = (
    "#####",
    "#M .#",
    "### #",
    "#. .#",
    "#####",
)
CORRIDOR_LADYBIRD = (
    "#########",
    "#M . . L#",
    "#########",
)
CORRIDOR_HEDGEHOG = (
    "###########",
    "#M . H . .#",
    "###########",
)


def _garden(lattice, critters=(), seed: int = 1) -> Garden:
    layout = GardenLayout.parse(1, lattice)
    return Garden(layout, RungSpec(1, tuple(lattice), tuple(critters)), random.Random(seed))


def _run(garden: Garden, seconds: float, step: float = 1 / 30) -> list:
    events = []
    for _ in range(max(1, int(seconds / step))):
        events.extend(garden.update(step))
    return events


class _Storage:
    def __init__(self, value=None) -> None:
        self.values = {} if value is None else {STORAGE_KEY: value}

    def kv_get(self, key, default=None):
        return self.values.get(key, default)

    def kv_set(self, key, value) -> None:
        self.values[key] = json.loads(json.dumps(value))


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.sounds: list[str] = []

    def say(self, cue: str) -> None:
        self.spoken.append(cue)

    def play(self, name: str) -> None:
        self.sounds.append(name)


class _Events:
    def __init__(self) -> None:
        self.gardens: list[tuple] = []
        self.visits: list[tuple] = []

    def garden_cleared(self, *args) -> None:
        self.gardens.append(args)

    def visit_completed(self, *args) -> None:
        self.visits.append(args)


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_berry_chase_loop(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.corsa-bacche")
        self.assertEqual(data["activity"]["version"], "0.2.0")
        self.assertEqual(set(data["activity"]["languages"]), {"it", "en"})  # ES/FR stay staged
        self.assertEqual(data["input"]["profile"], "directional")
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 7))
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, MAX_LEVEL))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertIn("inhibition_control", education["categories"])
        events = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(events, {"berries.garden_cleared": "milestone", "berries.visit_completed": "completion"})
        self.assertEqual(data["storage"]["schema_version"], 1)

    def test_four_locale_parity_without_emoji_or_retired_text_banners(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in LOCALES
        }
        keys = set(bundles["en"]["strings"])
        self.assertEqual(keys, {"activity.title", "activity.corsa_bacche.title", "victory.title", "btn.play_again"})
        for locale, bundle in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(bundle["strings"]), keys)
                for value in bundle["strings"].values():
                    self.assertTrue(value.strip())
                    self.assertTrue(all(ord(ch) < 0x2000 for ch in value), value)
        self.assertEqual(bundles["es"]["audio"], {})
        self.assertEqual(bundles["fr"]["audio"], {})

    def test_no_private_cast_redraw_hearts_or_emoji_remain(self) -> None:
        source = "\n".join(path.read_text(encoding="utf-8") for path in ACTIVITY_ROOT.glob("*.py"))
        for retired in ("COLOR_MOMO", "BAFFO", "hearts", "RAINBOW_STAR", "apple_munch", "🍓", "✨", "msg.oops"):
            self.assertNotIn(retired, source)
        self.assertIn('CastFeedback(\n                "momo"', source)
        self.assertIn('character="momo"', source)
        self.assertIn("CompletionScene(self.kit", source)
        icon = ACTIVITY_ROOT / "assets" / "source" / "icon.svg"
        self.assertTrue(icon.is_file())
        self.assertIn("momo", icon.read_text(encoding="utf-8"))


class LadderTests(unittest.TestCase):
    def test_every_rung_and_mirror_is_small_readable_and_fully_reachable(self) -> None:
        previous_cells = 0
        expected_berries = (8, 10, 12, 14, 16, 18)
        for spec, berries in zip(RUNGS, expected_berries):
            base = GardenLayout.parse(spec.level, spec.lattice)
            self.assertEqual(len(base.berries), berries, spec.level)
            self.assertGreaterEqual(base.rows * base.cols, previous_cells)
            previous_cells = base.rows * base.cols
            self.assertEqual({kind for kind, _ in base.critters}, {c.kind for c in spec.critters})
            for horizontal in (False, True):
                for vertical in (False, True):
                    layout = base.mirrored(horizontal, vertical)
                    with self.subTest(level=spec.level, h=horizontal, v=vertical):
                        reach = distances(layout, layout.start)
                        self.assertEqual(len(reach), layout.rows * layout.cols)
                        self.assertEqual(len(layout.berries), berries)
                        for _, cell in layout.critters:
                            self.assertGreaterEqual(reach[cell], 2)  # never next to Momo at the start

    def test_no_critters_at_the_youngest_rung_and_they_get_quicker(self) -> None:
        self.assertEqual(RUNGS[0].critters, ())
        fastest = [max((c.speed for c in spec.critters), default=0.0) for spec in RUNGS]
        self.assertEqual(fastest, sorted(fastest))
        self.assertTrue(all(c.follow == 0 for spec in RUNGS[:4] for c in spec.critters))
        self.assertGreater(max(c.follow for c in RUNGS[-1].critters), 0)

    def test_next_garden_rung_follows_how_the_last_one_went(self) -> None:
        self.assertEqual(next_level(2, GardenSummary(2)), 3)
        self.assertEqual(next_level(MAX_LEVEL, GardenSummary(MAX_LEVEL)), MAX_LEVEL)
        self.assertEqual(next_level(3, GardenSummary(3, bumps=2)), 3)
        self.assertEqual(next_level(3, GardenSummary(3, bumps=4)), 2)
        self.assertEqual(next_level(3, GardenSummary(3, hints=2)), 2)
        self.assertEqual(next_level(1, GardenSummary(1, hints=5)), 1)


class MovementTests(unittest.TestCase):
    def test_momo_stops_at_junctions_and_dead_ends_and_bumps_hedges_softly(self) -> None:
        garden = _garden(JUNCTION)
        self.assertIs(garden.steer(RIGHT), StepResult.MOVED)
        _run(garden, 1.0)
        self.assertEqual(garden.momo.cell, (0, 1))  # a junction: the child chooses
        self.assertFalse(garden.momo.moving)
        garden.steer(RIGHT)
        _run(garden, 1.0)
        self.assertEqual(garden.momo.cell, (0, 2))
        self.assertIs(garden.steer(DOWN), StepResult.BLOCKED)
        self.assertEqual(garden.summary.walls, 1)

    def test_momo_follows_bends_and_holding_keeps_him_going(self) -> None:
        garden = _garden(BEND)
        garden.steer(RIGHT)
        _run(garden, 2.0)
        self.assertEqual(garden.momo.cell, (1, 0))  # around the bend to the dead end
        held = _garden(JUNCTION)
        held.hold(RIGHT)
        held.steer(RIGHT)
        _run(held, 1.5)
        self.assertEqual(held.momo.cell, (0, 2))  # held through the junction

    def test_turn_around_is_instant_and_a_sideways_press_is_buffered(self) -> None:
        garden = _garden(JUNCTION)
        garden.steer(RIGHT)
        _run(garden, 0.1)
        self.assertEqual(garden.steer(LEFT), StepResult.MOVED)
        self.assertEqual(garden.momo.heading, LEFT)
        _run(garden, 0.2)
        self.assertEqual(garden.momo.cell, (0, 0))  # back home at once (then round the bend)
        garden = _garden(JUNCTION)
        garden.steer(RIGHT)
        _run(garden, 0.05)
        self.assertIs(garden.steer(DOWN), StepResult.QUEUED)
        _run(garden, 1.5)
        self.assertEqual(garden.momo.cell, (1, 1))

    def test_tap_to_go_walks_the_shortest_path_and_picks_berries_on_the_way(self) -> None:
        garden = _garden(JUNCTION)
        self.assertTrue(garden.go_to((1, 2)))
        self.assertEqual(list(garden.path), bfs_path(garden.layout, (0, 0), (1, 2))[1:])
        events = _run(garden, 3.0)
        self.assertEqual(garden.momo.cell, (1, 2))
        self.assertGreaterEqual([e.kind for e in events].count(GardenEventKind.BERRY), 2)
        self.assertFalse(garden.go_to((5, 5)))

    def test_the_last_berry_clears_the_garden(self) -> None:
        garden = _garden(BEND)
        garden.steer(RIGHT)
        events = _run(garden, 3.0)
        kinds = [e.kind for e in events]
        self.assertEqual(kinds.count(GardenEventKind.BERRY), 3)
        self.assertEqual(kinds[-1], GardenEventKind.CLEARED)
        self.assertTrue(garden.cleared)
        self.assertEqual(garden.update(0.1), [])


class CritterTests(unittest.TestCase):
    LADYBIRD = CritterSpec(CritterKind.LADYBIRD, speed=1.0)
    HEDGEHOG = CritterSpec(CritterKind.HEDGEHOG, speed=1.0, awake_seconds=50.0, nap_seconds=50.0)

    def test_walking_into_an_awake_critter_is_a_gentle_bounce_back(self) -> None:
        garden = _garden(CORRIDOR_LADYBIRD, (self.LADYBIRD,))
        garden.critters[0].pause = 0.0
        garden.steer(RIGHT)
        events = _run(garden, 2.0)
        bumps = [e for e in events if e.kind is GardenEventKind.BUMP]
        self.assertEqual(len(bumps), 1)
        self.assertEqual(garden.summary.bumps, 1)
        self.assertEqual(garden.momo.cell, (0, 1))  # bounced back to the cell he came from
        self.assertEqual(garden.collected, 1)  # the berry he had stays in the basket
        self.assertFalse(garden.cleared)

    def test_standing_still_is_always_safe(self) -> None:
        garden = _garden(CORRIDOR_LADYBIRD, (self.LADYBIRD,))
        garden.critters[0].pause = 0.0
        _run(garden, 8.0)
        self.assertEqual(garden.summary.bumps, 0)
        self.assertEqual(garden.momo.cell, (0, 0))
        # A critter already heading into a still Momo turns around ("boop").
        critter = garden.critters[0]
        critter.walker.cell, critter.walker.target, critter.walker.t = (0, 1), (0, 0), 0.5
        critter.heading, critter.pause, critter.cooldown = LEFT, 0.0, 0.0
        events = garden.update(1 / 60)
        self.assertIn(GardenEventKind.BOOP, [e.kind for e in events])
        self.assertEqual(critter.heading, RIGHT)
        self.assertEqual(garden.summary.bumps, 0)

    def test_a_sleeping_hedgehog_can_be_passed(self) -> None:
        garden = _garden(CORRIDOR_HEDGEHOG, (self.HEDGEHOG,))
        self.assertTrue(garden.critters[0].asleep)
        garden.steer(RIGHT)
        events = _run(garden, 4.0)
        self.assertEqual(garden.summary.bumps, 0)
        self.assertTrue(garden.cleared)
        self.assertIn(GardenEventKind.CLEARED, [e.kind for e in events])

    def test_a_tapped_path_waits_in_front_of_an_awake_critter(self) -> None:
        garden = _garden(CORRIDOR_LADYBIRD, (self.LADYBIRD,))
        garden.critters[0].pause = 100.0  # stays put for the test
        garden.critters[0].walker.cell = (0, 2)
        self.assertTrue(garden.go_to((0, 3)))
        events = _run(garden, 2.0)
        waits = [e for e in events if e.kind is GardenEventKind.WAIT]
        self.assertEqual(len(waits), 1)
        self.assertEqual(garden.momo.cell, (0, 0))
        self.assertEqual(garden.summary.bumps, 0)
        self.assertEqual(garden.summary.waits, 1)
        self.assertEqual(garden.path, ())

    def test_hedgehogs_nap_and_wake_on_their_rhythm(self) -> None:
        spec = CritterSpec(CritterKind.HEDGEHOG, speed=1.0, awake_seconds=1.0, nap_seconds=1.0)
        garden = _garden(CORRIDOR_HEDGEHOG, (spec,))
        events = _run(garden, 6.0)
        kinds = [e.kind for e in events]
        self.assertIn(GardenEventKind.WAKE, kinds)
        self.assertIn(GardenEventKind.NAP, kinds)


class SaveTests(unittest.TestCase):
    def test_progress_round_trips_and_junk_starts_fresh(self) -> None:
        progress = CorsaProgress(level=4, gardens_cleared=7, visits_completed=2, berries=90)
        storage = _Storage()
        port = GreiaCorsaProgress(storage)
        port.save(progress)
        self.assertEqual(storage.values[STORAGE_KEY]["schema_version"], SCHEMA_VERSION)
        self.assertEqual(port.load(), progress)
        for junk in (None, [], {"level": 3}, {"schema_version": 1, "level": True}, {"schema_version": 1, "level": 99}):
            with self.subTest(junk=junk):
                self.assertEqual(progress_from_payload(junk).level, 1)
        bad_counts = progress_from_payload({"schema_version": 1, "level": 2, "berries": -4, "gardens_cleared": "x"})
        self.assertEqual((bad_counts.level, bad_counts.berries, bad_counts.gardens_cleared), (2, 0, 0))
        self.assertEqual(progress_payload(CorsaProgress(level=50))["level"], MAX_LEVEL)

    def test_event_keys_are_scoped_per_visit_and_garden(self) -> None:
        import corsa_services

        calls = []
        original = corsa_services.emit_activity_event
        corsa_services.emit_activity_event = lambda event_id, payload, idempotency_key: calls.append(
            (event_id, payload, idempotency_key)
        )
        try:
            events = GreiaCorsaEvents()
            events.garden_cleared("v1", 2, GardenSummary(3, berries=12, bumps=1))
            events.visit_completed("v1", 3, 4)
        finally:
            corsa_services.emit_activity_event = original
        self.assertEqual(calls[0][0], "berries.garden_cleared")
        self.assertEqual(calls[0][2], "corsa-bacche:v1:g2")
        self.assertEqual(calls[0][1]["berries"], 12)
        self.assertEqual(calls[1], ("berries.visit_completed", {"gardens": 3, "level": 4}, "corsa-bacche:v1"))


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def _app(self, level: int = 1, size: tuple[int, int] = (1024, 600), seed: int = 3, storage=None, locale: str = "en"):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from corsa_app import CorsaActivity

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = storage if storage is not None else _Storage()
        progress = GreiaCorsaProgress(storage)
        loaded = progress.load()
        loaded.level = level
        app = CorsaActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            visit=Visit(loaded, random.Random(seed)),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_ROOT, requested_locale=locale),
            audio=_Audio(),
            progress=progress,
            events=_Events(),
            clock=lambda: now[0],
        )
        return app, now, storage

    @staticmethod
    def _advance(app, now, seconds: float, step: float = 1 / 30) -> None:
        for _ in range(max(1, int(seconds / step))):
            now[0] += step
            app.step(step)

    def _clear_with_keys(self, app, now) -> None:
        """Steer Momo with arrow keys towards the nearest berry until the basket is full."""

        from corsa_app import AppState

        garden = app.garden
        for _ in range(4000):
            if garden.cleared or app.state is not AppState.PLAYING:
                break
            if garden.momo.moving or garden.bouncing:
                self._advance(app, now, 1 / 30)
                continue
            route = garden.hint_route(avoid_critters=True)
            step = (route[1][0] - route[0][0], route[1][1] - route[0][1])
            app.press(_KEYS[step])
            self._advance(app, now, 1 / 30)
        self.assertTrue(garden.cleared)

    def test_keyboard_plays_a_whole_visit_to_the_completion_scene_and_replays(self) -> None:
        from corsa_app import AppState

        for level in (1, 4, 6):
            app, now, storage = self._app(level=level)
            first_visit = app._visit_id
            for index in range(GARDENS_PER_VISIT):
                self.assertEqual(app.controls.progress.current, index)
                self._clear_with_keys(app, now)
                self.assertIn("cleared", app.audio.spoken)
                app.render()
                self._advance(app, now, 2.2)
            self.assertIs(app.state, AppState.TERMINAL)
            self.assertEqual(len(app.events.gardens), GARDENS_PER_VISIT)
            self.assertEqual(len(app.events.visits), 1)
            self.assertIn("complete", app.audio.spoken)
            saved = storage.values[STORAGE_KEY]
            self.assertEqual((saved["gardens_cleared"], saved["visits_completed"]), (GARDENS_PER_VISIT, 1))
            self.assertGreater(saved["berries"], 0)
            app.render()
            self.assertTrue(app.tap(app.canvas.mapper.point(*app.completion.primary_rect.center)))
            self.assertIs(app.state, AppState.PLAYING)
            self.assertEqual(app.visit.completed, 0)
            self.assertNotEqual(app._visit_id, first_visit)  # fresh idempotency scope
            self._clear_with_keys(app, now)

    def test_space_on_completion_replays_through_kit_focus(self) -> None:
        from corsa_app import AppState

        app, now, _ = self._app(level=1)
        for _ in range(GARDENS_PER_VISIT):
            self._clear_with_keys(app, now)
            self._advance(app, now, 2.2)
        self.assertIs(app.state, AppState.TERMINAL)
        app.press(pygame.K_SPACE)
        self.assertIs(app.state, AppState.PLAYING)

    def test_a_berry_cheers_and_fills_one_basket_slot(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, now, _ = self._app(level=1)
        garden = app.garden
        icon_before = app.controls.basket.icon
        target = garden.next_berry()
        x, y = app.geometry.center(*target)
        self.assertTrue(app.tap(app.canvas.mapper.point(int(x), int(y))))
        for _ in range(120):
            if garden.collected:
                break
            self._advance(app, now, 1 / 30)
        self.assertEqual(garden.collected, 1)
        self.assertIs(app.cast.feedback.pose, CastPose.CHEER)
        self.assertIn("pop", app.audio.sounds)
        self.assertIsNot(app.controls.basket.icon, icon_before)
        self.assertTrue(app.motion.fx)

    def test_a_bump_thinks_says_try_again_and_then_demonstrates_a_way(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from corsa_model import GardenEvent

        app, now, _ = self._app(level=3, seed=8)
        garden = app.garden
        critter = garden.critters[0]
        for bump in range(2):
            garden.summary.bumps += 1  # the model counts; the app reacts to the event
            app._on_garden_event(GardenEvent(GardenEventKind.BUMP, garden.momo.cell, 0))
        self.assertIs(app.cast.feedback.pose, CastPose.THINK)
        self.assertIn("bump", app.audio.sounds)
        self.assertEqual(app.audio.spoken.count("retry"), 1)  # voice is rate limited
        self.assertIn(0, app.motion.critter_pulses)
        self.assertIsNone(app.motion.trail)
        self._advance(app, now, 0.7)
        self.assertIsNotNone(app.motion.trail)  # demonstration of a way around
        self.assertEqual(app.motion.trail.route[0], garden.momo.resting_cell)
        self.assertTrue(critter is garden.critters[0])

    def test_space_stops_momo_and_hint_button_shows_the_way(self) -> None:
        app, now, _ = self._app(level=2, seed=5)
        garden = app.garden
        direction = garden.layout.open_directions(garden.momo.cell)[0]
        app.press(_KEYS[direction])
        self._advance(app, now, 1 / 30)
        self.assertTrue(garden.momo.moving)
        self.assertTrue(app.press(pygame.K_SPACE))
        self._advance(app, now, 1.0)
        self.assertFalse(garden.momo.moving)
        stopped = garden.momo.cell
        self._advance(app, now, 0.5)
        self.assertEqual(garden.momo.cell, stopped)
        hints = garden.summary.hints
        self.assertTrue(app.tap(app.canvas.mapper.point(*app.controls.hint.rect.center)))
        self.assertEqual(garden.summary.hints, hints + 1)
        self.assertIsNotNone(app.motion.trail)
        self.assertTrue(app.cast.pointing)
        app.tap(app.canvas.mapper.point(*app.controls.hint.rect.center))
        self.assertEqual(garden.summary.hints, hints + 1)  # one hint at a time

    def test_idle_hints_are_graduated(self) -> None:
        app, now, _ = self._app(level=1)
        app.audio.spoken.clear()
        self._advance(app, now, 6.2)
        self.assertTrue(app.cast.pointing)
        self.assertEqual(app.audio.spoken, ["nudge"])
        self.assertIsNone(app.motion.trail)  # first nudge only points and hops a berry
        self.assertTrue(app.motion.pulses)
        self._advance(app, now, 6.2)
        self.assertIsNotNone(app.motion.trail)
        self.assertEqual(app.garden.summary.hints, 1)

    def test_drag_retargets_and_hud_taps_stay_with_the_kit(self) -> None:
        app, now, _ = self._app(level=1)
        garden = app.garden
        far = max(garden.layout.cells(), key=lambda cell: abs(cell[0] - garden.momo.cell[0]) + abs(cell[1] - garden.momo.cell[1]))
        x, y = app.geometry.center(*far)
        start = app.canvas.mapper.point(*[int(v) for v in app.geometry.center(*garden.momo.cell)])
        end = app.canvas.mapper.point(int(x), int(y))
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start, button=1))
        app._handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=end, rel=(1, 1), buttons=(1, 0, 0)))
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=end, button=1))
        self._advance(app, now, 4.0)
        self.assertEqual(garden.momo.cell, far)
        # A protected-chrome tap never reaches gameplay.
        self.assertFalse(app.tap((5, 5)))

    def test_hud_and_garden_stay_clear_of_protected_chrome_at_every_size(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            for level in (1, MAX_LEVEL):
                app, now, _ = self._app(level=level, size=size)
                with self.subTest(size=size, level=level):
                    layout = ControlLayout.for_canvas(app.canvas, size)
                    for control in (app.controls.hint, app.controls.progress, app.controls.basket):
                        self.assertFalse(control.rect.colliderect(layout.protected), control.control_id)
                    self.assertLessEqual(app.controls.basket.rect.right, app.controls.progress.rect.left)
                    garden_rect = app.geometry.rect.inflate(app.geometry.gap, app.geometry.gap)
                    self.assertFalse(garden_rect.colliderect(layout.protected))
                    self.assertGreaterEqual(garden_rect.top, app.controls.bar.bottom)
                    self.assertLessEqual(garden_rect.bottom + app.geometry.depth, 600)
                    if size == (1024, 600):
                        self.assertGreaterEqual(app.geometry.cell, 72)
                    app.render()

    def test_frames_are_blits_only_after_warm_up(self) -> None:
        app, now, _ = self._app(level=4, seed=2)
        app.render()
        self._advance(app, now, 0.5)
        app.render()
        built = app.kit.painter.build_count
        scene = app.scene
        sprites = app.art.sprites(app.geometry.cell)
        for _ in range(60):
            self._advance(app, now, 1 / 30)
            app.render()
        self.assertEqual(app.kit.painter.build_count, built)
        self.assertIs(app.scene, scene)
        self.assertIs(app.art.sprites(app.geometry.cell), sprites)
        self.assertLessEqual(len(app.motion.fx), 12)

    def test_italian_completion_uses_localized_capitals(self) -> None:
        app, now, _ = self._app(level=1, locale="it")
        for _ in range(GARDENS_PER_VISIT):
            self._clear_with_keys(app, now)
            self._advance(app, now, 2.2)
        self.assertEqual(app._text("victory.title", "?"), "CESTINO PIENO!")


if __name__ == "__main__":
    unittest.main()
