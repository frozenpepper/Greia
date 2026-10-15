"""Tito's Marble Run — deterministic fixed-step marble physics (no Pygame).

One run = one marble rolling through the board's colliders (frame walls,
fixed shelves, the basket and the child's placed pieces). Every collider is a
``Capsule`` (a thick segment, or a circle), so ramps, funnels, bumpers,
shelves and the basket share one contact rule:

* push the marble out along the contact normal;
* fast impacts bounce with the collider's restitution, slow ones just stop the
  normal motion, so the marble settles and *rolls* along a plank (gravity's
  component along the plank does the rest);
* while touching anything the marble loses a little speed (rolling drag).

The integrator runs at a fixed ``STEP_SECONDS`` with an accumulator and a
per-frame step cap, so a run is identical on a fast desktop and on the Acer
floor, and tests replay it exactly. Every run ends: basket, off the open
bottom of the board, at rest, or at the hard time cap (no soft-lock).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Final

if __package__:
    from .ramp_content import (
        AIR_DRAG,
        BOARD_HEIGHT,
        BOARD_WIDTH,
        BOUNCE_MIN,
        GRAVITY,
        HIT_SOUND_MIN,
        MARBLE_RADIUS,
        MAX_RUN_SECONDS,
        MAX_SPEED,
        MAX_STEPS_PER_FRAME,
        PLANK_RADIUS,
        REST_RADIUS,
        REST_SECONDS,
        ROLL_DRAG,
        SHELF_RESTITUTION,
        STEP_SECONDS,
        Basket,
        Capsule,
        Shelf,
        Start,
        board_walls,
    )
else:
    from ramp_content import (
        AIR_DRAG,
        BOARD_HEIGHT,
        BOARD_WIDTH,
        BOUNCE_MIN,
        GRAVITY,
        HIT_SOUND_MIN,
        MARBLE_RADIUS,
        MAX_RUN_SECONDS,
        MAX_SPEED,
        MAX_STEPS_PER_FRAME,
        PLANK_RADIUS,
        REST_RADIUS,
        REST_SECONDS,
        ROLL_DRAG,
        SHELF_RESTITUTION,
        STEP_SECONDS,
        Basket,
        Capsule,
        Shelf,
        Start,
        board_walls,
    )

TRAIL_EVERY: Final = 3  # record a trail dot every N physics steps
TRAIL_LIMIT: Final = 240  # bounded trail (~6 s of dots)


class Outcome(StrEnum):
    BASKET = "basket"
    LOST = "lost"  # rolled off the open bottom of the board
    STOPPED = "stopped"  # came to rest (or hit the time cap) outside the basket


@dataclass(frozen=True, slots=True)
class Hit:
    """A fresh impact (for clack sounds and the bumper's squash)."""

    tag: str
    position: tuple[float, float]
    speed: float


@dataclass
class Marble:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    spin: float = 0.0  # rolled angle (radians), for the swirl on the marble


def _closest_on_segment(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 <= 1e-9:
        return ax, ay
    t = ((px - ax) * dx + (py - ay) * dy) / length2
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return ax + dx * t, ay + dy * t


def shelf_capsules(shelves: Iterable[Shelf]) -> tuple[Capsule, ...]:
    return tuple(Capsule(shelf.a, shelf.b, PLANK_RADIUS, SHELF_RESTITUTION, "shelf") for shelf in shelves)


@dataclass
class MarbleRun:
    """One deterministic run of the marble through a fixed set of colliders."""

    start: Start
    basket: Basket
    colliders: tuple[Capsule, ...]
    marble: Marble = field(init=False)
    elapsed: float = 0.0
    steps: int = 0
    outcome: Outcome | None = None
    trail: deque = field(default_factory=lambda: deque(maxlen=TRAIL_LIMIT))
    _accumulator: float = 0.0
    _rest_anchor: tuple[float, float] = (0.0, 0.0)
    _rest_time: float = 0.0
    _touching: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.colliders = (*board_walls(), *self.basket.capsules(), *self.colliders)
        self.marble = Marble(self.start.x, self.start.y, self.start.vx, 0.0)
        self._rest_anchor = (self.marble.x, self.marble.y)
        self.trail.append((self.marble.x, self.marble.y))

    @property
    def finished(self) -> bool:
        return self.outcome is not None

    # -- stepping -----------------------------------------------------------

    def advance(self, dt: float) -> list[Hit]:
        """Advance by a frame delta (fixed sub-steps, capped per frame)."""

        if self.finished:
            return []
        self._accumulator = min(self._accumulator + max(0.0, dt), STEP_SECONDS * MAX_STEPS_PER_FRAME)
        hits: list[Hit] = []
        while self._accumulator >= STEP_SECONDS and not self.finished:
            self._accumulator -= STEP_SECONDS
            hits.extend(self.step())
        return hits

    def run_to_end(self, max_steps: int = 0) -> Outcome:
        """Simulate the whole run (tests, the solver, hint planning)."""

        limit = max_steps or int(MAX_RUN_SECONDS / STEP_SECONDS) + 2
        for _ in range(limit):
            if self.finished:
                break
            self.step()
        if self.outcome is None:
            self.outcome = Outcome.STOPPED
        return self.outcome

    def step(self) -> list[Hit]:
        """One fixed physics step."""

        if self.finished:
            return []
        dt = STEP_SECONDS
        m = self.marble
        m.vy += GRAVITY * dt
        drag = 1.0 - AIR_DRAG * dt
        m.vx *= drag
        m.vy *= drag
        speed = math.hypot(m.vx, m.vy)
        if speed > MAX_SPEED:
            m.vx *= MAX_SPEED / speed
            m.vy *= MAX_SPEED / speed
        m.x += m.vx * dt
        m.y += m.vy * dt
        hits = self._collide(dt)
        m.spin += m.vx * dt / MARBLE_RADIUS
        self.elapsed += dt
        self.steps += 1
        if self.steps % TRAIL_EVERY == 0:
            self.trail.append((m.x, m.y))
        self._check_end(dt)
        return hits

    def _collide(self, dt: float) -> list[Hit]:
        m = self.marble
        hits: list[Hit] = []
        touching: set[str] = set()
        for capsule in self.colliders:
            reach = capsule.radius + MARBLE_RADIUS
            # Cheap bounding reject before the exact distance.
            if m.x < min(capsule.a[0], capsule.b[0]) - reach or m.x > max(capsule.a[0], capsule.b[0]) + reach:
                continue
            if m.y < min(capsule.a[1], capsule.b[1]) - reach or m.y > max(capsule.a[1], capsule.b[1]) + reach:
                continue
            px, py = _closest_on_segment(m.x, m.y, capsule.a, capsule.b)
            dx, dy = m.x - px, m.y - py
            dist2 = dx * dx + dy * dy
            if dist2 >= reach * reach:
                continue
            dist = math.sqrt(dist2)
            if dist < 1e-6:
                nx, ny = 0.0, -1.0
            else:
                nx, ny = dx / dist, dy / dist
            m.x += nx * (reach - dist)
            m.y += ny * (reach - dist)
            vn = m.vx * nx + m.vy * ny
            if vn < 0.0:
                bounce = capsule.restitution if -vn > BOUNCE_MIN else 0.0
                m.vx -= (1.0 + bounce) * vn * nx
                m.vy -= (1.0 + bounce) * vn * ny
                if -vn > HIT_SOUND_MIN and capsule.tag not in self._touching:
                    hits.append(Hit(capsule.tag, (px, py), -vn))
            touching.add(capsule.tag)
        if touching:
            roll = 1.0 - ROLL_DRAG * dt
            m.vx *= roll
            m.vy *= roll
        self._touching = touching
        return hits

    def _check_end(self, dt: float) -> None:
        m = self.marble
        if self.basket.holds(m.x, m.y):
            self.outcome = Outcome.BASKET
            return
        if m.y - MARBLE_RADIUS > BOARD_HEIGHT:
            self.outcome = Outcome.LOST
            return
        ax, ay = self._rest_anchor
        if (m.x - ax) ** 2 + (m.y - ay) ** 2 > REST_RADIUS * REST_RADIUS:
            self._rest_anchor = (m.x, m.y)
            self._rest_time = 0.0
        else:
            self._rest_time += dt
        if self._rest_time >= REST_SECONDS or self.elapsed >= MAX_RUN_SECONDS:
            self.outcome = Outcome.STOPPED

    # -- presentation helpers ------------------------------------------------

    def drawn_position(self) -> tuple[float, float]:
        """Marble centre clamped to the board (a lost marble never draws outside)."""

        m = self.marble
        r = MARBLE_RADIUS
        return (
            max(r, min(BOARD_WIDTH - r, m.x)),
            max(r, min(BOARD_HEIGHT - r, m.y)),
        )


__all__ = ["Hit", "Marble", "MarbleRun", "Outcome", "TRAIL_LIMIT", "shelf_capsules"]
