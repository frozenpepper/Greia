"""Authored gardens and the difficulty ladder for La Corsa delle Bacche.

Pure data, no Pygame. Each rung of the ladder is one small hand-authored
garden maze (plus its mirror images, chosen at random for replay variety)
and the friendly garden critters that live in it.

Garden lattice notation (the same convention as Il Labirinto Magico, so
both hedge mazes look like one family): a garden of ``cols x rows`` cells is
written as ``2 * rows + 1`` strings of ``2 * cols + 1`` characters. Cells sit
on odd/odd positions; even rows/columns are hedge lines.

* ``#`` hedge (every even/even corner is a hedge post);
* `` `` (space) an open gap between two cells, or an empty cell;
* ``.`` a cell with a berry;
* ``M`` Momo's start cell;
* ``L`` the ladybird's start cell, ``H`` the hedgehog's start cell.

Berries per rung: 8, 10, 12, 14, 16, 18 -- every berry is visible at once
and every garden is loopy, so a critter can always be walked around.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class CritterKind(StrEnum):
    """Friendly garden critters (shared ``creature.woodland.*`` art)."""

    LADYBIRD = "ladybird"  # never naps; trundles along the paths
    HEDGEHOG = "hedgehog"  # naps (eyes closed = safe to pass) and wakes up


@dataclass(frozen=True, slots=True)
class CritterSpec:
    """How one critter behaves on a rung."""

    kind: CritterKind
    speed: float  # cells per second
    awake_seconds: float = 0.0  # 0 = never naps
    nap_seconds: float = 0.0
    follow: float = 0.0  # chance to turn towards Momo at a junction (gentle chase)


@dataclass(frozen=True, slots=True)
class RungSpec:
    """One rung of the ladder (manifest difficulty 1..6)."""

    level: int
    lattice: tuple[str, ...]
    critters: tuple[CritterSpec, ...] = ()
    momo_speed: float = 2.6  # cells per second


GARDENS_PER_VISIT: Final = 3

_R1: Final = (
    "#######",
    "#M . .#",
    "# # # #",
    "#. .#.#",
    "# ### #",
    "#. . .#",
    "#######",
)

_R2: Final = (
    "#########",
    "#M . . .#",
    "# ### # #",
    "#. H . .#",
    "# # ### #",
    "#. . . .#",
    "#########",
)

_R3: Final = (
    "###########",
    "#M . .#. .#",
    "# ### # # #",
    "#. . L . .#",
    "# # # ### #",
    "#. .#.   .#",
    "###########",
)

_R4: Final = (
    "###########",
    "#M . . . .#",
    "# ### # # #",
    "#. .#H . .#",
    "# # # ### #",
    "#.   L#. .#",
    "# ### # # #",
    "#. .   .  #",
    "###########",
)

_R5: Final = (
    "#############",
    "#M . .#. .  #",
    "# ### # ### #",
    "#. .   L   .#",
    "# # ### # # #",
    "#. .#H .   .#",
    "# # # ### # #",
    "#. .   .#. .#",
    "#############",
)

_R6: Final = (
    "###############",
    "#M . . .#.   .#",
    "# ### # # ### #",
    "#. .#.   L   .#",
    "# # # ### # # #",
    "#.   . H  #. .#",
    "# ### # # ### #",
    "#. . .#.     .#",
    "###############",
)

_HEDGEHOG_SLEEPY: Final = CritterSpec(CritterKind.HEDGEHOG, speed=0.8, awake_seconds=3.0, nap_seconds=4.0)

RUNGS: Final[tuple[RungSpec, ...]] = (
    # 1: tiny open garden, no critters -- just steer and collect.
    RungSpec(1, _R1),
    # 2: one very sleepy, slow hedgehog (asleep more than awake).
    RungSpec(2, _R2, (_HEDGEHOG_SLEEPY,)),
    # 3: one slow ladybird that never naps: wait for her to pass.
    RungSpec(3, _R3, (CritterSpec(CritterKind.LADYBIRD, speed=0.9),)),
    # 4: ladybird + napping hedgehog in a bigger garden.
    RungSpec(
        4,
        _R4,
        (
            CritterSpec(CritterKind.LADYBIRD, speed=1.0),
            CritterSpec(CritterKind.HEDGEHOG, speed=0.9, awake_seconds=4.0, nap_seconds=3.5),
        ),
    ),
    # 5: the ladybird now sometimes turns towards Momo (gentle chase).
    RungSpec(
        5,
        _R5,
        (
            CritterSpec(CritterKind.LADYBIRD, speed=1.15, follow=0.3),
            CritterSpec(CritterKind.HEDGEHOG, speed=1.0, awake_seconds=4.5, nap_seconds=3.0),
        ),
        momo_speed=2.8,
    ),
    # 6: the widest garden, quicker critters that both follow a little.
    RungSpec(
        6,
        _R6,
        (
            CritterSpec(CritterKind.LADYBIRD, speed=1.3, follow=0.45),
            CritterSpec(CritterKind.HEDGEHOG, speed=1.1, awake_seconds=5.0, nap_seconds=2.5, follow=0.2),
        ),
        momo_speed=3.0,
    ),
)

MIN_LEVEL: Final = 1
MAX_LEVEL: Final = len(RUNGS)
CRITTER_CHARS: Final[dict[str, CritterKind]] = {"L": CritterKind.LADYBIRD, "H": CritterKind.HEDGEHOG}


def clamp_level(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return MIN_LEVEL
    return max(MIN_LEVEL, min(MAX_LEVEL, value))


def rung_spec(level: int) -> RungSpec:
    return RUNGS[clamp_level(level) - 1]


__all__ = [
    "CRITTER_CHARS",
    "GARDENS_PER_VISIT",
    "MAX_LEVEL",
    "MIN_LEVEL",
    "RUNGS",
    "CritterKind",
    "CritterSpec",
    "RungSpec",
    "clamp_level",
    "rung_spec",
]
