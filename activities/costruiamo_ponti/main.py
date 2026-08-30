from __future__ import annotations

"""Thin bootstrap for Costruiamo Ponti.

Keeps the Greia composition root explicit and preserves the historical
``activities.costruiamo_ponti.main`` public surface. Domain, presentation
and lifecycle details live in sibling modules.
"""

from pathlib import Path

import pygame

if __package__:
    from .ponti_app import BridgeAudio, PontiApp
    from .ponti_content import (
        BLOCK_TYPES,
        BLOCKS,
        LEVELS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
else:
    from ponti_app import BridgeAudio, PontiApp
    from ponti_content import (
        BLOCK_TYPES,
        BLOCKS,
        LEVELS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )

# Historical symbols expected by repository tests/tools remain reachable
# from the canonical entrypoint even after decomposition.
__all__ = [
    "BLOCKS",
    "BLOCK_TYPES",
    "LEVELS",
    "BridgeAudio",
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "STORAGE_KEY",
    "main",
]


def main() -> int:
    """Compose Greia platform owners and run the traveler bridge activity."""

    pygame.init()
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        pygame.mouse.set_visible(False)
        app = PontiApp(screen=screen)
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
