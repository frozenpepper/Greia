"""Scene geometry of Specchi Magici in 1024x600 logical pixels (pure data).

The magic mirror board stands centre stage (its vertical mirror line sits on
the stage's centre line), Lilli stands on the boards at its left and the
tile kit lies along the bottom. The top band stays free for the kit progress
dots, the listen button and the platform's protected Home region (ADR 0019);
at 480x320 that region maps to about 240x88 logical pixels, so nothing
interactive starts left of x 254 above y 92.
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .mirror_model import GRID_COLS, GRID_ROWS, HALF_COLS, HALF_ROWS, MAX_TRAY
else:
    from mirror_model import GRID_COLS, GRID_ROWS, HALF_COLS, HALF_ROWS, MAX_TRAY

CELL: Final = 80
TILE_SIZE: Final = 62
GRID_LEFT: Final = 512 - (GRID_COLS * CELL) // 2
GRID_TOP: Final = 94
GRID_RECT: Final = pygame.Rect(GRID_LEFT, GRID_TOP, GRID_COLS * CELL, GRID_ROWS * CELL)
FRAME_PAD: Final = 18
FRAME_RECT: Final = GRID_RECT.inflate(2 * FRAME_PAD, 2 * FRAME_PAD)
MIRROR_X: Final = GRID_LEFT + HALF_COLS * CELL
MIRROR_Y: Final = GRID_TOP + HALF_ROWS * CELL

TRAY_TOP: Final = 462
SLOT: Final = 86
SLOT_GAP: Final = 10
TRAY_TILE: Final = 64
TRAY_PAD: Final = 14
TRAY_CENTER_X: Final = 512

LILLI_HEIGHT: Final = 176
LILLI_MIDBOTTOM: Final = (134, 440)
LILLI_TAP_RECT: Final = pygame.Rect(LILLI_MIDBOTTOM[0] - 80, LILLI_MIDBOTTOM[1] - 168, 160, 168)

TOP_BAR_HEIGHT: Final = 48
LISTEN_SIZE: Final = 60
LISTEN_RECT: Final = pygame.Rect(1024 - 24 - LISTEN_SIZE, 14, LISTEN_SIZE, LISTEN_SIZE)


def cell_rect(row: int, col: int) -> pygame.Rect:
    return pygame.Rect(GRID_LEFT + col * CELL, GRID_TOP + row * CELL, CELL, CELL)


def cell_at(point: tuple[int, int]) -> tuple[int, int] | None:
    x, y = point
    if not GRID_RECT.collidepoint(x, y):
        return None
    return ((y - GRID_TOP) // CELL, (x - GRID_LEFT) // CELL)


def tray_rects(count: int) -> tuple[pygame.Rect, ...]:
    count = max(0, min(MAX_TRAY, count))
    total = count * SLOT + max(0, count - 1) * SLOT_GAP
    left = TRAY_CENTER_X - total // 2
    return tuple(pygame.Rect(left + i * (SLOT + SLOT_GAP), TRAY_TOP, SLOT, SLOT) for i in range(count))


def tray_panel(count: int) -> pygame.Rect:
    rects = tray_rects(max(1, count))
    union = rects[0].unionall(rects[1:]) if len(rects) > 1 else rects[0]
    return union.inflate(2 * TRAY_PAD, 2 * TRAY_PAD - 4)


__all__ = [
    "CELL",
    "FRAME_PAD",
    "FRAME_RECT",
    "GRID_LEFT",
    "GRID_RECT",
    "GRID_TOP",
    "LILLI_HEIGHT",
    "LILLI_MIDBOTTOM",
    "LILLI_TAP_RECT",
    "LISTEN_RECT",
    "LISTEN_SIZE",
    "MIRROR_X",
    "MIRROR_Y",
    "SLOT",
    "TILE_SIZE",
    "TOP_BAR_HEIGHT",
    "TRAY_TILE",
    "TRAY_TOP",
    "cell_at",
    "cell_rect",
    "tray_panel",
    "tray_rects",
]
