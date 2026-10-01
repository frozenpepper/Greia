"""Thin Greia composition root for Colline Allegre (Bumpy Hills).

This file is the Activity's composition/bootstrap boundary. The
real work lives in the sibling modules (colline_model, colline_renderer,
colline_audio, colline_content, colline_app). Keeping `main.py` thin makes
per-module responsibilities obvious and respects the engineering rule that
the entrypoint should not own gameplay, rendering, audio, or storage.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure local package imports work cleanly in direct script execution
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pygame

if __package__:
    from .colline_app import build_app
else:
    from colline_app import build_app


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((1024, 600), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)
    app = build_app(screen, locale="it")
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
