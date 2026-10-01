"""Content, layout definitions, and constants for Corsa delle Bacche."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

# Grid metrics
GRID_COLS: Final[int] = 19
GRID_ROWS: Final[int] = 11
CELL_SIZE: Final[int] = 40
GRID_ORIGIN_X: Final[int] = (REFERENCE_WIDTH - GRID_COLS * CELL_SIZE) // 2  # 132
GRID_ORIGIN_Y: Final[int] = 95  # Safe below system chrome (0..160, 0..50)

# Colors
COLOR_BG_GARDEN: Final[tuple[int, int, int]] = (236, 246, 230)
COLOR_PATH: Final[tuple[int, int, int]] = (248, 242, 224)
COLOR_PATH_BORDER: Final[tuple[int, int, int]] = (226, 216, 192)
COLOR_HEDGE: Final[tuple[int, int, int]] = (52, 126, 62)
COLOR_HEDGE_SHADOW: Final[tuple[int, int, int]] = (34, 88, 42)
COLOR_HEDGE_LIGHT: Final[tuple[int, int, int]] = (80, 168, 92)
COLOR_HEDGE_FLOWER: Final[tuple[int, int, int]] = (255, 245, 170)

# Character colors
COLOR_MOMO_ORANGE: Final[tuple[int, int, int]] = (235, 115, 35)
COLOR_MOMO_BELLY: Final[tuple[int, int, int]] = (255, 235, 205)
COLOR_MOMO_TAIL: Final[tuple[int, int, int]] = (245, 145, 65)
COLOR_MOMO_INNER_EAR: Final[tuple[int, int, int]] = (245, 175, 165)
COLOR_MOMO_DARK: Final[tuple[int, int, int]] = (40, 25, 20)

COLOR_BAFFO_BROWN: Final[tuple[int, int, int]] = (135, 90, 55)
COLOR_BAFFO_BELLY: Final[tuple[int, int, int]] = (215, 185, 150)
COLOR_BAFFO_NOSE: Final[tuple[int, int, int]] = (235, 125, 140)

COLOR_BEE_YELLOW: Final[tuple[int, int, int]] = (252, 215, 45)
COLOR_BEE_STRIPE: Final[tuple[int, int, int]] = (45, 40, 35)
COLOR_BEE_WING: Final[tuple[int, int, int, int]] = (220, 240, 255, 200)

# Collectible colors
COLOR_STRAWBERRY: Final[tuple[int, int, int]] = (235, 45, 65)
COLOR_STRAWBERRY_SEED: Final[tuple[int, int, int]] = (255, 235, 120)
COLOR_STRAWBERRY_LEAF: Final[tuple[int, int, int]] = (65, 165, 65)
COLOR_BLUEBERRY: Final[tuple[int, int, int]] = (70, 100, 215)
COLOR_GOLDEN_BERRY: Final[tuple[int, int, int]] = (255, 195, 30)

COLOR_RAINBOW: Final[list[tuple[int, int, int]]] = [
    (255, 80, 80),
    (255, 160, 50),
    (255, 230, 60),
    (70, 215, 95),
    (60, 175, 255),
    (175, 85, 255),
]

COLOR_HEART: Final[tuple[int, int, int]] = (235, 55, 75)
COLOR_HUD_TEXT: Final[tuple[int, int, int]] = (45, 55, 40)
COLOR_STAR_GOLD: Final[tuple[int, int, int]] = (255, 215, 35)


class BerryType(Enum):
    BLUEBERRY = auto()
    STRAWBERRY = auto()
    GOLDEN_BERRY = auto()
    RAINBOW_STAR = auto()


class CritterKind(Enum):
    BAFFO = auto()   # Grumpy sleepy hedgehog
    BEE = auto()     # Buzzing garden bumblebee


class Direction(Enum):
    NONE = (0, 0)
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def opposite(self) -> "Direction":
        if self == Direction.UP:
            return Direction.DOWN
        if self == Direction.DOWN:
            return Direction.UP
        if self == Direction.LEFT:
            return Direction.RIGHT
        if self == Direction.RIGHT:
            return Direction.LEFT
        return Direction.NONE


@dataclass(frozen=True)
class CritterConfig:
    kind: CritterKind
    start_grid: tuple[int, int]
    speed: float
    patrol_route: list[tuple[int, int]] = field(default_factory=list)
    nap_interval: float = 0.0
    nap_duration: float = 0.0


@dataclass(frozen=True)
class LevelConfig:
    level_number: int
    name_key: str
    maze_layout: list[str]
    momo_start: tuple[int, int]
    critters: list[CritterConfig]
    has_bonus_fruit: bool = False
    powerup_duration: float = 6.0


# 5 Curated Levels matching D1-D5 specifications
LEVEL_1_LAYOUT: list[str] = [
    "###################",
    "#M....#.....#....*#",
    "#.###.#.###.#.###.#",
    "#...#...#.#...#...#",
    "###.###.#.#.###.###",
    "#.......#.#.......#",
    "###.###.#.#.###.###",
    "#...#...#.#...#...#",
    "#.###.#.###.#.###.#",
    "#*....#.....#....*#",
    "###################",
]

LEVEL_2_LAYOUT: list[str] = [
    "###################",
    "#M.................#",
    "#.###.#########.###.#",
    "#.#...#.......#...#.#",
    "#.#.###...H...###.#.#",
    "#.......#####.......#",
    "#.#.###...#...###.#.#",
    "#.#...#.......#...#.#",
    "#.###.#########.###.#",
    "#.................*#",
    "###################",
]

LEVEL_3_LAYOUT: list[str] = [
    "###################",
    "#M....#...*...#....#",
    "#@###.#.#####.#.###@",
    "#.#...#...#...#...#.#",
    "#.#.#####.#.#####.#.#",
    "#.........H.........#",
    "#.#####.#####.#####.#",
    "#...#.....#.....#...#",
    "#.###.###.#.###.###.#",
    "#*....#.......#...*#",
    "###################",
]

LEVEL_4_LAYOUT: list[str] = [
    "###################",
    "#M..#...*...*...#..#",
    "#.#.#.#########.#.#.#",
    "#.#.....#...#.....#.#",
    "#@#####.#.H.#.#####@",
    "#.......#...#.......#",
    "#.#####.#.B.#.#####.#",
    "#.#.....#...#.....#.#",
    "#.#.###.#####.###.#.#",
    "#...#...........#..#",
    "###################",
]

LEVEL_5_LAYOUT: list[str] = [
    "###################",
    "#M..#...*#*...#...*#",
    "#@#.###.#.#.###.#.#@",
    "#.#.#...#.#...#.#.#.#",
    "#.#.#.###.###.#.#.#.#",
    "#.....#..H..#.....#.#",
    "#.###.#.###.#.###.#.#",
    "#...#.#..B..#.#...#.#",
    "###.#.#######.#.###.#",
    "#*....#...@...#...*#",
    "###################",
]

LEVELS: Final[list[LevelConfig]] = [
    # D1: Open gentle maze, 0 pursuers, joyful berry harvesting
    LevelConfig(
        level_number=1,
        name_key="level.1",
        maze_layout=LEVEL_1_LAYOUT,
        momo_start=(1, 1),
        critters=[],
        has_bonus_fruit=False,
    ),
    # D2: 1 slow sleepy hedgehog with frequent nap pauses
    LevelConfig(
        level_number=2,
        name_key="level.2",
        maze_layout=LEVEL_2_LAYOUT,
        momo_start=(1, 1),
        critters=[
            CritterConfig(
                kind=CritterKind.BAFFO,
                start_grid=(9, 4),
                speed=46.0,
                nap_interval=4.0,
                nap_duration=2.5,
            )
        ],
        has_bonus_fruit=False,
    ),
    # D3: 1 active patrol creature, rainbow berry power-up available
    LevelConfig(
        level_number=3,
        name_key="level.3",
        maze_layout=LEVEL_3_LAYOUT,
        momo_start=(1, 1),
        critters=[
            CritterConfig(
                kind=CritterKind.BAFFO,
                start_grid=(9, 5),
                speed=64.0,
                nap_interval=6.5,
                nap_duration=1.8,
            )
        ],
        has_bonus_fruit=False,
        powerup_duration=6.0,
    ),
    # D4: 2 creatures (Baffo + Bee) with distinct patrol routes, moving bonus fruit
    LevelConfig(
        level_number=4,
        name_key="level.4",
        maze_layout=LEVEL_4_LAYOUT,
        momo_start=(1, 1),
        critters=[
            CritterConfig(
                kind=CritterKind.BAFFO,
                start_grid=(9, 4),
                speed=68.0,
                nap_interval=7.0,
                nap_duration=2.0,
            ),
            CritterConfig(
                kind=CritterKind.BEE,
                start_grid=(9, 6),
                speed=82.0,
                nap_interval=0.0,
                nap_duration=0.0,
            ),
        ],
        has_bonus_fruit=True,
        powerup_duration=6.0,
    ),
    # D5: Challenging winding maze layout, smart patrol, lots of sparkle stars
    LevelConfig(
        level_number=5,
        name_key="level.5",
        maze_layout=LEVEL_5_LAYOUT,
        momo_start=(1, 1),
        critters=[
            CritterConfig(
                kind=CritterKind.BAFFO,
                start_grid=(9, 5),
                speed=75.0,
                nap_interval=8.0,
                nap_duration=1.5,
            ),
            CritterConfig(
                kind=CritterKind.BEE,
                start_grid=(9, 7),
                speed=92.0,
                nap_interval=0.0,
                nap_duration=0.0,
            ),
        ],
        has_bonus_fruit=True,
        powerup_duration=6.0,
    ),
]
