from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "pasticceria_magica.state.v3"

# Sweet Bakery Palette (R7.3)
BAKERY_WALL: Final = (255, 243, 235)
BAKERY_COUNTER: Final = (235, 195, 155)
COUNTER_TOP: Final = (215, 165, 120)
PLATE_COLOR: Final = (255, 255, 255)
PLATE_RIM: Final = (230, 240, 255)
SHELF_COLOR: Final = (195, 135, 90)
WHITE: Final = (255, 255, 255)
DARK_TEXT: Final = (55, 38, 30)
GOLD: Final = (255, 215, 50)
PINK: Final = (255, 125, 165)
PASTEL_PINK: Final = (255, 215, 230)

TOPPINGS: Final[list[tuple[str, str, tuple[int, int, int]]]] = [
    ("strawberry", "🍓", (255, 80, 100)),
    ("blueberry", "🫐", (80, 140, 240)),
    ("star", "⭐", (255, 215, 50)),
    ("chocolate", "🍫", (140, 85, 55)),
    ("cherry", "🍒", (240, 50, 70)),
    ("cookie", "🍪", (220, 160, 90)),
]

# 16 Distinct, Non-Overlapping Slot Coordinates on the Cake Plate
CAKE_SLOTS: Final[list[tuple[int, int]]] = [
    # Center Cluster (4 slots)
    (435, 310),
    (495, 310),
    (435, 365),
    (495, 365),
    # Inner Oval Ring (6 slots)
    (380, 290),
    (550, 290),
    (350, 340),
    (580, 340),
    (380, 390),
    (550, 390),
    # Outer Decor Ring (6 slots)
    (465, 270),
    (320, 315),
    (610, 315),
    (320, 375),
    (610, 375),
    (465, 410),
]

# Pattern mode content (semantic, not runtime state)
PATTERN_OPTIONS: Final[list[tuple[list[str], str, list[str]]]] = [
    (["🍓", "⭐", "🍓", "⭐"], "🍓", ["🍓", "🫐", "🍪"]),
    (["🫐", "🍪", "🫐", "🍪"], "🫐", ["⭐", "🫐", "🍫"]),
    (["🍫", "🍓", "🍫", "🍓"], "🍫", ["🍫", "🍒", "🍓"]),
    (["🍒", "⭐", "🍒", "⭐"], "🍒", ["🍪", "⭐", "🍒"]),
    (["🍪", "🍪", "⭐", "🍪", "🍪"], "⭐", ["⭐", "🍓", "🍫"]),
]

__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "STORAGE_KEY",
    "BAKERY_WALL",
    "BAKERY_COUNTER",
    "COUNTER_TOP",
    "PLATE_COLOR",
    "PLATE_RIM",
    "SHELF_COLOR",
    "WHITE",
    "DARK_TEXT",
    "GOLD",
    "PINK",
    "PASTEL_PINK",
    "TOPPINGS",
    "CAKE_SLOTS",
    "PATTERN_OPTIONS",
]
