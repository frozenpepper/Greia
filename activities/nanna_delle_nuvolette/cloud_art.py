"""Prepared visual resources and storybook bedtime art for Nanna delle Nuvolette."""

from __future__ import annotations

import math
from typing import Final

import pygame

from greia_platform.activity_api import get_shared_visual_path

if __package__:
    from .cloud_content import BLANKETS, Blanket
    from .cloud_model import CloudFriend
else:
    from cloud_content import BLANKETS, Blanket
    from cloud_model import CloudFriend


class CloudArt:
    """Own background scenery, Momo mascot, clouds, blankets, and star tokens."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.background = self._build_background(width, height)
        self.momo = self._load_momo()
        self._blanket_textures: dict[str, pygame.Surface] = {}

    @staticmethod
    def _load_momo() -> pygame.Surface | None:
        try:
            path = get_shared_visual_path("character.momo", variant="sleepy")
            image = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
            return pygame.transform.scale(image, (150, 150))
        except (OSError, ValueError, pygame.error, RuntimeError):
            try:
                path = get_shared_visual_path("character.momo", variant="happy")
                image = pygame.image.load(path)
                if pygame.display.get_surface() is not None:
                    image = image.convert_alpha()
                return pygame.transform.scale(image, (150, 150))
            except (OSError, ValueError, pygame.error, RuntimeError):
                return None

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))

        # Deep velvet night indigo-violet gradient
        for y in range(height):
            t = y / height
            r = int(18 * (1 - t) + 10 * t)
            g = int(24 * (1 - t) + 14 * t)
            b = int(58 * (1 - t) + 38 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Distant dreamy cloud banks at the bottom
        pygame.draw.ellipse(surface, (28, 38, 75), (-80, 420, 480, 260))
        pygame.draw.ellipse(surface, (24, 32, 65), (280, 440, 520, 260))
        pygame.draw.ellipse(surface, (28, 38, 75), (680, 410, 460, 260))

        # Large Golden Bedtime Moon on top right
        moon_center = (900, 90)
        # Outer soft glow aura
        for r in range(48, 28, -4):
            alpha = int(40 * (1.0 - r / 48.0))
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (254, 240, 138, alpha), (r, r), r)
            surface.blit(aura, (moon_center[0] - r, moon_center[1] - r))

        pygame.draw.circle(surface, (254, 240, 138), moon_center, 30)
        pygame.draw.circle(surface, (18, 24, 58), (moon_center[0] - 10, moon_center[1] - 8), 26)

        # Fixed dreamy starlight coordinates
        star_coords = [
            (80, 60), (160, 110), (280, 50), (420, 85), (560, 45), (720, 95),
            (110, 220), (220, 180), (840, 230), (960, 190), (512, 120),
        ]
        for sx, sy in star_coords:
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 2)
            pygame.draw.circle(surface, (254, 240, 138, 100), (sx, sy), 4)

        return surface

    def draw_cloud(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        cloud: CloudFriend,
        *,
        is_hovered: bool = False,
        is_selected: bool = False,
        yawn_progress: float = 0.0,
    ) -> None:
        """Render a fluffy pillowy cloud friend with expressive face and rosy cheeks."""
        cx, cy = rect.centerx, rect.centery
        w, h = rect.width, rect.height

        # Drop shadow
        pygame.draw.ellipse(target, (10, 14, 28, 80), (rect.left + 8, rect.bottom - 16, w - 16, 28))

        # Cloud fluffy body (layered white/sky-tinted ovals)
        cloud_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Fluffy cloud lobes
        pygame.draw.ellipse(cloud_surf, (241, 245, 249), (w * 0.15, h * 0.25, w * 0.7, h * 0.65))
        pygame.draw.circle(cloud_surf, (255, 255, 255), (int(w * 0.32), int(h * 0.45)), int(h * 0.32))
        pygame.draw.circle(cloud_surf, (255, 255, 255), (int(w * 0.52), int(h * 0.35)), int(h * 0.36))
        pygame.draw.circle(cloud_surf, (255, 255, 255), (int(w * 0.70), int(h * 0.48)), int(h * 0.28))

        # Outline
        if is_selected:
            pygame.draw.ellipse(cloud_surf, (56, 189, 248), (w * 0.10, h * 0.15, w * 0.8, h * 0.75), width=4)
        elif is_hovered:
            pygame.draw.ellipse(cloud_surf, (147, 197, 253), (w * 0.10, h * 0.15, w * 0.8, h * 0.75), width=3)

        # Rosy blush cheeks
        pygame.draw.circle(cloud_surf, (254, 205, 211), (int(w * 0.32), int(h * 0.58)), 10)
        pygame.draw.circle(cloud_surf, (254, 205, 211), (int(w * 0.68), int(h * 0.58)), 10)

        # Face expressions
        if cloud.asleep:
            # Sleeping curved eyes (︶ ︶)
            pygame.draw.arc(cloud_surf, (71, 85, 105), (int(w * 0.34), int(h * 0.44), 22, 16), 3.4, 6.0, 3)
            pygame.draw.arc(cloud_surf, (71, 85, 105), (int(w * 0.54), int(h * 0.44), 22, 16), 3.4, 6.0, 3)
            # Peaceful curved smile
            pygame.draw.arc(cloud_surf, (71, 85, 105), (int(w * 0.44), int(h * 0.56), 20, 14), 3.4, 6.0, 3)
        elif yawn_progress > 0.0:
            # Yawning open mouth (O)
            pygame.draw.circle(cloud_surf, (71, 85, 105), (int(w * 0.38), int(h * 0.48)), 5)
            pygame.draw.circle(cloud_surf, (71, 85, 105), (int(w * 0.62), int(h * 0.48)), 5)
            m_size = int(8 + 8 * math.sin(math.pi * yawn_progress))
            pygame.draw.circle(cloud_surf, (225, 29, 72), (int(w * 0.50), int(h * 0.60)), m_size)
        else:
            # Awake happy eyes
            pygame.draw.circle(cloud_surf, (30, 41, 59), (int(w * 0.38), int(h * 0.48)), 6)
            pygame.draw.circle(cloud_surf, (255, 255, 255), (int(w * 0.36), int(h * 0.46)), 2)
            pygame.draw.circle(cloud_surf, (30, 41, 59), (int(w * 0.62), int(h * 0.48)), 6)
            pygame.draw.circle(cloud_surf, (255, 255, 255), (int(w * 0.60), int(h * 0.46)), 2)
            # Sweet smile
            pygame.draw.arc(cloud_surf, (30, 41, 59), (int(w * 0.44), int(h * 0.54), 20, 14), 3.4, 6.0, 3)

        target.blit(cloud_surf, rect.topleft)

        # Draw Blanket if tucked in
        if cloud.blanket_id is not None:
            self._draw_cloud_blanket(target, rect, cloud.blanket_id)

        # Draw Stars attached to this cloud (1 to 3 stars)
        for s_idx, star_id in enumerate(cloud.star_ids):
            sx = rect.left + 40 + s_idx * 48
            sy = rect.top + 20 + (s_idx % 2) * 12
            self.draw_star(target, (sx, sy), size=18)

        # Sleepy Zzz bubbles if asleep
        if cloud.asleep:
            for z_i, (zx_off, zy_off, z_r) in enumerate([(30, -10, 8), (48, -26, 12), (70, -46, 16)]):
                z_pos = (rect.right - zx_off, rect.top + zy_off)
                pygame.draw.circle(target, (216, 180, 254), z_pos, z_r, width=2)
                pygame.draw.circle(target, (255, 255, 255, 180), z_pos, z_r - 2)

    def _draw_cloud_blanket(self, target: pygame.Surface, rect: pygame.Rect, blanket_id: str) -> None:
        b_rect = pygame.Rect(rect.left + 16, rect.centery + 10, rect.width - 32, rect.height // 2 - 14)
        blanket = next((b for b in BLANKETS if b.blanket_id == blanket_id), BLANKETS[0])

        # Blanket quilted curve
        pygame.draw.rect(target, blanket.primary_color, b_rect, border_radius=16)
        pygame.draw.rect(target, blanket.accent_color, b_rect, width=3, border_radius=16)
        # Folded quilt top border
        pygame.draw.rect(target, (255, 255, 255), (b_rect.left + 2, b_rect.top + 2, b_rect.width - 4, 8), border_radius=4)

    def draw_blanket_card(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        blanket: Blanket,
        *,
        is_selected: bool = False,
        is_hovered: bool = False,
    ) -> None:
        """Render a cozy blanket patch card on the tray."""
        draw_rect = rect.move(0, -6) if (is_hovered or is_selected) else rect

        # Drop shadow
        pygame.draw.rect(target, (10, 14, 28, 80), rect.move(0, 6), border_radius=16)

        # Blanket patch
        pygame.draw.rect(target, blanket.primary_color, draw_rect, border_radius=16)

        # Border
        if is_selected:
            pygame.draw.rect(target, (56, 189, 248), draw_rect, width=4, border_radius=16)
            pygame.draw.rect(target, (255, 255, 255), draw_rect.inflate(-6, -6), width=2, border_radius=12)
        elif is_hovered:
            pygame.draw.rect(target, (147, 197, 253), draw_rect, width=3, border_radius=16)
        else:
            pygame.draw.rect(target, blanket.accent_color, draw_rect, width=3, border_radius=16)

        # Decorative stitches on blanket card
        pygame.draw.rect(target, (255, 255, 255, 160), draw_rect.inflate(-8, -8), width=1, border_radius=10)

    @staticmethod
    def draw_star(target: pygame.Surface, center: tuple[int, int], size: int = 20) -> None:
        """Render a golden glowing five-pointed bedtime star."""
        cx, cy = center
        r_outer = size
        r_inner = size * 0.45
        pts: list[tuple[float, float]] = []
        for i in range(10):
            r = r_outer if (i % 2 == 0) else r_inner
            angle = i * (math.pi / 5.0) - math.pi / 2.0
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

        # Outer soft golden glow
        pygame.draw.circle(target, (254, 240, 138, 80), (cx, cy), size + 4)
        # Star polygon
        pygame.draw.polygon(target, (254, 240, 138), pts)
        pygame.draw.polygon(target, (217, 119, 6), pts, width=2)
        # Center sparkle
        pygame.draw.circle(target, (255, 255, 255), (cx, cy), max(2, size // 5))

    def draw_star_basket(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        available_stars: int,
        *,
        is_hovered: bool = False,
        is_selected: bool = False,
    ) -> None:
        """Render a wicker star basket holding glowing stars."""
        draw_rect = rect.move(0, -4) if (is_hovered or is_selected) else rect

        # Drop shadow
        pygame.draw.rect(target, (10, 14, 28, 80), rect.move(0, 6), border_radius=18)

        # Wicker basket base
        pygame.draw.rect(target, (180, 83, 9), draw_rect, border_radius=18)
        border_c = (56, 189, 248) if (is_hovered or is_selected) else (245, 158, 11)
        pygame.draw.rect(target, border_c, draw_rect, width=3, border_radius=18)

        # Wicker basket weave lines
        for wx in range(draw_rect.left + 12, draw_rect.right - 8, 16):
            pygame.draw.line(target, (120, 53, 15), (wx, draw_rect.top + 6), (wx, draw_rect.bottom - 6), 2)

        # Stars peeking out of basket
        star_count = min(3, max(1, available_stars))
        for i in range(star_count):
            sx = draw_rect.left + 24 + i * 24
            sy = draw_rect.top + 16
            self.draw_star(target, (sx, sy), size=14)
