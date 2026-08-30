"""Treno Numeri — content constants (no pygame).

This module owns the reference canvas size, storage key, fruit catalogue
and station generation data. It has no pygame dependency so pure domain
logic can be tested without a display.
"""

from __future__ import annotations

from typing import Any, Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "treno_numeri.progress.v2"

FRUITS: list[dict[str, Any]] = [
    {"id": "apple", "color": (239, 68, 68), "leaf": (34, 197, 94), "stem": (120, 53, 15)},
    {"id": "banana", "color": (234, 179, 8), "leaf": (161, 98, 7), "stem": (113, 63, 18)},
    {"id": "carrot", "color": (249, 115, 22), "leaf": (34, 197, 94), "stem": (22, 101, 52)},
    {"id": "strawberry", "color": (244, 63, 94), "leaf": (34, 197, 94), "stem": (225, 29, 72)},
]
ITEMS = FRUITS

TOTAL_STATIONS: Final = 5

ADDITION_PAIRS: Final[tuple[tuple[int, int], ...]] = (
    (1, 1),
    (1, 2),
    (2, 1),
    (2, 2),
    (2, 3),
    (3, 2),
    (1, 3),
    (3, 1),
    (4, 1),
    (2, 4),
)

COUNT_CHOICES: Final[tuple[int, ...]] = (2, 3, 4, 5, 6)

__all__ = [
    "ADDITION_PAIRS",
    "COUNT_CHOICES",
    "FRUITS",
    "ITEMS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "TOTAL_STATIONS",
]
