"""Courses, physics constants and the difficulty ladder of Colline Allegre.

Pure data. A *set* is five finite courses of rising bumpiness, each in its
own shared-library biome, each ending at a picnic where a cast friend waits:

1. meadow    — gentle rolling hills; Tito's buggy rights itself in the air;
2. pond      — bigger hills, a small jump and a wooden bridge over the pond;
3. autumn    — mud patches that slow the buggy (keep going, do not stop);
4. snow      — steep drops behind a turtle sign: slow down before the edge;
5. sky       — high hills above the clouds, bouncy mushrooms and a drop.

A course is a sequence of terrain *features* laid end to end after a flat
start. The ``rung`` (1 gentle, 2 bumpy, 3 wild) scales every hill height
between sets; it adapts to how many tumbles the last set had. Nothing here
draws, plays sound or touches storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

# -- fixed-step physics --------------------------------------------------------

FIXED_DT: Final[float] = 1.0 / 120.0
MAX_STEPS_PER_FRAME: Final[int] = 8  # a slow frame never spirals (<= 1/15 s simulated)

# Vehicle geometry (logical px). The buggy art is drawn to these numbers.
WHEELBASE: Final[float] = 96.0
WHEEL_RADIUS: Final[float] = 23.0
CHASSIS_WIDTH: Final[float] = 150.0
CHASSIS_HEIGHT: Final[float] = 52.0

SUSPENSION_REST_LENGTH: Final[float] = 30.0
SUSPENSION_MIN_LENGTH: Final[float] = 10.0
SUSPENSION_MAX_LENGTH: Final[float] = 48.0
SUSPENSION_STIFFNESS: Final[float] = 260.0
SUSPENSION_DAMPING: Final[float] = 16.0

GRAVITY: Final[float] = 820.0
DRIVE_ACCEL: Final[float] = 520.0
BRAKE_DECEL: Final[float] = 700.0
ROLLING_FRICTION: Final[float] = 0.9965  # per fixed step
AIR_DRAG: Final[float] = 0.9985  # per fixed step
MAX_FORWARD_SPEED: Final[float] = 380.0
MAX_REVERSE_SPEED: Final[float] = -90.0
MUD_TRACTION: Final[float] = 0.45
MUD_DRAG: Final[float] = 0.985  # per fixed step while a wheel is in mud

AIR_TILT_TORQUE: Final[float] = 5.2
ANGULAR_DAMPING: Final[float] = 3.6
AUTO_UPRIGHT_GAIN: Final[float] = 6.0
PERFECT_LANDING_ANGLE_TOLERANCE: Final[float] = 0.28  # ~16 degrees
PERFECT_LANDING_MIN_AIR: Final[float] = 0.35
PERFECT_LANDING_BOOST: Final[float] = 70.0

# A tumble: upside down this long (in the air or on the roof) -> back to the flag.
FLIP_TOLERANCE_ANGLE: Final[float] = 2.0  # ~115 degrees
FLIP_DURATION_THRESHOLD: Final[float] = 0.45
# Leaving a drop edge faster than this sends the buggy head over heels.
DROP_SAFE_SPEED: Final[float] = 175.0
DROP_LAUNCH_SPIN: Final[float] = 4.4  # rad/s, nose down (about half a turn before the roof lands)
DROP_TUMBLE_SECONDS: Final[float] = 1.0
# Assist (after two tumbles in one course, or always on gentle courses):
# the buggy rights itself in the air and slows itself at drop signs.
ASSIST_AFTER_TUMBLES: Final[int] = 2
ASSIST_DROP_SPEED: Final[float] = 140.0

MUSHROOM_BOUNCE_VY: Final[float] = -560.0
MUSHROOM_BOUNCE_VX: Final[float] = 60.0

STAR_PICKUP_RADIUS: Final[float] = 58.0
TERRAIN_SAMPLE: Final[int] = 4  # px between precomputed height samples
BASE_Y: Final[float] = 450.0  # flat ground level (world y, +y down)
START_FLAT: Final[float] = 520.0
FINISH_RUNOUT: Final[float] = 1200.0  # flat picnic meadow after the finish arch
START_X: Final[float] = 200.0
STARS_PER_COURSE: Final[int] = 3
COURSES_PER_SET: Final[int] = 5

MIN_RUNG: Final[int] = 1
MAX_RUNG: Final[int] = 3
RUNG_SCALE: Final[dict[int, float]] = {1: 0.8, 2: 1.0, 3: 1.18}
# Between sets: a smooth set promotes, a set with many tumbles eases off.
PROMOTE_MAX_TUMBLES: Final[int] = 2
DEMOTE_MIN_TUMBLES: Final[int] = 8
HISTORY_LIMIT: Final[int] = 6


class FeatureKind(StrEnum):
    FLAT = "flat"
    HILL = "hill"
    VALLEY = "valley"
    BUMPS = "bumps"
    JUMP = "jump"
    BRIDGE = "bridge"
    MUD = "mud"
    DROP = "drop"
    MUSHROOM = "mushroom"


class Surface(StrEnum):
    GRASS = "grass"
    BRIDGE = "bridge"
    MUD = "mud"
    MUSHROOM = "mushroom"


@dataclass(frozen=True, slots=True)
class Feature:
    """One stretch of a course, laid after the previous one.

    ``height`` is in px at rung 2 (scaled by the rung); its meaning depends on
    the kind (hill/jump/drop rise, valley/mud/mushroom dip, bridge pond depth).
    ``checkpoint`` plants a flag at the start of this feature.
    """

    kind: FeatureKind
    width: float
    height: float = 0.0
    count: int = 1
    checkpoint: bool = False


@dataclass(frozen=True, slots=True)
class StarSpot:
    """A star floating ``lift`` px above the ground at ``t`` of feature ``feature``."""

    feature: int
    t: float
    lift: float = 70.0


@dataclass(frozen=True, slots=True)
class CourseSpec:
    course_id: str
    biome: str
    friend: str
    features: tuple[Feature, ...]
    stars: tuple[StarSpot, ...]
    auto_upright: bool = False


F = Feature
K = FeatureKind

COURSES: Final[tuple[CourseSpec, ...]] = (
    CourseSpec(
        "meadow",
        "meadow_day",
        "leo",
        (
            F(K.HILL, 560, 45),
            F(K.FLAT, 160),
            F(K.HILL, 640, 65),
            F(K.VALLEY, 520, 40),
            F(K.HILL, 600, 60),
            F(K.FLAT, 200),
            F(K.BUMPS, 480, 14, count=3, checkpoint=True),
            F(K.HILL, 700, 80),
            F(K.FLAT, 160),
            F(K.VALLEY, 560, 45),
            F(K.HILL, 640, 70),
            F(K.FLAT, 200),
            F(K.HILL, 560, 55),
        ),
        (StarSpot(1, 0.5, 60), StarSpot(6, 0.5, 70), StarSpot(10, 0.5, 70)),
        auto_upright=True,
    ),
    CourseSpec(
        "pond",
        "woodland_pond",
        "lilli",
        (
            F(K.HILL, 620, 70),
            F(K.FLAT, 140),
            F(K.JUMP, 440, 46),
            F(K.FLAT, 300),
            F(K.HILL, 640, 80),
            F(K.FLAT, 120),
            F(K.BRIDGE, 560, 70, checkpoint=True),
            F(K.FLAT, 160),
            F(K.HILL, 720, 95),
            F(K.BUMPS, 520, 18, count=3, checkpoint=True),
            F(K.JUMP, 460, 52),
            F(K.FLAT, 260),
            F(K.HILL, 640, 80),
        ),
        (StarSpot(2, 0.92, 120), StarSpot(6, 0.5, 70), StarSpot(10, 0.92, 120)),
        auto_upright=True,
    ),
    CourseSpec(
        "autumn",
        "woodland_autumn",
        "momo",
        (
            F(K.HILL, 640, 80),
            F(K.FLAT, 120),
            F(K.MUD, 520, 22),
            F(K.HILL, 700, 100, checkpoint=True),
            F(K.JUMP, 460, 55),
            F(K.FLAT, 300),
            F(K.BUMPS, 520, 20, count=3),
            F(K.MUD, 600, 26, checkpoint=True),
            F(K.HILL, 720, 105),
            F(K.FLAT, 160),
            F(K.JUMP, 480, 60),
            F(K.FLAT, 260),
            F(K.HILL, 620, 85),
        ),
        (StarSpot(2, 0.5, 60), StarSpot(4, 0.95, 130), StarSpot(10, 0.95, 130)),
    ),
    CourseSpec(
        "snow",
        "woodland_snow",
        "dani",
        (
            F(K.HILL, 640, 80),
            F(K.FLAT, 200),
            F(K.DROP, 900, 120, checkpoint=True),
            F(K.FLAT, 200),
            F(K.BUMPS, 520, 22, count=3),
            F(K.HILL, 700, 100, checkpoint=True),
            F(K.FLAT, 160),
            F(K.DROP, 900, 130, checkpoint=True),
            F(K.FLAT, 200),
            F(K.HILL, 640, 85),
            F(K.FLAT, 160),
            F(K.HILL, 600, 70),
        ),
        (StarSpot(2, 0.80, 60), StarSpot(4, 0.5, 70), StarSpot(7, 0.80, 60)),
    ),
    CourseSpec(
        "sky",
        "sky_clouds",
        "flash",
        (
            F(K.HILL, 660, 95),
            F(K.MUSHROOM, 440, 60),
            F(K.HILL, 760, 110, checkpoint=True),
            F(K.FLAT, 160),
            F(K.DROP, 900, 130, checkpoint=True),
            F(K.FLAT, 160),
            F(K.MUSHROOM, 440, 60, checkpoint=True),
            F(K.JUMP, 480, 60),
            F(K.FLAT, 200),
            F(K.BUMPS, 520, 22, count=3),
            F(K.DROP, 900, 120, checkpoint=True),
            F(K.FLAT, 200),
            F(K.HILL, 760, 110),
        ),
        (StarSpot(1, 0.5, 230), StarSpot(6, 0.5, 230), StarSpot(10, 0.80, 60)),
    ),
)

del F, K

__all__ = [
    "AIR_DRAG",
    "AIR_TILT_TORQUE",
    "ANGULAR_DAMPING",
    "ASSIST_AFTER_TUMBLES",
    "ASSIST_DROP_SPEED",
    "AUTO_UPRIGHT_GAIN",
    "BASE_Y",
    "BRAKE_DECEL",
    "CHASSIS_HEIGHT",
    "CHASSIS_WIDTH",
    "COURSES",
    "COURSES_PER_SET",
    "CourseSpec",
    "DEMOTE_MIN_TUMBLES",
    "DRIVE_ACCEL",
    "DROP_LAUNCH_SPIN",
    "DROP_SAFE_SPEED",
    "DROP_TUMBLE_SECONDS",
    "FINISH_RUNOUT",
    "FIXED_DT",
    "FLIP_DURATION_THRESHOLD",
    "FLIP_TOLERANCE_ANGLE",
    "Feature",
    "FeatureKind",
    "GRAVITY",
    "HISTORY_LIMIT",
    "MAX_FORWARD_SPEED",
    "MAX_REVERSE_SPEED",
    "MAX_RUNG",
    "MAX_STEPS_PER_FRAME",
    "MIN_RUNG",
    "MUD_DRAG",
    "MUD_TRACTION",
    "MUSHROOM_BOUNCE_VX",
    "MUSHROOM_BOUNCE_VY",
    "PERFECT_LANDING_ANGLE_TOLERANCE",
    "PERFECT_LANDING_BOOST",
    "PERFECT_LANDING_MIN_AIR",
    "PROMOTE_MAX_TUMBLES",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "ROLLING_FRICTION",
    "RUNG_SCALE",
    "STARS_PER_COURSE",
    "START_FLAT",
    "START_X",
    "STAR_PICKUP_RADIUS",
    "SUSPENSION_DAMPING",
    "SUSPENSION_MAX_LENGTH",
    "SUSPENSION_MIN_LENGTH",
    "SUSPENSION_REST_LENGTH",
    "SUSPENSION_STIFFNESS",
    "StarSpot",
    "Surface",
    "TERRAIN_SAMPLE",
    "WHEELBASE",
    "WHEEL_RADIUS",
]
