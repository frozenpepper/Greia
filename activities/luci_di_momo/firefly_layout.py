"""Scene geometry for Luci di Momo in 1024x600 logical pixels.

Momo stands on the meadow at the left with her firefly jar; the fireflies
glow in the night air to the right (``firefly_model`` owns that playfield);
the three number cards and the "look again" button sit on the grass below.
Nothing here enters the protected Home/Back region (top-left corner); the
kit's top bar (listen + progress) is placed by ``ControlLayout``.
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .firefly_model import CHOICE_COUNT, FIELD_CENTER, FRAME_CELL, FRAME_COLUMNS, FRAME_ROWS
else:
    from firefly_model import CHOICE_COUNT, FIELD_CENTER, FRAME_CELL, FRAME_COLUMNS, FRAME_ROWS

MOMO_MIDBOTTOM: Final[tuple[int, int]] = (110, 592)
MOMO_HEIGHT: Final = 212

JAR_SIZE: Final = 200
JAR_TOPLEFT: Final[tuple[int, int]] = (196, 368)
# Where collected lights rest inside the jar (logical px), bottom row first.
JAR_SLOTS: Final[tuple[tuple[int, int], ...]] = (
    (270, 520), (322, 520), (296, 488), (250, 474), (342, 476), (296, 444),
)
JAR_MOUTH: Final[tuple[int, int]] = (296, 412)
JAR_GLOW_CENTER: Final[tuple[int, int]] = (296, 480)

CARD_SIZE: Final[tuple[int, int]] = (128, 144)
CARD_GAP: Final = 30
CARD_TOP: Final = 432
CARD_CENTER_X: Final = 672
REPLAY_SIZE: Final = 96
REPLAY_RECT: Final[pygame.Rect] = pygame.Rect(1012 - REPLAY_SIZE, CARD_TOP + 24, REPLAY_SIZE, REPLAY_SIZE)

FRAME_RECT: Final[pygame.Rect] = pygame.Rect(
    FIELD_CENTER[0] - (FRAME_COLUMNS * FRAME_CELL) // 2 - 14,
    FIELD_CENTER[1] - (FRAME_ROWS * FRAME_CELL) // 2 - 14,
    FRAME_COLUMNS * FRAME_CELL + 28,
    FRAME_ROWS * FRAME_CELL + 28,
)


def card_rects(count: int = CHOICE_COUNT) -> tuple[pygame.Rect, ...]:
    width, height = CARD_SIZE
    total = count * width + (count - 1) * CARD_GAP
    left = CARD_CENTER_X - total // 2 - 40
    return tuple(pygame.Rect(left + i * (width + CARD_GAP), CARD_TOP, width, height) for i in range(count))


CHOICE_RECTS: Final[tuple[pygame.Rect, ...]] = card_rects()


__all__ = [
    "CARD_SIZE",
    "CHOICE_RECTS",
    "FRAME_RECT",
    "JAR_GLOW_CENTER",
    "JAR_MOUTH",
    "JAR_SIZE",
    "JAR_SLOTS",
    "JAR_TOPLEFT",
    "MOMO_HEIGHT",
    "MOMO_MIDBOTTOM",
    "REPLAY_RECT",
    "card_rects",
]
