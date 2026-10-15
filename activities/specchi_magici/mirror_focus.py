"""Keyboard / controller focus for Specchi Magici.

Pointer play picks a tray piece and then a board cell. The same two steps are
reachable with arrows / D-pad and Space / south button (ADR 0020 learned
vocabulary): the cursor lives either on the board or on the tray row (whose
last slot is the Undo button), and moving down past the board or up from the
tray switches between the two, matching how they are laid out on screen.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

if __package__:
    from .mirror_model import GRID_COLS, GRID_ROWS
else:
    from mirror_model import GRID_COLS, GRID_ROWS


class FocusZone(StrEnum):
    GRID = "grid"
    TRAY = "tray"


class MirrorFocus:
    """Small value object: where the non-pointer cursor currently is.

    ``tray_index == tray_count`` addresses the Undo button, so the whole bottom
    row is one linear strip. The object never touches the session; the
    Activity applies the focused target the same way as a pointer press.
    """

    START_CELL: Final = (GRID_ROWS // 2, GRID_COLS // 2 - 1)

    def __init__(self) -> None:
        self.active = False
        self.zone = FocusZone.TRAY
        self.cell = self.START_CELL
        self.tray_index = 0

    def reset(self) -> None:
        self.active = False
        self.zone = FocusZone.TRAY
        self.cell = self.START_CELL
        self.tray_index = 0

    def move(self, dx: int, dy: int, tray_count: int) -> None:
        """Move the cursor one step; the first move only reveals it."""
        if not self.active:
            self.active = True
            self.tray_index = min(self.tray_index, tray_count)
            return
        if self.zone is FocusZone.GRID:
            row, col = self.cell
            if dy > 0 and row == GRID_ROWS - 1:
                self.zone = FocusZone.TRAY
                self.tray_index = self._tray_index_for_column(col, tray_count)
                return
            self.cell = (
                max(0, min(GRID_ROWS - 1, row + dy)),
                max(0, min(GRID_COLS - 1, col + dx)),
            )
            return
        self.tray_index = max(0, min(tray_count, self.tray_index + dx))
        if dy < 0:
            self.zone = FocusZone.GRID
            self.cell = (GRID_ROWS - 1, self._column_for_tray_index(tray_count))

    def enter_grid(self) -> None:
        """Switch to the board, e.g. right after a tray piece was picked up."""
        self.zone = FocusZone.GRID

    def _tray_index_for_column(self, col: int, tray_count: int) -> int:
        if tray_count <= 0:
            return 0
        return min(tray_count - 1, col * tray_count // GRID_COLS)

    def _column_for_tray_index(self, tray_count: int) -> int:
        if tray_count <= 0:
            return GRID_COLS // 2
        index = min(self.tray_index, tray_count - 1)
        return min(GRID_COLS - 1, (index * GRID_COLS) // tray_count + GRID_COLS // (2 * tray_count))


__all__ = ["FocusZone", "MirrorFocus"]
