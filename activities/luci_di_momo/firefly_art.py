"""Prepared visual resources for Luci di Momo."""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_shared_visual_path


class FireflyArt:
    """Own finite, pre-scaled Activity art and a baked opaque garden backdrop."""

    def __init__(self, width: int, height: int) -> None:
        self.background = self._build_background(width, height)
        self.momo = self._load_momo()

    @staticmethod
    def _load_momo() -> pygame.Surface | None:
        try:
            path = get_shared_visual_path("character.momo", variant="happy")
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(image, (180, 180))
        except (OSError, ValueError, pygame.error, RuntimeError):
            return None

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))
        surface.fill((31, 47, 79))
        pygame.draw.rect(surface, (43, 65, 98), (0, 0, width, 190))
        pygame.draw.rect(surface, (38, 77, 75), (0, 190, width, 210))
        pygame.draw.rect(surface, (31, 92, 67), (0, 400, width, height - 400))
        for x, y, radius in (
            (890, 84, 28), (75, 118, 4), (135, 72, 3), (225, 120, 4),
            (780, 135, 3), (835, 52, 3), (680, 88, 4),
        ):
            pygame.draw.circle(surface, (255, 244, 180), (x, y), radius)
        for x in range(0, width, 32):
            pygame.draw.polygon(
                surface,
                (24, 74, 58),
                ((x, height), (x + 10, 430), (x + 18, height), (x + 27, 446), (x + 32, height)),
            )
        return surface
