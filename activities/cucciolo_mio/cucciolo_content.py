"""Authoritative content for My Cute Pet (Cucciolo Mio).

Pure data, no pygame and no Greia IO. The Activity is one experience: the
child adopts a pet (shared ``creature.pet.*`` art), names it with a picture
name tag, and then looks after it for one finite "day". Each need is shown
only by the pet's body language (the library's need-state variants); the
child reads it and chooses the matching care from a picture tray. The day
always ends with bedtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
# The historical key is kept so earlier saves (schema 3, meters) migrate.
STORAGE_KEY: Final = "cucciolo_mio.state.v3"


class Need(StrEnum):
    """What the pet needs; each one is a ``creature.pet.*`` art variant."""

    HUNGRY = "hungry"
    DIRTY = "dirty"
    PLAYFUL = "playful"
    HURT = "hurt"
    SLEEPY = "sleepy"


class Care(StrEnum):
    """A care tool in the tray; exactly one answers each need."""

    FOOD = "food"
    BATH = "bath"
    BALL = "ball"
    PLASTER = "plaster"
    BED = "bed"


class Room(StrEnum):
    """Cozy rooms composed from shared ``bg.indoor_room`` walls and floors."""

    PLAYROOM = "playroom"  # the pet's home room, where needs show up
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    BEDROOM = "bedroom"


@dataclass(frozen=True, slots=True)
class RoomKit:
    wall: str
    floor: str

    @property
    def layers(self) -> tuple[str, str]:
        return (self.wall, self.floor)


ROOMS: Final[dict[Room, RoomKit]] = {
    Room.PLAYROOM: RoomKit("bg.indoor_room.wall_playroom", "bg.indoor_room.floor_wood"),
    Room.KITCHEN: RoomKit("bg.indoor_room.wall_kitchen", "bg.indoor_room.floor_tile"),
    Room.BATHROOM: RoomKit("bg.indoor_room.wall_bathroom", "bg.indoor_room.floor_tile"),
    Room.BEDROOM: RoomKit("bg.indoor_room.wall_bedroom", "bg.indoor_room.floor_carpet"),
}


@dataclass(frozen=True, slots=True)
class CareKind:
    """How one care is done: its room, how many child actions it takes and its event."""

    care: Care
    need: Need
    room: Room
    steps: int
    event_id: str


CARES: Final[dict[Care, CareKind]] = {
    Care.FOOD: CareKind(Care.FOOD, Need.HUNGRY, Room.KITCHEN, 3, "pet.fed"),
    Care.BATH: CareKind(Care.BATH, Need.DIRTY, Room.BATHROOM, 3, "pet.groomed"),
    Care.BALL: CareKind(Care.BALL, Need.PLAYFUL, Room.PLAYROOM, 3, "pet.played"),
    Care.PLASTER: CareKind(Care.PLASTER, Need.HURT, Room.PLAYROOM, 3, "pet.comforted"),
    Care.BED: CareKind(Care.BED, Need.SLEEPY, Room.BEDROOM, 2, "pet.tucked_in"),
}
CARE_FOR_NEED: Final[dict[Need, Care]] = {kind.need: care for care, kind in CARES.items()}
TRAY_ORDER: Final[tuple[Care, ...]] = (Care.FOOD, Care.BATH, Care.BALL, Care.PLASTER, Care.BED)


@dataclass(frozen=True, slots=True)
class Species:
    """An adoptable pet: shared art id, its favourite food and a caption key."""

    species_id: str
    asset_id: str
    food_asset: str
    name_key: str
    # The little owie on the ``hurt`` art, where the plaster goes (fraction of the canvas).
    paw: tuple[float, float]


SPECIES: Final[tuple[Species, ...]] = (
    Species("puppy", "creature.pet.puppy", "prop.vocab.bone", "pet.puppy", (0.609, 0.719)),
    Species("kitten", "creature.pet.kitten", "prop.food.fish", "pet.kitten", (0.609, 0.719)),
    Species("guinea_pig", "creature.pet.guinea_pig", "prop.food.carrot", "pet.guinea_pig", (0.61, 0.777)),
)
SPECIES_BY_ID: Final[dict[str, Species]] = {species.species_id: species for species in SPECIES}
SPECIES_IDS: Final[tuple[str, ...]] = tuple(SPECIES_BY_ID)
# Pre-rework saves stored cat/bunny/puppy (emoji pets).
LEGACY_SPECIES: Final[dict[str, str]] = {"cat": "kitten", "bunny": "guinea_pig", "puppy": "puppy"}


@dataclass(frozen=True, slots=True)
class PetName:
    """A picture name tag: the picture is the choice, the word is spoken/shown."""

    name_id: str  # also the shared vocabulary audio id (spoken name)
    asset_id: str

    @property
    def text_key(self) -> str:
        return f"name.{self.name_id}"


NAMES: Final[tuple[PetName, ...]] = (
    PetName("moon", "prop.vocab.moon"),
    PetName("sun", "prop.nature.sun"),
    PetName("flower", "prop.nature.flower"),
    PetName("apple", "prop.food.apple"),
)
NAMES_BY_ID: Final[dict[str, PetName]] = {name.name_id: name for name in NAMES}


@dataclass(frozen=True, slots=True)
class Level:
    """One rung of the day ladder."""

    daytime_needs: int
    pool: tuple[Need, ...]
    tray: tuple[Care, ...]


LEVELS: Final[tuple[Level, ...]] = (
    Level(3, (Need.HUNGRY, Need.DIRTY, Need.PLAYFUL), (Care.FOOD, Care.BATH, Care.BALL, Care.BED)),
    Level(4, (Need.HUNGRY, Need.DIRTY, Need.PLAYFUL, Need.HURT), TRAY_ORDER),
    Level(5, (Need.HUNGRY, Need.DIRTY, Need.PLAYFUL, Need.HURT), TRAY_ORDER),
)
MAX_LEVEL: Final = len(LEVELS) - 1
MAX_DAY_NEEDS: Final = max(level.daytime_needs for level in LEVELS) + 1

# Gentle daily logic for what tends to come next (weights; filtered by the
# level's pool, never the same need twice in a row): breakfast first, play
# makes the pet muddy or gives it a little bump, a bath or a bump is
# followed by food or play again. Bedtime always ends the day.
FIRST_NEEDS: Final[dict[Need, int]] = {Need.HUNGRY: 3, Need.PLAYFUL: 1, Need.DIRTY: 1}
NEXT_NEEDS: Final[dict[Need, dict[Need, int]]] = {
    Need.HUNGRY: {Need.PLAYFUL: 3, Need.DIRTY: 1, Need.HURT: 1},
    Need.PLAYFUL: {Need.DIRTY: 2, Need.HURT: 2, Need.HUNGRY: 1},
    Need.DIRTY: {Need.HUNGRY: 2, Need.PLAYFUL: 2, Need.HURT: 1},
    Need.HURT: {Need.HUNGRY: 1, Need.PLAYFUL: 1, Need.DIRTY: 1},
}


__all__ = [
    "CARES",
    "CARE_FOR_NEED",
    "Care",
    "CareKind",
    "FIRST_NEEDS",
    "LEGACY_SPECIES",
    "LEVELS",
    "Level",
    "MAX_DAY_NEEDS",
    "MAX_LEVEL",
    "NAMES",
    "NAMES_BY_ID",
    "NEXT_NEEDS",
    "Need",
    "PetName",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "ROOMS",
    "Room",
    "RoomKit",
    "SPECIES",
    "SPECIES_BY_ID",
    "SPECIES_IDS",
    "STORAGE_KEY",
    "Species",
    "TRAY_ORDER",
]
