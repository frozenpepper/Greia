"""Wave 37 regression: child-operable hybrid input and corrupt-save recovery.

Runs with the same Pygame dependency as the shipped Activities, but without
opening a window, fetching voices, or using live child profile data.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import pygame

from activities.nascondino_bosco.woodland_app import WoodlandApp
from activities.nascondino_bosco.woodland_model import WoodlandGameState
from activities.piccola_serra.serra_app import SerraApp
from activities.piccola_serra.serra_model import SerraModel
from activities.acquario_magico.acquarium_app import (
    AquariumApp,
    CHEST_RECT,
    _safe_saved_counter,
    build_app as build_aquarium,
)
from activities.acquario_magico.acquarium_model import AquariumSession
from greia_platform.localization import activity_resources
from pathlib import Path

AQUARIUM_DIR = Path(__file__).resolve().parents[1] / "activities" / "acquario_magico"


class WoodlandKeyboardCycleTests(TestCase):
    def build_app(self) -> WoodlandApp:
        app = WoodlandApp.__new__(WoodlandApp)
        app.state = WoodlandGameState()
        app.state.start_round()
        app.selected_spot_index = 0
        app.audio = Mock()
        app.storage = None
        return app

    def test_four_unique_keyboard_discoveries_and_replay(self) -> None:
        app = self.build_app()
        with patch("activities.nascondino_bosco.woodland_app.emit_activity_event") as publish:
            for expected_found in range(1, app.state.total_to_find + 1):
                target_index = next(
                    i for i, spot in enumerate(app.state.spots)
                    if spot.spot_id not in app.state.found_spot_ids
                    and app.state.hiding_map[spot.spot_id] == app.state.target_animal_id
                )
                while app.selected_spot_index != target_index:
                    self.assertTrue(app._handle_keydown(pygame.K_RIGHT))
                self.assertTrue(app._handle_keydown(pygame.K_RETURN))
                self.assertEqual(app.state.found_count, expected_found)
                self.assertEqual(len(app.state.found_spot_ids), expected_found)
                if not app.state.is_victory:
                    focused = app.state.spots[app.selected_spot_index].spot_id
                    self.assertNotIn(focused, app.state.found_spot_ids)
            self.assertTrue(app.state.is_victory)
            self.assertEqual(app.state.total_stars, app.state.total_to_find)
            self.assertEqual(
                [c.args[0] for c in publish.call_args_list].count("woodland.animal_found"),
                app.state.total_to_find,
            )
            self.assertEqual(
                [c.args[0] for c in publish.call_args_list].count("woodland.round_completed"),
                1,
            )
            self.assertTrue(app._handle_keydown(pygame.K_SPACE))
            self.assertFalse(app.state.is_victory)
            self.assertEqual(app.state.found_count, 0)
            self.assertFalse(app.state.found_spot_ids)
            self.assertEqual(app.selected_spot_index, 0)

    def test_rewarded_spot_cannot_be_counted_again(self) -> None:
        state = WoodlandGameState()
        state.start_round()
        spot_id = next(
            spot for spot, animal in state.hiding_map.items()
            if animal == state.target_animal_id
        )
        self.assertTrue(state.inspect_spot(spot_id)[0])
        stars = state.total_stars
        self.assertEqual(state.inspect_spot(spot_id), (False, None))
        self.assertEqual(state.total_stars, stars)

    def test_keyboard_direction_is_cyclic(self) -> None:
        app = self.build_app()
        self.assertTrue(app._handle_keydown(pygame.K_LEFT))
        self.assertEqual(app.selected_spot_index, len(app.state.spots) - 1)
        self.assertTrue(app._handle_keydown(pygame.K_DOWN))
        self.assertEqual(app.selected_spot_index, 0)


class GreenhouseKeyboardCycleTests(TestCase):
    def build_app(self) -> SerraApp:
        app = SerraApp.__new__(SerraApp)
        app.model = SerraModel()
        app.active_tool = 0
        app.selected_plant_type = 0
        app.selected_pot_index = 0
        app.sounds = Mock()
        return app

    def test_keyboard_only_full_harvest_and_tool_state(self) -> None:
        app = self.build_app()
        with patch("activities.piccola_serra.serra_app.emit_activity_event") as publish:
            for harvest in range(app.model.target_harvest):
                if harvest:
                    app._handle_keydown(pygame.K_RIGHT)
                for key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_2, pygame.K_4):
                    app._handle_keydown(key)
                    app._handle_keydown(pygame.K_RETURN)
                self.assertEqual(app.model.harvest_count, harvest + 1)
            self.assertTrue(app.model.is_victory)
            self.assertEqual(
                [c.args[0] for c in publish.call_args_list].count("greenhouse.harvest_completed"),
                1,
            )
            app._handle_keydown(pygame.K_1)
            app._handle_keydown(pygame.K_RETURN)
            self.assertTrue(app.model.is_victory)
            self.assertEqual(app.model.harvest_count, app.model.target_harvest)

    def test_keyboard_plant_and_pot_selection_are_bounded(self) -> None:
        app = self.build_app()
        app._handle_keydown(pygame.K_LEFT)
        self.assertEqual(app.selected_pot_index, 3)
        app._handle_keydown(pygame.K_UP)
        self.assertEqual(app.selected_pot_index, 1)
        app._handle_keydown(pygame.K_TAB)
        self.assertEqual(app.selected_plant_type, 1)

    def test_touch_mouse_emulation_does_not_duplicate_growth(self) -> None:
        app = self.build_app()
        app._handle_pointer = Mock()
        app.handle_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONUP, button=1, pos=(200, 360), touch=True
            )
        )
        app._handle_pointer.assert_not_called()

    def test_touch_normalizes_position_before_shared_pointer_path(self) -> None:
        app = self.build_app()
        app.screen = pygame.Surface((800, 480))
        app._handle_pointer = Mock()
        app.handle_event(pygame.event.Event(pygame.FINGERDOWN, x=0.25, y=0.75))
        app._handle_pointer.assert_called_once_with((200, 360))


class AquariumKeyboardAndRecoveryTests(TestCase):
    def build_app(self) -> AquariumApp:
        # Real app (shared control kit owns Space/Enter/arrows); empty tank,
        # no optional missions, so each key's effect is observable alone.
        app = build_aquarium(pygame.Surface((1024, 600)), activity_resources(AQUARIUM_DIR, requested_locale="en"), audio=Mock())
        app.missions_enabled = False
        app._missions.enabled = False
        app.session = AquariumSession()
        app.keyboard_cursor = (512, 300)
        return app

    def test_keyboard_can_spawn_feed_bubble_toggle_and_open_chest(self) -> None:
        app = self.build_app()
        with patch("activities.acquario_magico.acquarium_app.emit_activity_event"):
            app._handle_keydown(pygame.K_1)
            app._handle_keydown(pygame.K_RETURN)
            self.assertEqual(len(app.session.creatures), 1)
            app.keyboard_cursor = (100, 180)
            app._handle_keydown(pygame.K_2)
            app._handle_keydown(pygame.K_RETURN)
            self.assertEqual(len(app.session.food_pellets), 3)
            app._handle_keydown(pygame.K_3)
            app._handle_keydown(pygame.K_RETURN)
            self.assertGreater(len(app.session.bubbles), 0)
            # Space is the standard ACTIVATE key now; night has its own key.
            app._handle_keydown(pygame.K_n)
            self.assertTrue(app.session.glow_mode)
            app.keyboard_cursor = CHEST_RECT.center
            app._handle_keydown(pygame.K_RETURN)
            self.assertGreater(app.session.chest_open_timer, 0)
        self.assertGreaterEqual(app.audio.play.call_count, 4)

    def test_cursor_is_bounded_and_moves_with_arrows(self) -> None:
        app = self.build_app()
        for _ in range(50):
            app._handle_keydown(pygame.K_LEFT)
            app._handle_keydown(pygame.K_UP)
        self.assertEqual(app.keyboard_cursor, (70, 85))
        for _ in range(50):
            app._handle_keydown(pygame.K_RIGHT)
        for _ in range(9):  # one more Down would leave the water for the toolbar
            app._handle_keydown(pygame.K_DOWN)
        self.assertEqual(app.keyboard_cursor, (954, 490))

    def test_touch_emulated_mouse_is_not_counted_as_second_action(self) -> None:
        app = self.build_app()
        app.handle_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=(512, 300), touch=True
            )
        )
        self.assertEqual(len(app.session.creatures), 0)

    def test_corrupt_persisted_counters_are_bounded(self) -> None:
        app = self.build_app()
        app.storage = SimpleNamespace(
            kv_get=lambda key: {
                "total_fed": "invalid",
                "total_popped": float("nan"),
                "glow_mode": True,
            }
        )
        app._restore_saved_state()
        self.assertEqual(app.session.total_fed, 0)
        self.assertEqual(app.session.total_popped, 0)
        self.assertTrue(app.session.glow_mode)
        self.assertEqual(_safe_saved_counter(-100), 0)
        self.assertEqual(_safe_saved_counter("99999999999999"), 1_000_000_000)
        self.assertEqual(_safe_saved_counter(None), 0)
