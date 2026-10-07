"""Constants, configuration and physical parameters for Colline Allegre."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

# Top-left system chrome clearance boundary (ADR 0019)
SYSTEM_CHROME_SAFE_X: Final[int] = 100
SYSTEM_CHROME_SAFE_Y: Final[int] = 100

# Vehicle geometry and physics (Acer floor calibrated)
WHEELBASE: Final[float] = 84.0
WHEEL_RADIUS: Final[float] = 22.0
CHASSIS_WIDTH: Final[float] = 110.0
CHASSIS_HEIGHT: Final[float] = 52.0
CHASSIS_MASS: Final[float] = 1.0

# Suspension spring constants
SUSPENSION_REST_LENGTH: Final[float] = 30.0
SUSPENSION_MIN_LENGTH: Final[float] = 10.0
SUSPENSION_MAX_LENGTH: Final[float] = 48.0
SUSPENSION_STIFFNESS: Final[float] = 260.0
SUSPENSION_DAMPING: Final[float] = 16.0

# Physical dynamics
GRAVITY: Final[float] = 820.0
DRIVE_ACCEL: Final[float] = 460.0
BRAKE_DECEL: Final[float] = 600.0
ROLLING_FRICTION: Final[float] = 0.985
AIR_DRAG: Final[float] = 0.994
MAX_FORWARD_SPEED: Final[float] = 540.0
MAX_REVERSE_SPEED: Final[float] = -150.0

# Mid-air orientation and tilt controls
AIR_TILT_TORQUE: Final[float] = 5.2
ANGULAR_DAMPING: Final[float] = 3.6
PERFECT_LANDING_ANGLE_TOLERANCE: Final[float] = 0.28  # ~16 degrees
PERFECT_LANDING_BOOST: Final[float] = 110.0

# Comical failure recovery
FLIP_TOLERANCE_ANGLE: Final[float] = 2.2  # ~126 degrees tilt
FLIP_DURATION_THRESHOLD: Final[float] = 0.55  # seconds upside down before boxing-glove spring
BOUNCE_IMPULSE_Y: Final[float] = -520.0
BOUNCE_IMPULSE_X: Final[float] = 180.0
BOUNCE_ANIMATION_DURATION: Final[float] = 0.85

# Scale: 10 pixels = 1 meter
PIXELS_PER_METER: Final[float] = 10.0

# Milestones in meters
DISTANCE_MILESTONES: Final[tuple[int, ...]] = (100, 250, 500, 750, 1000)


@dataclass(frozen=True)
class DifficultyProfile:
    level: int
    hill_amplitude: float
    hill_wavelength: float
    roughness: float
    auto_upright: bool
    has_bridges: bool
    has_mud: bool
    has_mushrooms: bool
    target_distance: float


PROFILES: Final[dict[int, DifficultyProfile]] = {
    1: DifficultyProfile(
        level=1,
        hill_amplitude=35.0,
        hill_wavelength=500.0,
        roughness=0.0,
        auto_upright=True,
        has_bridges=False,
        has_mud=False,
        has_mushrooms=False,
        target_distance=300.0,
    ),
    2: DifficultyProfile(
        level=2,
        hill_amplitude=55.0,
        hill_wavelength=460.0,
        roughness=0.08,
        auto_upright=False,
        has_bridges=True,
        has_mud=False,
        has_mushrooms=False,
        target_distance=500.0,
    ),
    3: DifficultyProfile(
        level=3,
        hill_amplitude=75.0,
        hill_wavelength=420.0,
        roughness=0.15,
        auto_upright=False,
        has_bridges=True,
        has_mud=False,
        has_mushrooms=True,
        target_distance=750.0,
    ),
    4: DifficultyProfile(
        level=4,
        hill_amplitude=95.0,
        hill_wavelength=380.0,
        roughness=0.22,
        auto_upright=False,
        has_bridges=True,
        has_mud=True,
        has_mushrooms=True,
        target_distance=1000.0,
    ),
    5: DifficultyProfile(
        level=5,
        hill_amplitude=115.0,
        hill_wavelength=340.0,
        roughness=0.30,
        auto_upright=False,
        has_bridges=True,
        has_mud=True,
        has_mushrooms=True,
        target_distance=1250.0,
    ),
}
