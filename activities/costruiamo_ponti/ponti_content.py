from __future__ import annotations

"""Pure content constants for the Costruiamo Ponti activity.

No pygame or platform imports. This module owns reference geometry,
storage identity and level/material data so gameplay, presentation and
bootstrap code share one semantic source.
"""

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "costruiamo_ponti.progress.v2"

BLOCKS: list[dict[str, object]] = [
    {"id": "wood", "color": (180, 83, 9), "border": (146, 64, 14), "type_name": "wood"},
    {"id": "stone", "color": (100, 116, 139), "border": (71, 85, 105), "type_name": "stone"},
    {"id": "shroom", "color": (239, 68, 68), "border": (220, 38, 38), "type_name": "shroom"},
    {"id": "rainbow", "color": (168, 85, 247), "border": (147, 51, 234), "type_name": "rainbow"},
]
BLOCK_TYPES = BLOCKS

LEVELS: list[dict[str, object]] = [
    {
        "id": "river",
        "sky": (205, 238, 252),
        "gap_water": (56, 189, 248),
        "cliff_color": (34, 197, 94),
        "required": ["wood", "wood", "shroom", "wood"],
    },
    {
        "id": "canyon",
        "sky": (254, 225, 185),
        "gap_water": (217, 119, 6),
        "cliff_color": (120, 53, 15),
        "required": ["stone", "shroom", "stone", "rainbow"],
    },
    {
        "id": "space",
        "sky": (18, 22, 45),
        "gap_water": (30, 27, 75),
        "cliff_color": (59, 130, 246),
        "required": ["rainbow", "shroom", "rainbow", "shroom"],
    },
]

# Reference bridge geometry (logical 1024x600 canvas).
BRIDGE_START_X = 220
BRIDGE_END_X = 800
BRIDGE_Y = 350

__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "STORAGE_KEY",
    "BLOCKS",
    "BLOCK_TYPES",
    "LEVELS",
    "BRIDGE_START_X",
    "BRIDGE_END_X",
    "BRIDGE_Y",
]
