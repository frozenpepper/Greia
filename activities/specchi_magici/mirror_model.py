"""Domain model for Specchi Magici (Magic Mirrors).

Half a mosaic is laid on the picture side of a magic mirror line; the child
completes the reflection by placing mosaic tiles on the mirror side. This
module owns the geometry (exact reflections across a vertical line, a
horizontal "water" line, or both), puzzle generation per difficulty rung,
the per-mosaic placement rules, bounded adaptation and the milestone /
completion facts. It knows nothing about Pygame.

Board: ``GRID_COLS`` x ``GRID_ROWS`` cells. The vertical mirror runs between
columns 2 and 3, the horizontal one between rows 1 and 2.

Orientation: ``Piece.rotation`` 0..3 = the tile's point/dome/lobes face up,
right, down, left. A vertical mirror swaps right/left, a horizontal one swaps
up/down; circles, squares and rhombi look the same in every mirror, hearts
only turn over in water.

The tray is a *kit* of tile kinds with unlimited supply: it always offers the
tiles the reflection needs plus decoys, never the answer alone. Rungs with
oriented tiles also offer the *unreflected* copy, so choosing the mirrored
orientation is a real decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Final, Sequence

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CHALLENGE_COUNT: Final = 5
GRID_COLS: Final = 6
GRID_ROWS: Final = 4
HALF_COLS: Final = GRID_COLS // 2
HALF_ROWS: Final = GRID_ROWS // 2
HISTORY_LIMIT: Final = 8
MAX_LEVEL: Final = 5
MAX_TRAY: Final = 8
COLOUR_COUNT: Final = 6


class ShapeKind(StrEnum):
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    SEMICIRCLE = "semicircle"
    RHOMBUS = "rhombus"
    HEART = "heart"


# Shapes whose look depends on ``rotation`` (hearts only turn upside down).
ORIENTED: Final = frozenset({ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE, ShapeKind.HEART})
SYMMETRIC: Final = (ShapeKind.CIRCLE, ShapeKind.SQUARE, ShapeKind.RHOMBUS, ShapeKind.HEART)


class MirrorAxis(StrEnum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    BOTH = "both"


@dataclass(frozen=True, slots=True)
class Piece:
    """One mosaic tile kind: shape, colour token index and 90-degree rotation."""

    kind: ShapeKind
    color_index: int
    rotation: int = 0

    def __post_init__(self) -> None:
        if not (0 <= self.rotation <= 3):
            raise ValueError("rotation must be in 0..3")
        if not (0 <= self.color_index < COLOUR_COUNT):
            raise ValueError(f"color_index must be in 0..{COLOUR_COUNT - 1}")
        if self.kind not in ORIENTED and self.rotation != 0:
            raise ValueError(f"{self.kind} tiles have no orientation")
        if self.kind is ShapeKind.HEART and self.rotation not in (0, 2):
            raise ValueError("hearts are upright (0) or upside down (2)")


def reflect_vertical(piece: Piece) -> Piece:
    """Mirror image across a vertical line: right <-> left."""

    if piece.kind in {ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE}:
        return Piece(piece.kind, piece.color_index, (4 - piece.rotation) % 4)
    return piece


def reflect_horizontal(piece: Piece) -> Piece:
    """Mirror image across a horizontal (water) line: up <-> down."""

    if piece.kind in ORIENTED:
        return Piece(piece.kind, piece.color_index, (6 - piece.rotation) % 4)
    return piece


# Backwards-compatible name used by older callers/tests: the vertical mirror.
reflect_piece = reflect_vertical


def mirror_col(col: int) -> int:
    """Reflect a column across the vertical mirror (between columns 2 and 3)."""

    if not (0 <= col < GRID_COLS):
        raise ValueError(f"col must be in 0..{GRID_COLS - 1}")
    return (GRID_COLS - 1) - col


def mirror_row(row: int) -> int:
    """Reflect a row across the horizontal mirror (between rows 1 and 2)."""

    if not (0 <= row < GRID_ROWS):
        raise ValueError(f"row must be in 0..{GRID_ROWS - 1}")
    return (GRID_ROWS - 1) - row


@dataclass(frozen=True, slots=True)
class CellPlacement:
    """A piece at an authoritative grid coordinate (row, col)."""

    row: int
    col: int
    piece: Piece

    def __post_init__(self) -> None:
        if not (0 <= self.row < GRID_ROWS):
            raise ValueError(f"row must be in 0..{GRID_ROWS - 1}")
        if not (0 <= self.col < GRID_COLS):
            raise ValueError(f"col must be in 0..{GRID_COLS - 1}")

    @property
    def cell(self) -> tuple[int, int]:
        return (self.row, self.col)


def reflections(source: CellPlacement, axis: MirrorAxis) -> tuple[CellPlacement, ...]:
    """Every mirror image of ``source`` for ``axis`` (one, or three for BOTH)."""

    row, col, piece = source.row, source.col, source.piece
    if axis is MirrorAxis.VERTICAL:
        return (CellPlacement(row, mirror_col(col), reflect_vertical(piece)),)
    if axis is MirrorAxis.HORIZONTAL:
        return (CellPlacement(mirror_row(row), col, reflect_horizontal(piece)),)
    return (
        CellPlacement(row, mirror_col(col), reflect_vertical(piece)),
        CellPlacement(mirror_row(row), col, reflect_horizontal(piece)),
        CellPlacement(mirror_row(row), mirror_col(col), reflect_horizontal(reflect_vertical(piece))),
    )


@dataclass(frozen=True, slots=True)
class MosaicPuzzle:
    """One mosaic: the given half, the reflection to build and the tile kit."""

    puzzle_id: str
    axis: MirrorAxis
    givens: tuple[CellPlacement, ...]
    required: tuple[CellPlacement, ...]
    tray: tuple[Piece, ...]

    def __post_init__(self) -> None:
        if not self.puzzle_id:
            raise ValueError("puzzle_id must not be empty")
        if not self.givens or not self.required:
            raise ValueError("a mosaic needs given and required tiles")
        given_cells = {g.cell for g in self.givens}
        required_cells = [r.cell for r in self.required]
        if len(given_cells) != len(self.givens) or len(set(required_cells)) != len(required_cells):
            raise ValueError("mosaic cells must be unique")
        if given_cells & set(required_cells):
            raise ValueError("given and required cells must not overlap")
        if not self.tray or len(self.tray) > MAX_TRAY or len(set(self.tray)) != len(self.tray):
            raise ValueError(f"the tray holds 1..{MAX_TRAY} distinct tile kinds")
        if not {r.piece for r in self.required} <= set(self.tray):
            raise ValueError("the tray must offer every tile the reflection needs")
        if len(self.tray) < 2:
            raise ValueError("the tray must leave a choice")

    def target_at(self, cell: tuple[int, int]) -> CellPlacement | None:
        for placement in self.required:
            if placement.cell == cell:
                return placement
        return None

    def source_of(self, cell: tuple[int, int]) -> CellPlacement | None:
        """The given tile whose reflection belongs at ``cell``."""

        for given in self.givens:
            if any(image.cell == cell for image in reflections(given, self.axis)):
                return given
        return None

    def target_side(self, cell: tuple[int, int]) -> bool:
        """True for cells on the mirror side(s), where the child builds."""

        row, col = cell
        given_side_col = self.givens[0].col < HALF_COLS
        given_side_row = self.givens[0].row < HALF_ROWS
        if self.axis is MirrorAxis.VERTICAL:
            return (col < HALF_COLS) != given_side_col
        if self.axis is MirrorAxis.HORIZONTAL:
            return (row < HALF_ROWS) != given_side_row
        return (col < HALF_COLS) != given_side_col or (row < HALF_ROWS) != given_side_row


# ---------------------------------------------------------------------------
# Difficulty ladder
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LevelSpec:
    """One rung of the ladder (levels 1..5)."""

    axis: MirrorAxis
    sources: tuple[int, int]          # min/max given tiles
    shapes: tuple[ShapeKind, ...]
    oriented_min: int                 # given tiles that must face a mirrored way
    colours: int                      # palette size per mosaic
    decoys: int                       # extra tile kinds besides the needed ones
    near_mirror: bool = False         # rung 1: tiles touch / almost touch the line
    flip_chance: float = 0.0          # picture on the right (or bottom) instead
    offer_unreflected: bool = False   # oriented tiles also come unmirrored
    tray_max: int = MAX_TRAY          # keep the kit small enough to scan


LEVELS: Final[dict[int, LevelSpec]] = {
    1: LevelSpec(MirrorAxis.VERTICAL, (2, 3), (ShapeKind.CIRCLE, ShapeKind.SQUARE, ShapeKind.HEART), 0, 3, 1, near_mirror=True),
    2: LevelSpec(MirrorAxis.VERTICAL, (3, 4), SYMMETRIC, 0, 4, 2, flip_chance=0.34),
    3: LevelSpec(
        MirrorAxis.VERTICAL, (3, 3), (*SYMMETRIC, ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE), 2, 4, 1,
        flip_chance=0.34, offer_unreflected=True, tray_max=6,
    ),
    4: LevelSpec(
        MirrorAxis.HORIZONTAL, (3, 3), (ShapeKind.CIRCLE, ShapeKind.SQUARE, ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE, ShapeKind.HEART),
        2, 4, 1, offer_unreflected=True, tray_max=6,
    ),
    5: LevelSpec(
        MirrorAxis.BOTH, (1, 2), (ShapeKind.CIRCLE, ShapeKind.SQUARE, ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE, ShapeKind.HEART, ShapeKind.RHOMBUS),
        1, 3, 1, tray_max=6,
    ),
}


class MirrorRoundFactory:
    """Create mosaics for a rung from an injected RNG (deterministic per seed)."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[MosaicPuzzle, ...]:
        _require_level(level)
        return tuple(self.build(level, index) for index in range(count))

    def build(self, level: int, index: int) -> MosaicPuzzle:
        _require_level(level)
        spec = LEVELS[level]
        rng = self._rng
        pid = f"L{level}-M{index + 1}-{rng.randrange(1_000_000):06d}"
        low, high = spec.sources
        count = low + (index % (high - low + 1)) if spec.axis is MirrorAxis.BOTH else rng.randint(low, high)
        flipped = rng.random() < spec.flip_chance
        cells = self._cells(spec, count, flipped)
        palette = rng.sample(range(COLOUR_COUNT), spec.colours)
        oriented_slots = set(rng.sample(range(count), min(count, spec.oriented_min)))
        givens = tuple(
            CellPlacement(row, col, self._piece(spec, palette, oriented=i in oriented_slots))
            for i, (row, col) in enumerate(cells)
        )
        required = tuple(image for given in givens for image in reflections(given, spec.axis))
        return MosaicPuzzle(pid, spec.axis, givens, required, self._tray(spec, givens, required, palette))

    # -- generation helpers ---------------------------------------------------

    def _region(self, spec: LevelSpec, flipped: bool) -> list[tuple[int, int]]:
        if spec.axis is MirrorAxis.VERTICAL:
            cols = range(HALF_COLS, GRID_COLS) if flipped else range(HALF_COLS)
            if spec.near_mirror:
                cols = (HALF_COLS, HALF_COLS + 1) if flipped else (HALF_COLS - 2, HALF_COLS - 1)
            return [(r, c) for r in range(GRID_ROWS) for c in cols]
        if spec.axis is MirrorAxis.HORIZONTAL:
            rows = range(HALF_ROWS, GRID_ROWS) if flipped else range(HALF_ROWS)
            return [(r, c) for r in rows for c in range(GRID_COLS)]
        return [(r, c) for r in range(HALF_ROWS) for c in range(HALF_COLS)]

    def _touches_mirror(self, spec: LevelSpec, cell: tuple[int, int]) -> bool:
        row, col = cell
        near_col = col in (HALF_COLS - 1, HALF_COLS)
        near_row = row in (HALF_ROWS - 1, HALF_ROWS)
        if spec.axis is MirrorAxis.VERTICAL:
            return near_col
        if spec.axis is MirrorAxis.HORIZONTAL:
            return near_row
        return near_col or near_row

    def _cells(self, spec: LevelSpec, count: int, flipped: bool) -> list[tuple[int, int]]:
        rng = self._rng
        region = self._region(spec, flipped)
        if spec.near_mirror:
            # Rung 1: each tile in its own row, touching or one step from the line.
            rows = rng.sample(range(GRID_ROWS), count)
            cols = sorted({c for _, c in region}, key=lambda c: abs(c - (HALF_COLS - 0.5)))
            return [(row, rng.choice(cols) if rng.random() < 0.5 else cols[0]) for row in rows]
        # A small cluster grown from the mirror line reads as one designed mosaic.
        start = rng.choice([cell for cell in region if self._touches_mirror(spec, cell)])
        chosen = [start]
        while len(chosen) < count:
            frontier = [
                cell
                for cell in region
                if cell not in chosen
                and any(abs(cell[0] - r) <= 1 and abs(cell[1] - c) <= 1 for r, c in chosen)
            ]
            chosen.append(rng.choice(frontier))
        return chosen

    def _piece(self, spec: LevelSpec, palette: Sequence[int], *, oriented: bool) -> Piece:
        rng = self._rng
        colour = rng.choice(palette)
        if oriented:
            kinds = [k for k in spec.shapes if k in ORIENTED and _turns_in(k, spec.axis)]
            kind = rng.choice(kinds)
            return Piece(kind, colour, rng.choice(_mirror_sensitive_rotations(kind, spec.axis)))
        kind = rng.choice(spec.shapes)
        if kind in ORIENTED and spec.oriented_min:
            return Piece(kind, colour, rng.choice(_rotations(kind)))
        return Piece(kind, colour, 0)

    def _tray(
        self,
        spec: LevelSpec,
        givens: Sequence[CellPlacement],
        required: Sequence[CellPlacement],
        palette: Sequence[int],
    ) -> tuple[Piece, ...]:
        rng = self._rng
        needed: list[Piece] = []
        for placement in required:
            if placement.piece not in needed:
                needed.append(placement.piece)
        tray = list(needed)
        if spec.offer_unreflected:
            # The unmirrored copy of an oriented tile: choosing the mirrored
            # orientation becomes a real decision.
            for given in givens:
                if given.piece.kind in ORIENTED and given.piece not in tray and len(tray) < spec.tray_max:
                    tray.append(given.piece)
        wanted = max(2, min(spec.tray_max, len(tray) + spec.decoys))
        attempts = 0
        while len(tray) < wanted and attempts < 200:
            attempts += 1
            decoy = self._decoy(spec, needed, palette)
            if decoy not in tray:
                tray.append(decoy)
        rng.shuffle(tray)
        return tuple(tray)

    def _decoy(self, spec: LevelSpec, needed: Sequence[Piece], palette: Sequence[int]) -> Piece:
        """A near miss: a needed shape in another colour, or another shape."""

        rng = self._rng
        base = rng.choice(list(needed))
        colours = list(palette) + [c for c in range(COLOUR_COUNT) if c not in palette][:1]
        if rng.random() < 0.5:
            kind = base.kind
            colour = rng.choice([c for c in colours if c != base.color_index] or colours)
        else:
            kind = rng.choice([k for k in spec.shapes if k is not base.kind] or list(spec.shapes))
            colour = base.color_index
        rotation = 0
        if kind in ORIENTED:
            rotation = base.rotation if base.kind is kind else rng.choice(_rotations(kind))
        return Piece(kind, colour, rotation)


def _rotations(kind: ShapeKind) -> tuple[int, ...]:
    if kind is ShapeKind.HEART:
        return (0, 2)
    if kind in ORIENTED:
        return (0, 1, 2, 3)
    return (0,)


def _turns_in(kind: ShapeKind, axis: MirrorAxis) -> bool:
    """Can this shape look different in the mirror for ``axis``?"""

    if kind is ShapeKind.HEART:
        return axis is not MirrorAxis.VERTICAL
    return kind in ORIENTED


def _mirror_sensitive_rotations(kind: ShapeKind, axis: MirrorAxis) -> tuple[int, ...]:
    """Rotations whose reflection differs from the original for ``axis``."""

    if kind is ShapeKind.HEART:
        return (0, 2)
    if axis is MirrorAxis.VERTICAL:
        return (1, 3)
    if axis is MirrorAxis.HORIZONTAL:
        return (0, 2)
    return (0, 1, 2, 3)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class PlaceOutcome(StrEnum):
    CORRECT = "correct"
    WRONG_PIECE = "wrong_piece"   # right spot, but another tile belongs there
    WRONG_CELL = "wrong_cell"     # nothing belongs on that spot
    IGNORED = "ignored"           # not a playable cell / no puzzle


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Evidence from one finished mosaic for adaptation."""

    first_attempt_success: bool
    hints_used: int
    used_retry: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class PlaceResult:
    """What one placement did; ``focus`` is the target a hint should explain."""

    outcome: PlaceOutcome
    focus: CellPlacement | None = None
    puzzle_completed: bool = False
    session_complete: bool = False

    @property
    def correct(self) -> bool:
        return self.outcome is PlaceOutcome.CORRECT


class MirrorSession:
    """Own the current mosaic, the placed tiles, misses and the facts of a set."""

    def __init__(
        self,
        puzzles: Sequence[MosaicPuzzle],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(puzzles) != CHALLENGE_COUNT:
            raise ValueError(f"a Specchi Magici set has exactly {CHALLENGE_COUNT} mosaics")
        self._puzzles = tuple(puzzles)
        self.level = level
        self._index = 0
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None
        self._finished = 0
        self.placed: dict[tuple[int, int], Piece] = {}
        self.misses = 0
        self.hints = 0

    # -- state ------------------------------------------------------------------

    @property
    def current_puzzle(self) -> MosaicPuzzle | None:
        if self._index >= len(self._puzzles):
            return None
        return self._puzzles[self._index]

    @property
    def puzzle_index(self) -> int:
        return self._index

    @property
    def finished_count(self) -> int:
        return self._finished

    @property
    def puzzle_done(self) -> bool:
        puzzle = self.current_puzzle
        return puzzle is not None and all(self.placed.get(r.cell) == r.piece for r in puzzle.required)

    @property
    def is_complete(self) -> bool:
        return self._finished >= len(self._puzzles)

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    def piece_at(self, cell: tuple[int, int]) -> Piece | None:
        """The tile shown at ``cell``: a given one or one the child placed."""

        puzzle = self.current_puzzle
        if puzzle is None:
            return None
        for given in puzzle.givens:
            if given.cell == cell:
                return given.piece
        return self.placed.get(cell)

    def is_open(self, cell: tuple[int, int]) -> bool:
        """An empty mirror-side cell the child can build on."""

        puzzle = self.current_puzzle
        return puzzle is not None and puzzle.target_side(cell) and cell not in self.placed

    def next_unmatched(self) -> CellPlacement | None:
        """The missing reflection to hint at next (closest to the mirror first)."""

        puzzle = self.current_puzzle
        if puzzle is None:
            return None
        missing = [r for r in puzzle.required if self.placed.get(r.cell) != r.piece]
        if not missing:
            return None
        return min(missing, key=lambda r: (_mirror_distance(r.cell, puzzle.axis), r.row, r.col))

    # -- actions ----------------------------------------------------------------

    def place(self, piece: Piece, cell: tuple[int, int]) -> PlaceResult:
        """Try ``piece`` at ``cell``; only a matching reflection stays."""

        puzzle = self.current_puzzle
        if puzzle is None or self.puzzle_done or not self.is_open(cell):
            return PlaceResult(PlaceOutcome.IGNORED)
        target = puzzle.target_at(cell)
        if target is None:
            self.misses += 1
            return PlaceResult(PlaceOutcome.WRONG_CELL, focus=self.next_unmatched())
        if target.piece != piece:
            self.misses += 1
            return PlaceResult(PlaceOutcome.WRONG_PIECE, focus=target)
        self.placed[cell] = piece
        if not self.puzzle_done:
            return PlaceResult(PlaceOutcome.CORRECT, focus=target)
        self._record_finished()
        return PlaceResult(PlaceOutcome.CORRECT, focus=target, puzzle_completed=True, session_complete=self.is_complete)

    def note_hint(self) -> None:
        self.hints += 1

    def next_puzzle(self) -> bool:
        """Show the next mosaic once the current one is finished."""

        if not self.puzzle_done or self._index >= len(self._puzzles):
            return False
        self._index += 1
        self.placed = {}
        self.misses = 0
        self.hints = 0
        return self.current_puzzle is not None

    def _record_finished(self) -> None:
        first = self.misses == 0
        summary = AttemptSummary(first_attempt_success=first, hints_used=min(32, self.misses + self.hints), used_retry=self.misses > 0)
        self._history.append(summary)
        del self._history[:-HISTORY_LIMIT]
        self._finished += 1
        self._pending_milestone = {
            "level": self.level,
            "puzzle_index": self._index + 1,
            "first_attempt": int(first),
        }

    def consume_milestone(self) -> dict[str, int] | None:
        fact = self._pending_milestone
        self._pending_milestone = None
        return fact

    def consume_completion(self) -> dict[str, int] | None:
        if not self.is_complete or self._completion_consumed:
            return None
        self._completion_consumed = True
        recent = self._history[-CHALLENGE_COUNT:]
        return {
            "level": self.level,
            "first_attempt_count": sum(item.first_attempt_success for item in recent),
            "retries": sum(item.used_retry for item in recent),
        }


def _mirror_distance(cell: tuple[int, int], axis: MirrorAxis) -> int:
    row, col = cell
    dc = min(abs(col - (HALF_COLS - 1)), abs(col - HALF_COLS))
    dr = min(abs(row - (HALF_ROWS - 1)), abs(row - HALF_ROWS))
    if axis is MirrorAxis.VERTICAL:
        return dc
    if axis is MirrorAxis.HORIZONTAL:
        return dr
    return dc + dr


def adapt_level(current: int, history: Sequence[AttemptSummary]) -> int:
    """Bounded between-set adaptation across levels 1..5."""

    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 6:
            return min(MAX_LEVEL, current + 1)
    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 1 for item in last_three):
            return max(1, current - 1)
    return current


def _require_level(level: int) -> None:
    if not (1 <= level <= MAX_LEVEL):
        raise ValueError(f"level must be in 1..{MAX_LEVEL}")
