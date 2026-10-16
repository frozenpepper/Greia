"""Scene geometry of Cloud Bedtime in 1024x600 logical pixels (pure data).

Three little clouds float over the night hills with their dream bubbles above
them; the quilt tray lies along the bottom with sleepy Momo beside it. The top
band stays free for the kit progress dots and the platform's protected Home
region (ADR 0019): the leftmost dream bubble starts below the largest mapped
protected rect (480x320 maps it to roughly 240x88 logical pixels).
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .cloud_content import MAX_TRAY
else:
    from cloud_content import MAX_TRAY

# Clouds and quilts share one 256 art frame (assets/source/cloud_*.svg and
# blanket_tucked_*.svg), drawn at CLOUD_SIZE.
CLOUD_SIZE: Final = 220
CLOUD_TOP: Final = 182
CLOUD_CENTERS_X: Final[tuple[int, ...]] = (206, 486, 766)
ART_FRAME: Final = 256

BUBBLE_SIZE: Final = 168
BUBBLE_TOP: Final = 78
# Inner area of the bubble art (256 frame) where the dream is drawn.
BUBBLE_INNER: Final = (34, 44, 192, 128)

TRAY_TOP: Final = 452
TRAY_CENTER_X: Final = 440
TILE_SIZE: Final = (154, 106)
TILE_GAP: Final = 14
TRAY_PANEL: Final = pygame.Rect(20, 440, 840, 152)
# Flat quilt art crop (256 frame) and the stitched patch where stars sit.
QUILT_CROP: Final = pygame.Rect(10, 68, 236, 128)
QUILT_PATCH: Final = pygame.Rect(28, 111, 200, 58)
TILE_QUILT_WIDTH: Final = 146

MOMO_HEIGHT: Final = 168
MOMO_MIDBOTTOM: Final = (938, 592)
MOMO_TAP_RECT: Final = pygame.Rect(MOMO_MIDBOTTOM[0] - 76, MOMO_MIDBOTTOM[1] - 150, 152, 150)

MOON_CENTER: Final = (900, 100)
MOON_TAP_RECT: Final = pygame.Rect(840, 40, 120, 120)

PROGRESS_HEIGHT: Final = 44


def cloud_box(index: int) -> pygame.Rect:
    """The cloud's 256-frame art box (also used for its tucked quilt)."""

    rect = pygame.Rect(0, 0, CLOUD_SIZE, CLOUD_SIZE)
    rect.midtop = (CLOUD_CENTERS_X[index], CLOUD_TOP)
    return rect


def cloud_body(index: int) -> pygame.Rect:
    """The visible cloud (focus ring and the core of its hit area)."""

    box = cloud_box(index)
    return pygame.Rect(box.x + 14, box.y + 42, box.width - 28, box.height - 60)


def bubble_box(index: int) -> pygame.Rect:
    rect = pygame.Rect(0, 0, BUBBLE_SIZE, BUBBLE_SIZE)
    rect.midtop = (CLOUD_CENTERS_X[index], BUBBLE_TOP)
    return rect


def cloud_hit(index: int) -> pygame.Rect:
    """Where a tap or a dropped quilt counts for this cloud (cloud + its dream)."""

    body = cloud_body(index)
    bubble = bubble_box(index)
    top = bubble.y + 12
    return pygame.Rect(body.x - 6, top, body.width + 12, body.bottom + 30 - top)


def tile_rects(count: int) -> tuple[pygame.Rect, ...]:
    count = max(0, min(MAX_TRAY, count))
    width, height = TILE_SIZE
    total = count * width + max(0, count - 1) * TILE_GAP
    left = TRAY_CENTER_X - total // 2
    return tuple(pygame.Rect(left + index * (width + TILE_GAP), TRAY_TOP, width, height) for index in range(count))


__all__ = [
    "ART_FRAME",
    "BUBBLE_INNER",
    "BUBBLE_SIZE",
    "BUBBLE_TOP",
    "CLOUD_CENTERS_X",
    "CLOUD_SIZE",
    "CLOUD_TOP",
    "MOMO_HEIGHT",
    "MOMO_MIDBOTTOM",
    "MOMO_TAP_RECT",
    "MOON_CENTER",
    "MOON_TAP_RECT",
    "PROGRESS_HEIGHT",
    "QUILT_CROP",
    "QUILT_PATCH",
    "TILE_GAP",
    "TILE_QUILT_WIDTH",
    "TILE_SIZE",
    "TRAY_PANEL",
    "TRAY_TOP",
    "bubble_box",
    "cloud_body",
    "cloud_box",
    "cloud_hit",
    "tile_rects",
]
