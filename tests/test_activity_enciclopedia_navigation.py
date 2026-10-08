"""Safety and source-level interaction coverage for Encyclopedia internal Back."""

from __future__ import annotations

import os
import unittest
from unittest.mock import Mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from activities.enciclopedia_greia.enciclopedia_app import EncyclopediaApp, INTERNAL_BACK_RECT


class EncyclopediaBackSafetyTests(unittest.TestCase):
    def test_internal_back_lives_outside_platform_chrome(self) -> None:
        pygame.init()
        screen = pygame.Surface((1024, 600))
        app = object.__new__(EncyclopediaApp)
        app.screen = screen
        app.canvas = PygameReferenceCanvas(screen)
        app.navigator = Mock(can_go_back=True)
        chrome = activity_viewport_for_surface(screen).protected_regions[0]
        protected = (int(chrome.x) + 25, int(chrome.y) + 25)
        self.assertFalse(app._point_in_back_hitbox(protected))
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
            "button": 1,
            "pos": protected,
        }))
        app.navigator.back.assert_not_called()
        app.navigator.handle_input.assert_not_called()
        back = INTERNAL_BACK_RECT.center
        self.assertTrue(app._point_in_back_hitbox(back))
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
            "button": 1,
            "pos": back,
        }))
        app.navigator.back.assert_called_once()


if __name__ == "__main__":
    unittest.main()
