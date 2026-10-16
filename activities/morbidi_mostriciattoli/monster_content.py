"""Part catalogue for Fluffy Monsters (pure data, no Pygame).

A monster is nine picture choices: body shape, colour, pattern, eyes, mouth,
horns/ears ("top"), arms, feet and one accessory. Every option names the
Activity-private art it uses (``assets/runtime/parts/<stem>.png``, authored as
SVG under ``assets/source/parts/`` per GREIA_SVG_AUTHORING_RULES) and how the
compositor places and tints it:

* **anchors** — parts are drawn on a 256-unit monster canvas at canonical
  anchors (eyes centre 128,128 · head top 128,80 · right arm root 190,150 ·
  right foot root 152,208 · neck 128,188). Each body shape moves those anchors
  to its own face/top/arms/feet, so every part fits every body;
* **pairs** — arms, feet, horns and ears are authored once for the right side
  and mirrored for the left;
* **tint** — silhouettes in body colour (gradient light -> base from the palette
  token), shade (base mixed with ink) or light (base mixed with white). Fixed
  parts keep their own colours.

The look is the Puff archetype of the Greia character grammar and is kept
deliberately distinct from Momo (no purple scalloped body, no antennae, no
turquoise feet). Stable option IDs are stored in saves; renamed IDs from the
first release are mapped by ``LEGACY_OPTION_IDS``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

MAX_SAVED_PORTRAITS: Final = 24
GALLERY_PAGE_SIZE: Final = 6
MAX_NAME_SYLLABLES: Final = 3
SHARE_ROLE: Final = "picture"  # Painting/Shape Garden/Teatrino/Posta accept it


class Category(StrEnum):
    """One drawer of the studio (stored values are stable save keys)."""

    BODY_SHAPE = "body_shape"
    BODY_COLOR = "body_color"
    PATTERN = "pattern"
    EYES = "eyes"
    MOUTH = "mouth"
    TUFT = "tuft"  # horns and ears
    ARMS = "arms"
    FEET = "feet"
    ACCESSORY = "accessory"


CATEGORY_ORDER: Final[tuple[Category, ...]] = (
    Category.BODY_SHAPE,
    Category.BODY_COLOR,
    Category.PATTERN,
    Category.EYES,
    Category.MOUTH,
    Category.TUFT,
    Category.ARMS,
    Category.FEET,
    Category.ACCESSORY,
)


class Tint(StrEnum):
    NONE = "none"
    BODY = "body"
    SHADE = "shade"
    LIGHT = "light"


class Anchor(StrEnum):
    FACE = "face"
    TOP = "top"
    ARM = "arm"
    FOOT = "foot"
    NECK = "neck"


class Layer(StrEnum):
    BEHIND = "behind"  # roots hidden by the body (arms, horns, ears)
    FRONT = "front"


@dataclass(frozen=True, slots=True)
class PartOption:
    """One choice in a drawer and how its art is placed."""

    option_id: str
    category: Category
    art: str | None  # file stem under assets/runtime/parts (None = nothing)
    tint: Tint = Tint.NONE
    anchor: Anchor = Anchor.FACE
    layer: Layer = Layer.FRONT
    pair: bool = False
    follows_spread: bool = False  # a single top part that sits beside the head

    @property
    def is_none(self) -> bool:
        return self.art is None


@dataclass(frozen=True, slots=True)
class BodyShape:
    """A body silhouette and where its face, top, arms and feet sit."""

    option_id: str
    category: Category
    art: str
    face_dy: int
    top_dy: int
    spread_dx: int
    arm: tuple[int, int]
    foot: tuple[int, int]
    neck_dy: int
    shadow_rx: int


@dataclass(frozen=True, slots=True)
class ColorOption:
    """A body colour (theme token or a derived step of one)."""

    option_id: str
    category: Category
    base: tuple[int, int, int]
    token: str


# Authored anchor roots on the 256-unit canvas (see module docstring).
AUTHORED_ARM_ROOT: Final = (190, 150)
AUTHORED_FOOT_ROOT: Final = (152, 208)

C = Category

BODY_SHAPES: Final[tuple[BodyShape, ...]] = (
    BodyShape("round", C.BODY_SHAPE, "body_round", face_dy=4, top_dy=0, spread_dx=0, arm=(190, 150), foot=(152, 208), neck_dy=2, shadow_rx=64),
    BodyShape("egg", C.BODY_SHAPE, "body_egg", face_dy=-10, top_dy=-26, spread_dx=-10, arm=(176, 146), foot=(148, 210), neck_dy=-10, shadow_rx=54),
    BodyShape("bean", C.BODY_SHAPE, "body_bean", face_dy=16, top_dy=24, spread_dx=14, arm=(210, 164), foot=(168, 208), neck_dy=10, shadow_rx=82),
    BodyShape("pear", C.BODY_SHAPE, "body_pear", face_dy=-4, top_dy=-14, spread_dx=-10, arm=(190, 162), foot=(160, 210), neck_dy=-2, shadow_rx=70),
    BodyShape("square", C.BODY_SHAPE, "body_square", face_dy=2, top_dy=-2, spread_dx=8, arm=(190, 150), foot=(158, 208), neck_dy=0, shadow_rx=64),
    BodyShape("star", C.BODY_SHAPE, "body_star", face_dy=10, top_dy=-30, spread_dx=-14, arm=(200, 128), foot=(180, 222), neck_dy=6, shadow_rx=74),
)

# Colours: Greia palette tokens or their derived light steps
# (GREIA_SVG_AUTHORING_RULES §2). No deep purple: that is Momo's identity.
BODY_COLORS: Final[tuple[ColorOption, ...]] = (
    ColorOption("sky_blue", C.BODY_COLOR, (98, 160, 222), "ocean (light 15%)"),
    ColorOption("midnight_teal", C.BODY_COLOR, (68, 184, 174), "turquoise"),
    ColorOption("mint_green", C.BODY_COLOR, (122, 198, 136), "leaf (light 25%)"),
    ColorOption("sunny_yellow", C.BODY_COLOR, (255, 194, 52), "sunshine"),
    ColorOption("peach_orange", C.BODY_COLOR, (243, 154, 56), "orange"),
    ColorOption("fluffy_pink", C.BODY_COLOR, (234, 135, 170), "raspberry (light 30%)"),
    ColorOption("soft_lavender", C.BODY_COLOR, (190, 162, 223), "grape (light 40%)"),
    ColorOption("cloud_white", C.BODY_COLOR, (246, 236, 218), "cream"),
)

PATTERN_OPTIONS: Final[tuple[PartOption, ...]] = (
    PartOption("none", C.PATTERN, None),
    PartOption("spots", C.PATTERN, "pattern_spots", tint=Tint.SHADE),
    PartOption("stripes", C.PATTERN, "pattern_stripes", tint=Tint.SHADE),
    PartOption("hearts", C.PATTERN, "pattern_hearts", tint=Tint.LIGHT),
    PartOption("stars", C.PATTERN, "pattern_stars", tint=Tint.LIGHT),
    PartOption("belly", C.PATTERN, "pattern_belly"),
)

EYE_OPTIONS: Final[tuple[PartOption, ...]] = (
    PartOption("two_dots", C.EYES, "eyes_two_dots"),
    PartOption("cyclops", C.EYES, "eyes_cyclops"),
    PartOption("three_sparkles", C.EYES, "eyes_three_sparkles"),
    PartOption("big_goggles", C.EYES, "eyes_big_goggles"),
    PartOption("sleepy_winks", C.EYES, "eyes_sleepy_winks"),
    PartOption("happy_lashes", C.EYES, "eyes_happy_lashes"),
)

MOUTH_OPTIONS: Final[tuple[PartOption, ...]] = (
    PartOption("broad_grin", C.MOUTH, "mouth_broad_grin"),
    PartOption("toothy_smile", C.MOUTH, "mouth_toothy_smile"),
    PartOption("tongue_out", C.MOUTH, "mouth_tongue_out"),
    PartOption("tiny_o", C.MOUTH, "mouth_tiny_o"),
    PartOption("snaggle_tooth", C.MOUTH, "mouth_snaggle_tooth"),
    PartOption("cat_whiskers", C.MOUTH, "mouth_cat_whiskers"),
)

TUFT_OPTIONS: Final[tuple[PartOption, ...]] = (
    PartOption("none", C.TUFT, None, anchor=Anchor.TOP),
    PartOption("horns", C.TUFT, "top_horns", anchor=Anchor.TOP, layer=Layer.BEHIND, pair=True),
    PartOption("long_ears", C.TUFT, "top_long_ears", tint=Tint.BODY, anchor=Anchor.TOP, layer=Layer.BEHIND, pair=True),
    PartOption("round_ears", C.TUFT, "top_round_ears", tint=Tint.BODY, anchor=Anchor.TOP, layer=Layer.BEHIND, pair=True),
    PartOption("spikes", C.TUFT, "top_spikes", tint=Tint.SHADE, anchor=Anchor.TOP, layer=Layer.BEHIND),
    PartOption("tuft", C.TUFT, "top_tuft", tint=Tint.SHADE, anchor=Anchor.TOP, layer=Layer.BEHIND),
    PartOption("crown", C.TUFT, "top_crown", anchor=Anchor.TOP),
)

ARM_OPTIONS: Final[tuple[PartOption, ...]] = (
    PartOption("none", C.ARMS, None, anchor=Anchor.ARM),
    PartOption("stubby", C.ARMS, "arms_stubby", tint=Tint.BODY, anchor=Anchor.ARM, layer=Layer.BEHIND, pair=True),
    PartOption("noodle", C.ARMS, "arms_noodle", tint=Tint.BODY, anchor=Anchor.ARM, layer=Layer.BEHIND, pair=True),
    PartOption("mitts", C.ARMS, "arms_mitts", tint=Tint.BODY, anchor=Anchor.ARM, layer=Layer.BEHIND, pair=True),
    PartOption("wings", C.ARMS, "arms_wings", anchor=Anchor.ARM, layer=Layer.BEHIND, pair=True),
    PartOption("claws", C.ARMS, "arms_claws", tint=Tint.BODY, anchor=Anchor.ARM, layer=Layer.BEHIND, pair=True),
)

FEET_OPTIONS: Final[tuple[PartOption, ...]] = (
    PartOption("none", C.FEET, None, anchor=Anchor.FOOT),
    PartOption("paws", C.FEET, "feet_paws", tint=Tint.SHADE, anchor=Anchor.FOOT, pair=True),
    PartOption("toes", C.FEET, "feet_toes", tint=Tint.SHADE, anchor=Anchor.FOOT, pair=True),
    PartOption("big", C.FEET, "feet_big", tint=Tint.SHADE, anchor=Anchor.FOOT, pair=True),
    PartOption("boots", C.FEET, "feet_boots", anchor=Anchor.FOOT, pair=True),
    PartOption("spring", C.FEET, "feet_spring", tint=Tint.SHADE, anchor=Anchor.FOOT, pair=True),
)

ACCESSORY_OPTIONS: Final[tuple[PartOption, ...]] = (
    PartOption("none", C.ACCESSORY, None, anchor=Anchor.NECK),
    PartOption("bow_tie", C.ACCESSORY, "acc_bow_tie", anchor=Anchor.NECK),
    PartOption("star_pin", C.ACCESSORY, "acc_star_pin", anchor=Anchor.NECK),
    PartOption("scarf", C.ACCESSORY, "acc_scarf", anchor=Anchor.NECK),
    PartOption("glasses", C.ACCESSORY, "acc_glasses", anchor=Anchor.FACE),
    PartOption("flower", C.ACCESSORY, "acc_flower", anchor=Anchor.TOP, follows_spread=True),
    PartOption("party_hat", C.ACCESSORY, "acc_party_hat", anchor=Anchor.TOP),
)

OPTIONS: Final[dict[Category, tuple]] = {
    C.BODY_SHAPE: BODY_SHAPES,
    C.BODY_COLOR: BODY_COLORS,
    C.PATTERN: PATTERN_OPTIONS,
    C.EYES: EYE_OPTIONS,
    C.MOUTH: MOUTH_OPTIONS,
    C.TUFT: TUFT_OPTIONS,
    C.ARMS: ARM_OPTIONS,
    C.FEET: FEET_OPTIONS,
    C.ACCESSORY: ACCESSORY_OPTIONS,
}

VALID_IDS: Final[dict[Category, frozenset[str]]] = {
    category: frozenset(option.option_id for option in options) for category, options in OPTIONS.items()
}

DEFAULTS: Final[dict[Category, str]] = {
    C.BODY_SHAPE: "round",
    C.BODY_COLOR: "sky_blue",
    C.PATTERN: "none",
    C.EYES: "two_dots",
    C.MOUTH: "broad_grin",
    C.TUFT: "horns",
    C.ARMS: "stubby",
    C.FEET: "paws",
    C.ACCESSORY: "none",
}

# First-release IDs that were renamed (saves keep loading as close matches).
LEGACY_OPTION_IDS: Final[dict[Category, dict[str, str]]] = {
    C.TUFT: {
        "single_horn": "horns",
        "bunny_ears": "long_ears",
        "little_antennas": "round_ears",
        "dino_spikes": "spikes",
        "fuzzy_pom": "tuft",
    },
    C.ACCESSORY: {"monocle": "glasses", "flowered_lei": "flower", "striped_scarf": "scarf"},
}

# Fields that older saves lack get these (not DEFAULTS: an old monster had no arms/feet art).
LEGACY_MISSING: Final[dict[Category, str]] = {C.PATTERN: "none", C.ARMS: "stubby", C.FEET: "paws"}


def option(category: Category, option_id: str):
    for item in OPTIONS[category]:
        if item.option_id == option_id:
            return item
    raise KeyError(f"unknown {category.value} option: {option_id!r}")


def canonical_id(category: Category, raw: object) -> str | None:
    """A stored option ID mapped onto the current catalogue (or None)."""

    if not isinstance(raw, str):
        return None
    mapped = LEGACY_OPTION_IDS.get(category, {}).get(raw, raw)
    return mapped if mapped in VALID_IDS[category] else None


# Names are built from big syllable tiles (no typing). The syllables read the
# same in EN/IT/ES/FR; letters are the taught object here.
SYLLABLES: Final[tuple[str, ...]] = ("BU", "MI", "ZU", "LU", "PO", "KI", "TO", "NA")
SYLLABLE_COLORS: Final[tuple[tuple[int, int, int], ...]] = (
    (244, 111, 97),
    (74, 145, 216),
    (89, 184, 106),
    (148, 100, 201),
    (243, 154, 56),
    (216, 86, 131),
    (68, 184, 174),
    (255, 194, 52),
)
# Picture-selectable presets for the dice (first-release names stay valid).
PRESET_NAMES: Final[tuple[str, ...]] = ("BUBU", "ZUZU", "MIMI", "KIKI", "LULU", "TOTO", "POPO", "NANA", "MIKI", "LUPO")


__all__ = [
    "ACCESSORY_OPTIONS",
    "ARM_OPTIONS",
    "AUTHORED_ARM_ROOT",
    "AUTHORED_FOOT_ROOT",
    "Anchor",
    "BODY_COLORS",
    "BODY_SHAPES",
    "BodyShape",
    "CATEGORY_ORDER",
    "Category",
    "ColorOption",
    "DEFAULTS",
    "EYE_OPTIONS",
    "FEET_OPTIONS",
    "GALLERY_PAGE_SIZE",
    "LEGACY_MISSING",
    "LEGACY_OPTION_IDS",
    "Layer",
    "MAX_NAME_SYLLABLES",
    "MAX_SAVED_PORTRAITS",
    "MOUTH_OPTIONS",
    "OPTIONS",
    "PATTERN_OPTIONS",
    "PRESET_NAMES",
    "PartOption",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SHARE_ROLE",
    "SYLLABLES",
    "SYLLABLE_COLORS",
    "TUFT_OPTIONS",
    "Tint",
    "VALID_IDS",
    "canonical_id",
    "option",
]
