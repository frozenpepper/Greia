"""Reference-canvas geometry for La Corsa delle Bacche.

Everything is laid out on the 1024x600 logical canvas
(``PygameReferenceCanvas`` scales it to the display), below the top HUD bar,
which itself sits beside -- never inside -- the protected Home/Back region.
Garden cells are square; hedge lines are thinner (``GAP_SHARE`` of a cell) so
paths, berries, Momo and the critters stay as big as the screen allows
(cells are >= 72 px at 1024x600 on every rung).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .corsa_model import Cell, GardenLayout
else:
    from corsa_model import Cell, GardenLayout

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
GAP_SHARE: Final = 0.42  # a hedge line is this share of a cell
MAX_CELL: Final = 112
MIN_CELL: Final = 18
SIDE_MARGIN: Final = 20
BOTTOM_MARGIN: Final = 12


@dataclass(frozen=True, slots=True)
class GardenGeometry:
    """Pixel placement of one garden (lattice squares -> logical px)."""

    cell: int
    gap: int
    xs: tuple[int, ...]  # left edge of each lattice column (+ final right edge)
    ys: tuple[int, ...]  # top edge of each lattice row (+ final bottom edge)

    @classmethod
    def fit(cls, layout: GardenLayout, area: pygame.Rect) -> "GardenGeometry":
        cols, rows = layout.cols, layout.rows
        # Units: cells + hedge lines, plus the garden panel's rim (half a hedge
        # on each side) and the hedges' front-face depth.
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
        for index in range(2 * cols + 1):
            xs.append(xs[-1] + (cell if index % 2 else gap))
        ys = [top]
        for index in range(2 * rows + 1):
            ys.append(ys[-1] + (cell if index % 2 else gap))
        return cls(cell, gap, tuple(xs), tuple(ys))

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.xs[0], self.ys[0], self.xs[-1] - self.xs[0], self.ys[-1] - self.ys[0])

    @property
    def depth(self) -> int:
        """Height of a hedge's front face (it hangs into the path below)."""

        return max(3, int(round(self.gap * 0.36)))

    def square_rect(self, square: tuple[int, int]) -> pygame.Rect:
        """Rect of one lattice square (row, col)."""

        r, c = square
        return pygame.Rect(self.xs[c], self.ys[r], self.xs[c + 1] - self.xs[c], self.ys[r + 1] - self.ys[r])

    def cell_rect(self, cell: Cell) -> pygame.Rect:
        return self.square_rect((2 * cell[0] + 1, 2 * cell[1] + 1))

    def center(self, row: float, col: float) -> tuple[float, float]:
        """Centre of a (possibly fractional) garden cell position."""

        return (_interp(self.xs, 2 * col + 1), _interp(self.ys, 2 * row + 1))

    def cell_at(self, point: tuple[int, int]) -> Cell | None:
        """The garden cell under, or nearest to, a tap inside the garden."""

        x, y = point
        rect = self.rect.inflate(self.gap, self.gap)
        if not rect.collidepoint(x, y):
            return None
        rows = (len(self.ys) - 2) // 2
        cols = (len(self.xs) - 2) // 2
        best: Cell | None = None
        best_d = 0.0
        for r in range(rows):
            for c in range(cols):
                cx, cy = self.center(r, c)
                d = (cx - x) ** 2 + (cy - y) ** 2
                if best is None or d < best_d:
                    best, best_d = (r, c), d
        return best


def _interp(edges: tuple[int, ...], position: float) -> float:
    """Centre of fractional lattice square ``position`` along one axis."""

    last = len(edges) - 2
    position = max(0.0, min(float(last), position))
    low = int(position)
    high = min(last, low + 1)
    t = position - low
    low_c = (edges[low] + edges[low + 1]) / 2.0
    high_c = (edges[high] + edges[high + 1]) / 2.0
    return low_c + (high_c - low_c) * t


def garden_area(top: int) -> pygame.Rect:
    """Free area for the garden below the HUD bar (logical px)."""

    return pygame.Rect(SIDE_MARGIN, top, REFERENCE_WIDTH - 2 * SIDE_MARGIN, REFERENCE_HEIGHT - BOTTOM_MARGIN - top)


__all__ = ["GAP_SHARE", "GardenGeometry", "REFERENCE_HEIGHT", "REFERENCE_WIDTH", "garden_area"]
