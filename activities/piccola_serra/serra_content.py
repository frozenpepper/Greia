"""Piccola Serra — content constants (no pygame).

This module owns the reference canvas size, storage key, plant catalogue
and toolbar/pot geometry. It has no pygame dependency so pure domain
logic can be tested without a display.
"""

from __future__ import annotations

from typing import Any, Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "piccola_serra.progress.v1"

PLANTS: list[dict[str, Any]] = [
    {
        "id": "sunflower",
        "name_it": "Girasole 🌻",
        "name_en": "Sunflower 🌻",
        "flower_color": (254, 240, 138),
        "center_color": (120, 53, 15),
        "petal_color": (234, 179, 8),
    },
    {
        "id": "strawberry",
        "name_it": "Fragola 🍓",
        "name_en": "Strawberry 🍓",
        "flower_color": (239, 68, 68),
        "center_color": (254, 202, 87),
        "petal_color": (244, 63, 94),
    },
    {
        "id": "tulip",
        "name_it": "Tulipano 🌷",
        "name_en": "Tulip 🌷",
        "flower_color": (236, 72, 153),
        "center_color": (244, 114, 182),
        "petal_color": (219, 39, 119),
    },
    {
        "id": "carrot",
        "name_it": "Carota 🥕",
        "name_en": "Carrot 🥕",
        "flower_color": (249, 115, 22),
        "center_color": (34, 197, 94),
        "petal_color": (234, 88, 12),
    },
]

# Pot geometry as plain tuples (x, y, w, h) so content stays pygame-free.
# The renderer/app convert them to pygame.Rect.
POT_RECT_TUPLES: Final[tuple[tuple[int, int, int, int], ...]] = (
    (120, 160, 180, 280),
    (320, 160, 180, 280),
    (520, 160, 180, 280),
    (720, 160, 180, 280),
)

# Toolbar button definitions: (x, tool_index, label, color).
TOOL_DEFS: Final[tuple[tuple[int, int, str, tuple[int, int, int]], ...]] = (
    (100, 0, "SEME", (22, 101, 52)),
    (310, 1, "ACQUA", (2, 132, 199)),
    (520, 2, "SOLE", (202, 138, 4)),
    (730, 3, "RACCOLTA", (194, 65, 12)),
)

TARGET_HARVEST: Final = 6

__all__ = [
    "PLANTS",
    "POT_RECT_TUPLES",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "TARGET_HARVEST",
    "TOOL_DEFS",
]
