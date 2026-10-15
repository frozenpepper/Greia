"""Tito's Marble Run — authored boards, pieces and physics constants.

Pure data (no Pygame). Every board lives in fixed *board units*
(``BOARD_WIDTH`` x ``BOARD_HEIGHT``, y grows downwards) so the physics is
identical at every screen size; the layout maps units to the reference canvas.

A board is a picture puzzle: the marble waits in a tube at the top, the basket
sits somewhere below, a few fixed wooden shelves shape the run and 1-3 shining
**slots** are the only places where the child's pieces can go. The tray holds
exactly the pieces of that board. Sets introduce one new piece at a time:
ramps (place, then turn), the bumper block (stop and drop), the funnel
(gather and drop straight down), then everything together. Each board carries
at least one authored solution; tests prove every solution lands in the basket
and that an empty board (and the obvious wrong turns) do not.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Final

Point = tuple[float, float]

BOARD_WIDTH: Final = 800
BOARD_HEIGHT: Final = 480

# -- physics (board units, seconds) -------------------------------------------
STEP_SECONDS: Final = 1.0 / 120.0  # fixed physics step (deterministic)
MAX_STEPS_PER_FRAME: Final = 8  # a stalled frame never fast-forwards a run
GRAVITY: Final = 760.0
MAX_SPEED: Final = 900.0  # <= 7.5 units per step, far below the contact depth
AIR_DRAG: Final = 0.02  # per second
ROLL_DRAG: Final = 0.35  # per second while touching something
BOUNCE_MIN: Final = 70.0  # slower impacts do not bounce (no endless jitter)
HIT_SOUND_MIN: Final = 120.0  # impact speed that makes a "clack"

MARBLE_RADIUS: Final = 16.0
PLANK_RADIUS: Final = 9.0  # half the thickness of every wooden plank
SHELF_RESTITUTION: Final = 0.25
BUMPER_RESTITUTION: Final = 0.5
BASKET_RESTITUTION: Final = 0.2

# Every run ends: in the basket, off the bottom of the board, or at rest (the
# marble moved less than REST_RADIUS for REST_SECONDS), or at the hard cap.
REST_RADIUS: Final = 3.0
REST_SECONDS: Final = 0.7
MAX_RUN_SECONDS: Final = 10.0

# -- pieces -------------------------------------------------------------------
RAMP_HALF_LENGTH: Final = 74.0
RAMP_TILT_DEGREES: Final = 22.0
BUMPER_RADIUS: Final = 26.0
BUMPER_HALF_HEIGHT: Final = 16.0
FUNNEL_MOUTH: Final = 70.0  # half width of the funnel's top opening
FUNNEL_SPOUT: Final = 31.0  # half width at the spout (inner gap 2*(31-9) = 44)
FUNNEL_DEPTH: Final = 30.0  # spout sits this far below the slot centre
FUNNEL_TOP: Final = 30.0  # mouth sits this far above the slot centre
FUNNEL_TUBE: Final = 26.0  # straight spout below the V (straightens the drop)

# Slot hit/ghost box (board units) and the basket's inner size.
SLOT_WIDTH: Final = 156.0
SLOT_HEIGHT: Final = 84.0
BASKET_INNER: Final = 104.0
BASKET_DEPTH: Final = 64.0
BASKET_WALL: Final = 6.0


class PieceKind(StrEnum):
    RAMP = "ramp"
    BUMPER = "bumper"
    FUNNEL = "funnel"


class Facing(StrEnum):
    """Which way a ramp runs downhill."""

    RIGHT = "right"
    LEFT = "left"

    def flipped(self) -> "Facing":
        return Facing.LEFT if self is Facing.RIGHT else Facing.RIGHT


@dataclass(frozen=True, slots=True)
class Capsule:
    """A collider: a segment ``a``-``b`` thickened by ``radius`` (a circle when a == b)."""

    a: Point
    b: Point
    radius: float
    restitution: float
    tag: str  # "shelf" | "wall" | "basket" | "piece:<slot index>"


def piece_capsules(kind: PieceKind, facing: Facing, centre: Point, tag: str) -> tuple[Capsule, ...]:
    """Colliders of one piece placed at ``centre`` (pure geometry)."""

    cx, cy = centre
    if kind is PieceKind.RAMP:
        angle = math.radians(RAMP_TILT_DEGREES)
        dx = math.cos(angle) * RAMP_HALF_LENGTH
        dy = math.sin(angle) * RAMP_HALF_LENGTH
        if facing is Facing.LEFT:
            dy = -dy
        return (Capsule((cx - dx, cy - dy), (cx + dx, cy + dy), PLANK_RADIUS, SHELF_RESTITUTION, tag),)
    if kind is PieceKind.BUMPER:
        return (
            Capsule(
                (cx, cy - BUMPER_HALF_HEIGHT),
                (cx, cy + BUMPER_HALF_HEIGHT),
                BUMPER_RADIUS,
                BUMPER_RESTITUTION,
                tag,
            ),
        )
    return (
        Capsule((cx - FUNNEL_MOUTH, cy - FUNNEL_TOP), (cx - FUNNEL_SPOUT, cy + FUNNEL_DEPTH), PLANK_RADIUS, SHELF_RESTITUTION, tag),
        Capsule((cx + FUNNEL_MOUTH, cy - FUNNEL_TOP), (cx + FUNNEL_SPOUT, cy + FUNNEL_DEPTH), PLANK_RADIUS, SHELF_RESTITUTION, tag),
        Capsule((cx - FUNNEL_SPOUT, cy + FUNNEL_DEPTH), (cx - FUNNEL_SPOUT, cy + FUNNEL_DEPTH + FUNNEL_TUBE), PLANK_RADIUS, SHELF_RESTITUTION, tag),
        Capsule((cx + FUNNEL_SPOUT, cy + FUNNEL_DEPTH), (cx + FUNNEL_SPOUT, cy + FUNNEL_DEPTH + FUNNEL_TUBE), PLANK_RADIUS, SHELF_RESTITUTION, tag),
    )


@dataclass(frozen=True, slots=True)
class Shelf:
    """A fixed wooden plank of the board (not movable)."""

    a: Point
    b: Point


@dataclass(frozen=True, slots=True)
class Start:
    """The tube the marble drops out of (and its initial sideways speed)."""

    x: float
    y: float
    vx: float = 0.0


@dataclass(frozen=True, slots=True)
class Basket:
    x: float  # centre
    floor: float  # y of the basket floor

    @property
    def rim(self) -> float:
        return self.floor - BASKET_DEPTH

    def capsules(self) -> tuple[Capsule, ...]:
        half = BASKET_INNER / 2 + BASKET_WALL
        left, right = self.x - half, self.x + half
        return (
            Capsule((left, self.rim), (left, self.floor), BASKET_WALL, BASKET_RESTITUTION, "basket"),
            Capsule((right, self.rim), (right, self.floor), BASKET_WALL, BASKET_RESTITUTION, "basket"),
            Capsule((left, self.floor), (right, self.floor), BASKET_WALL, BASKET_RESTITUTION, "basket"),
        )

    def holds(self, x: float, y: float) -> bool:
        """True once the marble is inside the basket, below its rim."""

        return abs(x - self.x) < BASKET_INNER / 2 and self.rim + MARBLE_RADIUS * 0.6 < y < self.floor


@dataclass(frozen=True, slots=True)
class Placement:
    """One piece of a solution: tray piece ``piece`` in slot ``slot`` facing ``facing``."""

    piece: int
    slot: int
    facing: Facing = Facing.RIGHT


@dataclass(frozen=True, slots=True)
class Board:
    """One authored puzzle board."""

    board_id: str
    start: Start
    basket: Basket
    slots: tuple[Point, ...]
    pieces: tuple[PieceKind, ...]
    shelves: tuple[Shelf, ...] = ()
    solutions: tuple[tuple[Placement, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class BoardSet:
    """Four boards in one setting; a visit plays one set to the completion scene."""

    set_id: str
    setting: str  # "garden" | "playroom"
    new_piece: PieceKind
    boards: tuple[Board, ...]


R, L = Facing.RIGHT, Facing.LEFT
P = Placement
RAMP, BUMPER, FUNNEL = PieceKind.RAMP, PieceKind.BUMPER, PieceKind.FUNNEL

BOARD_SETS: Final[tuple[BoardSet, ...]] = (
    BoardSet(
        "ramps",
        "garden",
        RAMP,
        (
            # 1. One ramp, one slot: place it and the marble rolls to the basket.
            Board(
                "ramps.1",
                Start(250.0, 60.0),
                Basket(495.0, 452.0),
                slots=((290.0, 250.0),),
                pieces=(RAMP,),
                solutions=((P(0, 0, R),),),
            ),
            # 2. The basket is on the other side: the ramp must be turned.
            Board(
                "ramps.2",
                Start(550.0, 60.0),
                Basket(305.0, 452.0),
                slots=((510.0, 250.0),),
                pieces=(RAMP,),
                solutions=((P(0, 0, L),),),
            ),
            # 3. Two slots, one ramp: which spot does the marble fall on?
            Board(
                "ramps.3",
                Start(380.0, 60.0),
                Basket(640.0, 452.0),
                slots=((190.0, 230.0), (420.0, 210.0)),
                pieces=(RAMP,),
                solutions=((P(0, 1, R),),),
            ),
            # 4. Zig-zag: two ramps hand the marble down and back.
            Board(
                "ramps.4",
                Start(220.0, 60.0),
                Basket(340.0, 452.0),
                slots=((250.0, 170.0), (470.0, 300.0)),
                pieces=(RAMP, RAMP),
                solutions=((P(0, 0, R), P(1, 1, L)),),
            ),
        ),
    ),
    BoardSet(
        "bumpers",
        "playroom",
        BUMPER,
        (
            # 5. The shelf throws the marble too far: a bumper stops it over the basket.
            Board(
                "bumpers.1",
                Start(190.0, 60.0),
                Basket(455.0, 452.0),
                slots=((545.0, 262.0),),
                pieces=(BUMPER,),
                shelves=(Shelf((140.0, 150.0), (440.0, 260.0)),),
                solutions=((P(0, 0, R),),),
            ),
            # 6. Bumper or ramp? Only one of them stops the marble.
            Board(
                "bumpers.2",
                Start(610.0, 60.0),
                Basket(345.0, 452.0),
                slots=((255.0, 262.0),),
                pieces=(RAMP, BUMPER),
                shelves=(Shelf((660.0, 150.0), (360.0, 260.0)),),
                solutions=((P(1, 0, R),),),
            ),
            # 7. A ramp sends it, a bumper stops it.
            Board(
                "bumpers.3",
                Start(230.0, 60.0),
                Basket(345.0, 452.0),
                slots=((260.0, 190.0), (433.0, 240.0)),
                pieces=(RAMP, BUMPER),
                solutions=((P(0, 0, R), P(1, 1, R)),),
            ),
            # 8. Three spots, three pieces: plan the whole run.
            Board(
                "bumpers.4",
                Start(570.0, 60.0),
                Basket(435.0, 452.0),
                slots=((540.0, 190.0), (367.0, 240.0), (180.0, 250.0)),
                pieces=(RAMP, RAMP, BUMPER),
                solutions=((P(0, 0, L), P(2, 1, R)),),
            ),
        ),
    ),
    BoardSet(
        "funnels",
        "garden",
        FUNNEL,
        (
            # 9. A peg bounces the marble away: the funnel gathers it.
            Board(
                "funnels.1",
                Start(400.0, 60.0),
                Basket(330.0, 452.0),
                slots=((320.0, 320.0),),
                pieces=(FUNNEL,),
                shelves=(Shelf((412.0, 200.0), (412.0, 200.0)),),
                solutions=((P(0, 0, R),),),
            ),
            # 10. Funnel or ramp under the flying marble?
            Board(
                "funnels.2",
                Start(610.0, 60.0),
                Basket(280.0, 452.0),
                slots=((270.0, 330.0),),
                pieces=(RAMP, FUNNEL),
                shelves=(Shelf((660.0, 150.0), (360.0, 260.0)),),
                solutions=((P(1, 0, R),),),
            ),
            # 11. A ramp sends it, the funnel drops it in.
            Board(
                "funnels.3",
                Start(600.0, 60.0),
                Basket(445.0, 452.0),
                slots=((570.0, 180.0), (430.0, 300.0)),
                pieces=(FUNNEL, RAMP),
                solutions=((P(1, 0, L), P(0, 1, R)),),
            ),
            # 12. Everything together (the bumper is optional: two ways work).
            Board(
                "funnels.4",
                Start(230.0, 60.0),
                Basket(415.0, 452.0),
                slots=((260.0, 190.0), (433.0, 240.0), (400.0, 340.0)),
                pieces=(RAMP, BUMPER, FUNNEL),
                solutions=((P(0, 0, R), P(1, 1, R), P(2, 2, R)), (P(0, 0, R), P(2, 2, R))),
            ),
        ),
    ),
)

BOARDS_PER_SET: Final = 4
ALL_BOARDS: Final[tuple[Board, ...]] = tuple(board for board_set in BOARD_SETS for board in board_set.boards)


def board_walls() -> tuple[Capsule, ...]:
    """The board's frame: solid left/right sides and top; the bottom is open."""

    w, h = float(BOARD_WIDTH), float(BOARD_HEIGHT)
    r = 4.0
    return (
        Capsule((-r, -200.0), (-r, h + 200.0), r, SHELF_RESTITUTION, "wall"),
        Capsule((w + r, -200.0), (w + r, h + 200.0), r, SHELF_RESTITUTION, "wall"),
        Capsule((0.0, -r), (w, -r), r, SHELF_RESTITUTION, "wall"),
    )


__all__ = [
    "ALL_BOARDS",
    "BASKET_DEPTH",
    "BASKET_INNER",
    "BOARD_HEIGHT",
    "BOARD_SETS",
    "BOARD_WIDTH",
    "BOARDS_PER_SET",
    "Basket",
    "Board",
    "BoardSet",
    "Capsule",
    "Facing",
    "MARBLE_RADIUS",
    "PieceKind",
    "Placement",
    "Shelf",
    "Start",
    "board_walls",
    "piece_capsules",
]
