"""Prepared visual resources and warm storybook art for La Casa del Dieci."""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_shared_visual_path


class TenHouseArt:
    """Own finite pre-scaled Activity art and the cozy 10-room townhouse."""

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

        # Deep twilight gradient
        for y in range(height):
            t = y / height
            r = int(18 * (1 - t) + 12 * t)
            g = int(28 * (1 - t) + 45 * t)
            b = int(58 * (1 - t) + 52 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Distant rolling hills
        pygame.draw.ellipse(surface, (15, 45, 38), (-100, 360, 600, 350))
        pygame.draw.ellipse(surface, (20, 60, 48), (550, 370, 600, 350))

        # Lush lawn
        pygame.draw.rect(surface, (28, 95, 70), (0, 440, width, height - 440))
        pygame.draw.rect(surface, (34, 115, 85), (0, 470, width, height - 470))

        # Stone garden pathway
        for px, py in [(180, 520), (140, 545), (100, 570), (220, 550)]:
            pygame.draw.ellipse(surface, (71, 85, 105), (px, py, 38, 20))
            pygame.draw.ellipse(surface, (100, 116, 139), (px + 2, py + 2, 34, 16))

        # Stars & Crescent Moon
        moon_center = (890, 85)
        # Moon aura
        for r in range(45, 25, -3):
            alpha = int(40 * (1.0 - (r - 25) / 20.0))
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (254, 240, 138, alpha), (r, r), r)
            surface.blit(aura, (moon_center[0] - r, moon_center[1] - r))
        # Moon
        pygame.draw.circle(surface, (254, 240, 138), moon_center, 26)
        pygame.draw.circle(surface, (20, 32, 60), (moon_center[0] - 10, moon_center[1] - 8), 22)

        for sx, sy, sr in [
            (95, 60, 2), (180, 45, 3), (290, 80, 2), (410, 40, 3),
            (680, 55, 3), (760, 110, 2), (970, 50, 2), (830, 40, 3),
        ]:
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), sr)
            pygame.draw.circle(surface, (254, 240, 138, 120), (sx, sy), sr + 2)

        # House drop shadow
        house_rect = pygame.Rect(205, 95, 614, 315)
        pygame.draw.rect(surface, (10, 20, 30), house_rect.move(0, 8), border_radius=18)

        # Chimney with smoke
        pygame.draw.rect(surface, (153, 27, 27), (725, 42, 38, 62), border_radius=6)
        pygame.draw.rect(surface, (185, 28, 28), (723, 38, 42, 10), border_radius=4)
        # Brick lines
        pygame.draw.line(surface, (120, 20, 20), (725, 58), (763, 58), 2)
        pygame.draw.line(surface, (120, 20, 20), (725, 78), (763, 78), 2)
        # Smoke puffs
        for sx, sy, sr in [(744, 26, 7), (752, 14, 9), (764, 4, 11)]:
            smoke = pygame.Surface((sr * 2, sr * 2), pygame.SRCALPHA)
            pygame.draw.circle(smoke, (226, 232, 240, 180), (sr, sr), sr)
            surface.blit(smoke, (sx - sr, sy - sr))

        # Roof
        pygame.draw.polygon(
            surface,
            (180, 20, 40),
            [(512, 14), (160, 102), (864, 102)],
        )
        pygame.draw.polygon(
            surface,
            (225, 29, 72),
            [(512, 22), (175, 98), (849, 98)],
        )
        # Roof scalloped tiles highlight
        pygame.draw.polygon(
            surface,
            (251, 113, 133),
            [(512, 30), (195, 94), (829, 94)],
        )

        # House timbered facade
        pygame.draw.rect(surface, (255, 251, 235), house_rect, border_radius=18)
        pygame.draw.rect(surface, (180, 83, 9), house_rect, width=6, border_radius=18)

        # Wooden timber beam dividing 1st & 2nd floor
        pygame.draw.rect(surface, (180, 83, 9), (205, 246, 614, 10))
        pygame.draw.rect(surface, (217, 119, 6), (207, 248, 610, 6))

        return surface
