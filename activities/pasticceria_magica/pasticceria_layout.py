"""Scene geometry for Magic Bakery in 1024x600 logical pixels (pure).

The shared bakery wall + wood floor fill the screen; this package's counter
runs from x 264 to the right edge with its top at y 420. The customer stands
on the floor at the counter's rounded left end, their order bubble above
them; the cake sits on the counter. Toppings are drawn by their *base point*
(the middle of the sprite's bottom edge) on the frosting ellipse.

Nothing here enters the protected Home/Back corner: the order bubble starts
below y 116, which clears the protected region at every supported size; the
top bar is laid out by the control kit.
"""

from __future__ import annotations

import math
from typing import Final

import pygame

if __package__:
    from .pasticceria_content import COUNT, PATTERN
else:
    from pasticceria_content import COUNT, PATTERN

COUNTER_POS: Final[tuple[int, int]] = (264, 420)
CAKE_POS: Final[tuple[int, int]] = (400, 148)
CAKE_SIZE: Final[tuple[int, int]] = (420, 300)
# The frosting top of ``cake.svg`` (cx 210, cy 110, rx 186, ry 66) on screen.
FROSTING_CENTER: Final[tuple[int, int]] = (CAKE_POS[0] + 210, CAKE_POS[1] + 110)
FROSTING_RX: Final = 186
FROSTING_RY: Final = 66

BUBBLE_RECT: Final[pygame.Rect] = pygame.Rect(10, 116, 290, 206)
# Inner drawing area of ``bubble.svg`` (x 18-272, y 16-154) on screen.
BUBBLE_INNER: Final[pygame.Rect] = pygame.Rect(BUBBLE_RECT.x + 18, BUBBLE_RECT.y + 16, 254, 138)

CUSTOMER_HEIGHT: Final = 250
CUSTOMER_MIDBOTTOM: Final[tuple[int, int]] = (142, 594)
WALK_DISTANCE: Final = 330

TOPPING_SIZE: Final = 76
PATTERN_SIZE: Final = 62
TILE: Final = 100
TILE_ICON: Final = 72
TILE_TOP: Final = 470
SIDE_BUTTON: Final[pygame.Rect] = pygame.Rect(846, 292, 160, 124)  # serve / save on the counter
SIDE_ICON: Final = 58
UNDO_SIZE: Final = 88
UNDO_ICON: Final = 52


def _row(y: int, offsets: tuple[int, ...]) -> tuple[tuple[int, int], ...]:
    return tuple((FROSTING_CENTER[0] + dx, y) for dx in offsets)


# Count places, filled in this order: the middle row left to right (a child
# counts a short line easily), then the back row and the two front places,
# each set between the middle ones so every topping stays visible.
COUNT_POINTS: Final[tuple[tuple[int, int], ...]] = (
    *_row(FROSTING_CENTER[1] + 8, (-148, -74, 0, 74, 148)),
    *_row(FROSTING_CENTER[1] - 30, (-111, -37, 37, 111)),
    *_row(FROSTING_CENTER[1] + 46, (-37, 37)),
)
# The six places of a pattern row, a straight line across the frosting.
PATTERN_POINTS: Final[tuple[tuple[int, int], ...]] = _row(
    FROSTING_CENTER[1] + 20, (-150, -90, -30, 30, 90, 150)
)


# Where each kind of order puts its toppings and how big they are drawn.
PLACES: Final[dict[str, tuple[tuple[tuple[int, int], ...], int]]] = {
    COUNT: (COUNT_POINTS, TOPPING_SIZE),
    PATTERN: (PATTERN_POINTS, PATTERN_SIZE),
}


def place_point(kind: str, index: int) -> tuple[tuple[int, int], int]:
    """Base point and sprite size of cake place ``index`` for an order kind."""

    points, size = PLACES[kind]
    return points[index], size


def sprite_rect(base: tuple[int, int], size: int) -> pygame.Rect:
    """Square sprite standing on ``base`` (library props carry their own shadow)."""

    rect = pygame.Rect(0, 0, size, size)
    rect.midbottom = (int(base[0]), int(base[1]) + max(2, size // 14))
    return rect


def to_frosting(point: tuple[float, float]) -> tuple[float, float]:
    """Screen point -> normalised frosting coordinates (u, v)."""

    return (
        (point[0] - FROSTING_CENTER[0]) / FROSTING_RX,
        (point[1] - FROSTING_CENTER[1]) / FROSTING_RY,
    )


def from_frosting(u: float, v: float) -> tuple[int, int]:
    return (int(round(FROSTING_CENTER[0] + u * FROSTING_RX)), int(round(FROSTING_CENTER[1] + v * FROSTING_RY)))


def on_frosting(point: tuple[float, float], margin: float = 0.95) -> bool:
    u, v = to_frosting(point)
    return math.hypot(u, v) <= margin


# Free decorating: a pantry tap drops the topping on the first count place
# still open (then anywhere on the frosting); a tap on the frosting puts it
# exactly there.
FREE_POINTS: Final[tuple[tuple[float, float], ...]] = tuple(to_frosting(point) for point in COUNT_POINTS)


def pantry_rects(count: int, *, free: bool) -> tuple[pygame.Rect, ...]:
    """Pantry tiles on the counter front (centred under the cake in a round)."""

    if count <= 0:
        return ()
    gap = 10 if free else 16
    width = TILE - 4 if free else TILE
    total = count * width + (count - 1) * gap
    left = 280 if free else FROSTING_CENTER[0] - total // 2
    return tuple(pygame.Rect(left + i * (width + gap), TILE_TOP, width, TILE) for i in range(count))


UNDO_RECT: Final[pygame.Rect] = pygame.Rect(920, TILE_TOP + (TILE - UNDO_SIZE) // 2, UNDO_SIZE, UNDO_SIZE)


__all__ = [
    "BUBBLE_INNER",
    "BUBBLE_RECT",
    "CAKE_POS",
    "CAKE_SIZE",
    "COUNTER_POS",
    "COUNT_POINTS",
    "CUSTOMER_HEIGHT",
    "CUSTOMER_MIDBOTTOM",
    "FREE_POINTS",
    "FROSTING_CENTER",
    "FROSTING_RX",
    "FROSTING_RY",
    "PATTERN_POINTS",
    "PATTERN_SIZE",
    "PLACES",
    "SIDE_BUTTON",
    "SIDE_ICON",
    "TILE",
    "TILE_ICON",
    "TILE_TOP",
    "TOPPING_SIZE",
    "UNDO_ICON",
    "UNDO_RECT",
    "UNDO_SIZE",
    "WALK_DISTANCE",
    "from_frosting",
    "on_frosting",
    "pantry_rects",
    "place_point",
    "sprite_rect",
    "to_frosting",
]
