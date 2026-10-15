"""Tito's Marble Run — board state, hints and the visit ladder (no Pygame).

``BoardState`` is what the child edits: which tray piece sits in which slot
and which way each ramp runs. Pieces only ever go into the board's shining
slots, so every board stays solvable and keyboard/controller play needs no
free positioning. ``HintPlanner`` compares the board with the closest
authored solution (pieces of the same kind are interchangeable) and names the
single next helpful step: place a piece, turn a ramp, take a piece away, or
press GO. ``Visit`` walks one set of four boards; ``RampProgress`` is the
profile-scoped save.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

if __package__:
    from .ramp_content import (
        BOARD_SETS,
        BOARDS_PER_SET,
        Board,
        BoardSet,
        Capsule,
        Facing,
        PieceKind,
        Placement,
        piece_capsules,
    )
    from .ramp_engine import MarbleRun, shelf_capsules
else:
    from ramp_content import (
        BOARD_SETS,
        BOARDS_PER_SET,
        Board,
        BoardSet,
        Capsule,
        Facing,
        PieceKind,
        Placement,
        piece_capsules,
    )
    from ramp_engine import MarbleRun, shelf_capsules

SNAP_AFTER_MISSES: Final = 3  # from the third miss on a board, the demo also places the piece


class HintAction(StrEnum):
    PLACE = "place"
    TURN = "turn"
    REMOVE = "remove"
    GO = "go"


@dataclass(frozen=True, slots=True)
class HintStep:
    """One concrete next step towards a solution."""

    action: HintAction
    slot: int | None = None
    kind: PieceKind | None = None
    facing: Facing = Facing.RIGHT


@dataclass(slots=True)
class BoardSummary:
    runs: int = 0
    misses: int = 0
    hints: int = 0


class BoardState:
    """The child's arrangement of tray pieces on one board."""

    def __init__(self, board: Board) -> None:
        self.board = board
        count = len(board.pieces)
        self.facings: list[Facing] = [Facing.RIGHT] * count
        self.slot_of: list[int | None] = [None] * count
        self.selected: int | None = 0 if count else None
        self.summary = BoardSummary()
        self.revision = 0  # bumps on every arrangement change (render caches)

    # -- queries ---------------------------------------------------------------

    def kind(self, piece: int) -> PieceKind:
        return self.board.pieces[piece]

    def occupant(self, slot: int) -> int | None:
        for piece, where in enumerate(self.slot_of):
            if where == slot:
                return piece
        return None

    def in_tray(self, piece: int) -> bool:
        return self.slot_of[piece] is None

    def tray_pieces(self) -> list[int]:
        return [piece for piece, where in enumerate(self.slot_of) if where is None]

    def placements(self) -> tuple[Placement, ...]:
        return tuple(
            Placement(piece, where, self.facings[piece])
            for piece, where in enumerate(self.slot_of)
            if where is not None
        )

    def arrangement(self) -> dict[int, tuple[PieceKind, Facing]]:
        """Slot -> (kind, facing); what the physics sees (piece identity is irrelevant)."""

        return {p.slot: (self.kind(p.piece), _norm(self.kind(p.piece), p.facing)) for p in self.placements()}

    def colliders(self) -> tuple[Capsule, ...]:
        board = self.board
        result: list[Capsule] = list(shelf_capsules(board.shelves))
        for placement in self.placements():
            result.extend(
                piece_capsules(
                    self.kind(placement.piece),
                    placement.facing,
                    board.slots[placement.slot],
                    f"piece:{placement.slot}",
                )
            )
        return tuple(result)

    def new_run(self) -> MarbleRun:
        return MarbleRun(self.board.start, self.board.basket, self.colliders())

    # -- edits -----------------------------------------------------------------

    def select(self, piece: int) -> bool:
        if not (0 <= piece < len(self.slot_of)) or not self.in_tray(piece):
            return False
        self.selected = piece
        return True

    def place(self, piece: int, slot: int) -> int | None:
        """Put ``piece`` into ``slot``; a piece already there goes back to the tray.

        Returns the displaced piece (if any). A piece moved from another slot
        leaves that slot empty.
        """

        if not (0 <= slot < len(self.board.slots)):
            raise ValueError("no such slot")
        displaced = self.occupant(slot)
        if displaced == piece:
            return None
        if displaced is not None:
            self.slot_of[displaced] = None
        self.slot_of[piece] = slot
        self._reselect(prefer=displaced)
        self.revision += 1
        return displaced

    def place_selected(self, slot: int) -> int | None:
        """Place the selected tray piece; returns the placed piece or ``None``."""

        piece = self.selected
        if piece is None or not self.in_tray(piece):
            tray = self.tray_pieces()
            if not tray:
                return None
            piece = tray[0]
        self.place(piece, slot)
        return piece

    def remove(self, piece: int) -> bool:
        if self.slot_of[piece] is None:
            return False
        self.slot_of[piece] = None
        self.selected = piece
        self.revision += 1
        return True

    def turn(self, piece: int) -> bool:
        """Turn a ramp the other way (other pieces look the same both ways)."""

        if self.kind(piece) is not PieceKind.RAMP:
            return False
        self.facings[piece] = self.facings[piece].flipped()
        self.revision += 1
        return True

    def clear(self) -> None:
        self.slot_of = [None] * len(self.slot_of)
        self.selected = 0 if self.slot_of else None
        self.revision += 1

    def _reselect(self, prefer: int | None = None) -> None:
        if prefer is not None and self.in_tray(prefer):
            self.selected = prefer
            return
        tray = self.tray_pieces()
        if self.selected is not None and self.selected in tray:
            return
        self.selected = tray[0] if tray else None

    # -- solutions ---------------------------------------------------------------

    def solution_arrangement(self, solution: tuple[Placement, ...]) -> dict[int, tuple[PieceKind, Facing]]:
        return {p.slot: (self.kind(p.piece), _norm(self.kind(p.piece), p.facing)) for p in solution}

    def solved_by(self, solution: tuple[Placement, ...]) -> bool:
        return self.arrangement() == self.solution_arrangement(solution)


def _norm(kind: PieceKind, facing: Facing) -> Facing:
    return facing if kind is PieceKind.RAMP else Facing.RIGHT


class HintPlanner:
    """Name the single next step from the child's board towards a solution."""

    @staticmethod
    def closest_solution(state: BoardState) -> tuple[Placement, ...]:
        current = state.arrangement()
        best = state.board.solutions[0]
        best_score = -1
        for solution in state.board.solutions:
            wanted = state.solution_arrangement(solution)
            score = sum(1 for slot, item in wanted.items() if current.get(slot) == item)
            score -= sum(1 for slot in current if slot not in wanted)
            if score > best_score:
                best, best_score = solution, score
        return best

    @classmethod
    def next_step(cls, state: BoardState) -> HintStep:
        current = state.arrangement()
        wanted = state.solution_arrangement(cls.closest_solution(state))
        # A ramp of the right kind in the right slot that runs the wrong way: turn it.
        for slot in sorted(wanted):
            kind, facing = wanted[slot]
            have = current.get(slot)
            if have is not None and have[0] is kind and have[1] is not facing:
                return HintStep(HintAction.TURN, slot, kind, facing)
        # A piece where the solution wants nothing (or another kind): take it away.
        for slot in sorted(current):
            want = wanted.get(slot)
            if want is None or want[0] is not current[slot][0]:
                return HintStep(HintAction.REMOVE, slot, current[slot][0], current[slot][1])
        for slot in sorted(wanted):
            if slot not in current:
                kind, facing = wanted[slot]
                return HintStep(HintAction.PLACE, slot, kind, facing)
        return HintStep(HintAction.GO)

    @classmethod
    def apply(cls, state: BoardState, step: HintStep) -> bool:
        """Carry out a hint step on the board (the snap after repeated misses)."""

        if step.action is HintAction.GO or step.slot is None:
            return False
        piece = state.occupant(step.slot)
        if step.action is HintAction.TURN and piece is not None:
            return state.turn(piece)
        if step.action is HintAction.REMOVE and piece is not None:
            return state.remove(piece)
        if step.action is HintAction.PLACE and step.kind is not None:
            candidates = [p for p in state.tray_pieces() if state.kind(p) is step.kind]
            if not candidates:
                candidates = [
                    p for p in range(len(state.slot_of))
                    if state.kind(p) is step.kind and state.slot_of[p] not in cls._wanted_slots(state)
                ]
            if not candidates:
                return False
            piece = candidates[0]
            if state.facings[piece] is not step.facing and step.kind is PieceKind.RAMP:
                state.facings[piece] = step.facing
            state.place(piece, step.slot)
            return True
        return False

    @classmethod
    def _wanted_slots(cls, state: BoardState) -> set[int]:
        current = state.arrangement()
        wanted = state.solution_arrangement(cls.closest_solution(state))
        return {slot for slot, item in wanted.items() if current.get(slot) == item}


# -- progress + visit ------------------------------------------------------------


@dataclass(slots=True)
class RampProgress:
    """Profile-scoped save: which set comes next and simple lifetime counters.

    ``legacy_best_times`` keeps the first release's per-level best times
    untouched (child data is never dropped by a migration).
    """

    next_set: int = 0
    boards_solved: int = 0
    sets_completed: int = 0
    legacy_best_times: dict[str, float] = field(default_factory=dict)


class Visit:
    """One set of four boards, played to the shared completion scene."""

    def __init__(self, progress: RampProgress) -> None:
        self.progress = progress
        self.set_index = progress.next_set % len(BOARD_SETS)
        self.index = 0
        self.state = BoardState(self.board_set.boards[0])

    @property
    def board_set(self) -> BoardSet:
        return BOARD_SETS[self.set_index]

    @property
    def board(self) -> Board:
        return self.state.board

    @property
    def total(self) -> int:
        return BOARDS_PER_SET

    @property
    def completed(self) -> int:
        return self.index

    @property
    def complete(self) -> bool:
        return self.index >= self.total

    def finish_board(self) -> None:
        self.progress.boards_solved += 1
        self.index += 1

    def next_board(self) -> None:
        if not self.complete:
            self.state = BoardState(self.board_set.boards[self.index])

    def finish_set(self) -> None:
        self.progress.sets_completed += 1
        self.progress.next_set = (self.set_index + 1) % len(BOARD_SETS)

    def start_next_set(self) -> None:
        self.set_index = self.progress.next_set % len(BOARD_SETS)
        self.index = 0
        self.state = BoardState(self.board_set.boards[0])


__all__ = [
    "BoardState",
    "BoardSummary",
    "HintAction",
    "HintPlanner",
    "HintStep",
    "RampProgress",
    "SNAP_AFTER_MISSES",
    "Visit",
]
