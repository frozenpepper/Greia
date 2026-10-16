"""Pure garden rules for La Corsa delle Bacche (Momo's berry chase).

No Pygame here: layouts, Momo's walking, the friendly critters, gentle
bumps, the adaptive ladder and the visit are plain Python so they can be
tested exhaustively.

Coordinates are cells ``(row, col)``; positions between cells are floats
in the same units. Walking is continuous (a ``Walker`` moves from one cell
centre to the next), so this is a real-time action game -- but never a
scary one:

* Momo walks along a corridor by himself, follows bends and stops at a
  junction unless a direction is held; a tap on the garden plans the
  shortest path there (BFS);
* walking *into* an awake critter is a gentle bump: Momo bounces back to
  the cell he came from (nothing is lost, there are no lives); a critter
  that walks into a Momo who is standing still or walking away simply
  turns around -- standing still is always safe;
* a planned (tapped) path stops in front of an awake critter instead of
  walking into it (Momo waits; the child taps again when the way is clear);
* a sleeping hedgehog (eyes closed) can be passed safely.

The next garden's rung adapts to how the last one went (bumps, hints).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
import math
import random
from typing import Final

if __package__:
    from .corsa_content import (
        CRITTER_CHARS,
        GARDENS_PER_VISIT,
        MAX_LEVEL,
        MIN_LEVEL,
        CritterKind,
        CritterSpec,
        RungSpec,
        clamp_level,
        rung_spec,
    )
else:
    from corsa_content import (
        CRITTER_CHARS,
        GARDENS_PER_VISIT,
        MAX_LEVEL,
        MIN_LEVEL,
        CritterKind,
        CritterSpec,
        RungSpec,
        clamp_level,
        rung_spec,
    )

Cell = tuple[int, int]
Direction = tuple[int, int]

UP: Final[Direction] = (-1, 0)
DOWN: Final[Direction] = (1, 0)
LEFT: Final[Direction] = (0, -1)
RIGHT: Final[Direction] = (0, 1)
DIRECTIONS: Final[tuple[Direction, ...]] = (UP, DOWN, LEFT, RIGHT)

CONTACT_DISTANCE: Final = 0.62  # cells between centres that count as touching
BUMP_GRACE_SECONDS: Final = 1.6
BOUNCE_BOOST: Final = 2.2
CRITTER_BUMP_PAUSE: Final = 1.2
CRITTER_TURN_PAUSE: Final = 0.5
CRITTER_COOLDOWN: Final = 1.2
CRITTER_START_PAUSE: Final = 1.2
WAIT_DISTANCE: Final = 1.05  # an awake critter this close to the next cell blocks a tapped path


def opposite(direction: Direction | None) -> Direction | None:
    if direction is None:
        return None
    return (-direction[0], -direction[1])


def step(cell: Cell, direction: Direction) -> Cell:
    return (cell[0] + direction[0], cell[1] + direction[1])


def direction_between(a: Cell, b: Cell) -> Direction:
    return (b[0] - a[0], b[1] - a[1])


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GardenLayout:
    """One authored garden: hedges, Momo's start, berries and critter starts."""

    level: int
    lattice: tuple[str, ...]
    start: Cell
    berries: tuple[Cell, ...]
    critters: tuple[tuple[CritterKind, Cell], ...] = ()

    @classmethod
    def parse(cls, level: int, lattice: Sequence[str]) -> "GardenLayout":
        rows = tuple(lattice)
        if len(rows) < 3 or len(rows) % 2 == 0:
            raise ValueError("lattice must have an odd number (>= 3) of rows")
        width = len(rows[0])
        if width < 3 or width % 2 == 0 or any(len(row) != width for row in rows):
            raise ValueError("lattice rows must share one odd width")
        start: Cell | None = None
        berries: list[Cell] = []
        critters: list[tuple[CritterKind, Cell]] = []
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                border = r in (0, len(rows) - 1) or c in (0, width - 1)
                if (border or (r % 2 == 0 and c % 2 == 0)) and ch != "#":
                    raise ValueError(f"lattice ({r},{c}) must be a hedge")
                if r % 2 == 1 and c % 2 == 1:
                    cell = (r // 2, c // 2)
                    if ch == "M":
                        if start is not None:
                            raise ValueError("lattice has two starts")
                        start = cell
                    elif ch == ".":
                        berries.append(cell)
                    elif ch in CRITTER_CHARS:
                        critters.append((CRITTER_CHARS[ch], cell))
                    elif ch != " ":
                        raise ValueError(f"unknown cell mark {ch!r}")
                elif ch not in "# ":
                    raise ValueError(f"unknown hedge mark {ch!r} at ({r},{c})")
        if start is None:
            raise ValueError("lattice has no start")
        return cls(level, rows, start, tuple(berries), tuple(critters))

    @property
    def rows(self) -> int:
        return len(self.lattice) // 2

    @property
    def cols(self) -> int:
        return len(self.lattice[0]) // 2

    def inside(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.rows and 0 <= cell[1] < self.cols

    def is_open(self, cell: Cell, direction: Direction) -> bool:
        """True when Momo can step from ``cell`` towards ``direction``."""

        if not self.inside(cell) or not self.inside(step(cell, direction)):
            return False
        r, c = cell
        return self.lattice[2 * r + 1 + direction[0]][2 * c + 1 + direction[1]] != "#"

    def open_directions(self, cell: Cell) -> list[Direction]:
        return [d for d in DIRECTIONS if self.is_open(cell, d)]

    def neighbours(self, cell: Cell, blocked: Collection[Cell] = ()) -> list[Cell]:
        result = []
        for direction in DIRECTIONS:
            if self.is_open(cell, direction):
                nxt = step(cell, direction)
                if nxt not in blocked:
                    result.append(nxt)
        return result

    def cells(self) -> Iterable[Cell]:
        for r in range(self.rows):
            for c in range(self.cols):
                yield (r, c)

    def mirrored(self, horizontal: bool, vertical: bool) -> "GardenLayout":
        rows = list(self.lattice)
        if vertical:
            rows.reverse()
        if horizontal:
            rows = [row[::-1] for row in rows]
        return GardenLayout.parse(self.level, rows)


def bfs_path(layout: GardenLayout, start: Cell, goal: Cell, blocked: Collection[Cell] = ()) -> list[Cell]:
    """Shortest route from ``start`` to ``goal`` (both inclusive), or ``[]``."""

    if start == goal:
        return [start]
    parent: dict[Cell, Cell | None] = {start: None}
    queue: deque[Cell] = deque([start])
    while queue:
        current = queue.popleft()
        for nxt in layout.neighbours(current, blocked):
            if nxt in parent:
                continue
            parent[nxt] = current
            if nxt == goal:
                path = [nxt]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])  # type: ignore[arg-type]
                path.reverse()
                return path
            queue.append(nxt)
    return []


def distances(layout: GardenLayout, start: Cell) -> dict[Cell, int]:
    seen = {start: 0}
    queue: deque[Cell] = deque([start])
    while queue:
        current = queue.popleft()
        for nxt in layout.neighbours(current):
            if nxt not in seen:
                seen[nxt] = seen[current] + 1
                queue.append(nxt)
    return seen


# --------------------------------------------------------------------------
# Walking
# --------------------------------------------------------------------------


@dataclass(slots=True)
class Walker:
    """Continuous cell-to-cell movement (Momo and the critters)."""

    cell: Cell
    speed: float = 2.6  # cells per second
    target: Cell | None = None
    t: float = 0.0
    boost: float = 1.0

    @property
    def moving(self) -> bool:
        return self.target is not None

    @property
    def heading(self) -> Direction | None:
        return direction_between(self.cell, self.target) if self.target is not None else None

    @property
    def resting_cell(self) -> Cell:
        """Where the walker will stand next (its target while moving)."""

        return self.target if self.target is not None else self.cell

    def position(self) -> tuple[float, float]:
        if self.target is None:
            return (float(self.cell[0]), float(self.cell[1]))
        return (
            self.cell[0] + (self.target[0] - self.cell[0]) * self.t,
            self.cell[1] + (self.target[1] - self.cell[1]) * self.t,
        )

    def start(self, target: Cell) -> None:
        self.target = target
        self.t = 0.0

    def reverse(self) -> None:
        if self.target is not None:
            self.cell, self.target = self.target, self.cell
            self.t = 1.0 - self.t

    def halt(self) -> None:
        """Stop at the current cell (only called between steps)."""

        self.target = None
        self.t = 0.0
        self.boost = 1.0

    def advance(self, dt: float) -> float | None:
        """Move on; return the leftover seconds when a cell is reached, else None."""

        if self.target is None or dt <= 0:
            return None
        rate = self.speed * self.boost
        self.t += dt * rate
        if self.t < 1.0:
            return None
        leftover = (self.t - 1.0) / rate
        self.cell = self.target
        self.target = None
        self.t = 0.0
        return leftover


@dataclass(slots=True)
class Critter:
    """One friendly garden critter wandering the paths."""

    spec: CritterSpec
    walker: Walker
    heading: Direction = RIGHT
    asleep: bool = False
    timer: float = 0.0  # seconds until it naps (awake) or wakes (asleep)
    pause: float = 0.0
    cooldown: float = 0.0
    wants_nap: bool = False

    @property
    def kind(self) -> CritterKind:
        return self.spec.kind

    @property
    def naps(self) -> bool:
        return self.spec.awake_seconds > 0 and self.spec.nap_seconds > 0

    @property
    def awake(self) -> bool:
        return not self.asleep

    def position(self) -> tuple[float, float]:
        return self.walker.position()

    def occupies(self) -> set[Cell]:
        cells = {self.walker.cell}
        if self.walker.target is not None:
            cells.add(self.walker.target)
        return cells


# --------------------------------------------------------------------------
# One garden
# --------------------------------------------------------------------------


class GardenEventKind(StrEnum):
    BERRY = "berry"  # a berry went into the basket
    CLEARED = "cleared"  # the last berry: the garden is done
    BUMP = "bump"  # Momo walked into an awake critter and bounced back
    WAIT = "wait"  # a tapped path stopped in front of an awake critter
    BOOP = "boop"  # a critter met a still Momo and turned around
    NAP = "nap"
    WAKE = "wake"


@dataclass(frozen=True, slots=True)
class GardenEvent:
    kind: GardenEventKind
    cell: Cell
    critter: int = -1


class StepResult(StrEnum):
    MOVED = "moved"
    QUEUED = "queued"
    BLOCKED = "blocked"  # a hedge in that direction
    IGNORED = "ignored"


@dataclass(slots=True)
class GardenSummary:
    """How one garden went (drives the next rung; never shown as a score)."""

    level: int
    berries: int = 0
    bumps: int = 0
    hints: int = 0
    waits: int = 0
    walls: int = 0

    @property
    def clean(self) -> bool:
        return self.bumps <= 1 and self.hints == 0

    @property
    def struggled(self) -> bool:
        return self.bumps >= 4 or self.hints >= 2


def next_level(level: int, summary: GardenSummary) -> int:
    if summary.clean:
        return clamp_level(level + 1)
    if summary.struggled:
        return clamp_level(level - 1)
    return clamp_level(level)


class Garden:
    """Momo, the berries and the critters of one garden."""

    def __init__(self, layout: GardenLayout, spec: RungSpec, rng: random.Random | None = None) -> None:
        self.layout = layout
        self.spec = spec
        self.rng = rng if rng is not None else random.Random()
        self.momo = Walker(layout.start, speed=spec.momo_speed)
        self.remaining: list[Cell] = list(layout.berries)
        self.basket: list[Cell] = []  # berries in the order Momo picked them
        self.summary = GardenSummary(layout.level)
        self.cleared = False
        self.bouncing = False
        self.grace = 0.0
        self.critters: list[Critter] = []
        for index, (kind, cell) in enumerate(layout.critters):
            critter_spec = next((s for s in spec.critters if s.kind is kind), None)
            if critter_spec is None:
                continue
            critter = Critter(critter_spec, Walker(cell, speed=critter_spec.speed))
            critter.pause = CRITTER_START_PAUSE + 0.4 * index
            if critter.naps:
                # Hedgehogs start the garden asleep: a calm first look.
                critter.asleep = True
                critter.timer = critter_spec.nap_seconds
            self.critters.append(critter)
        self._path: deque[Cell] = deque()
        self._queued: Direction | None = None
        self._held: Direction | None = None
        self._auto = False
        self._stop = False
        self._last_heading: Direction | None = None

    # -- queries -----------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self.layout.berries)

    @property
    def collected(self) -> int:
        return self.total - len(self.remaining)

    @property
    def path(self) -> tuple[Cell, ...]:
        return tuple(self._path)

    @property
    def queued(self) -> Direction | None:
        return self._queued

    @property
    def held(self) -> Direction | None:
        return self._held

    def awake_critters(self) -> list[int]:
        return [index for index, critter in enumerate(self.critters) if critter.awake]

    def critter_near(self, cell: Cell, distance: float = WAIT_DISTANCE) -> int | None:
        """An awake critter on, heading to, or right next to ``cell``."""

        for index, critter in enumerate(self.critters):
            if critter.asleep:
                continue
            if cell in critter.occupies():
                return index
            r, c = critter.position()
            if math.hypot(r - cell[0], c - cell[1]) < distance:
                return index
        return None

    def next_berry(self) -> Cell | None:
        """The nearest remaining berry by walking distance."""

        if not self.remaining:
            return None
        dist = distances(self.layout, self.momo.resting_cell)
        return min(self.remaining, key=lambda cell: (dist.get(cell, 999), cell))

    def hint_route(self, *, avoid_critters: bool = False) -> list[Cell]:
        """Route to the nearest berry (around awake critters when asked and possible)."""

        target = self.next_berry()
        if target is None:
            return []
        origin = self.momo.resting_cell
        if avoid_critters:
            blocked = set()
            for index in self.awake_critters():
                blocked |= self.critters[index].occupies()
            blocked.discard(origin)
            blocked.discard(target)
            route = bfs_path(self.layout, origin, target, blocked)
            if route:
                return route
        return bfs_path(self.layout, origin, target)

    # -- steering ----------------------------------------------------------

    def steer(self, direction: Direction) -> StepResult:
        """Arrow / D-pad / stick press: walk, turn around, or queue a turn."""

        if self.cleared or self.bouncing or direction not in DIRECTIONS:
            return StepResult.IGNORED
        self._path.clear()
        self._stop = False
        momo = self.momo
        if momo.moving:
            heading = momo.heading
            if direction == opposite(heading):
                momo.reverse()
                self._last_heading = direction
                self._queued = None
                self._auto = True
                return StepResult.MOVED
            if direction == heading:
                self._queued = None
                self._auto = True
                return StepResult.MOVED
            self._queued = direction
            self._auto = True
            return StepResult.QUEUED
        if self.layout.is_open(momo.cell, direction):
            self._step_to(step(momo.cell, direction))
            self._auto = True
            self._queued = None
            return StepResult.MOVED
        self.summary.walls += 1
        return StepResult.BLOCKED

    def hold(self, direction: Direction | None) -> None:
        """A direction is held (or released with ``None``).

        While held, Momo keeps walking that way through junctions; the press
        itself is delivered through ``steer``.
        """

        self._held = direction if direction in DIRECTIONS else None

    def go_to(self, cell: Cell) -> bool:
        """Tap-to-go: plan the shortest path to ``cell`` and walk it."""

        if self.cleared or self.bouncing or not self.layout.inside(cell):
            return False
        origin = self.momo.resting_cell
        route = bfs_path(self.layout, origin, cell)
        if not route:
            return False
        self._queued = None
        self._auto = False
        self._stop = False
        self._path = deque(route[1:])
        return True

    def stop(self) -> bool:
        """Space / south button: stop at the next cell and wait."""

        self._path.clear()
        self._queued = None
        self._auto = False
        if self.momo.moving and not self.bouncing:
            self._stop = True
            return True
        return False

    def _step_to(self, cell: Cell) -> None:
        self._last_heading = direction_between(self.momo.cell, cell)
        self.momo.start(cell)

    # -- simulation ---------------------------------------------------------

    def update(self, dt: float) -> list[GardenEvent]:
        events: list[GardenEvent] = []
        if self.cleared or dt <= 0:
            return events
        self.grace = max(0.0, self.grace - dt)
        momo = self.momo
        if not momo.moving:
            self._choose_next(events)
        remaining = dt
        for _ in range(4):
            if not momo.moving:
                break
            leftover = momo.advance(remaining)
            if leftover is None:
                break
            if self.bouncing:
                self.bouncing = False
                momo.halt()
                break
            self._arrive(events)
            if self.cleared:
                break
            self._choose_next(events)
            remaining = leftover
        if not self.cleared:
            for index, critter in enumerate(self.critters):
                self._update_critter(index, critter, dt, events)
            self._contacts(events)
        return events

    def _choose_next(self, events: list[GardenEvent]) -> None:
        momo = self.momo
        if momo.moving or self.bouncing or self.cleared:
            return
        here = momo.cell
        if self._stop:
            self._stop = False
            self._auto = False
            return
        if self._path:
            nxt = self._path[0]
            blocker = self.critter_near(nxt)
            if blocker is not None:
                self._path.clear()
                self.summary.waits += 1
                events.append(GardenEvent(GardenEventKind.WAIT, here, blocker))
                return
            self._path.popleft()
            self._step_to(nxt)
            return
        if self._queued is not None and self.layout.is_open(here, self._queued):
            direction, self._queued = self._queued, None
            self._auto = True
            self._step_to(step(here, direction))
            return
        if self._held is not None and self.layout.is_open(here, self._held):
            self._auto = True
            self._step_to(step(here, self._held))
            return
        heading = self._last_heading
        if not self._auto or heading is None:
            return
        onward = [d for d in self.layout.open_directions(here) if d != opposite(heading)]
        if heading in onward and len(onward) == 1:
            self._step_to(step(here, heading))  # straight corridor
            return
        if heading not in onward and len(onward) == 1:
            self._step_to(step(here, onward[0]))  # follow the bend
            return
        # A junction (or a dead end): stop and let the child choose.
        self._auto = False
        self._queued = None

    def _arrive(self, events: list[GardenEvent]) -> None:
        cell = self.momo.cell
        if cell in self.remaining:
            self.remaining.remove(cell)
            self.basket.append(cell)
            self.summary.berries += 1
            events.append(GardenEvent(GardenEventKind.BERRY, cell))
            if not self.remaining:
                self.cleared = True
                self._path.clear()
                self._queued = None
                self._auto = False
                self.momo.halt()
                events.append(GardenEvent(GardenEventKind.CLEARED, cell))

    def _update_critter(self, index: int, critter: Critter, dt: float, events: list[GardenEvent]) -> None:
        critter.cooldown = max(0.0, critter.cooldown - dt)
        if critter.naps:
            critter.timer -= dt
            if critter.asleep and critter.timer <= 0:
                critter.asleep = False
                critter.timer = critter.spec.awake_seconds
                critter.pause = max(critter.pause, 0.4)
                events.append(GardenEvent(GardenEventKind.WAKE, critter.walker.cell, index))
            elif critter.awake and critter.timer <= 0:
                critter.wants_nap = True
        if critter.asleep:
            return
        if critter.pause > 0:
            critter.pause = max(0.0, critter.pause - dt)
            return
        remaining = dt
        for _ in range(3):
            if not critter.walker.moving:
                if critter.wants_nap:
                    critter.wants_nap = False
                    critter.asleep = True
                    critter.timer = critter.spec.nap_seconds
                    events.append(GardenEvent(GardenEventKind.NAP, critter.walker.cell, index))
                    return
                nxt = self._critter_choice(index, critter)
                if nxt is None:
                    critter.pause = 0.5
                    return
                critter.heading = direction_between(critter.walker.cell, nxt)
                critter.walker.start(nxt)
            leftover = critter.walker.advance(remaining)
            if leftover is None:
                return
            remaining = leftover

    def _critter_choice(self, index: int, critter: Critter) -> Cell | None:
        here = critter.walker.cell
        blocked: set[Cell] = set()
        for other_index, other in enumerate(self.critters):
            if other_index != index:
                blocked |= other.occupies()
        if not self.momo.moving:
            blocked.add(self.momo.cell)  # never walk into a Momo who is standing still
        options = self.layout.neighbours(here, blocked)
        if not options:
            return None
        back = step(here, opposite(critter.heading) or (0, 0))
        forward = [cell for cell in options if cell != back]
        pool = forward or options
        rng = self.rng
        if critter.spec.follow > 0 and rng.random() < critter.spec.follow:
            dist = distances(self.layout, self.momo.resting_cell)
            return min(pool, key=lambda cell: (dist.get(cell, 999), cell))
        straight = step(here, critter.heading)
        if straight in pool and rng.random() < 0.65:
            return straight
        return rng.choice(pool)

    def _contacts(self, events: list[GardenEvent]) -> None:
        momo = self.momo
        mr, mc = momo.position()
        for index, critter in enumerate(self.critters):
            if critter.asleep or critter.cooldown > 0:
                continue
            cr, cc = critter.position()
            if math.hypot(cr - mr, cc - mc) >= CONTACT_DISTANCE:
                continue
            heading = momo.heading
            towards = heading is not None and ((cr - mr) * heading[0] + (cc - mc) * heading[1]) > 0.05
            if towards and not self.bouncing and self.grace <= 0:
                self._bump(index, critter, events)
                return
            c_heading = critter.heading if critter.walker.moving else None
            if c_heading is not None and ((mr - cr) * c_heading[0] + (mc - cc) * c_heading[1]) > 0.05:
                critter.walker.reverse()
                critter.heading = opposite(c_heading) or critter.heading
                critter.pause = CRITTER_TURN_PAUSE
                critter.cooldown = CRITTER_COOLDOWN
                events.append(GardenEvent(GardenEventKind.BOOP, critter.walker.resting_cell, index))

    def _bump(self, index: int, critter: Critter, events: list[GardenEvent]) -> None:
        """Gentle bump: Momo bounces back to the cell he came from; nothing is lost."""

        momo = self.momo
        self.summary.bumps += 1
        momo.reverse()
        momo.boost = BOUNCE_BOOST
        self.bouncing = True
        self.grace = BUMP_GRACE_SECONDS
        self._path.clear()
        self._queued = None
        self._auto = False
        self._stop = False
        if critter.walker.moving:
            critter.walker.reverse()
            critter.heading = opposite(critter.heading) or critter.heading
        critter.pause = CRITTER_BUMP_PAUSE
        critter.cooldown = BUMP_GRACE_SECONDS
        events.append(GardenEvent(GardenEventKind.BUMP, momo.resting_cell, index))


# --------------------------------------------------------------------------
# Progress + visit
# --------------------------------------------------------------------------


@dataclass(slots=True)
class CorsaProgress:
    """Profile-scoped progress (see ``corsa_services``)."""

    level: int = MIN_LEVEL
    gardens_cleared: int = 0
    visits_completed: int = 0
    berries: int = 0


@dataclass(slots=True)
class Visit:
    """One sitting: ``GARDENS_PER_VISIT`` gardens, then the completion scene."""

    progress: CorsaProgress
    rng: random.Random = field(default_factory=random.Random)
    total: int = GARDENS_PER_VISIT
    completed: int = 0
    garden: Garden = field(init=False)
    _last_variant: tuple[int, bool, bool] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.progress.level = clamp_level(self.progress.level)
        self.garden = self._new_garden()

    @property
    def complete(self) -> bool:
        return self.completed >= self.total

    def _new_garden(self) -> Garden:
        spec = rung_spec(self.progress.level)
        variants = [(spec.level, h, v) for h in (False, True) for v in (False, True)]
        if self._last_variant in variants and len(variants) > 1:
            variants.remove(self._last_variant)
        choice = self.rng.choice(variants)
        self._last_variant = choice
        layout = GardenLayout.parse(spec.level, spec.lattice).mirrored(choice[1], choice[2])
        return Garden(layout, spec, self.rng)

    def finish_garden(self) -> GardenSummary:
        summary = self.garden.summary
        self.completed += 1
        self.progress.gardens_cleared += 1
        self.progress.berries += summary.berries
        self.progress.level = next_level(self.progress.level, summary)
        return summary

    def next_garden(self) -> None:
        self.garden = self._new_garden()

    def finish_visit(self) -> None:
        self.progress.visits_completed += 1

    def restart(self) -> None:
        self.completed = 0
        self.garden = self._new_garden()


__all__ = [
    "BUMP_GRACE_SECONDS",
    "CONTACT_DISTANCE",
    "DIRECTIONS",
    "DOWN",
    "GARDENS_PER_VISIT",
    "LEFT",
    "MAX_LEVEL",
    "MIN_LEVEL",
    "RIGHT",
    "UP",
    "Cell",
    "CorsaProgress",
    "Critter",
    "Direction",
    "Garden",
    "GardenEvent",
    "GardenEventKind",
    "GardenLayout",
    "GardenSummary",
    "StepResult",
    "Visit",
    "Walker",
    "bfs_path",
    "distances",
    "next_level",
    "opposite",
]
