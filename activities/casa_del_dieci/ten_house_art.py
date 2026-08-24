"""Prepared visual resources for La Casa del Dieci."""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_shared_visual_path


class TenHouseArt:
    """Own finite pre-scaled Activity art and the baked 10-frame house backdrop."""

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
        surface.fill((24, 36, 64))

        # Sky gradient bands
        pygame.draw.rect(surface, (30, 48, 80), (0, 0, width, 180))
        pygame.draw.rect(surface, (36, 62, 94), (0, 180, width, 160))
        # Ground
        pygame.draw.rect(surface, (30, 78, 62), (0, 420, width, height - 420))
        pygame.draw.rect(surface, (22, 60, 48), (0, 490, width, height - 490))

        # Stars & Moon
        for x, y, r in [
            (880, 70, 24), (110, 80, 3), (210, 50, 4), (320, 110, 3),
            (680, 60, 4), (760, 120, 3), (940, 130, 3),
        ]:
            pygame.draw.circle(surface, (254, 240, 138), (x, y), r)

        # House structure silhouette & outline
        house_rect = pygame.Rect(210, 90, 604, 310)
        # Chimney
        pygame.draw.rect(surface, (153, 27, 27), (720, 44, 34, 56), border_radius=4)
        pygame.draw.circle(surface, (226, 232, 240), (737, 30), 6)
        pygame.draw.circle(surface, (226, 232, 240), (745, 18), 8)

        # Roof
        pygame.draw.polygon(
            surface,
            (225, 29, 72),
            [(512, 18), (170, 102), (854, 102)],
        )
        pygame.draw.polygon(
            surface,
            (251, 113, 133),
            [(512, 30), (195, 100), (829, 100)],
        )

        # House facade
        pygame.draw.rect(surface, (254, 243, 199), house_rect, border_radius=16)
        pygame.draw.rect(surface, (180, 83, 9), house_rect, width=6, border_radius=16)

        # Divider beam between 1st and 2nd floor
        pygame.draw.rect(surface, (217, 119, 6), (216, 242, 592, 8), border_radius=3)

        return surface
