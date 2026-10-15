"""Pure maze rules for Il Labirinto Magico (Tito's hedge maze).

No Pygame here: generation, movement, pickups, hints and the adaptive visit
ladder are plain Python so they can be tested exhaustively.

Grid convention: ``grid[r][c]`` is ``OPEN`` (0) or ``WALL`` (1) on a
``(2 * rows + 1) x (2 * cols + 1)`` lattice. Maze *cells* sit on odd/odd
coordinates; the even rows/columns are the hedge lines, and an open
even-coordinate square is a gap through a hedge. Tito always stands on a cell.

One visit is ``MAZES_PER_VISIT`` short mazes. Every maze asks the child to
plan a route to Tito's tent: early mazes are small and loopy, later ones add
dead ends, stars that must be gathered before the tent opens, and finally a
key that opens a garden door on the only route. The next maze's level adapts
to how the previous one went; nothing is ever timed.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Final

OPEN: Final = 0
WALL: Final = 1

Cell = tuple[int, int]

DIRECTIONS: Final[tuple[Cell, ...]] = ((-1, 0), (1, 0), (0, -1), (0, 1))
MAZES_PER_VISIT: Final = 4
MIN_LEVEL: Final = 1
MAX_LEVEL: Final = 6
STAR_SEPARATION: Final = 3  # grid squares (Manhattan) between two stars


@dataclass(frozen=True, slots=True)
class LevelSpec:
    """One rung of the ladder (manifest difficulty 1..6)."""

    level: int
    cols: int
    rows: int
    stars: int
    key: bool
    braid: float  # share of dead ends knocked open (1.0 = loops everywhere)
    guide_arrows: bool  # show the open directions beside Tito while idle


LEVELS: Final[tuple[LevelSpec, ...]] = (
    LevelSpec(1, 4, 3, 0, False, 1.0, True),
    LevelSpec(2, 5, 4, 1, False, 0.6, True),
    LevelSpec(3, 6, 4, 2, False, 0.3, False),
    LevelSpec(4, 7, 5, 1, True, 0.15, False),
    LevelSpec(5, 8, 5, 3, False, 0.0, False),
    LevelSpec(6, 9, 6, 2, True, 0.0, False),
)


def clamp_level(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return MIN_LEVEL
    return max(MIN_LEVEL, min(MAX_LEVEL, value))


def level_spec(level: int) -> LevelSpec:
    return LEVELS[clamp_level(level) - 1]


def is_cell(position: Cell) -> bool:
    return position[0] % 2 == 1 and position[1] % 2 == 1


# --------------------------------------------------------------------------
# Layout + generation
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MazeLayout:
    """One generated maze: hedges, start, tent, stars and the optional key/door."""

    level: int
    grid: tuple[tuple[int, ...], ...]
    start: Cell
    goal: Cell
    stars: tuple[Cell, ...] = ()
    key: Cell | None = None
    door: Cell | None = None

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def width(self) -> int:
        return len(self.grid[0])

    @property
    def rows(self) -> int:
        return self.height // 2

    @property
    def cols(self) -> int:
        return self.width // 2

    def is_open(self, position: Cell) -> bool:
        r, c = position
        return 0 <= r < self.height and 0 <= c < self.width and self.grid[r][c] == OPEN

    def open_neighbours(self, position: Cell, blocked: Collection[Cell] = ()) -> list[Cell]:
        r, c = position
        result = []
        for dr, dc in DIRECTIONS:
            nxt = (r + dr, c + dc)
            if nxt not in blocked and self.is_open(nxt):
                result.append(nxt)
        return result

    def cells(self) -> Iterable[Cell]:
        for r in range(1, self.height, 2):
            for c in range(1, self.width, 2):
                yield (r, c)


def bfs_path(layout: MazeLayout, start: Cell, goal: Cell, blocked: Collection[Cell] = ()) -> list[Cell]:
    """Shortest grid route from ``start`` to ``goal`` (inclusive), or ``[]``."""

    if start == goal:
        return [start]
    parent: dict[Cell, Cell | None] = {start: None}
    queue: deque[Cell] = deque([start])
    while queue:
        current = queue.popleft()
        for nxt in layout.open_neighbours(current, blocked):
            if nxt in parent:
                continue
            parent[nxt] = current
            if nxt == goal:
                path = [nxt]
                step: Cell | None = current
                while step is not None:
                    path.append(step)
                    step = parent[step]
                path.reverse()
                return path
            queue.append(nxt)
    return []


def reachable(layout: MazeLayout, start: Cell, blocked: Collection[Cell] = ()) -> set[Cell]:
    seen = {start}
    queue: deque[Cell] = deque([start])
    while queue:
        for nxt in layout.open_neighbours(queue.popleft(), blocked):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


class MazeGenerator:
    """Build solvable mazes for a ladder level from an injected RNG."""

    MAX_ATTEMPTS: Final = 40

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def build(self, level: int) -> MazeLayout:
        spec = level_spec(level)
        for _ in range(self.MAX_ATTEMPTS):
            layout = self._attempt(spec)
            if layout is not None:
                return layout
        # A key level that never found a door spot falls back to a keyless maze
        # of the same size: still solvable, never a crash in front of a child.
        fallback = LevelSpec(spec.level, spec.cols, spec.rows, spec.stars, False, spec.braid, spec.guide_arrows)
        layout = self._attempt(fallback)
        assert layout is not None
        return layout

    # -- steps ------------------------------------------------------------

    def _attempt(self, spec: LevelSpec) -> MazeLayout | None:
        rng = self._rng
        grid = self._carve(spec.cols, spec.rows)
        self._braid(grid, spec.braid)
        height, width = len(grid), len(grid[0])
        corners = [(1, 1), (1, width - 2), (height - 2, 1), (height - 2, width - 2)]
        start = rng.choice(corners)
        goal = (height - 1 - start[0], width - 1 - start[1])
        frozen = tuple(tuple(row) for row in grid)
        layout = MazeLayout(spec.level, frozen, start, goal)
        route = bfs_path(layout, start, goal)
        if not route:
            return None
        key = door = None
        if spec.key:
            placed = self._place_key_and_door(layout, route)
            if placed is None:
                return None
            key, door = placed
        stars = self._place_stars(layout, route, spec.stars, {start, goal, key, door})
        if len(stars) < spec.stars:
            return None
        # Everything to fetch must be reachable while the tent is still closed
        # (some loopy mazes would otherwise hide a star behind the tent).
        open_garden = reachable(layout, start, blocked=(goal,))
        if any(cell not in open_garden for cell in (*stars, key) if cell is not None):
            return None
        if key is not None and key not in reachable(layout, start, blocked=(goal, door)):
            return None
        return MazeLayout(spec.level, frozen, start, goal, tuple(stars), key, door)

    def _carve(self, cols: int, rows: int) -> list[list[int]]:
        """Iterative recursive-backtracker (perfect maze: one route, dead ends)."""

        height, width = 2 * rows + 1, 2 * cols + 1
        grid = [[WALL] * width for _ in range(height)]
        origin = (2 * self._rng.randrange(rows) + 1, 2 * self._rng.randrange(cols) + 1)
        grid[origin[0]][origin[1]] = OPEN
        stack = [origin]
        while stack:
            r, c = stack[-1]
            options = [
                (r + 2 * dr, c + 2 * dc, r + dr, c + dc)
                for dr, dc in DIRECTIONS
                if 0 < r + 2 * dr < height - 1 and 0 < c + 2 * dc < width - 1 and grid[r + 2 * dr][c + 2 * dc] == WALL
            ]
            if not options:
                stack.pop()
                continue
            nr, nc, wr, wc = self._rng.choice(options)
            grid[wr][wc] = OPEN
            grid[nr][nc] = OPEN
            stack.append((nr, nc))
        return grid

    def _braid(self, grid: list[list[int]], share: float) -> None:
        """Knock a hedge gap at ``share`` of the dead ends to make loops."""

        if share <= 0.0:
            return
        height, width = len(grid), len(grid[0])
        dead_ends = []
        for r in range(1, height, 2):
            for c in range(1, width, 2):
                if sum(grid[r + dr][c + dc] == OPEN for dr, dc in DIRECTIONS) == 1:
                    dead_ends.append((r, c))
        self._rng.shuffle(dead_ends)
        for r, c in dead_ends:
            if sum(grid[r + dr][c + dc] == OPEN for dr, dc in DIRECTIONS) != 1:
                continue  # an earlier opening already fixed this one
            if self._rng.random() > share:
                continue
            walls = [
                (dr, dc)
                for dr, dc in DIRECTIONS
                if 0 < r + 2 * dr < height - 1 and 0 < c + 2 * dc < width - 1 and grid[r + dr][c + dc] == WALL
            ]
            if walls:
                dr, dc = self._rng.choice(walls)
                grid[r + dr][c + dc] = OPEN

    def _place_key_and_door(self, layout: MazeLayout, route: Sequence[Cell]) -> tuple[Cell, Cell] | None:
        """Door on a straight corridor cell of the route; key in a side branch before it."""

        route_cells = [cell for cell in route if is_cell(cell)]
        count = len(route_cells)
        candidates = route_cells[max(2, int(count * 0.4)) : max(3, int(count * 0.8))]
        self._rng.shuffle(candidates)
        on_route = set(route)
        for door in candidates:
            if door in (layout.start, layout.goal):
                continue
            neighbours = layout.open_neighbours(door)
            if len(neighbours) != 2:
                continue
            (r1, c1), (r2, c2) = neighbours
            if r1 != r2 and c1 != c2:
                continue  # a bend: doors stand in straight corridors only
            region = reachable(layout, layout.start, blocked=(door,))
            if layout.goal in region:
                continue  # a loop bypasses the door
            side = [cell for cell in region if is_cell(cell) and cell not in on_route and cell != layout.start]
            if not side:
                continue
            dead = [cell for cell in side if len(layout.open_neighbours(cell)) == 1]
            pool = dead or side
            # The farthest side spot makes fetching the key a real detour.
            distance = {cell: len(bfs_path(layout, layout.start, cell, blocked=(door,))) for cell in pool}
            key = max(pool, key=lambda cell: (distance[cell], self._rng.random()))
            return key, door
        return None

    def _place_stars(
        self, layout: MazeLayout, route: Sequence[Cell], count: int, taken: set[Cell | None]
    ) -> list[Cell]:
        if count <= 0:
            return []
        on_route = set(route)
        cells = [cell for cell in layout.cells() if cell not in taken and layout.is_open(cell)]
        self._rng.shuffle(cells)
        dead = [cell for cell in cells if len(layout.open_neighbours(cell)) == 1]
        off_route = [cell for cell in cells if cell not in on_route and cell not in dead]
        rest = [cell for cell in cells if cell in on_route and cell not in dead]
        stars: list[Cell] = []
        blocked = {cell for cell in taken if cell is not None}
        for cell in (*dead, *off_route, *rest):
            if len(stars) == count:
                break
            if any(abs(cell[0] - o[0]) + abs(cell[1] - o[1]) < STAR_SEPARATION for o in (*stars, *blocked)):
                continue
            stars.append(cell)
        return stars


# --------------------------------------------------------------------------
# Movement and play state
# --------------------------------------------------------------------------


class MazeEventKind(StrEnum):
    STAR = "star"
    KEY = "key"
    DOOR_OPENED = "door_opened"
    GOAL_LOCKED = "goal_locked"
    SOLVED = "solved"
    DEAD_END = "dead_end"
    DOOR_LOCKED = "door_locked"


@dataclass(frozen=True, slots=True)
class MazeEvent:
    kind: MazeEventKind
    cell: Cell


class MoveResult(StrEnum):
    MOVED = "moved"
    WALL = "wall"
    DOOR_LOCKED = "door_locked"
    BUSY = "busy"
    DONE = "done"


@dataclass(slots=True)
class MazeSummary:
    """How one maze went (drives the adaptive ladder; never shown as a score)."""

    level: int
    stars: int
    dead_ends: int = 0
    bumps: int = 0
    hints: int = 0
    locked_tries: int = 0

    @property
    def clean(self) -> bool:
        return self.dead_ends <= 1 and self.hints == 0 and self.locked_tries == 0 and self.bumps <= 4

    @property
    def struggled(self) -> bool:
        return self.dead_ends >= 4 or self.hints >= 2 or self.locked_tries >= 2


# Relative length of one grid step: a cell is 1 unit, a hedge gap ``GAP_SHARE``.
GAP_SHARE: Final = 0.5


def step_length(a: Cell, b: Cell) -> float:
    """Units between neighbouring squares (cells are wider than hedge gaps)."""

    size_a = 1.0 if is_cell(a) else GAP_SHARE
    size_b = 1.0 if is_cell(b) else GAP_SHARE
    return (size_a + size_b) / 2.0


class Maze:
    """Tito's state inside one ``MazeLayout`` (route following + pickups)."""

    def __init__(self, layout: MazeLayout) -> None:
        self.layout = layout
        self.position: Cell = layout.start
        self.collected: set[Cell] = set()
        self.has_key = False
        self.door_open = False
        self.solved = False
        self.summary = MazeSummary(layout.level, len(layout.stars))

    # -- queries -----------------------------------------------------------

    @property
    def locked_door(self) -> Cell | None:
        door = self.layout.door
        if door is None or self.door_open or self.has_key:
            return None
        return door

    @property
    def tent_closed(self) -> bool:
        return bool(self.missing_stars) and not self.solved

    @property
    def missing_stars(self) -> tuple[Cell, ...]:
        return tuple(star for star in self.layout.stars if star not in self.collected)

    @property
    def key_waiting(self) -> bool:
        return self.layout.key is not None and not self.has_key

    def blocked(self, *, allow: Cell | None = None) -> frozenset[Cell]:
        """Cells Tito cannot enter now: a locked door and a closed tent."""

        cells = {self.locked_door, self.layout.goal if self.tent_closed else None}
        cells.discard(None)
        cells.discard(allow)
        return frozenset(cells)  # type: ignore[arg-type]

    def open_directions(self) -> list[Cell]:
        return [direction for direction in DIRECTIONS if self.route(direction)]

    def is_dead_end(self, cell: Cell) -> bool:
        return len(self.layout.open_neighbours(cell, self.blocked())) <= 1

    # -- planning ----------------------------------------------------------

    def route(self, direction: Cell, *, target: Cell | None = None) -> list[Cell]:
        """Follow the corridor in ``direction`` until a choice must be made.

        Tito walks around bends on his own and stops at a junction, a dead
        end, the tent, or the tapped ``target`` square. Stars and the key are
        picked up on the way; a locked door (and the tent while stars are
        still missing) is a hedge he stops in front of.
        """

        layout = self.layout
        blocked = self.blocked()
        previous = self.position
        current = (previous[0] + direction[0], previous[1] + direction[1])
        if current in blocked or not layout.is_open(current):
            return []
        path = [current]
        guard = layout.width * layout.height
        while len(path) < guard:
            if current == layout.goal or current == target:
                break
            onward = [cell for cell in layout.open_neighbours(current, blocked) if cell != previous]
            if is_cell(current) and len(onward) != 1:
                break  # junction (>1 way on) or dead end (none)
            if not onward:
                break
            previous, current = current, onward[0]
            path.append(current)
        return _settle(path)

    def _closed_ahead(self, direction: Cell) -> Cell | None:
        r, c = self.position
        gap = (r + direction[0], c + direction[1])
        cell = (r + 2 * direction[0], c + 2 * direction[1])
        if self.layout.is_open(gap) and cell in self.blocked():
            return cell
        return None

    def blocked_by_door(self, direction: Cell) -> bool:
        """True when the locked door is the next cell in ``direction``."""

        door = self.locked_door
        return door is not None and self._closed_ahead(direction) == door

    def blocked_by_tent(self, direction: Cell) -> bool:
        """True when the still-closed tent is the next cell in ``direction``."""

        return self.tent_closed and self._closed_ahead(direction) == self.layout.goal

    def door_ahead(self) -> Cell | None:
        """The direction of a locked door right next to Tito, if any."""

        return next((d for d in DIRECTIONS if self.blocked_by_door(d)), None)

    def tent_ahead(self) -> Cell | None:
        """The direction of the closed tent right next to Tito, if any."""

        return next((d for d in DIRECTIONS if self.blocked_by_tent(d)), None)

    def direction_towards(self, target: Cell) -> tuple[Cell, list[Cell]] | None:
        """Best single corridor move towards a tapped square (no auto-solving).

        A route that passes the target stops on it; otherwise the move that
        ends closest to it wins, but only if it gets Tito closer.
        """

        if target == self.position:
            return None
        here = _manhattan(self.position, target)
        best: tuple[int, Cell, list[Cell]] | None = None
        for direction in DIRECTIONS:
            path = self.route(direction, target=target)
            if not path:
                continue
            if target in path:
                return direction, path[: path.index(target) + 1]
            closest = min(range(len(path)), key=lambda i: (_manhattan(path[i], target), i))
            end = _settle(path[: closest + 1]) or _settle(path)
            distance = _manhattan(end[-1], target)
            if distance < here and (best is None or distance < best[0]):
                best = (distance, direction, end)
        if best is None:
            return None
        return best[1], best[2]

    def hint_route(self) -> list[Cell]:
        """Route to the next thing to fetch: key, nearest star, then the tent."""

        layout = self.layout
        blocked = self.blocked()
        if self.key_waiting and layout.key is not None:
            return bfs_path(layout, self.position, layout.key, blocked)
        best: list[Cell] = []
        for star in self.missing_stars:
            path = bfs_path(layout, self.position, star, blocked)
            if path and (not best or len(path) < len(best)):
                best = path
        if best:
            return best
        return bfs_path(layout, self.position, layout.goal, self.blocked(allow=layout.goal))

    def next_target(self) -> Cell:
        route = self.hint_route()
        return route[-1] if route else self.layout.goal

    # -- arriving ----------------------------------------------------------

    def enter(self, cell: Cell, *, final: bool) -> list[MazeEvent]:
        """Tito steps onto ``cell``; ``final`` is the last square of this move."""

        self.position = cell
        events: list[MazeEvent] = []
        layout = self.layout
        if cell in layout.stars and cell not in self.collected:
            self.collected.add(cell)
            events.append(MazeEvent(MazeEventKind.STAR, cell))
        if cell == layout.key and not self.has_key:
            self.has_key = True
            events.append(MazeEvent(MazeEventKind.KEY, cell))
        if cell == layout.door and not self.door_open:
            self.door_open = True
            events.append(MazeEvent(MazeEventKind.DOOR_OPENED, cell))
        if cell == layout.goal and not self.solved:
            self.solved = True
            events.append(MazeEvent(MazeEventKind.SOLVED, cell))
            return events
        if not final or events:
            return events
        if self.tent_ahead() is not None:
            self.summary.locked_tries += 1
            events.append(MazeEvent(MazeEventKind.GOAL_LOCKED, cell))
        elif self.door_ahead() is not None:
            events.append(MazeEvent(MazeEventKind.DOOR_LOCKED, cell))
        elif cell != layout.start and is_cell(cell) and self.is_dead_end(cell):
            self.summary.dead_ends += 1
            events.append(MazeEvent(MazeEventKind.DEAD_END, cell))
        return events


def _settle(path: list[Cell]) -> list[Cell]:
    """Drop trailing hedge gaps: Tito always comes to rest on a cell."""

    end = len(path)
    while end and not is_cell(path[end - 1]):
        end -= 1
    return path[:end]


def _manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Walker:
    """Animated progress of Tito along a planned route (units per second)."""

    def __init__(self, speed: float = 5.5) -> None:
        self.speed = float(speed)
        self.waypoints: deque[Cell] = deque()
        self.origin: Cell = (1, 1)
        self.progress = 0.0

    @property
    def moving(self) -> bool:
        return bool(self.waypoints)

    def start(self, origin: Cell, path: Sequence[Cell]) -> None:
        self.origin = origin
        self.waypoints = deque(path)
        self.progress = 0.0

    def stop(self) -> None:
        self.waypoints.clear()
        self.progress = 0.0

    def advance(self, dt: float) -> list[tuple[Cell, bool]]:
        """Move on; return squares reached as ``(cell, is_last_of_route)``."""

        arrived: list[tuple[Cell, bool]] = []
        budget = max(0.0, dt) * self.speed
        while self.waypoints and budget > 0.0:
            target = self.waypoints[0]
            length = step_length(self.origin, target)
            remaining = length * (1.0 - self.progress)
            if budget >= remaining:
                budget -= remaining
                self.origin = self.waypoints.popleft()
                self.progress = 0.0
                arrived.append((self.origin, not self.waypoints))
            else:
                self.progress += budget / length
                budget = 0.0
        return arrived

    def position(self) -> tuple[float, float]:
        """Fractional (row, col) for drawing."""

        if not self.waypoints:
            return float(self.origin[0]), float(self.origin[1])
        target = self.waypoints[0]
        t = self.progress
        return (
            self.origin[0] + (target[0] - self.origin[0]) * t,
            self.origin[1] + (target[1] - self.origin[1]) * t,
        )


# --------------------------------------------------------------------------
# Visit (one round of mazes) + saved progress
# --------------------------------------------------------------------------


@dataclass(slots=True)
class LabyrinthProgress:
    """Profile-scoped progress (bounded counters; see maze_services)."""

    level: int = MIN_LEVEL
    stars: int = 0
    mazes_solved: int = 0
    visits_completed: int = 0


def next_level(level: int, summary: MazeSummary) -> int:
    if summary.clean:
        return clamp_level(level + 1)
    if summary.struggled:
        return clamp_level(level - 1)
    return clamp_level(level)


@dataclass(slots=True)
class Visit:
    """``MAZES_PER_VISIT`` mazes in a row; levels adapt between mazes."""

    generator: MazeGenerator
    progress: LabyrinthProgress
    total: int = MAZES_PER_VISIT
    completed: int = 0
    summaries: list[MazeSummary] = field(default_factory=list)
    maze: Maze = field(init=False)

    def __post_init__(self) -> None:
        self.progress.level = clamp_level(self.progress.level)
        self.maze = Maze(self.generator.build(self.progress.level))

    @property
    def complete(self) -> bool:
        return self.completed >= self.total

    def finish_maze(self) -> MazeSummary:
        summary = self.maze.summary
        self.summaries.append(summary)
        self.completed += 1
        self.progress.mazes_solved += 1
        self.progress.level = next_level(self.progress.level, summary)
        return summary

    def next_maze(self) -> Maze:
        self.maze = Maze(self.generator.build(self.progress.level))
        return self.maze

    def restart(self) -> Maze:
        self.completed = 0
        self.summaries.clear()
        return self.next_maze()


__all__ = [
    "Cell",
    "DIRECTIONS",
    "GAP_SHARE",
    "LEVELS",
    "LabyrinthProgress",
    "LevelSpec",
    "MAX_LEVEL",
    "MAZES_PER_VISIT",
    "MIN_LEVEL",
    "Maze",
    "MazeEvent",
    "MazeEventKind",
    "MazeGenerator",
    "MazeLayout",
    "MazeSummary",
    "MoveResult",
    "OPEN",
    "Visit",
    "WALL",
    "Walker",
    "bfs_path",
    "clamp_level",
    "is_cell",
    "level_spec",
    "next_level",
    "reachable",
    "step_length",
]
