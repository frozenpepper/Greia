from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from greia_platform.input_core import InputEdge, InputSource, SemanticAction, SemanticInputEvent
from greia_platform.localization import activity_resources
from greia_platform.system_chrome import ActivitySystemChromeLayout

from activities.acquario_magico.acquarium_assets import AquariumAssetCache
from activities.acquario_magico.acquarium_app import CHEST_RECT, build_app
from activities.acquario_magico.acquarium_content import (
    MAX_BUBBLES,
    MAX_EFFECTS,
    MISSIONS_PER_PEARL,
    SPECIES,
    STORAGE_KEY,
    ToolIndex,
)
from activities.acquario_magico.acquarium_controls import DAY_NIGHT_ID, TANK_ID
from activities.acquario_magico.acquarium_missions import (
    Mission,
    MissionDirector,
    MissionKind,
    MissionOutcome,
)
from activities.acquario_magico.acquarium_model import AquariumSession

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "acquario_magico"
RUNTIME_ASSETS = ACTIVITY_DIR / "assets" / "runtime"
APP = "activities.acquario_magico.acquarium_app"


class _MemoryStore:
    def __init__(self, data: dict | None = None) -> None:
        self.data = dict(data or {})

    def kv_get(self, key):
        return self.data.get(key)

    def kv_set(self, key, value) -> None:
        self.data[key] = json.loads(json.dumps(value))


def _press(action: SemanticAction) -> SemanticInputEvent:
    return SemanticInputEvent(action, InputEdge.PRESSED, InputSource.KEYBOARD)


class AquariumTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((64, 64))  # _draw presents with display.flip()
        cls._emit = patch(f"{APP}.emit_activity_event")
        cls.emit = cls._emit.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._emit.stop()

    def make_app(self, size=(1024, 600), locale="en", storage=None):
        screen = pygame.Surface(size)
        resources = activity_resources(ACTIVITY_DIR, requested_locale=locale)
        app = build_app(screen, resources, storage=storage, audio=Mock())
        app.rng.seed(7)
        random.seed(7)
        return app

    def tap(self, app, logical) -> None:
        physical = app.canvas.mapper.transform.logical_to_physical(logical)
        app._handle_pointer((int(physical[0]), int(physical[1])))

    def frames(self, app, count: int) -> None:
        for _ in range(count):
            app.advance(0.033)


class AquariumAssetTests(AquariumTestCase):
    def test_private_runtime_renditions_exist_beside_sources(self) -> None:
        for stem in (
            "pufferfish", "pufferfish_happy", "pufferfish_puffed", "kelp",
            "chest", "chest_open", "fish_food", "pellet", "bubble",
        ):
            png = RUNTIME_ASSETS / f"{stem}.png"
            self.assertTrue(png.exists(), stem)
            self.assertTrue((ACTIVITY_DIR / "assets" / "source" / f"{stem}.svg").exists(), stem)
            with png.open("rb") as handle:
                self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n", stem)

    def test_every_species_resolves_library_or_private_art(self) -> None:
        cache = AquariumAssetCache()
        for species in SPECIES:
            box = (species["w"], species["h"])
            for variant in ("default", "happy"):
                image = cache.creature(species, variant, box)
                self.assertIsNotNone(image, (species["id"], variant))
                self.assertLessEqual(image.get_width(), box[0])
                self.assertLessEqual(image.get_height(), box[1])
            self.assertTrue(species["visual"] or species["private"])

    def test_background_cache_has_reference_size_and_reuses_surface(self) -> None:
        cache = AquariumAssetCache()
        day = cache.background(glow_mode=False)
        night = cache.background(glow_mode=True)
        self.assertEqual(day.get_size(), (1024, 600))
        self.assertEqual(night.get_size(), (1024, 600))
        self.assertIs(cache.background(glow_mode=False), day)
        # Night is the same reef under moonlight: clearly darker water.
        self.assertLess(sum(night.get_at((512, 200))[:3]), sum(day.get_at((512, 200))[:3]))

    def test_creature_cache_supports_both_facings_and_reuses_surface(self) -> None:
        cache = AquariumAssetCache()
        clownfish = SPECIES[0]
        right = cache.creature(clownfish, "default", (84, 66), True)
        left = cache.creature(clownfish, "default", (84, 66), False)
        self.assertIsNotNone(right)
        self.assertEqual(right.get_size(), left.get_size())
        self.assertIs(cache.creature(clownfish, "default", (84, 66), True), right)

    def test_missing_shared_art_degrades_without_crashing(self) -> None:
        def missing(asset_id, variant):
            raise FileNotFoundError(asset_id)

        cache = AquariumAssetCache(resolver=missing)
        self.assertIsNone(cache.creature(SPECIES[0], "default", (84, 66)))
        self.assertEqual(cache.background(False).get_size(), (1024, 600))


class AquariumMissionDirectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = AquariumSession()
        self.session.seed_default_population()
        self.director = MissionDirector(rng=random.Random(1), first_delay=1.0)

    def test_missions_wait_for_free_play_then_invite(self) -> None:
        self.assertIs(self.director.update(0.5, self.session.creatures), MissionOutcome.NONE)
        self.assertIsNone(self.director.current)
        self.assertIs(self.director.update(0.6, self.session.creatures), MissionOutcome.STARTED)
        self.assertIsNotNone(self.director.current)

    def test_feed_missions_only_target_creatures_that_eat(self) -> None:
        eaters = {c["uid"] for c in self.session.creatures if c["spec"]["eats"]}
        for seed in range(30):
            director = MissionDirector(rng=random.Random(seed), first_delay=0.0)
            director._recent_kinds = [MissionKind.FIND]
            director.update(0.1, self.session.creatures)
            mission = director.current
            self.assertIs(mission.kind, MissionKind.FEED)
            self.assertIn(mission.target_uid, eaters)

    def test_hint_after_idle_then_quiet_retire_never_fails(self) -> None:
        self.director.update(1.1, self.session.creatures)
        outcomes = [self.director.update(0.5, self.session.creatures) for _ in range(120)]
        self.assertIn(MissionOutcome.HINT, outcomes)
        self.assertIn(MissionOutcome.RETIRED, outcomes)
        self.assertEqual(self.director.done_in_set, 0)

    def test_three_missions_earn_a_pearl(self) -> None:
        results = []
        for _ in range(MISSIONS_PER_PEARL):
            self.director._cooldown = 0
            self.director.update(0.1, self.session.creatures)
            mission = self.director.current
            target = self.session.creature_by_uid(mission.target_uid)
            if mission.kind is MissionKind.FIND:
                results.append(self.director.creature_touched(target))
            else:
                results.append(self.director.creature_ate(target["uid"]))
        self.assertEqual(results[-1], MissionOutcome.PEARL)
        self.assertTrue(all(r is MissionOutcome.COMPLETED for r in results[:-1]))
        self.assertEqual(self.director.done_in_set, 0)

    def test_evicted_target_is_replaced_or_retired(self) -> None:
        self.director._cooldown = 0
        self.director.update(0.1, self.session.creatures)
        mission = self.director.current
        others = [c for c in self.session.creatures if c["uid"] != mission.target_uid]
        outcome = self.director.update(0.1, others)
        self.assertIs(outcome, MissionOutcome.RETIRED)
        self.assertIsNone(self.director.current)

    def test_disabled_director_never_offers_missions(self) -> None:
        director = MissionDirector(first_delay=0.0, enabled=False)
        self.assertIs(director.update(5.0, self.session.creatures), MissionOutcome.NONE)


class AquariumModelTests(unittest.TestCase):
    def test_jellyfish_and_starfish_do_not_chase_food(self) -> None:
        session = AquariumSession()
        session.seed_default_population()
        jelly = next(c for c in session.creatures if c["spec"]["id"] == "jellyfish")
        session.drop_food_at(int(jelly["x"]), int(jelly["y"]))
        for _ in range(10):
            session.update(0.033)
        self.assertNotIn(jelly["uid"], session.meals)

    def test_transient_lists_are_bounded(self) -> None:
        session = AquariumSession()
        for _ in range(40):
            session.emit_bubble_storm(16, 100, 900, 300, 400)
            session.emit_effect("sparkle", 10, 10)
        self.assertLessEqual(len(session.bubbles), MAX_BUBBLES)
        self.assertLessEqual(len(session.effects), MAX_EFFECTS)

    def test_corrupt_saved_positions_are_clamped(self) -> None:
        session = AquariumSession()
        session.restore_saved_population([
            {"id": "turtle", "x": float("nan"), "y": 1e9, "facing": "x"},
            "not-a-record",
            {"id": "unknown", "x": -50, "y": 300},
        ])
        self.assertEqual(len(session.creatures), 2)
        for creature in session.creatures:
            self.assertTrue(60 <= creature["x"] <= 964)
            self.assertTrue(90 <= creature["y"] <= 470)


class AquariumAppLoopTests(AquariumTestCase):
    def test_free_play_tools_work_without_any_mission(self) -> None:
        app = self.make_app()
        app._missions.enabled = False
        start = len(app.session.creatures)
        self.tap(app, (500, 250))  # Creatures tool is selected by default
        self.assertEqual(len(app.session.creatures), start + 1)
        app._select_tool(ToolIndex.FEED)
        pellets = len(app.session.food_pellets)
        self.tap(app, (300, 200))
        self.assertGreater(len(app.session.food_pellets), pellets)
        app._select_tool(ToolIndex.BUBBLES)
        self.tap(app, (300, 200))
        self.assertGreater(len(app.session.bubbles), 0)
        self.tap(app, CHEST_RECT.center)
        self.assertGreater(app.session.chest_open_timer, 0)
        self.frames(app, 30)
        app._draw()

    def test_toolbar_is_kit_controls_and_day_night_keeps_the_tool(self) -> None:
        app = self.make_app()
        layer = app._controls.layer
        feed = layer.target("tool.feed")
        self.tap(app, feed.rect.center)
        self.assertEqual(app.session.active_tool, ToolIndex.FEED)
        self.tap(app, layer.target(DAY_NIGHT_ID).rect.center)
        self.assertTrue(app.session.glow_mode)
        self.assertEqual(app.session.active_tool, ToolIndex.FEED)
        self.assertEqual(app._controls.day_night.label, app.resources.text("tool.night").strip())

    def test_round_of_missions_plays_to_a_pearl_and_persists(self) -> None:
        store = _MemoryStore()
        app = self.make_app(storage=store)
        app._missions._cooldown = 0
        for _ in range(MISSIONS_PER_PEARL):
            self.frames(app, 2)
            mission = app._missions.current
            self.assertIsNotNone(mission)
            self.assertTrue(app._controls.mission.visible)
            target = app.session.creature_by_uid(mission.target_uid)
            if mission.kind is MissionKind.FEED:
                self.assertEqual(app.mission_hungry_uid, target["uid"])
                app._select_tool(ToolIndex.FEED)
                for _ in range(200):
                    target = app.session.creature_by_uid(mission.target_uid)
                    app.session.drop_food_at(int(target["x"]), int(target["y"]), 1)
                    self.frames(app, 1)
                    if app._missions.current is not mission:
                        break
            else:
                self.tap(app, (int(target["x"]), int(target["y"])))
            self.assertIsNot(app._missions.current, mission)
            app._missions._cooldown = 0
        self.assertEqual(app.session.stars, 1)
        self.assertGreater(app.session.chest_open_timer, 0)
        self.assertTrue(app._controls.stars.visible)
        app.audio.say.assert_any_call("celebrate.success")
        app.audio.say.assert_any_call("praise.general")
        app._autosave()
        self.assertEqual(store.data[STORAGE_KEY]["stars"], 1)
        app._draw()

    def test_missions_never_block_free_play(self) -> None:
        app = self.make_app()
        app._missions._cooldown = 0
        self.frames(app, 2)
        mission = app._missions.current
        self.assertIsNotNone(mission)
        other = next(c for c in app.session.creatures if c["spec"]["id"] != mission.species_id and c["spec"]["behavior"] != "floor")
        self.tap(app, (int(other["x"]), int(other["y"])))
        self.assertIs(app._missions.current, mission)  # no failure, mission still open
        self.assertGreater(other["name_t"], 0)
        self.assertGreater(other["happy_t"], 0)
        app._activate_tool(ToolIndex.BUBBLES)  # toolbar tap plays the tool at once
        self.assertGreater(len(app.session.bubbles), 0)

    def test_hint_points_and_highlights_the_target(self) -> None:
        app = self.make_app()
        app._missions._cooldown = 0
        self.frames(app, 2)
        self.assertIsNone(app.mission_hint_uid)
        app._request_hint()
        self.assertEqual(app.mission_hint_uid, app._missions.current.target_uid)
        app._draw()

    def test_old_v1_save_loads_and_stars_default_to_zero(self) -> None:
        old = {
            STORAGE_KEY: {
                "glow_mode": True,
                "total_fed": 12,
                "total_popped": 4,
                "creatures": [{"id": "turtle", "x": 300, "y": 200, "facing": -1}],
            }
        }
        app = self.make_app(storage=_MemoryStore(old))
        self.assertTrue(app.session.glow_mode)
        self.assertEqual(app.session.total_fed, 12)
        self.assertEqual(app.session.stars, 0)
        self.assertEqual([c["spec"]["id"] for c in app.session.creatures], ["turtle"])


class AquariumInputParityTests(AquariumTestCase):
    def test_keyboard_steers_the_tank_cursor_and_acts_there(self) -> None:
        app = self.make_app()
        layer = app._controls.layer
        self.assertEqual(layer.focused_id, TANK_ID)
        app._handle_keydown(pygame.K_RIGHT)  # first press only reveals the cursor
        self.assertTrue(layer.focus_visible)
        self.assertEqual(app.keyboard_cursor, (512, 300))
        app._handle_keydown(pygame.K_RIGHT)
        self.assertEqual(app.keyboard_cursor, (560, 300))
        count = len(app.session.creatures)
        app._handle_keydown(pygame.K_SPACE)
        self.assertEqual(len(app.session.creatures), count + 1)

    def test_cursor_is_bounded_and_leaves_the_water_to_the_toolbar(self) -> None:
        app = self.make_app()
        layer = app._controls.layer
        for _ in range(40):
            app._handle_keydown(pygame.K_LEFT)
            app._handle_keydown(pygame.K_UP)
        self.assertEqual(app.keyboard_cursor, (70, 85))
        for _ in range(20):
            app._handle_keydown(pygame.K_DOWN)
        self.assertNotEqual(layer.focused_id, TANK_ID)
        self.assertTrue(layer.focused_id.startswith("tool.") or layer.focused_id == DAY_NIGHT_ID)
        if layer.focused_id == DAY_NIGHT_ID:
            app._handle_keydown(pygame.K_LEFT)
        app._handle_keydown(pygame.K_RETURN)
        tool_by_id = {"tool.creatures": ToolIndex.SPAWN, "tool.feed": ToolIndex.FEED, "tool.bubbles": ToolIndex.BUBBLES}
        self.assertEqual(app.session.active_tool, tool_by_id[layer.focused_id])

    def test_controller_dpad_and_south_button_use_the_same_semantics(self) -> None:
        app = self.make_app()
        app._route(_press(SemanticAction.NAV_DOWN))
        app._route(_press(SemanticAction.NAV_DOWN))
        count = len(app.session.creatures)
        app._route(_press(SemanticAction.ACTIVATE))
        self.assertEqual(len(app.session.creatures), count + 1)

    def test_shortcut_keys_select_tools_and_toggle_night(self) -> None:
        app = self.make_app()
        app._handle_keydown(pygame.K_2)
        self.assertEqual(app.session.active_tool, ToolIndex.FEED)
        app._handle_keydown(pygame.K_n)
        self.assertTrue(app.session.glow_mode)
        self.assertEqual(app.session.active_tool, ToolIndex.FEED)

    def test_touch_acts_once_and_synthesized_mouse_is_ignored(self) -> None:
        app = self.make_app()
        count = len(app.session.creatures)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(512, 300), touch=True))
        self.assertEqual(len(app.session.creatures), count)
        app.handle_event(pygame.event.Event(pygame.FINGERDOWN, x=0.5, y=0.45, finger_id=1, touch_id=1, dx=0, dy=0))
        app.handle_event(pygame.event.Event(pygame.FINGERUP, x=0.5, y=0.45, finger_id=1, touch_id=1, dx=0, dy=0))
        self.assertEqual(len(app.session.creatures), count + 1)

    def test_touch_reaches_kit_toolbar(self) -> None:
        app = self.make_app()
        rect = app._controls.layer.target("tool.bubbles").rect
        x, y = rect.centerx / 1024, rect.centery / 600
        app.handle_event(pygame.event.Event(pygame.FINGERDOWN, x=x, y=y, finger_id=1, touch_id=1, dx=0, dy=0))
        app.handle_event(pygame.event.Event(pygame.FINGERUP, x=x, y=y, finger_id=1, touch_id=1, dx=0, dy=0))
        self.assertEqual(app.session.active_tool, ToolIndex.BUBBLES)

    def test_protected_home_region_taps_are_dropped(self) -> None:
        app = self.make_app()
        region = ActivitySystemChromeLayout.for_surface(1024, 600).protected_region
        count = len(app.session.creatures)
        app._handle_pointer((region.x + 5, region.y + 5))
        self.assertEqual(len(app.session.creatures), count)


class AquariumLayoutTests(AquariumTestCase):
    def test_controls_stay_outside_protected_chrome_at_supported_sizes(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            app = self.make_app(size=size)
            app._controls.set_mission("feed", "clownfish", 1)
            app._controls.set_stars(3)
            protected = app._controls._layout.protected
            for target in app._controls.layer.targets:
                if target.control_id == TANK_ID:
                    continue
                self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))
                self.assertTrue(pygame.Rect(0, 0, 1024, 600).contains(target.rect), (size, target.control_id))

    def test_keyboard_hint_rests_above_the_bar_end_and_lights_the_pressed_key(self) -> None:
        from greia_platform.activity_keyboard_hint import KeyCap

        for size in ((1024, 600), (800, 480)):
            app = self.make_app(size=size)
            controls = app._controls
            keys = controls.keys
            self.assertTrue(keys.visible, "shown at start")
            self.assertEqual(keys.active, {KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
            day = controls.day_night.rect
            self.assertEqual(keys.rect.right, day.right, "at the right end of the bottom bar")
            self.assertLessEqual(day.top - keys.rect.bottom, 10)
            self.assertGreaterEqual(day.top - keys.rect.bottom, 0)
            self.assertFalse(keys.rect.colliderect(CHEST_RECT))
            self.assertFalse(keys.rect.colliderect(controls._layout.protected))
            for target in controls.layer.targets:
                if target.control_id != TANK_ID and target.visible:
                    self.assertFalse(keys.rect.colliderect(target.rect), target.control_id)
            self.assertNotIn(keys, list(controls.layer.targets), "display-only, never a focus target")
            smallest = min(r.height for r in keys.key_rects().values()) * controls._layout.scale
            self.assertGreaterEqual(smallest, 25, "legible keycaps")
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode="", scancode=0))
        self.assertIn(KeyCap.SPACE, keys.lit)
        app.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE, mod=0, unicode="", scancode=0))
        app._draw()

    def test_it_and_en_render_every_state(self) -> None:
        for locale in ("en", "it"):
            app = self.make_app(locale=locale)
            app._missions.current = Mission(MissionKind.FEED, "clownfish", app.session.creatures[0]["uid"])
            app._sync_controls()
            self.assertTrue(app._controls.mission.text)
            app._toggle_glow_mode()
            self.frames(app, 3)
            app._draw()


class AquariumLocaleTests(unittest.TestCase):
    def test_four_locales_keep_key_parity_and_cover_mission_text(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"])
        for locale, strings in bundles.items():
            self.assertEqual(set(strings), keys, locale)
        for species in SPECIES:
            self.assertIn(f"mission.find.{species['id']}", keys)
            self.assertIn(species["name_key"], keys)
            if species["eats"]:
                self.assertIn(f"mission.feed.{species['id']}", keys)


class AquariumLoopContractTests(unittest.TestCase):
    """The run loop and milestone events, on a minimally wired app."""

    def test_run_processes_queued_child_input_before_rendering(self) -> None:
        from activities.acquario_magico.acquarium_app import AquariumApp

        app = object.__new__(AquariumApp)
        app._running = True
        app.handle_event = Mock()
        app._step_frame = Mock()
        app._autosave = Mock()
        events = [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (300, 300)}),
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}),
        ]
        with patch("activities.acquario_magico.acquarium_app.activity_stop_requested", side_effect=[False, True]), patch(
            "activities.acquario_magico.acquarium_app.pygame.event.get", return_value=events
        ):
            self.assertEqual(app.run(), 0)
        self.assertEqual(app.handle_event.call_count, 2)
        app.handle_event.assert_any_call(events[0])
        app._step_frame.assert_called_once_with(0.033)
        app._autosave.assert_called_once()

    def test_milestones_come_from_real_model_transitions(self) -> None:
        from activities.acquario_magico.acquarium_app import AquariumApp

        app = object.__new__(AquariumApp)
        app.session = Mock(total_fed=0, glow_mode=False)
        app.session.update.side_effect = lambda dt: setattr(app.session, "total_fed", 2)
        app.audio = Mock()
        app.storage = None
        app._draw = Mock()
        app.ready_published = True
        app.clock = Mock()
        with patch("activities.acquario_magico.acquarium_app.emit_activity_event") as emit:
            app._step_frame(0.033)
            app._toggle_glow_mode()
        self.assertEqual(emit.call_args_list[0].args, ("aquarium.fish_fed", {"count": 2, "total_fed": 2}))
        self.assertEqual(emit.call_args_list[1].args, ("aquarium.glow_mode_toggled", {"glow_mode": True}))

    def test_taps_on_platform_chrome_are_rejected(self) -> None:
        from activities.acquario_magico.acquarium_app import _is_safe_point
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        surface = pygame.Surface((1024, 600))
        region = activity_viewport_for_surface(surface).protected_regions[0]
        self.assertFalse(_is_safe_point(surface, (int(region.x) + 1, int(region.y) + 1)))
        self.assertTrue(_is_safe_point(surface, (500, 300)))


if __name__ == "__main__":
    unittest.main()
