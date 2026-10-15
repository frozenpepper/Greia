"""Screen geometry for Stories of My Voice in 1024x600 logical pixels.

Every screen keeps the top-left corner free for the platform Home/Back chrome
(``ControlLayout.protected`` is mapped into this logical space, and is largest
at 480x320). Leo stands on the lower left; cards and controls use the rest.
All rects are computed once per screen/viewport, never per frame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .voice_content import CARD_SPACE, REFERENCE_HEIGHT, REFERENCE_WIDTH, SHELF_PAGE_SIZE
else:
    from voice_content import CARD_SPACE, REFERENCE_HEIGHT, REFERENCE_WIDTH, SHELF_PAGE_SIZE

HOST_MIDBOTTOM: Final[tuple[int, int]] = (112, 590)
HOST_HEIGHT: Final = 196
STAGE_LEFT: Final = 214  # content starts right of Leo
MARGIN: Final = 12


def _card_size(width: int) -> tuple[int, int]:
    return width, round(width * CARD_SPACE[1] / CARD_SPACE[0])


def _row(count: int, width: int, gap: int, top: int, centre_x: int) -> tuple[pygame.Rect, ...]:
    _, height = _card_size(width)
    total = count * width + (count - 1) * gap
    left = centre_x - total // 2
    return tuple(pygame.Rect(left + index * (width + gap), top, width, height) for index in range(count))


def _clear_top(protected: pygame.Rect) -> int:
    """First y below the protected chrome (and below a top bar beside it)."""

    return max(protected.bottom + 10, 92)


@dataclass(frozen=True, slots=True)
class TopBar:
    """One row beside the protected chrome, right-aligned buttons."""

    bar: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect, height: int) -> "TopBar":
        left = protected.right + 14
        return cls(pygame.Rect(left, MARGIN, REFERENCE_WIDTH - MARGIN - left, height))

    def right(self, index: int, size: int, gap: int = 12) -> pygame.Rect:
        """``index`` 0 is the right-most button."""

        x = self.bar.right - (index + 1) * size - index * gap
        return pygame.Rect(x, self.bar.centery - size // 2, size, size)


@dataclass(frozen=True, slots=True)
class PickerLayout:
    """3x2 tiles: five stories + the My-stories shelf tile."""

    tiles: tuple[pygame.Rect, ...]
    top: TopBar

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "PickerLayout":
        top = TopBar.build(protected, button)
        tile_w, tile_h, gap = 240, 214, 22
        first = max(_clear_top(protected), top.bar.bottom + 8)
        rows = (first, first + tile_h + 18)
        total = 3 * tile_w + 2 * gap
        left = (STAGE_LEFT + REFERENCE_WIDTH - MARGIN) // 2 - total // 2
        tiles = tuple(
            pygame.Rect(left + column * (tile_w + gap), rows[row], tile_w, tile_h)
            for row in range(2)
            for column in range(3)
        )
        return cls(tiles, top)


@dataclass(frozen=True, slots=True)
class OrderLayout:
    """Numbered slots on top, the shuffled tray below, hint button top right."""

    slots: tuple[pygame.Rect, ...]
    tray: tuple[pygame.Rect, ...]
    board: pygame.Rect
    top: TopBar

    @classmethod
    def build(cls, count: int, protected: pygame.Rect, *, button: int) -> "OrderLayout":
        top = TopBar.build(protected, button)
        width = 176 if count >= 4 else 222
        gap = 20 if count >= 4 else 28
        centre = (STAGE_LEFT + REFERENCE_WIDTH - MARGIN) // 2
        slot_top = max(_clear_top(protected), top.bar.bottom + 14)
        slots = _row(count, width, gap, slot_top, centre)
        tray_top = slots[0].bottom + 72
        tray = _row(count, width, gap, tray_top, centre)
        board = pygame.Rect(slots[0].left - 18, slots[0].top - 14, slots[-1].right - slots[0].left + 36, slots[0].height + 28)
        return cls(slots, tray, board, top)


@dataclass(frozen=True, slots=True)
class TellLayout:
    """One big card, the microphone column on its right, dots + arrows below."""

    card: pygame.Rect
    mic: pygame.Rect
    play: pygame.Rect
    redo: pygame.Rect
    previous: pygame.Rect
    following: pygame.Rect
    dots: pygame.Rect
    top: TopBar

    @classmethod
    def build(cls, count: int, protected: pygame.Rect, *, button: int) -> "TellLayout":
        top = TopBar.build(protected, button)
        card_top = max(_clear_top(protected), top.bar.bottom + 10)
        card_h = min(372, REFERENCE_HEIGHT - card_top - 104)
        width, height = round(card_h * CARD_SPACE[0] / CARD_SPACE[1]), card_h
        card = pygame.Rect(236, card_top, width, height)
        column_x = (card.right + REFERENCE_WIDTH - MARGIN) // 2
        mic = pygame.Rect(0, 0, 148, 156)
        mic.center = (column_x, card.top + 112)
        small = 96
        play = pygame.Rect(column_x - small - 6, mic.bottom + 30, small, small + 6)
        redo = pygame.Rect(column_x + 6, mic.bottom + 30, small, small + 6)
        row_y = card.bottom + 14
        arrow = 86
        dots_h = 40
        from_dots = max(120, int(count * dots_h * 0.62 + (count - 1) * dots_h * 0.22 + dots_h * 0.5))
        dots = pygame.Rect(card.centerx - from_dots // 2, row_y + (arrow - dots_h) // 2, from_dots, dots_h)
        previous = pygame.Rect(dots.left - 28 - arrow, row_y, arrow, arrow + 4)
        following = pygame.Rect(dots.right + 28, row_y - 6, arrow + 16, arrow + 10)
        return cls(card, mic, play, redo, previous, following, dots, top)


@dataclass(frozen=True, slots=True)
class WatchLayout:
    """The slideshow: a large card, progress dots and the side actions."""

    card: pygame.Rect
    dots: pygame.Rect
    replay: pygame.Rect
    share: pygame.Rect
    top: TopBar

    @classmethod
    def build(cls, count: int, protected: pygame.Rect, *, button: int) -> "WatchLayout":
        top = TopBar.build(protected, button)
        card_top = max(_clear_top(protected), top.bar.bottom + 10)
        card_h = min(408, REFERENCE_HEIGHT - card_top - 76)
        card = pygame.Rect(0, card_top, round(card_h * CARD_SPACE[0] / CARD_SPACE[1]), card_h)
        card.centerx = (STAGE_LEFT + 40 + 868) // 2
        dots_h = 40
        width = max(120, int(count * dots_h * 0.62 + (count - 1) * dots_h * 0.22 + dots_h * 0.5))
        dots = pygame.Rect(card.centerx - width // 2, card.bottom + 18, width, dots_h)
        column_x = (card.right + REFERENCE_WIDTH - MARGIN) // 2
        replay = pygame.Rect(0, 0, 96, 102)
        replay.center = (column_x, card.centery - 60)
        share = pygame.Rect(0, 0, 96, 102)
        share.center = (column_x, card.centery + 70)
        return cls(card, dots, replay, share, top)


@dataclass(frozen=True, slots=True)
class ShelfLayout:
    """Paged 3x2 shelf of saved stories with page arrows and card actions."""

    cards: tuple[pygame.Rect, ...]
    previous: pygame.Rect
    following: pygame.Rect
    play: pygame.Rect
    share: pygame.Rect
    delete: pygame.Rect
    meter: pygame.Rect
    empty: pygame.Rect
    top: TopBar

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "ShelfLayout":
        top = TopBar.build(protected, button)
        width, gap_x, gap_y = 214, 30, 24
        _, height = _card_size(width)
        first = max(_clear_top(protected), top.bar.bottom + 14)
        total = 3 * width + 2 * gap_x
        left = (STAGE_LEFT + REFERENCE_WIDTH - MARGIN) // 2 - total // 2
        cards = tuple(
            pygame.Rect(left + column * (width + gap_x), first + row * (height + gap_y), width, height)
            for row in range(SHELF_PAGE_SIZE // 3)
            for column in range(3)
        )
        bottom = REFERENCE_HEIGHT - MARGIN - 78
        previous = pygame.Rect(left, bottom, 84, 76)
        following = pygame.Rect(left + total - 84, bottom, 84, 76)
        action = 84
        centre = left + total // 2
        play = pygame.Rect(centre - action // 2 - action - 16, bottom, action, action)
        share = pygame.Rect(centre - action // 2, bottom, action, action)
        delete = pygame.Rect(centre + action // 2 + 16, bottom, action, action)
        meter = pygame.Rect(top.bar.left, top.bar.top + 6, 168, top.bar.height - 12)
        empty = pygame.Rect(0, 0, 360, 260)
        empty.center = (centre, first + 150)
        return cls(cards, previous, following, play, share, delete, meter, empty, top)


@dataclass(frozen=True, slots=True)
class SheetLayout:
    """A centred modal panel with a preview and two big choices."""

    panel: pygame.Rect
    preview: pygame.Rect
    left: pygame.Rect
    right: pygame.Rect

    @classmethod
    def build(cls) -> "SheetLayout":
        panel = pygame.Rect(0, 0, 560, 380)
        panel.center = (REFERENCE_WIDTH // 2 + 60, REFERENCE_HEIGHT // 2 + 20)
        preview = pygame.Rect(0, 0, 240, 180)
        preview.midtop = (panel.centerx, panel.top + 30)
        size = 112
        left = pygame.Rect(panel.centerx - 40 - size, panel.bottom - 30 - size, size, size)
        right = pygame.Rect(panel.centerx + 40, panel.bottom - 30 - size, size, size)
        return cls(panel, preview, left, right)


__all__ = [
    "HOST_HEIGHT",
    "HOST_MIDBOTTOM",
    "OrderLayout",
    "PickerLayout",
    "SheetLayout",
    "ShelfLayout",
    "TellLayout",
    "TopBar",
    "WatchLayout",
]
