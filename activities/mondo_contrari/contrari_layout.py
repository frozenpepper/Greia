"""Scene geometry for Mondo Contrari in 1024x600 logical pixels.

Flash stands on the lawn at the left; every pair scene lives in the stage to
his right (x >= 250) and below the top control bar, so nothing is drawn under
the protected Home/Back corner or clipped by the bar. Choice target rects are
generous (pre-reader fingers) and never overlap each other.
"""

from __future__ import annotations

from typing import Final

import pygame

# Flash (host + feedback cast) on the lawn, feet midpoint.
FLASH_MIDBOTTOM: Final[tuple[int, int]] = (122, 590)
FLASH_HEIGHT: Final[int] = 210

STAGE_LEFT: Final[int] = 250
GROUND_Y: Final[int] = 586

# -- up / down: a balloon between the cloud (above) and the flowers (below) --
BALLOON_SIZE: Final[int] = 214
BALLOON_X: Final[int] = 640
BALLOON_TOP_NEUTRAL: Final[int] = 220
BALLOON_TOP_UP: Final[int] = 86
BALLOON_TOP_DOWN: Final[int] = 384
CLOUD_CENTER: Final[tuple[int, int]] = (BALLOON_X + 20, 150)
CLOUD_SIZE: Final[int] = 280
FLOWER_SPOTS: Final[tuple[tuple[int, int], ...]] = ((560, 590), (640, 598), (720, 590))
FLOWER_SIZE: Final[int] = 92
SKY_TARGET: Final[pygame.Rect] = pygame.Rect(BALLOON_X - 190, 84, 380, 136)
GRASS_TARGET: Final[pygame.Rect] = pygame.Rect(BALLOON_X - 190, 474, 380, 122)

# -- in / out: a cardboard box and the kitten's play spot beside it --
BOX_SIZE: Final[int] = 300
BOX_SLOTS: Final[tuple[int, int]] = (480, 790)  # centre x of the two halves
BOX_BOTTOM: Final[int] = 590
KITTEN_SIZE: Final[int] = 168
BALL_SIZE: Final[int] = 92

# -- find pairs: two pictures side by side --
SLOT_CENTERS: Final[tuple[int, int]] = (480, 790)
SLOT_WIDTH: Final[int] = 300
SLOT_TOP: Final[int] = 200
BIG_SIZE: Final[int] = 260
SMALL_SIZE: Final[int] = 104
GIFT_SIZE: Final[int] = 300
PUPPY_SIZE: Final[int] = 172

# -- fast / slow: two racing lanes on the meadow --
LANE_RECTS: Final[tuple[pygame.Rect, pygame.Rect]] = (
    pygame.Rect(STAGE_LEFT, 362, 1024 - STAGE_LEFT - 12, 112),
    pygame.Rect(STAGE_LEFT, 480, 1024 - STAGE_LEFT - 12, 116),
)
RACER_SIZES: Final[tuple[int, int]] = (118, 140)
RACE_START_X: Final[int] = STAGE_LEFT + 60
RACE_END_X: Final[int] = 1024 + 80


def slot_rect(index: int) -> pygame.Rect:
    centre = SLOT_CENTERS[index]
    return pygame.Rect(centre - SLOT_WIDTH // 2, SLOT_TOP, SLOT_WIDTH, GROUND_Y + 10 - SLOT_TOP)


def box_target(centre_x: int) -> pygame.Rect:
    """The box face (below the rim, so a perched kitten is not part of it)."""

    return pygame.Rect(centre_x - 130, 428, 260, 166)


def out_target(centre_x: int) -> pygame.Rect:
    return pygame.Rect(centre_x - 140, 368, 280, 228)


__all__ = [
    "BALL_SIZE",
    "BALLOON_SIZE",
    "BALLOON_TOP_DOWN",
    "BALLOON_TOP_NEUTRAL",
    "BALLOON_TOP_UP",
    "BALLOON_X",
    "BIG_SIZE",
    "BOX_BOTTOM",
    "BOX_SIZE",
    "BOX_SLOTS",
    "CLOUD_CENTER",
    "CLOUD_SIZE",
    "FLASH_HEIGHT",
    "FLASH_MIDBOTTOM",
    "FLOWER_SIZE",
    "FLOWER_SPOTS",
    "GIFT_SIZE",
    "GRASS_TARGET",
    "GROUND_Y",
    "KITTEN_SIZE",
    "LANE_RECTS",
    "PUPPY_SIZE",
    "RACE_END_X",
    "RACE_START_X",
    "RACER_SIZES",
    "SKY_TARGET",
    "SLOT_CENTERS",
    "SLOT_TOP",
    "SLOT_WIDTH",
    "SMALL_SIZE",
    "STAGE_LEFT",
    "box_target",
    "out_target",
    "slot_rect",
]
