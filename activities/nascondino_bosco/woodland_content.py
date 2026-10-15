"""Woodland Hide & Seek content: friends, hiding props, seasonal scenes, levels.

Everything the child sees is addressed by a stable id:

* friends are shared library creatures (``creature.woodland.<id>``, with
  ``peek`` and full ``default`` variants); their names are locale keys
  ``animal.<id>`` and their spoken names come from the shared vocabulary bank
  (concept id = ``<id>``) where an approved recording exists;
* hiding props are shared library props (``prop.*``) or this package's own
  props (``assets/runtime/<name>.png``, drawn from ``assets/source``);
* every prop carries the **position word** a child learns from it ("behind
  the bush", "under the leaves", "in the pond") as a locale key ``place.<id>``;
* each season is one layered shared backdrop (``bg.<kit>.*``) composed through
  the scene-composition runtime, plus six grounded hiding anchors. A round
  picks some of the anchors at random, so memorising places never works.

Geometry is authored in the 1024x600 reference canvas. Prop silhouettes are
described by fractions of their art canvas: ``top`` is where a peeking friend
emerges, ``cut`` is the deepest row that is still fully covered (friends are
clipped there, so a cut edge never shows) and ``solid`` is the covered width
at ``cut`` (friends are sized to fit inside it).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from greia_platform.scene import SceneDefinition, SceneFit, SceneNode

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "nascondino_bosco.progress.v2"
FINDS_PER_ROUND: Final = 4


@dataclass(frozen=True, slots=True)
class Friend:
    """One woodland friend who can hide (shared creature art)."""

    friend_id: str

    @property
    def asset_id(self) -> str:
        return f"creature.woodland.{self.friend_id}"

    @property
    def name_key(self) -> str:
        return f"animal.{self.friend_id}"


# Nine friends whose peeking heads are easy to tell apart (ears, spines,
# shell, wings, colours). Ladybird, beetle and firefly are left out on
# purpose: only their alike dark heads would show above a hiding place.
# Nine is the minimum for the top rung (six places + three found friends).
FRIENDS: Final[tuple[Friend, ...]] = tuple(
    Friend(friend_id)
    for friend_id in (
        "hedgehog",
        "squirrel",
        "frog",
        "bear",
        "deer",
        "mouse",
        "duck",
        "snail",
        "butterfly",
    )
)
FRIEND_IDS: Final[tuple[str, ...]] = tuple(friend.friend_id for friend in FRIENDS)
FRIENDS_BY_ID: Final[dict[str, Friend]] = {friend.friend_id: friend for friend in FRIENDS}


class Relation(StrEnum):
    """The position word a hiding place teaches."""

    BEHIND = "behind"
    UNDER = "under"
    IN = "in"


@dataclass(frozen=True, slots=True)
class PropKind:
    """A kind of hiding place and how its art hides a friend."""

    kind_id: str
    relation: Relation
    asset_id: str | None  # shared library art; ``None`` -> private ``art_file``
    art_file: str | None
    canvas: tuple[int, int]  # art canvas size (aspect)
    width: int  # drawn width at depth scale 1.0 (reference px)
    top: float
    cut: float
    solid: float
    rustle_fx: str  # library FX played when the place rustles

    @property
    def place_key(self) -> str:
        return f"place.{self.kind_id}"


def _shared(kind_id, relation, asset_id, width, top, cut, solid, fx, canvas=(256, 256)) -> PropKind:
    return PropKind(kind_id, relation, asset_id, None, canvas, width, top, cut, solid, fx)


def _private(kind_id, relation, art_file, width, top, cut, solid, fx) -> PropKind:
    return PropKind(kind_id, relation, None, art_file, (512, 256), width, top, cut, solid, fx)


PROPS: Final[dict[str, PropKind]] = {
    kind.kind_id: kind
    for kind in (
        _private("bush", Relation.BEHIND, "bush_green.png", 252, 0.27, 0.58, 0.76, "leaf_drift"),
        _private("bush_autumn", Relation.BEHIND, "bush_autumn.png", 252, 0.27, 0.58, 0.76, "leaf_drift"),
        _private("bush_snow", Relation.BEHIND, "bush_snow.png", 252, 0.27, 0.58, 0.76, "snow"),
        _private("leaves", Relation.UNDER, "leaf_pile.png", 252, 0.42, 0.74, 0.72, "leaf_drift"),
        _private("snow", Relation.UNDER, "snow_drift.png", 252, 0.46, 0.74, 0.72, "snow"),
        _shared("rock", Relation.BEHIND, "prop.everyday.stone", 200, 0.43, 0.68, 0.76, "dust_puff"),
        _shared("log", Relation.BEHIND, "prop.vocab.log", 206, 0.52, 0.74, 0.78, "dust_puff"),
        _shared("mushroom", Relation.BEHIND, "prop.nature.mushroom", 184, 0.18, 0.57, 0.84, "sparkle"),
        _shared("pumpkin", Relation.BEHIND, "prop.vocab.pumpkin", 190, 0.38, 0.70, 0.78, "leaf_drift"),
        # Water has no prop art: the friend rises out of the pond surface.
        PropKind("pond", Relation.IN, None, None, (256, 256), 200, 0.0, 0.0, 0.84, "ripple"),
    )
}


@dataclass(frozen=True, slots=True)
class Anchor:
    """A grounded hiding place in a season scene (midbottom on the ground)."""

    kind_id: str
    x: int
    y: int
    depth: float  # 1.0 = front row, smaller = further away

    @property
    def kind(self) -> PropKind:
        return PROPS[self.kind_id]


@dataclass(frozen=True, slots=True)
class Season:
    """One seasonal woodland scene: shared backdrop layers + hiding anchors."""

    season_id: str
    kit: str  # shared bg kit id (``bg.<kit>.<layer>``)
    anchors: tuple[Anchor, ...]

    @property
    def layers(self) -> tuple[str, ...]:
        return tuple(f"bg.{self.kit}.{layer}" for layer in ("sky", "far", "mid", "ground", "foreground"))

    def scene(self) -> SceneDefinition:
        """The backdrop as a renderer-neutral scene (layers only; baked once)."""

        return SceneDefinition(
            scene_id=f"nascondino_bosco.{self.season_id}",
            canvas_size=(REFERENCE_WIDTH, REFERENCE_HEIGHT),
            background=(207, 234, 247),
            nodes=tuple(
                SceneNode(f"layer_{index}", asset_id, (0, 0, REFERENCE_WIDTH, REFERENCE_HEIGHT), z=index * 10)
                for index, asset_id in enumerate(self.layers)
            ),
            fit=SceneFit.COVER,
        )


BACK: Final = 0.8
FRONT: Final = 1.0

# Two staggered rows on the ground (back row baseline ~455, front ~585). The
# bottom-left corner stays free for Lilli and the friends already found; the
# top band stays free for the prompt and progress controls.
SEASONS: Final[tuple[Season, ...]] = (
    Season(
        "meadow",
        "meadow_day",
        (
            Anchor("bush", 318, 452, BACK),
            Anchor("rock", 572, 446, BACK),
            Anchor("mushroom", 810, 452, BACK),
            Anchor("log", 470, 586, FRONT),
            Anchor("bush", 712, 588, FRONT),
            Anchor("rock", 920, 586, FRONT),
        ),
    ),
    Season(
        "pond",
        "woodland_pond",
        (
            Anchor("bush", 300, 456, BACK),
            Anchor("rock", 566, 436, BACK),
            Anchor("log", 828, 458, BACK),
            Anchor("pond", 420, 506, FRONT),
            Anchor("pond", 628, 512, FRONT),
            Anchor("bush", 884, 588, FRONT),
        ),
    ),
    Season(
        "autumn",
        "woodland_autumn",
        (
            Anchor("bush_autumn", 318, 452, BACK),
            Anchor("pumpkin", 572, 448, BACK),
            Anchor("mushroom", 810, 452, BACK),
            Anchor("leaves", 470, 588, FRONT),
            Anchor("log", 706, 586, FRONT),
            Anchor("leaves", 900, 588, FRONT),
        ),
    ),
    Season(
        "snow",
        "woodland_snow",
        (
            Anchor("bush_snow", 318, 452, BACK),
            Anchor("rock", 572, 446, BACK),
            Anchor("log", 810, 452, BACK),
            Anchor("snow", 470, 588, FRONT),
            Anchor("bush_snow", 712, 588, FRONT),
            Anchor("snow", 900, 586, FRONT),
        ),
    ),
)
SEASON_IDS: Final[tuple[str, ...]] = tuple(season.season_id for season in SEASONS)


@dataclass(frozen=True, slots=True)
class Level:
    """One rung of the difficulty ladder (same loop, harder looking).

    ``rise`` is how much of a peeking head shows (fraction of its height);
    ``up``/``down`` are the seconds a friend stays up / ducks between peeks
    (``down == 0`` means friends never duck).
    """

    spots: int
    rise: float
    up: float
    down: float


LEVELS: Final[tuple[Level, ...]] = (
    Level(3, 0.86, 1.0, 0.0),  # three places, big steady peeks (eyes show)
    Level(4, 0.72, 1.0, 0.0),
    Level(5, 0.58, 2.6, 0.9),  # friends start to duck and peek again
    Level(5, 0.46, 1.8, 1.5),
    Level(6, 0.36, 1.4, 2.0),  # six places, just the top of a head for a moment
)
MAX_LEVEL: Final = len(LEVELS) - 1


__all__ = [
    "Anchor",
    "BACK",
    "FINDS_PER_ROUND",
    "FRIENDS",
    "FRIENDS_BY_ID",
    "FRIEND_IDS",
    "FRONT",
    "Friend",
    "LEVELS",
    "Level",
    "MAX_LEVEL",
    "PROPS",
    "PropKind",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "Relation",
    "SEASONS",
    "SEASON_IDS",
    "STORAGE_KEY",
    "Season",
]
