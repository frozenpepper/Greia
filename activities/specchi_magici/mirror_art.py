"""Prepared visual resources and shape rendering for Specchi Magici."""

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
            return pygame.transform.scale(image, (170, 170))
        except (OSError, ValueError, pygame.error, RuntimeError):
            return None

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))
        surface.fill((26, 16, 48))

        # Ambient crystal purple/blue gradients
        pygame.draw.rect(surface, (36, 22, 64), (0, 0, width, 200))
        pygame.draw.rect(surface, (22, 14, 40), (0, 360, width, height - 360))

        # Floating sparkles
        for x, y, r in [
            (120, 60, 3), (220, 40, 4), (840, 70, 4), (920, 120, 3),
            (160, 320, 3), (880, 340, 4), (512, 40, 6),
        ]:
            pygame.draw.circle(surface, (233, 213, 255), (x, y), r)

        return surface

    @staticmethod
    def draw_piece(target: pygame.Surface, cx: int, cy: int, size: int, piece: Piece) -> None:
        """Render a crisp geometric shape piece at (cx, cy) with diameter size."""
        palette = COLOR_PALETTES[piece.color_index % len(COLOR_PALETTES)]
        fill_col, border_col = palette
        radius = size // 2

        if piece.kind == ShapeKind.CIRCLE:
            pygame.draw.circle(target, fill_col, (cx, cy), radius)
            pygame.draw.circle(target, border_col, (cx, cy), radius, 3)

        elif piece.kind == ShapeKind.SQUARE:
            rect = pygame.Rect(cx - radius + 2, cy - radius + 2, size - 4, size - 4)
            pygame.draw.rect(target, fill_col, rect, border_radius=6)
            pygame.draw.rect(target, border_col, rect, width=3, border_radius=6)

        elif piece.kind == ShapeKind.TRIANGLE:
            # Rotations: 0 (UP), 1 (RIGHT), 2 (DOWN), 3 (LEFT)
            rot = piece.rotation
            if rot == 0:  # UP
                pts = [(cx, cy - radius), (cx + radius, cy + radius - 2), (cx - radius, cy + radius - 2)]
            elif rot == 1:  # RIGHT
                pts = [(cx + radius, cy), (cx - radius + 2, cy - radius), (cx - radius + 2, cy + radius)]
            elif rot == 2:  # DOWN
                pts = [(cx, cy + radius), (cx + radius, cy - radius + 2), (cx - radius, cy - radius + 2)]
            else:  # LEFT
                pts = [(cx - radius, cy), (cx + radius - 2, cy - radius), (cx + radius - 2, cy + radius)]

            pygame.draw.polygon(target, fill_col, pts)
            pygame.draw.polygon(target, border_col, pts, width=3)

        elif piece.kind == ShapeKind.SEMICIRCLE:
            # Rotations: 0 (TOP), 1 (RIGHT), 2 (BOTTOM), 3 (LEFT)
            rot = piece.rotation
            rect = pygame.Rect(cx - radius, cy - radius, size, size)
            if rot == 0:  # TOP curve
                start, end = 0, math.pi
            elif rot == 1:  # RIGHT curve
                start, end = -math.pi / 2, math.pi / 2
            elif rot == 2:  # BOTTOM curve
                start, end = math.pi, 2 * math.pi
            else:  # LEFT curve
                start, end = math.pi / 2, 3 * math.pi / 2

            # Semicircle filled with pie slice or arc
            pygame.draw.circle(target, fill_col, (cx, cy), radius)
            # Mask the opposite half
            if rot == 0:
                pygame.draw.rect(target, (26, 16, 48), (cx - radius - 2, cy, size + 4, radius + 4))
            elif rot == 1:
                pygame.draw.rect(target, (26, 16, 48), (cx - radius - 2, cy - radius - 2, radius + 2, size + 4))
            elif rot == 2:
                pygame.draw.rect(target, (26, 16, 48), (cx - radius - 2, cy - radius - 2, size + 4, radius + 2))
            else:
                pygame.draw.rect(target, (26, 16, 48), (cx, cy - radius - 2, radius + 4, size + 4))

            pygame.draw.arc(target, border_col, rect, start, end, 3)
