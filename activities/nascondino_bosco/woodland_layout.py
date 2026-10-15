"""Geometry for Woodland Hide & Seek in 1024x600 logical pixels (pure).

``SpotGeometry`` turns one hiding anchor into the rectangles the renderer and
the controls need: where the prop is drawn, the row a peeking friend emerges
from (``top_y``), the row below which a friend is clipped (``cut_y``, always
inside the covered part of the prop, so a cut edge never shows), the friend's
size and the touch target (never smaller than ``MIN_TARGET``).

``peek_rect`` places a friend for a given visibility: 0 = fully hidden below
``cut_y``, 1 = peeking out by ``rise`` of its head height. Friends are drawn
with their full library art and clipped at ``cut_y``, so any amount of peek
reads as "the rest of me is behind/under/in this" without a cut edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .woodland_content import REFERENCE_HEIGHT, Anchor
else:
    from woodland_content import REFERENCE_HEIGHT, Anchor

FRIEND_BASE_SIZE: Final = 150
MIN_TARGET: Final = 112
HEAD_FRACTION: Final = 0.46  # "head" height of a friend as a fraction of its art size
ART_BASE_FRACTION: Final = 232 / 256  # props stand on y = H - 24 (SVG rules)
LILLI_HEIGHT: Final = 168
LILLI_MIDBOTTOM: Final[tuple[int, int]] = (96, REFERENCE_HEIGHT - 4)
FRIEND_SLOT_SIZE: Final = 78
# Friends already found gather around Lilli in the bottom-left corner.
FRIEND_SLOTS: Final[tuple[tuple[int, int], ...]] = ((198, 597), (258, 590), (166, 552), (230, 548))


@dataclass(frozen=True, slots=True)
class SpotGeometry:
    anchor: Anchor
    prop_rect: pygame.Rect | None
    top_y: int
    cut_y: int
    center_x: int
    friend_size: int
    hit_rect: pygame.Rect

    @classmethod
    def build(cls, anchor: Anchor, max_rise: float = 0.9) -> "SpotGeometry":
        kind = anchor.kind
        size = int(round(FRIEND_BASE_SIZE * anchor.depth))
        if kind.asset_id is None and kind.art_file is None:
            # Water: friends rise out of the surface line (the anchor row).
            prop_rect = None
            top_y = cut_y = anchor.y
            body = pygame.Rect(0, 0, int(kind.width * anchor.depth), int(size * 0.34))
            body.midtop = (anchor.x, anchor.y - 6)
        else:
            width = int(round(kind.width * anchor.depth))
            height = int(round(width * kind.canvas[1] / kind.canvas[0]))
            bottom = anchor.y + int(round(height * (1.0 - ART_BASE_FRACTION)))
            prop_rect = pygame.Rect(0, 0, width, height)
            prop_rect.midbottom = (anchor.x, bottom)
            top_y = prop_rect.top + int(round(kind.top * height))
            cut_y = prop_rect.top + int(round(kind.cut * height))
            body = pygame.Rect(prop_rect.left, top_y, width, anchor.y - top_y)
        head = int(size * HEAD_FRACTION * max_rise)
        hit = body.union(pygame.Rect(anchor.x - size // 2, top_y - head, size, head))
        if hit.width < MIN_TARGET:
            hit.inflate_ip(MIN_TARGET - hit.width, 0)
        if hit.height < MIN_TARGET:
            grow = MIN_TARGET - hit.height
            hit.height = MIN_TARGET
            hit.top -= grow
        return cls(anchor, prop_rect, top_y, cut_y, anchor.x, size, hit)

    def peek_rect(self, top_fraction: float, rise: float, visibility: float) -> pygame.Rect:
        """Friend sprite rect for this visibility (see module docstring)."""

        size = self.friend_size
        head = HEAD_FRACTION * size
        hidden_top = self.cut_y + 4
        shown_top = self.top_y - rise * head
        v = max(0.0, min(1.0, visibility))
        content_top = hidden_top + (shown_top - hidden_top) * v
        return pygame.Rect(
            self.center_x - size // 2,
            int(round(content_top - top_fraction * size)),
            size,
            size,
        )

    def clip_rect(self, surface_width: int) -> pygame.Rect:
        """Everything a hiding friend may cover: above ``cut_y``, full width."""

        return pygame.Rect(0, 0, surface_width, max(0, self.cut_y))

    @property
    def peek_point(self) -> tuple[int, int]:
        """Where FX for this place appear (just above the hiding line)."""

        return (self.center_x, self.top_y - int(self.friend_size * 0.18))


__all__ = [
    "FRIEND_SLOTS",
    "FRIEND_SLOT_SIZE",
    "LILLI_HEIGHT",
    "LILLI_MIDBOTTOM",
    "MIN_TARGET",
    "SpotGeometry",
]
