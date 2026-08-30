"""Authoritative constants for Cucciolo Mio (Lilli affinity)."""

from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "cucciolo_mio.state.v3"

# Sweet Nursery Palette
ROOM_WALL: Final = (255, 245, 238)
ROOM_FLOOR: Final = (235, 195, 160)
NIGHT_WALL: Final = (25, 25, 45)
NIGHT_FLOOR: Final = (18, 18, 30)
WHITE: Final = (255, 255, 255)
DARK_TEXT: Final = (50, 40, 35)
GOLD: Final = (255, 215, 50)
PINK: Final = (255, 120, 165)
PASTEL_PINK: Final = (255, 215, 230)
ACCENT_BLUE: Final = (80, 175, 245)

# Domain vocabularies
VALID_SPECIES: Final[tuple[str, ...]] = ("cat", "bunny", "puppy")
VALID_ACCESSORIES: Final[tuple[str, ...]] = ("bow", "crown", "glasses", "party_hat", "none")
VALID_TABS: Final[tuple[str, ...]] = ("feed", "bath", "play", "sleep", "dress")

SPECIES_ICONS: Final[dict[str, str]] = {
    "cat": "🐱",
    "bunny": "🐰",
    "puppy": "🐶",
}

# Geometry constants in reference coordinates
RUG_RECT: Final = (262, 380, 500, 120)  # ellipse bounds
FLOOR_Y: Final = 420
BALL_BOUNDS_X: Final[tuple[float, float]] = (150.0, 874.0)
BALL_BOUNDS_Y: Final[tuple[float, float]] = (160.0, 450.0)
PET_TARGET_X_BOUNDS: Final[tuple[float, float]] = (240.0, 780.0)
DEFAULT_PET_POS: Final[tuple[float, float]] = (512.0, 340.0)
DEFAULT_BALL_POS: Final[tuple[float, float]] = (512.0, 440.0)

# UI layout constants
STATS_ORIGINS: Final[tuple[tuple[str, int, tuple[int, int, int], int], ...]] = (
    ("💖", 138, PINK, 0),
    ("🍎", 246, (255, 150, 40), 1),
    ("✨", 354, ACCENT_BLUE, 2),
)
SPECIES_BUTTON_X: Final[tuple[int, ...]] = (470, 550, 630)
TAB_X_START: Final = 95
TAB_X_STEP: Final = 170
TAB_SIZE: Final[tuple[int, int]] = (155, 84)

MAX_PARTICLES: Final = 96
MAX_BUBBLES: Final = 32

__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "STORAGE_KEY",
    "ROOM_WALL",
    "ROOM_FLOOR",
    "NIGHT_WALL",
    "NIGHT_FLOOR",
    "WHITE",
    "DARK_TEXT",
    "GOLD",
    "PINK",
    "PASTEL_PINK",
    "ACCENT_BLUE",
    "VALID_SPECIES",
    "VALID_ACCESSORIES",
    "VALID_TABS",
    "SPECIES_ICONS",
    "RUG_RECT",
    "FLOOR_Y",
    "BALL_BOUNDS_X",
    "BALL_BOUNDS_Y",
    "PET_TARGET_X_BOUNDS",
    "DEFAULT_PET_POS",
    "DEFAULT_BALL_POS",
    "STATS_ORIGINS",
    "SPECIES_BUTTON_X",
    "TAB_X_START",
    "TAB_X_STEP",
    "TAB_SIZE",
    "MAX_PARTICLES",
    "MAX_BUBBLES",
]
