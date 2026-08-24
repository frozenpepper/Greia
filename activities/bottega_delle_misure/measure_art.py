"""Prepared visual resources for La Bottega delle Misure."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_api import get_shared_visual_path


UNIT_PX: Final[int] = 56
UNIT_H_PX: Final[int] = 44

PARCEL_PALETTES: Final[tuple[tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], ...]] = (
    ((254, 240, 138), (202, 138, 4), (244, 63, 94)),   # Gold with Red ribbon
    ((254, 205, 211), (225, 29, 72), (59, 130, 246)),   # Rose with Blue ribbon
    ((187, 247, 208), (22, 163, 74), (234, 88, 12)),   # Mint with Orange ribbon
    ((191, 219, 254), (37, 99, 235), (234, 179, 8)),   # Sky with Gold ribbon
    ((233, 213, 255), (147, 51, 234), (16, 185, 129)), # Lavender with Emerald ribbon
)


class MeasureArt:
    """Own finite pre-scaled Activity art and workshop presentation."""

    def __init__(self, width: int, height: int) -> None:
        self.background = self._build_background(width, height)
        self.dani = self._load_dani()

    @staticmethod
    def _load_dani() -> pygame.Surface | None:
        try:
            path = get_shared_visual_path("character.dani", variant="happy")
            image = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
            return pygame.transform.scale(image, (170, 170))
        except (OSError, ValueError, pygame.error, RuntimeError):
            return None

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))
        surface.fill((40, 32, 28))

        # Workshop wall
        pygame.draw.rect(surface, (54, 44, 38), (0, 0, width, 340))
        # Shelves on the back wall
        pygame.draw.rect(surface, (78, 54, 40), (80, 64, 864, 16), border_radius=4)
        pygame.draw.rect(surface, (120, 84, 54), (80, 64, 864, 4), border_radius=2)
        # Decorative jars / boxes on shelf
        for jx, jw, jh, col in [
            (120, 28, 38, (59, 130, 246)),
            (160, 36, 46, (234, 179, 8)),
            (210, 24, 32, (16, 185, 129)),
            (780, 42, 48, (244, 63, 94)),
            (836, 32, 36, (168, 85, 247)),
        ]:
            pygame.draw.rect(surface, col, (jx, 64 - jh, jw, jh), border_radius=4)

        # Workshop counter table (large sturdy oak bench)
        pygame.draw.rect(surface, (120, 75, 42), (0, 340, width, height - 340))
        pygame.draw.rect(surface, (156, 102, 58), (0, 340, width, 18))
        pygame.draw.line(surface, (78, 48, 26), (0, 358), (width, 358), 3)

        return surface
