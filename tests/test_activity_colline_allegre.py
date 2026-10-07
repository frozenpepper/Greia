"""Unit and integration tests for Colline Allegre (Bumpy Hills)."""

from __future__ import annotations

import math
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

from activities.colline_allegre.colline_audio import CollineAudio
from activities.colline_allegre.colline_content import (
    PIXELS_PER_METER,
    PROFILES,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    SYSTEM_CHROME_SAFE_X,
    SYSTEM_CHROME_SAFE_Y,
    WHEEL_RADIUS,
    WHEELBASE,
)
from activities.colline_allegre.colline_model import (
    TERRAIN_BASE_Y,
    Collectible,
    CollineWorld,
    Terrain,
    Vehicle,
)
from activities.colline_allegre.colline_renderer import CollineRenderer
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "colline_allegre"


class CollineAllegreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def test_real_script_entrypoint_imports_in_non_package_context(self) -> None:
        """The supervisor executes main.py as a script, not as a package."""
        import runpy

        source_root = str(ACTIVITY_DIR)
        sys.path.insert(0, source_root)
        try:
            namespace = runpy.run_path(
                str(ACTIVITY_DIR / "main.py"), run_name="greia_script_import_smoke"
            )
        finally:
            sys.path.remove(source_root)
        self.assertTrue(callable(namespace["main"]))

    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.colline-allegre")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])
        self.assertEqual(data["runtime"]["entrypoint"], "main.py")
        self.assertEqual(data["input"]["profile"], "hybrid")

        events = {e["id"] for e in data["education"]["events"]}
        self.assertIn("colline.run_started", events)
        self.assertIn("colline.star_collected", events)
        self.assertIn("colline.perfect_landing", events)
        self.assertIn("colline.comical_flip", events)
        self.assertIn("colline.milestone_distance", events)
        self.assertIn("colline.course_completed", events)

    def test_locales_and_title_audio_with_receipts_exist(self) -> None:
        it_json = ACTIVITY_DIR / "locales" / "it.json"
        en_json = ACTIVITY_DIR / "locales" / "en.json"
        self.assertTrue(it_json.is_file())
        self.assertTrue(en_json.is_file())

        it_audio = ACTIVITY_DIR / "locales" / "it" / "audio" / "activity-title.wav"
        it_receipt = ACTIVITY_DIR / "locales" / "it" / "audio" / "activity-title.wav.receipt.json"
        en_audio = ACTIVITY_DIR / "locales" / "en" / "audio" / "activity-title.wav"
        en_receipt = ACTIVITY_DIR / "locales" / "en" / "audio" / "activity-title.wav.receipt.json"

        self.assertTrue(it_audio.is_file(), "Italian title audio must exist")
        self.assertTrue(it_receipt.is_file(), "Italian title receipt must exist")
        self.assertTrue(en_audio.is_file(), "English title audio must exist")
        self.assertTrue(en_receipt.is_file(), "English title receipt must exist")

        self.assertGreater(it_audio.stat().st_size, 1000)
        self.assertGreater(en_audio.stat().st_size, 1000)

    def test_icon_exists_and_is_256(self) -> None:
        icon_path = ACTIVITY_DIR / "assets" / "icon.png"
        self.assertTrue(icon_path.is_file())
        surf = pygame.image.load(str(icon_path))
        self.assertEqual(surf.get_size(), (256, 256))

    def test_terrain_elevation_and_continuity(self) -> None:
        world = CollineWorld(difficulty=2)
        terrain = world.terrain
        # Spawn is flat
        self.assertEqual(terrain.get_height(50.0), TERRAIN_BASE_Y)
        self.assertEqual(terrain.get_height(150.0), TERRAIN_BASE_Y)

        # Height changes smoothly
        prev_h = terrain.get_height(200.0)
        for x in range(200, 1000, 10):
            h = terrain.get_height(float(x))
            self.assertLess(abs(h - prev_h), 25.0, f"Discontinuity detected at x={x}")
            prev_h = h

        # Surface kinds
        self.assertEqual(terrain.get_surface_kind(900.0), "bridge")
        self.assertEqual(terrain.get_surface_kind(100.0), "grass")

    def test_vehicle_accelerates_forward_under_throttle(self) -> None:
        world = CollineWorld(difficulty=2)
        # Settle vehicle on ground
        for _ in range(30):
            world.step(0.016, throttle=0.0)

        initial_vx = world.vehicle.vx
        initial_x = world.vehicle.x

        # Apply full throttle
        for _ in range(40):
            world.step(0.016, throttle=1.0)

        self.assertGreater(world.vehicle.vx, initial_vx + 50.0)
        self.assertGreater(world.vehicle.x, initial_x + 20.0)

    def test_vehicle_brakes_and_slows_down(self) -> None:
        world = CollineWorld(difficulty=2)
        world.vehicle.vx = 300.0
        # Settle on ground
        for _ in range(15):
            world.step(0.016, throttle=0.0)

        speed_before = world.vehicle.vx
        # Apply brake
        for _ in range(30):
            world.step(0.016, brake=1.0)

        self.assertLess(world.vehicle.vx, speed_before)

    def test_suspension_supports_chassis(self) -> None:
        world = CollineWorld(difficulty=2)
        # Step for 1 second of physics
        for _ in range(60):
            world.step(0.016, throttle=0.0)

        veh = world.vehicle
        ground_y = world.terrain.get_height(veh.x)
        # Chassis should be held comfortably above ground
        self.assertLess(veh.y, ground_y - 20.0)
        self.assertTrue(veh.rear_wheel.in_contact or veh.front_wheel.in_contact)
        self.assertGreater(veh.rear_wheel.compression + veh.front_wheel.compression, 0.0)

    def test_mid_air_tilt_controls(self) -> None:
        world = CollineWorld(difficulty=2)
        veh = world.vehicle
        # Place in the air
        veh.y = 100.0
        veh.vy = 0.0
        world.step(0.02, tilt=1.0)
        self.assertTrue(veh.is_airborne)
        self.assertGreater(veh.angular_velocity, 0.0)

        world.step(0.02, tilt=-1.0)
        # Counter-tilt reduces angular velocity
        self.assertLess(veh.angular_velocity, 0.5)

    def test_comical_flip_and_boxing_glove_recovery(self) -> None:
        world = CollineWorld(difficulty=2)
        veh = world.vehicle
        ground_y = world.terrain.get_height(veh.x)

        # Place vehicle upside down near ground
        veh.angle = math.pi
        veh.y = ground_y - 10.0
        veh.vx = 0.0
        veh.vy = 0.0

        recovered = False
        for _ in range(60):
            events = world.step(0.02)
            if "colline.comical_flip" in events:
                recovered = True
                break

        self.assertTrue(recovered, "Comical flip recovery event must be triggered")
        self.assertTrue(veh.bounce_active, "Bounce animation must be active")
        # Vehicle must be uprighted and launched upward
        self.assertLess(abs(veh.angle), 0.5, "Vehicle must be right-side up")
        self.assertLess(veh.vy, -200.0, "Vehicle must receive upward bounce impulse")

    def test_collectibles_pickup(self) -> None:
        world = CollineWorld(difficulty=2)
        veh = world.vehicle
        # Place a collectible right in front of the vehicle
        col = Collectible(x=veh.x + 40.0, y=veh.y, kind="star", value=1)
        world.collectibles.append(col)

        initial_stars = world.stars_collected
        # Drive forward into it
        collected = False
        for _ in range(30):
            events = world.step(0.016, throttle=1.0)
            if "colline.star_collected" in events:
                collected = True
                break

        self.assertTrue(collected, "Star collected event must be emitted")
        self.assertEqual(world.stars_collected, initial_stars + 1)
        self.assertTrue(col.collected)

    def test_distance_milestones_and_completion(self) -> None:
        world = CollineWorld(difficulty=1)
        # Advance vehicle to 105 meters (1050 px)
        world.vehicle.x = 105.0 * PIXELS_PER_METER
        events = world.step(0.016)
        self.assertIn("colline.milestone_distance", events)
        self.assertEqual(world.highest_milestone, 100)

        # Advance past target distance
        world.vehicle.x = world.profile.target_distance * PIXELS_PER_METER + 10.0
        events = world.step(0.016)
        self.assertIn("colline.course_completed", events)
        self.assertTrue(world.is_completed)

    def test_audio_manager_fail_soft(self) -> None:
        audio = CollineAudio()
        # Should not raise exception even under dummy audio driver
        audio.play("star")
        audio.play("boing")
        audio.play("whoosh")
        audio.play("squeak")
        audio.play("fanfare")
        audio.play("perfect_landing")
        audio.stop_all()

    def test_renderer_top_left_system_chrome_clearance(self) -> None:
        typo = GreiaTypography()
        renderer = CollineRenderer(typo)
        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        world = CollineWorld(difficulty=2)
        renderer.render(surf, world, 0.016)

        # Pedals must not intersect system chrome region (0..SYSTEM_CHROME_SAFE_X, 0..SYSTEM_CHROME_SAFE_Y)
        chrome_rect = pygame.Rect(0, 0, SYSTEM_CHROME_SAFE_X, SYSTEM_CHROME_SAFE_Y)
        self.assertFalse(chrome_rect.colliderect(renderer.gas_pedal_rect))
        self.assertFalse(chrome_rect.colliderect(renderer.brake_pedal_rect))


if __name__ == "__main__":
    unittest.main()
