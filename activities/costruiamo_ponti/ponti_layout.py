"""Reference-canvas geometry for Bridge Builders.

Everything is laid out on the 1024x600 logical canvas (``PygameReferenceCanvas``
scales it to the display). The HUD bar sits beside -- never inside -- the
protected Home/Back region and holds progress and hint (right). The river
runs across the middle; the tray of planks lies along the bottom with the big
GO pill at its right end, so choosing planks and pressing GO is one compact
mouse-first cluster (ADR 0037 §4a), never a trip back to the top bar beside
Home.

One **unit** (one plank board) is ``UNIT`` logical pixels everywhere: on the
river, on the standing planks and on the tray tiles, so the child can compare
a plank with a gap by eye or by counting boards and dashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

from greia_platform.activity_controls import ControlLayout

if __package__:
    from .ponti_content import MAX_TRAY, Crossing, PieceKind
    from .ponti_model import BANK, Span, island_seat, spot_seat
else:
    from ponti_content import MAX_TRAY, Crossing, PieceKind
    from ponti_model import BANK, Span, island_seat, spot_seat

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
UNIT: Final = 60  # logical px per plank board
BANK_TOP: Final = 340  # the walking surface of banks, islands and pillars
WATER_TOP: Final = 424
GAP_CENTER_X: Final = 548
TRAY_HEIGHT: Final = 108
TRAY_PAD: Final = 26
TRAY_MIN_TILE: Final = 112
TRAY_GAP: Final = 14
CAST_HEIGHT: Final = 124
GO_WIDTH: Final = 190
GO_TRAY_GAP: Final = 24  # GO sits this far right of the last tray tile
GO_TRAY_INSET: Final = 10  # GO is a little shorter than the tray tiles
WOOD_THICKNESS: Final = 20
STONE_THICKNESS: Final = 30
PILLAR_DEPTH: Final = WATER_TOP + 34 - BANK_TOP  # pillar height (logical px)
HOME_OFFSET: Final = 104  # friend waits this far left of the river
SEAT_REACH: Final = 170  # how far above the bank a seat target reaches


def thickness(strong: bool) -> int:
    return STONE_THICKNESS if strong else WOOD_THICKNESS


@dataclass(frozen=True, slots=True)
class CrossingView:
    """Map one crossing's units to logical pixels."""

    crossing: Crossing

    @property
    def left_x(self) -> int:
        return int(round(GAP_CENTER_X - self.crossing.gap * UNIT / 2))

    @property
    def right_x(self) -> int:
        return self.x(self.crossing.gap)

    def x(self, units: float) -> int:
        return int(round(self.left_x + units * UNIT))

    @property
    def home_x(self) -> int:
        return self.left_x - HOME_OFFSET

    @property
    def picnic_x(self) -> int:
        return min(REFERENCE_WIDTH - 118, self.right_x + 128)

    @property
    def arrive_x(self) -> int:
        return self.picnic_x - 64

    def seat_x(self, seat: str) -> int:
        """The near edge (hinge) of a seat: where its plank stands."""

        crossing = self.crossing
        if seat == BANK:
            return self.left_x
        for index, (start, width) in enumerate(crossing.islands):
            if seat == island_seat(index):
                return self.x(start + width)
        for index, start in enumerate(crossing.spots):
            if seat == spot_seat(index):
                return self.x(start + 1)
        raise ValueError(f"unknown seat {seat!r}")

    def seat_rect(self, span: Span) -> pygame.Rect:
        """Pointer/focus target for a span: the air above its water."""

        left = self.x(span.start) - 26
        right = self.x(span.end) - 2
        return pygame.Rect(left, BANK_TOP - SEAT_REACH, max(60, right - left), SEAT_REACH + 26)

    def span_band(self, span: Span) -> pygame.Rect:
        """The line where a plank across ``span`` would lie (for glows)."""

        left = self.x(span.start)
        return pygame.Rect(left, BANK_TOP - 34, max(UNIT, self.x(span.end) - left), 46)

    def spot_rect(self, spot: int) -> pygame.Rect:
        start = self.crossing.spots[spot]
        left = self.x(start) - 8
        return pygame.Rect(left, BANK_TOP + 34, UNIT + 16, WATER_TOP + 44 - BANK_TOP - 34)

    def pillar_rect(self, spot: int) -> pygame.Rect:
        start = self.crossing.spots[spot]
        return pygame.Rect(self.x(start), BANK_TOP, UNIT, PILLAR_DEPTH)

    def island_rect(self, index: int) -> pygame.Rect:
        start, width = self.crossing.islands[index]
        return pygame.Rect(self.x(start), BANK_TOP, self.x(start + width) - self.x(start), REFERENCE_HEIGHT - BANK_TOP)


def tray_widths(crossing: Crossing) -> list[int]:
    widths = []
    for piece in crossing.pieces:
        if piece.kind is PieceKind.PILLAR:
            widths.append(TRAY_MIN_TILE)
        else:
            widths.append(max(TRAY_MIN_TILE, piece.length * UNIT + 2 * TRAY_PAD))
    return widths


@dataclass(frozen=True, slots=True)
class ScreenLayout:
    """Where the HUD bar, GO button and tray sit (logical px).

    ``go`` holds GO's size; its position comes from ``tray_rects`` (GO sits at
    the right end of the tray it confirms).
    """

    bar: pygame.Rect
    go: pygame.Rect
    tray_band: pygame.Rect
    protected: pygame.Rect

    @classmethod
    def build(cls, layout: ControlLayout) -> "ScreenLayout":
        bar_h = layout.control_height(60, maximum=80)
        bar = layout.top_bar(bar_h)
        tray_h = max(layout.control_height(TRAY_HEIGHT, maximum=TRAY_HEIGHT), TRAY_HEIGHT)
        tray_band = pygame.Rect(layout.margin, REFERENCE_HEIGHT - 8 - tray_h, REFERENCE_WIDTH - 2 * layout.margin, tray_h)
        go_h = max(bar_h, tray_h - 2 * GO_TRAY_INSET)
        go = pygame.Rect(0, 0, GO_WIDTH, go_h)
        go.midleft = (tray_band.right - GO_WIDTH, tray_band.centery)
        return cls(bar, go, tray_band, layout.protected)

    def tray_rects(self, crossing: Crossing, go_width: int | None = None) -> tuple[pygame.Rect, ...]:
        """Tray tiles, centred as one group with GO (``go_width``) at their right."""

        widths = tray_widths(crossing)[:MAX_TRAY]
        total = sum(widths) + TRAY_GAP * (len(widths) - 1)
        go_w = self.go.width if go_width is None else int(go_width)
        group = total + GO_TRAY_GAP + go_w
        band = self.tray_band
        x = band.centerx - group // 2
        x = max(band.left, min(x, band.right - group))
        rects = []
        for width in widths:
            rects.append(pygame.Rect(x, band.top, width, band.height))
            x += width + TRAY_GAP
        return tuple(rects)

    def go_rect(self, tiles: tuple[pygame.Rect, ...], go_width: int | None = None) -> pygame.Rect:
        """GO at the right end of ``tiles`` (vertically centred on the tray)."""

        go = self.go.copy()
        if go_width is not None:
            go.width = int(go_width)
        left = tiles[-1].right + GO_TRAY_GAP if tiles else self.tray_band.centerx - go.width // 2
        go.midleft = (min(left, self.tray_band.right - go.width), self.tray_band.centery)
        return go


__all__ = [
    "BANK_TOP",
    "CAST_HEIGHT",
    "CrossingView",
    "GAP_CENTER_X",
    "PILLAR_DEPTH",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STONE_THICKNESS",
    "ScreenLayout",
    "UNIT",
    "WATER_TOP",
    "WOOD_THICKNESS",
    "thickness",
    "tray_widths",
]
