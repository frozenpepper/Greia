"""Domain model for Specchi Magici (Magic Mirrors).

Owns geometric symmetry invariants, exact vertical reflection across an 8x6 board,
deterministic mosaic puzzle generation, bounded adaptation, and milestone/completion facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Final, Sequence


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CHALLENGE_COUNT: Final = 6
GRID_COLS: Final = 8
GRID_ROWS: Final = 6
HISTORY_LIMIT: Final = 8


class ShapeKind(StrEnum):
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    SEMICIRCLE = "semicircle"


@dataclass(frozen=True, slots=True)
class Piece:
    """A geometric shape piece with color and discrete 90-degree rotation (0..3)."""

    kind: ShapeKind
    color_index: int
    rotation: int = 0

    def __post_init__(self) -> None:
        if not (0 <= self.rotation <= 3):
            raise ValueError("rotation must be in 0..3")
        if not (0 <= self.color_index <= 5):
            raise ValueError("color_index must be in 0..5")


def reflect_piece(piece: Piece) -> Piece:
    """Compute the exact reflection across a vertical mirror axis."""
    if piece.kind in {ShapeKind.CIRCLE, ShapeKind.SQUARE}:
        return Piece(piece.kind, piece.color_index, 0)

    # For TRIANGLE and SEMICIRCLE:
    # 0 (UP) -> 0 (UP)
    # 1 (RIGHT) -> 3 (LEFT)
    # 2 (DOWN) -> 2 (DOWN)
    # 3 (LEFT) -> 1 (RIGHT)
    mirrored_rot = (4 - piece.rotation) % 4
    return Piece(piece.kind, piece.color_index, mirrored_rot)


def mirror_col(col: int) -> int:
    """Reflect column index across the central axis between columns 3 and 4."""
    if not (0 <= col < GRID_COLS):
        raise ValueError(f"col must be in 0..{GRID_COLS - 1}")
    return (GRID_COLS - 1) - col


@dataclass(frozen=True, slots=True)
class CellPlacement:
    """Piece placed at an authoritative grid coordinate (row, col)."""

    row: int
    col: int
    piece: Piece

    def __post_init__(self) -> None:
        if not (0 <= self.row < GRID_ROWS):
            raise ValueError(f"row must be in 0..{GRID_ROWS - 1}")
        if not (0 <= self.col < GRID_COLS):
            raise ValueError(f"col must be in 0..{GRID_COLS - 1}")


@dataclass(frozen=True, slots=True)
class MosaicPuzzle:
    """One discrete symmetry puzzle on the 8x6 board."""

    puzzle_id: str
    givens: tuple[CellPlacement, ...]
    required: tuple[CellPlacement, ...]
    tray_pieces: tuple[Piece, ...]

    def __post_init__(self) -> None:
        if not self.puzzle_id:
            raise ValueError("puzzle_id must not be empty")
        if not self.givens:
            raise ValueError("givens must not be empty")
        if not self.required:
            raise ValueError("required must not be empty")


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Evidence from one completed symmetry puzzle for adaptation."""

    first_attempt_success: bool
    hints_used: int
    used_retry: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """Result returned by a piece placement or undo action."""

    correct: bool
    puzzle_completed: bool
    session_complete: bool
    first_attempt_success: bool
    hints_used: int
    used_retry: bool


class MirrorRoundFactory:
    """Create deterministic symmetry puzzles from an injected RNG."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[MosaicPuzzle, ...]:
        _require_level(level)
        puzzles: list[MosaicPuzzle] = []
        for index in range(count):
            puzzles.append(self._generate_puzzle(level, index))
        return tuple(puzzles)

    def _generate_puzzle(self, level: int, index: int) -> MosaicPuzzle:
        pid = f"L{level}-M{index + 1}-{self._rng.randrange(1_000_000):06d}"

        # Determine piece shapes and counts per level
        if level == 1:
            kinds = [ShapeKind.CIRCLE, ShapeKind.SQUARE]
            num_pieces = 2 + (index % 2)
            rotations = [0]
        elif level == 2:
            kinds = [ShapeKind.CIRCLE, ShapeKind.SQUARE, ShapeKind.TRIANGLE]
            num_pieces = 3
            rotations = [0, 2]
        elif level == 3:
            kinds = [ShapeKind.CIRCLE, ShapeKind.SQUARE, ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE]
            num_pieces = 3 + (index % 2)
            rotations = [0, 1, 2, 3]
        elif level == 4:
            kinds = [ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE, ShapeKind.CIRCLE, ShapeKind.SQUARE]
            num_pieces = 4
            rotations = [0, 1, 2, 3]
        else:
            # Level 5
            kinds = [ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE, ShapeKind.CIRCLE, ShapeKind.SQUARE]
            num_pieces = 4
            rotations = [0, 1, 2, 3]

        # Generate left-side placements (cols 0..3)
        available_cells = [(r, c) for r in range(GRID_ROWS) for c in range(4)]
        picked_cells = self._rng.sample(available_cells, num_pieces)

        givens_list: list[CellPlacement] = []
        required_list: list[CellPlacement] = []

        for r, c in picked_cells:
            kind = self._rng.choice(kinds)
            color_idx = self._rng.randint(0, 4)
            rot = self._rng.choice(rotations) if kind in {ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE} else 0
            left_piece = Piece(kind, color_idx, rot)
            right_piece = reflect_piece(left_piece)

            mc = mirror_col(c)

            if level == 5 and self._rng.random() < 0.35:
                # Two-sided symmetry: given on right side, required on left side
                givens_list.append(CellPlacement(r, mc, right_piece))
                required_list.append(CellPlacement(r, c, left_piece))
            else:
                # Standard: given on left, required on right
                givens_list.append(CellPlacement(r, c, left_piece))
                required_list.append(CellPlacement(r, mc, right_piece))

        # Tray contains the exact required pieces, shuffled
        tray = [req.piece for req in required_list]
        self._rng.shuffle(tray)

        return MosaicPuzzle(
            puzzle_id=pid,
            givens=tuple(givens_list),
            required=tuple(required_list),
            tray_pieces=tuple(tray),
        )


class MirrorSession:
    """Own active puzzle state, placed grid cells, tray inventory, undo, and facts."""

    def __init__(
        self,
        puzzles: Sequence[MosaicPuzzle],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(puzzles) != CHALLENGE_COUNT:
            raise ValueError(f"a Specchi Magici session requires exactly {CHALLENGE_COUNT} puzzles")
        self._puzzles = tuple(puzzles)
        self.level = level
        self._index = 0
        self._attempts_this_puzzle = 0
        self._hints_this_puzzle = 0
        self._used_retry_this_puzzle = False
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None

        # Interactive state for current puzzle
        self.grid: dict[tuple[int, int], Piece] = {}
        self.tray: list[Piece] = []
        self.selected_tray_index: int | None = None
        self.undo_stack: list[tuple[int, int]] = []
        self._load_current_puzzle()

    @property
    def current_puzzle(self) -> MosaicPuzzle | None:
        if self.is_complete:
            return None
        return self._puzzles[self._index]

    @property
    def puzzle_index(self) -> int:
        return self._index

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._puzzles)

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    def _load_current_puzzle(self) -> None:
        p = self.current_puzzle
        if p is None:
            return
        self.grid = {(g.row, g.col): g.piece for g in p.givens}
        self.tray = list(p.tray_pieces)
        self.selected_tray_index = 0 if self.tray else None
        self.undo_stack = []

    def select_tray_index(self, index: int) -> bool:
        if 0 <= index < len(self.tray):
            self.selected_tray_index = index
            return True
        return False

    def place_selected_at(self, row: int, col: int) -> AttemptResult | None:
        """Place the selected tray piece onto cell (row, col)."""
        p = self.current_puzzle
        if p is None or self.selected_tray_index is None:
            return None
        if not (0 <= row < GRID_ROWS and 0 <= col < GRID_COLS):
            return None
        if (row, col) in self.grid:
            # Cell is already occupied
            return None

        piece = self.tray[self.selected_tray_index]
        self._attempts_this_puzzle += 1

        # Find expected piece at (row, col)
        expected = next((req for req in p.required if req.row == row and req.col == col), None)

        if expected is None or expected.piece != piece:
            # Incorrect placement: reject and wobble
            self._hints_this_puzzle += 1
            self._used_retry_this_puzzle = True
            return AttemptResult(
                correct=False,
                puzzle_completed=False,
                session_complete=False,
                first_attempt_success=False,
                hints_used=self._hints_this_puzzle,
                used_retry=self._used_retry_this_puzzle,
            )

        # Correct placement!
        self.grid[(row, col)] = piece
        self.tray.pop(self.selected_tray_index)
        self.undo_stack.append((row, col))
        self.selected_tray_index = 0 if self.tray else None

        # Check if all required pieces are placed
        puzzle_done = all(self.grid.get((req.row, req.col)) == req.piece for req in p.required)
        return self._evaluate_completion(puzzle_done)

    def undo(self) -> bool:
        """Undo last correct piece placement."""
        if not self.undo_stack:
            return False
        row, col = self.undo_stack.pop()
        piece = self.grid.pop((row, col), None)
        if piece is not None:
            self.tray.append(piece)
            self.selected_tray_index = len(self.tray) - 1
            return True
        return False

    def _evaluate_completion(self, puzzle_done: bool) -> AttemptResult:
        if not puzzle_done:
            return AttemptResult(
                correct=True,
                puzzle_completed=False,
                session_complete=False,
                first_attempt_success=not self._used_retry_this_puzzle,
                hints_used=self._hints_this_puzzle,
                used_retry=self._used_retry_this_puzzle,
            )

        first_attempt = self._attempts_this_puzzle == len(self.current_puzzle.required) and not self._used_retry_this_puzzle
        summary = AttemptSummary(
            first_attempt_success=first_attempt,
            hints_used=self._hints_this_puzzle,
            used_retry=self._used_retry_this_puzzle,
        )
        self._history.append(summary)
        del self._history[:-HISTORY_LIMIT]

        self._pending_milestone = {
            "level": self.level,
            "puzzle_index": self._index + 1,
            "first_attempt": int(first_attempt),
        }

        self._index += 1
        session_complete = self.is_complete
        result = AttemptResult(
            correct=True,
            puzzle_completed=True,
            session_complete=session_complete,
            first_attempt_success=first_attempt,
            hints_used=summary.hints_used,
            used_retry=summary.used_retry,
        )
        self._attempts_this_puzzle = 0
        self._hints_this_puzzle = 0
        self._used_retry_this_puzzle = False
        self._load_current_puzzle()
        return result

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


def adapt_level(current: int, history: Sequence[AttemptSummary]) -> int:
    """Bounded between-set adaptation policy across levels 1..5."""
    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 6:
            return min(5, current + 1)

    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 1 for item in last_three):
            return max(1, current - 1)
    return current


def _require_level(level: int) -> None:
    if not (1 <= level <= 5):
        raise ValueError("level must be in 1..5")
