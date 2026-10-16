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
PEDAL_SIZE: Final = 132
PEDAL_MARGIN: Final = 22
PEDAL_HIT_SLOP: Final = 26
BRAKE_RECT: Final = pygame.Rect(PEDAL_MARGIN, REFERENCE_HEIGHT - PEDAL_MARGIN - PEDAL_SIZE, PEDAL_SIZE, PEDAL_SIZE)
GO_RECT: Final = pygame.Rect(
    REFERENCE_WIDTH - PEDAL_MARGIN - PEDAL_SIZE, REFERENCE_HEIGHT - PEDAL_MARGIN - PEDAL_SIZE, PEDAL_SIZE, PEDAL_SIZE
)

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


def pedal_hit(rect: pygame.Rect) -> pygame.Rect:
    return rect.inflate(2 * PEDAL_HIT_SLOP, 2 * PEDAL_HIT_SLOP)


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
    "LISTEN_SIZE",
    "PEDAL_SIZE",
    "PICNIC_OFFSET",
    "ROAD_WIDTH",
    "STARS_WIDTH",
    "TOP_BAR_HEIGHT",
    "pedal_hit",
]
