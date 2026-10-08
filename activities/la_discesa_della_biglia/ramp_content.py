"""La Discesa della Biglia — level, tool and physics content.

This module is the single source of truth for:
  * the three authored physical layouts (open, moving and narrow);
    no fourth level is generated and difficulty is not adaptive;
  * the four draggable tools the child can place on the playfield
    (slope, bumper, fan, spring);
  * the physics constants used by the engine (gravity, restitution,
    spring impulse, fan wind).

Constants are pulled out of main.py so the engine + render layer
can both read them without re-declaring. They are deliberately
small integers; on the Acer reference floor the simulation
sub-steps 4 times per frame to keep trajectories stable without
spending the entire frame budget on physics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final


# Reference viewport (1024x600) used by the platform. The real Shell
# viewports are scaled by ChildUiMetrics; everything here lives in
# reference pixels so the visual layout is identical at the canonical
# floor and the engine can be unit-tested in isolation.
REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

# Playfield geometry
PLAYFIELD_LEFT: Final = 80
PLAYFIELD_RIGHT: Final = 944
PLAYFIELD_TOP: Final = 70
PLAYFIELD_BOTTOM: Final = 470
TOOL_PALETTE_TOP: Final = 488

# Physics constants (per second unless noted)
GRAVITY: Final = 880.0            # px / s^2
RESTITUTION: Final = 0.55          # marble on tool / wall bounce
FRICTION_PER_SECOND: Final = 0.4   # linear damping coefficient
SPRING_IMPULSE: Final = 360.0      # px / s outward on activation
FAN_WIND: Final = 240.0            # px / s^2 horizontal push while in arc
PHYSICS_SUBSTEPS: Final = 4        # physics sub-steps per frame
MAX_DT: Final = 1.0 / 30.0         # upper-bound a single frame delta

# Marble
MARBLE_RADIUS: Final = 14
MARBLE_COLOR: Final = (245, 158, 11)
MARBLE_OUTLINE: Final = (180, 83, 9)
MARBLE_START: Final = (160.0, 110.0)
MARBLE_SPAWN_DELAY: Final = 0.45  # seconds between release and the start of the drop

# Tools
TOOL_RADIUS: Final = 22
TOOL_BUMPER_RADIUS: Final = 26
SPRING_RADIUS: Final = 24


class ToolKind(StrEnum):
    SLOPE = "slope"
    BUMPER = "bumper"
    FAN = "fan"
    SPRING = "spring"


TOOL_COLORS: Final[dict[ToolKind, tuple[int, int, int]]] = {
    ToolKind.SLOPE: (180, 130, 70),
    ToolKind.BUMPER: (239, 68, 68),
    ToolKind.FAN: (56, 189, 248),
    ToolKind.SPRING: (34, 197, 94),
}


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Static description of a tool a child can drag onto the playfield."""

    kind: ToolKind
    label_key: str
    palette_index: int


TOOL_CATALOGUE: Final[tuple[ToolSpec, ...]] = (
    ToolSpec(ToolKind.SLOPE, "tool_slope", 0),
    ToolSpec(ToolKind.BUMPER, "tool_bumper", 1),
    ToolSpec(ToolKind.FAN, "tool_fan", 2),
    ToolSpec(ToolKind.SPRING, "tool_spring", 3),
)


@dataclass(frozen=True, slots=True)
class PlacedTool:
    """A tool the child has dropped onto the playfield."""

    spec: ToolSpec
    x: float
    y: float
    angle: float = 0.0  # for slope tilt; unused for the others


@dataclass(frozen=True, slots=True)
class Level:
    """A single play level: start position is fixed; basket varies."""

    level_id: str
    basket_x: float
    basket_y: float
    basket_radius: float
    basket_moves: bool = False
    basket_amplitude: float = 0.0
    basket_period: float = 0.0
    obstacles: tuple[tuple[float, float, float], ...] = field(default_factory=tuple)
    time_bonus: float = 1.0  # personal-best allowance (seconds) above the canonical


LEVELS: Final[tuple[Level, ...]] = (
    Level(
        level_id="open",
        basket_x=820.0,
        basket_y=400.0,
        basket_radius=46.0,
    ),
    Level(
        level_id="moving",
        basket_x=760.0,
        basket_y=380.0,
        basket_radius=42.0,
        basket_moves=True,
        basket_amplitude=80.0,
        basket_period=2.6,
    ),
    Level(
        level_id="narrow",
        basket_x=860.0,
        basket_y=410.0,
        basket_radius=32.0,
        obstacles=((220.0, 320.0, 30.0), (520.0, 360.0, 30.0)),
    ),
)


@dataclass(frozen=True, slots=True)
class ProgressState:
    """Durable per-profile progress for the Activity.

    Stored through the platform's approved Activity storage, never as
    authoritative global state. Per-level best time in seconds; a
    missing value means the child has not completed that level yet.
    """

    best_times: dict[str, float]


def empty_progress() -> ProgressState:
    return ProgressState(best_times={})
