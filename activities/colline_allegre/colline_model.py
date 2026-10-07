"""2D Physics simulation and game state for Colline Allegre.

Pure logic module with zero pygame drawing dependencies.
Fully deterministic and unit-testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Final

if __package__:
    from .colline_content import (
        AIR_DRAG,
        AIR_TILT_TORQUE,
        ANGULAR_DAMPING,
        BOUNCE_ANIMATION_DURATION,
        BOUNCE_IMPULSE_X,
        BOUNCE_IMPULSE_Y,
        BRAKE_DECEL,
        CHASSIS_HEIGHT,
        CHASSIS_MASS,
        CHASSIS_WIDTH,
        DISTANCE_MILESTONES,
        DRIVE_ACCEL,
        DifficultyProfile,
        FLIP_DURATION_THRESHOLD,
        FLIP_TOLERANCE_ANGLE,
        GRAVITY,
        MAX_FORWARD_SPEED,
        MAX_REVERSE_SPEED,
        PERFECT_LANDING_ANGLE_TOLERANCE,
        PERFECT_LANDING_BOOST,
        PIXELS_PER_METER,
        PROFILES,
        ROLLING_FRICTION,
        SUSPENSION_DAMPING,
        SUSPENSION_MAX_LENGTH,
        SUSPENSION_MIN_LENGTH,
        SUSPENSION_REST_LENGTH,
        SUSPENSION_STIFFNESS,
        WHEEL_RADIUS,
        WHEELBASE,
    )

    TERRAIN_BASE_Y:
else:
    from colline_content import (
        AIR_DRAG,
        AIR_TILT_TORQUE,
        ANGULAR_DAMPING,
        BOUNCE_ANIMATION_DURATION,
        BOUNCE_IMPULSE_X,
        BOUNCE_IMPULSE_Y,
        BRAKE_DECEL,
        CHASSIS_HEIGHT,
        CHASSIS_MASS,
        CHASSIS_WIDTH,
        DISTANCE_MILESTONES,
        DRIVE_ACCEL,
        DifficultyProfile,
        FLIP_DURATION_THRESHOLD,
        FLIP_TOLERANCE_ANGLE,
        GRAVITY,
        MAX_FORWARD_SPEED,
        MAX_REVERSE_SPEED,
        PERFECT_LANDING_ANGLE_TOLERANCE,
        PERFECT_LANDING_BOOST,
        PIXELS_PER_METER,
        PROFILES,
        ROLLING_FRICTION,
        SUSPENSION_DAMPING,
        SUSPENSION_MAX_LENGTH,
        SUSPENSION_MIN_LENGTH,
        SUSPENSION_REST_LENGTH,
        SUSPENSION_STIFFNESS,
        WHEEL_RADIUS,
        WHEELBASE,
    )

    TERRAIN_BASE_Y:
 Final[float] = 430.0


@dataclass
class Wheel:
    rel_x: float  # offset from chassis center along heading
    x: float = 0.0
    y: float = 0.0
    hub_x: float = 0.0
    hub_y: float = 0.0
    suspension_len: float = SUSPENSION_REST_LENGTH
    in_contact: bool = False
    compression: float = 0.0
    surface_kind: str = "grass"


@dataclass
class Vehicle:
    x: float = 120.0
    y: float = TERRAIN_BASE_Y - 80.0
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0  # radians (0 = horizontal facing right, positive = nose down)
    angular_velocity: float = 0.0
    rear_wheel: Wheel = field(default_factory=lambda: Wheel(rel_x=-WHEELBASE / 2.0))
    front_wheel: Wheel = field(default_factory=lambda: Wheel(rel_x=WHEELBASE / 2.0))
    is_airborne: bool = False
    air_time: float = 0.0
    flip_timer: float = 0.0
    is_flipped: bool = False
    bounce_active: bool = False
    bounce_timer: float = 0.0
    perfect_landing_active: bool = False
    perfect_landing_timer: float = 0.0


@dataclass
class Collectible:
    x: float
    y: float
    kind: str  # "star", "gear", "balloon"
    value: int = 1
    radius: float = 24.0
    collected: bool = False


class Terrain:
    """Procedural rolling hills terrain with bridges, mud and bouncy mushrooms."""

    def __init__(self, profile: DifficultyProfile) -> None:
        self.profile = profile

    def get_height(self, x: float) -> float:
        # Safe spawn zone
        if x < 180.0:
            return TERRAIN_BASE_Y
        blend = min(1.0, (x - 180.0) / 100.0)

        wl = self.profile.hill_wavelength
        amp = self.profile.hill_amplitude

        # Primary rolling wave
        h = -math.sin((x - 180.0) / wl * 2.0 * math.pi) * amp
        # Secondary harmonics
        h += -math.sin((x - 180.0) / (wl * 0.43) * 2.0 * math.pi) * (amp * 0.35)

        if self.profile.roughness > 0.0:
            h += -math.cos((x - 180.0) / (wl * 0.21) * 2.0 * math.pi) * (amp * self.profile.roughness)

        # Wooden bridge segment flattening
        if self.profile.has_bridges:
            if 800.0 <= x <= 1050.0:
                bridge_y = -amp * 0.3
                bridge_blend = math.sin((x - 800.0) / 250.0 * math.pi)
                h = h * (1.0 - bridge_blend) + bridge_y * bridge_blend
            elif 2100.0 <= x <= 2400.0:
                bridge_y = -amp * 0.4
                bridge_blend = math.sin((x - 2100.0) / 300.0 * math.pi)
                h = h * (1.0 - bridge_blend) + bridge_y * bridge_blend

        return TERRAIN_BASE_Y + h * blend

    def get_slope(self, x: float) -> float:
        dx = 2.0
        return (self.get_height(x + dx) - self.get_height(x - dx)) / (2.0 * dx)

    def get_normal(self, x: float) -> tuple[float, float]:
        slope = self.get_slope(x)
        # In screen coordinates where +y is down:
        # Tangent vector is (1, slope)
        # Normal pointing upwards is (-slope, 1) or (slope, -1) normalized.
        # Upward normal in +y-down coords has negative y:
        length = math.hypot(1.0, slope)
        nx = -slope / length
        ny = -1.0 / length
        return nx, ny

    def get_surface_kind(self, x: float) -> str:
        if self.profile.has_bridges:
            if (800.0 <= x <= 1050.0) or (2100.0 <= x <= 2400.0):
                return "bridge"
        if self.profile.has_mud:
            if (1400.0 <= x <= 1650.0) or (2700.0 <= x <= 2950.0):
                return "mud"
        if self.profile.has_mushrooms:
            # Mushroom pads at valley bottoms
            if abs(x - 620.0) < 30.0 or abs(x - 1850.0) < 30.0:
                return "mushroom"
        return "grass"


class CollineWorld:
    """Deterministic 2D vehicle physics world."""

    def __init__(self, difficulty: int = 2) -> None:
        self.difficulty = max(1, min(5, difficulty))
        self.profile = PROFILES.get(self.difficulty, PROFILES[2])
        self.terrain = Terrain(self.profile)
        self.vehicle = Vehicle()
        self.collectibles: list[Collectible] = []
        self.events: list[str] = []
        self.stars_collected: int = 0
        self.score: int = 0
        self.distance_traveled: float = 0.0
        self.highest_milestone: int = 0
        self.is_completed: bool = False
        self._init_collectibles()

    def _init_collectibles(self) -> None:
        # Spawn collectibles along the hill path (stars on crests, gears in bridges, balloons over jumps)
        for d in range(250, int(self.profile.target_distance * PIXELS_PER_METER), 160):
            x = float(d)
            ground_y = self.terrain.get_height(x)
            slope = self.terrain.get_slope(x)
            # On hill crests or jumps
            if slope > 0.2:
                # Up in the air
                self.collectibles.append(Collectible(x=x, y=ground_y - 85.0, kind="balloon", value=3))
            elif (800 <= x <= 1050) or (2100 <= x <= 2400):
                self.collectibles.append(Collectible(x=x, y=ground_y - 45.0, kind="gear", value=2))
            else:
                self.collectibles.append(Collectible(x=x, y=ground_y - 50.0, kind="star", value=1))

    def reset(self, difficulty: int | None = None) -> None:
        if difficulty is not None:
            self.difficulty = max(1, min(5, difficulty))
            self.profile = PROFILES.get(self.difficulty, PROFILES[2])
            self.terrain = Terrain(self.profile)
        self.vehicle = Vehicle()
        self.collectibles.clear()
        self.events.clear()
        self.stars_collected = 0
        self.score = 0
        self.distance_traveled = 0.0
        self.highest_milestone = 0
        self.is_completed = False
        self._init_collectibles()

    def step(self, dt: float, throttle: float = 0.0, brake: float = 0.0, tilt: float = 0.0) -> list[str]:
        """Advance physics by dt using multi-step integration for suspension stability."""
        new_events: list[str] = []
        if dt <= 0.0:
            return new_events

        # Clamp inputs
        throttle = max(0.0, min(1.0, throttle))
        brake = max(0.0, min(1.0, brake))
        tilt = max(-1.0, min(1.0, tilt))

        # Sub-step integration (4 sub-steps per frame)
        sub_steps = 4
        sub_dt = min(0.05, dt) / sub_steps

        for _ in range(sub_steps):
            self._physics_substep(sub_dt, throttle, brake, tilt, new_events)

        # Update timers
        veh = self.vehicle
        if veh.bounce_active:
            veh.bounce_timer += dt
            if veh.bounce_timer >= BOUNCE_ANIMATION_DURATION:
                veh.bounce_active = False
                veh.bounce_timer = 0.0

        if veh.perfect_landing_active:
            veh.perfect_landing_timer += dt
            if veh.perfect_landing_timer >= 1.2:
                veh.perfect_landing_active = False
                veh.perfect_landing_timer = 0.0

        # Check collectibles
        for c in self.collectibles:
            if not c.collected:
                dx = veh.x - c.x
                dy = veh.y - c.y
                if (dx * dx + dy * dy) < (c.radius + 36.0) ** 2:
                    c.collected = True
                    self.stars_collected += 1
                    self.score += c.value
                    new_events.append("colline.star_collected")

        # Distance & Milestones
        meters = max(0.0, veh.x / PIXELS_PER_METER)
        if meters > self.distance_traveled:
            self.distance_traveled = meters

        for m in DISTANCE_MILESTONES:
            if self.distance_traveled >= m > self.highest_milestone:
                self.highest_milestone = m
                new_events.append("colline.milestone_distance")

        # Course completion check
        if self.distance_traveled >= self.profile.target_distance and not self.is_completed:
            self.is_completed = True
            new_events.append("colline.course_completed")

        self.events.extend(new_events)
        return new_events

    def _physics_substep(
        self, sub_dt: float, throttle: float, brake: float, tilt: float, new_events: list[str]
    ) -> None:
        veh = self.vehicle
        cos_a = math.cos(veh.angle)
        sin_a = math.sin(veh.angle)

        # Heading vector (forward along chassis)
        hx, hy = cos_a, sin_a
        # Perpendicular normal vector downwards relative to chassis
        nx, ny = -sin_a, cos_a

        # Gravity
        veh.vy += GRAVITY * sub_dt

        # Calculate wheel positions & suspension forces
        wheels = [veh.rear_wheel, veh.front_wheel]
        total_spring_force_x = 0.0
        total_spring_force_y = 0.0
        chassis_torque = 0.0
        contacts = 0

        for w in wheels:
            # Mount point on chassis
            mx = veh.x + w.rel_x * hx
            my = veh.y + w.rel_x * hy

            # Uncompressed hub position
            hub_x = mx + nx * SUSPENSION_REST_LENGTH
            hub_y = my + ny * SUSPENSION_REST_LENGTH

            # Wheel bottom ground query
            ground_y = self.terrain.get_height(hub_x)
            surface_kind = self.terrain.get_surface_kind(hub_x)
            w.surface_kind = surface_kind

            wheel_bottom_y = hub_y + WHEEL_RADIUS
            penetration = wheel_bottom_y - ground_y

            if penetration > 0.0:
                # Wheel is touching ground
                w.in_contact = True
                contacts += 1
                comp = min(SUSPENSION_MAX_LENGTH, max(0.0, penetration))
                w.compression = comp
                w.suspension_len = max(SUSPENSION_MIN_LENGTH, SUSPENSION_REST_LENGTH - comp)

                # Wheel hub sits above ground by WHEEL_RADIUS
                w.hub_x = hub_x
                w.hub_y = ground_y - WHEEL_RADIUS
                w.x = w.hub_x
                w.y = ground_y

                # Terrain normal at contact point
                tnx, tny = self.terrain.get_normal(w.hub_x)

                # Normal spring force
                # Project vehicle velocity onto terrain normal
                rel_v = veh.vx * tnx + veh.vy * tny
                spring_f = comp * SUSPENSION_STIFFNESS - rel_v * SUSPENSION_DAMPING
                if spring_f > 0.0:
                    total_spring_force_x += tnx * spring_f
                    total_spring_force_y += tny * spring_f

                    # Torque on chassis: arm is w.rel_x
                    # If rear wheel pushes up, it tilts nose down (+torque in clockwise sys)
                    # If front wheel pushes up, it tilts nose up (-torque)
                    chassis_torque += (w.rel_x / (WHEELBASE / 2.0)) * (-spring_f * 0.015)

                # Bouncy mushroom bounce
                if surface_kind == "mushroom":
                    veh.vy = min(veh.vy, -480.0)
                    veh.vx += 120.0
                    new_events.append("colline.mushroom_bounce")

                # Traction & Braking
                surface_friction = 0.55 if surface_kind == "mud" else 1.0
                slope = self.terrain.get_slope(w.hub_x)
                tx, ty = 1.0 / math.hypot(1.0, slope), slope / math.hypot(1.0, slope)

                if throttle > 0.0:
                    accel = DRIVE_ACCEL * throttle * surface_friction
                    veh.vx += tx * accel * sub_dt
                    veh.vy += ty * accel * sub_dt
                elif brake > 0.0:
                    decel = BRAKE_DECEL * brake
                    speed = math.hypot(veh.vx, veh.vy)
                    if speed > 5.0:
                        veh.vx -= (veh.vx / speed) * decel * sub_dt
                        veh.vy -= (veh.vy / speed) * decel * sub_dt
                    else:
                        veh.vx += tx * MAX_REVERSE_SPEED * 0.4 * sub_dt
            else:
                # Airborne wheel
                w.in_contact = False
                w.compression = 0.0
                w.suspension_len = SUSPENSION_REST_LENGTH
                w.hub_x = hub_x
                w.hub_y = hub_y
                w.x = hub_x
                w.y = hub_y + WHEEL_RADIUS

        # Apply spring forces to vehicle
        veh.vx += total_spring_force_x * sub_dt
        veh.vy += total_spring_force_y * sub_dt

        # Check airborne status
        was_airborne = veh.is_airborne
        veh.is_airborne = contacts == 0

        if veh.is_airborne:
            veh.air_time += sub_dt
            # Mid-air tilt control
            if tilt != 0.0:
                veh.angular_velocity += tilt * AIR_TILT_TORQUE * sub_dt
            # Auto-uprighting for D1
            if self.profile.auto_upright:
                target_ang = 0.0
                veh.angular_velocity += (target_ang - veh.angle) * 3.0 * sub_dt
            # Air drag
            veh.vx *= AIR_DRAG
        else:
            # Wheels on ground
            # Landing detection
            if was_airborne and veh.air_time > 0.35 and contacts == 2:
                # Check landing angle alignment with terrain slope
                terrain_angle = math.atan(self.terrain.get_slope(veh.x))
                angle_diff = abs(veh.angle - terrain_angle)
                if angle_diff <= PERFECT_LANDING_ANGLE_TOLERANCE:
                    # Perfect landing boost!
                    veh.vx += PERFECT_LANDING_BOOST
                    veh.perfect_landing_active = True
                    veh.perfect_landing_timer = 0.0
                    new_events.append("colline.perfect_landing")
            veh.air_time = 0.0
            veh.vx *= ROLLING_FRICTION

        # Apply torque & angular damping
        veh.angular_velocity += chassis_torque * sub_dt
        veh.angular_velocity *= max(0.0, 1.0 - ANGULAR_DAMPING * sub_dt)
        veh.angle += veh.angular_velocity * sub_dt

        # Clamp speed
        veh.vx = max(MAX_REVERSE_SPEED, min(MAX_FORWARD_SPEED, veh.vx))

        # Integrate linear position
        veh.x += veh.vx * sub_dt
        veh.y += veh.vy * sub_dt

        # Enforce ground floor for chassis (so it doesn't sink deep into terrain)
        ground_center_y = self.terrain.get_height(veh.x)
        min_y = ground_center_y - CHASSIS_HEIGHT / 2.0
        if veh.y > min_y + 12.0:
            veh.y = min_y + 12.0
            if veh.vy > 0:
                veh.vy = 0.0

        # Flip detection & Comical Boxing-Glove Spring Recovery
        # Angle normalized between -pi and pi
        norm_angle = (veh.angle + math.pi) % (2.0 * math.pi) - math.pi
        is_upside_down = abs(norm_angle) > FLIP_TOLERANCE_ANGLE

        # Also check if chassis roof hits ground
        roof_contact = veh.y >= ground_center_y - 20.0 and is_upside_down

        if is_upside_down and (contacts == 0 or roof_contact):
            veh.flip_timer += sub_dt
            if veh.flip_timer >= FLIP_DURATION_THRESHOLD:
                # TRIGGER BOING! COMICAL RECOVERY!
                veh.is_flipped = False
                veh.flip_timer = 0.0
                veh.bounce_active = True
                veh.bounce_timer = 0.0

                # Upright vehicle and give bouncy jump!
                veh.angle = math.atan(self.terrain.get_slope(veh.x))
                veh.angular_velocity = 0.0
                veh.vy = BOUNCE_IMPULSE_Y
                veh.vx = max(veh.vx + BOUNCE_IMPULSE_X, 160.0)
                veh.y = ground_center_y - 70.0
                new_events.append("colline.comical_flip")
        else:
            veh.flip_timer = max(0.0, veh.flip_timer - sub_dt * 1.5)
