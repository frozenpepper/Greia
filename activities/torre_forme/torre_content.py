from __future__ import annotations

"""Constants, geometry, shapes and color palettes for La Torre delle Forme."""

from dataclasses import dataclass
from enum import IntEnum

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600

# Cozy wooden tower grid
GRID_COLS = 8
GRID_ROWS = 10
CELL_SIZE = 46

TOWER_X = 220
TOWER_Y = 88
TOWER_WIDTH = GRID_COLS * CELL_SIZE
TOWER_HEIGHT = GRID_ROWS * CELL_SIZE

STORAGE_KEY = "torre_forme_save"


class TowerMode(IntEnum):
    FREE_BUILD = 1      # Costruisci Libero (Age 3, D1-D2)
    SLOW_FALL = 2       # Scendi Piano (Age 4, D3)
    TOWER_CHALLENGE = 3 # Sfida della Torre (Age 5, D4-D5)


# High-contrast storybook wooden toy palette
COLOR_FRAME_OUTER = (110, 68, 38)
COLOR_FRAME_INNER = (148, 98, 56)
COLOR_CELL_BG = (248, 238, 220)
COLOR_CELL_GRID = (218, 198, 172)
COLOR_BACKGROUND = (245, 236, 218)
COLOR_PANEL_BG = (255, 252, 245)
COLOR_PANEL_BORDER = (168, 130, 96)

# Wooden toy block colors (warm, matte, friendly)
COLOR_SQUARE = (245, 158, 11)     # Warm Sunny Amber
COLOR_BAR_2 = (59, 130, 246)      # Sky Blue
COLOR_BAR_3 = (14, 165, 233)      # Light Cerulean
COLOR_CORNER_L = (249, 115, 22)   # Coral Orange
COLOR_ROOF = (34, 197, 94)        # Spring Green
COLOR_ARCH = (168, 85, 247)       # Lavender Purple
COLOR_RAINBOW = (250, 204, 21)    # Golden Star Sparkle


@dataclass(frozen=True)
class ShapeDefinition:
    shape_id: str
    name_key: str
    color: tuple[int, int, int]
    blocks: tuple[tuple[int, int], ...]
    can_rotate: bool = True
    is_rainbow: bool = False


# Shapes: Chunky wooden toy blocks
SHAPES: dict[str, ShapeDefinition] = {
    "square": ShapeDefinition(
        shape_id="square",
        name_key="shape.square",
        color=COLOR_SQUARE,
        blocks=((0, 0), (1, 0), (0, 1), (1, 1)),
        can_rotate=False,
    ),
    "bar_2": ShapeDefinition(
        shape_id="bar_2",
        name_key="shape.bar_2",
        color=COLOR_BAR_2,
        blocks=((0, 0), (1, 0)),
        can_rotate=True,
    ),
    "bar_3": ShapeDefinition(
        shape_id="bar_3",
        name_key="shape.bar_3",
        color=COLOR_BAR_3,
        blocks=((0, 0), (1, 0), (2, 0)),
        can_rotate=True,
    ),
    "corner_l": ShapeDefinition(
        shape_id="corner_l",
        name_key="shape.corner_l",
        color=COLOR_CORNER_L,
        blocks=((0, 0), (0, 1), (1, 1)),
        can_rotate=True,
    ),
    "roof_wedge": ShapeDefinition(
        shape_id="roof_wedge",
        name_key="shape.roof_wedge",
        color=COLOR_ROOF,
        blocks=((1, 0), (0, 1), (1, 1), (2, 1)),
        can_rotate=True,
    ),
    "arch_bridge": ShapeDefinition(
        shape_id="arch_bridge",
        name_key="shape.arch_bridge",
        color=COLOR_ARCH,
        blocks=((0, 0), (1, 0), (2, 0), (0, 1), (2, 1)),
        can_rotate=True,
    ),
    "rainbow_star": ShapeDefinition(
        shape_id="rainbow_star",
        name_key="shape.rainbow_star",
        color=COLOR_RAINBOW,
        blocks=((0, 0),),
        can_rotate=False,
        is_rainbow=True,
    ),
}

# Mode shapes availability
FREE_BUILD_SHAPES = ["square", "bar_2", "bar_3", "corner_l", "roof_wedge", "arch_bridge"]
SLOW_FALL_SHAPES = ["square", "bar_2", "bar_3", "corner_l", "roof_wedge"]
CHALLENGE_SHAPES = ["square", "bar_2", "bar_3", "corner_l", "roof_wedge", "arch_bridge", "rainbow_star"]
