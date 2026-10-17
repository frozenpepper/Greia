"""Tests for Costruiamo Ponti / Bridge Builders (manifest, authored crossings,
the bridge test, hints, the GO timeline, saves and the real app loop).

The first release's copy-the-icon contract (per-slot answer icons, fixed
``target_x = bridge_end_x + 50`` hop, ``SceneActorDefinition`` Flash, pointer
required) is superseded by the 2026-10-16 rethink; these tests assert the
measuring/engineering loop that replaced it.
"""

from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import sys
import tomllib
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "costruiamo_ponti"
for path in (ROOT / "src", ACTIVITY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ponti_content import (  # noqa: E402
    ALL_CROSSINGS,
    CROSSING_SETS,
    CROSSINGS_PER_SET,
    MAX_TRAY,
    Crossing,
    PieceKind,
    wood,
)
from ponti_layout import BANK_TOP, UNIT, CrossingView  # noqa: E402
from ponti_model import (  # noqa: E402
    SNAP_AFTER_MISSES,
    BridgeState,
    Failure,
    Fit,
    HintAction,
    HintPlanner,
    PontiProgress,
    Visit,
    solve,
)
from ponti_run import BridgeRun, RunPhase  # noqa: E402
from ponti_services import (  # noqa: E402
    SCHEMA_VERSION,
    STORAGE_KEY,
    GreiaPontiEvents,
    GreiaPontiProgress,
    progress_from_payload,
    progress_payload,
)

LOCALES = ("en", "it", "es", "fr")


def _arrangements(crossing: Crossing):
    """Every complete bridge: pillar rocks (if any) x every plank choice per span."""

    pillars = [i for i, p in enumerate(crossing.pieces) if p.kind is PieceKind.PILLAR]
    planks = [i for i, p in enumerate(crossing.pieces) if p.kind is PieceKind.PLANK]
    for count in range(len(pillars) + 1):
        for spots in itertools.combinations(range(len(crossing.spots)), count):
            probe = BridgeState(crossing)
            for pillar, spot in zip(pillars, spots):
                probe.place_pillar(pillar, spot)
            seats = probe.seats()
            for chosen in itertools.permutations(planks, len(seats)):
                state = BridgeState(crossing)
                for pillar, spot in zip(pillars, spots):
                    state.place_pillar(pillar, spot)
                for plank, seat in zip(chosen, seats):
                    state.place_plank(plank, seat)
                yield state


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
        self.speakers: list[str] = []

    def use_speaker(self, speaker: str) -> None:
        self.speakers.append(speaker)

    def say(self, cue: str) -> None:
        self.spoken.append(cue)

    def say_if_quiet(self, cue: str) -> None:
        self.spoken.append(cue)

    def then(self, cue: str) -> None:
        self.spoken.append(cue)

    def play(self, name: str) -> None:
        self.sounds.append(name)


class _Events:
    def __init__(self) -> None:
        self.calls: dict[str, list[tuple]] = {}

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *args: self.calls.setdefault(name, []).append(args)


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_claims_match_the_measuring_loop(self) -> None:
        data = tomllib.loads((ACTIVITY / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.costruiamo-ponti")
        self.assertEqual(data["activity"]["version"], "0.2.0")
        self.assertEqual(set(data["activity"]["languages"]), {"it", "en", "es", "fr"})  # four released languages (owner 2026-10-17)
        self.assertEqual(data["input"]["profile"], "hybrid")
        self.assertEqual(data["requirements"]["required_capabilities"], ["display"])
        self.assertEqual(data["permissions"]["requested"], [])
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (5, 7))
        # A fixed authored ladder: no adaptive range is claimed.
        self.assertNotIn("adaptive_difficulty", education)
        self.assertNotIn("difficulty_min", education)
        self.assertNotIn("difficulty_max", education)
        skills = {skill["id"] for skill in education["skills"]}
        self.assertIn("math.comparison.length_height", skills)
        self.assertIn("math.comparison.weight", skills)
        events = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(
            events,
            {
                "bridge.plank_placed": "milestone",
                "bridge.test_started": "milestone",
                "bridge.level_completed": "completion",  # kept: platform policies count it
                "bridge.crossing_missed": "milestone",
                "bridge.set_completed": "completion",
            },
        )

    def test_four_locale_parity_without_emoji_or_retired_copy(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in LOCALES
        }
        keys = set(bundles["en"]["strings"])
        self.assertEqual(
            keys, {"activity.title", "activity.costruiamo_ponti.title", "btn.go", "btn.play_again", "victory.title"}
        )
        for locale, bundle in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(bundle["strings"]), keys)
                for value in bundle["strings"].values():
                    self.assertTrue(value.strip())
                    self.assertTrue(all(ord(ch) < 0x2000 for ch in value), value)
                    self.assertNotEqual(value, value.upper(), "case comes from the platform policy (ADR 0034)")
        self.assertEqual(bundles["es"]["audio"], {})
        self.assertEqual(bundles["fr"]["audio"], {})
        for locale in ("en", "it"):
            path = bundles[locale]["audio"]["activity.title"]["path"]
            self.assertTrue((ACTIVITY / path).is_file())
        source = "\n".join(path.read_text(encoding="utf-8") for path in ACTIVITY.glob("*.py"))
        for retired in ("block.shroom", "rainbow", "trampoline", "btn.cross", "set_visible(False)", "ui.clear"):
            self.assertNotIn(retired, source)
        self.assertIn("CastFeedback(friend", source)
        self.assertIn("CompletionScene(self.kit", source)
        self.assertFalse((ACTIVITY / "ponti_focus.py").exists())


class AuthoredCrossingTests(unittest.TestCase):
    def test_four_sets_of_four_with_trays_that_fit(self) -> None:
        self.assertEqual(len(CROSSING_SETS), 4)
        for crossing_set in CROSSING_SETS:
            self.assertEqual(len(crossing_set.crossings), CROSSINGS_PER_SET)
        ids = [crossing.crossing_id for crossing in ALL_CROSSINGS]
        self.assertEqual(len(ids), len(set(ids)))
        for crossing in ALL_CROSSINGS:
            self.assertLessEqual(len(crossing.pieces), MAX_TRAY)
            view = CrossingView(crossing)
            self.assertGreater(view.home_x - 60, 0, crossing.crossing_id)
            self.assertLess(view.picnic_x + 100, 1024, crossing.crossing_id)
        # A standing plank never reaches the HUD bar.
        self.assertGreater(BANK_TOP - 4 * UNIT, 92)

    def test_every_crossing_is_solvable_and_needs_a_decision(self) -> None:
        for crossing in ALL_CROSSINGS:
            with self.subTest(crossing=crossing.crossing_id):
                self.assertTrue(solve(crossing))
                self.assertFalse(BridgeState(crossing).evaluate().success)
                outcomes = [state.evaluate().success for state in _arrangements(crossing)]
                self.assertIn(True, outcomes)
                self.assertIn(False, outcomes, "some complete bridge must fail, or there is no decision")

    def test_the_ladder_introduces_one_idea_per_set(self) -> None:
        long_enough, two_rivers, pillars, heavy = CROSSING_SETS
        for crossing in long_enough.crossings:
            self.assertEqual((crossing.islands, crossing.spots, crossing.heavy), ((), (), False))
        for crossing in two_rivers.crossings:
            self.assertTrue(crossing.islands)
            # Using the longest plank first never works: lengths must be matched.
            for solution in solve(crossing):
                self.assertEqual(len(solution.planks), 2)
        for crossing in pillars.crossings:
            self.assertEqual(crossing.pillars, 1)
            longest = max(p.length for p in crossing.pieces if p.kind is PieceKind.PLANK)
            self.assertGreater(crossing.gap, longest, "too wide for any plank: a pillar is needed")
            self.assertTrue(all(solution.pillars for solution in solve(crossing)))
        heavy_ones = [crossing for crossing in heavy.crossings if crossing.heavy]
        self.assertGreaterEqual(len(heavy_ones), 3)
        for crossing in heavy_ones:
            for solution in solve(crossing):
                self.assertTrue(all(signature[2] for _, signature in solution.planks), "heavy loads need stone")
        self.assertIn(False, [crossing.heavy for crossing in heavy.crossings], "stone is not always the answer")


class BridgeStateTests(unittest.TestCase):
    def test_fits_short_long_empty_and_bend(self) -> None:
        crossing = Crossing("t", 3, (wood(2), wood(3), wood(4)), "flash")
        state = BridgeState(crossing)
        self.assertEqual(state.evaluate().failure, Failure.EMPTY)
        state.place_plank(0, "bank")
        result = state.evaluate()
        self.assertEqual((result.failure, result.results[0].fit), (Failure.SHORT, Fit.SHORT))
        state.place_plank(1, "bank")
        self.assertTrue(state.in_tray(0), "a swapped plank goes back to the tray")
        self.assertEqual(state.evaluate().results[0].fit, Fit.JUST_RIGHT)
        state.place_plank(2, "bank")
        self.assertTrue(state.evaluate().success)
        self.assertEqual(state.evaluate().results[0].fit, Fit.LONG)
        heavy = BridgeState(Crossing("h", 3, (wood(3),), "momo", heavy=True))
        heavy.place_plank(0, "bank")
        self.assertEqual(heavy.evaluate().failure, Failure.BEND)

    def test_pillar_splits_the_gap_and_takes_its_plank_back(self) -> None:
        crossing = CROSSING_SETS[2].crossings[2]  # gap 6, rocks at 1 and 3
        state = BridgeState(crossing)
        self.assertEqual([span.width for span in state.spans()], [6])
        self.assertTrue(state.place_pillar(0, 1))
        self.assertEqual([(span.seat, span.width) for span in state.spans()], [("bank", 3), ("spot1", 2)])
        state.place_plank(1, "spot1")
        self.assertTrue(state.place_pillar(0, 0), "the one pillar moves to the other rock")
        self.assertEqual(state.pillar_spots(), [0])
        self.assertTrue(state.in_tray(1), "its plank comes back to the tray")
        state.place_plank(1, "spot0")
        state.remove(0)
        self.assertTrue(state.in_tray(1), "a removed pillar takes its plank back")
        self.assertEqual(state.selected, 0)

    def test_following_hints_always_reaches_a_working_bridge(self) -> None:
        for crossing in ALL_CROSSINGS:
            for start in itertools.islice(_arrangements(crossing), 6):
                with self.subTest(crossing=crossing.crossing_id):
                    for _ in range(10):
                        step = HintPlanner.next_step(start)
                        if step.action is HintAction.GO:
                            break
                        self.assertTrue(HintPlanner.apply(start, step), step)
                    self.assertTrue(start.evaluate().success)


class RunTimelineTests(unittest.TestCase):
    @staticmethod
    def _run(state: BridgeState) -> tuple[BridgeRun, list[str]]:
        run = BridgeRun(state, CrossingView(state.crossing))
        moments: list[str] = []
        for _ in range(400):
            moments += run.advance(1 / 30)
            if run.finished:
                break
        return run, moments

    def test_success_lowers_sparkles_and_arrives_at_the_picnic(self) -> None:
        state = BridgeState(CROSSING_SETS[0].crossings[0])  # gap 2
        state.place_plank(1, "bank")  # just right
        run, moments = self._run(state)
        self.assertIs(run.phase, RunPhase.ARRIVED)
        self.assertEqual(moments[0], "landed")
        self.assertIn("pass:1", moments)
        self.assertEqual(moments[-1], "arrive")
        self.assertEqual(run.angle(), 0.0)
        self.assertEqual(run.traveler_midbottom()[0], run.view.arrive_x)

    def test_short_plank_stops_the_friend_at_the_edge_never_in_the_water(self) -> None:
        state = BridgeState(CROSSING_SETS[0].crossings[1])  # gap 3
        state.place_plank(1, "bank")  # 2: too short
        run, moments = self._run(state)
        self.assertIs(run.phase, RunPhase.STOPPED)
        self.assertEqual(moments[-1], "stop")
        self.assertLess(run.x, run.view.left_x)
        self.assertEqual(run.traveler_midbottom()[1], BANK_TOP + 4)
        run.start_return()
        for _ in range(200):
            if "home" in run.advance(1 / 30):
                break
        self.assertIs(run.phase, RunPhase.HOME)
        self.assertEqual(run.angle(), 90.0)
        self.assertEqual(run.x, run.view.home_x)

    def test_thin_plank_bends_under_a_heavy_friend(self) -> None:
        state = BridgeState(CROSSING_SETS[3].crossings[0])  # heavy, gap 2
        state.place_plank(0, "bank")  # thin wood
        run, moments = self._run(state)
        self.assertIn("bend", moments)
        self.assertIs(run.phase, RunPhase.STOPPED)
        self.assertGreater(run.sag, 10)
        self.assertGreater(run.traveler_midbottom()[1], BANK_TOP - 20 + 4)


class SaveAndEventTests(unittest.TestCase):
    def test_first_release_stars_migrate_and_schema_three_round_trips(self) -> None:
        legacy = progress_from_payload({"stars": 5})
        self.assertEqual((legacy.legacy_stars, legacy.next_set), (5, 0))
        payload = progress_payload(PontiProgress(next_set=2, crossings_solved=9, sets_completed=2, legacy_stars=5))
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["stars"], 5)
        again = progress_from_payload(json.loads(json.dumps(payload)))
        self.assertEqual((again.next_set, again.crossings_solved, again.sets_completed, again.legacy_stars), (2, 9, 2, 5))
        self.assertEqual(progress_from_payload("junk"), PontiProgress())
        self.assertEqual(progress_from_payload({"schema_version": 3, "next_set": 99}).next_set, 99 % 4)

    def test_storage_adapter_uses_the_original_key_and_never_raises(self) -> None:
        storage = _Storage({"stars": 3})
        adapter = GreiaPontiProgress(storage)
        progress = adapter.load()
        self.assertEqual(progress.legacy_stars, 3)
        adapter.save(progress)
        self.assertEqual(storage.values[STORAGE_KEY]["stars"], 3)
        self.assertEqual(STORAGE_KEY, "costruiamo_ponti.progress.v2")

        class Broken:
            def kv_get(self, *args):
                raise OSError("disk")

            def kv_set(self, *args):
                raise OSError("disk")

        broken = GreiaPontiProgress(Broken())
        self.assertEqual(broken.load(), PontiProgress())
        broken.save(PontiProgress())

    def test_event_keys_are_scoped_per_visit(self) -> None:
        sent = []
        with mock.patch("ponti_services.emit_activity_event", lambda *a, **k: sent.append((a, k))):
            events = GreiaPontiEvents()
            events.crossing_completed("v1", "le1", 1)
            events.crossing_completed("v2", "le1", 1)
            events.plank_placed("v1", "le1", 2, False)
        keys = [call[1]["idempotency_key"] for call in sent]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(sent[0][0][0], "bridge.level_completed")


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def _app(self, size=(1024, 600), next_set=0, storage=None, locale="en"):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from ponti_app import BridgeActivity

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = storage if storage is not None else _Storage()
        progress = GreiaPontiProgress(storage)
        loaded = progress.load()
        loaded.next_set = next_set
        app = BridgeActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            visit=Visit(loaded),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY, requested_locale=locale),
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

    def _until(self, app, now, states, limit: float = 12.0) -> None:
        for _ in range(int(limit * 30)):
            if app.state in states:
                return
            self._advance(app, now, 1 / 30)
        self.fail(f"never reached {states}, stuck in {app.state}")

    def test_keycap_hint_shows_at_start_and_lights_only_the_held_key(self) -> None:
        from greia_platform.activity_keyboard_hint import KeyCap

        app, now, _ = self._app()
        keys = app.controls.keys
        self.assertTrue(keys.visible, "shown at the start of a crossing")
        self.assertEqual(keys.lit, frozenset())
        controls = app.controls
        layout_protected = controls.screen.protected
        self.assertFalse(keys.rect.colliderect(layout_protected), "never under Home/Back")
        for other in (controls.hint.rect, controls.progress.rect, controls.go.rect, *(b.rect for b in controls.tray)):
            self.assertFalse(keys.rect.colliderect(other))
        self.assertGreaterEqual(min(r.height for r in keys.key_rects().values()), 28, "legible keycaps")
        app._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode="", scancode=0))
        self.assertEqual(keys.lit, {KeyCap.RIGHT})
        self.assertTrue(app._keys_changed, "a lit key redraws the static build screen")
        app.render()
        self._advance(app, now, 2.0)
        self.assertEqual(keys.lit, {KeyCap.RIGHT}, "lit while held")
        app._handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT, mod=0, unicode="", scancode=0))
        self._advance(app, now, 0.5)
        self.assertEqual(keys.lit, frozenset())
        keys.hide()
        self._advance(app, now, 6.0)  # first idle hint 6 s after the key release
        self.assertTrue(keys.visible, "an idle hint shows the keys again")
        self.assertEqual(keys.lit, frozenset(), "without lighting keys nobody pressed")

    def _key_activate(self, app, control_id: str) -> None:
        self.assertTrue(app.controls.layer.focus(control_id, visible=True), control_id)
        self.assertTrue(app.press(pygame.K_SPACE), control_id)

    def _solve_with_keys(self, app, now) -> None:
        """Build the bridge with keyboard activation only (tray -> span/rock, GO)."""

        from ponti_app import AppState
        from ponti_controls import seat_id, spot_id, tray_id

        bridge = app.bridge
        for _ in range(10):
            step = HintPlanner.next_step(bridge)
            if step.action is HintAction.GO:
                break
            piece = HintPlanner.piece_for(bridge, step)
            if step.action is HintAction.REMOVE_PILLAR:
                self._key_activate(app, spot_id(step.spot))
                continue
            if bridge.in_tray(piece):
                self._key_activate(app, tray_id(piece))
                self.assertEqual(bridge.selected, piece)
            else:
                self._key_activate(app, tray_id(piece))  # call it back first
            if step.action is HintAction.PLACE_PILLAR:
                self._key_activate(app, spot_id(step.spot))
            else:
                self._key_activate(app, seat_id(bridge.seats().index(step.seat)))
        self._key_activate(app, "go")
        self.assertIs(app.state, AppState.RUNNING)
        self._until(app, now, {AppState.CELEBRATE})
        app.render()

    def test_keyboard_plays_every_set_to_the_completion_scene_and_moves_on(self) -> None:
        from ponti_app import AppState

        for next_set in range(len(CROSSING_SETS)):
            app, now, storage = self._app(next_set=next_set)
            first_visit = app._visit_id
            for index in range(CROSSINGS_PER_SET):
                self.assertEqual(app.controls.progress.current, index)
                self._solve_with_keys(app, now)
                self.assertIn("arrive", app.audio.spoken)
                self._advance(app, now, 2.4)
            self.assertIs(app.state, AppState.TERMINAL)
            self.assertEqual(len(app.events.calls["crossing_completed"]), CROSSINGS_PER_SET)
            self.assertEqual(len(app.events.calls["set_completed"]), 1)
            self.assertIn("complete", app.audio.spoken)
            saved = storage.values[STORAGE_KEY]
            self.assertEqual((saved["crossings_solved"], saved["sets_completed"]), (CROSSINGS_PER_SET, 1))
            self.assertEqual(saved["next_set"], (next_set + 1) % len(CROSSING_SETS))
            app.render()
            self.assertTrue(app.tap(app.canvas.mapper.point(*app.completion.primary_rect.center)))
            self.assertIs(app.state, AppState.BUILD)
            self.assertEqual(app.visit.set_index, (next_set + 1) % len(CROSSING_SETS))
            self.assertNotEqual(app._visit_id, first_visit)

    def test_space_on_completion_plays_the_next_set(self) -> None:
        from ponti_app import AppState

        app, now, _ = self._app()
        for _ in range(CROSSINGS_PER_SET):
            self._solve_with_keys(app, now)
            self._advance(app, now, 2.4)
        self.assertIs(app.state, AppState.TERMINAL)
        app.press(pygame.K_SPACE)
        self.assertIs(app.state, AppState.BUILD)
        self.assertEqual(app.visit.set_index, 1)

    def test_controller_dpad_and_south_button_drive_the_same_path(self) -> None:
        from greia_platform.pygame_input import CONTROLLER_BUTTON_A, CONTROLLER_BUTTON_DPAD_UP

        app, now, _ = self._app()
        pad = lambda button: app._handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=button))
        app.controls.layer.focus("tray.1", visible=True)
        pad(CONTROLLER_BUTTON_A)
        self.assertEqual(app.bridge.selected, 1)
        pad(CONTROLLER_BUTTON_DPAD_UP)
        self.assertTrue(app.controls.layer.focused_id.startswith(("seat.", "spot.")), app.controls.layer.focused_id)
        pad(CONTROLLER_BUTTON_A)
        self.assertEqual(app.bridge.seat_of[1], "bank")

    def test_pointer_tap_and_drag_build_the_bridge(self) -> None:
        app, now, _ = self._app(next_set=2)  # pillars: pillar, 2, 2 on a gap of 5
        mapper = app.canvas.mapper
        self.assertTrue(app.tap(mapper.point(*app.controls.tray[0].rect.center)))
        self.assertTrue(app.tap(mapper.point(*app.view.spot_rect(0).center)))
        self.assertEqual(app.bridge.pillar_spots(), [0])
        spans = app.bridge.spans()
        self.assertTrue(app.drag_to(mapper.point(*app.controls.tray[1].rect.center), mapper.point(*app.view.seat_rect(spans[0]).center)))
        self.assertEqual(app.bridge.seat_of[1], "bank")
        self.assertTrue(app.drag_to(mapper.point(*app.controls.tray[2].rect.center), mapper.point(*app.view.seat_rect(spans[1]).center)))
        self.assertTrue(app.bridge.evaluate().success)
        # Dragging a plank off the bridge returns it; tapping a faded tile calls one back.
        self.assertTrue(app.drag_to(mapper.point(*app.view.seat_rect(spans[1]).center), mapper.point(900, 250)))
        self.assertTrue(app.bridge.in_tray(2))
        self.assertTrue(app.tap(mapper.point(*app.controls.tray[1].rect.center)))
        self.assertTrue(app.bridge.in_tray(1))

    def test_pillar_crossing_asks_for_a_pillar_and_a_good_plank_is_just_right(self) -> None:
        from ponti_app import AppState

        app, now, _ = self._app(next_set=2)
        self.assertEqual(app.audio.spoken, ["pillar_on_rock"])
        app, now, _ = self._app()  # le1: gap 2 -> the 2-board plank is just right
        app._on_tray(1)
        app._on_seat(0)
        app._on_go()
        self._until(app, now, {AppState.CELEBRATE})
        self.assertEqual(app.audio.spoken.count("just_right"), 1)
        self.assertLess(app.audio.spoken.index("just_right"), app.audio.spoken.index("arrive"))

    def test_a_lifted_pillar_is_never_dropped_on_a_span(self) -> None:
        app, now, _ = self._app(next_set=2)
        app.bridge.select(0)  # the pillar
        app._on_seat(0)
        self.assertTrue(app.bridge.in_tray(0))
        self.assertIn("clack", app.audio.sounds)
        self.assertIn("spot:0", app.motion.pulses)

    def test_a_stop_thinks_shows_the_missing_length_returns_and_demonstrates(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from ponti_app import AppState

        app, now, _ = self._app()  # le1: gap 2, planks 1/2/3
        self.assertEqual(app.audio.spoken, ["long_enough"])  # one gap: "Is it long enough?"
        app._on_tray(0)
        app._on_seat(0)  # the 1-board plank
        app._on_go()
        self.assertEqual(app.audio.spoken[-2:], ["go", "lets_picnic"])
        self._until(app, now, {AppState.PAUSE})
        self.assertIs(app.cast.feedback.pose, CastPose.THINK)
        self.assertEqual(app.motion.missing, (1.0, 2.0))
        self.assertEqual(app.events.calls["crossing_missed"][0][-1], "short")
        self.assertEqual(app.audio.spoken[-1], "too_short")  # the reason replaces "try again"
        app.render()
        self._until(app, now, {AppState.BUILD})
        self.assertEqual(app.bridge.seat_of[0], "bank", "the child's plank stays for fixing")
        self.assertIsNotNone(app.motion.demo)
        self.assertIs(app.motion.demo[0].action, HintAction.PLACE_PLANK)
        app.render()
        hints = app.bridge.summary.hints
        self.assertTrue(app.tap(app.canvas.mapper.point(*app.controls.hint.rect.center)))
        self.assertEqual(app.bridge.summary.hints, hints + 1)

    def test_repeated_stops_also_carry_out_the_demonstrated_step(self) -> None:
        from ponti_app import AppState

        app, now, _ = self._app()
        for _ in range(SNAP_AFTER_MISSES):
            app.bridge.place_plank(0, "bank")
            app._sync()
            app._on_go()
            self._until(app, now, {AppState.BUILD})
        self._advance(app, now, 1.6)
        self.assertTrue(app.bridge.evaluate().success)

    def test_idle_hints_are_graduated(self) -> None:
        app, now, _ = self._app()
        self._advance(app, now, 6.2)
        self.assertTrue(app.cast.pointing)
        self.assertIn("nudge", app.audio.spoken)
        self.assertIsNone(app.motion.demo, "the first nudge only points")
        self.assertTrue(app.motion.pulses)
        self._advance(app, now, 12.2)  # back-off: 6 s, then a further 12 s
        self.assertIsNotNone(app.motion.demo)

    def test_layout_stays_clear_of_protected_chrome_at_every_size(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            app, now, _ = self._app(size=size, next_set=1)
            with self.subTest(size=size):
                layout = ControlLayout.for_canvas(app.canvas, size)
                controls = app.controls
                for control in (*controls.tray, controls.go, controls.hint, controls.progress):
                    if control.visible:
                        self.assertFalse(control.rect.colliderect(layout.protected), control.control_id)
                for tile in controls.tray[: len(app.bridge.crossing.pieces)]:
                    self.assertGreaterEqual(tile.rect.height * layout.scale, 40)
                    self.assertLessEqual(tile.rect.bottom, 600)
                for span in app.bridge.spans():
                    self.assertFalse(app.view.seat_rect(span).colliderect(layout.protected))
                self.assertGreaterEqual(BANK_TOP - 4 * UNIT, controls.screen.bar.bottom)
                app.render()

    def test_go_sits_at_the_right_end_of_the_tray_it_confirms(self) -> None:
        from activities.costruiamo_ponti.ponti_content import ALL_CROSSINGS

        for size in ((1024, 600), (800, 480)):
            app, now, _ = self._app(size=size, next_set=1)
            controls = app.controls
            with self.subTest(size=size):
                for crossing in ALL_CROSSINGS:
                    controls.set_crossing(crossing)
                    tiles = [tile.rect for tile in controls.tray[: len(crossing.pieces)]]
                    go = controls.go.rect
                    self.assertGreater(go.left, tiles[-1].right, crossing.crossing_id)
                    self.assertLessEqual(go.left - tiles[-1].right, 30, "GO beside the tray, not across the screen")
                    self.assertTrue(tiles[-1].top <= go.centery <= tiles[-1].bottom)
                    self.assertLessEqual(go.right, 1024 - 8)
                    self.assertGreater(go.top, 300, "GO is no longer in the top bar beside Home")

    def test_pointer_in_the_protected_region_is_ignored(self) -> None:
        app, now, _ = self._app()
        before = list(app.bridge.seat_of)
        self.assertFalse(app.tap((10, 10)))
        self.assertEqual(app.bridge.seat_of, before)

    def test_frames_are_blits_only_after_warm_up(self) -> None:
        from ponti_app import AppState

        app, now, _ = self._app(next_set=3)
        app.bridge.place_plank(0, "bank")  # thin wood under a heavy friend: lower, walk, bend
        app._sync()
        app.render()
        app._on_go()
        self._advance(app, now, 0.1)
        app.render()
        built = app.kit.painter.build_count
        scene = app.scene
        frames = app.art.plank(app.bridge.piece(0))
        for _ in range(45):
            self._advance(app, now, 1 / 30)
            app.render()
        self.assertIn(app.state, (AppState.RUNNING, AppState.PAUSE))
        self.assertEqual(app.kit.painter.build_count, built)
        self.assertIs(app.scene, scene)
        self.assertIs(app.art.plank(app.bridge.piece(0)), frames)
        self.assertLessEqual(len(app.motion.fx), 12)

    def test_platform_pointer_is_drawn_during_play_and_on_the_completion_screen(self) -> None:
        from ponti_app import AppState

        app, now, _ = self._app()
        target = app.canvas.target
        color = (254, 202, 87)  # draw_activity_pointer default body colour
        for position in ((300, 200), (600, 300)):
            with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
                "pygame.mouse.get_pos", return_value=position
            ):
                app.render()
                app.canvas.present()
                self.assertEqual(tuple(target.get_at((position[0] + 8, position[1])))[:3], color)
        for _ in range(CROSSINGS_PER_SET):
            self._solve_with_keys(app, now)
            self._advance(app, now, 2.4)
        self.assertIs(app.state, AppState.TERMINAL)
        with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
            "pygame.mouse.get_pos", return_value=(200, 450)
        ):
            app.render()
            app.canvas.present()
            self.assertEqual(tuple(target.get_at((208, 450)))[:3], color)

    def test_italian_go_label_and_friend_voice(self) -> None:
        app, now, _ = self._app(locale="it")
        self.assertEqual(app.controls.go.label, "VIA!")
        self.assertEqual(app.audio.speakers[-1], CROSSING_SETS[0].crossings[0].traveler)


if __name__ == "__main__":
    unittest.main()
