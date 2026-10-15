"""Scene geometry for La Casa del Dieci in 1024x600 logical pixels.

The house art (``assets/source/house.svg``) is drawn at 1:1 at
``HOUSE_ORIGIN``; every room rect, the roof sign and the chimney below are
expressed in the same logical space so art, renderer and controls agree.
Nothing here enters the protected Home/Back region (top-left corner).
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .ten_house_model import ROOM_COUNT, ROW_LENGTH, room_row_column
else:
    from ten_house_model import ROOM_COUNT, ROW_LENGTH, room_row_column

HOUSE_ORIGIN: Final[tuple[int, int]] = (196, 20)
HOUSE_SIZE: Final[tuple[int, int]] = (632, 400)
ROOM_SIZE: Final[tuple[int, int]] = (88, 92)
_ROOM_X: Final = (64, 168, 272, 376, 480)  # house-local
_ROOM_Y: Final = (150, 280)


def _room_rect(index: int) -> pygame.Rect:
    row, column = room_row_column(index)
    return pygame.Rect(
        HOUSE_ORIGIN[0] + _ROOM_X[column],
        HOUSE_ORIGIN[1] + _ROOM_Y[row],
        *ROOM_SIZE,
    )


ROOM_RECTS: Final[tuple[pygame.Rect, ...]] = tuple(_room_rect(index) for index in range(ROOM_COUNT))
assert len(_ROOM_X) == ROW_LENGTH

# Where a firefly sits inside a lit room (centre), slightly below the glass centre.
FIREFLY_IN_ROOM: Final[tuple[tuple[int, int], ...]] = tuple((r.centerx, r.centery + 3) for r in ROOM_RECTS)

# Cream face of the roof sign (house-local 216,38 200x84).
SIGN_RECT: Final[pygame.Rect] = pygame.Rect(HOUSE_ORIGIN[0] + 216, HOUSE_ORIGIN[1] + 38, 200, 84)
CHIMNEY_TOP: Final[tuple[int, int]] = (HOUSE_ORIGIN[0] + 519, HOUSE_ORIGIN[1] + 2)

# Guests wait in the garden air to the right of the house.
GUEST_SLOTS: Final[tuple[tuple[int, int], ...]] = ((880, 262), (962, 228), (884, 356), (964, 330))
GUEST_TARGET: Final[int] = 92
# Fireflies that fly home gather in the sky on the left (clear of Home/Back).
SKY_SLOTS: Final[tuple[tuple[int, int], ...]] = ((110, 176), (178, 140), (100, 250), (182, 220))
# Fireflies enter from beyond the right edge and leave the same way.
OFFSTAGE_RIGHT: Final[tuple[int, int]] = (1080, 300)

# Dani stands on the lawn at the left; feet midpoint in logical space.
DANI_MIDBOTTOM: Final[tuple[int, int]] = (110, 594)
DANI_HEIGHT: Final[int] = 204

# Answer cards and the "house is ready" button below the house.
CARD_SIZE: Final[tuple[int, int]] = (132, 148)
CARD_GAP: Final[int] = 40
CARD_TOP: Final[int] = 436
CONFIRM_RECT: Final[pygame.Rect] = pygame.Rect(512 - 58, 448, 116, 122)


def card_rects(count: int = 3) -> tuple[pygame.Rect, ...]:
    width, height = CARD_SIZE
    total = count * width + (count - 1) * CARD_GAP
    left = 512 - total // 2
    return tuple(pygame.Rect(left + i * (width + CARD_GAP), CARD_TOP, width, height) for i in range(count))


CHOICE_RECTS: Final[tuple[pygame.Rect, ...]] = card_rects(3)
# The number-bond strip ("5 + 2 = 7") shown under the house once a challenge is solved.
BOND_CENTER: Final[tuple[int, int]] = (512, 508)


__all__ = [
    "CARD_SIZE",
    "CHIMNEY_TOP",
    "CHOICE_RECTS",
    "CONFIRM_RECT",
    "DANI_HEIGHT",
    "DANI_MIDBOTTOM",
    "FIREFLY_IN_ROOM",
    "GUEST_SLOTS",
    "GUEST_TARGET",
    "HOUSE_ORIGIN",
    "HOUSE_SIZE",
    "OFFSTAGE_RIGHT",
    "ROOM_RECTS",
    "ROOM_SIZE",
    "SIGN_RECT",
    "SKY_SLOTS",
    "BOND_CENTER",
    "card_rects",
]
