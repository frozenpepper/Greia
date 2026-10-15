"""Treno Numeri — content catalogue and scene geometry (no pygame).

The reference canvas is 1024x600 logical pixels. Every position the model,
renderer and controls share lives here so the three stay in agreement and the
pure model can be tested without a display.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600
# Kept from the first release so existing child saves load (schema migrates).
STORAGE_KEY: Final[str] = "treno_numeri.progress.v2"


class CargoKind(StrEnum):
    """Station cargo; each kind is one shared-library prop (no emoji content)."""

    APPLE = "apple"
    STRAWBERRY = "strawberry"
    PEAR = "pear"
    CARROT = "carrot"
    COOKIE = "cookie"
    CUPCAKE = "cupcake"
    BALL = "ball"
    DUCK = "duck"
    BLOCK = "block"
    CUP = "cup"

    @property
    def asset_id(self) -> str:
        return _CARGO_ASSETS[self]


_CARGO_ASSETS: Final[dict[CargoKind, str]] = {
    CargoKind.APPLE: "prop.food.apple",
    CargoKind.STRAWBERRY: "prop.food.strawberry",
    CargoKind.PEAR: "prop.vocab.pear",
    CargoKind.CARROT: "prop.food.carrot",
    CargoKind.COOKIE: "prop.food.cookie",
    CargoKind.CUPCAKE: "prop.food.cupcake",
    CargoKind.BALL: "prop.everyday.ball",
    CargoKind.DUCK: "prop.everyday.duck",
    CargoKind.BLOCK: "prop.everyday.block",
    CargoKind.CUP: "prop.everyday.cup",
}

# -- scene geometry (reference logical pixels) ---------------------------------

RAIL_Y: Final[int] = 365  # top of the rail; wheels stand on it
STATION_TOP: Final[int] = 360  # station strip (track bed + platform) origin
PLATFORM_TOP: Final[int] = 404

SIGN_POS: Final[tuple[int, int]] = (8, 140)
SIGN_SIZE: Final[tuple[int, int]] = (190, 274)
# The cream face of the order board, in sign-local pixels.
SIGN_FACE: Final[tuple[int, int, int, int]] = (20, 42, 150, 139)

WAGON_SIZE: Final[tuple[int, int]] = (282, 126)
WAGON_X: Final[tuple[int, int]] = (204, 490)
WAGON_TOP: Final[int] = RAIL_Y - WAGON_SIZE[1]
WAGON_WELLS: Final[int] = 5
WELL_FIRST_X: Final[float] = 13.3 + 25.53  # wagon-local centre of bay 0
WELL_PITCH: Final[float] = 51.06
WELL_FLOOR_Y: Final[int] = 74  # wagon-local y where cargo rests
WAGON_WHEEL_SIZE: Final[int] = 42
WAGON_WHEELS_X: Final[tuple[int, int]] = (63, 219)
WAGON_ITEM_SIZE: Final[int] = 62

LOCO_SIZE: Final[tuple[int, int]] = (216, 187)
LOCO_X: Final[int] = 776
LOCO_TOP: Final[int] = RAIL_Y - LOCO_SIZE[1]
# (local centre x, wheel diameter) for the two drivers and the pony wheel.
LOCO_WHEELS: Final[tuple[tuple[int, int], ...]] = ((90, 50), (144, 50), (191, 32))
CHIMNEY_TOP: Final[tuple[int, int]] = (173, 22)  # loco-local smoke origin

TRAIN_LEFT: Final[int] = WAGON_X[0]
TRAIN_RIGHT: Final[int] = LOCO_X + LOCO_SIZE[0]
ARRIVE_FROM: Final[float] = -float(TRAIN_RIGHT + 40)
DEPART_TO: Final[float] = float(REFERENCE_WIDTH - TRAIN_LEFT + 40)

DANI_MIDBOTTOM: Final[tuple[int, int]] = (104, 596)
DANI_HEIGHT: Final[int] = 188

FIELD_COLUMNS_X: Final[tuple[int, ...]] = (300, 420, 540, 660, 780)
FIELD_ROWS_Y: Final[tuple[int, ...]] = (466, 552)
FIELD_JITTER: Final[int] = 8
ITEM_SIZE: Final[int] = 92
POP_ITEM_SIZE: Final[int] = 108
ITEM_TARGET: Final[int] = 108  # < cell pitch (120), so targets never overlap

GO_CENTER: Final[tuple[int, int]] = (930, 512)
GO_SIZE: Final[int] = 112


def field_cells() -> list[tuple[int, int]]:
    """The ten cargo spots on the platform, row-major (top row first)."""

    return [(x, y) for y in FIELD_ROWS_Y for x in FIELD_COLUMNS_X]


def wagon_rect(wagon: int, offset: float = 0.0) -> tuple[int, int, int, int]:
    return (int(WAGON_X[wagon] + offset), WAGON_TOP, WAGON_SIZE[0], WAGON_SIZE[1])


def slot_position(slot: int, offset: float = 0.0) -> tuple[int, int]:
    """Mid-bottom resting point of wagon slot 0-9 (slots 0-4 = first wagon)."""

    if not 0 <= slot < 2 * WAGON_WELLS:
        raise ValueError("slot out of range")
    wagon, bay = divmod(slot, WAGON_WELLS)
    x = WAGON_X[wagon] + WELL_FIRST_X + WELL_PITCH * bay + offset
    return (int(round(x)), WAGON_TOP + WELL_FLOOR_Y)


def sign_face_rect() -> tuple[int, int, int, int]:
    x, y, w, h = SIGN_FACE
    return (SIGN_POS[0] + x, SIGN_POS[1] + y, w, h)


__all__ = [
    "ARRIVE_FROM",
    "CHIMNEY_TOP",
    "CargoKind",
    "DANI_HEIGHT",
    "DANI_MIDBOTTOM",
    "DEPART_TO",
    "FIELD_JITTER",
    "GO_CENTER",
    "GO_SIZE",
    "ITEM_SIZE",
    "ITEM_TARGET",
    "LOCO_SIZE",
    "LOCO_TOP",
    "LOCO_WHEELS",
    "LOCO_X",
    "PLATFORM_TOP",
    "POP_ITEM_SIZE",
    "RAIL_Y",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SIGN_FACE",
    "SIGN_POS",
    "SIGN_SIZE",
    "STATION_TOP",
    "STORAGE_KEY",
    "TRAIN_LEFT",
    "TRAIN_RIGHT",
    "WAGON_ITEM_SIZE",
    "WAGON_SIZE",
    "WAGON_TOP",
    "WAGON_WELLS",
    "WAGON_WHEELS_X",
    "WAGON_WHEEL_SIZE",
    "WAGON_X",
    "field_cells",
    "sign_face_rect",
    "slot_position",
    "wagon_rect",
]
