"""Screen geometry for Leo's Post in 1024x600 logical pixels.

Every screen keeps the platform Home/Back region free: ``protected`` is the
chrome mapped into this logical space by ``ControlLayout.for_canvas`` (it is
largest at 480x320, where it reaches x 239 / y 87). Bars start right of it and
every content row starts below y 100. Rects are computed once per screen and
viewport, never per frame. Tray tiles stay >= 92 logical px so they remain a
40 px physical touch target at 480x320.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .postcard_content import CARD_ASPECT, POSTBOX_PAGE_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from postcard_content import CARD_ASPECT, POSTBOX_PAGE_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH

MARGIN: Final = 12
CONTENT_TOP: Final = 108
TRAY_TILE: Final = 92


def _card(left: int, top: int, height: int) -> pygame.Rect:
    return pygame.Rect(left, top, round(height * CARD_ASPECT), height)


@dataclass(frozen=True, slots=True)
class TopBar:
    """One row beside the protected chrome."""

    bar: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect, height: int) -> "TopBar":
        left = protected.right + 14
        return cls(pygame.Rect(left, MARGIN, REFERENCE_WIDTH - MARGIN - left, height))

    def left(self, index: int, size: int, gap: int = 12) -> pygame.Rect:
        return pygame.Rect(self.bar.left + index * (size + gap), self.bar.centery - size // 2, size, size)

    def right(self, index: int, size: int, gap: int = 12) -> pygame.Rect:
        """``index`` 0 is the right-most slot."""

        x = self.bar.right - (index + 1) * size - index * gap
        return pygame.Rect(x, self.bar.centery - size // 2, size, size)


def tray_row(count: int, tray: pygame.Rect, *, size: int = TRAY_TILE, gap: int = 10) -> tuple[pygame.Rect, ...]:
    """``count`` square tiles centred in the tray strip (shrunk to fit)."""

    room = tray.width - 24
    size = min(size, (room - gap * (count - 1)) // max(1, count))
    total = count * size + (count - 1) * gap
    left = tray.centerx - total // 2
    top = tray.centery - size // 2 - 2
    return tuple(pygame.Rect(left + index * (size + gap), top, size, size) for index in range(count))


@dataclass(frozen=True, slots=True)
class ComposerLayout:
    """Steps on top, the big card left, Leo + send + mailbox right, tray below."""

    top: TopBar
    steps: tuple[pygame.Rect, ...]
    card: pygame.Rect
    send: pygame.Rect
    mailbox: pygame.Rect
    host_midbottom: tuple[int, int]
    host_height: int
    tray: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "ComposerLayout":
        top = TopBar.build(protected, button)
        steps = tuple(top.left(index, button) for index in range(4))
        card = _card(24, CONTENT_TOP, 364)
        column = pygame.Rect(card.right + 18, CONTENT_TOP, REFERENCE_WIDTH - MARGIN - card.right - 18, card.height)
        send = pygame.Rect(0, 0, 132, 132)
        send.midtop = (column.centerx, column.top + 4)
        mailbox = pygame.Rect(0, 0, 112, 112)
        mailbox.bottomright = (column.right - 2, card.bottom)
        tray = pygame.Rect(MARGIN, card.bottom + 14, REFERENCE_WIDTH - 2 * MARGIN, REFERENCE_HEIGHT - MARGIN - card.bottom - 14)
        return cls(
            top=top,
            steps=steps,
            card=card,
            send=send,
            mailbox=mailbox,
            host_midbottom=(column.left + 92, card.bottom + 6),
            host_height=196,
            tray=tray,
        )

    def tiles(self, count: int) -> tuple[pygame.Rect, ...]:
        return tray_row(count, self.tray)


@dataclass(frozen=True, slots=True)
class PostboxLayout:
    """3x2 big postcards, a count chip, page arrows and a delete tile."""

    top: TopBar
    new_card: pygame.Rect
    chip: pygame.Rect
    cards: tuple[pygame.Rect, ...]
    previous: pygame.Rect
    next: pygame.Rect
    delete: pygame.Rect
    dots_centre: tuple[int, int]

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "PostboxLayout":
        top = TopBar.build(protected, button)
        new_card = top.right(0, button)
        chip = pygame.Rect(top.bar.left, top.bar.centery - button // 2 + 8, 170, button - 16)
        gap_x, gap_y = 30, 16
        width = 300
        height = round(width / CARD_ASPECT)
        left = (REFERENCE_WIDTH - 3 * width - 2 * gap_x) // 2
        cards = tuple(
            pygame.Rect(left + col * (width + gap_x), CONTENT_TOP + row * (height + gap_y), width, height)
            for row in range(2)
            for col in range(3)
        )[:POSTBOX_PAGE_SIZE]
        strip_top = cards[-1].bottom + 14
        strip_h = REFERENCE_HEIGHT - MARGIN - strip_top
        size = min(92, strip_h)
        y = strip_top + (strip_h - size) // 2
        previous = pygame.Rect(24, y, 112, size)
        following = pygame.Rect(REFERENCE_WIDTH - 24 - 112, y, 112, size)
        delete = pygame.Rect(0, 0, size, size)
        delete.midright = (following.left - 60, following.centery)
        return cls(
            top=top,
            new_card=new_card,
            chip=chip,
            cards=cards,
            previous=previous,
            next=following,
            delete=delete,
            dots_centre=((previous.right + delete.left) // 2, previous.centery),
        )


@dataclass(frozen=True, slots=True)
class CardViewLayout:
    """One sent postcard, big, with its friend beside it."""

    top: TopBar
    back: pygame.Rect
    flip: pygame.Rect
    share: pygame.Rect
    delete: pygame.Rect
    card: pygame.Rect
    friend_midbottom: tuple[int, int]
    friend_height: int

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "CardViewLayout":
        top = TopBar.build(protected, button)
        card = _card(24, CONTENT_TOP + 4, 420)
        return cls(
            top=top,
            back=top.left(0, button),
            flip=top.right(2, button),
            share=top.right(1, button),
            delete=top.right(0, button),
            card=card,
            friend_midbottom=((card.right + REFERENCE_WIDTH - MARGIN) // 2, card.bottom + 8),
            friend_height=250,
        )


@dataclass(frozen=True, slots=True)
class DeliveredLayout:
    """The friend receives the postcard: card left, friend right, two choices."""

    card: pygame.Rect
    friend_midbottom: tuple[int, int]
    friend_height: int
    new_card: pygame.Rect
    mailbox: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "DeliveredLayout":
        card = _card(52, max(CONTENT_TOP + 8, protected.bottom + 24), 300)
        size = max(button, 104)
        new_card = pygame.Rect(0, 0, size + 24, size)
        mailbox = pygame.Rect(0, 0, size, size)
        y = REFERENCE_HEIGHT - MARGIN - 8 - size
        new_card.topleft = (card.centerx + 12, y)
        mailbox.topright = (card.centerx - 12, y)
        return cls(
            card=card,
            friend_midbottom=(card.right + (REFERENCE_WIDTH - card.right) // 2, REFERENCE_HEIGHT - 40),
            friend_height=256,
            new_card=new_card,
            mailbox=mailbox,
        )


@dataclass(frozen=True, slots=True)
class SheetLayout:
    """A centred modal panel: preview on top, two choices below."""

    panel: pygame.Rect
    preview: pygame.Rect
    symbol: tuple[int, int]
    left: pygame.Rect
    right: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect) -> "SheetLayout":
        top = max(CONTENT_TOP - 8, protected.bottom + 10)
        height = min(440, REFERENCE_HEIGHT - MARGIN - top)
        panel = pygame.Rect(0, 0, 560, height)
        panel.midtop = (REFERENCE_WIDTH // 2, top)
        preview = _card(0, 0, height - 20 - 104 - 16 - 20 - 56)
        preview.midtop = (panel.centerx, panel.top + 20)
        button = 104
        y = panel.bottom - 20 - button
        left = pygame.Rect(panel.centerx - 24 - button, y, button, button)
        right = pygame.Rect(panel.centerx + 24, y, button, button)
        return cls(panel, preview, (panel.centerx, preview.bottom + 32), left, right)


__all__ = [
    "CONTENT_TOP",
    "CardViewLayout",
    "ComposerLayout",
    "DeliveredLayout",
    "PostboxLayout",
    "SheetLayout",
    "TRAY_TILE",
    "TopBar",
    "tray_row",
]
