"""Reference geometry and constants for workshop_settings.

Pure data — no pygame imports. Keeps the Parent Settings / My Greia
surface simple, fast and cute. The curated visual choices remain
profile-scoped and immediately reversible.
"""

from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

SCAN_INTERVAL_SECONDS: Final = 1.5
MAX_THUMBNAIL_CACHE: Final = 20
MAX_THUMBNAIL_PIXELS: Final = 12_000_000

MODES: Final = ("colors", "wallpapers", "size", "avatar")
MODE_ICONS: Final = {
    "colors": "palette",
    "wallpapers": "notebook",
    "size": "abc_blocks",
    "avatar": "unicorn",
}

__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "SCAN_INTERVAL_SECONDS",
    "MAX_THUMBNAIL_CACHE",
    "MAX_THUMBNAIL_PIXELS",
    "MODES",
    "MODE_ICONS",
]
