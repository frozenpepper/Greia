"""Domain model and simulation for Il Viaggio del Delfino.

The module owns the gameplay invariants:

- one journey is a finite course with a finish line; the dolphin always
  swims forward and the child steers its depth (and leaps out of the water);
- above the water line motion is ballistic (a leap), below it swimming is a
  smooth spring-damped pursuit of the child's target depth (no fail state);
- pearls come in small groups; a group above the waves needs a leap;
- jellyfish never harm: contact gently bumps the dolphin away;
- sea friends wait for the dolphin and always end up being met (kindly
  drifting closer if the child does not steer to them), unlocking one fact;
- course content is a fixed, bounded set built once per journey.

Rendering, audio, storage and platform IO live elsewhere; this file stays
pure simulation so it is unit-testable without pygame or Greia services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
import random
from typing import Final

try:
    from delfino_content import JourneySpec, FriendSpec, REFERENCE_HEIGHT, REFERENCE_WIDTH, SURFACE_Y
except ImportError:  # repository/package import context
    from .delfino_content import JourneySpec, FriendSpec, REFERENCE_HEIGHT, REFERENCE_WIDTH, SURFACE_Y

__all__ = [
    "Course",
    "Dolphin",
    "DOLPHIN_SCREEN_X",
    "EventKind",
    "Friend",
    "FriendState",
    "JourneyEvent",
    "JourneyRun",
    "Jellyfish",
    "MAX_SWIM_Y",
    "MIN_SWIM_Y",
    "Pearl",
    "PearlGroup",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SURFACE_Y",
    "build_course",
]

#: Vertical bounds for the dolphin centre. The upper bound allows real leaps
#: above the waves while keeping the animal fully on screen.
MIN_SWIM_Y: Final = 70.0
MAX_SWIM_Y: Final = 520.0

#: Where the dolphin swims on screen; the camera follows it.
DOLPHIN_SCREEN_X: Final = 220.0

#: Pickup radius around the dolphin centre and around its nose: children aim
#: with the nose of a long sprite, so both count.
DOLPHIN_RADIUS: Final = 46.0
DOLPHIN_NOSE_OFFSET: Final = 80.0

#: A leap: the dolphin rises quickly, breaks the surface with a boost, flies a
#: ballistic arc and dives back. Swimming is a little faster while leaping.
LEAP_SPEED_FACTOR: Final = 1.45
LEAP_SECONDS: Final = 2.2
RISE_SPEED: Final = 520.0
GRAVITY: Final = 900.0
LEAVE_WATER_BOOST: Final = -380.0
SURFACE_SWIM_MARGIN: Final = 30.0
REENTRY_COOLDOWN: Final = 0.5

#: Course geometry.
COURSE_START_X: Final = 900.0
FINISH_MARGIN: Final = 520.0
PEARL_SPACING: Final = 92.0
GROUP_TOP: Final = SURFACE_Y + 80.0
GROUP_BOTTOM: Final = MAX_SWIM_Y - 24.0

#: Friends: where they start waiting on screen, how close they come, and how
#: long the meeting escort lasts.
FRIEND_WAIT_SCREEN_X: Final = 780.0
FRIEND_HOLD_SCREEN_X: Final = DOLPHIN_SCREEN_X + 150.0
FRIEND_APPROACH_SPEED: Final = 95.0
FRIEND_MEET_RADIUS: Final = 74.0
FRIEND_PATIENT_SECONDS: Final = 7.0
FRIEND_ESCORT_SECONDS: Final = 7.5

#: Bounded decorative wake.
MAX_WAKE: Final = 24


class EventKind(StrEnum):
    """Semantic journey events reported to the app layer."""

    PEARL = "pearl"
    GROUP_COMPLETE = "group_complete"
    GROUP_MISSED = "group_missed"
    SPLASH_OUT = "splash_out"
    SPLASH_IN = "splash_in"
    BUMP = "bump"
    FRIEND_WAITING = "friend_waiting"
    FRIEND_MET = "friend_met"
    STRETCH = "stretch"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class JourneyEvent:
    kind: EventKind
    x: float = 0.0
    y: float = 0.0
    ref: str | None = None


@dataclass(slots=True)
class Dolphin:
    """The child-controlled dolphin."""

    x: float = DOLPHIN_SCREEN_X
    y: float = 330.0
    target_y: float = 330.0
    base_speed: float = 160.0
    vertical_velocity: float = 0.0
    leap_timer: float = 0.0
    leap_pending: bool = False
    airborne: bool = False
    air_time: float = 0.0
    surface_cooldown: float = 0.0
    swim_phase: float = 0.0
    stopped: bool = False

    @property
    def speed(self) -> float:
        if self.stopped:
            return 0.0
        return self.base_speed * (LEAP_SPEED_FACTOR if self.leap_timer > 0.0 else 1.0)

    @property
    def nose(self) -> tuple[float, float]:
        return (self.x + DOLPHIN_NOSE_OFFSET, self.y)

    @property
    def pitch(self) -> float:
        """Body angle in degrees (counter-clockwise positive = nose up)."""

        return max(-34.0, min(34.0, -self.vertical_velocity * 0.07))

    def steer(self, delta_y: float) -> None:
        """Nudge the target depth (keyboard / controller / pointer semantics)."""

        self.target_y = max(MIN_SWIM_Y, min(MAX_SWIM_Y, self.target_y + delta_y))

    def aim(self, target_y: float) -> None:
        self.target_y = max(MIN_SWIM_Y, min(MAX_SWIM_Y, float(target_y)))

    def trigger_leap(self) -> bool:
        """Start one leap; returns False while one is already under way."""

        if self.stopped or self.airborne or self.leap_pending or self.surface_cooldown > 0.0:
            return False
        self.leap_pending = True
        self.leap_timer = LEAP_SECONDS
        return True

    def stop(self) -> None:
        self.stopped = True
        self.leap_pending = False

    def touches(self, x: float, y: float, radius: float = DOLPHIN_RADIUS) -> bool:
        r2 = radius * radius
        nx, ny = self.nose
        return (self.x - x) ** 2 + (self.y - y) ** 2 <= r2 or (nx - x) ** 2 + (ny - y) ** 2 <= r2

    def update(self, dt: float) -> EventKind | None:
        """Advance one step; report surface crossings."""

        event: EventKind | None = None
        self.x += self.speed * dt
        self.swim_phase = (self.swim_phase + (9.0 if self.leap_timer > 0 else 5.5) * dt) % (2.0 * math.pi)
        if self.surface_cooldown > 0.0:
            self.surface_cooldown = max(0.0, self.surface_cooldown - dt)

        if self.y < SURFACE_Y - 8.0:
            if not self.airborne:
                self.airborne = True
                self.air_time = 0.0
                self.vertical_velocity = LEAVE_WATER_BOOST
                event = EventKind.SPLASH_OUT
            self.air_time += dt
            self.vertical_velocity += GRAVITY * dt
            self.y += self.vertical_velocity * dt
        else:
            if self.airborne:
                self.airborne = False
                self.air_time = 0.0
                self.leap_pending = False
                self.surface_cooldown = REENTRY_COOLDOWN
                event = EventKind.SPLASH_IN
                # Dive back under rather than skimming the surface again.
                self.target_y = max(self.target_y, SURFACE_Y + 70.0)
            if self.leap_pending:
                self.vertical_velocity = -RISE_SPEED
            else:
                target = max(self.target_y, SURFACE_Y + SURFACE_SWIM_MARGIN)
                self.vertical_velocity = (target - self.y) * 3.2
            self.y += self.vertical_velocity * dt

        self.y = max(MIN_SWIM_Y, min(MAX_SWIM_Y, self.y))
        if self.leap_timer > 0.0:
            self.leap_timer = max(0.0, self.leap_timer - dt)
            if self.leap_timer == 0.0 and not self.airborne:
                self.leap_pending = False
        return event


@dataclass(slots=True)
class Pearl:
    x: float
    y: float
    group: int
    bob_phase: float = 0.0
    collected: bool = False

    @property
    def effective_y(self) -> float:
        return self.y + math.sin(self.bob_phase) * 4.0


@dataclass(slots=True)
class PearlGroup:
    index: int
    start_x: float
    end_x: float
    size: int
    arc: bool
    collected: int = 0
    resolved: bool = False


@dataclass(slots=True)
class Jellyfish:
    """A friendly drifting jellyfish: contact only bumps, never harms."""

    x: float
    y: float
    drift_amplitude: float = 36.0
    drift_phase: float = 0.0
    drift_speed: float = 1.1
    bump_cooldown: float = 0.0
    happy_timer: float = 0.0

    @property
    def effective_y(self) -> float:
        return self.y + math.sin(self.drift_phase) * self.drift_amplitude

    def update(self, dt: float) -> None:
        self.drift_phase = (self.drift_phase + self.drift_speed * dt) % (2.0 * math.pi)
        self.bump_cooldown = max(0.0, self.bump_cooldown - dt)
        self.happy_timer = max(0.0, self.happy_timer - dt)


class FriendState(StrEnum):
    AHEAD = "ahead"
    WAITING = "waiting"
    MET = "met"
    LEAVING = "leaving"
    GONE = "gone"


@dataclass(slots=True)
class Friend:
    """A sea friend that waits for the dolphin and shares a fact when met."""

    spec: FriendSpec
    x: float
    y: float
    state: FriendState = FriendState.AHEAD
    wait_time: float = 0.0
    escort_time: float = 0.0
    bob_phase: float = 0.0

    @property
    def facing_right(self) -> bool:
        return self.state in (FriendState.MET, FriendState.LEAVING)

    @property
    def happy(self) -> bool:
        return self.state in (FriendState.MET, FriendState.LEAVING)

    @property
    def draw_y(self) -> float:
        return self.y + math.sin(self.bob_phase) * 6.0


@dataclass(slots=True)
class Course:
    """Fixed, bounded content of one journey."""

    spec: JourneySpec
    pearls: list[Pearl]
    groups: list[PearlGroup]
    jellies: list[Jellyfish]
    friends: list[Friend]
    stretch_ends: list[float]
    finish_x: float

    @property
    def total_pearls(self) -> int:
        return len(self.pearls)


def _leap_path(speed: float, start_y: float) -> list[tuple[float, float]]:
    """Simulated airborne path of one leap started at ``start_y`` (x from 0)."""

    probe = Dolphin(x=0.0, y=start_y, target_y=start_y, base_speed=speed)
    probe.trigger_leap()
    path: list[tuple[float, float]] = []
    for _ in range(600):
        probe.update(1.0 / 60.0)
        if probe.airborne:
            path.append((probe.x, probe.y))
        elif path:
            break
    return path


def _arc_points(speed: float, count: int) -> list[tuple[float, float]]:
    """``count`` points evenly spread along the airborne part of a leap."""

    path = _leap_path(speed, SURFACE_Y + 90.0)
    if len(path) < 2:
        return [(i * PEARL_SPACING, SURFACE_Y - 40.0) for i in range(count)]
    lengths = [0.0]
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    total = lengths[-1]
    points: list[tuple[float, float]] = []
    for i in range(count):
        # Keep the first/last pearls just above the splash, not on it.
        goal = total * (0.12 + 0.76 * (i / max(1, count - 1)))
        for j in range(1, len(lengths)):
            if lengths[j] >= goal:
                span = max(1e-6, lengths[j] - lengths[j - 1])
                t = (goal - lengths[j - 1]) / span
                (x0, y0), (x1, y1) = path[j - 1], path[j]
                points.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
                break
    return points


def _group_points(shape: str, count: int, rng: random.Random) -> list[tuple[float, float]]:
    span = PEARL_SPACING * (count - 1)
    if shape == "wave":
        base = rng.uniform(GROUP_TOP + 50.0, GROUP_BOTTOM - 50.0)
        return [(i * PEARL_SPACING, base + math.sin(i * 1.2) * 42.0) for i in range(count)]
    if shape in ("rise", "dip"):
        drop = min(150.0, 40.0 * count)
        top = rng.uniform(GROUP_TOP, GROUP_BOTTOM - drop)
        ys = [top + drop * (i / max(1, count - 1)) for i in range(count)]
        if shape == "rise":
            ys.reverse()
        return [(i * PEARL_SPACING, y) for i, y in enumerate(ys)]
    y = rng.uniform(GROUP_TOP, GROUP_BOTTOM)
    del span
    return [(i * PEARL_SPACING, y) for i in range(count)]


def build_course(spec: JourneySpec, rng: random.Random) -> Course:
    """Lay out one journey: pearl groups, arcs, jellies and friends by stretch."""

    slots = spec.layout
    usable = spec.length_x - COURSE_START_X - FINISH_MARGIN
    width = usable / len(slots)
    pearls: list[Pearl] = []
    groups: list[PearlGroup] = []
    friends: list[Friend] = []
    jelly_spots: list[tuple[float, float]] = []
    friend_specs = iter(spec.friends)
    stretch_ends = [COURSE_START_X + width * (i + 1) for i in range(len(slots))]
    shapes = ["line", "wave", "rise", "dip"]
    last_shape = ""
    for index, slot in enumerate(slots):
        centre = COURSE_START_X + width * (index + 0.5)
        if slot == "F":
            friend_spec = next(friend_specs, None)
            if friend_spec is not None:
                friends.append(Friend(friend_spec, centre, rng.uniform(GROUP_TOP + 30.0, GROUP_BOTTOM - 60.0)))
            continue
        if slot == "A":
            points = _arc_points(spec.speed, spec.group_size)
        else:
            choice = rng.choice([s for s in shapes if s != last_shape])
            last_shape = choice
            points = _group_points(choice, spec.group_size, rng)
        span = points[-1][0] - points[0][0]
        start = centre - span / 2.0
        group = PearlGroup(len(groups), start, start + span, len(points), slot == "A")
        for px, py in points:
            pearls.append(Pearl(start + px - points[0][0], py, group.index, bob_phase=rng.uniform(0.0, math.tau)))
        groups.append(group)
        if slot == "G":
            mean_y = sum(p[1] for p in points) / len(points)
            for side in (-1.0, 1.0):
                jx = centre + side * (span / 2.0 + width * 0.22)
                offset = rng.uniform(120.0, 170.0) * rng.choice((-1.0, 1.0))
                jy = mean_y + offset
                if not GROUP_TOP - 10.0 <= jy <= GROUP_BOTTOM:
                    jy = mean_y - offset
                jelly_spots.append((jx, max(GROUP_TOP, min(GROUP_BOTTOM - 20.0, jy))))
    rng.shuffle(jelly_spots)
    chosen = sorted(jelly_spots[: spec.jellies])
    jellies = [
        Jellyfish(x, y, drift_phase=rng.uniform(0.0, math.tau), drift_speed=rng.uniform(0.8, 1.4))
        for x, y in chosen
    ]
    return Course(spec, pearls, groups, jellies, friends, stretch_ends, spec.length_x)


@dataclass
class JourneyRun:
    """Complete simulation state for one journey on one course."""

    course: Course
    dolphin: Dolphin = field(default_factory=Dolphin)
    collected: int = 0
    stretches_passed: int = 0
    finished: bool = False
    leaps: int = 0
    wake: list[tuple[float, float, float]] = field(default_factory=list)
    _wake_timer: float = 0.0

    @classmethod
    def start(cls, spec: JourneySpec, rng: random.Random) -> "JourneyRun":
        run = cls(build_course(spec, rng))
        run.dolphin = Dolphin(base_speed=spec.speed)
        return run

    @property
    def spec(self) -> JourneySpec:
        return self.course.spec

    @property
    def camera_x(self) -> float:
        return self.dolphin.x - DOLPHIN_SCREEN_X

    @property
    def fraction(self) -> float:
        return max(0.0, min(1.0, self.dolphin.x / self.course.finish_x))

    def leap(self) -> bool:
        if self.dolphin.trigger_leap():
            self.leaps += 1
            return True
        return False

    def waiting_friend(self) -> Friend | None:
        for friend in self.course.friends:
            if friend.state is FriendState.WAITING:
                return friend
        return None

    def next_target(self) -> tuple[float, float] | None:
        """World point the child should head for next (hints only)."""

        friend = self.waiting_friend()
        if friend is not None:
            return (friend.x, friend.y)
        ahead = self.dolphin.x - 30.0
        for group in self.course.groups:
            if group.resolved or group.end_x < ahead:
                continue
            for pearl in self.course.pearls:
                if pearl.group == group.index and not pearl.collected and pearl.x >= ahead:
                    return (pearl.x, pearl.y)
        return None

    # ------------------------------------------------------------------ sim

    def update(self, dt: float) -> list[JourneyEvent]:
        events: list[JourneyEvent] = []
        dolphin = self.dolphin
        crossing = dolphin.update(dt)
        if crossing is not None:
            events.append(JourneyEvent(crossing, dolphin.x, SURFACE_Y))
        self._update_wake(dt)
        self._update_pearls(dt, events)
        self._update_jellies(dt, events)
        self._update_friends(dt, events)
        passed = sum(1 for end in self.course.stretch_ends if dolphin.x >= end)
        while self.stretches_passed < passed:
            self.stretches_passed += 1
            events.append(JourneyEvent(EventKind.STRETCH, dolphin.x, dolphin.y))
        if not self.finished and dolphin.x >= self.course.finish_x:
            self.finished = True
            self.stretches_passed = len(self.course.stretch_ends)
            dolphin.stop()
            events.append(JourneyEvent(EventKind.FINISHED, dolphin.x, dolphin.y))
        return events

    def _update_wake(self, dt: float) -> None:
        dolphin = self.dolphin
        aged = [(x, y, age + dt) for x, y, age in self.wake if age + dt < 1.2]
        self._wake_timer -= dt
        if self._wake_timer <= 0.0 and not dolphin.airborne and not dolphin.stopped:
            self._wake_timer = 0.09 if dolphin.leap_timer > 0 else 0.22
            aged.append((dolphin.x - 92.0, dolphin.y + math.sin(dolphin.swim_phase) * 8.0, 0.0))
        self.wake = aged[-MAX_WAKE:]

    def _update_pearls(self, dt: float, events: list[JourneyEvent]) -> None:
        dolphin = self.dolphin
        groups = self.course.groups
        for pearl in self.course.pearls:
            if pearl.collected:
                continue
            pearl.bob_phase = (pearl.bob_phase + 2.6 * dt) % math.tau
            if abs(pearl.x - dolphin.x) > 200.0:
                continue
            if dolphin.touches(pearl.x, pearl.effective_y):
                pearl.collected = True
                self.collected += 1
                group = groups[pearl.group]
                group.collected += 1
                events.append(JourneyEvent(EventKind.PEARL, pearl.x, pearl.effective_y))
                if group.collected >= group.size and not group.resolved:
                    group.resolved = True
                    events.append(JourneyEvent(EventKind.GROUP_COMPLETE, pearl.x, pearl.effective_y, "arc" if group.arc else "water"))
        for group in groups:
            if not group.resolved and dolphin.x - 60.0 > group.end_x:
                group.resolved = True
                if group.collected == 0:
                    events.append(JourneyEvent(EventKind.GROUP_MISSED, group.end_x, dolphin.y, "arc" if group.arc else "water"))

    def _update_jellies(self, dt: float, events: list[JourneyEvent]) -> None:
        dolphin = self.dolphin
        for jelly in self.course.jellies:
            jelly.update(dt)
            if jelly.bump_cooldown > 0.0 or dolphin.airborne:
                continue
            if abs(dolphin.x - jelly.x) <= 56.0 and abs(dolphin.y - jelly.effective_y) <= 52.0:
                jelly.bump_cooldown = 1.4
                jelly.happy_timer = 1.2
                if dolphin.y >= jelly.effective_y:
                    dolphin.aim(min(MAX_SWIM_Y, jelly.effective_y + 120.0))
                else:
                    dolphin.aim(max(SURFACE_Y + SURFACE_SWIM_MARGIN, jelly.effective_y - 120.0))
                events.append(JourneyEvent(EventKind.BUMP, jelly.x, jelly.effective_y))

    def _update_friends(self, dt: float, events: list[JourneyEvent]) -> None:
        dolphin = self.dolphin
        camera = self.camera_x
        for friend in self.course.friends:
            friend.bob_phase = (friend.bob_phase + 2.0 * dt) % math.tau
            state = friend.state
            if state is FriendState.AHEAD:
                if friend.x - camera <= FRIEND_WAIT_SCREEN_X:
                    friend.state = FriendState.WAITING
                    events.append(JourneyEvent(EventKind.FRIEND_WAITING, friend.x, friend.y, friend.spec.friend_id))
            elif state is FriendState.WAITING:
                friend.wait_time += dt
                screen_x = friend.x - camera
                # The friend swims towards the dolphin, then holds just ahead
                # of its nose: it never scrolls away unmet.
                screen_x = max(FRIEND_HOLD_SCREEN_X, screen_x - FRIEND_APPROACH_SPEED * dt)
                friend.x = camera + screen_x
                patient = friend.wait_time >= FRIEND_PATIENT_SECONDS
                glide = (75.0 if patient else 12.0) * dt
                if abs(dolphin.y - friend.y) > glide:
                    friend.y += glide if dolphin.y > friend.y else -glide
                friend.y = max(SURFACE_Y + 40.0, min(MAX_SWIM_Y, friend.y))
                if not dolphin.airborne and dolphin.touches(friend.x, friend.draw_y, FRIEND_MEET_RADIUS):
                    friend.state = FriendState.MET
                    friend.escort_time = 0.0
                    events.append(JourneyEvent(EventKind.FRIEND_MET, friend.x, friend.draw_y, friend.spec.friend_id))
            elif state is FriendState.MET:
                friend.escort_time += dt
                if friend.spec.joins:
                    goal = (dolphin.x - 150.0, max(SURFACE_Y + 50.0, dolphin.y + 60.0))
                else:
                    goal = (dolphin.x + 30.0, min(MAX_SWIM_Y, dolphin.y + 95.0))
                friend.x += (goal[0] - friend.x) * min(1.0, 2.2 * dt)
                friend.y += (goal[1] - friend.y) * min(1.0, 1.6 * dt)
                if not friend.spec.joins and friend.escort_time >= FRIEND_ESCORT_SECONDS:
                    friend.state = FriendState.LEAVING
            elif state is FriendState.LEAVING:
                # Waves goodbye: drifts down and behind until off screen.
                friend.x += (dolphin.speed - 140.0) * dt
                friend.y = min(REFERENCE_HEIGHT + 120.0, friend.y + 50.0 * dt)
                if friend.x - camera < -260.0:
                    friend.state = FriendState.GONE
