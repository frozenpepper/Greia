"""Domain model for Il Volo del Draghetto: one finite sky course.

The child steers a little dragon through a side-scrolling sky. A course is a
fixed sequence of rainbow rings (the checkpoints shown as progress dots),
star trails that lead towards each ring, a few bouncy clouds and a finish
rainbow. Nothing can fail: clouds only bounce the dragon away, and a ring the
dragon flies past hops a little further ahead, closer to the dragon and a
little wider, with a trail of stars showing the way (unlimited kind retries).

Coordinates are logical 1024x600 pixels. ``FlightRun.distance`` is the
dragon's world x; the dragon is drawn at a fixed screen x
(``DRAGON_SCREEN_X``) and the world scrolls. Pure Python: no Pygame here, so
the whole flight is testable headlessly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
import random
from typing import Final

try:
    from dragon_courses import CourseSpec
except ImportError:  # pragma: no cover - package import path
    from .dragon_courses import CourseSpec

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

DRAGON_SCREEN_X: Final = 250.0
MIN_Y: Final = 150.0
MAX_Y: Final = 498.0
CENTER_Y: Final = (MIN_Y + MAX_Y) / 2.0
DRAGON_RADIUS: Final = 34.0

STEER_SPEED: Final = 260.0
GLIDE_SINK: Final = 38.0
RESPONSE: Final = 7.0
FLAP_LIFT: Final = 300.0
LIFT_DECAY: Final = 4.0
DRAG_GAIN: Final = 6.0
FAST_FACTOR: Final = 1.4
SLOW_FACTOR: Final = 0.6
BUMP_SPEED: Final = 230.0
BUMP_COOLDOWN: Final = 0.6
BUMP_SLOW_SECONDS: Final = 0.5

START_GAP: Final = 900.0
FINISH_GAP: Final = 900.0
RETRY_GAP: Final = 760.0
MAX_HALF_OPEN: Final = 130.0
STAR_STEP: Final = 76.0
PICKUP_REACH: Final = 26.0
GEM_REACH: Final = 30.0
RING_MOVE_SECONDS: Final = 0.7
FINISH_SECONDS: Final = 2.4
GEM_WEIGHT: Final = 3


class PickupKind(StrEnum):
    STAR = "star"
    GEM = "gem"


class RingState(StrEnum):
    WAITING = "waiting"
    PASSED = "passed"


class FlightPhase(StrEnum):
    FLYING = "flying"
    FINISHING = "finishing"
    DONE = "done"


class FlightEventKind(StrEnum):
    STAR = "star"
    GEM = "gem"
    RING_PASSED = "ring_passed"
    RING_MISSED = "ring_missed"
    BUMP = "bump"
    HALFWAY = "halfway"
    FINISH = "finish"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class FlightEvent:
    kind: FlightEventKind
    x: float
    y: float
    index: int = -1


@dataclass(slots=True)
class FlightInput:
    """Steering intent for one step, already normalised by the app.

    ``vertical`` is -1 (climb) .. +1 (dive) from arrows / D-pad / stick;
    ``horizontal`` is -1 (hover slower) .. +1 (fly faster); ``drag_y`` is the
    logical y of a held pointer/touch drag, which steers towards it.
    """

    vertical: float = 0.0
    horizontal: float = 0.0
    drag_y: float | None = None


@dataclass(slots=True)
class DragonFlier:
    """Vertical flight physics: steer, glide gently down, flap up, bounce."""

    y: float = CENTER_Y
    vy: float = 0.0
    lift: float = 0.0
    wing_phase: float = 0.0
    flap_boost: float = 0.0
    slow_timer: float = 0.0

    def flap(self) -> None:
        """One wing beat: an upward lift that fades out (~75 px climb)."""

        self.lift = min(FLAP_LIFT * 1.4, self.lift + FLAP_LIFT)
        self.vy = min(self.vy, GLIDE_SINK)
        self.flap_boost = 0.35

    def bump(self, direction: float) -> None:
        self.lift = 0.0
        self.vy = BUMP_SPEED * (1.0 if direction >= 0 else -1.0)
        self.slow_timer = BUMP_SLOW_SECONDS

    def speed_factor(self, horizontal: float) -> float:
        h = max(-1.0, min(1.0, horizontal))
        factor = 1.0 + (FAST_FACTOR - 1.0) * h if h > 0 else 1.0 + (1.0 - SLOW_FACTOR) * h
        if self.slow_timer > 0.0:
            factor *= 0.55
        return factor

    def update(self, dt: float, steer: FlightInput) -> None:
        if steer.drag_y is not None:
            target = max(-STEER_SPEED, min(STEER_SPEED, (steer.drag_y - self.y) * DRAG_GAIN))
        elif abs(steer.vertical) > 0.01:
            target = max(-1.0, min(1.0, steer.vertical)) * STEER_SPEED
        else:
            target = GLIDE_SINK
        self.vy += (target - self.vy) * min(1.0, RESPONSE * dt)
        self.lift *= math.exp(-LIFT_DECAY * dt)
        if self.lift < 4.0:
            self.lift = 0.0
        self.y += (self.vy - self.lift) * dt
        if self.y < MIN_Y:
            self.y = MIN_Y
            self.vy = max(self.vy, 0.0)
            self.lift = 0.0
        elif self.y > MAX_Y:
            # Soft cloud floor: a small bounce, never a fall.
            self.y = MAX_Y
            if self.vy > 0.0:
                self.vy = -max(40.0, self.vy * 0.3)
        climbing = self.vy - self.lift < -60.0
        self.wing_phase = (self.wing_phase + dt * (10.0 if climbing or self.flap_boost > 0 else 4.5)) % 4.0
        self.flap_boost = max(0.0, self.flap_boost - dt)
        self.slow_timer = max(0.0, self.slow_timer - dt)

    @property
    def wing_frame(self) -> int:
        """0 = wings up, 1 = mid, 2 = down (cycle up, mid, down, mid)."""

        return (0, 1, 2, 1)[int(self.wing_phase) % 4]


@dataclass(slots=True)
class Pickup:
    x: float
    y: float
    kind: PickupKind = PickupKind.STAR
    taken: bool = False


@dataclass(slots=True)
class Ring:
    """A rainbow ring checkpoint; ``half_open`` is the y tolerance."""

    checkpoint: int
    x: float
    y: float
    half_open: float
    state: RingState = RingState.WAITING
    retries: int = 0
    moved_from: tuple[float, float] | None = None
    moved_at: float = -10.0


@dataclass(slots=True)
class Cloud:
    x: float
    y: float
    half_w: float = 74.0
    half_h: float = 40.0
    bumped_at: float = -10.0


@dataclass(slots=True)
class FlightCourse:
    spec: CourseSpec
    pickups: list[Pickup]
    rings: list[Ring]
    clouds: list[Cloud]
    finish_x: float

    @property
    def stars_total(self) -> int:
        return sum(1 for p in self.pickups if p.kind is PickupKind.STAR)

    @property
    def gems_total(self) -> int:
        return sum(1 for p in self.pickups if p.kind is PickupKind.GEM)


@dataclass(frozen=True, slots=True)
class FlightResult:
    course_id: str
    stars: int
    stars_total: int
    gems: int
    gems_total: int
    misses: int

    @property
    def earned(self) -> int:
        """Completion stars 1..3: finishing always earns one."""

        total = self.stars_total + GEM_WEIGHT * self.gems_total
        if total <= 0:
            return 3
        share = (self.stars + GEM_WEIGHT * self.gems) / total
        if share >= 0.75:
            return 3
        if share >= 0.45:
            return 2
        return 1


def _clamp_y(y: float, margin: float = 0.0) -> float:
    return max(MIN_Y + margin, min(MAX_Y - margin, y))


class CourseBuilder:
    """Lay out one course from its spec (seeded, so tests are repeatable)."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def build(self, spec: CourseSpec, *, assist: bool = False) -> FlightCourse:
        rng = self._rng
        half_open = min(MAX_HALF_OPEN, spec.ring_half_open * (1.2 if assist else 1.0))
        pickups: list[Pickup] = []
        rings: list[Ring] = []
        clouds: list[Cloud] = []
        # A short welcome trail along the gentle glide path: even a child who
        # has not touched anything yet flies into the first stars.
        for i in range(5):
            x = 380.0 + i * STAR_STEP
            pickups.append(Pickup(x, _clamp_y(CENTER_Y + GLIDE_SINK * x / spec.speed * 0.9, 10.0)))
        x = START_GAP
        prev_y = CENTER_Y
        side = rng.choice((-1.0, 1.0))
        for k in range(spec.rings):
            ring_x = x + spec.segment
            swing = spec.altitude_swing * rng.uniform(0.6, 1.0)
            ring_y = _clamp_y(CENTER_Y + side * swing, 30.0)
            side = -side
            trail_y = _clamp_y(rng.uniform(CENTER_Y - spec.altitude_swing, CENTER_Y + spec.altitude_swing), 20.0)
            self._segment(spec, x, ring_x, prev_y, trail_y, ring_y, pickups, clouds)
            rings.append(Ring(k, ring_x, ring_y, half_open))
            prev_y = ring_y
            x = ring_x
        # Final trail to the finish rainbow.
        for i in range(6):
            t = i / 5.0
            pickups.append(Pickup(x + 220.0 + i * STAR_STEP, prev_y + (CENTER_Y - prev_y) * t))
        pickups.sort(key=lambda p: p.x)
        return FlightCourse(spec, pickups, rings, clouds, x + FINISH_GAP)

    def _segment(
        self,
        spec: CourseSpec,
        start: float,
        ring_x: float,
        prev_y: float,
        trail_y: float,
        ring_y: float,
        pickups: list[Pickup],
        clouds: list[Cloud],
    ) -> None:
        rng = self._rng
        pattern = rng.choice(("line", "wave", "arc", "steps"))
        group_a = start + 200.0
        lead = ring_x - 420.0
        group_b = group_a + (lead - group_a) * 0.55
        # Group A eases from the previous ring's height to the trail height.
        for i in range(5):
            t = i / 4.0
            base = prev_y + (trail_y - prev_y) * t
            pickups.append(Pickup(group_a + i * STAR_STEP, _clamp_y(base + _pattern(pattern, t, 50.0), 10.0)))
        lo, hi = spec.clouds_per_segment
        cloud_count = rng.randint(lo, hi)
        gap_x = (group_a + 5 * STAR_STEP + group_b) / 2.0
        gem_done = False
        if cloud_count >= 1:
            # A cloud sits on the trail: go over or under it (a gem rewards one way).
            cloud = Cloud(gap_x, _clamp_y(trail_y, 40.0))
            clouds.append(cloud)
            if spec.gems:
                gem_side = -1.0 if cloud.y > CENTER_Y else 1.0
                pickups.append(Pickup(gap_x, _clamp_y(cloud.y + gem_side * 100.0, 8.0), PickupKind.GEM))
                gem_done = True
        if cloud_count >= 2:
            far_y = _clamp_y(ring_y + (110.0 if ring_y < CENTER_Y else -110.0), 40.0)
            clouds.append(Cloud(lead - 140.0, far_y))
        for i in range(5):
            t = i / 4.0
            pickups.append(Pickup(group_b + i * STAR_STEP, _clamp_y(trail_y + _pattern(pattern, 1.0 - t, 40.0), 10.0)))
        if spec.gems and not gem_done:
            high = trail_y > CENTER_Y
            pickups.append(Pickup(group_b + 2 * STAR_STEP, _clamp_y(trail_y + (-120.0 if high else 120.0), 8.0), PickupKind.GEM))
        # Lead-in: stars that point straight into the ring.
        for i in range(4):
            t = (i + 1) / 4.0
            pickups.append(Pickup(lead + i * 100.0, trail_y + (ring_y - trail_y) * t))


def _pattern(pattern: str, t: float, amplitude: float) -> float:
    if pattern == "wave":
        return math.sin(t * math.pi * 2.0) * amplitude
    if pattern == "arc":
        return -math.sin(t * math.pi) * amplitude
    if pattern == "steps":
        return -amplitude * 0.8 if t < 0.5 else amplitude * 0.4
    return 0.0


@dataclass
class FlightRun:
    """State of one flight along a course; ``update`` returns what happened."""

    course: FlightCourse
    flier: DragonFlier = field(default_factory=DragonFlier)
    distance: float = 0.0
    time: float = 0.0
    phase: FlightPhase = FlightPhase.FLYING
    stars: int = 0
    gems: int = 0
    rings_passed: int = 0
    misses: int = 0
    finish_time: float = -1.0
    _halfway_sent: bool = False

    @property
    def spec(self) -> CourseSpec:
        return self.course.spec

    @property
    def next_ring(self) -> Ring | None:
        for ring in self.course.rings:
            if ring.state is RingState.WAITING:
                return ring
        return None

    @property
    def result(self) -> FlightResult:
        return FlightResult(
            self.spec.course_id,
            self.stars,
            self.course.stars_total,
            self.gems,
            self.course.gems_total,
            self.misses,
        )

    def screen_x(self, world_x: float) -> float:
        return world_x - self.distance + DRAGON_SCREEN_X

    def flap(self) -> bool:
        if self.phase is not FlightPhase.FLYING:
            return False
        self.flier.flap()
        return True

    def update(self, dt: float, steer: FlightInput | None = None) -> list[FlightEvent]:
        dt = max(0.0, min(0.1, dt))
        self.time += dt
        events: list[FlightEvent] = []
        if self.phase is FlightPhase.DONE:
            return events
        steer = steer if steer is not None else FlightInput()
        if self.phase is FlightPhase.FINISHING:
            # Hands off: the dragon glides to the middle and slows down.
            steer = FlightInput(drag_y=CENTER_Y - 30.0)
            factor = max(0.25, 1.0 - (self.time - self.finish_time) / FINISH_SECONDS)
        else:
            factor = self.flier.speed_factor(steer.horizontal)
        before = self.distance
        self.flier.update(dt, steer)
        self.distance += self.spec.speed * factor * dt
        if self.phase is FlightPhase.FINISHING:
            if self.time - self.finish_time >= FINISH_SECONDS:
                self.phase = FlightPhase.DONE
                events.append(FlightEvent(FlightEventKind.DONE, self.distance, self.flier.y))
            return events
        self._collect(events)
        self._clouds(events)
        self._rings(before, events)
        if self.distance >= self.course.finish_x and self.next_ring is None:
            self.phase = FlightPhase.FINISHING
            self.finish_time = self.time
            events.append(FlightEvent(FlightEventKind.FINISH, self.distance, self.flier.y))
        return events

    # -- collisions ----------------------------------------------------------

    def _collect(self, events: list[FlightEvent]) -> None:
        dx_limit = DRAGON_RADIUS + GEM_REACH
        y = self.flier.y
        for pickup in self.course.pickups:
            if pickup.x < self.distance - dx_limit:
                continue
            if pickup.x > self.distance + dx_limit:
                break
            if pickup.taken:
                continue
            reach = DRAGON_RADIUS + (GEM_REACH if pickup.kind is PickupKind.GEM else PICKUP_REACH)
            if (pickup.x - self.distance) ** 2 + (pickup.y - y) ** 2 <= reach * reach:
                pickup.taken = True
                if pickup.kind is PickupKind.GEM:
                    self.gems += 1
                    events.append(FlightEvent(FlightEventKind.GEM, pickup.x, pickup.y))
                else:
                    self.stars += 1
                    events.append(FlightEvent(FlightEventKind.STAR, pickup.x, pickup.y))

    def _clouds(self, events: list[FlightEvent]) -> None:
        y = self.flier.y
        for cloud in self.course.clouds:
            dx = (self.distance - cloud.x) / (cloud.half_w + DRAGON_RADIUS * 0.5)
            if abs(dx) >= 1.0:
                continue
            dy = (y - cloud.y) / (cloud.half_h + DRAGON_RADIUS * 0.5)
            if dx * dx + dy * dy >= 1.0 or self.time - cloud.bumped_at < BUMP_COOLDOWN:
                continue
            cloud.bumped_at = self.time
            direction = -1.0 if y < cloud.y else 1.0
            if (direction < 0 and y <= MIN_Y + 4) or (direction > 0 and y >= MAX_Y - 4):
                direction = -direction
            self.flier.bump(direction)
            events.append(FlightEvent(FlightEventKind.BUMP, cloud.x, cloud.y))

    def _rings(self, before: float, events: list[FlightEvent]) -> None:
        for ring in self.course.rings:
            if ring.state is not RingState.WAITING or not before < ring.x <= self.distance:
                continue
            if abs(self.flier.y - ring.y) <= ring.half_open:
                ring.state = RingState.PASSED
                self.rings_passed += 1
                events.append(FlightEvent(FlightEventKind.RING_PASSED, ring.x, ring.y, ring.checkpoint))
                if not self._halfway_sent and self.rings_passed == (len(self.course.rings) + 1) // 2:
                    self._halfway_sent = True
                    events.append(FlightEvent(FlightEventKind.HALFWAY, ring.x, ring.y, ring.checkpoint))
            else:
                self.misses += 1
                events.append(FlightEvent(FlightEventKind.RING_MISSED, ring.x, ring.y, ring.checkpoint))
                self._retry(ring)
            break

    def _retry(self, ring: Ring) -> None:
        """Move a missed ring ahead, nearer the dragon, a little wider."""

        old_x, old_y = ring.x, ring.y
        ring.retries += 1
        target = self.flier.y if ring.retries >= 2 else (ring.y + self.flier.y) / 2.0
        course = self.course
        for pickup in course.pickups:
            if pickup.x > old_x:
                pickup.x += RETRY_GAP
        for cloud in course.clouds:
            if cloud.x > old_x:
                cloud.x += RETRY_GAP
        for other in course.rings:
            if other is not ring and other.x > old_x:
                other.x += RETRY_GAP
        course.finish_x += RETRY_GAP
        ring.x = old_x + RETRY_GAP
        ring.y = _clamp_y(target, 30.0)
        ring.half_open = min(MAX_HALF_OPEN, ring.half_open * 1.2)
        ring.moved_from = (old_x, old_y)
        ring.moved_at = self.time
        # A short star trail shows the way into the ring (the "demonstration").
        start_y = self.flier.y
        for i in range(4):
            t = (i + 1) / 5.0
            course.pickups.append(
                Pickup(old_x + RETRY_GAP * (0.3 + 0.12 * i), start_y + (ring.y - start_y) * t)
            )
        course.pickups.sort(key=lambda p: p.x)


__all__ = [
    "CENTER_Y",
    "Cloud",
    "CourseBuilder",
    "DRAGON_RADIUS",
    "DRAGON_SCREEN_X",
    "DragonFlier",
    "FlightCourse",
    "FlightEvent",
    "FlightEventKind",
    "FlightInput",
    "FlightPhase",
    "FlightResult",
    "FlightRun",
    "MAX_Y",
    "MIN_Y",
    "Pickup",
    "PickupKind",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "RING_MOVE_SECONDS",
    "Ring",
    "RingState",
]
