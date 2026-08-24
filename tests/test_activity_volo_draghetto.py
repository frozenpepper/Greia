"""Unit and regression tests for Il Volo del Draghetto (Dragon Flight)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tomllib
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pygame

from activities.volo_draghetto.dragon_app import DragonFlightApp
from activities.volo_draghetto.dragon_art import DragonArtLibrary
from activities.volo_draghetto.dragon_audio import DragonAudio
from activities.volo_draghetto.dragon_model import (
    ACCESSORIES,
    BouncyCloud,
    CollectibleStar,
    DragonPlayer,
    FlightWorldState,
    RainbowGate,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    ROUND_STAR_TARGET,
)
from activities.volo_draghetto.dragon_renderer import DragonRenderer
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "volo_draghetto"


class VoloDraghettoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.volo-draghetto")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertEqual(data["runtime"]["entrypoint"], "main.py")
        self.assertEqual(data["input"]["profile"], "hybrid")
        self.assertIn("audio.basic", data["requirements"]["required_capabilities"])
        self.assertIn("display", data["requirements"]["required_capabilities"])
        self.assertIn("pointer", data["requirements"]["required_capabilities"])

    def test_localization_catalogue_contains_all_keys(self) -> None:
        locales_dir = ACTIVITY_DIR / "locales"
        for lang in ("it", "en"):
            fpath = locales_dir / f"{lang}.json"
            self.assertTrue(fpath.is_file(), f"Missing locale file {lang}.json")
            with fpath.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            strings = payload.get("strings", {})
            self.assertIn("activity.title", strings)
            self.assertIn("msg.rainbow_dash", strings)

    def test_dragon_model_movement_and_dash_decay(self) -> None:
        player = DragonPlayer(x=100.0, y=250.0, target_y=350.0)
        self.assertFalse(player.is_dashing)
        player.trigger_dash(2.0)
        self.assertTrue(player.is_dashing)
        self.assertEqual(player.current_speed, player.base_speed * 2.0)

        # Update by 1s (30 ticks)
        for _ in range(30):
            player.update(1.0 / 30.0)

        self.assertGreater(player.x, 100.0)
        self.assertGreater(player.y, 250.0)
        self.assertAlmostEqual(player.dash_timer, 1.0, places=1)

    def test_accessory_cycling(self) -> None:
        player = DragonPlayer(accessory="crown")
        next_acc = player.cycle_accessory()
        self.assertEqual(next_acc, "bow")
        self.assertIn(player.accessory, ACCESSORIES)

    def test_collision_detection_for_stars_and_rainbows(self) -> None:
        star = CollectibleStar(x=200.0, y=300.0)
        self.assertTrue(star.collides_with(200.0, 300.0))
        self.assertFalse(star.collides_with(400.0, 500.0))

        gate = RainbowGate(x=300.0, y=250.0)
        self.assertTrue(gate.collides_with(300.0, 220.0))
        self.assertFalse(gate.collides_with(500.0, 100.0))

        cloud = BouncyCloud(x=400.0, y=300.0)
        self.assertTrue(cloud.collides_with(400.0, 300.0))
        self.assertFalse(cloud.collides_with(600.0, 100.0))

    def test_dragon_move_altitude_snappy_arrows(self) -> None:
        player = DragonPlayer(x=200.0, y=300.0, target_y=300.0)
        player.move_altitude(-24.0)
        self.assertEqual(player.target_y, 276.0)
        self.assertLess(player.y, 300.0)

        player.move_altitude(50.0)
        self.assertEqual(player.target_y, 326.0)
        self.assertGreater(player.y, 280.0)

    def test_world_flight_continuous_star_accumulation_and_milestones(self) -> None:
        world = FlightWorldState()
        world.start_flight()
        self.assertEqual(world.round_stars, 0)

        # Place 10 stars directly in front of the dragon to hit milestone
        world.stars = [CollectibleStar(x=200.0 + i * 2, y=300.0) for i in range(10)]

        events = world.update(1.0 / 30.0)
        self.assertIn("star_collected", events)
        self.assertIn("star_milestone", events)
        self.assertEqual(world.round_stars, 10)
        self.assertEqual(world.total_stars, 10)

    def test_art_library_caching_and_rendering(self) -> None:
        art = DragonArtLibrary()
        bg = art.get_sky_background()
        self.assertEqual(bg.get_size(), (REFERENCE_WIDTH, REFERENCE_HEIGHT))

        star_surf = art.get_star_sprite()
        self.assertGreater(star_surf.get_width(), 0)

        gate_surf = art.get_rainbow_gate_sprite()
        self.assertGreater(gate_surf.get_width(), 0)

        cloud_surf = art.get_cloud_obstacle_sprite()
        self.assertGreater(cloud_surf.get_width(), 0)

        dragon_surf = art.get_dragon_sprite(0.0, "crown", False)
        self.assertEqual(dragon_surf.get_size(), (180, 140))

        particle_surf = art.get_particle_sprite("star", 16, (255, 215, 0))
        self.assertGreater(particle_surf.get_width(), 0)

    def test_renderer_frame_composition(self) -> None:
        art = DragonArtLibrary()
        typography = GreiaTypography()
        renderer = DragonRenderer(art, typography)

        world = FlightWorldState()
        world.start_flight()

        target_surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        renderer.render_world(target_surf, world, "Test Feedback")
        self.assertFalse(target_surf.get_at((100, 100)) == (0, 0, 0, 255))

    def test_audio_sound_synthesis_fail_soft(self) -> None:
        audio = DragonAudio()
        # Should not throw even in dummy driver
        audio.play("star")
        audio.play("whoosh")
        audio.play("boing")
        audio.play("pop")
        audio.play("victory")


if __name__ == "__main__":
    unittest.main()
