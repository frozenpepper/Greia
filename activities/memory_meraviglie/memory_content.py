"""Wonder Match content: sticker albums, their subjects and the grid ladder.

Every picture is shared library art addressed by semantic ID
(``prop.vocab.*``, ``prop.food.*``, ``prop.nature.*``, ``creature.marine.*``);
the Activity draws no subject itself. Each album has exactly eight subjects so
the largest board (4x4) uses the whole album and the sticker page has eight
wells. Album backdrops are shared scene layers composed once per album.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "memory_meraviglie.progress.v1"
ALBUM_SIZE: Final = 8

Rgb = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class Subject:
    """One picture of an album: stable id (locale key ``item.<id>``) + art ID."""

    subject_id: str
    asset_id: str


@dataclass(frozen=True, slots=True)
class Album:
    """A themed sticker album (one board theme)."""

    album_id: str
    subjects: tuple[Subject, ...]
    scene: tuple[str, ...]
    cover: tuple[str, str, str]
    tint: Rgb  # album page / cover colour (theme token light step)
    tint_deep: Rgb  # matching base token for contours/accents

    def subject(self, subject_id: str) -> Subject:
        for subject in self.subjects:
            if subject.subject_id == subject_id:
                return subject
        raise KeyError(subject_id)

    @property
    def subject_ids(self) -> tuple[str, ...]:
        return tuple(subject.subject_id for subject in self.subjects)


def _subjects(prefix_by_id: dict[str, str]) -> tuple[Subject, ...]:
    return tuple(Subject(subject_id, asset_id) for subject_id, asset_id in prefix_by_id.items())


ALBUMS: Final[tuple[Album, ...]] = (
    Album(
        "animals",
        _subjects(
            {
                "cat": "prop.vocab.cat",
                "dog": "prop.vocab.dog",
                "lion": "prop.vocab.lion",
                "elephant": "prop.vocab.elephant",
                "pig": "prop.vocab.pig",
                "frog": "prop.vocab.frog",
                "penguin": "prop.vocab.penguin",
                "mouse": "prop.vocab.mouse",
            }
        ),
        ("bg.meadow_day.sky", "bg.meadow_day.far", "bg.meadow_day.mid", "bg.meadow_day.ground"),
        ("lion", "cat", "elephant"),
        (217, 242, 208),  # mint
        (89, 184, 106),  # leaf
    ),
    Album(
        "sea",
        _subjects(
            {
                "fish": "creature.marine.clownfish",
                "turtle": "creature.marine.turtle",
                "octopus": "creature.marine.octopus",
                "jellyfish": "creature.marine.jellyfish",
                "seahorse": "creature.marine.seahorse",
                "crab": "creature.marine.crab",
                "starfish": "creature.marine.starfish",
                "dolphin": "creature.marine.dolphin",
            }
        ),
        ("bg.underwater.water", "bg.underwater.far", "bg.underwater.mid", "bg.underwater.ground"),
        ("octopus", "fish", "turtle"),
        (207, 234, 247),  # sky
        (74, 145, 216),  # ocean
    ),
    Album(
        "food",
        _subjects(
            {
                "apple": "prop.food.apple",
                "banana": "prop.food.banana",
                "carrot": "prop.food.carrot",
                "grapes": "prop.vocab.grapes",
                "pear": "prop.vocab.pear",
                "cake": "prop.vocab.cake",
                "pizza": "prop.vocab.pizza",
                "ice_cream": "prop.vocab.ice_cream",
            }
        ),
        ("bg.indoor_room.wall_kitchen", "bg.indoor_room.floor_tile"),
        ("cake", "apple", "ice_cream"),
        (245, 214, 223),  # rose
        (244, 111, 97),  # coral
    ),
    Album(
        "vehicles",
        _subjects(
            {
                "car": "prop.vocab.car",
                "bus": "prop.vocab.bus",
                "train": "prop.vocab.train",
                "boat": "prop.vocab.boat",
                "plane": "prop.vocab.plane",
                "rocket": "prop.vocab.rocket",
                "bicycle": "prop.vocab.bicycle",
                "kite": "prop.vocab.kite",
            }
        ),
        ("bg.sky_clouds.sky", "bg.sky_clouds.far", "bg.sky_clouds.mid"),
        ("rocket", "car", "train"),
        (207, 237, 231),  # aqua
        (68, 184, 174),  # turquoise
    ),
    Album(
        "nature",
        _subjects(
            {
                "flower": "prop.nature.flower",
                "mushroom": "prop.nature.mushroom",
                "sun": "prop.nature.sun",
                "moon": "prop.vocab.moon",
                "rainbow": "prop.nature.rainbow",
                "leaf": "prop.nature.leaf_autumn",
                "snowflake": "prop.nature.snowflake",
                "acorn": "prop.nature.acorn",
            }
        ),
        ("bg.woodland_pond.sky", "bg.woodland_pond.far", "bg.woodland_pond.mid", "bg.woodland_pond.ground"),
        ("rainbow", "flower", "mushroom"),
        (238, 221, 186),  # sand
        (243, 154, 56),  # orange
    ),
)

ALBUM_IDS: Final[tuple[str, ...]] = tuple(album.album_id for album in ALBUMS)
PICKER_SCENE: Final[tuple[str, ...]] = ("bg.indoor_room.wall_playroom", "bg.indoor_room.floor_wood")


def album_by_id(album_id: str) -> Album:
    for album in ALBUMS:
        if album.album_id == album_id:
            return album
    return ALBUMS[0]


@dataclass(frozen=True, slots=True)
class GridSpec:
    """One rung of the board ladder."""

    cols: int
    rows: int

    @property
    def pairs(self) -> int:
        return self.cols * self.rows // 2


# 2x2 -> 3x2 -> 4x3 -> 4x4 (adaptive; see ``memory_model.adapt_level``).
LEVELS: Final[tuple[GridSpec, ...]] = (GridSpec(2, 2), GridSpec(3, 2), GridSpec(4, 3), GridSpec(4, 4))
MAX_LEVEL: Final = len(LEVELS) - 1

assert all(len(album.subjects) == ALBUM_SIZE for album in ALBUMS)
assert max(spec.pairs for spec in LEVELS) <= ALBUM_SIZE


__all__ = [
    "ALBUMS",
    "ALBUM_IDS",
    "ALBUM_SIZE",
    "Album",
    "GridSpec",
    "LEVELS",
    "MAX_LEVEL",
    "PICKER_SCENE",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "Subject",
    "album_by_id",
]
