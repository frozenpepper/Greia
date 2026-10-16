"""Scene geometry of La Torre delle Forme in 1024x600 logical pixels (pure data).

Dani stands in the playroom at the left; the build rises from a wooden
workbench in the middle (every build is centred on the bench and stands on
its top edge); the "picture on the box" card stands on the wall shelf at the right;
the block kit lies in a tray along the bottom with the turn button at its
right end. The top band stays free for the progress dots, the listen button
and the platform's protected Home region (ADR 0019); at 480x320 that region
maps to about 240x88 logical pixels, so nothing interactive starts left of
x 254 above y 92.
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .torre_model import MAX_BUILD_COLS, MAX_BUILD_ROWS, MAX_KIT, Block, BuildPlan, Cell, Placement
else:
    from torre_model import MAX_BUILD_COLS, MAX_BUILD_ROWS, MAX_KIT, Block, BuildPlan, Cell, Placement

CELL: Final = 72
BENCH_TOP: Final = 452
BOARD_CENTER_X: Final = 560
BENCH_RECT: Final = pygame.Rect(BOARD_CENTER_X - (MAX_BUILD_COLS * CELL) // 2 - 40, BENCH_TOP, MAX_BUILD_COLS * CELL + 80, 24)
BOARD_RECT: Final = pygame.Rect(
    BOARD_CENTER_X - (MAX_BUILD_COLS * CELL) // 2,
    BENCH_TOP - MAX_BUILD_ROWS * CELL,
    MAX_BUILD_COLS * CELL,
    MAX_BUILD_ROWS * CELL,
)

TRAY_TOP: Final = 486
SLOT: Final = 100
SLOT_GAP: Final = 10
TRAY_UNIT: Final = 46
TRAY_PAD: Final = 12
TURN_SIZE: Final = 84
TURN_GAP: Final = 18
TRAY_CENTER_X: Final = 548

DANI_HEIGHT: Final = 188
DANI_MIDBOTTOM: Final = (146, 462)
DANI_TAP_RECT: Final = pygame.Rect(DANI_MIDBOTTOM[0] - 82, DANI_MIDBOTTOM[1] - 180, 164, 180)

# Stands on the lower shelf of the playroom wall art (shelf x 830..1010, top y 270).
CARD_RECT: Final = pygame.Rect(845, 118, 150, 150)

TOP_BAR_HEIGHT: Final = 48
LISTEN_SIZE: Final = 60
LISTEN_RECT: Final = pygame.Rect(1024 - 24 - LISTEN_SIZE, 14, LISTEN_SIZE, LISTEN_SIZE)


class BoardFrame:
    """Where one build sits: centred on the bench, standing on its top edge."""

    def __init__(self, plan: BuildPlan) -> None:
        width, height = plan.size
        self.cols = width
        self.rows = height
        self.left = BOARD_CENTER_X - (width * CELL) // 2
        self.top = BENCH_TOP - height * CELL

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.left, self.top, self.cols * CELL, self.rows * CELL)

    def cell_rect(self, cell: Cell) -> pygame.Rect:
        col, row = cell
        return pygame.Rect(self.left + col * CELL, self.top + row * CELL, CELL, CELL)

    def placement_rect(self, placement: Placement) -> pygame.Rect:
        width, height = placement.block.size
        return pygame.Rect(self.left + placement.col * CELL, self.top + placement.row * CELL, width * CELL, height * CELL)

    def to_cells(self, point: tuple[int, int]) -> tuple[float, float]:
        """A logical point in cell units of this build's grid."""

        return ((point[0] - self.left) / CELL, (point[1] - self.top) / CELL)

    def cell_at(self, point: tuple[int, int]) -> Cell | None:
        x, y = self.to_cells(point)
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return None
        return (int(x), int(y))

    def near_board(self, point: tuple[int, int], margin: int = CELL // 2) -> bool:
        return self.rect.inflate(2 * margin, 2 * margin).collidepoint(point)


def tray_rects(count: int) -> tuple[pygame.Rect, ...]:
    count = max(0, min(MAX_KIT, count))
    total = count * SLOT + max(0, count - 1) * SLOT_GAP + TURN_GAP + TURN_SIZE
    left = TRAY_CENTER_X - total // 2
    return tuple(pygame.Rect(left + i * (SLOT + SLOT_GAP), TRAY_TOP, SLOT, SLOT) for i in range(count))


def tray_panel(count: int) -> pygame.Rect:
    rects = tray_rects(max(1, count))
    union = rects[0].unionall(rects[1:]) if len(rects) > 1 else rects[0]
    return union.inflate(2 * TRAY_PAD, 2 * TRAY_PAD - 6)


def turn_rect(count: int) -> pygame.Rect:
    panel = tray_panel(count)
    return pygame.Rect(panel.right + TURN_GAP - TRAY_PAD, panel.centery - TURN_SIZE // 2, TURN_SIZE, TURN_SIZE)


def tray_block_size(block: Block) -> tuple[int, int]:
    width, height = block.size
    return (width * TRAY_UNIT, height * TRAY_UNIT)


__all__ = [
    "BENCH_RECT",
    "BENCH_TOP",
    "BOARD_CENTER_X",
    "BOARD_RECT",
    "BoardFrame",
    "CARD_RECT",
    "CELL",
    "DANI_HEIGHT",
    "DANI_MIDBOTTOM",
    "DANI_TAP_RECT",
    "LISTEN_RECT",
    "LISTEN_SIZE",
    "SLOT",
    "TOP_BAR_HEIGHT",
    "TRAY_TOP",
    "TRAY_UNIT",
    "TURN_SIZE",
    "tray_block_size",
    "tray_panel",
    "tray_rects",
    "turn_rect",
]
