"""Regression for missing Wave 36 gameplay repairs restored to GitHub main.

Provider-free; run with the supported Pygame/Greia test environment.
These are source/interaction tests, not a substitute for real child sessions.
"""

from __future__ import annotations

import random
import unittest
from unittest.mock import Mock, patch

import pygame

from activities.memory_meraviglie.memory_app import MemoryApp


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


# Magical Labyrinth's "a new command cannot overwrite an active slide" lock
# moved to tests/test_activity_labirinto_magico.py (AppLoopTests) when the
# Activity was reworked onto the shared control kit; a press while Tito walks
# is now one buffered turn applied on arrival. The old MazeApp/MazeEngine no
# longer exist.


# Treno Numeri's keyboard-only journey and bounded-celebration recovery moved to
# tests/test_activity_treno_numeri.py (AppLoopTests) when the Activity was
# reworked onto the shared control kit; the old TrainModel/auto-cap app no
# longer exists.


# Stelle Incantate's keyboard-only figure and number-input recovery moved to
# tests/test_activity_stelle_incantate.py (AppLoopTests) when the Activity was
# reworked onto the shared control kit; the old SkySession/auto-focus app no
# longer exists. Its "fact speech disallows foreign-language fallback" check was
# retired: the owner's speech fallback policy (selected -> base -> English ->
# silence) supersedes it.


