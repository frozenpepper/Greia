"""Prepared visual resources and storybook art for Luci di Momo."""

from __future__ import annotations

import math
import pygame

from greia_platform.activity_api import get_shared_visual_path


class FireflyArt:
    """Own finite, pre-scaled Activity art and an enchanting night garden backdrop."""

    def __init__(self, width: int, height: int) -> None:
        self.background = self._build_background(width, height)
        self.momo = self._load_momo()
        self._glow_surf = self._build_glow_surface()

    @staticmethod
    def _load_momo() -> pygame.Surface | None:
        try:
            path = get_shared_visual_path("character.momo", variant="happy")
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(image, (180, 180))
        except (OSError, ValueError, pygame.error, RuntimeError):
            return None

    @staticmethod
    def _build_glow_surface() -> pygame.Surface:
        """Pre-render a multi-layered soft radial glow for fireflies."""
        size = 64
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        for r in range(center, 0, -1):
            alpha = int(140 * (1.0 - (r / center) ** 1.5))
            pygame.draw.circle(surf, (253, 224, 71, alpha), (center, center), r)
        pygame.draw.circle(surf, (255, 255, 255, 220), (center, center), 6)
        return surf

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))
        
        # Deep twilight gradient
        for y in range(height):
            t = y / height
            r = int(15 * (1 - t) + 6 * t)
            g = int(23 * (1 - t) + 40 * t)
            b = int(42 * (1 - t) + 45 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Distant enchanted mountains
        mountain_points = [
            (0, 320), (160, 220), (320, 290), (480, 210),
            (650, 280), (820, 190), (1024, 270), (1024, 600), (0, 600)
        ]
        pygame.draw.polygon(surface, (20, 35, 55), mountain_points)

        # Distant rolling hills
        pygame.draw.ellipse(surface, (13, 50, 40), (-100, 300, 700, 450))
        pygame.draw.ellipse(surface, (18, 65, 50), (400, 310, 750, 450))

        # Foreground lush meadow hill
        pygame.draw.ellipse(surface, (22, 85, 60), (-50, 380, width + 100, 400))
        pygame.draw.ellipse(surface, (26, 105, 75), (100, 420, width - 100, 360))

        # Glowing crescent moon with soft aura
        moon_center = (880, 95)
        # Soft outer aura
        for r in range(48, 28, -2):
            alpha = int(45 * (1.0 - (r - 28) / 20.0))
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (254, 240, 138, alpha), (r, r), r)
            surface.blit(aura, (moon_center[0] - r, moon_center[1] - r))
        # Moon crescent
        pygame.draw.circle(surface, (254, 240, 138), moon_center, 28)
        pygame.draw.circle(surface, (15, 23, 42), (moon_center[0] - 10, moon_center[1] - 8), 24)

        # Twinkling stars
        star_coords = [
            (75, 60, 2), (140, 95, 3), (220, 50, 2), (310, 110, 3),
            (420, 45, 2), (540, 85, 3), (670, 55, 2), (760, 120, 3),
            (960, 60, 2), (830, 40, 2), (180, 140, 2), (610, 130, 2),
        ]
        for sx, sy, sr in star_coords:
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), sr)
            pygame.draw.circle(surface, (254, 240, 138, 120), (sx, sy), sr + 2)

        # Delicate meadow grass blades & cute flowers
        for x in range(20, width, 24):
            gh = 16 + (x * 7) % 20
            # Grass blades
            pygame.draw.line(surface, (34, 125, 90), (x, height), (x - 4, height - gh), 2)
            pygame.draw.line(surface, (40, 145, 105), (x + 6, height), (x + 8, height - gh + 4), 2)
            # Occasional glowing little night blossom
            if x % 72 == 0:
                bx, by = x + 2, height - gh - 2
                pygame.draw.circle(surface, (251, 191, 36), (bx, by), 3)

        return surface

    def draw_lantern(self, target: pygame.Surface, x: int, y: int, *, awake: bool) -> None:
        """Draw an ornate, cozy brass lantern on a wooden post with warm glowing glass."""
        # Wooden post & bracket
        pygame.draw.rect(target, (45, 30, 20), (x - 8, y + 60, 16, 200), border_radius=4)
        pygame.draw.rect(target, (60, 42, 28), (x - 25, y - 50, 12, 120), border_radius=4)
        pygame.draw.line(target, (90, 65, 45), (x - 20, y - 45), (x, y - 45), 6)
        pygame.draw.line(target, (30, 30, 30), (x, y - 45), (x, y - 25), 4)

        # Lantern drop shadow
        shadow = pygame.Surface((90, 120), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 80), (0, 0, 90, 120), border_radius=16)
        target.blit(shadow, (x - 45, y - 20))

        # Lantern Glass Body
        body_rect = pygame.Rect(x - 38, y - 20, 76, 95)
        if awake:
            # Warm glowing ambient halo around lantern
            halo = pygame.Surface((180, 180), pygame.SRCALPHA)
            for r in range(90, 0, -4):
                alpha = int(90 * (1.0 - r / 90.0))
                pygame.draw.circle(halo, (253, 224, 71, alpha), (90, 90), r)
            target.blit(halo, (x - 90, y + 25 - 90))

            pygame.draw.rect(target, (254, 240, 138), body_rect, border_radius=14)
            # Inner candle flame
            pygame.draw.ellipse(target, (245, 158, 11), (x - 10, y + 20, 20, 32))
            pygame.draw.ellipse(target, (255, 255, 255), (x - 5, y + 28, 10, 18))
        else:
            pygame.draw.rect(target, (55, 65, 81), body_rect, border_radius=14)
            # Candle out
            pygame.draw.ellipse(target, (75, 85, 99), (x - 6, y + 30, 12, 20))

        # Lantern Brass Roof & Base
        pygame.draw.polygon(target, (180, 83, 9), [(x - 48, y - 20), (x + 48, y - 20), (x, y - 48)])
        pygame.draw.polygon(target, (217, 119, 6), [(x - 44, y - 20), (x + 44, y - 20), (x, y - 44)])
        pygame.draw.circle(target, (245, 158, 11), (x, y - 48), 8)
        pygame.draw.circle(target, (120, 53, 15), (x, y - 48), 8, 2)
        pygame.draw.rect(target, (180, 83, 9), (x - 44, y + 70, 88, 16), border_radius=6)
        pygame.draw.rect(target, (217, 119, 6), (x - 42, y + 72, 84, 12), border_radius=4)

        # Lantern Grid Lines
        pygame.draw.rect(target, (120, 53, 15), body_rect, width=4, border_radius=14)
        pygame.draw.line(target, (120, 53, 15), (x, y - 20), (x, y + 75), 3)

    def draw_firefly(self, target: pygame.Surface, x: int, y: int, radius: int) -> None:
        """Draw an enchanting glowing firefly with radial aura and delicate wings."""
        # Translucent radial glow
        glow_size = radius * 4
        scaled_glow = pygame.transform.smoothscale(self._glow_surf, (glow_size, glow_size))
        target.blit(scaled_glow, (x - glow_size // 2, y - glow_size // 2))

        # Cute translucent wings
        wing_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(wing_surf, (255, 255, 255, 180), (0, 0, radius, int(radius * 1.8)))
        pygame.draw.ellipse(wing_surf, (255, 255, 255, 180), (radius, 0, radius, int(radius * 1.8)))
        target.blit(wing_surf, (x - radius, y - int(radius * 1.4)))

        # Little golden firefly body
        pygame.draw.circle(target, (254, 240, 138), (x, y), radius)
        pygame.draw.circle(target, (255, 255, 255), (x, y), max(2, radius // 2))
