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

# The save key is part of the child-data contract: keep it stable so
# existing aquariums load (new fields are optional and default safely).
STORAGE_KEY = "acquario_magico.progress.v1"

# Activity-private runtime renditions (source SVGs live under
# ``assets/source/`` and are rendered with rsvg-convert at authoring time).
ASSETS_DIR: Path = Path(__file__).resolve().parent / "assets" / "runtime"

# Primary Collection hue (explore -> leaf) for the shared control kit.
CONTROL_ACCENT = "leaf"

# Sand line in the shared ``bg.underwater.*`` composition: creatures that
# walk on the floor stand here and food settles here.
SAND_Y = 488
FLOOR_CREATURE_Y = REFERENCE_HEIGHT - 110
WATER_TOP_Y = 90
WATER_BOTTOM_Y = REFERENCE_HEIGHT - 130


class ToolIndex:
    """Stable constants for the bottom toolbar tools.

    The toolbar indexes are part of the Activity's UX contract;
    a downstream render or input branch that uses a raw integer
    would be hard to read, so the index symbols are exported as
    attributes of this class. ``DAY_NIGHT`` is a toggle, not an
    exclusive tool: toggling never changes what a tap in the water does.
    """

    SPAWN = 0
    FEED = 1
    BUBBLES = 2
    DAY_NIGHT = 3


TOOL_IDS: dict[int, str] = {
    ToolIndex.SPAWN: "creatures",
    ToolIndex.FEED: "feed",
    ToolIndex.BUBBLES: "bubbles",
}


class _Species(TypedDict):
    id: str
    name_key: str
    # Shared catalogue id (``creature.marine.*``) or ``None`` when the
    # creature is Activity-private art (``private`` stem in ASSETS_DIR).
    visual: str | None
    private: str | None
    color: tuple[int, int, int]
    size: int
    w: int
    h: int
    speed: float
    behavior: str
    eats: bool
    glows: bool


SPECIES: list[_Species] = [
    {
        "id": "clownfish",
        "name_key": "creature.clownfish",
        "visual": "creature.marine.clownfish",
        "private": None,
        "color": (249, 115, 22),
        "size": 36,
        "w": 84,
        "h": 66,
        "speed": 1.4,
        "behavior": "dart",
        "eats": True,
        "glows": False,
    },
    {
        "id": "turtle",
        "name_key": "creature.turtle",
        "visual": "creature.marine.turtle",
        "private": None,
        "color": (34, 197, 94),
        "size": 44,
        "w": 108,
        "h": 74,
        "speed": 0.9,
        "behavior": "glide",
        "eats": True,
        "glows": False,
    },
    {
        "id": "octopus",
        "name_key": "creature.octopus",
        "visual": "creature.marine.octopus",
        "private": None,
        "color": (236, 72, 153),
        "size": 40,
        "w": 86,
        "h": 86,
        "speed": 1.1,
        "behavior": "pulse",
        "eats": True,
        "glows": False,
    },
    {
        "id": "dolphin",
        "name_key": "creature.dolphin",
        "visual": "creature.marine.dolphin",
        "private": None,
        "color": (59, 130, 246),
        "size": 52,
        "w": 138,
        "h": 64,
        "speed": 1.8,
        "behavior": "leap",
        "eats": True,
        "glows": False,
    },
    {
        "id": "puffer",
        "name_key": "creature.puffer",
        "visual": None,
        "private": "pufferfish",
        "color": (234, 179, 8),
        "size": 38,
        "w": 80,
        "h": 80,
        "speed": 1.0,
        "behavior": "puffer",
        "eats": True,
        "glows": False,
    },
    {
        "id": "seahorse",
        "name_key": "creature.seahorse",
        "visual": "creature.marine.seahorse",
        "private": None,
        "color": (244, 114, 182),
        "size": 36,
        "w": 58,
        "h": 84,
        "speed": 0.8,
        "behavior": "vertical",
        "eats": True,
        "glows": False,
    },
    {
        "id": "jellyfish",
        "name_key": "creature.jellyfish",
        "visual": "creature.marine.jellyfish",
        "private": None,
        "color": (168, 85, 247),
        "size": 38,
        "w": 66,
        "h": 86,
        "speed": 0.7,
        "behavior": "float",
        "eats": False,
        "glows": True,
    },
    {
        "id": "starfish",
        "name_key": "creature.starfish",
        "visual": "creature.marine.starfish",
        "private": None,
        "color": (244, 63, 94),
        "size": 34,
        "w": 64,
        "h": 64,
        "speed": 0.4,
        "behavior": "floor",
        "eats": False,
        "glows": False,
    },
]

SPECIES_BY_ID: dict[str, _Species] = {species["id"]: species for species in SPECIES}


# Hard caps. The Activity must not accumulate unbounded lists
# even if a child spends a long time on it.
MAX_CREATURES = 20
MAX_PERSISTED_CREATURES = 16
MAX_FOOD_PELLETS = 48
MAX_BUBBLES = 96
MAX_PARTICLES = 160
MAX_EFFECTS = 24
AUTOSAVE_INTERVAL_SECONDS = 10.0

# Gentle optional missions (never required, never timed out as failure).
MISSIONS_PER_PEARL = 3
FIRST_MISSION_DELAY_SECONDS = 15.0
NEXT_MISSION_DELAY_SECONDS = 9.0
MISSION_IDLE_RETIRE_SECONDS = 45.0
NAME_TAG_SECONDS = 1.8
MAX_SAVED_STARS = 999
