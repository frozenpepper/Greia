"""Wave 37 regression: child-operable hybrid input and corrupt-save recovery.

Runs with the same Pygame dependency as the shipped Activities, but without
opening a window, fetching voices, or using live child profile data.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import pygame

from activities.nascondino_bosco.woodland_app import AppState, WoodlandApp
from activities.nascondino_bosco.woodland_content import FINDS_PER_ROUND, SEASONS
from activities.nascondino_bosco.woodland_model import HideRound, Pick
from activities.nascondino_bosco.woodland_services import WoodlandProgress
from activities.piccola_serra.serra_app import SerraActivity
from activities.piccola_serra.serra_content import CURE
from activities.piccola_serra.serra_model import Phase, SerraProgress, Visit
from activities.acquario_magico.acquarium_app import (
    AquariumApp,
    CHEST_RECT,
    _safe_saved_counter,
    build_app as build_aquarium,
)
from activities.acquario_magico.acquarium_model import AquariumSession
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography
from pathlib import Path
import random

AQUARIUM_DIR = Path(__file__).resolve().parents[1] / "activities" / "acquario_magico"
WOODLAND_DIR = Path(__file__).resolve().parents[1] / "activities" / "nascondino_bosco"
SERRA_DIR = Path(__file__).resolve().parents[1] / "activities" / "piccola_serra"


class WoodlandKeyboardCycleTests(TestCase):
    """Hide & Seek through the shared control kit: keys only, no window."""

    def build_app(self) -> WoodlandApp:
        surface = pygame.Surface((1024, 600))
        self.now = [500.0]
        self.events = SimpleNamespace(friend_found=Mock(), round_completed=Mock())
        progress = SimpleNamespace(load=lambda: WoodlandProgress(), save=Mock())
        return WoodlandApp(
            screen=surface,
            canvas=PygameReferenceCanvas(surface),
            typography=GreiaTypography(),
            resources=activity_resources(WOODLAND_DIR, requested_locale="en"),
            audio=Mock(has_name=Mock(return_value=False), say_name=Mock(return_value=False)),
            progress=progress,
            events=self.events,
            rng=random.Random(5),
            clock=lambda: self.now[0],
        )

    def advance(self, app: WoodlandApp, seconds: float) -> None:
        end = self.now[0] + seconds
        while self.now[0] < end:
            self.now[0] += 0.05
            app.step()

    def focus_spot(self, app: WoodlandApp, target: str) -> None:
        for _ in range(12):
            for key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT, pygame.K_UP):
                if app.controls.layer.focused_id == target:
                    return
                app.press(key)

    def test_four_unique_keyboard_discoveries_and_replay(self) -> None:
        app = self.build_app()
        self.advance(app, 1.0)
        for expected in range(1, FINDS_PER_ROUND + 1):
            target = f"spot.{app.round.target_spot}"
            self.focus_spot(app, target)
            self.assertEqual(app.controls.layer.focused_id, target)
            self.assertTrue(app.press(pygame.K_SPACE))
            self.assertEqual(len(app.round.found), expected)
            self.assertEqual(len(set(app.round.found)), expected)
            self.advance(app, 3.2)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(self.events.friend_found.call_count, FINDS_PER_ROUND)
        self.assertEqual(self.events.round_completed.call_count, 1)
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.round.found, [])

    def test_rewarded_spot_cannot_be_counted_again(self) -> None:
        game = HideRound(SEASONS[0], 1, random.Random(3))
        spot = game.target_spot
        self.assertIs(game.choose(spot).pick, Pick.FOUND)
        self.assertIs(game.choose(spot).pick, Pick.IGNORED)
        self.assertEqual(len(game.found), 1)

    def test_keyboard_focus_moves_between_places(self) -> None:
        app = self.build_app()
        self.advance(app, 1.0)
        start = app.controls.layer.focused_id
        self.assertTrue(start.startswith("spot."))
        app.press(pygame.K_RIGHT)
        self.assertTrue(app.controls.layer.focused_id.startswith("spot."))
        self.assertTrue(app.controls.layer.focus_visible)


class GreenhouseKeyboardCycleTests(TestCase):
    """Piccola Serra through the shared control kit: keys only, no window."""

    def build_app(self) -> SerraActivity:
        surface = pygame.Surface((1024, 600))
        self.now = [500.0]
        self.events = SimpleNamespace(seed_planted=Mock(), plant_finished=Mock(), visit_completed=Mock())
        progress = SimpleNamespace(load=lambda: SerraProgress(), save=Mock())
        return SerraActivity(
            screen=surface,
            canvas=PygameReferenceCanvas(surface),
            visit=Visit(SerraProgress(), random.Random(7)),
            typography=GreiaTypography(),
            resources=activity_resources(SERRA_DIR, requested_locale="en"),
            audio=Mock(),
            progress=progress,
            events=self.events,
            clock=lambda: self.now[0],
        )

    def settle(self, app: SerraActivity) -> None:
        for _ in range(400):
            if not app.busy and not app.timeline.busy and not app.motion.flights:
                return
            self.now[0] += 0.05
            app.step()
        self.fail("greenhouse never settled")

    def focus_and_enter(self, app: SerraActivity, control_id: str) -> None:
        self.settle(app)
        layer = app.controls.layer
        for _ in range(6):
            app.press(pygame.K_LEFT)
        for _ in range(6):
            if layer.focused_id == control_id:
                break
            app.press(pygame.K_RIGHT)
        self.assertEqual(layer.focused_id, control_id)
        self.assertTrue(layer.focus_visible)
        app.press(pygame.K_RETURN)

    def test_keyboard_only_grows_harvests_and_orders_one_plant(self) -> None:
        app = self.build_app()
        self.focus_and_enter(app, "seed.bean")
        self.events.seed_planted.assert_called_once()
        while app.visit.phase is Phase.GROW:
            self.focus_and_enter(app, f"care.{CURE[app.visit.cycle.need].value}")
        sequence = app.visit.sequence
        while not sequence.complete:
            self.focus_and_enter(app, f"card.{sequence.expected.value}")
        self.settle(app)
        self.events.plant_finished.assert_called_once()
        self.assertEqual(app.visit.completed, 1)
        self.assertIs(app.visit.phase, Phase.CHOOSE)

    def test_number_keys_pick_tiles_of_the_current_row(self) -> None:
        app = self.build_app()
        self.settle(app)
        self.assertTrue(app.press(pygame.K_2))  # second packet: sunflower
        self.assertEqual(app.visit.cycle.plant.plant_id, "sunflower")
        self.assertFalse(app.press(pygame.K_9))

    def test_touch_mouse_emulation_is_one_tap_not_two(self) -> None:
        app = self.build_app()
        self.settle(app)
        x, y = app.physical_center("seed.carrot")
        app.handle_event(pygame.event.Event(pygame.FINGERDOWN, x=x / 1024, y=y / 600, touch_id=1, finger_id=1))
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y), touch=True))
        app.handle_event(pygame.event.Event(pygame.FINGERUP, x=x / 1024, y=y / 600, touch_id=1, finger_id=1))
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(x, y), touch=True))
        self.events.seed_planted.assert_called_once()
        self.assertEqual(app.visit.cycle.plant.plant_id, "carrot")


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
