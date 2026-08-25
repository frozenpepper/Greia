"""Prepared visual resources and enchanted crystal salon art for Specchi Magici."""

from __future__ import annotations

import math
from typing import Final

import pygame

from greia_platform.activity_api import get_shared_visual_path

if __package__:
    from .mirror_model import Piece, ShapeKind
else:
    from mirror_model import Piece, ShapeKind


COLOR_PALETTES: Final[tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...]] = (
    ((244, 63, 94), (251, 113, 133)),   # Ruby
    ((251, 191, 36), (254, 240, 138)),  # Amber
    ((34, 197, 94), (134, 239, 172)),   # Emerald
    ((59, 130, 246), (147, 197, 253)),  # Sapphire
    ((168, 85, 247), (216, 180, 254)),  # Amethyst
    ((236, 72, 153), (244, 114, 182)),  # Pink Diamond
)


class MirrorArt:
    """Own finite pre-scaled Activity art and the enchanted mirror chamber."""

    def __init__(self, width: int, height: int) -> None:
        self.background = self._build_background(width, height)
        self.lilli = self._load_lilli()

    @staticmethod
    def _load_lilli() -> pygame.Surface | None:
        try:
            path = get_shared_visual_path("character.lilli", variant="happy")
            image = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
            return pygame.transform.scale(image, (110, 110))
        except (OSError, ValueError, pygame.error, RuntimeError):
            return None

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))

        # Deep velvet violet-indigo gradient
        for y in range(height):
            t = y / height
            r = int(30 * (1 - t) + 15 * t)
            g = int(18 * (1 - t) + 10 * t)
            b = int(60 * (1 - t) + 38 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Royal velvet arched curtains
        pygame.draw.polygon(surface, (76, 29, 149), [(0, 0), (140, 0), (60, 260), (0, 320)])
        pygame.draw.polygon(surface, (91, 33, 182), [(0, 0), (110, 0), (40, 240), (0, 300)])
        pygame.draw.polygon(surface, (76, 29, 149), [(width, 0), (width - 140, 0), (width - 60, 260), (width, 320)])
        pygame.draw.polygon(surface, (91, 33, 182), [(width, 0), (width - 110, 0), (width - 40, 240), (width, 300)])

        # Golden curtain tassels
        pygame.draw.circle(surface, (234, 179, 8), (55, 250), 10)
        pygame.draw.circle(surface, (234, 179, 8), (width - 55, 250), 10)

        # Starlight sparkles floating in the room
        for x, y, r in [
            (160, 80, 3), (240, 50, 4), (780, 60, 4), (860, 95, 3),
            (180, 340, 3), (840, 350, 4), (512, 35, 5), (320, 110, 2),
            (700, 115, 2), (90, 420, 3), (930, 420, 3),
        ]:
            pygame.draw.circle(surface, (255, 255, 255), (x, y), r)
            pygame.draw.circle(surface, (233, 213, 255, 120), (x, y), r + 2)

        return surface

    @staticmethod
    def draw_piece(target: pygame.Surface, cx: int, cy: int, size: int, piece: Piece) -> None:
        """Render a crisp, gem-like geometric shape piece with drop shadow and gloss."""
        palette = COLOR_PALETTES[piece.color_index % len(COLOR_PALETTES)]
        fill_col, border_col = palette
        radius = size // 2

        if piece.kind == ShapeKind.CIRCLE:
            # Shadow
            pygame.draw.circle(target, (10, 5, 20, 80), (cx, cy + 3), radius)
            pygame.draw.circle(target, fill_col, (cx, cy), radius)
            pygame.draw.circle(target, border_col, (cx, cy), radius, 3)
            # Gloss highlight
            pygame.draw.circle(target, (255, 255, 255, 160), (cx - radius // 3, cy - radius // 3), max(2, radius // 3))

        elif piece.kind == ShapeKind.SQUARE:
            rect = pygame.Rect(cx - radius + 2, cy - radius + 2, size - 4, size - 4)
            pygame.draw.rect(target, (10, 5, 20, 80), rect.move(0, 3), border_radius=8)
            pygame.draw.rect(target, fill_col, rect, border_radius=8)
            pygame.draw.rect(target, border_col, rect, width=3, border_radius=8)
            # Gloss highlight
            hl = pygame.Rect(rect.left + 4, rect.top + 4, rect.width - 8, max(4, rect.height // 3))
            pygame.draw.rect(target, (255, 255, 255, 120), hl, border_radius=4)

        elif piece.kind == ShapeKind.TRIANGLE:
            rot = piece.rotation
            if rot == 0:  # UP
                pts = [(cx, cy - radius), (cx + radius, cy + radius - 2), (cx - radius, cy + radius - 2)]
            elif rot == 1:  # RIGHT
                pts = [(cx + radius, cy), (cx - radius + 2, cy - radius), (cx - radius + 2, cy + radius)]
            elif rot == 2:  # DOWN
                pts = [(cx, cy + radius), (cx + radius, cy - radius + 2), (cx - radius, cy - radius + 2)]
            else:  # LEFT
                pts = [(cx - radius, cy), (cx + radius - 2, cy - radius), (cx + radius - 2, cy + radius)]

            # Shadow
            pts_sh = [(px, py + 3) for px, py in pts]
            pygame.draw.polygon(target, (10, 5, 20, 80), pts_sh)
            pygame.draw.polygon(target, fill_col, pts)
            pygame.draw.polygon(target, border_col, pts, width=3)

        elif piece.kind == ShapeKind.SEMICIRCLE:
            rot = piece.rotation
            rect = pygame.Rect(cx - radius, cy - radius, size, size)
            if rot == 0:  # TOP curve
                start, end = 0, math.pi
                chord_pts = [(rect.left, cy), (rect.right, cy)]
            elif rot == 1:  # RIGHT curve
                start, end = -math.pi / 2, math.pi / 2
                chord_pts = [(cx, rect.top), (cx, rect.bottom)]
            elif rot == 2:  # BOTTOM curve
                start, end = math.pi, 2 * math.pi
                chord_pts = [(rect.left, cy), (rect.right, cy)]
            else:  # LEFT curve
                start, end = math.pi / 2, 3 * math.pi / 2
                chord_pts = [(cx, rect.top), (cx, rect.bottom)]

            # Draw filled pie/chord approximation
            pygame.draw.circle(target, fill_col, (cx, cy), radius)
            # Clip / mask the flat half
            if rot == 0:
                pygame.draw.rect(target, (30, 41, 59), (rect.left, cy, size, radius + 2))
            elif rot == 1:
                pygame.draw.rect(target, (30, 41, 59), (rect.left, rect.top, radius, size))
            elif rot == 2:
                pygame.draw.rect(target, (30, 41, 59), (rect.left, rect.top - 2, size, radius + 2))
            else:
                pygame.draw.rect(target, (30, 41, 59), (cx, rect.top, radius + 2, size))

            # Border arc & chord
            pygame.draw.arc(target, border_col, rect, start, end, 3)
            pygame.draw.line(target, border_col, chord_pts[0], chord_pts[1], 3)
