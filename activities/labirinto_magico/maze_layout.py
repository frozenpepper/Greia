"""Reference-canvas geometry for Il Labirinto Magico.

Everything is laid out on the 1024x600 logical canvas
(``PygameReferenceCanvas`` scales it to the display), below the top HUD bar,
which itself sits beside -- never inside -- the protected Home/Back region.
Maze cells are square; hedge lines are thinner (``GAP_SHARE`` of a cell) so the
corridors and Tito stay as large as the screen allows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .maze_model import GAP_SHARE, Cell, MazeLayout
else:
    from maze_model import GAP_SHARE, Cell, MazeLayout

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
MAX_CELL: Final = 104
MIN_CELL: Final = 18
SIDE_MARGIN: Final = 20
BOTTOM_MARGIN: Final = 14


@dataclass(frozen=True, slots=True)
class MazeGeometry:
    """Pixel placement of one maze (rows/cols of squares -> logical px)."""

    cell: int
    gap: int
    xs: tuple[int, ...]  # left edge of each grid column (+ final right edge)
    ys: tuple[int, ...]  # top edge of each grid row (+ final bottom edge)

    @classmethod
    def fit(cls, layout: MazeLayout, area: pygame.Rect) -> "MazeGeometry":
        cols, rows = layout.cols, layout.rows
        # Units: cols cells + (cols + 1) hedge lines, plus the garden panel's
        # rim (half a hedge on each side) and the hedges' front-face depth.
        width_units = cols + (cols + 2) * GAP_SHARE
        height_units = rows + (rows + 2) * GAP_SHARE + GAP_SHARE * 0.5
        cell = int(min(area.width / width_units, area.height / height_units, MAX_CELL))
        cell = max(MIN_CELL, cell)
        gap = max(6, int(round(cell * GAP_SHARE)))
        total_w = cols * cell + (cols + 1) * gap
        total_h = rows * cell + (rows + 1) * gap
        outer_h = total_h + gap + gap // 2
        left = area.centerx - total_w // 2
        top = area.top + gap // 2 + max(0, (area.height - outer_h) // 2)
        xs = [left]
        for index in range(layout.width):
            xs.append(xs[-1] + (cell if index % 2 else gap))
        ys = [top]
        for index in range(layout.height):
            ys.append(ys[-1] + (cell if index % 2 else gap))
        return cls(cell, gap, tuple(xs), tuple(ys))

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.xs[0], self.ys[0], self.xs[-1] - self.xs[0], self.ys[-1] - self.ys[0])

    @property
    def depth(self) -> int:
        """Height of a hedge's front face (it hangs into the corridor below)."""

        return max(3, int(round(self.gap * 0.36)))

    def square_rect(self, square: Cell) -> pygame.Rect:
        r, c = square
        return pygame.Rect(self.xs[c], self.ys[r], self.xs[c + 1] - self.xs[c], self.ys[r + 1] - self.ys[r])

    def center(self, row: float, col: float) -> tuple[float, float]:
        """Centre of a (possibly fractional) square position."""

        return (_interp(self.xs, col), _interp(self.ys, row))

    def square_at(self, point: tuple[int, int]) -> Cell | None:
        x, y = point
        if not (self.xs[0] <= x < self.xs[-1] and self.ys[0] <= y < self.ys[-1]):
            return None
        col = next(index for index in range(len(self.xs) - 1) if x < self.xs[index + 1])
        row = next(index for index in range(len(self.ys) - 1) if y < self.ys[index + 1])
        return (row, col)

    def nearest_cell(self, point: tuple[int, int]) -> Cell | None:
        """The maze cell (odd/odd square) under or nearest to a tap in the maze."""

        square = self.square_at(point)
        if square is None:
            return None
        best: Cell | None = None
        best_d = 0.0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                r, c = square[0] + dr, square[1] + dc
                if r % 2 == 0 or c % 2 == 0 or r < 1 or c < 1 or r >= len(self.ys) - 2 or c >= len(self.xs) - 2:
                    continue
                cx, cy = self.center(r, c)
                d = (cx - point[0]) ** 2 + (cy - point[1]) ** 2
                if best is None or d < best_d:
                    best, best_d = (r, c), d
        return best


def _interp(edges: tuple[int, ...], position: float) -> float:
    """Centre of fractional square ``position`` along one axis."""

    last = len(edges) - 2
    position = max(0.0, min(float(last), position))
    low = int(position)
    high = min(last, low + 1)
    t = position - low
    low_c = (edges[low] + edges[low + 1]) / 2.0
    high_c = (edges[high] + edges[high + 1]) / 2.0
    return low_c + (high_c - low_c) * t


def maze_area(top: int) -> pygame.Rect:
    """Free area for the maze below the HUD bar (logical px)."""

    return pygame.Rect(SIDE_MARGIN, top, REFERENCE_WIDTH - 2 * SIDE_MARGIN, REFERENCE_HEIGHT - BOTTOM_MARGIN - top)


__all__ = ["MazeGeometry", "REFERENCE_HEIGHT", "REFERENCE_WIDTH", "maze_area"]
