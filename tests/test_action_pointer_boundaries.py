"""Regression contracts for action-game pointer ownership.

These tests use queued Pygame events rather than the global instantaneous
mouse state, matching touch translation and remote Simulator event injection.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

import pygame

from activities.corsa_bacche.corsa_app import CorsaActivity
from activities.quattro_amici.quattro_app import QuattroApp, _is_safe_pointer
from activities.viaggio_delfino.delfino_app import DelfinoJourneyApp


class CorsaPointerTests(unittest.TestCase):
    """Berry Chase: queued press/drag/release drive tap-to-go; chrome stays Greia's."""

    @classmethod
    def setUpClass(cls) -> None:
        import os

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()

    def _app(self):
        import random

        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from activities.corsa_bacche.corsa_model import CorsaProgress, Visit

        screen = pygame.display.set_mode((1024, 600))
        storage = SimpleNamespace(kv_get=lambda *a, **k: None, kv_set=lambda *a, **k: None)
        from activities.corsa_bacche.corsa_services import GreiaCorsaProgress

        return CorsaActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            visit=Visit(CorsaProgress(), random.Random(1)),
            typography=GreiaTypography(),
            resources=None,
            audio=SimpleNamespace(
                say=lambda *_: None, then=lambda *_: None, say_if_quiet=lambda *_: None, play=lambda *_: None
            ),
            progress=GreiaCorsaProgress(storage),
            events=SimpleNamespace(garden_cleared=lambda *_: None, visit_completed=lambda *_: None),
            clock=lambda: 100.0,
        )

    def _point(self, app, cell):
        x, y = app.geometry.center(*cell)
        return app.canvas.mapper.point(int(x), int(y))

    def test_queued_click_drag_release_and_focus_loss(self):
        app = self._app()
        targets = []
        app.garden.go_to = lambda cell: targets.append(cell) or True
        a, b, c = (1, 0), (2, 0), (2, 2)
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=self._point(app, a)))
        app._handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=self._point(app, b), rel=(0, 1), buttons=(1, 0, 0)))
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=self._point(app, b)))
        app._handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=self._point(app, c), rel=(1, 0), buttons=(0, 0, 0)))
        self.assertEqual(targets, [a, b])  # hover after release never steers
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=self._point(app, a)))
        app._handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        app._handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=self._point(app, c), rel=(1, 0), buttons=(1, 0, 0)))
        self.assertEqual(targets, [a, b, a])

    def test_secondary_button_and_protected_chrome_never_start_gameplay(self):
        app = self._app()
        targets = []
        app.garden.go_to = lambda cell: targets.append(cell) or True
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=self._point(app, (1, 1))))
        app._handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=self._point(app, (2, 2)), rel=(1, 1), buttons=(0, 0, 1)))
        self.assertFalse(app.tap((5, 5)))
        self.assertEqual(targets, [])


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
        app.canvas = old_canvas
        app._running = True
        app._enter_picker = lambda: None
        app.advance = lambda _dt: None
        drawn_on = []
        app.draw = lambda: drawn_on.append(app.canvas)
        app.shutdown = mock.Mock()

        def resize(_event):
            app.canvas = new_canvas

        app.handle_event = resize
        with (
            mock.patch(
                "activities.viaggio_delfino.delfino_app.pygame.event.get",
                return_value=[SimpleNamespace(type=pygame.VIDEORESIZE)],
            ),
            mock.patch("activities.viaggio_delfino.delfino_app.get_theme", return_value=SimpleNamespace(background=(0, 0, 0))),
            mock.patch("activities.viaggio_delfino.delfino_app.activity_stop_requested", side_effect=[False, True]),
            mock.patch("activities.viaggio_delfino.delfino_app.mark_activity_ready"),
            mock.patch("activities.viaggio_delfino.delfino_app.pygame.display.flip"),
            mock.patch("activities.viaggio_delfino.delfino_app.pygame.quit"),
        ):
            self.assertEqual(app.run(), 0)
        new_canvas.present.assert_called_once()
        old_canvas.present.assert_not_called()
        self.assertEqual(drawn_on, [new_canvas])


if __name__ == "__main__":
    unittest.main()
