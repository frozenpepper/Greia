"""Baia delle Orche — content constants (geometry, cast of orcas, foods, art ids).

Pure data: no Pygame imports and no side effects. Anything that only changes
when the bay is reauthored lives here so the model, renderer, controls and app
can be reasoned about independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
# Horizon of the fjord. It sits inside the shared scene recipe's horizon band
# (y 280-360) and leaves the orcas a deep band of water to swim in.
WATER_SURFACE_Y = 290.0
# Lowest centre an orca swims to: bigger orcas stop higher so even big Oskar
# never dips under the toolbar (see ``OrcaEntity.max_y``).
ORCA_MAX_Y = REFERENCE_HEIGHT - 95.0

# The save key is part of the child-data contract: keep it stable so existing
# bays load (new fields are optional and default safely).
STORAGE_KEY = "baia_delle_orche.progress.v1"
SAVE_SCHEMA = 2

# Activity-private renditions (sources live in ``assets/source`` and are
# rendered with rsvg-convert at authoring time).
PACKAGE_ROOT: Path = Path(__file__).resolve().parent
ASSETS_DIR: Path = PACKAGE_ROOT / "assets" / "runtime"

# Primary Collection hue (play -> ocean) for the shared control kit.
CONTROL_ACCENT = "ocean"


class Tool:
    """Stable indexes of the bay's tools (also the 1-6 keyboard shortcuts).

    FEED/CUDDLE/PLAY/SONG are exclusive modes that decide what a tap in the
    water does. DAY_NIGHT and TITO are one-shot actions: using them never
    changes the current mode.
    """

    FEED = 0
    CUDDLE = 1
    PLAY = 2
    SONG = 3
    DAY_NIGHT = 4
    TITO = 5


MODE_IDS: dict[int, str] = {
    Tool.FEED: "feed",
    Tool.CUDDLE: "cuddle",
    Tool.PLAY: "play",
    Tool.SONG: "song",
}


class FoodType(Enum):
    """Orca food the child can choose. All three are real orca food."""

    HERRING = "herring"
    SALMON = "salmon"
    SQUID = "squid"


@dataclass(frozen=True, slots=True)
class ArtRef:
    """Where one picture comes from: a shared library id or a private stem."""

    shared: str | None = None
    private: str | None = None


FOOD_ART: dict[str, ArtRef] = {
    FoodType.HERRING.value: ArtRef(private="food_herring"),
    FoodType.SALMON.value: ArtRef(shared="prop.food.fish"),
    FoodType.SQUID.value: ArtRef(private="food_squid"),
}


@dataclass(frozen=True, slots=True)
class OrcaLook:
    """Visual identity of one orca: art, drawn box and name key.

    The three friends stay distinguishable by silhouette, not only by size:
    Kiko is a calf, Luna has the swept-back fin, Oskar the tall upright fin
    and grey saddle patch of a grown male.
    """

    art: ArtRef
    box: tuple[int, int]


ORCA_LOOKS: dict[str, OrcaLook] = {
    "kiko": OrcaLook(ArtRef(shared="creature.marine.orca_calf"), (112, 70)),
    "luna": OrcaLook(ArtRef(shared="creature.marine.orca_adult"), (200, 126)),
    "oskar": OrcaLook(ArtRef(private="orca_elder"), (300, 190)),
}

ORCA_IDS: tuple[str, ...] = ("kiko", "luna", "oskar")

# Tito's six approved, recorded orca facts (spoken from assets/audio/<lang>).
FACT_KEYS: tuple[str, ...] = (
    "fact_breach",
    "fact_swallow",
    "fact_sleep",
    "fact_song",
    "fact_pod",
    "fact_fin",
)
FACT_SECONDS = 12.0

# Song bells (DO MI SOL DO'): colour carries the pitch for pre-readers.
BELL_COLORS: tuple[tuple[int, int, int], ...] = (
    (244, 111, 97),
    (255, 194, 52),
    (74, 145, 216),
    (148, 100, 201),
)
BELL_LABELS: tuple[str, ...] = ("DO", "MI", "SOL", "DO")
BELL_SIZE = 64
BELL_CENTERS: tuple[tuple[int, int], ...] = tuple(
    (330 + index * 112, int(WATER_SURFACE_Y) - 2) for index in range(4)
)

BALL_START = (250.0, WATER_SURFACE_Y)
HOOP_POSITION = (860.0, WATER_SURFACE_Y - 18.0)
HOOP_SIZE = (64, 100)

# Hard caps: the bay must not accumulate unbounded lists in a long session.
MAX_FOODS = 24
MAX_EFFECTS = 24
AUTOSAVE_INTERVAL_SECONDS = 5.0
MAX_SAVED_COUNTER = 1_000_000_000
MAX_SAVED_STARS = 999

# Gentle optional invitations (never required, never failed).
MISSIONS_PER_STAR = 3
FIRST_MISSION_DELAY_SECONDS = 15.0
NEXT_MISSION_DELAY_SECONDS = 9.0
MISSION_HINT_SECONDS = 6.0
MISSION_HINT_REPEAT_SECONDS = 10.0
MISSION_IDLE_RETIRE_SECONDS = 45.0
NAME_TAG_SECONDS = 1.8
HAPPY_SECONDS = 1.6

__all__ = [
    "ASSETS_DIR",
    "AUTOSAVE_INTERVAL_SECONDS",
    "ArtRef",
    "BALL_START",
    "BELL_CENTERS",
    "BELL_COLORS",
    "BELL_LABELS",
    "BELL_SIZE",
    "CONTROL_ACCENT",
    "FACT_KEYS",
    "FACT_SECONDS",
    "FIRST_MISSION_DELAY_SECONDS",
    "FOOD_ART",
    "FoodType",
    "HAPPY_SECONDS",
    "HOOP_POSITION",
    "HOOP_SIZE",
    "MAX_EFFECTS",
    "MAX_FOODS",
    "MAX_SAVED_COUNTER",
    "MAX_SAVED_STARS",
    "MISSION_HINT_REPEAT_SECONDS",
    "MISSION_HINT_SECONDS",
    "MISSION_IDLE_RETIRE_SECONDS",
    "MISSIONS_PER_STAR",
    "MODE_IDS",
    "NAME_TAG_SECONDS",
    "NEXT_MISSION_DELAY_SECONDS",
    "ORCA_IDS",
    "ORCA_LOOKS",
    "ORCA_MAX_Y",
    "OrcaLook",
    "PACKAGE_ROOT",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SAVE_SCHEMA",
    "STORAGE_KEY",
    "Tool",
    "WATER_SURFACE_Y",
]
