"""Unit and regression tests for La Corsa delle Bacche (Cute Maze Chase)."""

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

from activities.corsa_bacche.corsa_app import CorsaApp, build_app
from activities.corsa_bacche.corsa_audio import CorsaAudio
from activities.corsa_bacche.corsa_content import (
    CELL_SIZE,
    GRID_COLS,
    GRID_ROWS,
    LEVELS,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    BerryType,
    CritterKind,
    Direction,
)
from activities.corsa_bacche.corsa_model import (
    CorsaModel,
    CritterState,
    MomoPlayer,
    grid_to_world,
    world_to_grid,
)
from activities.corsa_bacche.corsa_renderer import CorsaRenderer

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "corsa_bacche"


class CorsaBaccheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file(), "activity.toml must exist")
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)

        self.assertEqual(data["activity"]["id"], "org.greia.corsa-bacche")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertEqual(data["activity"]["title_key"], "activity.corsa_bacche.title")
        self.assertEqual(data["runtime"]["entrypoint"], "main.py")
        self.assertEqual(data["input"]["profile"], "hybrid")

        # Capabilities
        reqs = data["requirements"]["required_capabilities"]
        self.assertIn("audio.basic", reqs)
        self.assertIn("display", reqs)
        self.assertIn("pointer", reqs)

        # Presentation and Education
        self.assertIn("play", data["presentation"]["categories"])
        self.assertIn("explore", data["presentation"]["categories"])
        self.assertIn("action", data["presentation"]["discovery_tags"])
        self.assertIn("puzzles", data["presentation"]["discovery_tags"])

        # Skills & Events
        skill_ids = [s["id"] for s in data["education"]["skills"]]
        self.assertIn("motor.reaction", skill_ids)
        self.assertIn("spatial.mapping", skill_ids)
        self.assertIn("cognition.inhibition", skill_ids)

        event_ids = [e["id"] for e in data["education"]["events"]]
        self.assertIn("berry.collected", event_ids)
        self.assertIn("rainbow_star.activated", event_ids)
        self.assertIn("critter.gentle_rescue", event_ids)
        self.assertIn("maze.level_completed", event_ids)

    def test_localization_catalogue_and_audio_receipts(self) -> None:
        locales_dir = ACTIVITY_DIR / "locales"
        for lang in ("it", "en"):
            fpath = locales_dir / f"{lang}.json"
            self.assertTrue(fpath.is_file(), f"Missing {lang}.json")
            with fpath.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

            strings = payload.get("strings", {})
            self.assertIn("activity.title", strings)
            self.assertIn("activity.corsa_bacche.title", strings)
            self.assertIn("msg.rainbow_power", strings)
            self.assertIn("msg.level_clear", strings)
            self.assertIn("msg.oops", strings)

            audio_entry = payload.get("audio", {}).get("activity.title", {})
            rel_audio_path = audio_entry.get("path")
            self.assertIsNotNone(rel_audio_path)

            wav_file = ACTIVITY_DIR / rel_audio_path
            self.assertTrue(wav_file.is_file(), f"WAV file missing: {wav_file}")
            receipt_file = Path(str(wav_file) + ".receipt.json")
            self.assertTrue(receipt_file.is_file(), f"Receipt file missing: {receipt_file}")

    def test_model_initialization(self) -> None:
        model = CorsaModel(level_index=0)
        self.assertEqual(model.level_index, 0)
        self.assertEqual(model.hearts, 3)
        self.assertEqual(model.score, 0)
        self.assertGreater(len(model.walls), 0)
        self.assertGreater(len(model.berries), 0)
        self.assertGreater(model.total_berries, 0)
        self.assertFalse(model.is_rainbow_active)
        # Level 1 has 0 critters (gentle open harvesting)
        self.assertEqual(len(model.critters), 0)

    def test_movement_and_wall_blocking(self) -> None:
        model = CorsaModel(level_index=0)
        # Player starts at (1, 1). Check wall at (1, 0) (above)
        self.assertTrue(model.is_wall(1, 0))
        # Request moving UP into wall
        model.request_direction(Direction.UP)
        model.update(0.1)
        # Player should not move through wall
        c, r = world_to_grid(model.player.x, model.player.y)
        self.assertEqual((c, r), (1, 1))

        # Request moving RIGHT (free path)
        model.request_direction(Direction.RIGHT)
        for _ in range(10):
            model.update(0.05)
        self.assertGreater(model.player.x, model.player.start_pos[0])

    def test_berry_collection_and_score(self) -> None:
        model = CorsaModel(level_index=0)
        initial_remaining = model.remaining_berries
        initial_score = model.score

        # Move Momo to collect berries along the row
        model.request_direction(Direction.RIGHT)
        collected_any = False
        for _ in range(30):
            events = model.update(0.05)
            if "pop" in events or "chime" in events:
                collected_any = True

        self.assertTrue(collected_any)
        self.assertGreater(model.score, initial_score)
        self.assertLess(model.remaining_berries, initial_remaining)

    def test_rainbow_star_powerup(self) -> None:
        # Level 3 (index 2) has Rainbow Star Berry
        model = CorsaModel(level_index=2)
        self.assertFalse(model.is_rainbow_active)

        # Find rainbow star berry and teleport Momo onto it
        star_berry = next(b for b in model.berries if b.berry_type == BerryType.RAINBOW_STAR)
        model.player.x = star_berry.x
        model.player.y = star_berry.y

        events = model.update(0.05)
        self.assertIn("star_fanfare", events)
        self.assertTrue(model.is_rainbow_active)
        self.assertAlmostEqual(model.rainbow_timer, 6.0, places=1)
        # Critters should be dizzy
        for cr in model.critters:
            self.assertTrue(cr.is_dizzy)

    def test_critter_collision_and_recoverable_failure(self) -> None:
        # Level 2 (index 1) has 1 hedgehog (Baffo)
        model = CorsaModel(level_index=1)
        self.assertEqual(len(model.critters), 1)
        critter = model.critters[0]
        critter.is_napping = False

        # Teleport Momo onto critter without rainbow berry
        model.player.x = critter.x
        model.player.y = critter.y

        events = model.update(0.05)
        self.assertIn("bounce", events)
        self.assertEqual(model.hearts, 2)
        self.assertTrue(model.player.is_wobbling)
        # Momo bounces safely back to start position
        self.assertAlmostEqual(model.player.x, model.player.start_pos[0])

        # Test losing remaining hearts (Recoverable failure at 0 hearts)
        model.hearts = 1
        model.player.wobble_timer = 0.0
        model.player.x = critter.x
        model.player.y = critter.y
        events2 = model.update(0.05)
        self.assertIn("apple_munch", events2)
        # Hearts restored to max (3), no game over!
        self.assertEqual(model.hearts, 3)
        self.assertTrue(model.player.is_munching_apple)

    def test_critter_rescue_during_rainbow_power(self) -> None:
        model = CorsaModel(level_index=2)
        # Mark berries collected so we only measure critter tag score
        for b in model.berries:
            b.collected = True
        model.score = 0
        critter = model.critters[0]

        # Activate rainbow power
        model.rainbow_timer = 5.0
        critter.is_dizzy = True

        # Teleport Momo to tag the dizzy critter
        model.player.x = critter.x
        model.player.y = critter.y

        events = model.update(0.05)
        self.assertIn("dizzy_squeak", events)
        self.assertEqual(model.hearts, 3)  # Did not lose any hearts!
        self.assertTrue(critter.scurrying_home)
        self.assertEqual(model.score, 100)

    def test_difficulty_scaling_across_levels(self) -> None:
        for idx, lvl_cfg in enumerate(LEVELS):
            model = CorsaModel(level_index=idx)
            self.assertEqual(model.level_config.level_number, idx + 1)
            if idx == 0:
                self.assertEqual(len(model.critters), 0)
            elif idx == 1:
                self.assertEqual(len(model.critters), 1)
                self.assertEqual(model.critters[0].kind, CritterKind.BAFFO)
            elif idx == 2:
                self.assertEqual(len(model.critters), 1)
                # Rainbow star berry is available
                has_rainbow = any(b.berry_type == BerryType.RAINBOW_STAR for b in model.berries)
                self.assertTrue(has_rainbow)
            elif idx == 3:
                self.assertEqual(len(model.critters), 2)
                self.assertIsNotNone(model.bonus_fruit)
            elif idx == 4:
                self.assertEqual(len(model.critters), 2)
                self.assertIsNotNone(model.bonus_fruit)

    def test_app_and_renderer_smoke_run(self) -> None:
        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        app = build_app(screen=surf, locale="it")
        self.assertIsNotNone(app)
        self.assertIsNotNone(app.renderer)
        self.assertIsNotNone(app.model)

        # Run several ticks of model and renderer
        for _ in range(5):
            events = app.model.update(1.0 / 60.0)
            app.renderer.render(app.canvas.surface, app.model, 1.0 / 60.0)
        self.assertEqual(app.model.hearts, 3)


if __name__ == "__main__":
    unittest.main()
