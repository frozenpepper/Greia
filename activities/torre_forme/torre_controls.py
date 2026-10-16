"""Shared control-kit wiring for La Torre delle Forme (ADR 0037).

The build and the block kit are the Activity's own drawing; their
interactive parts join the kit as ``ExternalTarget``s, so arrows / D-pad /
left stick move one shared focus ring over them and Space / Enter / the
south button activate them like a tap:

* each kit slot (activate = pick the block up; again = turn it);
* each still-open cell of the build (activate = put the block in hand there);
* the turn ``IconButton`` (``icon.hud.rotate``; turns the block in hand);
* the listen ``IconButton`` (Dani says what we are building);
* ``ProgressDots`` show the finished builds of the set (display only).

Pointer taps and drags on kit blocks and on the build are routed by the app
itself (it needs press / drag / drop on the same targets); the kit owns
focus, the two buttons, the dots and the completion overlay.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

import pygame

from greia_platform.activity_controls import (
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
)

if __package__:
    from .torre_layout import LISTEN_RECT, TOP_BAR_HEIGHT, TURN_SIZE, BoardFrame, turn_rect
    from .torre_model import BUILDS_PER_SET, MAX_KIT, Cell
else:
    from torre_layout import LISTEN_RECT, TOP_BAR_HEIGHT, TURN_SIZE, BoardFrame, turn_rect
    from torre_model import BUILDS_PER_SET, MAX_KIT, Cell


def tile_id(index: int) -> str:
    return f"tile.{index}"


def cell_id(cell: Cell) -> str:
    return f"cell.{cell[0]}.{cell[1]}"


class TorreControls:
    """Own the focus targets, the two buttons, the dots and one ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        on_tile: Callable[[int], object],
        on_cell: Callable[[Cell], object],
        on_turn: Callable[[], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._on_tile = on_tile
        self._on_cell = on_cell
        self.tiles: list[ExternalTarget] = []
        self.cells: dict[Cell, ExternalTarget] = {}
        self.turn: IconButton = kit.icon_button(
            "turn",
            pygame.Rect(0, 0, TURN_SIZE, TURN_SIZE),
            icon=kit.glyph("rotate", int(TURN_SIZE * 0.62)),
            on_activate=on_turn,
        )
        self.listen: IconButton = kit.icon_button(
            "listen",
            LISTEN_RECT,
            icon=kit.glyph("listen", int(LISTEN_RECT.width * 0.62)),
            on_activate=on_listen,
        )
        self.progress: ProgressDots = kit.progress_dots(
            "progress", pygame.Rect(0, 0, 160, TOP_BAR_HEIGHT), total=BUILDS_PER_SET
        )
        self.layer: ControlLayer = kit.layer((), layer_id="torre.controls")

    def place_bar(self, layout: ControlLayout) -> None:
        """Dots just after the protected Home region; listen at the right end."""

        height = layout.control_height(TOP_BAR_HEIGHT - 4, maximum=56)
        bar = layout.top_bar(height)
        width = ProgressDots.preferred_width(self.progress.total, height)
        self.progress.rect = pygame.Rect(bar.left, bar.top, width, height)
        size = layout.control_height(LISTEN_RECT.height, maximum=88)
        self.listen.rect = pygame.Rect(bar.right - size, bar.top, size, size)
        self.layer.invalidation.invalidate()

    def set_build(self, frame: BoardFrame, cells: Iterable[Cell], tray: Sequence[pygame.Rect]) -> None:
        """New build: one target per kit slot and per cell of the outline."""

        self.tiles = [
            ExternalTarget(tile_id(index), rect, (lambda i=index: self._on_tile(i)), focus_radius=20)
            for index, rect in enumerate(tray[:MAX_KIT])
        ]
        self.cells = {
            cell: ExternalTarget(
                cell_id(cell), frame.cell_rect(cell).inflate(-8, -8), (lambda c=cell: self._on_cell(c)), focus_radius=14
            )
            for cell in sorted(cells, key=lambda c: (c[1], c[0]))
        }
        self.turn.rect = turn_rect(len(self.tiles))
        self.layer.set_targets((*self.tiles, *self.cells.values(), self.turn, self.listen, self.progress))
        self.layer.invalidation.invalidate()

    def sync(self, *, open_cells: Iterable[Cell], playing: bool, can_turn: bool) -> None:
        """Only open cells (and kit slots while playing) take focus."""

        open_set = set(open_cells)
        for cell, target in self.cells.items():
            target.enabled = playing and cell in open_set
        for target in self.tiles:
            target.enabled = playing
        self.turn.enabled = playing and can_turn
        if self.layer.focused_id is not None:
            focused = self.layer.target(self.layer.focused_id)
            if not focused.focusable:
                self.layer.focused_id = None
        self.layer.invalidation.invalidate()

    def focus_tile(self, index: int = 0) -> None:
        if self.tiles:
            self.layer.focus(tile_id(max(0, min(len(self.tiles) - 1, index))))

    def focus_board(self, preferred: Cell | None) -> None:
        """Move focus onto the build (last cell if still open, else the lowest open one)."""

        if preferred is not None and preferred in self.cells and self.layer.focus(cell_id(preferred)):
            return
        for cell in sorted(self.cells, key=lambda c: (-c[1], c[0])):
            if self.cells[cell].focusable:
                self.layer.focus(cell_id(cell))
                return

    def focused_cell(self) -> Cell | None:
        focused = self.layer.focused_id
        if focused is None or not focused.startswith("cell."):
            return None
        _, col, row = focused.split(".")
        return (int(col), int(row))

    def focused_tile(self) -> int | None:
        focused = self.layer.focused_id
        if focused is None or not focused.startswith("tile."):
            return None
        return int(focused.split(".")[1])

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()


__all__ = ["TorreControls", "cell_id", "tile_id"]
