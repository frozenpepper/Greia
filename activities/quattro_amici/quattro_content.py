"""Design constants, color palettes, and level definitions for Quattro Amici in Fila.

Reference display target: 1024x600 (Greia standard child-viewport).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

# Top-left system chrome clearance boundary (ADR 0019)
CHROME_SAFE_MARGIN_X: Final[int] = 120
CHROME_SAFE_MARGIN_Y: Final[int] = 68


class Player(IntEnum):
    """Grid cell contents and player identification."""
    EMPTY = 0
    FLASH = 1  # Player 1 (Rabbit - Orange Carrot Disc)
    LEO = 2    # Player 2 / CPU (Owl - Purple Acorn Disc)

    @property
    def opponent(self) -> Player:
        if self == Player.FLASH:
            return Player.LEO
        if self == Player.LEO:
            return Player.FLASH
        return Player.EMPTY


class GameMode(StrEnum):
    """Supported child gameplay modes."""
    VS_CPU = "vs_cpu"           # Solo play against friendly Leo
    TWO_PLAYERS = "two_players" # Same-computer turn-taking between two children


class GameStatus(StrEnum):
    """Match state."""
    IN_PROGRESS = "in_progress"
    WON = "won"
    DRAW = "draw"


@dataclass(frozen=True, slots=True)
class LevelConfig:
    """Developmental level configuration (Section 8.4)."""
    difficulty: int
    cols: int
    rows: int
    target_in_a_row: int
    cpu_intelligence: str  # "silly", "defensive", "smart", "strategic"
    name_key: str


LEVEL_CONFIGS: Final[dict[int, LevelConfig]] = {
    1: LevelConfig(
        difficulty=1,
        cols=5,
        rows=4,
        target_in_a_row=3,
        cpu_intelligence="silly",
        name_key="ui.diff_1",
    ),
    2: LevelConfig(
        difficulty=2,
        cols=6,
        rows=5,
        target_in_a_row=3,
        cpu_intelligence="defensive",
        name_key="ui.diff_2",
    ),
    3: LevelConfig(
        difficulty=3,
        cols=7,
        rows=6,
        target_in_a_row=4,
        cpu_intelligence="smart",
        name_key="ui.diff_3",
    ),
    4: LevelConfig(
        difficulty=4,
        cols=7,
        rows=6,
        target_in_a_row=4,
        cpu_intelligence="strategic",
        name_key="ui.diff_4",
    ),
}

# Color definitions (Storybook natural meadow palette)
COLOR_SKY_TOP: Final[tuple[int, int, int]] = (205, 235, 252)
COLOR_SKY_BOTTOM: Final[tuple[int, int, int]] = (240, 248, 255)
COLOR_HILL_DISTANT: Final[tuple[int, int, int]] = (150, 205, 120)
COLOR_HILL_NEAR: Final[tuple[int, int, int]] = (110, 180, 80)
COLOR_GRASS_TABLE: Final[tuple[int, int, int]] = (95, 165, 68)
COLOR_TABLE_WOOD: Final[tuple[int, int, int]] = (196, 148, 92)
COLOR_TABLE_WOOD_DARK: Final[tuple[int, int, int]] = (148, 102, 54)

# Wooden board
COLOR_BOARD_WOOD: Final[tuple[int, int, int]] = (218, 162, 98)
COLOR_BOARD_DARK: Final[tuple[int, int, int]] = (128, 80, 36)
COLOR_BOARD_LIGHT: Final[tuple[int, int, int]] = (242, 194, 136)
COLOR_BOARD_HOLE: Final[tuple[int, int, int]] = (72, 42, 18)
COLOR_BOARD_HOLE_RIM: Final[tuple[int, int, int]] = (148, 98, 52)
COLOR_BOARD_LEG: Final[tuple[int, int, int]] = (142, 90, 44)

# Flash Tokens (Carrot orange)
COLOR_FLASH_MAIN: Final[tuple[int, int, int]] = (255, 122, 24)
COLOR_FLASH_LIGHT: Final[tuple[int, int, int]] = (255, 174, 88)
COLOR_FLASH_DARK: Final[tuple[int, int, int]] = (196, 76, 8)
COLOR_CARROT_LEAF: Final[tuple[int, int, int]] = (58, 182, 52)
COLOR_CARROT_LEAF_LIGHT: Final[tuple[int, int, int]] = (96, 214, 88)

# Leo Tokens (Vibrant acorn purple)
COLOR_LEO_MAIN: Final[tuple[int, int, int]] = (126, 87, 214)
COLOR_LEO_LIGHT: Final[tuple[int, int, int]] = (182, 150, 245)
COLOR_LEO_DARK: Final[tuple[int, int, int]] = (78, 44, 158)
COLOR_ACORN_CAP: Final[tuple[int, int, int]] = (142, 106, 92)
COLOR_ACORN_STEM: Final[tuple[int, int, int]] = (94, 62, 52)

# UI Elements
COLOR_BANNER_BG: Final[tuple[int, int, int]] = (255, 252, 244)
COLOR_BANNER_BORDER: Final[tuple[int, int, int]] = (180, 135, 80)
COLOR_TEXT_DARK: Final[tuple[int, int, int]] = (56, 42, 30)
COLOR_TEXT_MUTED: Final[tuple[int, int, int]] = (118, 98, 78)
COLOR_GOLD: Final[tuple[int, int, int]] = (255, 215, 0)
COLOR_WIN_GLOW: Final[tuple[int, int, int]] = (255, 245, 120)
