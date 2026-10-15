"""Tests for Sottomarino Giramondo (model, voice queue, art cache and app loop)."""

import json
import os
import random
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
ACTIVITY_DIR = Path(__file__).parent.parent / "activities" / "sottomarino_giramondo"
if str(ACTIVITY_DIR) not in sys.path:
    sys.path.insert(0, str(ACTIVITY_DIR))

import pygame  # noqa: E402

from sub_model import (  # noqa: E402
    FACT_SPECIES,
    MAX_DEPTH,
    MIN_DEPTH,
    ORDER_EXPIRE_SECONDS,
    ORDER_HINT_SECONDS,
    ORDERS_PER_STAR,
    BiomeType,
    EncounterType,
    SubmarineLog,
    SubmarineModel,
    get_biome,
)
from sub_audio import SpeechPriority, SpeechQueue  # noqa: E402


class _MemoryStore:
    """In-memory stand-in for Greia Storage (the host disk may refuse writes)."""

    def __init__(self, payload=None):
        self.payload = payload
        self.saves = 0

    def load(self):
        return SubmarineLog.from_payload(self.payload)

    def save(self, log):
        self.payload = log.export()
        self.saves += 1
        return True


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def _make_app(store=None, seed=7):
    if pygame.display.get_surface() is None:
        pygame.init()
        pygame.display.set_mode((1024, 600))
    from sub_app import SubmarineApp

    clock = _Clock()
    app = SubmarineApp(rng=random.Random(seed), clock=clock, store=store or _MemoryStore())
    app.test_clock = clock
    return app


def _step(app, seconds, dt=1 / 30):
    for _ in range(int(round(seconds / dt))):
        app.test_clock.now += dt
        app.advance(dt)


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0)


def _physical(app, logical):
    x, y = app.canvas.mapper.transform.logical_to_physical(logical)
    return int(round(x)), int(round(y))


class SottomarinoModelTests(unittest.TestCase):
    def test_submarine_manifest_matches_gameplay(self):
        import tomllib

        with (ACTIVITY_DIR / "activity.toml").open("rb") as source:
            data = tomllib.load(source)
        events = {item["id"] for item in data["education"]["events"]}
        self.assertIn("submarine.order_completed", events)
        self.assertNotIn("submarine.depth_milestone", events)
        self.assertNotIn("create", data["presentation"]["categories"])
        self.assertEqual(data["activity"]["id"], "org.greia.sottomarino-giramondo")
        self.assertEqual(set(data["activity"]["languages"]), {"it", "en"})

    def test_biome_transitions(self):
        self.assertEqual(get_biome(0.0), BiomeType.SHALLOW_REEF)
        self.assertEqual(get_biome(24.9), BiomeType.SHALLOW_REEF)
        self.assertEqual(get_biome(25.0), BiomeType.TWILIGHT_KELP)
        self.assertEqual(get_biome(64.9), BiomeType.TWILIGHT_KELP)
        self.assertEqual(get_biome(65.0), BiomeType.MIDNIGHT_ABYSS)
        self.assertEqual(get_biome(100.0), BiomeType.MIDNIGHT_ABYSS)

    def test_submarine_initial_state(self):
        model = SubmarineModel(rng=random.Random(1))
        self.assertEqual(model.depth, 5.0)
        self.assertEqual(model.speed, 0.5)
        self.assertFalse(model.lights_on)
        self.assertGreaterEqual(len(model.entities), 20)
        self.assertEqual(model.encounter.active_type, EncounterType.NONE)

    def test_submarine_controls(self):
        model = SubmarineModel(rng=random.Random(1))
        self.assertTrue(model.toggle_lights())
        model.trigger_sonar()
        self.assertTrue(model.sonar_active)
        model.set_speed(1.0)
        self.assertEqual(model.speed, 1.0)
        model.set_speed(0.0)
        self.assertEqual(model.speed, 0.0)

    def test_encounter_lifecycle(self):
        model = SubmarineModel(rng=random.Random(1))
        model.encounter.active_type = EncounterType.OCTOPUS_HUG
        self.assertTrue(model.resolve_encounter())
        self.assertTrue(model.encounter.solved)
        self.assertFalse(model.resolve_encounter())
        model.update(0.25)
        for _ in range(10):
            model.update(0.25)
        self.assertEqual(model.encounter.active_type, EncounterType.NONE)

    def test_order_condition_satisfaction(self):
        model = SubmarineModel(rng=random.Random(1))
        model.current_order.active = True
        model.current_order.order_id = "bubbles"
        self.assertFalse(model.check_action("horn"))
        self.assertFalse(model.current_order.solved)
        self.assertTrue(model.check_action("bubbles"))
        self.assertTrue(model.current_order.solved)

    def test_orders_hint_after_delay_or_two_other_instruments_and_fade_when_ignored(self):
        model = SubmarineModel(rng=random.Random(2))
        model._encounter_cooldown = 999
        model._order_cooldown = 0.0
        model.update(0.05)
        order = model.current_order
        self.assertTrue(order.waiting)
        self.assertFalse(order.hinted, "the order must be listened to first (no answer shown)")
        for _ in range(int(ORDER_HINT_SECONDS / 0.1) + 1):
            model.update(0.1)
        self.assertTrue(model.current_order.hinted)

        model2 = SubmarineModel(rng=random.Random(3))
        model2._encounter_cooldown = 999
        model2._order_cooldown = 0.0
        model2.update(0.05)
        model2.note_other_instrument()
        self.assertFalse(model2.current_order.hinted)
        model2.note_other_instrument()
        self.assertTrue(model2.current_order.hinted)

        ignored = model.current_order
        for _ in range(int(ORDER_EXPIRE_SECONDS / 0.25) + 2):
            model.update(0.25)
        self.assertIsNot(model.current_order, ignored, "an ignored order fades quietly")
        self.assertFalse(ignored.solved)

    def test_three_followed_orders_earn_a_star(self):
        model = SubmarineModel(rng=random.Random(4))
        self.assertFalse(model.record_order_followed())
        self.assertFalse(model.record_order_followed())
        self.assertEqual(ORDERS_PER_STAR, 3)
        self.assertTrue(model.record_order_followed())
        self.assertEqual(model.log.stars, 1)
        self.assertEqual(model.orders_in_set, 0)

    def test_species_facts_rotate_through_every_recording(self):
        model = SubmarineModel(rng=random.Random(1))
        seen = []
        for _ in range(5):
            self.assertTrue(model.trigger_species_fact("dolphin"))
            seen.append(model.active_fact.text_key)
        self.assertEqual(seen[:4], [f"voice.fact.dolphin.{i}" for i in range(1, 5)])
        self.assertEqual(seen[4], "voice.fact.dolphin.1")
        self.assertGreater(model.active_fact.display_timer, 0.0)
        # The anglerfish has no recorded facts: name card only.
        self.assertTrue(model.trigger_species_fact("angler"))
        self.assertEqual(model.active_fact.cue_key, "")
        self.assertFalse(model.trigger_species_fact("bubble"))

    def test_every_fact_key_has_text_and_audio_in_every_bundle(self):
        for locale in ("en", "it", "es", "fr"):
            strings = json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for species in FACT_SPECIES:
                for index in range(1, 5):
                    with self.subTest(locale=locale, species=species, index=index):
                        self.assertTrue(strings[f"voice.fact.{species}.{index}"].strip())
                        self.assertTrue((ACTIVITY_DIR / "audio" / locale / f"sub_fact_{species}_{index}.wav").is_file())

    def test_bundles_have_identical_keys(self):
        bundles = {
            locale: set(json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"])
            for locale in ("en", "it", "es", "fr")
        }
        for locale, keys in bundles.items():
            self.assertEqual(keys, bundles["en"], locale)

    def test_dive_and_surface_reach_every_zone(self):
        model = SubmarineModel(rng=random.Random(5))
        seen = {get_biome(model.depth)}
        for _ in range(8):
            model.change_depth(+1)
            for _ in range(60):
                model.update(0.1)
            seen.add(get_biome(model.depth))
        self.assertEqual(seen, set(BiomeType))
        self.assertEqual(model.target_depth, MAX_DEPTH)
        kinds = {e.kind for e in model.entities}
        self.assertTrue(kinds & {"angler", "whale", "krill"}, "the abyss shows its own creatures")
        for _ in range(12):
            model.change_depth(-1)
        self.assertEqual(model.target_depth, MIN_DEPTH)

    def test_population_and_bubble_bursts_stay_bounded(self):
        model = SubmarineModel(rng=random.Random(6))
        for _ in range(50):
            model.trigger_bubbles()
            model.update(0.05)
        self.assertLessEqual(len(model.entities), 26 + 24)

    def test_log_payload_is_sanitised(self):
        log = SubmarineLog.from_payload({"stars": 4, "species": ["whale", "../etc", 3, "whale"]})
        self.assertEqual(log.stars, 4)
        self.assertEqual(log.export(), {"schema": 1, "stars": 4, "species": ["whale"]})
        self.assertEqual(SubmarineLog.from_payload(None).stars, 0)
        self.assertEqual(SubmarineLog.from_payload({"stars": "lots"}).stars, 0)


class SpeechQueueTests(unittest.TestCase):
    def test_queue_is_bounded_prioritised_and_drops_stale_facts(self):
        queue = SpeechQueue(capacity=3, repeat_gap=4.0, stale_after=6.0, pause=0.0)
        for index in range(6):
            queue.push(f"voice.fact.whale.{index}", SpeechPriority.LOW)
        self.assertEqual(len(queue.pending), 3)
        queue.push("voice.order.left", SpeechPriority.URGENT)
        self.assertEqual(queue.pending[0], "voice.order.left")
        self.assertNotIn("voice.fact.whale.0", queue.pending, "an order clears waiting facts")
        spoken = []
        queue.update(0.1, False, lambda key: spoken.append(key) or True)
        self.assertEqual(spoken, ["voice.order.left"])
        # Same cue is not repeated within the gap unless forced (replay).
        self.assertFalse(queue.push("voice.order.left", SpeechPriority.URGENT))
        self.assertTrue(queue.push("voice.order.left", SpeechPriority.URGENT, force=True))
        queue.clear()
        queue.push("voice.creature.whale", SpeechPriority.NORMAL)
        queue.update(7.0, True, lambda key: True)  # channel busy for 7 s
        spoken.clear()
        queue.update(0.1, False, lambda key: spoken.append(key) or True)
        self.assertEqual(spoken, [], "a name heard long after the creature passed is dropped")


class SottomarinoAppTests(unittest.TestCase):
    def test_platform_home_pointer_not_used_as_cockpit_input(self):
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        app = _make_app()
        protected = activity_viewport_for_surface(app.screen).protected_regions[0]
        self.assertIsNone(app._safe_pointer((int(protected.x) + 1, int(protected.y) + 1)))
        self.assertIsNone(app._safe_pointer((-3, 200)))
        depth = app.model.target_depth
        app.tap((int(protected.x) + 2, int(protected.y) + 2))
        self.assertEqual(app.model.target_depth, depth)

    def test_arrows_dpad_and_stick_pilot_the_sub_directly(self):
        from greia_platform.pygame_input import CONTROLLER_BUTTON_DPAD_DOWN, CONTROLLER_BUTTON_DPAD_LEFT
        from sub_cockpit_view import BUTTON_RECTS

        app = _make_app()
        start = app.model.target_depth
        # Keyboard arrows: down dives, up surfaces, left/right steer (as before).
        app.handle_event(_key(pygame.K_DOWN))
        self.assertGreater(app.model.target_depth, start)
        app.handle_event(_key(pygame.K_UP))
        self.assertEqual(app.model.target_depth, start)
        app.handle_event(_key(pygame.K_LEFT))
        self.assertLess(app.model.heading, 0.0)
        app.handle_event(_key(pygame.K_RIGHT))
        app.handle_event(_key(pygame.K_RIGHT))
        self.assertGreater(app.model.heading, 0.0)
        self.assertFalse(app.controls.layer.focus_visible, "piloting never shows the focus ring")

        # Controller D-pad (brand-neutral SDL events).
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_DPAD_DOWN))
        self.assertGreater(app.model.target_depth, start)
        heading = app.model.heading
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_DPAD_LEFT))
        self.assertLess(app.model.heading, heading)

        # Left stick pushed down dives (central dead zone + repeat policy).
        depth = app.model.target_depth
        app.handle_event(pygame.event.Event(pygame.CONTROLLERAXISMOTION, axis=pygame.CONTROLLER_AXIS_LEFTY, value=32000))
        self.assertGreater(app.model.target_depth, depth)

        # Pointer: tap on the Dive button.
        depth = app.model.target_depth
        app.tap(_physical(app, BUTTON_RECTS["dive"].center))
        self.assertGreater(app.model.target_depth, depth)

        # Repeated dives reach the abyss.
        for _ in range(8):
            app.handle_event(_key(pygame.K_DOWN))
        _step(app, 8.0)
        self.assertEqual(get_biome(app.model.depth), BiomeType.MIDNIGHT_ABYSS)

    def test_space_sounds_the_alarm_unless_the_focus_ring_is_shown(self):
        from greia_platform.pygame_input import CONTROLLER_BUTTON_A, CONTROLLER_BUTTON_RIGHTSHOULDER

        app = _make_app()
        app.model.encounter.active_type = EncounterType.SHARK_WAVE
        app.handle_event(_key(pygame.K_SPACE))
        self.assertTrue(app.model.encounter.solved, "Space keeps its original alarm action")

        layer = app.controls.layer
        app.handle_event(_key(pygame.K_TAB))
        self.assertTrue(layer.focus_visible)
        self.assertEqual(layer.focused_id, "action")
        app.handle_event(_key(pygame.K_TAB))
        self.assertEqual(layer.focused_id, "bubbles")
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_LSHIFT, unicode="", scancode=0))
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_LSHIFT, unicode="", scancode=0))
        self.assertEqual(layer.focused_id, "sonar")
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_RIGHTSHOULDER))
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_RIGHTSHOULDER))
        self.assertEqual(layer.focused_id, "bubbles")
        before = len(app.model.entities)
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_A))
        self.assertGreater(len(app.model.entities), before, "south presses the focused control")
        # Arrows still pilot while the ring is shown.
        depth = app.model.target_depth
        app.handle_event(_key(pygame.K_DOWN))
        self.assertGreater(app.model.target_depth, depth)
        self.assertEqual(layer.focused_id, "bubbles")

    def test_letter_shortcuts_still_work(self):
        app = _make_app()
        app.handle_event(_key(pygame.K_l))
        self.assertTrue(app.model.lights_on)
        app.handle_event(_key(pygame.K_x))
        self.assertEqual(app.model.speed, 0.0)

    def test_octopus_bubbles_resolution_and_frame(self):
        app = _make_app()
        app.model.encounter.active_type = EncounterType.OCTOPUS_HUG
        app.model.encounter.progress = 1.0
        app.press("bubbles")
        self.assertTrue(app.model.encounter.solved)
        self.assertEqual(app.captain.feedback.pose.value, "cheer")
        app.draw()

    def test_shark_waits_for_lights_and_banner_is_pictorial(self):
        app = _make_app()
        app.model._order_cooldown = 999
        spoken = []
        app._speak_now = lambda key: spoken.append(key) or True
        app.model.encounter.active_type = EncounterType.SHARK_WAVE
        _step(app, 0.5)
        self.assertEqual(app.controls.banner_key, ("encounter", "shark_wave"))
        self.assertIsNotNone(app.controls.banner.icon)
        self.assertIn("voice.encounter.shark", spoken)
        app.press("sonar")
        self.assertFalse(app.model.encounter.solved)
        app.press("light")
        self.assertTrue(app.model.encounter.solved)

    def test_tapping_a_creature_names_it_and_tells_a_fact(self):
        app = _make_app()
        app.model._order_cooldown = 999
        app.model._encounter_cooldown = 999
        _step(app, 0.2)
        app.draw()
        from sub_cockpit_view import in_porthole

        candidates = [(rect, kind) for rect, kind in app.presenter.creature_rects if in_porthole(rect.center, 30)]
        self.assertTrue(candidates)
        rect, kind = candidates[-1]
        app.speech.clear()
        app.tap(_physical(app, rect.center))
        self.assertEqual(app.model.active_fact.species, app.presenter.creature_at(rect.center) or kind)
        self.assertIn(app.creature_cue(app.model.active_fact.species), app.speech.pending)
        _step(app, 0.1)
        self.assertEqual(app.controls.banner_key[0], "creature")

    def test_creature_name_cues_resolve_to_recordings(self):
        app = _make_app()
        for kind in ("clownfish", "turtle", "dolphin", "manta", "angler", "whale", "coral", "kelp", "krill"):
            with self.subTest(kind=kind):
                self.assertIsNotNone(app.resources.audio_path(app.creature_cue(kind)))

    def test_app_loop_follows_orders_to_a_star_and_saves(self):
        store = _MemoryStore({"stars": 2, "species": ["turtle"]})
        app = _make_app(store)
        self.assertEqual(app.controls.stars.value, 2, "existing saves load")
        spoken = []
        app._speak_now = lambda key: spoken.append(key) or True
        app.model._encounter_cooldown = 999
        followed = 0
        for _ in range(ORDERS_PER_STAR):
            app.model._order_cooldown = 0.0
            _step(app, 0.6)
            order = app.model.current_order
            self.assertTrue(order.waiting)
            self.assertEqual(app.controls.banner_key, ("order", order.order_id))
            self.assertIn(order.cue_key, spoken, "Leo speaks every order")
            _step(app, ORDER_HINT_SECONDS + 0.2)
            self.assertEqual(app.controls.banner_key, ("order_hint", order.order_id))
            self.assertTrue(app.captain.pointing)
            app.press(order.target)
            followed += 1
            self.assertTrue(app.model.current_order.solved)
            _step(app, 2.5)
            self.assertFalse(app.model.current_order.active)
            app.draw()
        self.assertEqual(followed, 3)
        self.assertEqual(app.model.log.stars, 3)
        self.assertEqual(app.controls.stars.value, 3)
        self.assertGreaterEqual(store.saves, 1)
        self.assertEqual(store.payload["stars"], 3)
        self.assertIn("turtle", store.payload["species"])

    def test_frames_render_at_every_supported_size(self):
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                pygame.display.set_mode(size)
                app = _make_app()
                _step(app, 1.0)
                app.draw()
                self.assertEqual(app.screen.get_size(), size)
        pygame.display.set_mode((1024, 600))

    def test_perspective_sprite_cache_is_bounded(self):
        app = _make_app()
        for kind in ("whale", "clownfish", "manta", "coral"):
            for longest in range(8, 400, 3):
                app.art.scaled(kind, longest)
                app.art.scaled(kind, longest, flip=True)
        self.assertLessEqual(app.art.scaled_count, 192)
        self.assertIsNotNone(app.art.get_sprite("octopus"))
        self.assertIsNotNone(app.art.get_sprite("whale"))


if __name__ == "__main__":
    unittest.main()
