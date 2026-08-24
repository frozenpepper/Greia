"""Catalogue and option definitions for Morbidi Mostriciattoli."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class Category(StrEnum):
    BODY_SHAPE = "body_shape"
    BODY_COLOR = "body_color"
    EYES = "eyes"
    MOUTH = "mouth"
    TUFT = "tuft"
    ACCESSORY = "accessory"


@dataclass(frozen=True, slots=True)
class MonsterOption:
    option_id: str
    category: Category
    name_key: str
    symbol: str


# 1. 6 Body Shapes
BODY_SHAPES: Final[tuple[MonsterOption, ...]] = (
    MonsterOption("round", Category.BODY_SHAPE, "shape.round", "⚪"),
    MonsterOption("pear", Category.BODY_SHAPE, "shape.pear", "🍐"),
    MonsterOption("square", Category.BODY_SHAPE, "shape.square", "⏹️"),
    MonsterOption("bean", Category.BODY_SHAPE, "shape.bean", "🫘"),
    MonsterOption("egg", Category.BODY_SHAPE, "shape.egg", "🥚"),
    MonsterOption("star", Category.BODY_SHAPE, "shape.star", "⭐"),
)

# 2. 8 Body Colors (Primary & Accent RGB)
@dataclass(frozen=True, slots=True)
class ColorOption:
    option_id: str
    primary_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    name_key: str
    symbol: str


BODY_COLORS: Final[tuple[ColorOption, ...]] = (
    ColorOption("fluffy_pink", (244, 114, 182), (219, 39, 119), "color.pink", "🩷"),
    ColorOption("sunny_yellow", (253, 224, 71), (202, 138, 4), "color.yellow", "💛"),
    ColorOption("mint_green", (134, 239, 172), (22, 163, 74), "color.mint", "💚"),
    ColorOption("sky_blue", (125, 211, 252), (2, 132, 199), "color.sky", "🩵"),
    ColorOption("soft_lavender", (216, 180, 254), (147, 51, 234), "color.lavender", "💜"),
    ColorOption("peach_orange", (253, 186, 116), (234, 88, 12), "color.peach", "🧡"),
    ColorOption("cloud_white", (248, 250, 252), (148, 163, 184), "color.white", "🤍"),
    ColorOption("midnight_teal", (45, 212, 191), (13, 148, 136), "color.teal", "🩵"),
)

# 3. 6 Eye Sets
EYE_OPTIONS: Final[tuple[MonsterOption, ...]] = (
    MonsterOption("cyclops", Category.EYES, "eyes.cyclops", "👁️"),
    MonsterOption("two_dots", Category.EYES, "eyes.two_dots", "👀"),
    MonsterOption("three_sparkles", Category.EYES, "eyes.three", "✨"),
    MonsterOption("sleepy_winks", Category.EYES, "eyes.sleepy", "😌"),
    MonsterOption("big_goggles", Category.EYES, "eyes.goggles", "🥽"),
    MonsterOption("happy_lashes", Category.EYES, "eyes.lashes", "😊"),
)

# 4. 6 Mouths
MOUTH_OPTIONS: Final[tuple[MonsterOption, ...]] = (
    MonsterOption("toothy_smile", Category.MOUTH, "mouth.toothy", "😁"),
    MonsterOption("tongue_out", Category.MOUTH, "mouth.tongue", "😋"),
    MonsterOption("tiny_o", Category.MOUTH, "mouth.tiny_o", "😮"),
    MonsterOption("snaggle_tooth", Category.MOUTH, "mouth.snaggle", "🤓"),
    MonsterOption("broad_grin", Category.MOUTH, "mouth.grin", "😀"),
    MonsterOption("cat_whiskers", Category.MOUTH, "mouth.whiskers", "😺"),
)

# 5. 6 Tufts / Headgear
TUFT_OPTIONS: Final[tuple[MonsterOption, ...]] = (
    MonsterOption("single_horn", Category.TUFT, "tuft.horn", "🦄"),
    MonsterOption("bunny_ears", Category.TUFT, "tuft.bunny", "🐰"),
    MonsterOption("little_antennas", Category.TUFT, "tuft.antennas", "🐛"),
    MonsterOption("dino_spikes", Category.TUFT, "tuft.dino", "🦕"),
    MonsterOption("fuzzy_pom", Category.TUFT, "tuft.pom", "🧶"),
    MonsterOption("crown", Category.TUFT, "tuft.crown", "👑"),
)

# 6. 6 Accessories
ACCESSORY_OPTIONS: Final[tuple[MonsterOption, ...]] = (
    MonsterOption("bow_tie", Category.ACCESSORY, "acc.bowtie", "🎀"),
    MonsterOption("star_pin", Category.ACCESSORY, "acc.star", "⭐"),
    MonsterOption("monocle", Category.ACCESSORY, "acc.monocle", "🧐"),
    MonsterOption("flowered_lei", Category.ACCESSORY, "acc.flower", "🌸"),
    MonsterOption("striped_scarf", Category.ACCESSORY, "acc.scarf", "🧣"),
    MonsterOption("party_hat", Category.ACCESSORY, "acc.hat", "🎉"),
)

# Validation lookups
VALID_SHAPE_IDS: Final[frozenset[str]] = frozenset(o.option_id for o in BODY_SHAPES)
VALID_COLOR_IDS: Final[frozenset[str]] = frozenset(o.option_id for o in BODY_COLORS)
VALID_EYE_IDS: Final[frozenset[str]] = frozenset(o.option_id for o in EYE_OPTIONS)
VALID_MOUTH_IDS: Final[frozenset[str]] = frozenset(o.option_id for o in MOUTH_OPTIONS)
VALID_TUFT_IDS: Final[frozenset[str]] = frozenset(o.option_id for o in TUFT_OPTIONS)
VALID_ACCESSORY_IDS: Final[frozenset[str]] = frozenset(o.option_id for o in ACCESSORY_OPTIONS)

DEFAULT_SHAPE_ID: Final[str] = "round"
DEFAULT_COLOR_ID: Final[str] = "fluffy_pink"
DEFAULT_EYES_ID: Final[str] = "cyclops"
DEFAULT_MOUTH_ID: Final[str] = "snaggle_tooth"
DEFAULT_TUFT_ID: Final[str] = "single_horn"
DEFAULT_ACCESSORY_ID: Final[str] = "bow_tie"
