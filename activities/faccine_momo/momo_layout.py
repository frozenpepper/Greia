"""Reference-canvas geometry (1024 x 600) for Momo's Happy Faces.

The playroom wall meets the wood floor at y ~430; Momo stands on that line and
the answer tiles sit on the floor below, the guide friend (Flash) at the
bottom left. Everything stays clear of the protected Home/Back region, whose
largest logical footprint (480 x 320 screens) is about 240 x 90.
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .momo_content import CARD_H, CARD_W, REFERENCE_WIDTH
else:
    from momo_content import CARD_H, CARD_W, REFERENCE_WIDTH

# Momo (cast canvas is 256 px with the contact shadow centre at y 229).
MOMO_HEIGHT: Final[int] = 340
MOMO_STAGE: Final[tuple[int, int]] = (512, 478)        # recognise: canvas midbottom
MOMO_SIDE: Final[tuple[int, int]] = (790, 478)         # explain / help
MOMO_WARMUP_HEIGHT: Final[int] = 360
MOMO_WARMUP: Final[tuple[int, int]] = (512, 490)

# Answer tiles on the floor.
TILE: Final[int] = 156          # tile height
TILE_W: Final[int] = 188        # room for the longest feeling word plus padding
TILE_GAP: Final[int] = 20
TILE_TOP: Final[int] = 432
TILE_ICON: Final[int] = 104
HELP_ICON: Final[int] = 128

# Warm-up mirror: three faces on each side of Momo.
MIRROR_TILE: Final[int] = 134       # tile height
MIRROR_TILE_W: Final[int] = 172     # room for ARRABBIATO / ASSONNATO plus padding
MIRROR_GAP: Final[int] = 14
MIRROR_TOP: Final[int] = 118
MIRROR_MARGIN: Final[int] = 34
MIRROR_ICON: Final[int] = 92
GO_RECT: Final[pygame.Rect] = pygame.Rect(512 - 54, 482, 108, 108)

# Picture-story card.
CARD_FRAME: Final[int] = 8
CARD_RECT: Final[pygame.Rect] = pygame.Rect(88, 104, CARD_W + 2 * CARD_FRAME, CARD_H + 2 * CARD_FRAME)

# Guide friend.
GUIDE_HEIGHT: Final[int] = 156
GUIDE_MIDBOTTOM: Final[tuple[int, int]] = (110, 594)

# Hit area of Momo for the warm-up cuddle (canvas-relative body box).
MOMO_BODY_BOX: Final[tuple[float, float, float, float]] = (0.2, 0.26, 0.6, 0.6)


def tile_rects(count: int) -> tuple[pygame.Rect, ...]:
    """``count`` answer tiles centred on the floor."""

    total = count * TILE_W + (count - 1) * TILE_GAP
    left = REFERENCE_WIDTH // 2 - total // 2
    return tuple(pygame.Rect(left + index * (TILE_W + TILE_GAP), TILE_TOP, TILE_W, TILE) for index in range(count))


def mirror_rects() -> tuple[pygame.Rect, ...]:
    """Six warm-up faces: left column top to bottom, then the right column."""

    rects = []
    for column_x in (MIRROR_MARGIN, REFERENCE_WIDTH - MIRROR_MARGIN - MIRROR_TILE_W):
        for row in range(3):
            rects.append(pygame.Rect(column_x, MIRROR_TOP + row * (MIRROR_TILE + MIRROR_GAP), MIRROR_TILE_W, MIRROR_TILE))
    return tuple(rects)


def momo_rect(midbottom: tuple[int, int], height: int) -> pygame.Rect:
    """Rect of the square cast canvas at ``midbottom``."""

    return pygame.Rect(midbottom[0] - height // 2, midbottom[1] - height, height, height)


def momo_body_rect(midbottom: tuple[int, int], height: int) -> pygame.Rect:
    canvas = momo_rect(midbottom, height)
    x, y, w, h = MOMO_BODY_BOX
    return pygame.Rect(
        canvas.x + int(canvas.width * x),
        canvas.y + int(canvas.height * y),
        int(canvas.width * w),
        int(canvas.height * h),
    )


def momo_chest(midbottom: tuple[int, int], height: int) -> tuple[int, int]:
    canvas = momo_rect(midbottom, height)
    return (canvas.centerx, canvas.y + int(canvas.height * 0.58))


def momo_head(midbottom: tuple[int, int], height: int) -> tuple[int, int]:
    canvas = momo_rect(midbottom, height)
    return (canvas.centerx, canvas.y + int(canvas.height * 0.3))


__all__ = [
    "CARD_FRAME",
    "CARD_RECT",
    "GO_RECT",
    "GUIDE_HEIGHT",
    "GUIDE_MIDBOTTOM",
    "HELP_ICON",
    "MIRROR_ICON",
    "MIRROR_TILE",
    "MIRROR_TILE_W",
    "MOMO_HEIGHT",
    "MOMO_SIDE",
    "MOMO_STAGE",
    "MOMO_WARMUP",
    "MOMO_WARMUP_HEIGHT",
    "TILE",
    "TILE_ICON",
    "TILE_W",
    "TILE_TOP",
    "mirror_rects",
    "momo_body_rect",
    "momo_chest",
    "momo_head",
    "momo_rect",
    "tile_rects",
]
