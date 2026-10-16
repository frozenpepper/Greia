"""Domain vocabulary, stages and design tokens for Quattro Amici in Fila.

One experience: Flash (the child) and Leo take turns dropping discs into a
standing board until one of them makes a row. A *match* is best of three
games; the board grows and Leo plays a little smarter as the child wins
matches (stages of the same loop, never separate modes).

Reference display target: 1024x600 logical pixels (Greia reference canvas).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

GAMES_PER_MATCH: Final[int] = 3
WINS_FOR_MATCH: Final[int] = 2


class Player(IntEnum):
    """Grid cell contents and player identification."""

    EMPTY = 0
    FLASH = 1  # first friend: carrot discs (the child in "vs Leo")
    LEO = 2  # second friend: acorn discs (Leo, or a second child)

    @property
    def opponent(self) -> "Player":
        if self == Player.FLASH:
            return Player.LEO
        if self == Player.LEO:
            return Player.FLASH
        return Player.EMPTY

    @property
    def cast_id(self) -> str:
        """Canonical cast id (``character.<id>``) of this player's friend."""

        return "leo" if self == Player.LEO else "flash"


class GameMode(StrEnum):
    """Who plays Leo's discs: Leo himself, or a second child on the same device."""

    VS_CPU = "vs_cpu"
    TWO_PLAYERS = "two_players"


class GameStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    WON = "won"
    DRAW = "draw"


class LeoStyle(StrEnum):
    """How Leo chooses a column (see ``quattro_model.leo_brain_for``)."""

    EASY = "easy"  # often misses a win or a block: a playful first opponent
    MEDIUM = "medium"  # takes wins and blocks obvious ones (nearly always)
    SMART = "smart"  # also avoids gifts and builds his own lines


@dataclass(frozen=True, slots=True)
class Stage:
    """One step of the automatic difficulty ladder."""

    number: int
    cols: int
    rows: int
    target: int
    leo: LeoStyle


STAGES: Final[dict[int, Stage]] = {
    1: Stage(1, cols=5, rows=4, target=3, leo=LeoStyle.EASY),
    2: Stage(2, cols=6, rows=5, target=3, leo=LeoStyle.MEDIUM),
    3: Stage(3, cols=7, rows=6, target=4, leo=LeoStyle.MEDIUM),
    4: Stage(4, cols=7, rows=6, target=4, leo=LeoStyle.SMART),
}
FIRST_STAGE: Final[int] = min(STAGES)
LAST_STAGE: Final[int] = max(STAGES)


def stage_for(number: int) -> Stage:
    """Return the stage, clamped into the ladder."""

    return STAGES[max(FIRST_STAGE, min(LAST_STAGE, int(number)))]


# Design tokens (runtime/theme-defaults.toml + cast artwork constants).
INK: Final = (75, 55, 47)  # cast contour #4B372F
COCOA: Final = (61, 44, 31)
CREAM: Final = (255, 251, 235)
SAND: Final = (238, 221, 186)
SAND_LIGHT: Final = (245, 235, 214)  # sand -> 40 % white
SAND_SHADE: Final = (202, 184, 155)  # sand -> 22 % ink
SAND_WELL: Final = (132, 113, 96)  # sand -> 65 % ink (inside a hole)
WOOD: Final = (201, 129, 54)  # orange -> 25 % ink
WOOD_SHADE: Final = (165, 104, 52)  # orange -> 45 % ink
SUNSHINE: Final = (255, 194, 52)
SUNSHINE_LIGHT: Final = (255, 218, 133)
CORAL: Final = (244, 111, 97)
TURQUOISE: Final = (68, 184, 174)
SHADOW: Final = (106, 81, 71)  # contact shadow #6A5147 (used with alpha)
NAVY: Final = (37, 59, 89)

PLAYER_ACCENT: Final[dict[Player, tuple[int, int, int]]] = {
    Player.FLASH: CORAL,
    Player.LEO: TURQUOISE,
}
