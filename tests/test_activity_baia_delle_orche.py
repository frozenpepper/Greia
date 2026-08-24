from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib
import unittest

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from activities.baia_delle_orche.orca_audio import PygameOrcaAudio
from activities.baia_delle_orche.orca_model import (
    FoodEntity,
    FoodType,
    OrcaEntity,
    OrcaPod,
    OrcaState,
    ToyEntity,
    WATER_SURFACE_Y,
)
from activities.baia_delle_orche.orca_renderer import OrcaRenderer
from activities.baia_delle_orche.orca_services import GreiaOrcaEvents, GreiaOrcaProgress
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "baia_delle_orche"


class BaiaDelleOrcheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600), pygame.HIDDEN)

    def test_manifest_is_valid_and_complete(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)

        self.assertEqual(data["activity"]["id"], "org.greia.baia-delle-orche")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertEqual(data["activity"]["icon"], "package:assets/icon.png")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])

        self.assertIn("play", data["presentation"]["categories"])
        self.assertIn("nature", data["presentation"]["discovery_tags"])

        self.assertEqual(data["education"]["difficulty"], 1)
        self.assertEqual(data["education"]["recommended_age_min"], 3)
        self.assertEqual(data["education"]["recommended_age_max"], 7)

        # Requirements and capabilities
        self.assertIn("display", data["requirements"]["required_capabilities"])
        self.assertIn("pointer", data["requirements"]["required_capabilities"])
        self.assertIn("audio.basic", data["requirements"]["required_capabilities"])

    def test_locales_presence_and_keys(self) -> None:
        for loc in ("it", "en"):
            loc_path = ACTIVITY_DIR / "locales" / f"{loc}.json"
            self.assertTrue(loc_path.is_file(), f"Missing locale: {loc}.json")
            with loc_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertEqual(data["schema_version"], 1)
            self.assertEqual(data["locale"], loc)
            strings = data["strings"]
            self.assertIn("activity.title", strings)
            self.assertIn("activity.baia_delle_orche.title", strings)
            self.assertIn("orca.kiko", strings)
            self.assertIn("orca.luna", strings)
            self.assertIn("orca.oskar", strings)
            self.assertIn("tool.feed", strings)
            self.assertIn("tool.cuddle", strings)
            self.assertIn("tool.play", strings)
            self.assertIn("tool.sing", strings)

    def test_icon_asset_exists_and_is_valid_png(self) -> None:
        icon_path = ACTIVITY_DIR / "assets" / "icon.png"
        self.assertTrue(icon_path.is_file())
        surf = pygame.image.load(str(icon_path))
        self.assertEqual(surf.get_size(), (256, 256))

    def test_orca_pod_members_and_morphology(self) -> None:
        pod = OrcaPod()
        self.assertEqual(len(pod.orcas), 3)

        ids = [o.id for o in pod.orcas]
        self.assertEqual(ids, ["kiko", "luna", "oskar"])

        # Check scales: Kiko is pup (< 1.0), Luna is teen (1.0), Oskar is elder (> 1.0)
        self.assertLess(pod.orcas[0].scale, 1.0)
        self.assertEqual(pod.orcas[1].scale, 1.0)
        self.assertGreater(pod.orcas[2].scale, 1.0)

        for orca in pod.orcas:
            self.assertGreater(orca.width, 0)
            self.assertGreater(orca.height, 0)
            self.assertEqual(orca.state, OrcaState.SWIMMING)

    def test_cuddle_state_transition(self) -> None:
        pod = OrcaPod()
        kiko = pod.orcas[0]
        self.assertEqual(kiko.state, OrcaState.SWIMMING)
        self.assertEqual(kiko.cuddle_happiness, 0.0)

        kiko.trigger_cuddle()
        self.assertEqual(kiko.state, OrcaState.CUDDLE_BELLY)
        self.assertGreater(kiko.cuddle_happiness, 0.0)
        self.assertGreater(kiko.state_timer, 0.0)

        # Update over duration to transition back to SWIMMING
        kiko.update(3.0, pod.foods, pod.toys, night_mode=False)
        self.assertEqual(kiko.state, OrcaState.SWIMMING)

    def test_breaching_jump_state_transition(self) -> None:
        pod = OrcaPod()
        luna = pod.orcas[1]
        luna.trigger_breach(jump_x=600.0, height_bonus=30.0)
        self.assertEqual(luna.state, OrcaState.BREACHING)

        # Progress through the jump
        events = luna.update(0.4, pod.foods, pod.toys, night_mode=False)
        self.assertEqual(luna.state, OrcaState.BREACHING)

        # Complete the jump and verify reentry splash
        events_end = luna.update(1.2, pod.foods, pod.toys, night_mode=False)
        self.assertEqual(luna.state, OrcaState.SWIMMING)
        self.assertIn("splash", events_end)
        self.assertIn("whistle", events_end)

    def test_food_drop_and_feeding(self) -> None:
        pod = OrcaPod()
        food = pod.spawn_food(x=pod.orcas[0].x, y=pod.orcas[0].y - 20.0, kind=FoodType.HERRING)
        self.assertIn(food, pod.foods)

        # Update pod physics
        events = pod.update(0.1)
        self.assertGreaterEqual(pod.total_fed, 0)

    def test_toy_physics_and_bouncing(self) -> None:
        ball = ToyEntity("ball", 400.0, WATER_SURFACE_Y - 50.0)
        ball.update(0.033)
        self.assertGreater(ball.vy, 0.0)  # Falling under gravity

        # Submerged in water
        ball.y = WATER_SURFACE_Y + 20.0
        ball.update(0.033)
        self.assertLess(ball.vy, 0.0)  # Buoyant push upward

    def test_audio_synthesizer_playback(self) -> None:
        audio = PygameOrcaAudio()
        # Verify sounds are initialized and don't raise exceptions on play
        for s_name in ("splash", "whistle", "clicks", "nibble", "purr", "bubble", "bounce", "bell_0", "bell_3", "aurora"):
            audio.play(s_name)

    def test_progress_export_and_restore(self) -> None:
        pod = OrcaPod()
        pod.total_fed = 12
        pod.total_cuddled = 8
        pod.total_acrobatics = 5
        pod.total_songs = 3
        pod.night_mode = True

        exported = pod.export_progress()
        self.assertEqual(exported["total_fed"], 12)
        self.assertEqual(exported["total_cuddled"], 8)
        self.assertEqual(exported["night_mode"], True)

        new_pod = OrcaPod()
        new_pod.restore_progress(exported)
        self.assertEqual(new_pod.total_fed, 12)
        self.assertEqual(new_pod.total_cuddled, 8)
        self.assertEqual(new_pod.total_acrobatics, 5)
        self.assertEqual(new_pod.total_songs, 3)
        self.assertTrue(new_pod.night_mode)

    def test_renderer_composition(self) -> None:
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_DIR, context)
        renderer = OrcaRenderer(GreiaTypography(), resources)

        surf = pygame.Surface((1024, 600))
        pod = OrcaPod()
        renderer.render_frame(surf, pod)
        self.assertEqual(surf.get_size(), (1024, 600))

        # Test night mode rendering
        pod.night_mode = True
        renderer.render_frame(surf, pod)
        self.assertEqual(surf.get_size(), (1024, 600))

    def test_app_interactions_and_tools(self) -> None:
        from activities.baia_delle_orche.orca_app import OrcaBayActivity
        from greia_platform.pygame_canvas import PygameReferenceCanvas

        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_DIR, context)
        renderer = OrcaRenderer(GreiaTypography(), resources)

        screen = pygame.Surface((1024, 600))
        canvas = PygameReferenceCanvas(screen)
        pod = OrcaPod()
        audio = PygameOrcaAudio()
        progress = GreiaOrcaProgress()
        events = GreiaOrcaEvents()

        app = OrcaBayActivity(
            screen=screen,
            canvas=canvas,
            pod=pod,
            renderer=renderer,
            audio=audio,
            progress=progress,
            events=events,
        )

        # Test tool click switching (0: Feed, 1: Cuddle, 2: Play, 3: Sing, 4: Night)
        app.handle_tool_click(0)
        self.assertEqual(pod.active_tool, 0)
        self.assertGreaterEqual(len(pod.foods), 1)

        app.handle_tool_click(1)
        self.assertEqual(pod.active_tool, 1)

        app.handle_tool_click(2)
        self.assertEqual(pod.active_tool, 2)
        for orca in pod.orcas:
            self.assertEqual(orca.state, OrcaState.BREACHING)

        app.handle_tool_click(3)
        self.assertEqual(pod.active_tool, 3)

        # Test chime interaction in Sing mode
        bell_rect, b_idx, _, _ = renderer.bell_rects[0]
        app.handle_pointer_down(float(bell_rect.centerx), float(bell_rect.centery))
        self.assertEqual(pod.total_songs, 1)

        # Test direct cuddle interaction
        app.handle_tool_click(1)
        kiko = pod.orcas[0]
        app.handle_pointer_down(kiko.x, kiko.y)
        self.assertEqual(kiko.state, OrcaState.CUDDLE_BELLY)
        self.assertEqual(pod.total_cuddled, 1)

        # Test Day/Night toggle
        app.handle_tool_click(4)
        self.assertTrue(pod.night_mode)


if __name__ == "__main__":
    unittest.main()
