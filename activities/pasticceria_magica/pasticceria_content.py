"""Authoritative content for Magic Bakery (Pasticceria Magica).

Pure data, no pygame and no Greia IO. The Activity is one experience: cast
friends come to the bakery counter one by one, each with an order card for a
cake (``3 strawberries``, or ``finish my pattern: strawberry, blueberry,
strawberry ...``). The child decorates the cake from a small pantry, rings
the bell to serve, and the customer reacts. Five customers make one round;
the round ends on the shared completion scene, from where the child can make
a cake of their own and keep it as a picture in My Creations.

Toppings are shared library food (``prop.food.*``); the room is the shared
bakery wall + wood floor; the customers are the canonical cast.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
# The historical key is kept so earlier saves (score / stars / recipes) migrate.
STORAGE_KEY: Final = "pasticceria_magica.state.v3"
PICTURE_NAME: Final = "cakes/shared.png"

ROOM_LAYERS: Final[tuple[str, ...]] = ("bg.indoor_room.wall_bakery", "bg.indoor_room.floor_wood")
BAKER: Final = "momo"
CUSTOMERS: Final[tuple[str, ...]] = ("lilli", "leo", "flash", "dani", "tito")
ORDERS_PER_ROUND: Final = len(CUSTOMERS)


@dataclass(frozen=True, slots=True)
class Topping:
    """One cake topping: a shared library food picture and its name key."""

    topping_id: str
    asset_id: str
    text_key: str


TOPPINGS: Final[tuple[Topping, ...]] = (
    Topping("strawberry", "prop.food.strawberry", "topping.strawberry"),
    Topping("blueberry", "prop.food.blueberry", "topping.blueberry"),
    Topping("cherry", "prop.food.cherry", "topping.cherry"),
    Topping("banana", "prop.food.banana", "topping.banana"),
    Topping("cookie", "prop.food.cookie", "topping.cookie"),
    Topping("chocolate", "prop.food.chocolate", "topping.chocolate"),
)
TOPPINGS_BY_ID: Final[dict[str, Topping]] = {topping.topping_id: topping for topping in TOPPINGS}
TOPPING_IDS: Final[tuple[str, ...]] = tuple(topping.topping_id for topping in TOPPINGS)
# Toppings that look alike (both red / both brown) are never offered side by side.
LOOKALIKES: Final[frozenset[frozenset[str]]] = frozenset(
    {frozenset({"strawberry", "cherry"}), frozenset({"cookie", "chocolate"})}
)

COUNT: Final = "count"
PATTERN: Final = "pattern"


@dataclass(frozen=True, slots=True)
class LevelSpec:
    """One rung of the counting/pattern ladder.

    ``orders`` is the round plan (``count`` / ``pattern`` per customer).
    Count orders ask for ``kinds`` toppings with ``count_range`` each (at
    most ``max_total`` toppings in all). ``pictures`` shows the quantity as
    pictures beside the numeral (one-to-one matching); without it the card
    shows the numeral and one picture, so the child counts out a number.
    Pattern orders use one of ``units`` (``AB``, ``AAB`` ...) on a six-place
    row with ``blanks`` places left for the child. ``pantry`` is how many
    toppings are offered.
    """

    orders: tuple[str, ...]
    kinds: tuple[int, int]
    count_range: tuple[int, int]
    max_total: int
    pictures: bool
    units: tuple[str, ...]
    blanks: int
    pantry: int


LEVELS: Final[tuple[LevelSpec, ...]] = (
    LevelSpec((COUNT, COUNT, PATTERN, COUNT, COUNT), (1, 1), (1, 3), 3, True, ("AB",), 2, 3),
    LevelSpec((COUNT, COUNT, PATTERN, COUNT, PATTERN), (1, 1), (2, 5), 5, True, ("AB",), 2, 3),
    LevelSpec((COUNT, PATTERN, COUNT, COUNT, PATTERN), (2, 2), (1, 3), 5, True, ("AB", "AAB"), 2, 4),
    LevelSpec((COUNT, PATTERN, COUNT, PATTERN, COUNT), (1, 2), (2, 5), 7, False, ("AAB", "ABB"), 3, 4),
    LevelSpec((COUNT, PATTERN, COUNT, PATTERN, COUNT), (2, 2), (2, 5), 9, False, ("ABC", "ABB", "AAB"), 3, 4),
)
MAX_LEVEL: Final = len(LEVELS) - 1
PATTERN_LENGTH: Final = 6
COUNT_SLOTS: Final = 11
FREE_LIMIT: Final = 24

__all__ = [
    "BAKER",
    "COUNT",
    "COUNT_SLOTS",
    "CUSTOMERS",
    "FREE_LIMIT",
    "LEVELS",
    "LOOKALIKES",
    "LevelSpec",
    "MAX_LEVEL",
    "ORDERS_PER_ROUND",
    "PATTERN",
    "PATTERN_LENGTH",
    "PICTURE_NAME",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "ROOM_LAYERS",
    "STORAGE_KEY",
    "TOPPINGS",
    "TOPPINGS_BY_ID",
    "TOPPING_IDS",
    "Topping",
]
