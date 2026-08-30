"""Shape Garden — content constants (no pygame).

This module owns the reference canvas size, storage key and visual
constants. It has no pygame dependency so pure domain logic can be tested
without a display.
"""

from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
SOIL_TOP: Final = 530

# Storage key kept for future progression; Activity is currently creative
# and profile-scoped autosave could be added without changing geometry.
STORAGE_KEY: Final = "shape_garden.progress.v1"

COLORS: Final[tuple[tuple[int, int, int], ...]] = (
    (247, 93, 89),   # Tomato Red
    (255, 190, 46),  # Sunflower Yellow
    (80, 188, 112),  # Meadow Green
    (67, 150, 222),  # Sky Blue
    (168, 105, 214), # Lilac Purple
)

STEM_COLOR: Final[tuple[int, int, int]] = (74, 158, 88)
LEAF_COLOR: Final[tuple[int, int, int]] = (102, 186, 115)

# Bounded limits reused by model and renderer/tests.
MAX_SHAPES: Final = 120
MAX_PARTICLES: Final = 30

__all__ = [
    "COLORS",
    "LEAF_COLOR",
    "MAX_PARTICLES",
    "MAX_SHAPES",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SOIL_TOP",
    "STEM_COLOR",
    "STORAGE_KEY",
]
