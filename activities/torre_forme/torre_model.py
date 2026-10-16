"""Domain model for La Torre delle Forme (Shape Tower): silhouette fitting.

A build (a lighthouse, a rocket, a cat ...) is a target *silhouette* made of
wooden blocks on a small grid. The child fills it from a kit of block kinds
(unlimited supply, like a toy box): pick a block, turn it in 90-degree steps
if needed, and put it where it fits. Nothing falls, nothing is cleared, and
there is no clock: a build is finished when the whole silhouette is filled.

Geometry is exact and pure (no Pygame):

* the grid uses ``(col, row)`` with row 0 at the top;
* every block kind has a footprint of one or two unit cells at rotation 0
  (square, triangle, cylinder 1x1; rectangle, half circle, arch 2x1) and is
  turned clockwise in quarter turns; ``TURNS`` lists how many distinct
  orientations a kind has (a square or a standing cylinder looks the same
  every way, a rectangle has two, triangles/half circles/arches four);
* every covered cell carries a *fill token*. Squares and rectangles fill a
  cell completely (``FULL``), so two squares can fill a rectangle's place and
  one rectangle can fill two squares' places; curved and pointed pieces carry
  their kind, orientation and half, so only that piece the right way round
  matches them.

Two outline styles set how much the board helps:

* ``SLOTS`` (younger rungs): each block's own dashed outline is drawn and a
  block must go into one of them exactly;
* ``SILHOUETTE`` (older rungs): only the outer shape is drawn; any
  combination of kit blocks that covers it exactly is accepted, and a block
  is only accepted where the rest can still be finished with the kit (so the
  board can never reach a dead end).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
BUILDS_PER_SET: Final = 5
MAX_LEVEL: Final = 5
HISTORY_LIMIT: Final = 8
MAX_KIT: Final = 6
MAX_BUILD_COLS: Final = 4
MAX_BUILD_ROWS: Final = 5
FIT_CACHE_LIMIT: Final = 512

Cell = tuple[int, int]  # (col, row)
FillToken = tuple


class BlockKind(StrEnum):
    SQUARE = "square"
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"
    HALF_CIRCLE = "half_circle"
    ARCH = "arch"
    CYLINDER = "cylinder"


class OutlineStyle(StrEnum):
    SLOTS = "slots"
    SILHOUETTE = "silhouette"


# Unit-cell size at rotation 0 and the number of distinct quarter turns.
BASE_SIZE: Final[Mapping[BlockKind, tuple[int, int]]] = {
    BlockKind.SQUARE: (1, 1),
    BlockKind.RECTANGLE: (2, 1),
    BlockKind.TRIANGLE: (1, 1),
    BlockKind.HALF_CIRCLE: (2, 1),
    BlockKind.ARCH: (2, 1),
    BlockKind.CYLINDER: (1, 1),
}
TURNS: Final[Mapping[BlockKind, int]] = {
    BlockKind.SQUARE: 1,
    BlockKind.RECTANGLE: 2,
    BlockKind.TRIANGLE: 4,
    BlockKind.HALF_CIRCLE: 4,
    BlockKind.ARCH: 4,
    BlockKind.CYLINDER: 1,
}
FULL: Final[FillToken] = ("full",)


@dataclass(frozen=True, slots=True)
class Block:
    """One block kind turned ``rotation`` quarter turns clockwise."""

    kind: BlockKind
    rotation: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.rotation < TURNS[self.kind]:
            raise ValueError(f"{self.kind} has rotations 0..{TURNS[self.kind] - 1}")

    @staticmethod
    def of(kind: BlockKind, rotation: int = 0) -> "Block":
        """Build a block, folding equivalent turns (a rectangle has two)."""

        return Block(kind, rotation % TURNS[kind])

    @property
    def rotates(self) -> bool:
        return TURNS[self.kind] > 1

    def turned(self) -> "Block":
        return Block.of(self.kind, self.rotation + 1)

    @property
    def size(self) -> tuple[int, int]:
        """(width, height) in cells."""

        width, height = BASE_SIZE[self.kind]
        return (height, width) if self.rotation % 2 else (width, height)

    def footprint(self) -> tuple[tuple[Cell, FillToken], ...]:
        return _footprint(self.kind, self.rotation)


_FOOTPRINTS: dict[tuple[BlockKind, int], tuple[tuple[Cell, FillToken], ...]] = {}


def _footprint(kind: BlockKind, rotation: int) -> tuple[tuple[Cell, FillToken], ...]:
    """Covered cells (relative to the top-left) and their fill tokens."""

    key = (kind, rotation)
    cached = _FOOTPRINTS.get(key)
    if cached is not None:
        return cached
    width, height = BASE_SIZE[kind]
    cells: list[tuple[Cell, FillToken]] = []
    for part in range(width * height):
        x, y = part % width, part // width
        w, h = width, height
        for _ in range(rotation):  # one clockwise quarter turn: (x, y) -> (h - 1 - y, x)
            x, y = h - 1 - y, x
            w, h = h, w
        if kind in (BlockKind.SQUARE, BlockKind.RECTANGLE):
            token: FillToken = FULL
        elif kind is BlockKind.CYLINDER:
            token = ("cylinder",)
        elif kind is BlockKind.TRIANGLE:
            token = ("triangle", rotation)
        else:
            token = (kind.value, rotation, part)
        cells.append(((x, y), token))
    result = tuple(sorted(cells))
    _FOOTPRINTS[key] = result
    return result


@dataclass(frozen=True, slots=True)
class Placement:
    """A block with its top-left cell on the build grid."""

    block: Block
    col: int
    row: int

    @property
    def fills(self) -> dict[Cell, FillToken]:
        return {(self.col + dx, self.row + dy): token for (dx, dy), token in self.block.footprint()}

    @property
    def cells(self) -> tuple[Cell, ...]:
        return tuple(sorted(self.fills))

    @property
    def center(self) -> tuple[float, float]:
        """Centre in cell units (cell (c, r) spans c..c+1, r..r+1)."""

        width, height = self.block.size
        return (self.col + width / 2.0, self.row + height / 2.0)


def place(kind: BlockKind, rotation: int, col: int, row: int) -> Placement:
    return Placement(Block.of(kind, rotation), col, row)


@dataclass(frozen=True, slots=True)
class BuildPlan:
    """One silhouette to build: its canonical blocks and what it is.

    ``noun`` names the shared spoken-word clip (``assets/audio/vocab``) and
    ``picture`` the shared picture (``prop.vocab.*``) shown on the box card;
    both are optional, the outline itself is the goal.
    """

    build_id: str
    placements: tuple[Placement, ...]
    noun: str | None = None
    picture: str | None = None

    def __post_init__(self) -> None:
        if not self.placements:
            raise ValueError("a build needs blocks")
        seen: dict[Cell, FillToken] = {}
        for item in self.placements:
            for cell, token in item.fills.items():
                if cell in seen:
                    raise ValueError(f"{self.build_id}: blocks overlap at {cell}")
                if cell[0] < 0 or cell[1] < 0:
                    raise ValueError(f"{self.build_id}: negative cell {cell}")
                seen[cell] = token
        width, height = self.size
        if width > MAX_BUILD_COLS or height > MAX_BUILD_ROWS:
            raise ValueError(f"{self.build_id}: build is larger than the board")
        if not _connected(seen):
            raise ValueError(f"{self.build_id}: a build is one connected shape")

    @property
    def fills(self) -> dict[Cell, FillToken]:
        result: dict[Cell, FillToken] = {}
        for item in self.placements:
            result.update(item.fills)
        return result

    @property
    def size(self) -> tuple[int, int]:
        cells = [cell for item in self.placements for cell in item.fills]
        return (max(c for c, _ in cells) + 1, max(r for _, r in cells) + 1)

    @property
    def kinds(self) -> tuple[BlockKind, ...]:
        return tuple(dict.fromkeys(item.block.kind for item in self.placements))

    @property
    def block_count(self) -> int:
        return len(self.placements)


def _connected(cells: Iterable[Cell]) -> bool:
    remaining = set(cells)
    if not remaining:
        return False
    stack = [remaining.pop()]
    while stack:
        col, row = stack.pop()
        for neighbour in ((col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)):
            if neighbour in remaining:
                remaining.remove(neighbour)
                stack.append(neighbour)
    return not remaining


@dataclass(frozen=True, slots=True)
class Puzzle:
    """A build plus how it is offered: outline style and the block kit."""

    plan: BuildPlan
    style: OutlineStyle
    kit: tuple[Block, ...]  # kit kinds with their starting turn

    def __post_init__(self) -> None:
        kinds = [block.kind for block in self.kit]
        if len(set(kinds)) != len(kinds):
            raise ValueError("one kit slot per block kind")
        if not 1 <= len(self.kit) <= MAX_KIT:
            raise ValueError(f"a kit has 1..{MAX_KIT} kinds")
        missing = set(self.plan.kinds) - set(kinds)
        if missing:
            raise ValueError(f"{self.plan.build_id}: kit lacks {sorted(missing)}")

    @property
    def distractors(self) -> tuple[BlockKind, ...]:
        used = set(self.plan.kinds)
        return tuple(block.kind for block in self.kit if block.kind not in used)


# -- covering (exact cover of the remaining silhouette) --------------------------------


def fits_cells(placement: Placement, open_fills: Mapping[Cell, FillToken]) -> bool:
    """True when ``placement`` covers only open cells with matching tokens."""

    return all(open_fills.get(cell) == token for cell, token in placement.fills.items())


def solve(open_fills: Mapping[Cell, FillToken], kinds: Sequence[BlockKind]) -> tuple[Placement, ...] | None:
    """One way to cover ``open_fills`` exactly with ``kinds`` (or None).

    Tiny backtracking search: the top-left open cell must be covered by some
    block, so only blocks that include it are tried. Builds have at most a
    few dozen cells and six kinds, so this is instant.
    """

    remaining = dict(open_fills)
    chosen: list[Placement] = []

    def search() -> bool:
        if not remaining:
            return True
        col, row = min(remaining, key=lambda cell: (cell[1], cell[0]))
        for kind in kinds:
            for rotation in range(TURNS[kind]):
                block = Block(kind, rotation)
                for (dx, dy), _ in block.footprint():
                    candidate = Placement(block, col - dx, row - dy)
                    if not fits_cells(candidate, remaining):
                        continue
                    covered = candidate.fills
                    for cell in covered:
                        del remaining[cell]
                    chosen.append(candidate)
                    if search():
                        return True
                    chosen.pop()
                    remaining.update(covered)
        return False

    return tuple(chosen) if search() else None


# -- per-set play ---------------------------------------------------------------------------


class PlaceOutcome(StrEnum):
    CORRECT = "correct"
    WRONG_SPOT = "wrong_spot"   # this block, turned like this, fits somewhere else
    NEEDS_TURN = "needs_turn"   # it fits somewhere once it is turned
    NO_FIT = "no_fit"           # this kind is not part of the build
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class PlaceResult:
    outcome: PlaceOutcome
    placement: Placement | None = None
    puzzle_completed: bool = False
    session_complete: bool = False

    @property
    def correct(self) -> bool:
        return self.outcome is PlaceOutcome.CORRECT


@dataclass(frozen=True, slots=True)
class HintStep:
    """What a helper would do next: which kit block, turned how, where."""

    kit_index: int
    placement: Placement

    def needs_turn(self, current: Block) -> bool:
        return current.rotation != self.placement.block.rotation


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    first_attempt_success: bool
    hints_used: int
    used_retry: bool


@dataclass(slots=True)
class _BuildState:
    placed: list[Placement] = field(default_factory=list)
    filled: dict[Cell, int] = field(default_factory=dict)  # cell -> index in placed
    misses: int = 0
    hints: int = 0


class TorreSession:
    """Own the builds of one set, the kit turns, misses/hints and the facts."""

    def __init__(
        self,
        puzzles: Sequence[Puzzle],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(puzzles) != BUILDS_PER_SET:
            raise ValueError(f"a Torre delle Forme set has exactly {BUILDS_PER_SET} builds")
        self._puzzles = tuple(puzzles)
        self.level = level
        self._index = 0
        self._history = list(history[-HISTORY_LIMIT:])
        self._finished = 0
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None
        self._state = _BuildState()
        # fits() answers depend only on the open cells and the kit kinds, so
        # they are memoised until the next placement (pointer hover asks
        # many times per second; the solver must not run per motion event).
        self._fit_cache: dict[Placement, bool] = {}
        self.kit: list[Block] = []
        self._reset_kit()

    # -- state ------------------------------------------------------------------------

    @property
    def current_puzzle(self) -> Puzzle | None:
        return self._puzzles[self._index] if self._index < len(self._puzzles) else None

    @property
    def puzzle_index(self) -> int:
        return self._index

    @property
    def finished_count(self) -> int:
        return self._finished

    @property
    def placed(self) -> tuple[Placement, ...]:
        return tuple(self._state.placed)

    @property
    def misses(self) -> int:
        return self._state.misses

    @property
    def hints(self) -> int:
        return self._state.hints

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    @property
    def is_complete(self) -> bool:
        return self._finished >= len(self._puzzles)

    @property
    def open_fills(self) -> dict[Cell, FillToken]:
        puzzle = self.current_puzzle
        if puzzle is None:
            return {}
        return {cell: token for cell, token in puzzle.plan.fills.items() if cell not in self._state.filled}

    @property
    def puzzle_done(self) -> bool:
        return self.current_puzzle is not None and not self.open_fills

    def is_open(self, cell: Cell) -> bool:
        return cell in self.open_fills

    def placement_at(self, cell: Cell) -> Placement | None:
        index = self._state.filled.get(cell)
        return None if index is None else self._state.placed[index]

    def open_slots(self) -> tuple[Placement, ...]:
        """Canonical blocks whose cells are all still open (bottom row first)."""

        puzzle = self.current_puzzle
        if puzzle is None:
            return ()
        open_cells = self.open_fills
        slots = [item for item in puzzle.plan.placements if all(cell in open_cells for cell in item.fills)]
        return tuple(sorted(slots, key=_bottom_first))

    # -- kit ----------------------------------------------------------------------------

    def kit_block(self, index: int) -> Block:
        return self.kit[index]

    def turn(self, index: int) -> bool:
        """Turn the kit block a quarter clockwise; False if it looks the same."""

        if not 0 <= index < len(self.kit) or not self.kit[index].rotates:
            return False
        self.kit[index] = self.kit[index].turned()
        return True

    def kit_index(self, kind: BlockKind) -> int | None:
        for index, block in enumerate(self.kit):
            if block.kind is kind:
                return index
        return None

    # -- fitting ------------------------------------------------------------------------

    def fits(self, placement: Placement) -> bool:
        """Would ``placement`` be accepted on the current board?"""

        cached = self._fit_cache.get(placement)
        if cached is None:
            cached = self._fits(placement)
            if len(self._fit_cache) >= FIT_CACHE_LIMIT:
                self._fit_cache.clear()
            self._fit_cache[placement] = cached
        return cached

    def _fits(self, placement: Placement) -> bool:
        puzzle = self.current_puzzle
        if puzzle is None:
            return False
        open_fills = self.open_fills
        if not fits_cells(placement, open_fills):
            return False
        if puzzle.style is OutlineStyle.SLOTS:
            wanted = placement.fills
            return any(slot.fills == wanted for slot in self.open_slots())
        rest = {cell: token for cell, token in open_fills.items() if cell not in placement.fills}
        return solve(rest, [block.kind for block in self.kit]) is not None

    def best_fit(self, block: Block, near: tuple[float, float], *, reach: float = 0.75) -> Placement | None:
        """The accepted placement of ``block`` closest to ``near`` (cell units).

        Only placements whose centre is within ``reach`` cells of the point
        on both axes count: a block snaps into place when it is held roughly
        over where it fits, never across the board.
        """

        width, height = block.size
        best: tuple[float, Placement] | None = None
        x, y = near
        for col in range(int(x - width / 2.0 - reach) - 1, int(x + reach) + 2):
            for row in range(int(y - height / 2.0 - reach) - 1, int(y + reach) + 2):
                candidate = Placement(block, col, row)
                cx, cy = candidate.center
                if abs(cx - x) > reach + 1e-9 or abs(cy - y) > reach + 1e-9:
                    continue
                if not self.fits(candidate):
                    continue
                distance = (cx - x) ** 2 + (cy - y) ** 2
                if best is None or distance < best[0]:
                    best = (distance, candidate)
        return None if best is None else best[1]

    def anywhere(self, block: Block) -> Placement | None:
        """Some accepted placement of ``block`` on the board, if any."""

        for cell in sorted(self.open_fills, key=lambda c: (-c[1], c[0])):
            for (dx, dy), _ in block.footprint():
                candidate = Placement(block, cell[0] - dx, cell[1] - dy)
                if self.fits(candidate):
                    return candidate
        return None

    def classify_miss(self, block: Block) -> PlaceOutcome:
        if self.anywhere(block) is not None:
            return PlaceOutcome.WRONG_SPOT
        for turns in range(1, TURNS[block.kind]):
            if self.anywhere(Block.of(block.kind, block.rotation + turns)) is not None:
                return PlaceOutcome.NEEDS_TURN
        return PlaceOutcome.NO_FIT

    def try_place(self, kit_index: int, near: tuple[float, float]) -> PlaceResult:
        """Put kit block ``kit_index`` (as turned now) near ``near`` (cell units)."""

        puzzle = self.current_puzzle
        if puzzle is None or self.puzzle_done or not 0 <= kit_index < len(self.kit):
            return PlaceResult(PlaceOutcome.IGNORED)
        block = self.kit[kit_index]
        placement = self.best_fit(block, near)
        if placement is None:
            self._state.misses += 1
            return PlaceResult(self.classify_miss(block))
        index = len(self._state.placed)
        self._fit_cache.clear()
        self._state.placed.append(placement)
        for cell in placement.fills:
            self._state.filled[cell] = index
        if not self.puzzle_done:
            return PlaceResult(PlaceOutcome.CORRECT, placement)
        self._record_finished()
        return PlaceResult(PlaceOutcome.CORRECT, placement, puzzle_completed=True, session_complete=self.is_complete)

    def next_step(self) -> HintStep | None:
        """The block a helper would place next (lowest first, like real building)."""

        puzzle = self.current_puzzle
        if puzzle is None or self.puzzle_done:
            return None
        if puzzle.style is OutlineStyle.SLOTS:
            options: Sequence[Placement] = self.open_slots()
        else:
            options = solve(self.open_fills, [block.kind for block in self.kit]) or ()
        for placement in sorted(options, key=_bottom_first):
            index = self.kit_index(placement.block.kind)
            if index is not None:
                return HintStep(index, placement)
        return None

    def note_hint(self) -> None:
        self._state.hints += 1

    def next_puzzle(self) -> bool:
        if not self.puzzle_done or self._index >= len(self._puzzles):
            return False
        self._index += 1
        self._state = _BuildState()
        self._fit_cache.clear()
        self._reset_kit()
        return self.current_puzzle is not None

    def _reset_kit(self) -> None:
        puzzle = self.current_puzzle
        self.kit = list(puzzle.kit) if puzzle is not None else []

    def _record_finished(self) -> None:
        state = self._state
        first = state.misses == 0
        self._history.append(
            AttemptSummary(first_attempt_success=first, hints_used=min(32, state.misses + state.hints), used_retry=state.misses > 0)
        )
        del self._history[:-HISTORY_LIMIT]
        self._finished += 1
        puzzle = self.current_puzzle
        assert puzzle is not None
        self._pending_milestone = {
            "level": self.level,
            "build_index": self._index + 1,
            "blocks": puzzle.plan.block_count,
            "first_attempt": int(first),
        }

    def consume_milestone(self) -> dict[str, int] | None:
        fact, self._pending_milestone = self._pending_milestone, None
        return fact

    def consume_completion(self) -> dict[str, int] | None:
        if not self.is_complete or self._completion_consumed:
            return None
        self._completion_consumed = True
        recent = self._history[-BUILDS_PER_SET:]
        return {
            "level": self.level,
            "builds": BUILDS_PER_SET,
            "first_attempt_count": sum(item.first_attempt_success for item in recent),
            "retries": sum(item.used_retry for item in recent),
        }


def _bottom_first(placement: Placement) -> tuple[int, int]:
    width, height = placement.block.size
    return (-(placement.row + height), placement.col)


def adapt_level(current: int, history: Sequence[AttemptSummary]) -> int:
    """Bounded between-set adaptation across levels 1..5."""

    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= BUILDS_PER_SET:
        window = recent[-BUILDS_PER_SET:]
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in window)
        if strong >= 4:
            return min(MAX_LEVEL, current + 1)
    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 2 for item in last_three):
            return max(1, current - 1)
    return current


def _require_level(level: int) -> None:
    if not 1 <= level <= MAX_LEVEL:
        raise ValueError(f"level must be in 1..{MAX_LEVEL}")


__all__ = [
    "AttemptSummary",
    "BASE_SIZE",
    "BUILDS_PER_SET",
    "Block",
    "BlockKind",
    "BuildPlan",
    "Cell",
    "FULL",
    "HISTORY_LIMIT",
    "HintStep",
    "MAX_BUILD_COLS",
    "MAX_BUILD_ROWS",
    "MAX_KIT",
    "MAX_LEVEL",
    "OutlineStyle",
    "PlaceOutcome",
    "PlaceResult",
    "Placement",
    "Puzzle",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "TURNS",
    "TorreSession",
    "adapt_level",
    "fits_cells",
    "place",
    "solve",
]
