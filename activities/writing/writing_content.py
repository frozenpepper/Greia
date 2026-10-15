"""Pure content constants for Writing.

No pygame imports. Defines reference geometry, storage keys, paper tints and
tunable bounds as pure data so runtime modules can be reasoned about
independently. Writing stays a calm, essential sheet of paper: big readable
text, colour emoji, six paper colours, bounded undo, autosave.
"""

from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

INDEX_KEY: Final = "documents.index.v1"
# STORAGE_KEY alias for app wiring; canonical key is INDEX_KEY.
STORAGE_KEY: Final = INDEX_KEY

AUTOSAVE_IDLE_SECONDS: Final = 1.2
CREATION_PICKER_POLL_SECONDS: Final = 0.12
MAX_DOCUMENTS: Final = 120
# Gallery shows a 3x2 page; every saved page must be reachable by paging.
GALLERY_PAGE_SIZE: Final = 6
MAX_CHARACTERS: Final = 120_000
MAX_UNDO_EDITS: Final = 128
MAX_UNDO_PAYLOAD_CHARS: Final = 65_536
PREVIEW_GRAPHEME_LIMIT: Final = 80
PREVIEW_MAX_CHARS: Final = 80

# Body text size at the 1024x600 reference scale: large and readable by default.
BODY_TEXT_SIZE: Final = 42
CARD_TEXT_SIZE: Final = 23

# Paper colours a child picks when starting a new page. The tint is index
# metadata only (the document body stays plain UTF-8 text) and doubles as the
# gallery card colour, the cheapest identity cue for a pre-reader.
DEFAULT_TINT: Final = "cream"
PAPER_TINTS: Final = (
    ("cream", (255, 250, 236)),
    ("sky", (210, 232, 255)),
    ("mint", (210, 243, 220)),
    ("rose", (255, 220, 232)),
    ("lemon", (255, 241, 180)),
    ("lilac", (230, 220, 255)),
)
TINT_IDS: Final = tuple(tint_id for tint_id, _rgb in PAPER_TINTS)

# The canonical cast friend who cheers when a page goes to My Creations.
CAST_FRIEND: Final = "leo"

# Short presentation timings (seconds).
FEEDBACK_SECONDS: Final = 2.0
LIBRARY_FULL_SECONDS: Final = 4.0


def tint_rgb(tint_id: str) -> tuple[int, int, int]:
    """Return the paper colour for ``tint_id`` (unknown ids fall back to cream)."""

    for candidate, rgb in PAPER_TINTS:
        if candidate == tint_id:
            return rgb
    return PAPER_TINTS[0][1]


__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "INDEX_KEY",
    "STORAGE_KEY",
    "AUTOSAVE_IDLE_SECONDS",
    "CREATION_PICKER_POLL_SECONDS",
    "MAX_CHARACTERS",
    "MAX_DOCUMENTS",
    "GALLERY_PAGE_SIZE",
    "MAX_UNDO_EDITS",
    "MAX_UNDO_PAYLOAD_CHARS",
    "PREVIEW_GRAPHEME_LIMIT",
    "PREVIEW_MAX_CHARS",
    "BODY_TEXT_SIZE",
    "CARD_TEXT_SIZE",
    "DEFAULT_TINT",
    "PAPER_TINTS",
    "TINT_IDS",
    "CAST_FRIEND",
    "FEEDBACK_SECONDS",
    "LIBRARY_FULL_SECONDS",
    "tint_rgb",
]
