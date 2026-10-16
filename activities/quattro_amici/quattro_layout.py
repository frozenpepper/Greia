"""Scene geometry for Quattro Amici in 1024x600 logical pixels.

Flash stands on the meadow at the left, Leo at the right, the standing board
in between. The board geometry depends on the stage (5x4 up to 7x6), so it is
computed once per stage by ``BoardGeometry.for_stage`` and shared by art,
renderer and controls. Nothing here enters the protected Home/Back corner:
the board area starts below the top control bar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .quattro_content import REFERENCE_WIDTH, Player, Stage
else:
    from quattro_content import REFERENCE_WIDTH, Player, Stage

CAST_HEIGHT: Final[int] = 204
CAST_MIDBOTTOM: Final[dict[Player, tuple[int, int]]] = {
    Player.FLASH: (124, 512),
    Player.LEO: (900, 512),
}
PLATE_SIZE: Final[tuple[int, int]] = (164, 62)
PLATE_TOP: Final[int] = 520

BOARD_AREA: Final[pygame.Rect] = pygame.Rect(244, 96, 536, 494)
BOARD_PAD: Final[int] = 16
FEET_HEIGHT: Final[int] = 18
MAX_CELL: Final[int] = 88
NEXT_BUTTON_SIZE: Final[int] = 136


def plate_rect(player: Player) -> pygame.Rect:
    """Score plate under a friend: their disc and one slot per needed win."""

    x, _ = CAST_MIDBOTTOM[player]
    width, height = PLATE_SIZE
    return pygame.Rect(x - width // 2, PLATE_TOP, width, height)


@dataclass(frozen=True, slots=True)
class BoardGeometry:
    """Pixel geometry of one stage's board (cells, frame, selector row)."""

    cols: int
    rows: int
    cell: int
    grid: pygame.Rect  # the cell area (holes)
    frame: pygame.Rect  # the wooden plate around the grid
    selector_y: int  # centre of the hovering disc above the board

    @classmethod
    def for_stage(cls, stage: Stage, area: pygame.Rect = BOARD_AREA) -> "BoardGeometry":
        usable_w = area.width - 2 * BOARD_PAD
        usable_h = area.height - FEET_HEIGHT - 2 * BOARD_PAD
        cell = int(min(MAX_CELL, usable_w / stage.cols, usable_h / (stage.rows + 1)))
        grid_w, grid_h = cell * stage.cols, cell * stage.rows
        bottom = area.bottom - FEET_HEIGHT - BOARD_PAD
        grid = pygame.Rect(area.centerx - grid_w // 2, bottom - grid_h, grid_w, grid_h)
        frame = grid.inflate(2 * BOARD_PAD, 2 * BOARD_PAD)
        selector_y = frame.top - cell // 2 - 4
        return cls(stage.cols, stage.rows, cell, grid, frame, selector_y)

    @property
    def hole_radius(self) -> int:
        return int(self.cell * 0.40)

    @property
    def token_size(self) -> int:
        """Disc diameter: a hair wider than the hole so the plate overlaps it."""

        return 2 * self.hole_radius + 4

    @property
    def selector_size(self) -> int:
        return int(self.token_size * 0.92)

    def cell_center(self, row: int, col: int) -> tuple[int, int]:
        return (
            self.grid.left + col * self.cell + self.cell // 2,
            self.grid.top + row * self.cell + self.cell // 2,
        )

    def column_x(self, col: int) -> int:
        return self.grid.left + col * self.cell + self.cell // 2

    def column_rect(self, col: int) -> pygame.Rect:
        """Tap/focus target: the column plus the selector row above the board."""

        top = self.selector_y - self.cell // 2
        return pygame.Rect(self.grid.left + col * self.cell, top, self.cell, self.frame.bottom - top)

    def column_at(self, x: float) -> int | None:
        if not self.grid.left <= x < self.grid.right:
            return None
        return max(0, min(self.cols - 1, int((x - self.grid.left) // self.cell)))

    def drop_start_y(self) -> float:
        return float(self.selector_y)


def next_button_rect(geometry: BoardGeometry) -> pygame.Rect:
    size = NEXT_BUTTON_SIZE
    return pygame.Rect(geometry.grid.centerx - size // 2, geometry.grid.centery - size // 2, size, size)


assert BOARD_AREA.right <= REFERENCE_WIDTH

__all__ = [
    "BOARD_AREA",
    "BoardGeometry",
    "CAST_HEIGHT",
    "CAST_MIDBOTTOM",
    "PLATE_SIZE",
    "next_button_rect",
    "plate_rect",
]
