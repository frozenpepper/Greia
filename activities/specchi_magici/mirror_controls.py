"""Shared control-kit wiring for Specchi Magici (ADR 0037).

The mirror board and the tile kit are the Activity's own drawing; their
interactive parts join the kit as ``ExternalTarget``s, so arrows / D-pad /
left stick move one shared focus ring over them and Space / Enter / the south
button activate them like a tap (this replaces the hand-rolled cursor of
cf0df9ec with the platform focus model):

* each tray tile (activate = pick it up, or put it back);
* each open cell on the mirror side (activate = place the tile in hand);
* the listen ``IconButton`` (replays Lilli's spoken goal);
* ``ProgressDots`` show the finished mosaics (display only).

Pointer taps and drags on tiles and cells are routed by the app itself (it
needs press / drag / drop on the same targets); the kit owns focus, the
listen button, the dots and the completion overlay.
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
    from .mirror_layout import CELL, LISTEN_RECT, TOP_BAR_HEIGHT, cell_rect
    from .mirror_model import CHALLENGE_COUNT, GRID_COLS, GRID_ROWS, MAX_TRAY
else:
    from mirror_layout import CELL, LISTEN_RECT, TOP_BAR_HEIGHT, cell_rect
    from mirror_model import CHALLENGE_COUNT, GRID_COLS, GRID_ROWS, MAX_TRAY


def tile_id(index: int) -> str:
    return f"tile.{index}"


def cell_id(row: int, col: int) -> str:
    return f"cell.{row}.{col}"


class MirrorControls:
    """Own the focus targets, the listen button, the dots and one ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        on_tile: Callable[[int], object],
        on_cell: Callable[[int, int], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._on_tile = on_tile
        self.cells: dict[tuple[int, int], ExternalTarget] = {
            (row, col): ExternalTarget(
                cell_id(row, col),
                cell_rect(row, col).inflate(-8, -8),
                (lambda r=row, c=col: on_cell(r, c)),
                focus_radius=16,
            )
            for row in range(GRID_ROWS)
            for col in range(GRID_COLS)
        }
        self.tiles: list[ExternalTarget] = []
        self.listen: IconButton = kit.icon_button(
            "listen",
            LISTEN_RECT,
            icon=kit.glyph("listen", int(LISTEN_RECT.width * 0.62)),
            on_activate=on_listen,
        )
        self.progress: ProgressDots = kit.progress_dots(
            "progress", pygame.Rect(0, 0, 160, TOP_BAR_HEIGHT), total=CHALLENGE_COUNT
        )
        self.layer: ControlLayer = kit.layer((), layer_id="specchi.controls")

    def place_bar(self, layout: ControlLayout) -> None:
        """Dots just after the protected Home region; listen at the right end."""

        height = layout.control_height(TOP_BAR_HEIGHT - 4, maximum=56)
        bar = layout.top_bar(height)
        width = ProgressDots.preferred_width(self.progress.total, height)
        self.progress.rect = pygame.Rect(bar.left, bar.top, width, height)
        size = layout.control_height(LISTEN_RECT.height, maximum=88)
        self.listen.rect = pygame.Rect(bar.right - size, bar.top, size, size)
        self.layer.invalidation.invalidate()

    def set_tray(self, rects: Sequence[pygame.Rect]) -> None:
        self.tiles = [
            ExternalTarget(tile_id(index), rect, (lambda i=index: self._on_tile(i)), focus_radius=20)
            for index, rect in enumerate(rects[:MAX_TRAY])
        ]
        self.layer.set_targets((*self.tiles, *self.cells.values(), self.listen, self.progress))
        self.layer.invalidation.invalidate()

    def sync(self, *, open_cells: Iterable[tuple[int, int]], playing: bool) -> None:
        """Only open mirror-side cells (and tiles while playing) take focus."""

        open_set = set(open_cells)
        for cell, target in self.cells.items():
            target.enabled = playing and cell in open_set
        for target in self.tiles:
            target.enabled = playing
        if self.layer.focused_id is not None:
            focused = self.layer.target(self.layer.focused_id)
            if not focused.focusable:
                self.layer.focused_id = None
        self.layer.invalidation.invalidate()

    def focus_tile(self, index: int = 0) -> None:
        if self.tiles:
            self.layer.focus(tile_id(max(0, min(len(self.tiles) - 1, index))))

    def focus_board(self, preferred: tuple[int, int] | None) -> None:
        """Move focus onto the board (last cell if still open, else the first open one)."""

        if preferred is not None and self.layer.focus(cell_id(*preferred)):
            return
        for target in self.cells.values():
            if target.focusable:
                self.layer.focus(target.control_id)
                return

    def focused_cell(self) -> tuple[int, int] | None:
        focused = self.layer.focused_id
        if focused is None or not focused.startswith("cell."):
            return None
        _, row, col = focused.split(".")
        return (int(row), int(col))

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()


__all__ = ["CELL", "MirrorControls", "cell_id", "tile_id"]
