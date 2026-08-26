"""Semantic contract tests for Il Viaggio del Delfino (org.greia.viaggio-delfino)."""

from __future__ import annotations

import json
import random
import unittest
from pathlib import Path

from activities.viaggio_delfino.delfino_content import (
    CHAPTERS,
    FACT_IDS,
    TOTAL_JOURNEY_X,
    audio_key,
    caption_key,
    chapter_index_for_x,
    chapter_start_x,
)
from activities.viaggio_delfino.delfino_model import (
    MAX_SWIM_Y,
    MIN_SWIM_Y,
    SURFACE_Y,
    Dolphin,
    JourneyState,
)
from activities.viaggio_delfino.delfino_services import (
    GreiaDelfinoEvents,
    GreiaDelfinoStorage,
)

PACKAGE = Path(__file__).resolve().parents[1] / "activities" / "viaggio_delfino"


class JourneyContentTests(unittest.TestCase):
    def test_chapters_are_ordered_with_positive_lengths(self) -> None:
        self.assertEqual(len(CHAPTERS), 3)
        for chapter in CHAPTERS:
            self.assertGreater(chapter.length_x, 0.0)
            self.assertTrue(chapter.name_key.startswith("chapter."))
        self.assertEqual(TOTAL_JOURNEY_X, sum(c.length_x for c in CHAPTERS))

    def test_chapter_index_tracks_boundaries_and_clamps(self) -> None:
        self.assertEqual(chapter_index_for_x(0.0), 0)
        self.assertEqual(chapter_index_for_x(chapter_start_x(1) - 1.0), 0)
        self.assertEqual(chapter_index_for_x(chapter_start_x(1)), 1)
        self.assertEqual(chapter_index_for_x(chapter_start_x(2)), 2)
        self.assertEqual(chapter_index_for_x(TOTAL_JOURNEY_X + 5000.0), 2)

    def test_fact_ids_have_caption_and_audio_key_helpers(self) -> None:
        self.assertEqual(len(FACT_IDS), 6)
        self.assertEqual(len(set(FACT_IDS)), 6)
        for fact_id in FACT_IDS:
            self.assertTrue(fact_id.startswith("curiosity.delfino."))
            self.assertEqual(caption_key(fact_id), f"{fact_id}.caption")
            self.assertEqual(audio_key(fact_id), f"{fact_id}.voice")


class LocaleParityTests(unittest.TestCase):
    def _bundle(self, locale: str) -> dict:
        return json.loads((PACKAGE / "locales" / f"{locale}.json").read_text(encoding="utf-8"))

    def test_every_chapter_and_fact_has_localized_captions(self) -> None:
        for locale in ("it", "en"):
            strings = self._bundle(locale)["strings"]
            with self.subTest(locale=locale):
                self.assertIn("activity.viaggio_delfino.title", strings)
                self.assertIn("completion.title", strings)
                self.assertIn("completion.replay", strings)
                self.assertIn("completion.body", strings)
                self.assertIn("presenter.welcome.caption", strings)
                for chapter in CHAPTERS:
                    self.assertTrue(strings[chapter.name_key].strip())
                for fact_id in FACT_IDS:
                    self.assertTrue(strings[caption_key(fact_id)].strip())

    def test_voice_audio_is_packaged_for_every_cue_in_every_locale(self) -> None:
        cue_keys = ["presenter.welcome.voice"] + [audio_key(f) for f in FACT_IDS]
        for locale in ("it", "en"):
            data = self._bundle(locale)
            audio = data.get("audio") or {}
            self.assertEqual(set(audio), set(cue_keys))
            for key in cue_keys:
                with self.subTest(locale=locale, key=key):
                    relative = audio[key]["path"]
                    self.assertNotIn("..", relative)
                    self.assertTrue(relative.startswith(f"assets/audio/{locale}/"))
                    packaged = PACKAGE / relative
                    self.assertTrue(packaged.is_file(), relative)
                    size = packaged.stat().st_size
                    self.assertGreater(size, 10_000, "voice cue suspiciously small")
                    self.assertLess(size, 512 * 1024, "voice cue exceeds package bound")


class DolphinMotionTests(unittest.TestCase):
    def test_dolphin_advances_and_steering_clamps(self) -> None:
        dolphin = Dolphin()
        start_x = dolphin.x
        dolphin.update(1 / 30)
        self.assertGreater(dolphin.x, start_x)
        dolphin.target_y = MIN_SWIM_Y
        for _ in range(40):
            dolphin.steer(-500.0)
        self.assertEqual(dolphin.target_y, MIN_SWIM_Y)
        for _ in range(40):
            dolphin.steer(500.0)
        self.assertEqual(dolphin.target_y, MAX_SWIM_Y)

    def test_dash_near_the_surface_breaches_exactly_once(self) -> None:
        dolphin = Dolphin(y=SURFACE_Y + 60.0)
        dolphin.target_y = MIN_SWIM_Y
        dolphin.trigger_dash()
        seen: list[str] = []
        for _ in range(240):
            event = dolphin.update(1 / 30)
            if event:
                seen.append(event)
        self.assertIn("splash_out", seen)
        self.assertIn("splash_in", seen)
        self.assertEqual(seen.count("splash_out"), 1)
        self.assertEqual(seen.count("splash_in"), 1)

    def test_cruising_cannot_breach_without_a_dash(self) -> None:
        dolphin = Dolphin(y=SURFACE_Y + 60.0)
        dolphin.target_y = MIN_SWIM_Y
        for _ in range(240):
            dolphin.update(1 / 30)
            self.assertGreaterEqual(dolphin.y, SURFACE_Y - 8.0)

    def test_dash_is_bounded_in_time(self) -> None:
        dolphin = Dolphin()
        dolphin.trigger_dash()
        self.assertTrue(dolphin.is_dashing)
        for _ in range(120):
            dolphin.update(1 / 30)
        self.assertFalse(dolphin.is_dashing)

    def test_breach_flip_progress_tracks_air_time_and_lands_reset(self) -> None:
        dolphin = Dolphin(y=SURFACE_Y + 60.0)
        dolphin.target_y = MIN_SWIM_Y
        self.assertEqual(dolphin.flip_step_fraction, 0.0)
        dolphin.trigger_dash()
        peak = 0.0
        for _ in range(240):
            dolphin.update(1 / 30)
            peak = max(peak, dolphin.flip_step_fraction)
        # The somersault completes before re-entry.
        self.assertGreaterEqual(peak, 0.99)
        # Landed: the flip state is fully reset for the next leap.
        self.assertEqual(dolphin.flip_step_fraction, 0.0)

    def test_flip_progress_clamps_at_one_while_airborne(self) -> None:
        dolphin = Dolphin(y=SURFACE_Y - 40.0, airborne=True, air_time=99.0)
        self.assertEqual(dolphin.flip_step_fraction, 1.0)


class JourneyStateTests(unittest.TestCase):
    def test_fresh_journey_has_content_and_no_instant_completion(self) -> None:
        world = JourneyState()
        world.start_journey(random.Random(3))
        self.assertGreater(len(world.pearls), 0)
        self.assertGreater(len(world.decor), 0)
        self.assertEqual(world.chapters_completed, 0)
        self.assertFalse(world.finished)
        events = world.update(1 / 30, random.Random(3))
        self.assertNotIn("chapter_completed", events)
        self.assertNotIn("journey_finished", events)

    def test_crossing_a_chapter_boundary_completes_it_exactly_once(self) -> None:
        world = JourneyState()
        world.start_journey(random.Random(5))
        world.dolphin.x = chapter_start_x(1) + 5.0
        events: list[str] = []
        for _ in range(5):
            events.extend(world.update(1 / 30, random.Random(5)))
        self.assertEqual(events.count("chapter_completed"), 1)
        self.assertEqual(world.chapters_completed, 1)
        self.assertFalse(world.finished)

    def test_full_journey_completes_all_chapters_and_finishes_once(self) -> None:
        world = JourneyState()
        world.start_journey(random.Random(5))
        world.dolphin.x = TOTAL_JOURNEY_X + 10.0
        events: list[str] = []
        for _ in range(10):
            events.extend(world.update(1 / 30, random.Random(5)))
        self.assertEqual(events.count("chapter_completed"), 3)
        self.assertEqual(events.count("journey_finished"), 1)
        self.assertEqual(world.chapters_completed, 3)
        self.assertTrue(world.finished)
        # Continuing to swim must not re-emit completion facts.
        for _ in range(10):
            events.extend(world.update(1 / 30, random.Random(5)))
        self.assertEqual(events.count("journey_finished"), 1)

    def test_pearls_score_and_vanish_when_collected(self) -> None:
        world = JourneyState()
        world.start_journey(random.Random(7))
        pearl = world.pearls[0]
        world.dolphin.x = pearl.x
        world.dolphin.y = pearl.effective_y
        events = world.update(1 / 30, random.Random(7))
        self.assertTrue(pearl.collected)
        self.assertEqual(world.session_pearls, 1)
        self.assertIn("pearl_collected", events)

    def test_jellyfish_pushes_away_without_harm_and_respects_cooldown(self) -> None:
        from activities.viaggio_delfino.delfino_model import Jellyfish

        world = JourneyState()
        world.start_journey(random.Random(11))
        jelly = Jellyfish(x=world.dolphin.x + 1.0, y=world.dolphin.y, drift_amplitude=0.0)
        world.jellies.append(jelly)
        events = world.update(1 / 30, random.Random(11))
        self.assertIn("jelly_bounce", events)
        self.assertEqual(world.session_pearls, 0)
        # Cooldown: still overlapping on the next tick must not re-bounce.
        events = world.update(1 / 30, random.Random(11))
        self.assertNotIn("jelly_bounce", events)

    def test_starfish_scores_counts_and_emits_special_pickup(self) -> None:
        from activities.viaggio_delfino.delfino_model import Starfish

        world = JourneyState()
        world.start_journey(random.Random(21))
        star = Starfish(x=world.dolphin.x + 2.0, y=world.dolphin.y)
        world.starfish.append(star)
        events = world.update(1 / 30, random.Random(21))
        self.assertIn("starfish_collected", events)
        self.assertTrue(star.collected)
        self.assertEqual(world.session_pearls, 1)

    def test_starfish_spawns_respect_the_minimum_gap(self) -> None:
        world = JourneyState()
        world.start_journey(random.Random(31))
        stars_before = len(world.starfish)
        pearls_before = len(world.pearls)
        world._last_starfish_x = world.dolphin.x + 5000.0
        # Too close: the treasure degrades to a plain pearl.
        world._spawn_starfish(world._last_starfish_x + 1000.0, 300.0)
        self.assertEqual(len(world.starfish), stars_before)
        self.assertEqual(len(world.pearls), pearls_before + 1)
        # Far enough: the starfish spawns.
        world._spawn_starfish(world._last_starfish_x + 3000.0, 300.0)
        self.assertEqual(len(world.starfish), stars_before + 1)

    def test_star_and_kelp_patterns_reach_every_chapter(self) -> None:
        self.assertIn("star_solo", JourneyState._patterns_for(0))
        self.assertGreaterEqual(JourneyState._patterns_for(1).count("kelp_grove"), 2)
        self.assertIn("starfish_run", JourneyState._patterns_for(2))

    def test_kelp_grove_plants_a_dense_grove(self) -> None:
        world = JourneyState()
        world.start_journey(random.Random(37))
        before = len(world.decor)
        world._pattern_kelp_grove(5000.0, random.Random(37))
        new_kelp = sum(1 for item in world.decor[before:] if item.kind == "kelp")
        self.assertGreaterEqual(new_kelp, 6)

    def test_world_collections_stay_bounded_behind_the_camera(self) -> None:
        world = JourneyState()
        world.start_journey(random.Random(13))
        world.dolphin.x = 9000.0
        for _ in range(30):
            world.update(1 / 30, random.Random(13))
        for pearl in world.pearls:
            self.assertGreater(pearl.x, world.dolphin.x - 700.0)
        for jelly in world.jellies:
            self.assertGreater(jelly.x, world.dolphin.x - 700.0)
        self.assertLess(len(world.bubbles), 60)
        self.assertLess(len(world.particles), 200)


class _StubStorage:
    def __init__(self) -> None:
        self.data: dict[str, object] = {}

    def kv_get(self, key: str) -> object:
        return self.data.get(key)

    def kv_set(self, key: str, value: object) -> None:
        self.data[key] = value


class _StubEvents:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def chapter_completed(self, chapter_number: int) -> None:
        self.calls.append(("dolphin.chapter_completed", {"chapter_number": chapter_number}))

    def fact_opened(self, fact_id: str) -> None:
        self.calls.append(("dolphin.fact_opened", {"fact_id": fact_id}))

    def journey_score(self, score: int) -> None:
        self.calls.append(("dolphin.journey_score", {"score": score}))


class GreiaDelfinoStorageTests(unittest.TestCase):
    def test_progress_round_trip_and_sanitization(self) -> None:
        stub = _StubStorage()
        storage = GreiaDelfinoStorage(storage=stub)
        self.assertEqual(
            storage.load_progress(), {"total_pearls": 0, "best_journey_score": 0}
        )
        self.assertTrue(storage.save_progress(42, 310))
        self.assertEqual(
            storage.load_progress(), {"total_pearls": 42, "best_journey_score": 310}
        )
        stub.data[storage._key] = {
            "total_pearls": "not-a-number",
            "best_journey_score": -5,
            "junk": "ignored",
        }
        self.assertEqual(
            storage.load_progress(), {"total_pearls": 0, "best_journey_score": 0}
        )
        stub.data[storage._key] = "corrupt"
        self.assertEqual(
            storage.load_progress(), {"total_pearls": 0, "best_journey_score": 0}
        )

    def test_missing_storage_degrades_to_defaults(self) -> None:
        storage = GreiaDelfinoStorage(storage=None)
        self.assertFalse(storage.available)
        self.assertEqual(
            storage.load_progress(), {"total_pearls": 0, "best_journey_score": 0}
        )
        self.assertFalse(storage.save_progress(1, 1))


class GreiaDelfinoEventsTests(unittest.TestCase):
    def test_event_helpers_exist_with_declared_semantics(self) -> None:
        # The service wrappers must expose exactly the manifest-declared facts.
        self.assertTrue(hasattr(GreiaDelfinoEvents, "chapter_completed"))
        self.assertTrue(hasattr(GreiaDelfinoEvents, "fact_opened"))
        self.assertTrue(hasattr(GreiaDelfinoEvents, "journey_score"))


if __name__ == "__main__":
    unittest.main()
