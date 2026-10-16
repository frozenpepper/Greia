"""Bedtime content for Cloud Bedtime: colours, quilts, the night ladder (pure data).

Every little cloud dreams of one quilt: a colour and, from the third rung on,
a small number of stars (1-5) sewn on it. The tray offers the dreamed quilts
plus a few that nobody dreamed of. A night is always three clouds; the ladder
only changes what has to be compared:

0. colour only, four basic colours, one extra quilt;
1. colour only, six colours, two extra quilts;
2. stars only (1-3): every quilt has the same colour, so only the number counts;
3. colour and stars (1-3);
4. colour and stars (1-5); two clouds may dream of the same colour.

Extra quilts are near misses (right colour / one star more or fewer, else
right number / wrong colour), never a copy of a dreamed quilt, so exactly the
dreamed quilt fits each cloud and, once stars appear, the number matters.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Final, Sequence

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CLOUDS_PER_NIGHT: Final = 3
MAX_STARS: Final = 5
STORAGE_KEY: Final = "nanna_delle_nuvolette.progress.v1"
# Pre-rework favourite-blanket preferences. Read-only history: never rewritten
# or deleted, so a child's earlier save survives the rework untouched.
LEGACY_STORAGE_KEY: Final = "nanna_delle_nuvolette.preferences.v1"

Rgb = tuple[int, int, int]


def _mix(color: Rgb, other: Rgb, amount: float) -> Rgb:
    return tuple(int(round(a + (b - a) * amount)) for a, b in zip(color, other))  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QuiltColour:
    """One quilt colour (a theme accent token) and the pastel of its cloud."""

    colour_id: str
    quilt: Rgb

    @property
    def cloud(self) -> Rgb:
        # The dreaming cloud wears a soft pastel of its quilt colour.
        return _mix(self.quilt, (255, 255, 255), 0.42)


# Theme accent tokens (runtime/theme-defaults.toml); chosen to stay apart
# for young eyes: pink, yellow, green, blue, purple, orange.
COLOURS: Final[dict[str, QuiltColour]] = {
    colour.colour_id: colour
    for colour in (
        QuiltColour("pink", (216, 86, 131)),     # raspberry
        QuiltColour("yellow", (255, 194, 52)),   # sunshine
        QuiltColour("green", (89, 184, 106)),    # leaf
        QuiltColour("blue", (74, 145, 216)),     # ocean
        QuiltColour("purple", (148, 100, 201)),  # grape
        QuiltColour("orange", (243, 154, 56)),   # orange
    )
}
BASIC_COLOURS: Final = ("pink", "yellow", "green", "blue")
ALL_COLOURS: Final = tuple(COLOURS)


@dataclass(frozen=True, slots=True)
class Quilt:
    """A quilt in the tray, or the quilt a cloud dreams of (``stars`` 0 = plain)."""

    colour_id: str
    stars: int = 0

    def __post_init__(self) -> None:
        if self.colour_id not in COLOURS:
            raise ValueError(f"unknown quilt colour: {self.colour_id!r}")
        if not 0 <= self.stars <= MAX_STARS:
            raise ValueError("a quilt carries 0..5 stars")

    @property
    def colour(self) -> QuiltColour:
        return COLOURS[self.colour_id]


@dataclass(frozen=True, slots=True)
class NightLevel:
    """One ladder rung: what the child has to compare to tuck each cloud in."""

    colours: tuple[str, ...]
    colour_matters: bool
    max_stars: int
    extras: int
    shared_colours: bool = False

    @property
    def uses_stars(self) -> bool:
        return self.max_stars > 0


LEVELS: Final[tuple[NightLevel, ...]] = (
    NightLevel(BASIC_COLOURS, colour_matters=True, max_stars=0, extras=1),
    NightLevel(ALL_COLOURS, colour_matters=True, max_stars=0, extras=2),
    NightLevel(ALL_COLOURS, colour_matters=False, max_stars=3, extras=1),
    NightLevel(ALL_COLOURS, colour_matters=True, max_stars=3, extras=2),
    NightLevel(ALL_COLOURS, colour_matters=True, max_stars=5, extras=2, shared_colours=True),
)
MAX_LEVEL: Final = len(LEVELS) - 1
MAX_TRAY: Final = CLOUDS_PER_NIGHT + max(level.extras for level in LEVELS)


@dataclass(frozen=True, slots=True)
class NightPlan:
    """The three dreams (left to right) and the tray order of the quilts."""

    dreams: tuple[Quilt, ...]
    tray: tuple[Quilt, ...]


def plan_night(level_index: int, rng: random.Random) -> NightPlan:
    """Draw one night for ``level_index``: distinct dreams plus near-miss extras."""

    level = LEVELS[max(0, min(MAX_LEVEL, level_index))]
    dreams = _dreams(level, rng)
    extras = _extras(level, dreams, rng)
    tray = list(dreams) + list(extras)
    rng.shuffle(tray)
    return NightPlan(tuple(dreams), tuple(tray))


def _dreams(level: NightLevel, rng: random.Random) -> list[Quilt]:
    if not level.colour_matters:
        colour = rng.choice(level.colours)
        counts = rng.sample(range(1, level.max_stars + 1), CLOUDS_PER_NIGHT)
        return [Quilt(colour, count) for count in counts]
    colours = rng.sample(level.colours, CLOUDS_PER_NIGHT)
    if level.shared_colours and rng.random() < 0.5:
        # "The same as": two clouds dream of one colour; only the stars differ.
        colours[2] = colours[rng.randrange(2)]
    dreams: list[Quilt] = []
    for colour in colours:
        if not level.uses_stars:
            dreams.append(Quilt(colour))
            continue
        taken = {dream.stars for dream in dreams if dream.colour_id == colour}
        free = [count for count in range(1, level.max_stars + 1) if count not in taken]
        dreams.append(Quilt(colour, rng.choice(free)))
    order = list(range(CLOUDS_PER_NIGHT))
    rng.shuffle(order)
    return [dreams[index] for index in order]


def _extras(level: NightLevel, dreams: Sequence[Quilt], rng: random.Random) -> list[Quilt]:
    taken = set(dreams)
    unused = [colour for colour in level.colours if colour not in {dream.colour_id for dream in dreams}]
    candidates: list[Quilt] = []
    if not level.uses_stars:
        candidates = [Quilt(colour) for colour in unused]
    elif not level.colour_matters:
        colour = dreams[0].colour_id
        candidates = [Quilt(colour, count) for count in range(1, MAX_STARS + 1)]
        # Prefer the nearest numbers that nobody dreamed of.
        candidates.sort(key=lambda quilt: abs(quilt.stars - level.max_stars) + rng.random() * 0.1)
    else:
        # Same colour, one star more or fewer: the number has to be compared.
        # One such near miss per dreamed colour first, then a wrong colour with
        # a dreamed number as the fallback.
        same_colour: list[Quilt] = []
        for dream in rng.sample(list(dreams), len(dreams)):
            steps = [step for step in (-1, 1) if 1 <= dream.stars + step <= level.max_stars]
            rng.shuffle(steps)
            same_colour.extend(Quilt(dream.colour_id, dream.stars + step) for step in steps)
        other_colour = [Quilt(colour, dream.stars) for dream in dreams for colour in unused]
        rng.shuffle(other_colour)
        first: dict[str, Quilt] = {}
        for quilt in same_colour:
            first.setdefault(quilt.colour_id, quilt)
        candidates = list(first.values()) + same_colour + other_colour
    extras: list[Quilt] = []
    for quilt in candidates:
        if quilt in taken:
            continue
        taken.add(quilt)
        extras.append(quilt)
        if len(extras) == level.extras:
            break
    return extras


def dice_points(count: int) -> tuple[tuple[float, float], ...]:
    """Star spots (0..1 box) in a dice pattern: a dream shows a number, not a row."""

    return {
        1: ((0.5, 0.5),),
        2: ((0.22, 0.25), (0.78, 0.75)),
        3: ((0.18, 0.2), (0.5, 0.5), (0.82, 0.8)),
        4: ((0.22, 0.22), (0.78, 0.22), (0.22, 0.78), (0.78, 0.78)),
        5: ((0.2, 0.2), (0.8, 0.2), (0.5, 0.5), (0.2, 0.8), (0.8, 0.8)),
    }.get(count, ())


__all__ = [
    "ALL_COLOURS",
    "BASIC_COLOURS",
    "CLOUDS_PER_NIGHT",
    "COLOURS",
    "LEGACY_STORAGE_KEY",
    "LEVELS",
    "MAX_LEVEL",
    "MAX_STARS",
    "MAX_TRAY",
    "NightLevel",
    "NightPlan",
    "Quilt",
    "QuiltColour",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "dice_points",
    "plan_night",
]
