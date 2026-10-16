"""Scene geometry of The Big Seasons Tree in 1024x600 logical pixels (pure data).

The big tree stands left of centre, the meadow spot on its left, the woodland
friend's spot on its right and Tito beside it; the weather fills the sky.
Picture cards (and the season tiles) sit in one row along the bottom, under
the tree and clear of Tito. The top band stays free for the kit bar and the
platform's protected Home region (ADR 0019).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .tree_content import REFERENCE_HEIGHT, Slot
else:
    from tree_content import REFERENCE_HEIGHT, Slot

# The tree art (432x432 canvas) stands on y = 478 with its trunk at x = 470.
TREE_SIZE: Final = 432
TREE_RECT: Final = pygame.Rect(254, 66, TREE_SIZE, TREE_SIZE)
TREE_TAP_RECT: Final = pygame.Rect(316, 104, 314, 374)
CROWN_CENTER: Final = (470, 218)
GROUND_Y: Final = 480

# Shared props are drawn on a 256 canvas whose base is y = 232 (SVG rules),
# so their drawn rect sits a little below the ground line they stand on.
PROP_BASE_FRACTION: Final = 232 / 256

GROUND_ANCHOR: Final = (172, GROUND_Y)
ANIMAL_ANCHOR: Final = (668, GROUND_Y + 2)
ANIMAL_SIZE: Final = 132
FLYING_LIFT: Final = 70  # butterflies hover above their spot

TITO_HEIGHT: Final = 184
TITO_MIDBOTTOM: Final = (862, GROUND_Y + 8)
TITO_TAP_RECT: Final = pygame.Rect(TITO_MIDBOTTOM[0] - 80, TITO_MIDBOTTOM[1] - 170, 160, 170)

SUN_CENTER: Final = (902, 150)
SUN_SIZE: Final = 150
CLOUDS: Final[tuple[tuple[int, int, int], ...]] = ((196, 156, 236), (790, 124, 214))  # centre x, y, width
SKY_RECT: Final = pygame.Rect(0, 40, 1024, GROUND_Y - 40)

# Ground pieces: (dx, dy, size) per item; a single piece by default.
GROUND_DEFAULT: Final[tuple[tuple[int, int, int], ...]] = ((0, 0, 150),)
GROUND_PIECES: Final[dict[str, tuple[tuple[int, int, int], ...]]] = {
    "flowers": ((-46, -2, 104), (14, 6, 124), (66, -4, 96)),
    "strawberries": ((-36, 0, 96), (36, 6, 108)),
    "mushrooms": ((-32, 0, 118), (44, 6, 88)),
    "snowman": ((0, 4, 180),),
    "pumpkin": ((0, 2, 160),),
}

# Picture cards and season tiles: one row along the bottom margin.
ROW_CENTER_X: Final = 466
CARD_SIZE: Final = (132, 108)
TILE_SIZE: Final = (138, 112)
ROW_GAP: Final = 18
ROW_BOTTOM: Final = REFERENCE_HEIGHT - 10
CARD_ICON: Final = 82
TILE_ICON: Final = 66
BANNER_HEIGHT: Final = 70
BANNER_WIDTH: Final = 460
BANNER_ICON: Final = 52


def row_rects(count: int, size: tuple[int, int]) -> tuple[pygame.Rect, ...]:
    """``count`` equal rects centred on ``ROW_CENTER_X`` above ``ROW_BOTTOM``."""

    width, height = size
    total = count * width + (count - 1) * ROW_GAP
    left = ROW_CENTER_X - total // 2
    return tuple(
        pygame.Rect(left + index * (width + ROW_GAP), ROW_BOTTOM - height, width, height)
        for index in range(count)
    )


@dataclass(frozen=True, slots=True)
class SlotSpot:
    """Where a slot's piece lives: FX/hint point and the hint glow footprint."""

    point: tuple[int, int]
    glow: pygame.Rect


SLOT_SPOTS: Final[dict[Slot, SlotSpot]] = {
    Slot.TREE: SlotSpot(CROWN_CENTER, pygame.Rect(296, 86, 348, 250)),
    # The whole sky glows (never just where the sun would go: that would hint).
    Slot.SKY: SlotSpot((560, 150), pygame.Rect(250, 84, 718, 176)),
    Slot.GROUND: SlotSpot((GROUND_ANCHOR[0], GROUND_Y - 60), pygame.Rect(GROUND_ANCHOR[0] - 104, GROUND_Y - 38, 208, 64)),
    Slot.ANIMAL: SlotSpot((ANIMAL_ANCHOR[0], GROUND_Y - 60), pygame.Rect(ANIMAL_ANCHOR[0] - 84, GROUND_Y - 34, 168, 58)),
    Slot.CLOTHES: SlotSpot((TITO_MIDBOTTOM[0], TITO_MIDBOTTOM[1] - 110), pygame.Rect(TITO_MIDBOTTOM[0] - 104, TITO_MIDBOTTOM[1] - 196, 208, 200)),
}


def prop_rect(anchor: tuple[int, int], size: int) -> pygame.Rect:
    """Rect of a 256-canvas prop drawn at ``size`` standing on ``anchor``."""

    rect = pygame.Rect(0, 0, size, size)
    rect.midbottom = (anchor[0], anchor[1] + int(round(size * (1.0 - PROP_BASE_FRACTION))))
    return rect


__all__ = [
    "ANIMAL_ANCHOR",
    "ANIMAL_SIZE",
    "BANNER_HEIGHT",
    "BANNER_ICON",
    "BANNER_WIDTH",
    "CARD_ICON",
    "CARD_SIZE",
    "CLOUDS",
    "CROWN_CENTER",
    "FLYING_LIFT",
    "GROUND_ANCHOR",
    "GROUND_DEFAULT",
    "GROUND_PIECES",
    "GROUND_Y",
    "ROW_BOTTOM",
    "SKY_RECT",
    "SLOT_SPOTS",
    "SUN_CENTER",
    "SUN_SIZE",
    "SlotSpot",
    "TILE_ICON",
    "TILE_SIZE",
    "TITO_HEIGHT",
    "TITO_MIDBOTTOM",
    "TITO_TAP_RECT",
    "TREE_RECT",
    "TREE_SIZE",
    "TREE_TAP_RECT",
    "prop_rect",
    "row_rects",
]
