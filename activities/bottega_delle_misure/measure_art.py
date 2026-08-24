"""Prepared visual resources and storybook workshop art for La Bottega delle Misure."""

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
    """Own finite pre-scaled Activity art and artisan workshop presentation."""

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
        
        # Warm workshop wooden wall gradient
        for y in range(340):
            t = y / 340.0
            r = int(55 * (1 - t) + 42 * t)
            g = int(45 * (1 - t) + 32 * t)
            b = int(38 * (1 - t) + 26 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Vertical wood plank lines
        for x in range(0, width, 64):
            pygame.draw.line(surface, (32, 24, 20), (x, 0), (x, 340), 2)
            pygame.draw.line(surface, (68, 52, 42), (x + 2, 0), (x + 2, 340), 1)

        # Workshop brass tools & clock on back wall
        # Clock
        pygame.draw.circle(surface, (217, 119, 6), (920, 50), 24)
        pygame.draw.circle(surface, (255, 251, 235), (920, 50), 20)
        pygame.draw.line(surface, (120, 53, 15), (920, 50), (920, 36), 3)
        pygame.draw.line(surface, (120, 53, 15), (920, 50), (930, 50), 2)

        # Tool pegboard shelf
        pygame.draw.rect(surface, (10, 8, 6), (70, 68, 804, 22), border_radius=6)
        pygame.draw.rect(surface, (120, 75, 42), (70, 64, 804, 20), border_radius=6)
        pygame.draw.rect(surface, (180, 115, 65), (70, 64, 804, 6), border_radius=3)

        # Hanging brass tools & jars
        for jx, jw, jh, col, label in [
            (110, 32, 42, (2, 132, 199), "jar"),
            (160, 40, 50, (234, 179, 8), "box"),
            (220, 28, 36, (22, 163, 74), "can"),
            (720, 48, 52, (225, 29, 72), "jar"),
            (786, 36, 40, (147, 51, 234), "box"),
        ]:
            pygame.draw.rect(surface, (10, 8, 6), (jx - 2, 64 - jh + 2, jw + 4, jh), border_radius=6)
            pygame.draw.rect(surface, col, (jx, 64 - jh, jw, jh), border_radius=6)
            pygame.draw.rect(surface, (255, 255, 255, 120), (jx + 4, 64 - jh + 4, jw - 8, 4), border_radius=2)

        # Hanging brass balance scales silhouette
        pygame.draw.line(surface, (245, 158, 11), (512, 0), (512, 45), 4)
        pygame.draw.line(surface, (245, 158, 11), (460, 45), (564, 45), 4)

        # Warm polished oak carpenter workbench counter
        pygame.draw.rect(surface, (10, 8, 6), (0, 335, width, 12))
        pygame.draw.rect(surface, (146, 92, 52), (0, 340, width, height - 340))
        pygame.draw.rect(surface, (185, 122, 75), (0, 340, width, 18))
        pygame.draw.line(surface, (90, 52, 28), (0, 358), (width, 358), 4)

        # Engraved brass measuring ruler inlay across the bench top
        pygame.draw.rect(surface, (217, 119, 6), (120, 344, 784, 10), border_radius=3)
        for rx in range(130, 895, 14):
            tick_h = 6 if ((rx - 130) % 70 == 0) else 3
            pygame.draw.line(surface, (120, 53, 15), (rx, 344), (rx, 344 + tick_h), 2)

        return surface
