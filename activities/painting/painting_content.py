"""Pure content constants for Painting.

No pygame imports. Defines reference geometry, storage keys and
tunable bounds as pure data so runtime modules can be reasoned
about independently. Keeps the Activity simple, fast and cute:
large canvas, small cheerful palette, bounded undo, autosave.
"""

from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

INDEX_KEY: Final = "paintings.index.v1"
# STORAGE_KEY alias for app wiring; canonical key is INDEX_KEY.
STORAGE_KEY: Final = INDEX_KEY

AUTOSAVE_IDLE_SECONDS: Final = 1.0
CREATION_PICKER_POLL_SECONDS: Final = 0.12
MAX_PAINTINGS: Final = 48
# Gallery shows a 3x2 page; every saved painting must be reachable by paging.
GALLERY_PAGE_SIZE: Final = 6
MAX_UNDO_STROKES: Final = 24
MAX_STROKE_POINTS: Final = 2048

# Cheerful fixed child palette (large pleasant swatches).
COLORS: Final = (
    (42, 45, 54),  # Charcoal Night
    (239, 77, 83),  # Coral Red
    (250, 145, 54),  # Bright Orange
    (252, 202, 62),  # Sunshine Yellow
    (77, 180, 96),  # Leaf Green
    (51, 163, 211),  # Sky Blue
    (92, 113, 224),  # Indigo Periwinkle
    (159, 94, 211),  # Lavender Purple
    (239, 104, 170),  # Blossom Pink
    (133, 91, 61),  # Warm Cocoa Brown
)

BRUSH_SIZES: Final = (8, 18, 34)

__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "INDEX_KEY",
    "STORAGE_KEY",
    "AUTOSAVE_IDLE_SECONDS",
    "CREATION_PICKER_POLL_SECONDS",
    "MAX_PAINTINGS",
    "GALLERY_PAGE_SIZE",
    "MAX_UNDO_STROKES",
    "MAX_STROKE_POINTS",
    "COLORS",
    "BRUSH_SIZES",
]
