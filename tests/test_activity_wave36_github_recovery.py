"""Regression for missing Wave 36 gameplay repairs restored to GitHub main.

Provider-free; run with the supported Pygame/Greia test environment.
These are source/interaction tests, not a substitute for real child sessions.
"""

from __future__ import annotations

import random
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pygame

from activities.memory_meraviglie.memory_app import MemoryApp
from activities.labirinto_magico.maze_app import MazeApp, MazeEngine
from activities.stelle_incantate.sky_app import AppState, SkyActivity
from activities.stelle_incantate.sky_model import SkySession
from activities.treno_numeri.treno_app import TrenoApp
from activities.treno_numeri.treno_model import TrainModel


def key(code: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=code)


class MemoryKeyboardRecoveryTests(unittest.TestCase):
    def make_app(self) -> MemoryApp:
        app = MemoryApp.__new__(MemoryApp)
        app.theme_idx = 0
        app.grid_idx = 1
        app.selected_card_index = 0
        app.flipped_indices = []
        app.particles = []
        app.cards = []
        app.sounds = Mock()
        app.completion = Mock()
        app._running = True
        app._start_new_game()
        return app

    def test_complete_match_round_using_keyboard_and_replay(self) -> None:
        app = self.make_app()
        with patch("activities.memory_meraviglie.memory_app.emit_activity_event") as report:
            pairs = {}
            for index, card in enumerate(app.cards):
                pairs.setdefault(card["id"], []).append(index)
            for pair in pairs.values():
                for destination in pair:
                    for _ in range(len(app.cards)):
                        if app.selected_card_index == destination:
                            break
                        app.handle_event(key(pygame.K_RIGHT))
                    self.assertEqual(app.selected_card_index, destination)
                    app.handle_event(key(pygame.K_RETURN))
            self.assertTrue(app.is_victory)
            self.assertEqual(app.pairs_found, app.total_pairs)
            self.assertEqual(
                [call.args[0] for call in report.call_args_list].count(
                    "memory.game_completed"
                ), 1
            )
        app.handle_event(key(pygame.K_SPACE))
        self.assertFalse(app.is_victory)
        self.assertEqual(app.pairs_found, 0)

    def test_keyboard_can_switch_theme_and_grid(self) -> None:
        app = self.make_app()
        original_theme, original_grid = app.theme_idx, app.grid_idx
        app.handle_event(key(pygame.K_t))
        app.handle_event(key(pygame.K_g))
        self.assertNotEqual(app.theme_idx, original_theme)
        self.assertNotEqual(app.grid_idx, original_grid)
        self.assertEqual(app.selected_card_index, 0)

    def test_vertical_focus_recovers_when_one_column_is_cleared(self) -> None:
        app = self.make_app()
        columns = 3
        for i, card in enumerate(app.cards):
            card["is_matched"] = i % columns == 0
        app.selected_card_index = 0
        app._move_focus(columns)
        self.assertNotEqual(app.selected_card_index % columns, 0)
        self.assertFalse(app.cards[app.selected_card_index]["is_matched"])

    def test_wrong_pair_is_temporarily_locked(self) -> None:
        app = self.make_app()
        first = 0
        other = next(i for i, card in enumerate(app.cards)
                     if card["id"] != app.cards[first]["id"])
        app._handle_card_click(first)
        app._handle_card_click(other)
        self.assertGreater(app.unflip_timer, 0)
        previously = app.moves_count
        for i in range(len(app.cards)):
            app._handle_card_click(i)
        self.assertEqual(app.moves_count, previously)
        for _ in range(40):
            app._update()
        self.assertEqual(app.flipped_indices, [])


class MazeMovingLockTests(unittest.TestCase):
    def test_new_commands_cannot_overwrite_active_slide(self) -> None:
        app = MazeApp.__new__(MazeApp)
        app.state = SimpleNamespace(
            is_victory=False, sliding_waypoints=[(0, 1)],
            facing_right=False, player_r=0, player_c=0,
            grid=[], exit_pos={"r": 2, "c": 2},
        )
        app.sounds = Mock()
        with patch.object(MazeEngine, "compute_slide_path") as compute:
            app.trigger_move(0, 1)
            compute.assert_not_called()
            self.assertEqual(app.state.sliding_waypoints, [(0, 1)])
            self.assertFalse(app.state.facing_right)
            app.state.sliding_waypoints.clear()
            compute.return_value = [(0, 1)]
            app.trigger_move(0, 1)
            self.assertEqual(app.state.sliding_waypoints, [(0, 1)])
            compute.assert_called_once()


class TrainKeyboardRecoveryTests(unittest.TestCase):
    def make_app(self) -> TrenoApp:
        app = TrenoApp.__new__(TrenoApp)
        app.model = TrainModel(rng=random.Random(12))
        app.train_state = "loading"
        app.model.train_state = "loading"
        app.train_offset_x = 0.0
        app.chug_timer = 0.0
        app.smoke_particles = []
        app.flying_items = []
        app.celebration_particles = []
        app.celebration_timer = 0.0
        app.selected_crate = 0
        app.running = True
        app.sounds = Mock()
        app.storage = None
        app.completion = Mock()
        app.renderer = Mock()
        app.completion_presented = False
        app._journey_id = "keyboard-test"
        return app

    def test_complete_all_stations_with_only_keyboard(self) -> None:
        app = self.make_app()
        with patch("activities.treno_numeri.treno_app.emit_activity_event") as report:
            for frame in range(1800):
                if app.model.is_victory:
                    break
                if app.train_state == "loading":
                    app.handle_event(key(pygame.K_SPACE))
                app._step_frame(0.2)
            self.assertTrue(app.model.is_victory, "journey should terminate")
            self.assertEqual(app.model.total_stars, app.model.total_stations)
            names = [call.args[0] for call in report.call_args_list]
            self.assertEqual(names.count("train.station_completed"), app.model.total_stations)
            self.assertEqual(names.count("train.journey_completed"), 1)
            app.handle_event(key(pygame.K_RETURN))
            self.assertFalse(app.model.is_victory)
            self.assertEqual(app.model.round_idx, 0)
            self.assertEqual(app.model.total_stars, app.model.total_stations)

    def test_crate_controls_do_not_load_during_travel(self) -> None:
        app = self.make_app()
        app.train_state = "arriving"
        app.handle_event(key(pygame.K_RETURN))
        self.assertEqual(app.model.loaded_count, 0)
        app.train_state = "loading"
        app.handle_event(key(pygame.K_RIGHT))
        self.assertEqual(app.selected_crate, 1 if app.model.mode == "addition" else 0)
        app.handle_event(key(pygame.K_RETURN))
        self.assertGreater(app.model.loaded_count, 0)


class StarsKeyboardRecoveryTests(unittest.TestCase):
    def make_app(self) -> SkyActivity:
        app = SkyActivity.__new__(SkyActivity)
        app.session = SkySession()
        app._state = AppState.PLAYING
        app._state_started = 0.0
        app.selected_star_index = 0
        app.audio = Mock()
        app.events = Mock()
        app.storage = Mock()
        app.storage.load_completed.return_value = ()
        app.resources = Mock()
        app.resources.text.return_value = "A constellation"
        app.clock = lambda: 10.0
        app.session_id = "test"
        app.completion = Mock()
        app._line_progress = 1.0
        app._wrong_star = None
        app._fact_opened_for = None
        return app

    def test_connect_star_round_and_advance_keyboard_only(self) -> None:
        app = self.make_app()
        expected = app.session.current.star_count
        for idx in range(expected):
            self.assertEqual(app.selected_star_index, idx)
            app._handle_keydown(pygame.K_RETURN)
        self.assertEqual(app._state, AppState.CELEBRATE)
        app._state_started = 0.0
        app._handle_keydown(pygame.K_SPACE)
        self.assertEqual(app._state, AppState.PLAYING)
        self.assertEqual(app.selected_star_index, 0)
        app.events.constellation_completed.assert_called_once()

    def test_number_shortcut_cannot_leave_selection_outside_star_array(self) -> None:
        app = self.make_app()
        count = app.session.current.star_count
        app._handle_keydown(pygame.K_9)
        if count < 9:
            self.assertEqual(app.selected_star_index, 0)
            self.assertEqual(len(app.session.current.connected), 0)

    def test_fact_speech_disallows_foreign_language_fallback(self) -> None:
        app = self.make_app()
        app.resources.audio_cue.return_value = None
        app._handle_keydown(pygame.K_f)
        app.resources.audio_cue.assert_called_once_with(
            app.session.current.constellation.fact_key, allow_fallback=False
        )
