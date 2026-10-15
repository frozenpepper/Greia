"""Pure content constants for Writing.

No pygame imports. Defines reference geometry, storage keys and
tunable bounds as pure data so runtime modules can be reasoned
about independently.
"""

from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

INDEX_KEY: Final = "documents.index.v1"
# STORAGE_KEY alias for app wiring; canonical key is INDEX_KEY.
STORAGE_KEY: Final = INDEX_KEY

AUTOSAVE_IDLE_SECONDS: Final = 1.2
MAX_DOCUMENTS: Final = 120
# Gallery shows a 3x2 page; every saved page must be reachable by paging.
GALLERY_PAGE_SIZE: Final = 6
MAX_CHARACTERS: Final = 120_000
MAX_UNDO_EDITS: Final = 128
MAX_UNDO_PAYLOAD_CHARS: Final = 65_536
PREVIEW_GRAPHEME_LIMIT: Final = 80
PREVIEW_MAX_CHARS: Final = 80

__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "INDEX_KEY",
    "STORAGE_KEY",
    "AUTOSAVE_IDLE_SECONDS",
    "MAX_CHARACTERS",
    "MAX_DOCUMENTS",
    "GALLERY_PAGE_SIZE",
    "MAX_UNDO_EDITS",
    "MAX_UNDO_PAYLOAD_CHARS",
    "PREVIEW_GRAPHEME_LIMIT",
    "PREVIEW_MAX_CHARS",
]
