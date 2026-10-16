"""Screen geometry of Colline Allegre in 1024x600 logical pixels (pure data).

The camera keeps Tito's buggy a third of the way in from the left, so the
child always sees the road ahead. The top band holds, left to right after
the platform's protected Home region (ADR 0019): the course dots, the
course road (start flag -> buggy -> finish + friend), the three star slots
and the listen button. The two big pedals sit in the bottom corners: BRAKE
left, GO right. At 480x320 the protected region maps to about 240x88
logical pixels; the top bar starts after it (``ControlLayout.top_bar``).
"""

from __future__ import annotations

import math
from typing import Final

import pygame

if __package__:
    from .colline_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from colline_content import REFERENCE_HEIGHT, REFERENCE_WIDTH

# Camera: the buggy's chassis centre sits here on screen (y is smoothed).
CAMERA_ANCHOR_X: Final = 300
CAMERA_ANCHOR_Y: Final = 372
CAMERA_Y_MIN: Final = -150
CAMERA_Y_MAX: Final = 70
CAMERA_Y_FOLLOW: Final = 4.0  # 1/s

# Pedals (round kit buttons; the hit area is a little larger than the art).
# They are placed by ``ControlLayout.cluster`` (``CollineControls.place``);
# the rects below are the 1024x600 result, kept for tools and docs.
PEDAL_SIZE: Final = 132
PEDAL_MARGIN: Final = 22
PEDAL_GAP: Final = 16
PEDAL_HIT_SLOP: Final = 26
KEY_HINT_KEY: Final = 34  # keycap height of the keyboard hint (legible for 4-7)
KEY_HINT_MIN_PHYSICAL: Final = 28  # keycaps never drawn smaller than this on screen
GO_RECT: Final = pygame.Rect(
    REFERENCE_WIDTH - PEDAL_MARGIN - PEDAL_SIZE, REFERENCE_HEIGHT - PEDAL_MARGIN - PEDAL_SIZE, PEDAL_SIZE, PEDAL_SIZE
)
BRAKE_RECT: Final = GO_RECT.move(-(PEDAL_SIZE + PEDAL_GAP), 0)

TOP_BAR_HEIGHT: Final = 56
LISTEN_SIZE: Final = 60
ROAD_WIDTH: Final = 330
STARS_WIDTH: Final = 150

# Terrain is pre-rendered in vertical strips of this width.
CHUNK_WIDTH: Final = 256
DECOR_HEADROOM: Final = 190  # px above the highest ground a chunk keeps for trees and signs

# Finish scene, relative to the finish line (world px).
PICNIC_OFFSET: Final = 560
FRIEND_OFFSET: Final = 740
FRIEND_HEIGHT: Final = 150


def key_hint_key(scale: float) -> int:
    """Logical keycap size: ``KEY_HINT_KEY``, raised so small screens keep it legible."""

    return max(KEY_HINT_KEY, math.ceil(KEY_HINT_MIN_PHYSICAL / max(0.01, scale)))


def pedal_hit(rect: pygame.Rect) -> pygame.Rect:
    return rect.inflate(2 * PEDAL_HIT_SLOP, 2 * PEDAL_HIT_SLOP)


def pedal_at(point: tuple[int, int], go: pygame.Rect, brake: pygame.Rect) -> str | None:
    """``"go"``/``"brake"`` for a press on (or just around) a pedal, else None.

    The pedals sit side by side, so their slop areas overlap in the gap: the
    nearer pedal centre wins there.
    """

    hits = [(name, rect) for name, rect in (("go", go), ("brake", brake)) if pedal_hit(rect).collidepoint(point)]
    if not hits:
        return None
    x, y = point
    return min(hits, key=lambda item: (item[1].centerx - x) ** 2 + (item[1].centery - y) ** 2)[0]


__all__ = [
    "BRAKE_RECT",
    "CAMERA_ANCHOR_X",
    "CAMERA_ANCHOR_Y",
    "CAMERA_Y_FOLLOW",
    "CAMERA_Y_MAX",
    "CAMERA_Y_MIN",
    "CHUNK_WIDTH",
    "DECOR_HEADROOM",
    "FRIEND_HEIGHT",
    "FRIEND_OFFSET",
    "GO_RECT",
    "KEY_HINT_KEY",
    "LISTEN_SIZE",
    "PEDAL_GAP",
    "PEDAL_MARGIN",
    "PEDAL_SIZE",
    "PICNIC_OFFSET",
    "ROAD_WIDTH",
    "STARS_WIDTH",
    "TOP_BAR_HEIGHT",
    "key_hint_key",
    "pedal_at",
    "pedal_hit",
]
