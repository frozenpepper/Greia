"""Terrain, fixed-step buggy physics and the course ladder of Colline Allegre.

Pure logic: no drawing, sound or storage. Deterministic for a given course,
rung and input sequence.

* ``CourseLayout`` turns a ``CourseSpec`` (+ rung) into a finite course:
  precomputed height samples, surface spans, checkpoints, stars, drop edges,
  mushroom pads and the finish line.
* ``CourseRun`` is one drive along one course. ``step(controls)`` advances the
  physics by exactly ``FIXED_DT`` and returns what happened (a star, a flag,
  a perfect landing, a tumble, the finish ...). A tumble never ends the game:
  the app shows it, then calls ``respawn()`` to put the buggy back upright at
  the last checkpoint flag.
* ``CourseSet`` plays the five courses in order and records stars and
  tumbles; ``adapt_rung`` picks the next set's rung.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Sequence

if __package__:
    from .colline_content import (
        AIR_DRAG,
        AIR_TILT_TORQUE,
        ANGULAR_DAMPING,
        ASSIST_AFTER_TUMBLES,
        ASSIST_DROP_SPEED,
        AUTO_UPRIGHT_GAIN,
        BASE_Y,
        BRAKE_DECEL,
        CHASSIS_HEIGHT,
        COURSES,
        COURSES_PER_SET,
        DEMOTE_MIN_TUMBLES,
        DRIVE_ACCEL,
        DROP_LAUNCH_SPIN,
        DROP_SAFE_SPEED,
        DROP_TUMBLE_SECONDS,
        FINISH_RUNOUT,
        FIXED_DT,
        FLIP_DURATION_THRESHOLD,
        FLIP_TOLERANCE_ANGLE,
        GRAVITY,
        HISTORY_LIMIT,
        MAX_FORWARD_SPEED,
        MAX_REVERSE_SPEED,
        MAX_RUNG,
        MIN_RUNG,
        MUD_DRAG,
        MUD_TRACTION,
        MUSHROOM_BOUNCE_VX,
        MUSHROOM_BOUNCE_VY,
        PERFECT_LANDING_ANGLE_TOLERANCE,
        PERFECT_LANDING_BOOST,
        PERFECT_LANDING_MIN_AIR,
        PROMOTE_MAX_TUMBLES,
        ROLLING_FRICTION,
        RUNG_SCALE,
        STAR_PICKUP_RADIUS,
        START_FLAT,
        START_X,
        SUSPENSION_DAMPING,
        SUSPENSION_MAX_LENGTH,
        SUSPENSION_MIN_LENGTH,
        SUSPENSION_REST_LENGTH,
        SUSPENSION_STIFFNESS,
        TERRAIN_SAMPLE,
        WHEEL_RADIUS,
        WHEELBASE,
        CourseSpec,
        Feature,
        FeatureKind,
        Surface,
    )
else:
    from colline_content import (
        AIR_DRAG,
        AIR_TILT_TORQUE,
        ANGULAR_DAMPING,
        ASSIST_AFTER_TUMBLES,
        ASSIST_DROP_SPEED,
        AUTO_UPRIGHT_GAIN,
        BASE_Y,
        BRAKE_DECEL,
        CHASSIS_HEIGHT,
        COURSES,
        COURSES_PER_SET,
        DEMOTE_MIN_TUMBLES,
        DRIVE_ACCEL,
        DROP_LAUNCH_SPIN,
        DROP_SAFE_SPEED,
        DROP_TUMBLE_SECONDS,
        FINISH_RUNOUT,
        FIXED_DT,
        FLIP_DURATION_THRESHOLD,
        FLIP_TOLERANCE_ANGLE,
        GRAVITY,
        HISTORY_LIMIT,
        MAX_FORWARD_SPEED,
        MAX_REVERSE_SPEED,
        MAX_RUNG,
        MIN_RUNG,
        MUD_DRAG,
        MUD_TRACTION,
        MUSHROOM_BOUNCE_VX,
        MUSHROOM_BOUNCE_VY,
        PERFECT_LANDING_ANGLE_TOLERANCE,
        PERFECT_LANDING_BOOST,
        PERFECT_LANDING_MIN_AIR,
        PROMOTE_MAX_TUMBLES,
        ROLLING_FRICTION,
        RUNG_SCALE,
        STAR_PICKUP_RADIUS,
        START_FLAT,
        START_X,
        SUSPENSION_DAMPING,
        SUSPENSION_MAX_LENGTH,
        SUSPENSION_MIN_LENGTH,
        SUSPENSION_REST_LENGTH,
        SUSPENSION_STIFFNESS,
        TERRAIN_SAMPLE,
        WHEEL_RADIUS,
        WHEELBASE,
        CourseSpec,
        Feature,
        FeatureKind,
        Surface,
    )

PADDING_AFTER_FEATURES = 160.0
MUSHROOM_PAD_HALF = 30.0
MUSHROOM_COOLDOWN = 0.4
STALL_SECONDS = 3.5
STALL_SPEED = 10.0
ASSIST_CLIMB = 1.35
FINISH_ROLL_BRAKE = 0.3


class RunEvent(StrEnum):
    """Facts one physics step can report to the app."""

    STAR = "star"
    CHECKPOINT = "checkpoint"
    PERFECT_LANDING = "perfect_landing"
    LANDING = "landing"
    BOUNCE = "bounce"
    DROP_SAFE = "drop_safe"
    DROP_TOO_FAST = "drop_too_fast"
    TUMBLE = "tumble"
    FINISH = "finish"


@dataclass(frozen=True, slots=True)
class Controls:
    """One step of driver input: GO / BRAKE pedals and the air tilt."""

    go: bool = False
    brake: bool = False
    tilt: float = 0.0


@dataclass(frozen=True, slots=True)
class Span:
    x0: float
    x1: float
    feature: Feature
    index: int

    def at(self, t: float) -> float:
        return self.x0 + (self.x1 - self.x0) * t


@dataclass(frozen=True, slots=True)
class DropEdge:
    sign_x: float
    edge_x: float
    bottom_x: float


@dataclass(slots=True)
class Star:
    x: float
    y: float
    collected: bool = False


def feature_offset(feature: Feature, t: float, scale: float) -> float:
    """Height offset (px, negative = up) of ``feature`` at ``t`` in [0, 1].

    Every shape starts and ends at 0, so features join without seams.
    """

    t = max(0.0, min(1.0, t))
    h = feature.height * scale
    kind = feature.kind
    if kind is FeatureKind.HILL:
        return -h * (1.0 - math.cos(2.0 * math.pi * t)) / 2.0
    if kind in (FeatureKind.VALLEY, FeatureKind.MUD, FeatureKind.MUSHROOM):
        return h * (1.0 - math.cos(2.0 * math.pi * t)) / 2.0
    if kind is FeatureKind.BUMPS:
        return -h * (1.0 - math.cos(2.0 * math.pi * max(1, feature.count) * t)) / 2.0
    if kind is FeatureKind.JUMP:
        if t < 0.78:
            return -h * math.sin(0.5 * math.pi * t / 0.78) ** 2
        return -h * math.cos(0.5 * math.pi * (t - 0.78) / 0.22) ** 2
    if kind is FeatureKind.DROP:
        if t < 0.3:
            return -h * math.sin(0.5 * math.pi * t / 0.3) ** 2
        if t < DROP_EDGE_T:
            return -h
        if t < DROP_BOTTOM_T:
            return -h * math.cos(0.5 * math.pi * (t - DROP_EDGE_T) / (DROP_BOTTOM_T - DROP_EDGE_T)) ** 2
        return 0.0
    return 0.0  # FLAT, BRIDGE (deck at ground level over a pond)


DROP_SIGN_T = 0.36
DROP_EDGE_T = 0.58
DROP_BOTTOM_T = 0.72


class CourseLayout:
    """A finite course: height samples, surfaces, flags, stars and the finish."""

    def __init__(self, spec: CourseSpec, rung: int = 2) -> None:
        self.spec = spec
        self.rung = max(MIN_RUNG, min(MAX_RUNG, int(rung)))
        self.scale = RUNG_SCALE[self.rung]
        spans: list[Span] = []
        x = START_FLAT
        for index, feature in enumerate(spec.features):
            spans.append(Span(x, x + feature.width, feature, index))
            x += feature.width
        self.spans: tuple[Span, ...] = tuple(spans)
        self.finish_x = x + PADDING_AFTER_FEATURES
        self.length = self.finish_x + FINISH_RUNOUT
        self.start_x = START_X

        count = int(self.length // TERRAIN_SAMPLE) + 2
        heights = [BASE_Y] * count
        for span in spans:
            first = int(span.x0 // TERRAIN_SAMPLE)
            last = min(count - 1, int(span.x1 // TERRAIN_SAMPLE) + 1)
            for i in range(first, last + 1):
                t = (i * TERRAIN_SAMPLE - span.x0) / (span.x1 - span.x0)
                if 0.0 <= t <= 1.0:
                    heights[i] = BASE_Y + feature_offset(span.feature, t, self.scale)
        self.heights: tuple[float, ...] = tuple(heights)
        self.min_y = min(heights)
        self.max_y = max(heights)

        surfaces: list[tuple[float, float, Surface]] = []
        drops: list[DropEdge] = []
        pads: list[float] = []
        checkpoints: list[float] = [self.start_x]
        for span in spans:
            kind = span.feature.kind
            if span.feature.checkpoint:
                # Just before the feature, where every feature meets level ground.
                checkpoints.append(span.x0 - 50.0)
            if kind is FeatureKind.BRIDGE:
                surfaces.append((span.x0, span.x1, Surface.BRIDGE))
            elif kind is FeatureKind.MUD:
                surfaces.append((span.at(0.1), span.at(0.9), Surface.MUD))
            elif kind is FeatureKind.MUSHROOM:
                center = span.at(0.5)
                pads.append(center)
                surfaces.append((center - MUSHROOM_PAD_HALF, center + MUSHROOM_PAD_HALF, Surface.MUSHROOM))
            elif kind is FeatureKind.DROP:
                drops.append(DropEdge(span.at(DROP_SIGN_T), span.at(DROP_EDGE_T), span.at(DROP_BOTTOM_T)))
        surfaces.sort(key=lambda item: item[0])
        self._surface_starts = [item[0] for item in surfaces]
        self._surfaces = surfaces
        self.drops: tuple[DropEdge, ...] = tuple(drops)
        self.pads: tuple[float, ...] = tuple(pads)
        self.checkpoints: tuple[float, ...] = tuple(sorted(checkpoints))
        self.star_spots: tuple[tuple[float, float], ...] = tuple(
            (spans[spot.feature].at(spot.t), self.height(spans[spot.feature].at(spot.t)) - spot.lift)
            for spot in spec.stars
            if 0 <= spot.feature < len(spans)
        )

    # -- queries ------------------------------------------------------------------

    def height(self, x: float) -> float:
        """Ground height (world y) at ``x``; flat outside the course."""

        if x <= 0.0:
            return self.heights[0]
        position = x / TERRAIN_SAMPLE
        index = int(position)
        if index >= len(self.heights) - 1:
            return self.heights[-1]
        frac = position - index
        a = self.heights[index]
        return a + (self.heights[index + 1] - a) * frac

    def slope(self, x: float) -> float:
        return (self.height(x + 3.0) - self.height(x - 3.0)) / 6.0

    def normal(self, x: float) -> tuple[float, float]:
        """Upward unit normal of the ground at ``x`` (screen coords, +y down)."""

        slope = self.slope(x)
        length = math.hypot(1.0, slope)
        return slope / length, -1.0 / length

    def surface(self, x: float) -> Surface:
        index = bisect_right(self._surface_starts, x) - 1
        if index >= 0:
            x0, x1, kind = self._surfaces[index]
            if x0 <= x <= x1:
                return kind
        return Surface.GRASS

    def surface_spans(self) -> tuple[tuple[float, float, Surface], ...]:
        return tuple(self._surfaces)

    def progress(self, x: float) -> float:
        span = max(1.0, self.finish_x - self.start_x)
        return max(0.0, min(1.0, (x - self.start_x) / span))

    def checkpoint_before(self, x: float) -> float:
        best = self.checkpoints[0]
        for flag in self.checkpoints:
            if flag <= x:
                best = flag
        return best


@dataclass
class Wheel:
    rel_x: float  # offset from the chassis centre along the heading
    hub_x: float = 0.0
    hub_y: float = 0.0
    in_contact: bool = False
    compression: float = 0.0
    surface: Surface = Surface.GRASS


@dataclass
class Vehicle:
    x: float = START_X
    y: float = BASE_Y - 70.0
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0  # radians, 0 = level facing right, + = nose down
    angular_velocity: float = 0.0
    rear_wheel: Wheel = field(default_factory=lambda: Wheel(rel_x=-WHEELBASE / 2.0))
    front_wheel: Wheel = field(default_factory=lambda: Wheel(rel_x=WHEELBASE / 2.0))
    airborne: bool = False
    air_time: float = 0.0
    flip_timer: float = 0.0
    wheel_spin: float = 0.0  # radians, for drawing

    @property
    def wheels(self) -> tuple[Wheel, Wheel]:
        return (self.rear_wheel, self.front_wheel)

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)


class CourseRun:
    """One drive along one course with fixed-step physics.

    Two kind helpers keep every child moving: ``air_assist`` rights the buggy
    in the air (gentle courses, the gentle rung, or after a tumble pile-up)
    and ``drop_assist`` slows the buggy by itself at a turtle sign once it has
    tumbled ``ASSIST_AFTER_TUMBLES`` times on this course. Either one also
    adds a little climbing help.
    """

    def __init__(self, layout: CourseLayout, *, assist: bool = False) -> None:
        self.layout = layout
        self.base_assist = assist or layout.spec.auto_upright
        self.vehicle = Vehicle()
        self.stars: list[Star] = [Star(x, y) for x, y in layout.star_spots]
        self.checkpoint_x = layout.start_x
        self.passed_flags: set[float] = {layout.start_x}
        self.tumbles = 0
        self.finished = False
        self.tumbling = False
        self.elapsed = 0.0
        self._drop_launch_timer = 0.0
        self._mushroom_cooldown = 0.0
        self._stall_timer = 0.0
        self.drop_hints: set[int] = set()  # drops where the buggy went over too fast
        self._settle()

    # -- state ----------------------------------------------------------------------

    @property
    def drop_assist(self) -> bool:
        return self.tumbles >= ASSIST_AFTER_TUMBLES

    @property
    def air_assist(self) -> bool:
        return self.base_assist or self.drop_assist

    @property
    def assist(self) -> bool:
        return self.air_assist or self.drop_assist

    @property
    def stars_collected(self) -> int:
        return sum(1 for star in self.stars if star.collected)

    @property
    def progress(self) -> float:
        return self.layout.progress(self.vehicle.x)

    def upcoming_drop(self, lookahead: float = 520.0) -> int | None:
        """Index of the drop whose sign is just ahead of (or under) the buggy."""

        x = self.vehicle.x
        for index, drop in enumerate(self.layout.drops):
            if drop.sign_x - lookahead <= x <= drop.edge_x:
                return index
        return None

    # -- lifecycle ------------------------------------------------------------------

    def respawn(self) -> None:
        """Put the buggy back upright, at rest, on the last flag it passed."""

        self.vehicle = Vehicle(x=self.checkpoint_x)
        self.tumbling = False
        self._drop_launch_timer = 0.0
        self._stall_timer = 0.0
        self._settle()

    def _settle(self) -> None:
        veh = self.vehicle
        ground = self.layout.height(veh.x)
        veh.angle = math.atan(self.layout.slope(veh.x))
        veh.y = ground - WHEEL_RADIUS - SUSPENSION_REST_LENGTH + 6.0
        for wheel in veh.wheels:
            wheel.hub_x = veh.x + wheel.rel_x * math.cos(veh.angle)
            wheel.hub_y = self.layout.height(wheel.hub_x) - WHEEL_RADIUS
            wheel.in_contact = True

    # -- physics ----------------------------------------------------------------------

    def step(self, controls: Controls = Controls()) -> list[RunEvent]:
        """Advance exactly one fixed step (``FIXED_DT``)."""

        events: list[RunEvent] = []
        dt = FIXED_DT
        self.elapsed += dt
        veh = self.vehicle
        go = controls.go and not self.tumbling and not self.finished
        brake = (controls.brake and not self.tumbling) or self.finished
        tilt = 0.0 if self.tumbling else max(-1.0, min(1.0, controls.tilt))
        before_x = veh.x
        if self._mushroom_cooldown > 0.0:
            self._mushroom_cooldown -= dt

        # Drop signs: with assist the buggy slows itself before the edge.
        if self.drop_assist and not veh.airborne:
            for drop in self.layout.drops:
                if drop.sign_x <= veh.x <= drop.edge_x and veh.vx > ASSIST_DROP_SPEED:
                    go = False
                    veh.vx = max(ASSIST_DROP_SPEED, veh.vx - BRAKE_DECEL * dt)

        self._integrate(dt, go, brake, tilt, events)
        if self.tumbling:
            # A tumbled buggy settles where it lies (on its roof), it does not roll on.
            veh.angular_velocity *= 0.86
            if not veh.airborne or veh.y >= self.layout.height(veh.x) - CHASSIS_HEIGHT:
                veh.vx *= 0.96

        # Drop edges: too fast over the edge -> head over heels.
        for index, drop in enumerate(self.layout.drops):
            if before_x < drop.edge_x <= veh.x and not self.tumbling:
                if veh.vx > DROP_SAFE_SPEED:
                    # Head over heels: a clear, comical half-somersault.
                    veh.angular_velocity = DROP_LAUNCH_SPIN
                    veh.vy = min(veh.vy, -160.0)
                    self._drop_launch_timer = DROP_TUMBLE_SECONDS
                    self.drop_hints.add(index)
                    events.append(RunEvent.DROP_TOO_FAST)
                else:
                    events.append(RunEvent.DROP_SAFE)
        if self._drop_launch_timer > 0.0 and not self.tumbling:
            self._drop_launch_timer -= dt
            if self._drop_launch_timer <= 0.0:
                self._tumble(events)

        # Flips: upside down for a moment, in the air or on the roof.
        norm = (veh.angle + math.pi) % (2.0 * math.pi) - math.pi
        upside_down = abs(norm) > FLIP_TOLERANCE_ANGLE
        if upside_down and not self.tumbling:
            veh.flip_timer += dt
            if veh.flip_timer >= FLIP_DURATION_THRESHOLD:
                self._tumble(events)
        else:
            veh.flip_timer = max(0.0, veh.flip_timer - dt * 1.5)

        # Stuck (on a side, or no progress while pressing GO): kindly reset.
        if go and not veh.airborne and abs(veh.vx) < STALL_SPEED and not self.tumbling:
            self._stall_timer += dt
            if self._stall_timer >= STALL_SECONDS:
                self._tumble(events)
        else:
            self._stall_timer = 0.0

        if not self.tumbling:
            for flag in self.layout.checkpoints:
                if flag not in self.passed_flags and veh.x >= flag:
                    self.passed_flags.add(flag)
                    self.checkpoint_x = max(self.checkpoint_x, flag)
                    events.append(RunEvent.CHECKPOINT)
            for star in self.stars:
                if not star.collected:
                    dx = veh.x - star.x
                    dy = (veh.y - 20.0) - star.y
                    if dx * dx + dy * dy < STAR_PICKUP_RADIUS * STAR_PICKUP_RADIUS:
                        star.collected = True
                        events.append(RunEvent.STAR)
            if not self.finished and veh.x >= self.layout.finish_x:
                self.finished = True
                events.append(RunEvent.FINISH)
        return events

    def _tumble(self, events: list[RunEvent]) -> None:
        self.tumbling = True
        self.tumbles += 1
        self.vehicle.flip_timer = 0.0
        self._drop_launch_timer = 0.0
        self._stall_timer = 0.0
        events.append(RunEvent.TUMBLE)

    def _integrate(self, dt: float, go: bool, brake: bool, tilt: float, events: list[RunEvent]) -> None:
        layout = self.layout
        veh = self.vehicle
        cos_a = math.cos(veh.angle)
        sin_a = math.sin(veh.angle)
        nx, ny = -sin_a, cos_a  # chassis "down"

        veh.vy += GRAVITY * dt
        force_x = force_y = torque = 0.0
        contacts = 0
        in_mud = False
        for wheel in veh.wheels:
            mount_x = veh.x + wheel.rel_x * cos_a
            mount_y = veh.y + wheel.rel_x * sin_a
            hub_x = mount_x + nx * SUSPENSION_REST_LENGTH
            hub_y = mount_y + ny * SUSPENSION_REST_LENGTH
            ground = layout.height(hub_x)
            surface = layout.surface(hub_x)
            wheel.surface = surface
            penetration = hub_y + WHEEL_RADIUS - ground
            if penetration <= 0.0:
                wheel.in_contact = False
                wheel.compression = 0.0
                wheel.hub_x, wheel.hub_y = hub_x, hub_y
                continue
            wheel.in_contact = True
            contacts += 1
            compression = min(SUSPENSION_MAX_LENGTH, penetration)
            wheel.compression = compression
            wheel.hub_x = hub_x
            wheel.hub_y = max(ground - WHEEL_RADIUS, mount_y + ny * SUSPENSION_MIN_LENGTH)
            tnx, tny = layout.normal(hub_x)
            along_normal = veh.vx * tnx + veh.vy * tny
            spring = compression * SUSPENSION_STIFFNESS - along_normal * SUSPENSION_DAMPING
            if spring > 0.0:
                force_x += tnx * spring
                force_y += tny * spring
                torque += (wheel.rel_x / (WHEELBASE / 2.0)) * (-spring * 0.015)
            if surface is Surface.MUSHROOM and self._mushroom_cooldown <= 0.0:
                veh.vy = min(veh.vy, MUSHROOM_BOUNCE_VY)
                veh.vx = max(veh.vx, 0.0) + MUSHROOM_BOUNCE_VX
                self._mushroom_cooldown = MUSHROOM_COOLDOWN
                events.append(RunEvent.BOUNCE)
            if surface is Surface.MUD:
                in_mud = True
            slope = layout.slope(hub_x)
            norm = math.hypot(1.0, slope)
            tx, ty = 1.0 / norm, slope / norm
            if go:
                # Half per wheel; assist adds a little climbing help so a buggy
                # put back at the foot of a steep hill can always get up it.
                accel = DRIVE_ACCEL * (MUD_TRACTION if surface is Surface.MUD else 1.0) * 0.5
                if self.assist:
                    accel *= ASSIST_CLIMB
                veh.vx += tx * accel * dt
                veh.vy += ty * accel * dt
            elif brake:
                speed = math.hypot(veh.vx, veh.vy)
                if speed > 6.0:
                    # After the finish the buggy rolls gently up to the picnic.
                    strength = FINISH_ROLL_BRAKE if self.finished else 1.0
                    cut = min(speed, BRAKE_DECEL * 0.5 * strength * dt)
                    veh.vx -= veh.vx / speed * cut
                    veh.vy -= veh.vy / speed * cut
                elif not self.finished:
                    veh.vx += tx * MAX_REVERSE_SPEED * 0.4 * dt

        veh.vx += force_x * dt
        veh.vy += force_y * dt
        was_airborne = veh.airborne
        veh.airborne = contacts == 0
        if veh.airborne:
            veh.air_time += dt
            if tilt:
                veh.angular_velocity += tilt * AIR_TILT_TORQUE * dt
            if self.air_assist and self._drop_launch_timer <= 0.0 and not self.tumbling:
                target = math.atan(layout.slope(veh.x + veh.vx * 0.25))
                veh.angular_velocity += (target - veh.angle) * AUTO_UPRIGHT_GAIN * dt
            veh.vx *= AIR_DRAG
        else:
            if was_airborne and veh.air_time > PERFECT_LANDING_MIN_AIR:
                events.append(RunEvent.LANDING)
                if contacts == 2 and not self.tumbling and self._drop_launch_timer <= 0.0:
                    ground_angle = math.atan(layout.slope(veh.x))
                    if abs(veh.angle - ground_angle) <= PERFECT_LANDING_ANGLE_TOLERANCE:
                        veh.vx += PERFECT_LANDING_BOOST
                        events.append(RunEvent.PERFECT_LANDING)
            veh.air_time = 0.0
            veh.vx *= ROLLING_FRICTION
            if in_mud:
                veh.vx *= MUD_DRAG

        if self._drop_launch_timer <= 0.0:
            veh.angular_velocity += torque * dt
            veh.angular_velocity *= max(0.0, 1.0 - ANGULAR_DAMPING * dt)
        veh.angle += veh.angular_velocity * dt
        veh.vx = max(MAX_REVERSE_SPEED, min(MAX_FORWARD_SPEED, veh.vx))
        veh.x += veh.vx * dt
        veh.y += veh.vy * dt
        veh.x = max(40.0, min(layout.length - 200.0, veh.x))

        # Keep the chassis out of the ground (the roof of a tumbled buggy rests on it).
        floor = layout.height(veh.x) - CHASSIS_HEIGHT / 2.0 + 12.0
        if veh.y > floor:
            veh.y = floor
            if veh.vy > 0.0:
                veh.vy = 0.0
            if veh.airborne:
                veh.vx *= 0.9
        if contacts:
            veh.wheel_spin = (veh.wheel_spin + veh.vx * dt / WHEEL_RADIUS) % (2.0 * math.pi)


# -- the set of five courses ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CourseResult:
    course_id: str
    stars: int
    tumbles: int
    seconds: float


class CourseSet:
    """Five courses in order (gentle -> wild) at one rung."""

    def __init__(self, rung: int = 1, courses: Sequence[CourseSpec] = COURSES) -> None:
        self.rung = max(MIN_RUNG, min(MAX_RUNG, int(rung)))
        self.courses = tuple(courses)[:COURSES_PER_SET]
        self.index = 0
        self.results: list[CourseResult] = []

    @property
    def total(self) -> int:
        return len(self.courses)

    @property
    def complete(self) -> bool:
        return len(self.results) >= self.total

    @property
    def current(self) -> CourseSpec:
        return self.courses[min(self.index, self.total - 1)]

    @property
    def total_stars(self) -> int:
        return sum(result.stars for result in self.results)

    @property
    def total_tumbles(self) -> int:
        return sum(result.tumbles for result in self.results)

    def build_run(self) -> CourseRun:
        """A fresh run of the current course (rung 1 always helps in the air)."""

        layout = CourseLayout(self.current, self.rung)
        return CourseRun(layout, assist=self.rung == MIN_RUNG)

    def record(self, run: CourseRun) -> CourseResult:
        result = CourseResult(run.layout.spec.course_id, run.stars_collected, run.tumbles, run.elapsed)
        if not self.complete:
            self.results.append(result)
            self.index = min(self.total, self.index + 1)
        return result


def adapt_rung(rung: int, tumbles: int) -> int:
    """Next set's rung: smooth sets climb, sets with many tumbles ease off."""

    if tumbles <= PROMOTE_MAX_TUMBLES:
        rung += 1
    elif tumbles >= DEMOTE_MIN_TUMBLES:
        rung -= 1
    return max(MIN_RUNG, min(MAX_RUNG, rung))


def bounded_history(history: Sequence[int], tumbles: int) -> tuple[int, ...]:
    return (*tuple(history), int(tumbles))[-HISTORY_LIMIT:]


__all__ = [
    "Controls",
    "CourseLayout",
    "CourseResult",
    "CourseRun",
    "CourseSet",
    "DropEdge",
    "RunEvent",
    "Span",
    "Star",
    "Vehicle",
    "Wheel",
    "adapt_rung",
    "bounded_history",
    "feature_offset",
]
