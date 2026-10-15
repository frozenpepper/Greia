"""Keyboard / controller focus for Costruiamo Ponti.

Pointer play has four kinds of targets: the Clear/Go buttons (top), the bridge
slots (middle) and the material palette (bottom). Arrows / D-pad move one
focus cursor over exactly those targets in the same visual rows and Space /
south button act on it, matching the learned ADR 0020 vocabulary. The object
is pure state (no Pygame, no model access); the app applies the focused target
exactly like a pointer press so there is one rule path.
"""

from __future__ import annotations

from typing import Callable, Final, NamedTuple

if __package__:
    from .ponti_content import BLOCKS
else:
    from ponti_content import BLOCKS


class FocusTarget(NamedTuple):
    kind: str  # "clear" | "go" | "slot" | "block"
    index: int


_ROW_BUTTONS: Final = 0
_ROW_SLOTS: Final = 1
_ROW_PALETTE: Final = 2
_BUTTON_KINDS: Final = ("clear", "go")
_ROW_KINDS: Final = (None, "slot", "block")


class PontiFocus:
    """Cursor over the visible targets, organised as three horizontal rows."""

    def __init__(self) -> None:
        self.active = False
        self._row = _ROW_PALETTE
        self._col = 0

    def reveal(self, selected_block_index: int = 0) -> None:
        """Show the cursor, starting on the currently selected material."""
        self.active = True
        self._row = _ROW_PALETTE
        self._col = max(0, min(len(BLOCKS) - 1, selected_block_index))

    def hide(self) -> None:
        self.active = False

    def target(self, num_slots: int) -> FocusTarget:
        self._clamp(num_slots)
        if self._row == _ROW_BUTTONS:
            return FocusTarget(_BUTTON_KINDS[self._col], 0)
        return FocusTarget(_ROW_KINDS[self._row], self._col)  # type: ignore[arg-type]

    def move(
        self,
        dx: int,
        dy: int,
        num_slots: int,
        center_x: Callable[[FocusTarget], float],
    ) -> FocusTarget:
        """Move one step; vertical moves land on the nearest target by x."""
        before = self.target(num_slots)
        row = max(_ROW_BUTTONS, min(_ROW_PALETTE, self._row + dy))
        if row != self._row:
            x = center_x(before)
            self._row = row
            self._col = min(
                range(self._row_size(num_slots)),
                key=lambda col: abs(center_x(self._target_at(row, col)) - x),
            )
        else:
            self._col += dx
        return self.target(num_slots)

    def _target_at(self, row: int, col: int) -> FocusTarget:
        if row == _ROW_BUTTONS:
            return FocusTarget(_BUTTON_KINDS[col], 0)
        return FocusTarget(_ROW_KINDS[row], col)  # type: ignore[arg-type]

    def _row_size(self, num_slots: int) -> int:
        return (len(_BUTTON_KINDS), num_slots, len(BLOCKS))[self._row]

    def _clamp(self, num_slots: int) -> None:
        self._col = max(0, min(self._row_size(num_slots) - 1, self._col))


__all__ = ["FocusTarget", "PontiFocus"]
