"""Pre-rendered visual assets, parallax backdrops, and hardware-friendly colorkey caches for Il Volo del Draghetto."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.ui_core import BoundedCache

try:
    from dragon_model import (
        ACCESSORIES,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
except ImportError:
    from .dragon_model import (
        ACCESSORIES,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )

COLORKEY: Final = (1, 2, 3)
SKY_TOP: Final = (115, 185, 255)
SKY_BOTTOM: Final = (248, 225, 240)
DARK_TEXT: Final = (48, 38, 58)
WHITE: Final = (255, 255, 255)
GOLD: Final = (255, 215, 0)
GOLD_DARK: Final = (245, 158, 11)
PINK: Final = (255, 130, 165)


def _mix(c1: tuple[int, int, int], c2: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    f = max(0.0, min(1.0, factor))
    return (
        int(round(c1[0] * (1.0 - f) + c2[0] * f)),
        int(round(c1[1] * (1.0 - f) + c2[1] * f)),
        int(round(c1[2] * (1.0 - f) + c2[2] * f)),
    )


def _make_colorkey_surface(width: int, height: int) -> pygame.Surface:
    """Create a hardware-friendly display-converted colorkey surface."""
    surf = pygame.Surface((width, height))
    if pygame.display.get_init() and pygame.display.get_surface():
        try:
            surf = surf.convert()
        except Exception:
            pass
    surf.fill(COLORKEY)
    surf.set_colorkey(COLORKEY)
    return surf


class DragonArtLibrary:
    """Owns pre-rendered gameplay scenery, dragon animation frames, and sprite caches."""

    def __init__(self, root_path: Path | None = None) -> None:
        self._root = root_path
        self._bg_surface: pygame.Surface | None = None
        self._distant_clouds: tuple[pygame.Surface, pygame.Surface, pygame.Surface] | None = None

        # Pre-rendered gameplay sprites
        self._star_sprite: pygame.Surface | None = None
        self._rainbow_gate_sprite: pygame.Surface | None = None
        self._cloud_obstacle_sprite: pygame.Surface | None = None

        # Pre-rendered dragon body and wing frames: (flap_frame_idx, accessory, is_dashing) -> Surface
        self._dragon_frames: dict[tuple[int, str, bool], pygame.Surface] = {}

        # Pre-rendered particles by kind and size bucket
        self._particle_cache: dict[tuple[str, int, tuple[int, int, int]], pygame.Surface] = {}

    def get_sky_background(self) -> pygame.Surface:
        """Return the pre-baked 1024x600 opaque sky gradient with distant rolling hills."""
        if self._bg_surface is None:
            surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if pygame.display.get_init() and pygame.display.get_surface():
                try:
                    surf = surf.convert()
                except Exception:
                    pass
            for y in range(REFERENCE_HEIGHT):
                t = y / float(REFERENCE_HEIGHT)
                color = _mix(SKY_TOP, SKY_BOTTOM, t)
                pygame.draw.line(surf, color, (0, y), (REFERENCE_WIDTH, y))

            # Distant gentle green rolling hills horizon far below (y=490..600)
            pygame.draw.ellipse(surf, (168, 220, 160), (-100, 500, 600, 200))
            pygame.draw.ellipse(surf, (148, 205, 140), (350, 480, 800, 240))
            pygame.draw.ellipse(surf, (180, 230, 175), (100, 520, 500, 180))

            self._bg_surface = surf
        return self._bg_surface

    def get_distant_clouds(self) -> tuple[pygame.Surface, pygame.Surface, pygame.Surface]:
        """Return 3 pre-rendered fast colorkey puffy cloud sprites for parallax scrolling."""
        if self._distant_clouds is None:
            # Cloud 1: Small puffy cloud
            c1 = _make_colorkey_surface(140, 75)
            pygame.draw.ellipse(c1, (215, 230, 250), (10, 20, 120, 45))
            pygame.draw.circle(c1, WHITE, (40, 36), 24)
            pygame.draw.circle(c1, WHITE, (72, 28), 30)
            pygame.draw.circle(c1, WHITE, (104, 38), 22)

            # Cloud 2: Medium cumulus cloud
            c2 = _make_colorkey_surface(200, 95)
            pygame.draw.ellipse(c2, (215, 230, 250), (15, 25, 170, 60))
            pygame.draw.circle(c2, WHITE, (50, 48), 34)
            pygame.draw.circle(c2, WHITE, (98, 36), 42)
            pygame.draw.circle(c2, WHITE, (148, 48), 32)
            pygame.draw.ellipse(c2, WHITE, (30, 40, 140, 46))

            # Cloud 3: Wide fluffy cloud
            c3 = _make_colorkey_surface(160, 80)
            pygame.draw.ellipse(c3, (215, 230, 250), (12, 22, 136, 50))
            pygame.draw.circle(c3, WHITE, (45, 42), 26)
            pygame.draw.circle(c3, WHITE, (82, 32), 34)
            pygame.draw.circle(c3, WHITE, (120, 40), 28)

            self._distant_clouds = (c1, c2, c3)
        return self._distant_clouds

    def get_star_sprite(self) -> pygame.Surface:
        """Return a pre-rendered glowing gold star collectible sprite (44x44 colorkey)."""
        if self._star_sprite is None:
            size = 44
            surf = _make_colorkey_surface(size, size)
            cx, cy = size // 2, size // 2

            # Soft golden halo ring
            pygame.draw.circle(surf, (255, 245, 175), (cx, cy), 20)
            pygame.draw.circle(surf, (255, 230, 110), (cx, cy), 16)

            # 5-pointed gold star
            pts = []
            for i in range(10):
                angle = -math.pi / 2 + i * (math.pi / 5)
                r = 14 if i % 2 == 0 else 6
                pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

            pygame.draw.polygon(surf, GOLD, pts)
            pygame.draw.polygon(surf, GOLD_DARK, pts, width=2)
            # Center highlight
            pygame.draw.circle(surf, (255, 255, 230), (cx - 2, cy - 2), 3)

            self._star_sprite = surf
        return self._star_sprite

    def get_rainbow_gate_sprite(self) -> pygame.Surface:
        """Return a pre-rendered vibrant upright rainbow arch gate (240x180 colorkey)."""
        if self._rainbow_gate_sprite is None:
            w, h = 240, 180
            surf = _make_colorkey_surface(w, h)
            cx, cy = w // 2, h - 35

            # Rainbow bands in upright arch (0 to pi)
            for i, col in enumerate(RAINBOW_COLORS):
                r = 95 - i * 9
                rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
                pygame.draw.arc(surf, col, rect, 0, math.pi, 9)

            # Fluffy cloud footings at bases
            for bx in (cx - 85, cx + 85):
                # Cloud shadow
                pygame.draw.ellipse(surf, (215, 230, 250), (bx - 32, cy - 8, 64, 32))
                # Cloud lobes
                pygame.draw.circle(surf, WHITE, (bx - 16, cy - 4), 18)
                pygame.draw.circle(surf, WHITE, (bx, cy - 12), 22)
                pygame.draw.circle(surf, WHITE, (bx + 16, cy - 4), 18)
                pygame.draw.circle(surf, (245, 250, 255), (bx, cy + 2), 16)

            self._rainbow_gate_sprite = surf
        return self._rainbow_gate_sprite

    def get_cloud_obstacle_sprite(self) -> pygame.Surface:
        """Return a pre-rendered soft bouncy cloud obstacle (130x80 colorkey)."""
        if self._cloud_obstacle_sprite is None:
            w, h = 130, 80
            surf = _make_colorkey_surface(w, h)
            cx, cy = w // 2, h // 2

            # Soft cloud shadow base
            pygame.draw.ellipse(surf, (215, 230, 250), (cx - 55, cy - 10, 110, 46))
            # Cloud lobes
            pygame.draw.ellipse(surf, (235, 245, 255), (cx - 50, cy - 24, 60, 48))
            pygame.draw.ellipse(surf, WHITE, (cx - 24, cy - 36, 68, 56))
            pygame.draw.ellipse(surf, (245, 250, 255), (cx + 8, cy - 22, 52, 44))
            pygame.draw.ellipse(surf, WHITE, (cx - 45, cy - 15, 90, 40))

            # Cute sleeping/smiling face on the cloud
            pygame.draw.arc(surf, (140, 165, 195), (cx - 16, cy - 4, 10, 8), math.pi, 2 * math.pi, 2)
            pygame.draw.arc(surf, (140, 165, 195), (cx + 6, cy - 4, 10, 8), math.pi, 2 * math.pi, 2)
            pygame.draw.arc(surf, (255, 160, 180), (cx - 4, cy + 4, 8, 6), math.pi, 2 * math.pi, 2)
            # Rosy cheeks
            pygame.draw.circle(surf, (255, 180, 200), (cx - 22, cy + 4), 5)
            pygame.draw.circle(surf, (255, 180, 200), (cx + 22, cy + 4), 5)

            self._cloud_obstacle_sprite = surf
        return self._cloud_obstacle_sprite

    def get_dragon_sprite(self, flap_phase: float, accessory: str, is_dashing: bool) -> pygame.Surface:
        """Return a cached, pre-rendered animated baby dragon sprite (180x140 colorkey)."""
        step = int(round((flap_phase % (2.0 * math.pi)) / (math.pi / 2.0))) % 4
        key = (step, accessory, is_dashing)
        cached = self._dragon_frames.get(key)
        if cached is not None:
            return cached

        w, h = 180, 140
        surf = _make_colorkey_surface(w, h)
        cx, cy = 80, 75

        # Wing offsets based on animation step
        wing_y_offsets = [16.0, 4.0, -14.0, 2.0]
        wy = wing_y_offsets[step]

        # 1. Turbo Aura Trail (when dashing)
        if is_dashing:
            for r_i, r_col in enumerate(RAINBOW_COLORS):
                aura_rect = pygame.Rect(cx - 55 - r_i * 8, cy - 30 + r_i * 2, 100, 60 - r_i * 4)
                pygame.draw.ellipse(surf, r_col, aura_rect, width=3)

        # 2. Tail with cute spade tip
        tail_pts = [
            (cx - 30, cy + 4),
            (cx - 65, cy + int(math.sin(step * math.pi / 2) * 8)),
            (cx - 34, cy + 16),
        ]
        pygame.draw.polygon(surf, (52, 211, 153), tail_pts)
        pygame.draw.polygon(surf, (5, 150, 105), tail_pts, width=2)
        # Gold spade
        pygame.draw.circle(surf, (253, 224, 71), (int(tail_pts[1][0]), int(tail_pts[1][1])), 7)

        # 3. Back Wing
        back_wing = [
            (cx - 10, cy - 12),
            (cx - 24, cy - 48 - int(wy)),
            (cx + 14, cy - 20),
        ]
        pygame.draw.polygon(surf, (192, 132, 252), back_wing)
        pygame.draw.polygon(surf, (147, 51, 234), back_wing, width=2)

        # 4. Chubby Green Body
        body_rect = pygame.Rect(cx - 36, cy - 22, 74, 52)
        pygame.draw.ellipse(surf, (52, 211, 153), body_rect)
        pygame.draw.ellipse(surf, (5, 150, 105), body_rect, width=2)

        # Soft Yellow Tummy
        tummy_rect = pygame.Rect(cx - 14, cy - 4, 42, 30)
        pygame.draw.ellipse(surf, (254, 240, 138), tummy_rect)
        # Tummy ridges
        pygame.draw.line(surf, (202, 138, 4), (cx - 6, cy + 3), (cx + 20, cy + 3), 2)
        pygame.draw.line(surf, (202, 138, 4), (cx - 4, cy + 12), (cx + 18, cy + 12), 2)

        # 5. Front Wing
        front_wing = [
            (cx + 4, cy - 8),
            (cx - 8, cy - 44 + int(wy)),
            (cx + 28, cy - 16),
        ]
        pygame.draw.polygon(surf, (216, 180, 254), front_wing)
        pygame.draw.polygon(surf, (168, 85, 247), front_wing, width=2)

        # 6. Cute Head
        head_rect = pygame.Rect(cx + 14, cy - 32, 52, 46)
        pygame.draw.ellipse(surf, (52, 211, 153), head_rect)
        pygame.draw.ellipse(surf, (5, 150, 105), head_rect, width=2)

        # Little Horns
        pygame.draw.polygon(surf, (253, 224, 71), [(cx + 28, cy - 30), (cx + 34, cy - 44), (cx + 40, cy - 30)])
        pygame.draw.polygon(surf, (202, 138, 4), [(cx + 28, cy - 30), (cx + 34, cy - 44), (cx + 40, cy - 30)], width=2)
        pygame.draw.polygon(surf, (253, 224, 71), [(cx + 42, cy - 28), (cx + 48, cy - 40), (cx + 52, cy - 26)])
        pygame.draw.polygon(surf, (202, 138, 4), [(cx + 42, cy - 28), (cx + 48, cy - 40), (cx + 52, cy - 26)], width=2)

        # Rosy Cheek
        pygame.draw.ellipse(surf, (255, 130, 155), (cx + 34, cy - 6, 13, 9))

        # Sparkling Eye
        eye_rect = pygame.Rect(cx + 38, cy - 24, 15, 17)
        pygame.draw.ellipse(surf, (30, 27, 75), eye_rect)
        pygame.draw.circle(surf, WHITE, (cx + 42, cy - 20), 4)
        pygame.draw.circle(surf, WHITE, (cx + 47, cy - 14), 2)

        # Happy Smile
        pygame.draw.arc(surf, (5, 150, 105), pygame.Rect(cx + 46, cy - 10, 14, 11), 0.1, math.pi * 0.9, 2)

        # 7. Accessories
        if accessory == "crown":
            crown_x, crown_y = cx + 36, cy - 42
            pts_c = [
                (crown_x - 13, crown_y),
                (crown_x - 13, crown_y - 13),
                (crown_x - 6, crown_y - 6),
                (crown_x, crown_y - 16),
                (crown_x + 6, crown_y - 6),
                (crown_x + 13, crown_y - 13),
                (crown_x + 13, crown_y),
            ]
            pygame.draw.polygon(surf, GOLD, pts_c)
            pygame.draw.polygon(surf, GOLD_DARK, pts_c, width=2)
            pygame.draw.circle(surf, (239, 68, 68), (crown_x, crown_y - 8), 3)

        elif accessory == "bow":
            bx, by = cx + 24, cy - 36
            pygame.draw.polygon(surf, PINK, [(bx, by), (bx - 12, by - 8), (bx - 12, by + 8)])
            pygame.draw.polygon(surf, PINK, [(bx, by), (bx + 12, by - 8), (bx + 12, by + 8)])
            pygame.draw.polygon(surf, (225, 29, 72), [(bx, by), (bx - 12, by - 8), (bx - 12, by + 8)], width=2)
            pygame.draw.polygon(surf, (225, 29, 72), [(bx, by), (bx + 12, by - 8), (bx + 12, by + 8)], width=2)
            pygame.draw.circle(surf, (255, 70, 110), (bx, by), 5)

        elif accessory == "glasses":
            gx, gy = cx + 44, cy - 16
            pygame.draw.circle(surf, (24, 24, 27), (gx, gy), 10, 2)
            pygame.draw.line(surf, (24, 24, 27), (gx - 10, gy), (gx - 18, gy - 4), 2)
            pygame.draw.circle(surf, (186, 230, 253), (gx, gy), 8)

        elif accessory == "flower":
            fx, fy = cx + 32, cy - 38
            for a_i in range(5):
                fa = a_i * (2 * math.pi / 5)
                px = int(fx + math.cos(fa) * 8)
                py = int(fy + math.sin(fa) * 8)
                pygame.draw.circle(surf, (251, 113, 133), (px, py), 5)
            pygame.draw.circle(surf, GOLD, (fx, fy), 4)

        self._dragon_frames[key] = surf
        return surf

    def get_particle_sprite(self, kind: str, size: int, color: tuple[int, int, int]) -> pygame.Surface:
        """Return a pre-rendered particle sprite avoiding any dynamic font rendering (colorkey)."""
        bucket_size = max(8, min(32, (size // 4) * 4))
        key = (kind, bucket_size, color)
        cached = self._particle_cache.get(key)
        if cached is not None:
            return cached

        surf = _make_colorkey_surface(bucket_size, bucket_size)
        cx, cy = bucket_size // 2, bucket_size // 2
        r = bucket_size // 2

        if kind == "star" or kind == "sparkle":
            pts = []
            for i in range(8):
                angle = -math.pi / 2 + i * (math.pi / 4)
                pr = r if i % 2 == 0 else max(2, r // 3)
                pts.append((cx + pr * math.cos(angle), cy + pr * math.sin(angle)))
            pygame.draw.polygon(surf, color, pts)

        elif kind == "cloud":
            pygame.draw.circle(surf, (220, 235, 250), (cx, cy), max(2, r - 1))
            pygame.draw.circle(surf, WHITE, (cx - max(1, r // 3), cy - max(1, r // 3)), max(2, r // 2))

        else:  # rainbow or general
            pygame.draw.circle(surf, color, (cx, cy), max(2, r - 2))
            pygame.draw.circle(surf, WHITE, (cx - 2, cy - 2), max(1, r // 3))

        self._particle_cache[key] = surf
        return surf
