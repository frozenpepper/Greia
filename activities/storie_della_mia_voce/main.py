"""Thin Greia composition root for Storie della Mia Voce.

Real work lives in the sibling modules (recorder, renderer,
storage, services, app). This file is a thin bootstrap that wires
the platform APIs and hands control to ``VoiceApp.run()``.
"""

from __future__ import annotations

import pygame

from voice_app import build_app


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode(
            (1024, 600), pygame.RESIZABLE
        )
    pygame.mouse.set_visible(True)
    app = build_app(screen)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
