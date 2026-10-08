"""Regression contracts for action-game pointer ownership.

These tests use queued Pygame events rather than the global instantaneous
mouse state, matching touch translation and remote Simulator event injection.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

import pygame

from activities.corsa_bacche.corsa_app import CorsaApp
from activities.quattro_amici.quattro_app import QuattroApp, _is_safe_pointer
from activities.viaggio_delfino.delfino_app import DelfinoJourneyApp


class CorsaPointerTests(unittest.TestCase):
    def test_queued_click_drag_release_and_focus_loss(self):
        app = object.__new__(CorsaApp)
        app._pointer_drag_held = False
        points = []
        app._handle_pointer_motion = lambda pos: points.append(pos)
        # Explicit press must steer regardless of current device-state polling.
        app._process_pointer_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 150))
        )
        app._process_pointer_event(
            pygame.event.Event(pygame.MOUSEMOTION, pos=(110, 152))
        )
        app._process_pointer_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(110, 152))
        )
        app._process_pointer_event(
            pygame.event.Event(pygame.MOUSEMOTION, pos=(200, 250))
        )
        self.assertEqual(points, [(100, 150), (110, 152)])
        self.assertFalse(app._pointer_drag_held)
        app._process_pointer_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(300, 350))
        )
        app._process_pointer_event(
            pygame.event.Event(pygame.WINDOWFOCUSLOST)
        )
        app._process_pointer_event(
            pygame.event.Event(pygame.MOUSEMOTION, pos=(350, 350))
        )
        self.assertEqual(points[-1], (300, 350))
        self.assertEqual(len(points), 3)

    def test_secondary_button_never_starts_gameplay_drag(self):
        app = object.__new__(CorsaApp)
        app._pointer_drag_held = False
        points = []
        app._handle_pointer_motion = lambda pos: points.append(pos)
        app._process_pointer_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(10, 10))
        )
        app._process_pointer_event(
            pygame.event.Event(pygame.MOUSEMOTION, pos=(20, 20))
        )
        self.assertEqual(points, [])


class QuattroPointerTests(unittest.TestCase):
    def test_protected_and_outside_region_rejected(self):
        viewport = SimpleNamespace(
            surface=SimpleNamespace(width=1024, height=600),
            protected_regions=(SimpleNamespace(x=0, y=0, right=90, bottom=90),),
        )
        with mock.patch(
            "activities.quattro_amici.quattro_app.activity_viewport_for_surface",
            return_value=viewport,
        ):
            surface = object()
            self.assertFalse(_is_safe_pointer(surface, (10, 10)))
            self.assertFalse(_is_safe_pointer(surface, (-1, 100)))
            self.assertFalse(_is_safe_pointer(surface, (1024, 100)))
            self.assertTrue(_is_safe_pointer(surface, (150, 150)))

    def test_blocked_pointer_cannot_hover_or_drop(self):
        app = object.__new__(QuattroApp)
        app.screen = object()
        app.model = object()
        app.canvas = SimpleNamespace(pointer=lambda pos: (float(pos[0]), float(pos[1])))
        app.renderer = SimpleNamespace(get_column_at_x=lambda *_: 3)
        app.audio = SimpleNamespace(play_hover=mock.Mock())
        app.selected_col = 1
        drops = []
        app._handle_click = lambda x, y: drops.append((x, y))
        events = [
            pygame.event.Event(pygame.MOUSEMOTION, pos=(5, 5)),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(5, 5)),
            pygame.event.Event(pygame.MOUSEMOTION, pos=(150, 150)),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(150, 150)),
        ]
        with (
            mock.patch("activities.quattro_amici.quattro_app.pygame.event.get", return_value=events),
            mock.patch(
                "activities.quattro_amici.quattro_app._is_safe_pointer",
                side_effect=lambda _screen, pos: pos[0] >= 100,
            ),
        ):
            app._process_events()
        self.assertEqual(app.selected_col, 3)
        app.audio.play_hover.assert_called_once()
        self.assertEqual(drops, [(150.0, 150.0)])



class DolphinResizeTests(unittest.TestCase):
    def test_main_loop_presents_replaced_canvas_after_video_resize(self):
        """Resize must switch the current frame, not only a future instance field."""
        app = object.__new__(DelfinoJourneyApp)
        old_canvas = SimpleNamespace(surface=object(), present=mock.Mock())
        new_canvas = SimpleNamespace(surface=object(), present=mock.Mock())
        app.screen = object()
        app.canvas = old_canvas
        app.completion_screen = None
        app.renderer = SimpleNamespace(render_world=mock.Mock(), draw_hud=mock.Mock())
        app.world = SimpleNamespace(
            dolphin=SimpleNamespace(x=0.0),
            session_pearls=0,
            update=lambda _dt, _rng: [],
        )
        app._rng = object()
        app._banner_text = None
        app._banner_until = 0.0
        app._active_fact = None
        app._fact_until = 0.0
        app.start_new_journey = lambda: None
        app._toggle_welcome = lambda: None
        app._persist = mock.Mock()
        app.events_service = SimpleNamespace(close=mock.Mock())
        app.audio = SimpleNamespace(shutdown=mock.Mock())

        def resize(_old_screen, _old_canvas, _running, _dt):
            app.screen = object()
            app.canvas = new_canvas
            return False

        app._handle_events = resize
        fake_clock = SimpleNamespace(tick=lambda *_: 16)
        with (
            mock.patch("activities.viaggio_delfino.delfino_app.pygame.time.Clock", return_value=fake_clock),
            mock.patch("activities.viaggio_delfino.delfino_app.get_theme", return_value=SimpleNamespace(background=(0, 0, 0))),
            mock.patch("activities.viaggio_delfino.delfino_app.activity_stop_requested", return_value=False),
            mock.patch("activities.viaggio_delfino.delfino_app.mark_activity_ready"),
            mock.patch("activities.viaggio_delfino.delfino_app.pygame.display.flip"),
            mock.patch("activities.viaggio_delfino.delfino_app.pygame.quit"),
        ):
            self.assertEqual(app.run(), 0)
        new_canvas.present.assert_called_once()
        old_canvas.present.assert_not_called()
        app.renderer.render_world.assert_called_once_with(new_canvas.surface, app.world)


if __name__ == "__main__":
    unittest.main()
