"""Comprehensive test suite for Il Grande Albero delle Stagioni (org.greia.quattro-stagioni)."""

from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

from activities.quattro_stagioni.tree_app import TreeActivity
from activities.quattro_stagioni.tree_audio import SpeechQueue, TreeAudio
from activities.quattro_stagioni.tree_model import (
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    Season,
    TreeModel,
    WeatherMode,
)
from activities.quattro_stagioni.tree_renderer import TreeRenderer

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "activities" / "quattro_stagioni"


class TestQuattroStagioniDomain(unittest.TestCase):
    """Test model invariants, weather, seasons, and entity mechanics."""

    def setUp(self) -> None:
        self.model = TreeModel()

    def test_initial_state(self) -> None:
        self.assertEqual(self.model.season, Season.SPRING)
        self.assertEqual(self.model.weather, WeatherMode.SUN)
        self.assertEqual(self.model.day_ratio, 1.0)
        self.assertFalse(self.model.experienced_night)
        self.assertFalse(self.model.completed_cycle)
        self.assertEqual(len(self.model.clouds), 3)

    def test_day_night_toggle(self) -> None:
        # Initial day
        is_day = self.model.toggle_day_night()
        self.assertFalse(is_day)
        self.assertEqual(self.model.target_day_ratio, 0.0)

        # Update dt to simulate transition to night
        self.model.update(1.0)
        self.assertLess(self.model.day_ratio, 0.5)
        self.assertTrue(self.model.experienced_night)

        # Toggle back to day
        is_day = self.model.toggle_day_night()
        self.assertTrue(is_day)
        self.assertEqual(self.model.target_day_ratio, 1.0)

    def test_weather_transitions(self) -> None:
        self.model.set_weather(WeatherMode.RAIN)
        self.assertEqual(self.model.weather, WeatherMode.RAIN)
        self.assertIn(WeatherMode.RAIN, self.model.discovered_weather)

        # Update generates rain particles
        self.model.update(0.1)
        rain_particles = [p for p in self.model.particles if p.kind == "rain"]
        self.assertGreater(len(rain_particles), 0)

        # Snow weather
        self.model.set_weather(WeatherMode.SNOW)
        self.assertEqual(self.model.weather, WeatherMode.SNOW)
        self.model.update(0.1)
        snow_particles = [p for p in self.model.particles if p.kind == "snow"]
        self.assertGreater(len(snow_particles), 0)

    def test_season_transitions_and_cycle(self) -> None:
        seasons_to_visit = [Season.SUMMER, Season.AUTUMN, Season.WINTER, Season.SPRING]
        for s in seasons_to_visit:
            self.model.set_season(s)
            self.assertEqual(self.model.season, s)

        self.assertEqual(len(self.model.discovered_seasons), 4)
        self.assertTrue(self.model.completed_cycle)

    def test_summer_apple_harvest(self) -> None:
        self.model.set_season(Season.SUMMER)
        self.assertGreater(len(self.model.apples), 0)

        # Tap first apple
        tapped = self.model.tap_apple(0)
        self.assertTrue(tapped)
        self.assertTrue(self.model.apples[0].is_falling)

        # Update until it lands in basket
        self.model.update(1.0)
        self.assertTrue(self.model.apples[0].in_basket)
        self.assertFalse(self.model.apples[0].is_falling)

    def test_winter_snowman_building(self) -> None:
        self.model.set_season(Season.WINTER)
        self.assertEqual(self.model.snowman_stage, 1)

        # Tap snowman to progress
        self.assertTrue(self.model.tap_snowman())
        self.assertEqual(self.model.snowman_stage, 2)
        self.assertTrue(self.model.tap_snowman())
        self.assertEqual(self.model.snowman_stage, 3)
        # Cannot exceed stage 3
        self.assertTrue(self.model.tap_snowman())
        self.assertEqual(self.model.snowman_stage, 3)

    def test_tito_hop_on_tap(self) -> None:
        self.model.tap_tito()
        self.assertEqual(self.model.tito_hop_offset, 25.0)
        self.model.update(0.1)
        self.assertLess(self.model.tito_hop_offset, 25.0)


class TestQuattroStagioniAudioAndSpeech(unittest.TestCase):
    """Test audio synthesis and speech queue logic."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.mixer.init()

    def test_audio_and_queue(self) -> None:
        audio = TreeAudio(PACKAGE_ROOT, locale="it")
        queue = SpeechQueue(audio)

        queue.enqueue("welcome", delay_after=0.1)
        queue.enqueue("day", delay_after=0.1)
        self.assertEqual(len(queue._queue), 2)

        queue.clear()
        self.assertEqual(len(queue._queue), 0)


class TestQuattroStagioniRendererAndApp(unittest.TestCase):
    """Test renderer execution and input handling in dummy mode."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def setUp(self) -> None:
        self.screen = pygame.display.get_surface()
        self.model = TreeModel()
        self.renderer = TreeRenderer()
        self.audio = TreeAudio(PACKAGE_ROOT, locale="it")
        self.app = TreeActivity(self.screen, self.renderer, self.audio, self.model)

    def test_discovery_events_require_new_season_and_complete_once(self) -> None:
        events = Mock()
        app = TreeActivity(self.screen, self.renderer, self.audio, self.model, events)
        for season, rect in self.renderer.season_buttons.items():
            app._handle_pointer_down(rect.center)
        self.assertEqual(events.season_explored.call_count, 3)
        events.all_seasons_discovered.assert_called_once()
        app._handle_pointer_down(self.renderer.season_buttons[Season.SUMMER].center)
        self.assertEqual(events.season_explored.call_count, 3)
        events.all_seasons_discovered.assert_called_once()

    def test_protected_home_is_not_a_season_button(self) -> None:
        from greia_platform.pygame_canvas import activity_viewport_for_surface
        app = TreeActivity(self.screen, self.renderer, self.audio, self.model)
        rect = activity_viewport_for_surface(self.screen).protected_regions[0]
        app._handle_pointer_down((int(rect.x) + 1, int(rect.y) + 1))
        self.assertTrue(app.running)
        self.assertEqual(self.model.season, Season.SPRING)
        self.assertFalse(self.model.experienced_night)

    def test_render_all_seasons_without_crash(self) -> None:
        for s in Season:
            self.model.set_season(s)
            self.renderer.render(self.screen, self.model)

    def test_render_night_and_day_without_crash(self) -> None:
        self.model.day_ratio = 0.0
        self.renderer.render(self.screen, self.model)
        self.model.day_ratio = 1.0
        self.renderer.render(self.screen, self.model)

    def test_pointer_input_handling(self) -> None:
        # Tap sun / moon
        cx, cy = self.renderer.celestial_rect.center
        self.app._handle_pointer_down((cx, cy))
        self.assertEqual(self.model.target_day_ratio, 0.0)

        # Tap summer season button
        summer_rect = self.renderer.season_buttons[Season.SUMMER]
        self.app._handle_pointer_down(summer_rect.center)
        self.assertEqual(self.model.season, Season.SUMMER)

        # Tap rain weather button
        rain_rect = self.renderer.weather_buttons[WeatherMode.RAIN]
        self.app._handle_pointer_down(rain_rect.center)
        self.assertEqual(self.model.weather, WeatherMode.RAIN)


if __name__ == "__main__":
    unittest.main()
