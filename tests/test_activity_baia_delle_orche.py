from __future__ import annotations

import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import Mock

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from activities.baia_delle_orche.orca_assets import OrcaAssetCache, quantize_angle
from activities.baia_delle_orche.orca_content import (
    ASSETS_DIR,
    FOOD_ART,
    MISSIONS_PER_STAR,
    ORCA_LOOKS,
    STORAGE_KEY,
    Tool,
)
from activities.baia_delle_orche.orca_missions import (
    Mission,
    MissionDirector,
    MissionKind,
    MissionOutcome,
)
from activities.baia_delle_orche.orca_model import (
    FoodType,
    OrcaPod,
    OrcaState,
    ToyEntity,
    WATER_SURFACE_Y,
)
from activities.baia_delle_orche.orca_renderer import OrcaRenderer
from activities.baia_delle_orche.orca_services import GreiaOrcaEvents, GreiaOrcaProgress
from greia_platform.activity_api import get_shared_visual_path
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
    shared_character_audio_path,
)
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "baia_delle_orche"


def _resources(locale: str = "it") -> LocalizedResources:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(locale, support)
    assert context is not None
    return LocalizedResources(ACTIVITY_DIR, context)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class BaiaDelleOrcheModelTests(unittest.TestCase):
    def test_orca_pod_members_and_morphology(self) -> None:
        pod = OrcaPod()
        self.assertEqual([orca.id for orca in pod.orcas], ["kiko", "luna", "oskar"])
        self.assertLess(pod.orcas[0].scale, 1.0)
        self.assertEqual(pod.orcas[1].scale, 1.0)
        self.assertGreater(pod.orcas[2].scale, 1.0)
        for orca in pod.orcas:
            self.assertGreater(orca.width, 0)
            self.assertGreater(orca.height, 0)
            self.assertEqual(orca.state, OrcaState.SWIMMING)

    def test_cuddle_state_transition_and_happiness_fades(self) -> None:
        pod = OrcaPod()
        kiko = pod.orcas[0]
        kiko.trigger_cuddle()
        self.assertEqual(kiko.state, OrcaState.CUDDLE_BELLY)
        self.assertTrue(kiko.is_happy)
        kiko.update(3.0, pod.foods, pod.toys, night_mode=False)
        self.assertEqual(kiko.state, OrcaState.SWIMMING)
        # A cuddle no longer leaves the orca on its happy face forever.
        self.assertFalse(kiko.is_happy)

    def test_breaching_jump_returns_to_swimming_with_feedback(self) -> None:
        pod = OrcaPod()
        luna = pod.orcas[1]
        luna.trigger_breach(jump_x=600.0, height_bonus=30.0)
        self.assertEqual(luna.state, OrcaState.BREACHING)
        luna.update(0.4, pod.foods, pod.toys, night_mode=False)
        events = luna.update(1.2, pod.foods, pod.toys, night_mode=False)
        self.assertEqual(luna.state, OrcaState.SWIMMING)
        self.assertIn("splash", events)
        self.assertIn("whistle", events)

    def test_orcas_sleep_at_night_and_wake_by_day(self) -> None:
        pod = OrcaPod()
        pod.night_mode = True
        pod.update(0.033)
        self.assertTrue(all(o.state == OrcaState.SLEEPING for o in pod.orcas))
        pod.night_mode = False
        pod.update(0.033)
        self.assertTrue(all(o.state == OrcaState.SWIMMING for o in pod.orcas))

    def test_food_and_toy_physics(self) -> None:
        pod = OrcaPod()
        food = pod.spawn_food(x=pod.orcas[0].x, y=pod.orcas[0].y - 20.0, kind=FoodType.HERRING)
        self.assertIn(food, pod.foods)
        pod.update(0.1)

        ball = ToyEntity("ball", 400.0, WATER_SURFACE_Y - 50.0)
        ball.update(0.033)
        self.assertGreater(ball.vy, 0.0)
        ball.y = WATER_SURFACE_Y + 20.0
        ball.update(0.033)
        self.assertLess(ball.vy, 0.0)

    def test_eating_records_the_meal_and_whether_it_was_craved(self) -> None:
        pod = OrcaPod(rng=random.Random(1))
        oskar = pod.orca("oskar")
        assert oskar is not None
        oskar.craved_food = FoodType.SQUID
        pod.spawn_food(oskar.x, oskar.y, kind=FoodType.SQUID)
        for _ in range(10):
            pod.update(0.033)
            if pod.meals:
                break
        self.assertIn(("oskar", "squid", True), pod.meals)
        self.assertEqual(pod.total_fed, 1)

    def test_transient_lists_are_bounded(self) -> None:
        pod = OrcaPod()
        for index in range(200):
            pod.spawn_food(10.0 + index, 10.0)
            pod.emit_effect("sparkle", 10.0, 10.0)
        self.assertLessEqual(len(pod.foods), 24)
        self.assertLessEqual(len(pod.effects), 24)

    def test_progress_export_and_restore(self) -> None:
        pod = OrcaPod()
        pod.total_fed = 12
        pod.total_cuddled = 8
        pod.total_acrobatics = 5
        pod.total_songs = 3
        pod.night_mode = True
        pod.stars = 2
        pod.selected_food = FoodType.SQUID
        pod.trigger_fact("fact_breach")

        restored = OrcaPod()
        restored.restore_progress(pod.export_progress())
        self.assertEqual(restored.total_fed, 12)
        self.assertEqual(restored.total_cuddled, 8)
        self.assertEqual(restored.total_acrobatics, 5)
        self.assertEqual(restored.total_songs, 3)
        self.assertEqual(restored.stars, 2)
        self.assertEqual(restored.selected_food, FoodType.SQUID)
        self.assertTrue(restored.night_mode)
        # The next fact is the first one this child has not heard.
        self.assertEqual(restored.trigger_fact(), "fact_swallow")

    def test_legacy_and_corrupt_saves_load_without_losing_data(self) -> None:
        legacy = {
            "total_fed": 40,
            "total_cuddled": 9,
            "total_acrobatics": 3,
            "total_songs": 1,
            "night_mode": False,
            "discovered_facts": ["fact_breach", "fact_pod", "not_a_fact"],
        }
        pod = OrcaPod()
        pod.restore_progress(legacy)
        self.assertEqual(pod.total_fed, 40)
        self.assertEqual(pod.discovered_facts, {"fact_breach", "fact_pod"})
        self.assertEqual(pod.stars, 0)
        corrupt = OrcaPod()
        corrupt.restore_progress({"total_fed": "lots", "stars": -4, "food": "seal", "discovered_facts": 7})
        self.assertEqual(corrupt.total_fed, 0)
        self.assertEqual(corrupt.stars, 0)
        self.assertEqual(corrupt.selected_food, FoodType.SALMON)
        corrupt.restore_progress(None)  # never raises
        self.assertEqual(GreiaOrcaProgress()._key, STORAGE_KEY)


class OrcaMissionDirectorTests(unittest.TestCase):
    def test_invitations_wait_for_free_play_and_daylight(self) -> None:
        director = MissionDirector(rng=random.Random(2), first_delay=5.0)
        self.assertIs(director.update(4.0, daytime=True), MissionOutcome.NONE)
        self.assertIs(director.update(60.0, daytime=False), MissionOutcome.NONE)
        self.assertIs(director.update(1.5, daytime=True), MissionOutcome.STARTED)
        self.assertIsNotNone(director.current)
        # Night falls: the invitation quietly retires (never a failure).
        self.assertIs(director.update(0.1, daytime=False), MissionOutcome.RETIRED)
        self.assertIsNone(director.current)

    def test_feed_invitation_needs_the_wanted_food_and_never_fails(self) -> None:
        director = MissionDirector(rng=random.Random(2), first_delay=0.0)
        director.current = Mission(MissionKind.FEED, "kiko", FoodType.SQUID)
        self.assertIs(director.orca_ate("luna", "squid"), MissionOutcome.NONE)
        self.assertIs(director.orca_ate("kiko", "herring"), MissionOutcome.NOT_YET)
        self.assertIsNotNone(director.current)
        self.assertIs(director.orca_ate("kiko", "squid"), MissionOutcome.COMPLETED)

    def test_hint_after_idle_and_every_third_invitation_earns_a_star(self) -> None:
        director = MissionDirector(rng=random.Random(4), first_delay=0.0)
        director.update(0.1, daytime=True)
        self.assertIs(director.update(6.5, daytime=True), MissionOutcome.HINT)
        outcomes = []
        for _ in range(MISSIONS_PER_STAR):
            if director.current is None:
                director._cooldown = 0.0
                director.update(0.1, daytime=True)
            mission = director.current
            assert mission is not None
            if mission.kind is MissionKind.FIND:
                outcomes.append(director.orca_touched(mission.orca_id))
            elif mission.kind is MissionKind.JUMP:
                outcomes.append(director.orca_jumped(mission.orca_id))
            else:
                outcomes.append(director.orca_ate(mission.orca_id, mission.food.value))
        self.assertEqual(outcomes[-1], MissionOutcome.STAR)
        self.assertEqual(director.done_in_set, 0)


class BaiaDelleOrcheArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def test_three_orcas_use_library_or_private_art_and_stay_distinct(self) -> None:
        sources = set()
        for orca_id, look in ORCA_LOOKS.items():
            for variant in ("default", "happy", "asleep"):
                if look.art.shared:
                    path = get_shared_visual_path(look.art.shared, variant=variant)
                else:
                    suffix = "" if variant == "default" else f"_{variant}"
                    path = ASSETS_DIR / f"{look.art.private}{suffix}.png"
                    self.assertTrue((ACTIVITY_DIR / "assets" / "source" / f"{look.art.private}{suffix}.svg").is_file())
                self.assertTrue(Path(path).is_file(), path)
            sources.add(look.art)
        self.assertEqual(len(sources), 3)
        widths = [ORCA_LOOKS[o].box[0] for o in ("kiko", "luna", "oskar")]
        self.assertEqual(widths, sorted(widths))

    def test_private_runtime_art_has_a_source_and_old_sourceless_pngs_are_gone(self) -> None:
        runtime = sorted(path.stem for path in ASSETS_DIR.glob("*.png"))
        for stem in runtime:
            self.assertTrue((ACTIVITY_DIR / "assets" / "source" / f"{stem}.svg").is_file(), stem)
        for art in FOOD_ART.values():
            if art.private:
                self.assertIn(art.private, runtime)
        self.assertNotIn("tito_avatar", runtime)

    def test_rotated_sprite_cache_stays_bounded(self) -> None:
        assets = OrcaAssetCache()
        for angle in range(-90, 90):
            for facing in (True, False):
                for orca_id in ORCA_LOOKS:
                    assets.orca(orca_id, "happy", facing, float(angle))
        self.assertLessEqual(assets.scaled_count, 128)
        self.assertEqual(quantize_angle(3.1), 6)
        self.assertEqual(quantize_angle(-90.0), -30)

    def test_tito_voice_uses_the_shared_character_library(self) -> None:
        for locale in ("en", "it"):
            for cue in ("celebrate.success", "praise.general"):
                path = shared_character_audio_path(PROJECT_ROOT, "tito", cue, locale)
                self.assertIsNotNone(path)
                self.assertIn(f"tito__{locale}__", path.name)
        source = "\n".join(path.read_text() for path in ACTIVITY_DIR.glob("*.py"))
        self.assertNotIn("../", source)
        self.assertIn("shared_character_audio_path", (ACTIVITY_DIR / "orca_audio.py").read_text())

    def test_mission_strings_exist_in_every_locale(self) -> None:
        for locale in ("en", "it", "es", "fr"):
            strings = json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for kind in MissionKind:
                for orca_id in ORCA_LOOKS:
                    self.assertTrue(strings.get(f"mission.{kind.value}.{orca_id}"), (locale, kind, orca_id))


class BaiaDelleOrcheAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600), pygame.HIDDEN)

    def _app(self, *, missions: bool = False, size=(1024, 600), seed: int = 5):
        from activities.baia_delle_orche.orca_app import OrcaBayActivity
        from greia_platform.pygame_canvas import PygameReferenceCanvas

        screen = pygame.Surface(size)
        clock = _Clock()
        pod = OrcaPod(rng=random.Random(seed))
        events = Mock()
        app = OrcaBayActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            pod=pod,
            renderer=OrcaRenderer(GreiaTypography(), _resources()),
            audio=Mock(),
            progress=Mock(),
            events=events,
            missions_enabled=missions,
            rng=random.Random(seed),
            clock=clock,
        )
        return app, pod, events, clock

    def _step(self, app, clock, frames: int = 1) -> None:
        for _ in range(frames):
            clock.now += 0.033
            app.advance(0.033)

    def test_renderer_handles_day_night_and_fact_bubble(self) -> None:
        app, pod, _, clock = self._app()
        app.draw()
        pod.night_mode = True
        app.handle_tool_click(Tool.TITO)
        self._step(app, clock, 20)
        app.draw()
        self.assertGreater(app.renderer.fact_banner_rect.width, 0)
        self.assertEqual(app.canvas.surface.get_size(), (1024, 600))

    def test_app_tools_and_fact_flow(self) -> None:
        app, pod, _, clock = self._app()
        app.handle_tool_click(Tool.FEED)
        self.assertGreaterEqual(len(pod.foods), 1)

        app.handle_tool_click(Tool.PLAY)
        self.assertTrue(all(orca.state == OrcaState.BREACHING for orca in pod.orcas))

        app.handle_tool_click(Tool.DAY_NIGHT)
        self.assertTrue(pod.night_mode)
        # Day/Night and Tito are actions: they never change the current mode.
        self.assertEqual(pod.active_tool, Tool.PLAY)

        app.handle_tool_click(Tool.TITO)
        self.assertEqual(pod.active_tool, Tool.PLAY)
        first_fact = pod.active_fact
        self.assertIsNotNone(first_fact)
        self.assertIn(first_fact, pod.discovered_facts)
        app.audio.play_voice.assert_called_with(first_fact, "it")

        self._step(app, clock, 15)
        app.draw()
        banner = app.renderer.fact_banner_rect
        app.handle_pointer_down(float(banner.centerx), float(banner.centery))
        self.assertIsNotNone(pod.active_fact)
        self.assertNotEqual(pod.active_fact, first_fact)

    def test_food_tray_chooses_and_drops_food(self) -> None:
        app, pod, _, clock = self._app()
        squid = next(slot for slot in app._controls.foods.slots if slot.tool_id == "squid")
        self.assertTrue(squid.visible)
        before = len(pod.foods)
        app.tap(squid.rect.center)
        self.assertEqual(pod.selected_food, FoodType.SQUID)
        self.assertEqual(len(pod.foods), before + 1)
        self.assertEqual(pod.foods[-1].kind, "squid")
        # Out of Feed mode the tray hides and the bells appear instead.
        song = next(slot for slot in app._controls.modes.slots if slot.tool_id == "song")
        app.tap(song.rect.center)
        self.assertEqual(pod.active_tool, Tool.SONG)
        self.assertFalse(squid.visible)
        bell = app._controls.bells[1]
        self.assertTrue(bell.focusable)
        app.tap(bell.rect.center)
        app.audio.play.assert_any_call("bell_1")
        self.assertEqual(pod.total_songs, 1)

    def test_bells_do_not_overlap_the_hoop_or_ball_start(self) -> None:
        app, pod, _, _ = self._app()
        hoop = app._hoop_rect()
        for bell in app._controls.bells:
            self.assertFalse(bell.rect.colliderect(hoop))
            self.assertFalse(bell.rect.collidepoint((int(pod.toys[0].x), int(pod.toys[0].y))))

    def test_tapping_orcas_cuddles_names_and_play_mode_makes_them_jump(self) -> None:
        app, pod, events, _ = self._app()
        kiko = pod.orca("kiko")
        assert kiko is not None
        app.handle_pointer_down(kiko.x, kiko.y)
        self.assertEqual(kiko.state, OrcaState.CUDDLE_BELLY)
        self.assertGreater(kiko.name_t, 0)
        self.assertEqual(pod.total_cuddled, 1)
        events.record_cuddled.assert_called_with("kiko", "belly_rub")
        pod.active_tool = Tool.PLAY
        luna = pod.orca("luna")
        assert luna is not None
        app.handle_pointer_down(luna.x, luna.y)
        self.assertEqual(luna.state, OrcaState.BREACHING)

    def test_hoop_tap_sends_the_nearest_orca_through_it(self) -> None:
        app, pod, events, _ = self._app()
        hoop = app._hoop_rect()
        app.handle_pointer_down(hoop.centerx, hoop.centery)
        jumper = pod.nearest_orca(hoop.centerx)
        self.assertEqual(jumper.state, OrcaState.RING_LEAP)
        events.record_acrobatics.assert_called_with(jumper.id, "ring_leap")

    def test_keyboard_cursor_acts_in_the_water(self) -> None:
        app, pod, _, clock = self._app()
        # Move the cursor clear of the orcas, then feed with Space.
        pod.orcas = [o for o in pod.orcas if o.id == "kiko"]
        pod.orcas[0].x, pod.orcas[0].y = 900.0, 450.0
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode=""))
        self.assertTrue(app._controls.layer.focus_visible)
        start = app.keyboard_cursor
        for _ in range(3):
            app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode=""))
        self.assertLess(app.keyboard_cursor[0], start[0])
        before = len(pod.foods)
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode=""))
        self.assertEqual(len(pod.foods), before + 1)
        # Number keys keep working as direct shortcuts.
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_4, mod=0, unicode=""))
        self.assertEqual(pod.active_tool, Tool.SONG)

    def test_taps_in_protected_chrome_never_reach_the_bay(self) -> None:
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        app, pod, _, _ = self._app()
        region = activity_viewport_for_surface(app.screen).protected_regions[0]
        before = len(pod.foods)
        app.tap((int(region.x) + 4, int(region.y) + 4))
        self.assertEqual(len(pod.foods), before)

    def test_controls_stay_clear_of_chrome_at_every_size(self) -> None:
        from greia_platform.activity_controls import KitControl

        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            app, _, _, _ = self._app(size=size)
            protected = app._controls._layout.protected
            for target in app._controls.layer.targets:
                if isinstance(target, KitControl) and target.visible:
                    self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))
            app.draw()

    def test_orcas_keep_their_size_and_stay_above_the_toolbar(self) -> None:
        app, pod, _, clock = self._app()
        toolbar = app._controls.toolbar_top
        boxes = {o: ORCA_LOOKS[o].box for o in ("kiko", "luna", "oskar")}
        self.assertGreaterEqual(boxes["oskar"][0], 280)
        self.assertLess(boxes["kiko"][0], boxes["luna"][0])
        for orca in pod.orcas:
            orca.y = 900.0
            orca.x = -50.0
        self._step(app, clock, 2)
        for orca in pod.orcas:
            half_w, half_h = boxes[orca.id][0] / 2, boxes[orca.id][1] / 2
            self.assertLessEqual(orca.y + half_h, toolbar + 2, orca.id)
            self.assertGreaterEqual(orca.x - half_w, -2, orca.id)

    def test_cached_hud_overlay_frame_matches_direct_kit_drawing(self) -> None:
        from unittest.mock import patch

        import activities.baia_delle_orche.orca_app as orca_app_module

        app, pod, _, clock = self._app()
        self._step(app, clock, 3)
        with patch.object(orca_app_module, "now_seconds", return_value=12.0):
            app.draw()
            composed = app._hud.compositions
            app.draw()
            self.assertEqual(app._hud.compositions, composed, "a still HUD is not re-composed")
            cached = app.canvas.surface.copy()
            with patch.object(app._hud, "draw", lambda surface, key, render, stale=False: render(surface)):
                app.draw()
            direct = app.canvas.surface.copy()
            app._controls.set_counters(pod.total_fed + 1, pod.total_cuddled, pod.stars)
            app.draw()
            self.assertGreater(app._hud.compositions, composed, "an invalidated layer re-composes")
        worst = 0
        for x in range(0, 1024, 3):
            for y in range(0, 600, 3):
                a, b = cached.get_at((x, y)), direct.get_at((x, y))
                worst = max(worst, abs(a.r - b.r), abs(a.g - b.g), abs(a.b - b.b))
        self.assertLessEqual(worst, 3)

    def test_keyboard_hint_sits_in_the_sky_and_lights_through_the_cached_hud(self) -> None:
        from greia_platform.activity_keyboard_hint import KeyCap

        from activities.baia_delle_orche.orca_content import WATER_SURFACE_Y

        for size in ((1024, 600), (800, 480)):
            app, pod, _, clock = self._app(size=size, missions=True)
            controls = app._controls
            keys = controls.keys
            self.assertTrue(keys.visible, "shown at start")
            self.assertEqual(keys.active, {KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
            self.assertLess(keys.rect.bottom, WATER_SURFACE_Y - 60, "in the sky, above the water")
            self.assertGreater(keys.rect.left, 1024 // 2 + 120, "right side, clear of the food tray")
            self.assertFalse(keys.rect.colliderect(controls._layout.protected))
            for target in (*controls.foods.controls, controls.fed, controls.cuddles, controls.stars, controls.dots):
                self.assertFalse(keys.rect.colliderect(target.rect), target.control_id)
            self.assertNotIn(keys, list(controls.layer.targets), "display-only, never a focus target")
            smallest = min(r.height for r in keys.key_rects().values()) * controls._layout.scale
            self.assertGreaterEqual(smallest, 25, "legible keycaps")
        app.draw()
        composed = app._hud.compositions
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode="", scancode=0))
        self.assertIn(KeyCap.LEFT, keys.lit)
        app.draw()
        self.assertGreater(app._hud.compositions, composed, "a lit key re-composes the cached HUD")
        app.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_LEFT, mod=0, unicode="", scancode=0))
        self._step(app, clock, 15)
        self.assertNotIn(KeyCap.LEFT, keys.lit)
        self.assertTrue(app._keys_changed or not keys.animating)

    def test_day_sea_keeps_the_deep_ocean_blue_and_moon_clears_counters(self) -> None:
        assets = OrcaAssetCache()
        day = assets.background(False)
        samples = [day.get_at((x, int(WATER_SURFACE_Y) + 60))[:3] for x in range(0, 1024, 16)]
        r, g, b = sorted(samples, key=sum)[len(samples) // 2]
        self.assertLess(r, 40)
        self.assertGreater(b, 150)
        self.assertGreater(b - r, 120)
        night = assets.background(True)
        app, _, _, _ = self._app()
        app._controls.set_counters(0, 0, 1)  # all three counters showing
        chips = app._controls.fed.rect.union(app._controls.cuddles.rect).union(app._controls.stars.rect)
        # The moon (a bright crescent, not single stars) left the counters' corner.
        def moon_pixels(area: pygame.Rect) -> int:
            return sum(
                1
                for x in range(area.left, area.right, 2)
                for y in range(area.top, area.bottom, 2)
                if sum(night.get_at((x, y))[:3]) > 600
            )

        self.assertLess(moon_pixels(chips.inflate(0, 80).clip(night.get_rect())), 40)
        self.assertGreater(moon_pixels(pygame.Rect(200, 50, 100, 100)), 60)
        self.assertFalse(pygame.Rect(200, 50, 100, 100).colliderect(app._controls.layer.target("hud.fed").rect))

    def test_round_of_invitations_plays_to_a_star(self) -> None:
        """App loop: three optional invitations completed -> a star and a pod leap."""

        app, pod, events, clock = self._app(missions=True, seed=11)
        app._missions._cooldown = 0.5
        completed = 0
        for _ in range(MISSIONS_PER_STAR):
            for _ in range(400):
                self._step(app, clock)
                if app._missions.current is not None:
                    break
            mission = app._missions.current
            self.assertIsNotNone(mission)
            self.assertTrue(app._controls.mission.visible)
            app.draw()
            orca = pod.orca(mission.orca_id)
            assert orca is not None
            for _ in range(60):  # let any jump finish so the orca is touchable
                if not orca.airborne:
                    break
                self._step(app, clock)
            if mission.kind is MissionKind.FIND:
                app.handle_pointer_down(orca.x, orca.y)
            elif mission.kind is MissionKind.JUMP:
                app.handle_tool_click(Tool.CUDDLE)
                pod.active_tool = Tool.PLAY
                app.handle_pointer_down(orca.x, orca.y)
            else:
                self.assertEqual(orca.craved_food, mission.food)
                pod.foods.clear()
                pod.spawn_food(orca.x, orca.y, kind=mission.food)
                for _ in range(30):
                    self._step(app, clock)
                    if app._missions.current is None:
                        break
            self._step(app, clock)
            self.assertIsNone(app._missions.current)
            completed += 1
            app.draw()
        self.assertEqual(completed, MISSIONS_PER_STAR)
        self.assertEqual(pod.stars, 1)
        self.assertEqual(app._controls.stars.value, 1)
        self.assertTrue(app._controls.stars.visible)
        stars = [call.kwargs.get("star") for call in events.record_mission_completed.call_args_list]
        self.assertEqual(stars, [False, False, True])
        app.audio.say.assert_any_call("praise.general")
        self.assertTrue(any(o.airborne for o in pod.orcas))

    def test_autosave_survives_a_storage_refusal(self) -> None:
        app, pod, _, clock = self._app()
        app.progress.save_progress.side_effect = OSError("volume budget")
        clock.now += 10.0
        app.advance(0.033)
        self.assertTrue(app.progress.save_progress.called)

    def test_events_include_mission_completed_in_manifest(self) -> None:
        import tomllib
        from unittest.mock import patch

        declared = {
            event["id"]
            for event in tomllib.loads((ACTIVITY_DIR / "activity.toml").read_text())["education"]["events"]
        }
        with patch("activities.baia_delle_orche.orca_services.emit_activity_event") as emit:
            GreiaOrcaEvents().record_mission_completed("find", star=False)
        self.assertIn(emit.call_args.args[0], declared)

    def test_feeding_and_fact_events_are_in_manifest(self) -> None:
        import tomllib
        from unittest.mock import patch

        declared = {
            event["id"]
            for event in tomllib.loads((ACTIVITY_DIR / "activity.toml").read_text())["education"]["events"]
        }
        with patch("activities.baia_delle_orche.orca_services.emit_activity_event") as emit:
            events = GreiaOrcaEvents()
            events.record_feeding(2)
            events.record_fact_discovered("fact_breach")
        emitted = [call.args[0] for call in emit.call_args_list]
        self.assertEqual(emitted, ["orca.fed", "orca.fact_discovered"])
        self.assertTrue(set(emitted) <= declared)


class BaiaDelleOrcheHandlerTests(unittest.TestCase):
    """Handler-level checks on a minimally wired app (no full composition)."""

    def _app(self):
        from types import SimpleNamespace

        from activities.baia_delle_orche.orca_app import OrcaBayActivity

        app = OrcaBayActivity.__new__(OrcaBayActivity)
        app.renderer = SimpleNamespace(resources=SimpleNamespace(
            context=SimpleNamespace(selected=SimpleNamespace(value="en"))
        ))
        app.pod = Mock()
        app.pod.trigger_fact.return_value = "orca.fact.1"
        app.pod.total_cuddled = 0
        app.audio = Mock()
        app.events = Mock()
        app._gesture_cuddled_ids = set()
        return app

    def test_spoken_facts_use_the_selected_locale(self) -> None:
        app = self._app()
        app._play_fact()
        app.audio.play_voice.assert_called_once_with("orca.fact.1", "en")
        app.events.record_fact_discovered.assert_called_once_with("orca.fact.1")

    def test_one_drag_cuddles_each_orca_at_most_once(self) -> None:
        from types import SimpleNamespace

        app = self._app()
        orca = SimpleNamespace(id="a", x=500, y=300, trigger_cuddle=Mock())
        app._cuddle_once(orca, drag=True)
        app._cuddle_once(orca, drag=True)
        self.assertEqual(app.pod.total_cuddled, 1)
        app.events.record_cuddled.assert_called_once_with("a", "belly_rub")
        orca.trigger_cuddle.assert_called_once()
        self.assertEqual(app.audio.play.call_count, 1)
        app._gesture_cuddled_ids.clear()  # the next, independent gesture
        app._cuddle_once(orca, drag=True)
        self.assertEqual(app.pod.total_cuddled, 2)

    def test_pointer_outside_surface_or_on_chrome_is_ignored(self) -> None:
        from activities.baia_delle_orche.orca_app import OrcaBayActivity
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        app = object.__new__(OrcaBayActivity)
        app.screen = pygame.Surface((1024, 600))
        region = activity_viewport_for_surface(app.screen).protected_regions[0]
        self.assertFalse(app._safe_pointer((int(region.x) + 1, int(region.y) + 1)))
        self.assertFalse(app._safe_pointer((-1, 200)))
        self.assertTrue(app._safe_pointer((500, 300)))


if __name__ == "__main__":
    unittest.main()
