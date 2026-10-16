"""Course and look catalogue for Il Volo del Draghetto.

Four finite sky courses form one gentle ladder of the same steering loop:
each adds a little speed, altitude swing between the rainbow rings and a
few more bouncy clouds. Finishing a course unlocks the next course and one
"look" (a hat-like prop from the shared library) for the dragon. Data only:
the course builder (``dragon_model``) and the renderer read these values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class SkyDecor(StrEnum):
    """Background motif that makes each course look different."""

    SUN = "sun"
    ISLANDS = "islands"
    RAINBOWS = "rainbows"
    SUNSET = "sunset"


@dataclass(frozen=True, slots=True)
class CourseSpec:
    """Tuning for one finite course (logical 1024x600 pixels, seconds)."""

    course_id: str
    rings: int
    speed: float
    segment: float
    ring_half_open: float
    altitude_swing: float
    clouds_per_segment: tuple[int, int]
    gems: bool
    decor: SkyDecor
    #: RGB tint mixed into the sky once when the backdrop is composed.
    tint: tuple[int, int, int] | None
    tint_amount: float
    look_reward: str

    def __post_init__(self) -> None:
        if not 2 <= self.rings <= 8:
            raise ValueError("a course has 2..8 rings")
        if self.speed <= 0 or self.segment < 900:
            raise ValueError("course speed/segment out of range")
        lo, hi = self.clouds_per_segment
        if not 0 <= lo <= hi <= 3:
            raise ValueError("clouds_per_segment must be within 0..3")


@dataclass(frozen=True, slots=True)
class LookSpec:
    """One cosmetic look: a shared prop worn on the dragon's head."""

    look_id: str
    visual_id: str | None
    #: Prop size as a share of the dragon frame height.
    scale: float = 0.36
    #: Anchor (share of frame width/height) for the prop's bottom centre.
    anchor: tuple[float, float] = (0.64, 0.24)
    tilt: float = -10.0


COURSES: Final[tuple[CourseSpec, ...]] = (
    CourseSpec(
        course_id="morning",
        rings=4,
        speed=160.0,
        segment=1800.0,
        ring_half_open=84.0,
        altitude_swing=70.0,
        clouds_per_segment=(0, 1),
        gems=False,
        decor=SkyDecor.SUN,
        tint=None,
        tint_amount=0.0,
        look_reward="crown",
    ),
    CourseSpec(
        course_id="islands",
        rings=5,
        speed=170.0,
        segment=1800.0,
        ring_half_open=76.0,
        altitude_swing=110.0,
        clouds_per_segment=(1, 1),
        gems=True,
        decor=SkyDecor.ISLANDS,
        tint=(217, 242, 208),  # mint
        tint_amount=0.18,
        look_reward="top_hat",
    ),
    CourseSpec(
        course_id="rainbow",
        rings=5,
        speed=180.0,
        segment=1900.0,
        ring_half_open=70.0,
        altitude_swing=140.0,
        clouds_per_segment=(1, 2),
        gems=True,
        decor=SkyDecor.RAINBOWS,
        tint=(232, 221, 247),  # lavender
        tint_amount=0.32,
        look_reward="flower",
    ),
    CourseSpec(
        course_id="sunset",
        rings=6,
        speed=190.0,
        segment=1800.0,
        ring_half_open=66.0,
        altitude_swing=160.0,
        clouds_per_segment=(1, 2),
        gems=True,
        decor=SkyDecor.SUNSET,
        tint=(244, 150, 120),  # coral-peach evening light
        tint_amount=0.38,
        look_reward="star",
    ),
)

LOOKS: Final[tuple[LookSpec, ...]] = (
    LookSpec("none", None),
    LookSpec("crown", "prop.vocab.crown", scale=0.34),
    LookSpec("top_hat", "prop.vocab.hat", scale=0.36),
    LookSpec("flower", "prop.nature.flower", scale=0.30, anchor=(0.66, 0.26), tilt=-14.0),
    LookSpec("star", "prop.shape.star", scale=0.28, anchor=(0.66, 0.24), tilt=-8.0),
)

LOOK_IDS: Final[tuple[str, ...]] = tuple(look.look_id for look in LOOKS)
COURSE_IDS: Final[tuple[str, ...]] = tuple(course.course_id for course in COURSES)


def course_by_id(course_id: str) -> CourseSpec:
    for course in COURSES:
        if course.course_id == course_id:
            return course
    raise KeyError(course_id)


def look_by_id(look_id: str) -> LookSpec:
    for look in LOOKS:
        if look.look_id == look_id:
            return look
    return LOOKS[0]


__all__ = [
    "COURSES",
    "COURSE_IDS",
    "CourseSpec",
    "LOOKS",
    "LOOK_IDS",
    "LookSpec",
    "SkyDecor",
    "course_by_id",
    "look_by_id",
]
