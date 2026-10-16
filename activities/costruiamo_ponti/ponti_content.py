"""Authored crossings for Bridge Builders (pure data, no Pygame).

A *crossing* is one river a cast friend has to cross to reach the picnic on
the far bank. Everything is measured in whole **units** (one plank board):

* ``gap`` -- the water between the two banks;
* ``islands`` -- fixed grassy islands in the river (they hold planks too);
* ``spots`` -- rocks in the water where the child may stand a pillar (the
  pillar is one unit wide and splits the gap into two shorter spans);
* ``pieces`` -- what lies in the tray: planks of 1-4 units (thin wood, or a
  thick stone slab that also holds a heavy load) and pillars;
* ``heavy`` -- the friend carries a big pumpkin: a thin wooden plank bends.

The physics the child discovers is deliberately simple and honest: a plank
shorter than its span cannot reach the other side, a plank as long as the span
is *just right*, a longer plank also reaches (it sticks out), and a heavy load
needs a stone plank. Four sets of four crossings form a fixed authored ladder
(long enough -> two rivers -> pillars -> heavy friends); nothing adapts
behind the child's back.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class PieceKind(StrEnum):
    PLANK = "plank"
    PILLAR = "pillar"


@dataclass(frozen=True, slots=True)
class Piece:
    """One tray piece. Planks of the same length and material are interchangeable."""

    kind: PieceKind
    length: int = 1  # units (a pillar is always one unit wide)
    strong: bool = False  # stone slab (holds a heavy load) vs thin wood

    def __post_init__(self) -> None:
        if self.kind is PieceKind.PLANK and not 1 <= self.length <= MAX_PLANK:
            raise ValueError("plank length out of range")
        if self.kind is PieceKind.PILLAR and (self.length != 1 or self.strong):
            raise ValueError("a pillar is one plain unit")

    @property
    def signature(self) -> tuple[str, int, bool]:
        return (self.kind.value, self.length, self.strong)


def wood(length: int) -> Piece:
    return Piece(PieceKind.PLANK, length, False)


def stone(length: int) -> Piece:
    return Piece(PieceKind.PLANK, length, True)


PILLAR: Final = Piece(PieceKind.PILLAR)
MAX_PLANK: Final = 4
MAX_GAP: Final = 7
MAX_TRAY: Final = 4
CROSSINGS_PER_SET: Final = 4


@dataclass(frozen=True, slots=True)
class Crossing:
    """One river to cross (all positions in units from the left bank's edge)."""

    crossing_id: str
    gap: int
    pieces: tuple[Piece, ...]
    traveler: str
    islands: tuple[tuple[int, int], ...] = ()  # (start, width)
    spots: tuple[int, ...] = ()  # pillar rock start units (one unit wide)
    heavy: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.gap <= MAX_GAP:
            raise ValueError("gap out of range")
        if not 1 <= len(self.pieces) <= MAX_TRAY:
            raise ValueError("tray must hold 1..4 pieces")
        for start, width in self.islands:
            if start <= 0 or width <= 0 or start + width >= self.gap:
                raise ValueError("island must stand inside the river")
        for start in self.spots:
            if start <= 0 or start + 1 >= self.gap:
                raise ValueError("pillar rock must stand inside the river")

    @property
    def pillars(self) -> int:
        return sum(1 for piece in self.pieces if piece.kind is PieceKind.PILLAR)


@dataclass(frozen=True, slots=True)
class CrossingSet:
    set_id: str
    crossings: tuple[Crossing, ...]

    def __post_init__(self) -> None:
        if len(self.crossings) != CROSSINGS_PER_SET:
            raise ValueError("a set has four crossings")


CROSSING_SETS: Final[tuple[CrossingSet, ...]] = (
    # 1. Long enough? One gap, one plank: too short, just right, longer.
    CrossingSet(
        "long_enough",
        (
            Crossing("le1", 2, (wood(1), wood(2), wood(3)), "flash"),
            Crossing("le2", 3, (wood(4), wood(2), wood(3)), "lilli"),
            Crossing("le3", 4, (wood(3), wood(4), wood(2)), "tito"),
            Crossing("le4", 3, (wood(2), wood(1), wood(3)), "leo"),
        ),
    ),
    # 2. Two rivers around an island: each plank must go where it fits.
    CrossingSet(
        "two_rivers",
        (
            Crossing("tr1", 6, (wood(3), wood(1), wood(2)), "flash", islands=((2, 1),)),
            Crossing("tr2", 6, (wood(2), wood(3), wood(1)), "tito", islands=((3, 1),)),
            Crossing("tr3", 5, (wood(2), wood(1), wood(1)), "lilli", islands=((1, 2),)),
            Crossing("tr4", 7, (wood(2), wood(4), wood(1)), "leo", islands=((2, 1),)),
        ),
    ),
    # 3. Too wide for any plank: stand a pillar on a rock first.
    CrossingSet(
        "pillars",
        (
            Crossing("pi1", 5, (PILLAR, wood(2), wood(2)), "lilli", spots=(2,)),
            Crossing("pi2", 6, (PILLAR, wood(3), wood(2)), "flash", spots=(2,)),
            Crossing("pi3", 6, (PILLAR, wood(2), wood(3)), "tito", spots=(1, 3)),
            Crossing("pi4", 7, (PILLAR, wood(3), wood(3)), "leo", spots=(1, 3)),
        ),
    ),
    # 4. Heavy friends carry a pumpkin: thin wood bends, stone holds.
    CrossingSet(
        "heavy",
        (
            Crossing("hv1", 2, (wood(2), stone(2), stone(1)), "momo", heavy=True),
            Crossing("hv2", 3, (stone(2), wood(3), wood(1)), "flash"),
            Crossing("hv3", 3, (wood(3), stone(3), wood(4)), "dani", heavy=True),
            Crossing("hv4", 6, (stone(3), wood(3), stone(2)), "momo", islands=((2, 1),), heavy=True),
        ),
    ),
)

ALL_CROSSINGS: Final = tuple(crossing for crossing_set in CROSSING_SETS for crossing in crossing_set.crossings)
COMPLETION_FRIEND: Final = "flash"

__all__ = [
    "ALL_CROSSINGS",
    "COMPLETION_FRIEND",
    "CROSSINGS_PER_SET",
    "CROSSING_SETS",
    "Crossing",
    "CrossingSet",
    "MAX_GAP",
    "MAX_PLANK",
    "MAX_TRAY",
    "PILLAR",
    "Piece",
    "PieceKind",
    "stone",
    "wood",
]
