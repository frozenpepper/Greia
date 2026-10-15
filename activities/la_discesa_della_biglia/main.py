"""Thin Greia composition root for La Discesa della Biglia.

This file is the Activity's composition/bootstrap boundary. The
real work lives in the sibling modules (engine, renderer, audio,
services, app). Keeping `main.py` thin makes the per-module
responsibilities obvious and matches the engineering rule that
the entrypoint should not own gameplay, rendering, audio, or
storage.

The Activity runs under Greia platform authority: it does not
bypass the platform lifecycle (READY/STOP), it does not pick
hardware (no microphone, no controller), and it does not write
global reward state.
"""

from __future__ import annotations

import pygame

if __package__:
    from .ramp_app import build_app
else:
    from ramp_app import build_app


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
