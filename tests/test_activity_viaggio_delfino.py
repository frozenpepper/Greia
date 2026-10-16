"""Contract and app-loop tests for Il Viaggio del Delfino (org.greia.viaggio-delfino)."""

from __future__ import annotations

import json
import os
import random
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from activities.viaggio_delfino.delfino_content import (
    FACT_IDS,
    JOURNEY_IDS,
    JOURNEYS,
    SURFACE_Y,
    audio_key,
    caption_key,
    journey,
    stars_for,
)
from activities.viaggio_delfino.delfino_model import (
    MAX_SWIM_Y,
    MIN_SWIM_Y,
    Dolphin,
    EventKind,
    FriendState,
    JourneyRun,
    build_course,
)
from activities.viaggio_delfino.delfino_services import (
    STORAGE_KEY,
    DelfinoProgress,
    GreiaDelfinoEvents,
    GreiaDelfinoStorage,
)

PACKAGE = Path(__file__).resolve().parents[1] / "activities" / "viaggio_delfino"
LOCALES = ("en", "it", "es", "fr")


def _strings(locale: str) -> dict[str, str]:
    return json.loads((PACKAGE / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]


def _run_until_finished(run: JourneyRun, *, steer: bool, leap: bool = True, limit: float = 240.0) -> list:
    """Advance a journey to its finish, optionally steering like a child."""

    events = []
    elapsed = 0.0
    while not run.finished and elapsed < limit:
        if steer:
            target = run.next_target()
            if target is not None:
                run.dolphin.aim(target[1])
            group = next((g for g in run.course.groups if not g.resolved and g.end_x >= run.dolphin.x - 30), None)
            if leap and group is not None and group.arc and 0 < group.start_x - run.dolphin.x < 175:
                run.leap()
        events.extend(run.update(1 / 30))
        elapsed += 1 / 30
    return events


class JourneyContentTests(unittest.TestCase):
    def test_three_finite_journeys_with_a_finish_and_friends(self) -> None:
        self.assertEqual(JOURNEY_IDS, ("bay", "reef", "lagoon"))
        for spec in JOURNEYS:
            with self.subTest(journey=spec.journey_id):
                self.assertGreater(spec.length_x, 5000.0)
                # 1-1.5 minutes of swimming at cruise speed.
                self.assertTrue(45.0 <= spec.length_x / spec.speed <= 90.0)
                self.assertEqual(spec.layout.count("F"), len(spec.friends))
                self.assertGreaterEqual(spec.layout.count("A"), 1)
                self.assertEqual(spec.total_pearls, spec.pearl_groups * spec.group_size)

    def test_difficulty_rises_gently_across_journeys(self) -> None:
        speeds = [spec.speed for spec in JOURNEYS]
        sizes = [spec.group_size for spec in JOURNEYS]
        self.assertEqual(speeds, sorted(speeds))
        self.assertEqual(sizes, sorted(sizes))

    def test_every_recorded_fact_is_unlocked_by_exactly_one_friend(self) -> None:
        facts = [friend.fact_id for spec in JOURNEYS for friend in spec.friends]
        self.assertEqual(sorted(facts), sorted(FACT_IDS))
        for friend in (friend for spec in JOURNEYS for friend in spec.friends):
            self.assertTrue(friend.visual.startswith("creature.marine."))

    def test_fact_key_helpers(self) -> None:
        self.assertEqual(caption_key("curiosity.delfino.pods"), "curiosity.delfino.pods.caption")
        self.assertEqual(audio_key("curiosity.delfino.pods"), "curiosity.delfino.pods.voice")

    def test_stars_reward_finishing_and_more_pearls(self) -> None:
        self.assertEqual(stars_for(0, 15), 1)
        self.assertEqual(stars_for(8, 15), 2)
        self.assertEqual(stars_for(12, 15), 3)
        self.assertEqual(stars_for(0, 0), 1)

    def test_manifest_matches_the_real_experience(self) -> None:
        manifest = tomllib.loads((PACKAGE / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.viaggio-delfino")
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        education = manifest["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 7))
        self.assertIn("sea", manifest["presentation"]["discovery_tags"])
        events = {event["id"] for event in education["events"]}
        self.assertEqual(events, {"dolphin.chapter_completed", "dolphin.fact_opened", "dolphin.journey_score"})
        self.assertEqual(set(manifest["activity"]["languages"]), {"it", "en"})


class LocaleParityTests(unittest.TestCase):
    def test_journey_names_and_completion_copy_exist_in_all_locales(self) -> None:
        english = set(_strings("en"))
        for locale in LOCALES:
            strings = _strings(locale)
            with self.subTest(locale=locale):
                self.assertEqual(set(strings), english)
                for spec in JOURNEYS:
                    self.assertTrue(strings[spec.name_key].strip())
                for key in ("completion.title", "completion.replay", "completion.journeys", "completion.body"):
                    self.assertTrue(strings[key].strip())
                for fact_id in FACT_IDS:
                    self.assertTrue(strings[caption_key(fact_id)].strip())

    def test_voice_audio_is_packaged_for_every_cue_in_both_base_locales(self) -> None:
        for locale in ("en", "it"):
            data = json.loads((PACKAGE / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for fact_id in (*FACT_IDS, "presenter.welcome"):
                with self.subTest(locale=locale, fact=fact_id):
                    entry = data["audio"][audio_key(fact_id)]
                    self.assertTrue((PACKAGE / entry["path"]).is_file())


class DolphinMotionTests(unittest.TestCase):
    def test_dolphin_advances_and_steering_clamps(self) -> None:
        dolphin = Dolphin(base_speed=160.0)
        start = dolphin.x
        dolphin.update(0.5)
        self.assertAlmostEqual(dolphin.x - start, 80.0, places=3)
        dolphin.steer(-10_000)
        self.assertEqual(dolphin.target_y, MIN_SWIM_Y)
        dolphin.steer(10_000)
        self.assertEqual(dolphin.target_y, MAX_SWIM_Y)

    def test_cruising_never_breaks_the_surface(self) -> None:
        dolphin = Dolphin()
        dolphin.aim(MIN_SWIM_Y)
        for _ in range(300):
            self.assertIsNone(dolphin.update(1 / 30))
        self.assertGreater(dolphin.y, SURFACE_Y)

    def test_one_leap_is_one_arc_out_of_the_water(self) -> None:
        dolphin = Dolphin(y=420.0, target_y=420.0)
        self.assertTrue(dolphin.trigger_leap())
        self.assertFalse(dolphin.trigger_leap())
        seen = []
        for _ in range(240):
            event = dolphin.update(1 / 60)
            if event is not None:
                seen.append(event)
        self.assertEqual(seen, [EventKind.SPLASH_OUT, EventKind.SPLASH_IN])
        self.assertFalse(dolphin.airborne)
        self.assertGreaterEqual(dolphin.y, SURFACE_Y)

    def test_stopped_dolphin_neither_moves_nor_leaps(self) -> None:
        dolphin = Dolphin()
        dolphin.stop()
        x = dolphin.x
        dolphin.update(1.0)
        self.assertEqual(dolphin.x, x)
        self.assertFalse(dolphin.trigger_leap())


class CourseTests(unittest.TestCase):
    def test_course_content_is_fixed_and_bounded(self) -> None:
        for spec in JOURNEYS:
            course = build_course(spec, random.Random(3))
            with self.subTest(journey=spec.journey_id):
                self.assertEqual(course.total_pearls, spec.total_pearls)
                self.assertLessEqual(len(course.jellies), spec.jellies)
                self.assertEqual(len(course.friends), len(spec.friends))
                self.assertEqual(len(course.stretch_ends), spec.stretches)
                self.assertTrue(all(p.x < course.finish_x for p in course.pearls))
                self.assertTrue(all(SURFACE_Y - 140 < p.y <= MAX_SWIM_Y for p in course.pearls))

    def test_arc_pearls_float_above_the_waves(self) -> None:
        course = build_course(journey("bay"), random.Random(5))
        arcs = [g for g in course.groups if g.arc]
        self.assertTrue(arcs)
        arc_pearls = [p for p in course.pearls if p.group == arcs[0].index]
        self.assertTrue(all(p.y < SURFACE_Y for p in arc_pearls))

    def test_a_well_timed_leap_collects_an_arc(self) -> None:
        run = JourneyRun.start(journey("bay"), random.Random(5))
        events = _run_until_finished(run, steer=True)
        arcs = [g for g in run.course.groups if g.arc]
        self.assertTrue(all(g.collected > 0 for g in arcs))
        self.assertIn(EventKind.GROUP_COMPLETE, [e.kind for e in events])

    def test_steering_child_finishes_with_most_pearls_and_meets_friends(self) -> None:
        for spec in JOURNEYS:
            run = JourneyRun.start(spec, random.Random(11))
            events = _run_until_finished(run, steer=True)
            kinds = [e.kind for e in events]
            with self.subTest(journey=spec.journey_id):
                self.assertTrue(run.finished)
                self.assertEqual(kinds.count(EventKind.FINISHED), 1)
                self.assertEqual(kinds.count(EventKind.FRIEND_MET), len(spec.friends))
                self.assertGreaterEqual(run.collected / run.course.total_pearls, 0.8)
                self.assertEqual(run.stretches_passed, spec.stretches)

    def test_passive_child_still_finishes_and_meets_every_friend(self) -> None:
        """No fail state: friends kindly come to the dolphin; jellies only bump."""

        run = JourneyRun.start(journey("reef"), random.Random(2))
        events = _run_until_finished(run, steer=False)
        kinds = [e.kind for e in events]
        self.assertTrue(run.finished)
        self.assertEqual(kinds.count(EventKind.FRIEND_MET), 2)
        self.assertTrue(all(f.state is not FriendState.WAITING for f in run.course.friends))

    def test_jellyfish_bump_pushes_away_without_harm(self) -> None:
        run = JourneyRun.start(journey("bay"), random.Random(1))
        jelly = run.course.jellies[0]
        run.dolphin.x = jelly.x
        run.dolphin.y = jelly.effective_y + 10
        collected = run.collected
        events = run.update(1 / 30)
        self.assertIn(EventKind.BUMP, [e.kind for e in events])
        self.assertGreater(run.dolphin.target_y, jelly.effective_y)
        self.assertEqual(run.collected, collected)
        # Cooldown: staying in contact does not bump again immediately.
        again = run.update(1 / 30)
        self.assertNotIn(EventKind.BUMP, [e.kind for e in again])

    def test_missed_group_is_reported_once(self) -> None:
        run = JourneyRun.start(journey("bay"), random.Random(1))
        first = run.course.groups[0]
        ys = [p.y for p in run.course.pearls if p.group == first.index]
        run.dolphin.aim(MAX_SWIM_Y if min(ys) < 360 else SURFACE_Y + 30)
        run.dolphin.y = run.dolphin.target_y
        missed = []
        while run.dolphin.x < first.end_x + 200:
            missed.extend(e for e in run.update(1 / 30) if e.kind is EventKind.GROUP_MISSED)
        self.assertEqual(len(missed), 1)

    def test_next_target_points_at_the_next_pearl_or_waiting_friend(self) -> None:
        run = JourneyRun.start(journey("bay"), random.Random(1))
        target = run.next_target()
        first = min(run.course.pearls, key=lambda p: p.x)
        self.assertEqual(target, (first.x, first.y))


class _StubStorage:
    def __init__(self) -> None:
        self.data: dict[str, object] = {}

    def kv_get(self, key: str) -> object:
        return self.data.get(key)

    def kv_set(self, key: str, value: object) -> None:
        self.data[key] = value


class _StubEvents:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def chapter_completed(self, chapter_number: int) -> None:
        self.calls.append(("dolphin.chapter_completed", chapter_number))

    def fact_opened(self, fact_id: str) -> None:
        self.calls.append(("dolphin.fact_opened", fact_id))

    def journey_score(self, score: int) -> None:
        self.calls.append(("dolphin.journey_score", score))

    def close(self) -> None:
        self.calls.append(("close", None))


class GreiaDelfinoStorageTests(unittest.TestCase):
    def test_progress_round_trip_unlocks_the_next_journey(self) -> None:
        stub = _StubStorage()
        storage = GreiaDelfinoStorage(storage=stub, journey_ids=JOURNEY_IDS)
        progress = storage.load()
        self.assertEqual(progress.unlocked(JOURNEY_IDS), ("bay",))
        progress = progress.with_result("bay", 12, 3)
        self.assertTrue(storage.save(progress))
        loaded = storage.load()
        self.assertEqual(loaded.unlocked(JOURNEY_IDS), ("bay", "reef"))
        self.assertEqual(loaded.record("bay").best_pearls, 12)
        self.assertEqual(loaded.record("bay").best_stars, 3)
        self.assertEqual(loaded.total_pearls, 12)
        # A weaker replay never lowers the best result but adds pearls.
        loaded = loaded.with_result("bay", 4, 1)
        self.assertEqual(loaded.record("bay").best_stars, 3)
        self.assertEqual(loaded.record("bay").completions, 2)
        self.assertEqual(loaded.total_pearls, 16)

    def test_schema_one_save_migrates_forward_without_losing_counters(self) -> None:
        stub = _StubStorage()
        stub.data[STORAGE_KEY] = {"total_pearls": 140, "best_journey_score": 310, "timestamp": 1.0}
        progress = GreiaDelfinoStorage(storage=stub, journey_ids=JOURNEY_IDS).load()
        self.assertEqual(progress.total_pearls, 140)
        self.assertEqual(progress.best_journey_score, 310)
        # The old full journey counts as the first course done.
        self.assertEqual(progress.unlocked(JOURNEY_IDS), ("bay", "reef"))

    def test_corrupt_payloads_degrade_to_defaults(self) -> None:
        stub = _StubStorage()
        storage = GreiaDelfinoStorage(storage=stub, journey_ids=JOURNEY_IDS)
        stub.data[STORAGE_KEY] = "corrupt"
        self.assertEqual(storage.load(), DelfinoProgress())
        stub.data[STORAGE_KEY] = {
            "total_pearls": "x",
            "best_journey_score": -5,
            "journeys": {"bay": {"completions": "?", "best_stars": 99}, "mars": {"completions": 3}, 7: {}},
        }
        progress = storage.load()
        self.assertEqual(progress.total_pearls, 0)
        self.assertEqual(progress.record("bay").best_stars, 3)
        self.assertFalse(progress.record("bay").done)
        self.assertNotIn("mars", progress.journeys)

    def test_missing_storage_degrades_to_defaults(self) -> None:
        storage = GreiaDelfinoStorage(storage=None)
        self.assertFalse(storage.available)
        self.assertEqual(storage.load(), DelfinoProgress())
        self.assertFalse(storage.save(DelfinoProgress()))


class GreiaDelfinoEventsTests(unittest.TestCase):
    def test_events_emit_asynchronously_without_blocking_the_caller(self) -> None:
        import time as time_module

        calls: list[tuple[str, object]] = []

        def slow_emitter(event_id, payload=None, idempotency_key=None, score=None):
            time_module.sleep(0.05)
            calls.append((event_id, score))

        service = GreiaDelfinoEvents(emitter=slow_emitter, queue_depth=8)
        try:
            submitted = time_module.monotonic()
            service.chapter_completed(1)
            service.fact_opened("curiosity.delfino.pods")
            service.journey_score(12)
            self.assertLess((time_module.monotonic() - submitted) * 1000, 15.0)
            self.assertTrue(service.flush(timeout=3.0))
            self.assertEqual(
                [name for name, _ in calls],
                ["dolphin.chapter_completed", "dolphin.fact_opened", "dolphin.journey_score"],
            )
            self.assertEqual(calls[2][1], 12)
        finally:
            service.close()

    def test_close_drains_pending_events(self) -> None:
        calls: list[str] = []
        service = GreiaDelfinoEvents(
            emitter=lambda event_id, payload=None, idempotency_key=None, score=None: calls.append(event_id),
            queue_depth=8,
        )
        service.chapter_completed(2)
        service.close()
        self.assertEqual(calls, ["dolphin.chapter_completed"])


class SteeringInputTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        from activities.viaggio_delfino.delfino_input import DolphinSteering, SwimInput

        self.steering = DolphinSteering()
        self.SwimInput = SwimInput

    def test_arrows_and_ws_hold_depth_and_space_leaps(self) -> None:
        handle = self.steering.handle
        self.assertIs(handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)), self.SwimInput.STEER)
        self.assertEqual(self.steering.axis, 1.0)
        self.assertGreater(self.steering.step(0.1), 0)
        handle(pygame.event.Event(pygame.KEYUP, key=pygame.K_DOWN))
        self.assertEqual(self.steering.axis, 0.0)
        handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
        self.assertEqual(self.steering.axis, -1.0)
        handle(pygame.event.Event(pygame.KEYUP, key=pygame.K_w))
        self.assertIs(handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)), self.SwimInput.LEAP)
        self.assertIs(handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)), self.SwimInput.LEAP)

    def test_stick_uses_the_central_dead_zone(self) -> None:
        axis_event = getattr(pygame, "CONTROLLERAXISMOTION", None)
        if axis_event is None:
            self.skipTest("SDL controller events unavailable")
        from greia_platform.pygame_input import CONTROLLER_AXIS_LEFTY

        self.steering.handle(pygame.event.Event(axis_event, axis=CONTROLLER_AXIS_LEFTY, value=3000))
        self.assertEqual(self.steering.axis, 0.0)
        self.steering.handle(pygame.event.Event(axis_event, axis=CONTROLLER_AXIS_LEFTY, value=30000))
        self.assertGreater(self.steering.axis, 0.5)


def _logical_to_physical(app, point):
    x, y = app.canvas.mapper.transform.logical_to_physical(point)
    return (int(x), int(y))


class _Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


class AppLoopTests(unittest.TestCase):
    """Real app, real Pygame frames, no platform services."""

    def setUp(self) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))
        from activities.viaggio_delfino.delfino_app import DelfinoJourneyApp, Phase
        from activities.viaggio_delfino.delfino_audio import SilentDelfinoAudio

        self.Phase = Phase
        self.clock = _Clock()
        self.stub = _StubStorage()
        self.events = _StubEvents()
        self.app = DelfinoJourneyApp(
            rng=random.Random(7),
            clock=self.clock,
            storage=GreiaDelfinoStorage(storage=self.stub, journey_ids=JOURNEY_IDS),
            events=self.events,
            audio=SilentDelfinoAudio(),
        )
        self.app._enter_picker()

    def tearDown(self) -> None:
        pygame.quit()

    def _step(self, frames: int = 1) -> None:
        for _ in range(frames):
            self.clock.t += 1 / 30
            self.app.advance(1 / 30)
            self.app.draw()

    def _key(self, key: int, *, up: bool = False) -> None:
        self.app.handle_event(pygame.event.Event(pygame.KEYUP if up else pygame.KEYDOWN, key=key, mod=0, unicode=""))

    def _swim_with_keys(self, limit_frames: int = 30 * 150) -> None:
        """Steer with held arrow keys and leap with Space, like a child."""

        app = self.app
        held: int | None = None
        for _ in range(limit_frames):
            if app.phase is not self.Phase.SWIM:
                return
            run = app.run_state
            target = run.next_target()
            wanted = None
            if target is not None:
                if target[1] < run.dolphin.target_y - 20:
                    wanted = pygame.K_UP
                elif target[1] > run.dolphin.target_y + 20:
                    wanted = pygame.K_DOWN
            if wanted != held:
                if held is not None:
                    self._key(held, up=True)
                if wanted is not None:
                    self._key(wanted)
                held = wanted
            group = next((g for g in run.course.groups if not g.resolved and g.end_x >= run.dolphin.x - 30), None)
            if group is not None and group.arc and 0 < group.start_x - run.dolphin.x < 175 and not run.dolphin.leap_pending:
                self._key(pygame.K_SPACE)
            self._step()

    def test_picker_offers_only_the_first_journey_at_first(self) -> None:
        app = self.app
        self.assertIs(app.phase, self.Phase.PICKER)
        self.assertTrue(app.picker.cards["bay"].enabled)
        self.assertFalse(app.picker.cards["reef"].enabled)
        # Tapping a closed card is answered kindly and starts nothing.
        app.tap(_logical_to_physical(app, app.picker.rect("lagoon").center))
        self.assertIs(app.phase, self.Phase.PICKER)
        self.assertTrue(app.picker_cast.feedback.animating)

    def test_idle_picker_hint_points_at_the_open_journey(self) -> None:
        self._step(int(30 * 6.5))
        self.assertTrue(self.app.picker_cast.pointing)

    def test_keyboard_child_plays_a_whole_journey_to_the_completion_scene(self) -> None:
        app = self.app
        self._key(pygame.K_SPACE)  # choose the focused (suggested) journey
        self.assertIs(app.phase, self.Phase.SWIM)
        self.assertEqual(app.spec.journey_id, "bay")
        self._swim_with_keys()
        self.assertIn(app.phase, (self.Phase.COUNT, self.Phase.DONE))
        collected = app.run_state.collected
        self.assertGreater(collected, 0)
        for _ in range(30 * 20):
            if app.phase is self.Phase.DONE:
                break
            self._step()
        self.assertIs(app.phase, self.Phase.DONE)
        self.assertEqual(app.hud.count.value, collected)
        self.assertTrue(app.completion.is_prepared)
        # Progress saved, reef unlocked, declared facts emitted.
        saved = self.stub.data[STORAGE_KEY]
        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["journeys"]["bay"]["completions"], 1)
        names = [name for name, _ in self.events.calls]
        self.assertEqual(names.count("dolphin.fact_opened"), 2)
        self.assertIn(("dolphin.chapter_completed", 1), self.events.calls)
        self.assertIn(("dolphin.journey_score", collected), self.events.calls)
        # Completion: arrow right + Space chooses "journeys" → back to the map.
        self._key(pygame.K_RIGHT)
        self._key(pygame.K_SPACE)
        self.assertIs(app.phase, self.Phase.PICKER)
        self.assertTrue(app.picker.cards["reef"].enabled)
        self.assertEqual(app._suggested, "reef")

    def test_count_up_can_be_skipped_and_replay_restarts_the_same_journey(self) -> None:
        app = self.app
        app.start_journey("bay")
        run = app.run_state
        for pearl in run.course.pearls[:5]:
            pearl.collected = True
        run.collected = 5
        run.dolphin.x = run.course.finish_x - 1
        self._step(2)
        self.assertTrue(run.finished)
        self._step(45)
        self.assertIs(app.phase, self.Phase.COUNT)
        self._key(pygame.K_SPACE)
        self.assertEqual(app.hud.count.value, 5)
        self._step(40)
        self.assertIs(app.phase, self.Phase.DONE)
        primary = app.completion.primary_rect.center
        app.tap(_logical_to_physical(app, primary))
        self.assertIs(app.phase, self.Phase.SWIM)
        self.assertEqual(app.spec.journey_id, "bay")
        self.assertEqual(app.run_state.collected, 0)

    def test_pointer_steers_and_click_leaps_but_protected_chrome_is_ignored(self) -> None:
        app = self.app
        app.start_journey("bay")
        app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(500, 450), rel=(0, 0), buttons=(0, 0, 0)))
        self.assertGreater(app.run_state.dolphin.target_y, 400)
        # Inside the protected Home/Back region: no steering.
        app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(20, 20), rel=(0, 0), buttons=(0, 0, 0)))
        self.assertGreater(app.run_state.dolphin.target_y, 400)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(500, 450), button=1))
        self.assertTrue(app.run_state.dolphin.leap_pending)

    def test_keyboard_hint_sits_on_the_sand_below_every_pearl_and_lights_the_pressed_key(self) -> None:
        from greia_platform.activity_controls import ControlLayout
        from greia_platform.activity_keyboard_hint import KeyCap

        app = self.app
        app.start_journey("bay")
        keys = app.hud.keys
        self.assertTrue(keys.visible, "shown at the start of a journey")
        self.assertEqual(keys.active, {KeyCap.UP, KeyCap.DOWN, KeyCap.SPACE})
        lowest = max(p.y for p in app.run_state.course.pearls)
        self.assertGreater(keys.rect.top, lowest + 20, "below the deepest pearl")
        self.assertGreater(keys.rect.left, app.run_state.dolphin.x + 200, "far from the dolphin")
        self.assertLessEqual(keys.rect.bottom, 600)
        self.assertFalse(keys.rect.colliderect(ControlLayout.for_canvas(app.canvas, app.screen.get_size()).protected))
        self.assertGreaterEqual(min(r.height for r in keys.key_rects().values()), 28, "legible keycaps")
        self._key(pygame.K_DOWN)
        self.assertIn(KeyCap.DOWN, keys.lit)
        self._step()
        self._key(pygame.K_DOWN, up=True)
        self._step(15)
        self.assertNotIn(KeyCap.DOWN, keys.lit)
        app._begin_count()
        self.assertFalse(keys.visible, "the count-up hides the hint")

    def test_missed_group_brings_tito_and_a_demonstration(self) -> None:
        app = self.app
        app.start_journey("bay")
        self.clock.t += 20.0  # past the welcome
        app._note_swim_input()  # the child is playing (not resting after the jump)
        app._talk_until = 0.0
        run = app.run_state
        first = run.course.groups[0]
        ys = [p.y for p in run.course.pearls if p.group == first.index]
        run.dolphin.aim(510 if min(ys) < 360 else SURFACE_Y + 30)
        run.dolphin.y = run.dolphin.target_y
        while run.dolphin.x < first.end_x + 80:
            self._step()
        self.assertTrue(app._demo_pending or app._hint_until > self.clock.t)
        for _ in range(30 * 8):
            if app._hint_until > self.clock.t:
                break
            self._step()
        self.assertGreater(app._hint_until, self.clock.t)
        self.assertTrue(app.cast.pointing)

    def test_an_idle_child_is_not_carried_to_the_finish_the_sea_comes_to_rest(self) -> None:
        from activities.viaggio_delfino.delfino_app import REST_AFTER_SECONDS, REST_EASE_SECONDS

        app = self.app
        app.start_journey("bay")
        self._step(int(30 * (REST_AFTER_SECONDS - 1.0)))
        self.assertFalse(app.resting, "both idle hints come first")
        for _ in range(30 * 60):  # a friend's fact may still be playing
            if app.resting:
                break
            self._step()
        self.assertTrue(app.resting)
        self.assertFalse(app.cast.talking)
        self._step(int(30 * (REST_EASE_SECONDS + 1.0)))
        self.assertIs(app.phase, self.Phase.SWIM)
        self.assertFalse(app.moving, "a resting sea lets the frame governor freeze")
        self.assertTrue(app.hud.keys.visible, "the keycaps show how to swim on")
        x = app.run_state.dolphin.x
        self._step(30 * 40)
        self.assertEqual(app.run_state.dolphin.x, x)
        self.assertFalse(app.run_state.finished)
        self._key(pygame.K_UP)
        self.assertFalse(app.resting)
        self.assertTrue(app.moving)
        self._step(10)
        self.assertGreater(app.run_state.dolphin.x, x)

    def test_holding_an_arrow_is_play_not_idleness(self) -> None:
        from activities.viaggio_delfino.delfino_app import REST_AFTER_SECONDS

        app = self.app
        app.start_journey("bay")
        self._key(pygame.K_DOWN)
        self._step(int(30 * (REST_AFTER_SECONDS + 5.0)))
        self.assertFalse(app.resting)


class DelfinoLaunchWorkTests(unittest.TestCase):
    """Work moved off the launch path keeps its exact result."""

    def setUp(self) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def tearDown(self) -> None:
        pygame.quit()

    def test_postcard_looks_share_identical_scene_parts_while_warming(self) -> None:
        from activities.viaggio_delfino.delfino_art import LOOKS, DelfinoArt

        art = DelfinoArt()
        art._warm_parts = {}
        try:
            bay = art._bake_scene(LOOKS["bay"])
            reef = art._bake_scene(LOOKS["reef"])
            lagoon = art._bake_scene(LOOKS["lagoon"])
        finally:
            art._warm_parts = None
        self.assertIs(bay.sky, reef.sky)
        self.assertIsNot(bay.sky, lagoon.sky)
        self.assertIs(bay.back[-1], lagoon.back[-1], "one sea band for every look")
        self.assertIs(bay.back[-2], reef.back[-2], "one sand strip for every look")
        # Shared parts give exactly the pixels a separate bake gives.
        for look, shared in (("reef", reef), ("lagoon", lagoon)):
            alone = art._bake_scene(LOOKS[look])
            for camera in (0.0, 2600.0):
                a = pygame.Surface((1024, 600))
                b = pygame.Surface((1024, 600))
                shared.draw_back(a, camera)
                alone.draw_back(b, camera)
                self.assertEqual(pygame.image.tostring(a, "RGB"), pygame.image.tostring(b, "RGB"), look)
        art.release_sources()

    def test_voice_cues_decode_after_the_first_frame_or_on_demand(self) -> None:
        from activities.viaggio_delfino.delfino_audio import PygameDelfinoAudio

        audio = PygameDelfinoAudio()
        if not audio.enabled:
            self.skipTest("no mixer")
        clip = sorted((PACKAGE / "assets" / "audio" / "en").glob("*.ogg")) or sorted(
            (PACKAGE / "assets" / "audio" / "en").glob("*.wav")
        )
        self.assertTrue(clip)
        audio.bind_resources(SimpleNamespace(audio_cue=lambda key: SimpleNamespace(path=clip[0])))
        audio.preload_voice([FACT_IDS[0], FACT_IDS[1]])
        self.assertFalse(audio._voices.built(FACT_IDS[0]), "nothing is decoded before the first frame")
        self.assertGreater(audio.play_voice(FACT_IDS[0]), 0.0, "a cue needed early decodes on demand")
        self.assertTrue(audio._voices.built(FACT_IDS[0]))
        audio.shutdown()


def _pointer_pixel_is_drawn(target, position) -> bool:
    # draw_activity_pointer's default body colour, 8 px right of the hot spot.
    return tuple(target.get_at((position[0] + 8, position[1])))[:3] == (254, 202, 87)


class ViaggioDelfinoPointerTests(unittest.TestCase):
    """The OS cursor is hidden; the platform canvas must draw Greia's pointer."""

    def test_frame_presentation_draws_the_platform_pointer(self) -> None:
        from greia_platform.activity_api import get_theme
        from activities.viaggio_delfino.delfino_app import DelfinoJourneyApp
        from activities.viaggio_delfino.delfino_audio import SilentDelfinoAudio

        pygame.init()
        pygame.display.set_mode((1024, 600))
        app = DelfinoJourneyApp(
            storage=GreiaDelfinoStorage(storage=None), events=_StubEvents(), audio=SilentDelfinoAudio()
        )
        app._enter_picker()
        app.draw()
        for position in ((300, 200), (700, 380)):
            with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
                "pygame.mouse.get_pos", return_value=position
            ):
                app._present_frame(app.canvas, get_theme())
                self.assertTrue(_pointer_pixel_is_drawn(app.canvas.target, position))
        pygame.quit()

    def test_main_loop_presents_the_replaced_canvas_after_video_resize(self) -> None:
        from activities.viaggio_delfino.delfino_app import DelfinoJourneyApp

        app = object.__new__(DelfinoJourneyApp)
        old_canvas = SimpleNamespace(surface=object(), present=mock.Mock())
        new_canvas = SimpleNamespace(surface=object(), present=mock.Mock())
        app.canvas = old_canvas
        app._running = True
        app._enter_picker = lambda: None
        app.advance = lambda _dt: None
        app.draw = lambda: None
        app.shutdown = mock.Mock()

        def resize(_event) -> None:
            app.canvas = new_canvas

        app.handle_event = resize
        with (
            mock.patch("activities.viaggio_delfino.delfino_app.pygame.event.get", return_value=[SimpleNamespace(type=pygame.VIDEORESIZE)]),
            mock.patch("activities.viaggio_delfino.delfino_app.get_theme", return_value=SimpleNamespace(background=(0, 0, 0))),
            mock.patch("activities.viaggio_delfino.delfino_app.activity_stop_requested", side_effect=[False, True]),
            mock.patch("activities.viaggio_delfino.delfino_app.mark_activity_ready"),
            mock.patch("activities.viaggio_delfino.delfino_app.pygame.display.flip"),
            mock.patch("activities.viaggio_delfino.delfino_app.pygame.quit"),
        ):
            self.assertEqual(app.run(), 0)
        new_canvas.present.assert_called_once()
        old_canvas.present.assert_not_called()
        app.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
