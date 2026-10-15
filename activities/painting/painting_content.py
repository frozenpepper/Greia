"""Pure content constants for Painting.

No pygame imports. Defines reference geometry, storage keys and
tunable bounds as pure data so runtime modules can be reasoned
about independently. Keeps the Activity simple, fast and cute:
large canvas, small cheerful palette, a few stamps from the shared
art library, a handful of colouring pages, bounded undo, autosave.
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

# Stroke widths at the 1024x600 reference scale (small, medium, large).
BRUSH_SIZES: Final = (8, 18, 34)

# Stamps are shared-library props (``assets/catalog/shared_visuals_v1_source``),
# never Activity-private redraws. One tap places one stamp; its size follows
# the selected brush size so the child keeps a single "how big" control.
STAMP_IDS: Final = (
    "prop.shape.star",
    "prop.shape.heart",
    "prop.nature.flower",
    "prop.nature.sun",
    "prop.nature.rainbow",
    "prop.nature.cloud",
    "prop.vocab.butterfly",
    "prop.vocab.bee",
    "prop.vocab.cat",
    "prop.vocab.dog",
    "prop.vocab.whale",
    "prop.vocab.turtle",
)
# Stamp edge length at the reference scale for each brush size index.
STAMP_SIZES: Final = (72, 116, 172)

# Colouring pages: Activity-private line art (1024x600 source SVG + runtime
# PNG). The outline stays above the paint while the child colours and is
# flattened only into the saved/shared PNG (one overlay, never layers).
COLOURING_PAGES: Final = ("garden", "sea", "pets")

# Short presentation timings (seconds).
FEEDBACK_SECONDS: Final = 2.0
LIBRARY_FULL_SECONDS: Final = 4.0

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
    "STAMP_IDS",
    "STAMP_SIZES",
    "COLOURING_PAGES",
    "FEEDBACK_SECONDS",
    "LIBRARY_FULL_SECONDS",
]
