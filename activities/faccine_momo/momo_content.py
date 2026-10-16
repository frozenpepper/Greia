"""Static content for Momo's Happy Faces: feelings, picture stories, helps, ladder.

Everything here is data. One visit is six tasks in three stages of the same
loop (recognise a feeling -> explain it from a picture story -> help Momo
feel better); ``LEVELS`` decides the stage mix and how many choices are shown.

Picture stories are composed from the shared art library (``bg.*`` layers,
``prop.*``, ``creature.*``, ``fx.*``) plus two Activity-private props
(``private:gift``, ``private:lightning``; shared-library candidates). Every
story names its feeling *and* the feelings that would also be reasonable
(``also_fits``): those are never offered as wrong choices, so every task has
exactly one sensible answer on screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

TASKS_PER_VISIT: Final[int] = 6
WARMUP_READY_FACES: Final[int] = 3
STORAGE_KEY: Final[str] = "faccine_momo.progress.v1"
GUIDE_CHARACTER: Final[str] = "flash"
SUBJECT_CHARACTER: Final[str] = "momo"
# Friends who show feelings on recognise tiles (the guide, Flash, is not one
# of them so a tile never looks like the helper).
FRIEND_CHARACTERS: Final[tuple[str, ...]] = ("lilli", "leo", "dani", "tito")


class Emotion(StrEnum):
    """The six feelings; values double as cast variant and voice cue ids."""

    HAPPY = "happy"
    SAD = "sad"
    SURPRISED = "surprised"
    SILLY = "silly"
    ANGRY = "angry"
    SLEEPY = "sleepy"


CORE_EMOTIONS: Final[tuple[Emotion, ...]] = (Emotion.HAPPY, Emotion.SAD, Emotion.ANGRY, Emotion.SLEEPY)
ALL_EMOTIONS: Final[tuple[Emotion, ...]] = tuple(Emotion)
# Warm-up mirror order: left column, then right column (as in the old mirror).
MIRROR_ORDER: Final[tuple[Emotion, ...]] = (
    Emotion.HAPPY,
    Emotion.SURPRISED,
    Emotion.SILLY,
    Emotion.SAD,
    Emotion.ANGRY,
    Emotion.SLEEPY,
)


class Stage(StrEnum):
    RECOGNISE = "recognise"
    EXPLAIN = "explain"
    HELP = "help"


@dataclass(frozen=True, slots=True)
class LevelPlan:
    """One rung of the ladder: the visit's stage mix and choice counts."""

    stages: tuple[Stage, ...]
    recognise_choices: int
    explain_choices: int
    help_choices: int
    pool: tuple[Emotion, ...]

    def choices_for(self, stage: Stage) -> int:
        if stage is Stage.RECOGNISE:
            return self.recognise_choices
        if stage is Stage.EXPLAIN:
            return self.explain_choices
        return self.help_choices


_R, _E, _H = Stage.RECOGNISE, Stage.EXPLAIN, Stage.HELP
LEVELS: Final[tuple[LevelPlan, ...]] = (
    LevelPlan((_R, _R, _E, _E, _H, _H), 2, 2, 2, CORE_EMOTIONS),
    LevelPlan((_R, _E, _E, _E, _H, _H), 3, 3, 2, ALL_EMOTIONS),
    LevelPlan((_R, _E, _E, _H, _H, _H), 3, 3, 3, ALL_EMOTIONS),
)
MAX_LEVEL: Final[int] = len(LEVELS) - 1


class Backdrop(StrEnum):
    PLAYROOM = "playroom"
    BEDROOM = "bedroom"
    MEADOW = "meadow"
    NIGHT = "night"
    STORM = "storm"


BACKDROP_LAYERS: Final[dict[Backdrop, tuple[str, ...]]] = {
    Backdrop.PLAYROOM: ("bg.indoor_room.wall_playroom", "bg.indoor_room.floor_wood"),
    Backdrop.BEDROOM: ("bg.indoor_room.wall_bedroom", "bg.indoor_room.floor_carpet"),
    Backdrop.MEADOW: ("bg.meadow_day.sky", "bg.meadow_day.far", "bg.meadow_day.mid", "bg.meadow_day.ground"),
    Backdrop.NIGHT: (
        "bg.night_sky.sky",
        "bg.night_sky.stars",
        "bg.night_sky.far",
        "bg.night_sky.mid",
        "bg.night_sky.ground",
    ),
    Backdrop.STORM: ("bg.night_sky.sky", "bg.night_sky.far", "bg.night_sky.ground"),
}


@dataclass(frozen=True, slots=True)
class Piece:
    """One picture in a story card (card space: 440 x 300, ground at y ~272).

    ``x, y`` is the midbottom of the piece (``center=True``: its centre).
    ``asset`` is a shared semantic id or ``private:<name>`` for this package's
    runtime art; ``frame`` picks an FX frame variant.
    """

    asset: str
    x: int
    y: int
    height: int
    angle: float = 0.0
    flip: bool = False
    variant: str = "default"
    center: bool = False
    dim: float = 0.0


@dataclass(frozen=True, slots=True)
class Story:
    """A little picture situation that explains (or needs help with) a feeling."""

    story_id: str
    backdrop: Backdrop
    emotion: Emotion
    pieces: tuple[Piece, ...]
    also_fits: frozenset[Emotion] = field(default_factory=frozenset)
    sound: str | None = None
    explain: bool = True


@dataclass(frozen=True, slots=True)
class HelpItem:
    """A kind thing to offer Momo. ``stack`` builds a little block tower
    from shared block props (bottom first) instead of one ``asset``."""

    item_id: str
    asset: str
    variant: str = "default"
    stack: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class HelpPlan:
    """Momo feels ``story.emotion``; ``helper`` is the kind thing that fits."""

    story_id: str
    helper: str
    distractors: tuple[str, ...]
    thanks: str = "praise"


CARD_W: Final[int] = 440
CARD_H: Final[int] = 300
GROUND: Final[int] = 274

STORIES: Final[tuple[Story, ...]] = (
    Story(
        "ice_cream_drop", Backdrop.MEADOW, Emotion.SAD,
        (
            Piece("fx.dust_puff", 222, GROUND - 16, 92, center=True),
            Piece("prop.vocab.ice_cream", 262, GROUND - 46, 132, angle=118, center=True),
            Piece("prop.vocab.hand", 104, CARD_H + 34, 128, angle=-12),
        ),
        also_fits=frozenset({Emotion.ANGRY, Emotion.SURPRISED}),
        sound="splat",
    ),
    Story(
        "balloon_away", Backdrop.MEADOW, Emotion.SAD,
        (
            Piece("prop.nature.cloud", 92, 96, 70),
            Piece("prop.vocab.balloon", 330, 140, 104, angle=-14),
            Piece("prop.vocab.hand", 150, CARD_H + 34, 128, angle=10),
        ),
        also_fits=frozenset({Emotion.ANGRY, Emotion.SURPRISED}),
        sound="whoosh",
    ),
    Story(
        "birthday", Backdrop.PLAYROOM, Emotion.HAPPY,
        (
            Piece("prop.vocab.balloon", 74, 214, 128, angle=-8),
            Piece("prop.vocab.balloon", 374, 204, 118, angle=8),
            Piece("prop.vocab.cake", 222, GROUND, 150),
            Piece("fx.confetti", 222, 74, 140, center=True),
        ),
        also_fits=frozenset({Emotion.SURPRISED, Emotion.SILLY}),
        sound="giggle",
    ),
    Story(
        "present", Backdrop.PLAYROOM, Emotion.HAPPY,
        (
            Piece("private:gift", 220, GROUND, 170),
            Piece("fx.sparkle", 92, 120, 80, center=True),
            Piece("fx.sparkle", 350, 96, 70, center=True, variant="frame_2"),
        ),
        also_fits=frozenset({Emotion.SURPRISED, Emotion.SILLY}),
        sound="chime",
    ),
    Story(
        "frog_box", Backdrop.PLAYROOM, Emotion.SURPRISED,
        (
            Piece("fx.star_burst", 222, 100, 150, center=True),
            Piece("creature.woodland.frog", 222, 168, 120),
            Piece("prop.vocab.box", 222, GROUND, 140),
        ),
        also_fits=frozenset({Emotion.HAPPY, Emotion.SILLY}),
        sound="boing",
    ),
    Story(
        "thunder", Backdrop.STORM, Emotion.SURPRISED,
        (
            Piece("private:lightning", 220, 252, 168),
            Piece("prop.nature.cloud", 128, 128, 120, dim=0.45),
            Piece("prop.nature.cloud", 310, 112, 130, dim=0.45),
            Piece("fx.rain", 120, 200, 110, center=True),
            Piece("fx.rain", 330, 196, 110, center=True, variant="frame_2"),
        ),
        also_fits=frozenset({Emotion.SAD, Emotion.ANGRY, Emotion.SLEEPY}),
        sound="rumble",
    ),
    Story(
        "bedtime", Backdrop.BEDROOM, Emotion.SLEEPY,
        (
            Piece("prop.vocab.moon", 352, 108, 84),
            Piece("prop.vocab.bed", 196, GROUND, 150),
            Piece("prop.vocab.clock", 372, GROUND, 88),
        ),
        also_fits=frozenset({Emotion.SAD}),
        sound=None,
    ),
    Story(
        "late_night", Backdrop.NIGHT, Emotion.SLEEPY,
        (
            Piece("prop.vocab.candle", 116, GROUND, 116),
            Piece("prop.everyday.book", 236, GROUND, 96),
            Piece("prop.vocab.bear", 340, GROUND, 110),
        ),
        also_fits=frozenset({Emotion.SAD, Emotion.SURPRISED}),
        sound=None,
    ),
    Story(
        "tower_fell", Backdrop.PLAYROOM, Emotion.ANGRY,
        (
            Piece("fx.dust_puff", 166, GROUND - 22, 110, center=True),
            Piece("prop.blocks.square", 92, GROUND, 62, variant="ocean", angle=18),
            Piece("prop.blocks.triangle", 178, GROUND, 52, variant="sunshine", angle=-70),
            Piece("prop.blocks.square", 248, GROUND + 2, 56, variant="coral", angle=-12),
            Piece("prop.blocks.arch", 150, GROUND - 74, 42, variant="leaf", angle=35),
            Piece("creature.pet.puppy", 358, GROUND, 122, variant="playful", flip=True),
        ),
        also_fits=frozenset({Emotion.SAD, Emotion.SURPRISED}),
        sound="crash",
    ),
    Story(
        "kite_stuck", Backdrop.MEADOW, Emotion.SAD,
        (
            Piece("prop.vocab.kite", 246, 124, 96, angle=-28),
            Piece("prop.vocab.tree", 190, GROUND, 236),
            Piece("prop.vocab.hand", 360, CARD_H + 34, 128, angle=14),
        ),
        also_fits=frozenset({Emotion.ANGRY, Emotion.SURPRISED}),
        sound="wobble",
    ),
    Story(
        "monkey_hat", Backdrop.PLAYROOM, Emotion.SILLY,
        (
            Piece("prop.vocab.monkey", 220, GROUND, 170),
            Piece("prop.vocab.hat", 232, 146, 70, angle=14),
            Piece("fx.sparkle", 96, 120, 80, center=True),
            Piece("fx.sparkle", 350, 110, 70, center=True, variant="frame_2"),
        ),
        also_fits=frozenset({Emotion.HAPPY, Emotion.SURPRISED}),
        sound="giggle",
    ),
    Story(
        "puppy_crown", Backdrop.PLAYROOM, Emotion.SILLY,
        (
            Piece("creature.pet.puppy", 220, GROUND, 160, variant="happy"),
            Piece("prop.vocab.crown", 214, 156, 62, angle=-16),
            Piece("fx.note_burst", 350, 110, 96, center=True),
            Piece("prop.everyday.duck", 88, GROUND, 70),
        ),
        also_fits=frozenset({Emotion.HAPPY, Emotion.SURPRISED}),
        sound="giggle",
    ),
    Story(
        "rainy_day", Backdrop.MEADOW, Emotion.SAD,
        (
            Piece("prop.nature.cloud", 150, 108, 120, dim=0.25),
            Piece("prop.nature.cloud", 300, 92, 110, dim=0.25),
            Piece("fx.rain", 150, 200, 120, center=True),
            Piece("fx.rain", 300, 190, 120, center=True, variant="frame_2"),
        ),
        also_fits=frozenset({Emotion.ANGRY, Emotion.SLEEPY, Emotion.SURPRISED}),
        sound=None,
        explain=False,
    ),
)
STORIES_BY_ID: Final[dict[str, Story]] = {story.story_id: story for story in STORIES}

HELP_ITEMS: Final[dict[str, HelpItem]] = {
    item.item_id: item
    for item in (
        HelpItem("hug", "icon.hud.heart"),
        HelpItem("share", "prop.vocab.ice_cream"),
        HelpItem("teddy", "prop.vocab.bear"),
        HelpItem("bed", "prop.vocab.bed"),
        HelpItem(
            "blocks",
            "prop.blocks.square",
            "ocean",
            stack=(
                ("prop.blocks.square", "ocean"),
                ("prop.blocks.square", "coral"),
                ("prop.blocks.triangle", "sunshine"),
            ),
        ),
        HelpItem("umbrella", "prop.vocab.umbrella"),
        HelpItem("ladder", "prop.vocab.ladder"),
        HelpItem("drum", "prop.instrument.drum"),
        HelpItem("sock", "prop.everyday.sock"),
        HelpItem("ball", "prop.everyday.ball"),
        HelpItem("pan", "prop.vocab.pan"),
        HelpItem("cake", "prop.vocab.cake"),
        HelpItem("trumpet", "prop.instrument.trumpet"),
    )
}

HELP_PLANS: Final[tuple[HelpPlan, ...]] = (
    HelpPlan("balloon_away", "hug", ("drum", "pan"), thanks="comfort"),
    HelpPlan("ice_cream_drop", "share", ("umbrella", "sock")),
    HelpPlan("thunder", "teddy", ("drum", "ball"), thanks="comfort"),
    HelpPlan("late_night", "bed", ("trumpet", "ball")),
    HelpPlan("tower_fell", "blocks", ("umbrella", "bed")),
    HelpPlan("kite_stuck", "ladder", ("pan", "cake")),
    HelpPlan("rainy_day", "umbrella", ("cake", "sock")),
)


def stories_for(pool: tuple[Emotion, ...]) -> tuple[Story, ...]:
    """Explainable stories whose feeling is in the level's pool."""

    return tuple(story for story in STORIES if story.explain and story.emotion in pool)


__all__ = [
    "ALL_EMOTIONS",
    "BACKDROP_LAYERS",
    "Backdrop",
    "CARD_H",
    "CARD_W",
    "CORE_EMOTIONS",
    "Emotion",
    "FRIEND_CHARACTERS",
    "GROUND",
    "GUIDE_CHARACTER",
    "HELP_ITEMS",
    "HELP_PLANS",
    "HelpItem",
    "HelpPlan",
    "LEVELS",
    "LevelPlan",
    "MAX_LEVEL",
    "MIRROR_ORDER",
    "Piece",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "STORIES",
    "STORIES_BY_ID",
    "SUBJECT_CHARACTER",
    "Stage",
    "Story",
    "TASKS_PER_VISIT",
    "WARMUP_READY_FACES",
    "stories_for",
]
