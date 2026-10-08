"""Source-phase regressions for real Memory Meraviglie quit and localization contracts."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from activities.memory_meraviglie.memory_app import MemoryApp


class MemoryLifecycleTests(unittest.TestCase):
    def test_quit_event_stops_main_loop_owner(self) -> None:
        app = object.__new__(MemoryApp)
        app._running = True
        app.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(app._running)

    def test_escape_event_stops_main_loop_owner(self) -> None:
        app = object.__new__(MemoryApp)
        app._running = True
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
        self.assertFalse(app._running)


if __name__ == "__main__":
    unittest.main()
