"""Acquario Magico — content constants (geometry, species, storage).

Pure data. No pygame imports, no side effects. Anything that
changes only when the catalogue is reauthored lives here so the
runtime modules can be reasoned about independently.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict


REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600

STORAGE_KEY = "acquario_magico.progress.v1"

# Path of the runtime-baked PNG assets that the Activity uses for
# sprites and decor. Source SVGs live next to it under
# ``assets/source/``; the build pipeline renders them to PNG.
ASSETS_DIR: Path = Path(__file__).resolve().parent / "assets" / "runtime"


class ToolIndex:
    """Stable constants for the bottom toolbar tools.

    The toolbar indexes are part of the Activity's UX contract;
    a downstream render or input branch that uses a raw integer
    would be hard to read, so the index symbols are exported as
    attributes of this class.
    """

    SPAWN = 0
    FEED = 1
    BUBBLES = 2
    DAY_NIGHT = 3


class _Species(TypedDict):
    id: str
    name_it: str
    name_en: str
    color: tuple[int, int, int]
    size: int
    w: int
    h: int
    speed: float
    behavior: str


SPECIES: list[_Species] = [
    {
        "id": "clownfish",
        "name_it": "Pesce Pagliaccio 🐠",
        "name_en": "Clownfish 🐠",
        "color": (249, 115, 22),
        "size": 36,
        "w": 72,
        "h": 54,
        "speed": 1.4,
        "behavior": "dart",
    },
    {
        "id": "turtle",
        "name_it": "Tartaruga 🐢",
        "name_en": "Sea Turtle 🐢",
        "color": (34, 197, 94),
        "size": 44,
        "w": 88,
        "h": 66,
        "speed": 0.9,
        "behavior": "glide",
    },
    {
        "id": "octopus",
        "name_it": "Polipetto 🐙",
        "name_en": "Octopus 🐙",
        "color": (236, 72, 153),
        "size": 40,
        "w": 76,
        "h": 76,
        "speed": 1.1,
        "behavior": "pulse",
    },
    {
        "id": "dolphin",
        "name_it": "Delfino 🐬",
        "name_en": "Dolphin 🐬",
        "color": (59, 130, 246),
        "size": 52,
        "w": 104,
        "h": 70,
        "speed": 1.8,
        "behavior": "leap",
    },
    {
        "id": "puffer",
        "name_it": "Pesce Palla 🐡",
        "name_en": "Pufferfish 🐡",
        "color": (234, 179, 8),
        "size": 38,
        "w": 76,
        "h": 76,
        "speed": 1.0,
        "behavior": "puffer",
    },
    {
        "id": "seahorse",
        "name_it": "Cavalluccio 🌿",
        "name_en": "Seahorse 🌿",
        "color": (244, 114, 182),
        "size": 36,
        "w": 50,
        "h": 70,
        "speed": 0.8,
        "behavior": "vertical",
    },
    {
        "id": "jellyfish",
        "name_it": "Medusa 🪼",
        "name_en": "Jellyfish 🪼",
        "color": (168, 85, 247),
        "size": 38,
        "w": 64,
        "h": 76,
        "speed": 0.7,
        "behavior": "float",
    },
    {
        "id": "starfish",
        "name_it": "Stella Marina ⭐",
        "name_en": "Starfish ⭐",
        "color": (244, 63, 94),
        "size": 34,
        "w": 60,
        "h": 60,
        "speed": 0.4,
        "behavior": "floor",
    },
]


# Hard caps. The Activity must not accumulate unbounded lists
# even if a child spends a long time on it.
MAX_CREATURES = 20
MAX_PERSISTED_CREATURES = 16
AUTOSAVE_INTERVAL_SECONDS = 10.0
