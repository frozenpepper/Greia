"""Reference-canvas geometry for Tito's Marble Run.

Everything is laid out on the 1024x600 logical canvas (``PygameReferenceCanvas``
scales it to the display). The HUD bar sits beside -- never inside -- the
protected Home/Back region and holds progress and hint (right); the tray
column runs down the left edge below that region with the big GO pill right
under the last piece (choosing pieces and pressing GO is one compact
mouse-first cluster, ADR 0037 §4a) and Tito standing at its foot, and the
board fills the rest at a fixed 5:3 aspect so the physics (in board units) is
identical at every size.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

from greia_platform.activity_controls import ControlLayout

if __package__:
    from .ramp_content import BOARD_HEIGHT, BOARD_WIDTH, SLOT_HEIGHT, SLOT_WIDTH
else:
    from ramp_content import BOARD_HEIGHT, BOARD_WIDTH, SLOT_HEIGHT, SLOT_WIDTH

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
COLUMN_WIDTH: Final = 150
MARGIN: Final = 12
FRAME: Final = 14  # wooden frame thickness around the board face (logical px)
MAX_TRAY: Final = 3
CAST_HEIGHT: Final = 150  # Tito, logical px (outside the board: never hides the run)
MIN_CAST_HEIGHT: Final = 96  # Tito on the smallest screens


@dataclass(frozen=True, slots=True)
class BoardView:
    """Map board units <-> logical canvas pixels (uniform scale)."""

    face: pygame.Rect  # the board face (inside the frame), logical px
    scale: float  # logical px per board unit

    @classmethod
    def fit(cls, area: pygame.Rect) -> "BoardView":
        inner = area.inflate(-2 * FRAME, -2 * FRAME)
        scale = min(inner.width / BOARD_WIDTH, inner.height / BOARD_HEIGHT)
        width = int(round(BOARD_WIDTH * scale))
        height = int(round(BOARD_HEIGHT * scale))
        face = pygame.Rect(0, 0, width, height)
        face.midbottom = (inner.centerx, inner.bottom)
        return cls(face, scale)

    @property
    def frame(self) -> pygame.Rect:
        return self.face.inflate(2 * FRAME, 2 * FRAME)

    def point(self, x: float, y: float) -> tuple[int, int]:
        return (int(round(self.face.x + x * self.scale)), int(round(self.face.y + y * self.scale)))

    def length(self, units: float) -> int:
        return max(1, int(round(units * self.scale)))

    def to_board(self, position: tuple[int, int]) -> tuple[float, float]:
        return ((position[0] - self.face.x) / self.scale, (position[1] - self.face.y) / self.scale)

    def slot_rect(self, centre: tuple[float, float]) -> pygame.Rect:
        rect = pygame.Rect(0, 0, self.length(SLOT_WIDTH), self.length(SLOT_HEIGHT))
        rect.center = self.point(*centre)
        return rect


@dataclass(frozen=True, slots=True)
class ScreenLayout:
    """Where the HUD bar, tray column, GO button and board sit (logical px).

    ``go`` is GO's slot under a full tray; ``go_after(count)`` puts it right
    under the last of ``count`` tray tiles.
    """

    bar: pygame.Rect
    tray: tuple[pygame.Rect, ...]
    go: pygame.Rect
    cast_midbottom: tuple[int, int]
    cast_height: int
    view: BoardView
    protected: pygame.Rect

    @classmethod
    def build(cls, layout: ControlLayout) -> "ScreenLayout":
        bar_h = layout.control_height(60, maximum=80)
        bar = layout.top_bar(bar_h)
        column_top = layout.protected.bottom + layout.gap
        cast_height = CAST_HEIGHT
        cast_midbottom = (MARGIN + COLUMN_WIDTH // 2, REFERENCE_HEIGHT - 4)
        gap = 10
        go_h = bar_h
        available = REFERENCE_HEIGHT - 4 - cast_height - gap - column_top - (go_h + gap)
        tile_h = min(118, (available - gap * (MAX_TRAY - 1)) // MAX_TRAY)
        floor = layout.control_height(0)
        if tile_h < floor:
            # Small screens: tiles keep the touch floor and Tito stands a bit smaller.
            tile_h = floor
            used = column_top + MAX_TRAY * tile_h + gap * (MAX_TRAY - 1) + gap + go_h + gap
            cast_height = max(MIN_CAST_HEIGHT, REFERENCE_HEIGHT - 4 - used)
        tray = tuple(
            pygame.Rect(MARGIN, column_top + index * (tile_h + gap), COLUMN_WIDTH, tile_h)
            for index in range(MAX_TRAY)
        )
        go = pygame.Rect(MARGIN, tray[-1].bottom + gap, COLUMN_WIDTH, go_h)
        left = MARGIN + COLUMN_WIDTH + MARGIN
        top = bar.bottom + 6
        if left < layout.protected.right:
            top = max(top, layout.protected.bottom + 6)
        area = pygame.Rect(left, top, REFERENCE_WIDTH - MARGIN - left, REFERENCE_HEIGHT - 4 - top)
        return cls(bar, tray, go, cast_midbottom, cast_height, BoardView.fit(area), layout.protected)

    def go_after(self, count: int) -> pygame.Rect:
        """GO right under the last of ``count`` tray tiles (the pieces it confirms)."""

        count = max(1, min(len(self.tray), int(count)))
        gap = self.go.top - self.tray[-1].bottom
        return self.go.move(0, self.tray[count - 1].bottom + gap - self.go.top)


__all__ = ["BoardView", "COLUMN_WIDTH", "FRAME", "CAST_HEIGHT", "MAX_TRAY", "REFERENCE_HEIGHT", "REFERENCE_WIDTH", "ScreenLayout"]
