"""Thin Greia composition root for La Corsa delle Bacche.

This module is the Activity's bootstrap entrypoint under Greia platform authority.
The domain simulation, rendering, audio, and lifecycle management live in dedicated
sibling modules.
"""

from __future__ import annotations

import sys
import pygame

from greia_platform.activity_api import get_profile_locale

if __package__:
    from .corsa_app import build_app
else:
    from corsa_app import build_app


def main() -> int:
    """Initialize Pygame and launch the CorsaApp."""
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((1024, 600), pygame.RESIZABLE)

    locale = get_profile_locale() or "it"
    app = build_app(screen, locale=locale)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
