"""Pure game model for Quattro Amici in Fila (no Pygame).

* ``QuattroBoard`` — the standing drop grid: gravity, lines, threats.
* ``LeoBrain`` — how Leo picks a column. Three substitutable strategies
  (easy / medium / smart) share one narrow protocol; ``kindness`` makes any of
  them slip a little more after the child has lost games in a row.
* ``QuattroGame`` — one game: turns, wins, draws, block detection.
* ``QuattroMatch`` — best of three games with alternating first player.
* ``adapt_stage`` — the automatic, kind difficulty ladder between matches.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Protocol, Sequence

if __package__:
    from .quattro_content import (
        FIRST_STAGE,
        GAMES_PER_MATCH,
        LAST_STAGE,
        WINS_FOR_MATCH,
        GameMode,
        GameStatus,
        LeoStyle,
        Player,
        Stage,
        stage_for,
    )
else:
    from quattro_content import (
        FIRST_STAGE,
        GAMES_PER_MATCH,
        LAST_STAGE,
        WINS_FOR_MATCH,
        GameMode,
        GameStatus,
        LeoStyle,
        Player,
        Stage,
        stage_for,
    )

_DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))  # (d_row, d_col): -, |, \, /
MAX_KINDNESS = 2


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------


class QuattroBoard:
    """Matrix of the vertical drop grid. ``grid[row][col]``, row 0 is the TOP."""

    def __init__(self, cols: int, rows: int, target_in_a_row: int) -> None:
        if cols < target_in_a_row and rows < target_in_a_row:
            raise ValueError("a row of the target length must fit on the board")
        self.cols = cols
        self.rows = rows
        self.target = target_in_a_row
        self.grid: list[list[Player]] = [[Player.EMPTY for _ in range(cols)] for _ in range(rows)]

    def can_drop(self, col: int) -> bool:
        return 0 <= col < self.cols and self.grid[0][col] == Player.EMPTY

    def valid_columns(self) -> list[int]:
        return [c for c in range(self.cols) if self.can_drop(c)]

    def landing_row(self, col: int) -> int:
        """Row a disc dropped in ``col`` would land on, or -1 when full/outside."""

        if not self.can_drop(col):
            return -1
        for r in range(self.rows - 1, -1, -1):
            if self.grid[r][col] == Player.EMPTY:
                return r
        return -1

    def drop_token(self, col: int, player: Player) -> int:
        """Drop with gravity; return the landing row or -1 if the column is full."""

        row = self.landing_row(col)
        if row >= 0:
            self.grid[row][col] = player
        return row

    def undo_drop(self, col: int) -> int:
        """Remove the top disc of ``col``; return the cleared row or -1."""

        if not 0 <= col < self.cols:
            return -1
        for r in range(self.rows):
            if self.grid[r][col] != Player.EMPTY:
                self.grid[r][col] = Player.EMPTY
                return r
        return -1

    def is_full(self) -> bool:
        return all(self.grid[0][c] != Player.EMPTY for c in range(self.cols))

    def is_empty(self) -> bool:
        return all(self.grid[self.rows - 1][c] == Player.EMPTY for c in range(self.cols))

    def run_through(self, row: int, col: int, d_row: int, d_col: int, player: Player) -> list[tuple[int, int]]:
        """Cells of ``player`` in one straight line through (row, col), in line order."""

        cells: list[tuple[int, int]] = []
        r, c = row - d_row, col - d_col
        while 0 <= r < self.rows and 0 <= c < self.cols and self.grid[r][c] == player:
            cells.insert(0, (r, c))
            r, c = r - d_row, c - d_col
        cells.append((row, col))
        r, c = row + d_row, col + d_col
        while 0 <= r < self.rows and 0 <= c < self.cols and self.grid[r][c] == player:
            cells.append((r, c))
            r, c = r + d_row, c + d_col
        return cells

    def line_at(self, row: int, col: int, target: int | None = None) -> list[tuple[int, int]]:
        """Winning cells through the disc at (row, col) (empty when no row)."""

        player = self.grid[row][col]
        if player == Player.EMPTY:
            return []
        need = self.target if target is None else target
        best: list[tuple[int, int]] = []
        for d_row, d_col in _DIRECTIONS:
            run = self.run_through(row, col, d_row, d_col, player)
            if len(run) >= need and len(run) > len(best):
                best = run
        return best

    def would_win(self, col: int, player: Player) -> bool:
        row = self.drop_token(col, player)
        if row < 0:
            return False
        try:
            return bool(self.line_at(row, col))
        finally:
            self.grid[row][col] = Player.EMPTY

    def winning_columns(self, player: Player) -> list[int]:
        """Columns where ``player`` would complete a row right now."""

        return [c for c in self.valid_columns() if self.would_win(c, player)]

    def gives_win_above(self, col: int, player: Player) -> bool:
        """True if dropping in ``col`` lets the opponent win on top of it."""

        row = self.drop_token(col, player)
        if row < 0:
            return False
        try:
            return self.can_drop(col) and self.would_win(col, player.opponent)
        finally:
            self.grid[row][col] = Player.EMPTY

    def check_win(self, target: int | None = None) -> tuple[Player, list[tuple[int, int]]]:
        """Full scan: (winner, sorted winning cells) or (EMPTY, [])."""

        need = self.target if target is None else target
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] != Player.EMPTY:
                    line = self.line_at(r, c, need)
                    if line:
                        return self.grid[r][c], sorted(line)
        return Player.EMPTY, []

    def clone(self) -> "QuattroBoard":
        copy = QuattroBoard(self.cols, self.rows, self.target)
        copy.grid = [row[:] for row in self.grid]
        return copy


def suggest_column(board: QuattroBoard, player: Player) -> tuple[int, str] | None:
    """Hint: a column that wins now, else one that blocks the opponent's row."""

    wins = board.winning_columns(player)
    if wins:
        return wins[0], "win"
    blocks = board.winning_columns(player.opponent)
    if blocks:
        return blocks[0], "block"
    return None


# ---------------------------------------------------------------------------
# Leo's brains
# ---------------------------------------------------------------------------


class LeoBrain(Protocol):
    """Choose Leo's column. ``kindness`` (0..2) makes Leo slip more often."""

    style: LeoStyle

    def choose(self, board: QuattroBoard, me: Player, rng: random.Random, kindness: int = 0) -> int: ...


def _center_weighted(columns: Sequence[int], cols: int, rng: random.Random) -> int:
    center = (cols - 1) / 2.0
    weights = [1.0 / (1.0 + abs(c - center)) for c in columns]
    return rng.choices(list(columns), weights=weights, k=1)[0]


def _chance(rng: random.Random, probability: float) -> bool:
    return rng.random() < max(0.0, min(1.0, probability))


@dataclass(frozen=True, slots=True)
class EasyLeo:
    """A playful first opponent: often misses wins and blocks."""

    style: LeoStyle = LeoStyle.EASY
    take_win: float = 0.6
    block: float = 0.35

    def choose(self, board: QuattroBoard, me: Player, rng: random.Random, kindness: int = 0) -> int:
        valid = board.valid_columns()
        if not valid:
            return -1
        wins = board.winning_columns(me)
        if wins and _chance(rng, self.take_win - 0.15 * kindness):
            return wins[0]
        blocks = board.winning_columns(me.opponent)
        if blocks and _chance(rng, self.block - 0.12 * kindness):
            return blocks[0]
        return _center_weighted(valid, board.cols, rng)


@dataclass(frozen=True, slots=True)
class MediumLeo:
    """Takes his wins, blocks obvious rows and does not gift a win above."""

    style: LeoStyle = LeoStyle.MEDIUM
    take_win: float = 0.95
    block: float = 0.9

    def choose(self, board: QuattroBoard, me: Player, rng: random.Random, kindness: int = 0) -> int:
        valid = board.valid_columns()
        if not valid:
            return -1
        wins = board.winning_columns(me)
        if wins and _chance(rng, self.take_win - 0.15 * kindness):
            return wins[0]
        blocks = board.winning_columns(me.opponent)
        if blocks and _chance(rng, self.block - 0.25 * kindness):
            return blocks[0]
        safe = [c for c in valid if not board.gives_win_above(c, me)]
        return _center_weighted(safe or valid, board.cols, rng)


@dataclass(frozen=True, slots=True)
class SmartLeo:
    """Also builds his own lines; still slips now and then (kid-friendly cap)."""

    style: LeoStyle = LeoStyle.SMART
    slip: float = 0.08

    def choose(self, board: QuattroBoard, me: Player, rng: random.Random, kindness: int = 0) -> int:
        valid = board.valid_columns()
        if not valid:
            return -1
        if _chance(rng, self.slip + 0.1 * kindness):
            return MediumLeo().choose(board, me, rng, kindness)
        wins = board.winning_columns(me)
        if wins:
            return wins[0]
        blocks = board.winning_columns(me.opponent)
        if blocks:
            return blocks[0]
        safe = [c for c in valid if not board.gives_win_above(c, me)] or valid
        scored = sorted(((self._score(board, c, me), c) for c in safe), reverse=True)
        best_score = scored[0][0]
        near = [c for score, c in scored if score >= best_score - 1.0]
        return rng.choice(near)

    @staticmethod
    def _score(board: QuattroBoard, col: int, me: Player) -> float:
        """Centre + the lines Leo would build here + the lines he would spoil."""

        center = (board.cols - 1) / 2.0
        score = 4.0 - abs(col - center)
        row = board.landing_row(col)
        for player, weight in ((me, 1.0), (me.opponent, 0.6)):
            board.grid[row][col] = player
            try:
                for d_row, d_col in _DIRECTIONS:
                    score += weight * len(board.run_through(row, col, d_row, d_col, player)) ** 2
            finally:
                board.grid[row][col] = Player.EMPTY
        return score


_BRAINS: dict[LeoStyle, LeoBrain] = {
    LeoStyle.EASY: EasyLeo(),
    LeoStyle.MEDIUM: MediumLeo(),
    LeoStyle.SMART: SmartLeo(),
}


def leo_brain_for(style: LeoStyle) -> LeoBrain:
    return _BRAINS[style]


# ---------------------------------------------------------------------------
# One game
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MoveRecord:
    col: int
    row: int
    player: Player


@dataclass(frozen=True, slots=True)
class DropResult:
    """What one drop did (for presentation and teaching moments)."""

    ok: bool
    col: int = -1
    row: int = -1
    player: Player = Player.EMPTY
    status: GameStatus = GameStatus.IN_PROGRESS
    blocked: bool = False  # the mover filled the opponent's winning hole


class QuattroGame:
    """One game on a stage board; ``starter`` drops first."""

    def __init__(self, stage: Stage, starter: Player = Player.FLASH) -> None:
        self.stage = stage
        self.board = QuattroBoard(stage.cols, stage.rows, stage.target)
        self.starter = starter
        self.current_player = starter
        self.status = GameStatus.IN_PROGRESS
        self.winner = Player.EMPTY
        self.winning_cells: list[tuple[int, int]] = []
        self.history: list[MoveRecord] = []

    @property
    def finished(self) -> bool:
        return self.status is not GameStatus.IN_PROGRESS

    def can_drop(self, col: int) -> bool:
        return not self.finished and self.board.can_drop(col)

    def drop(self, col: int) -> DropResult:
        if not self.can_drop(col):
            return DropResult(False, col)
        player = self.current_player
        threats = self.board.winning_columns(player.opponent)
        row = self.board.drop_token(col, player)
        self.history.append(MoveRecord(col, row, player))
        line = self.board.line_at(row, col)
        if line:
            self.status = GameStatus.WON
            self.winner = player
            self.winning_cells = line
        elif self.board.is_full():
            self.status = GameStatus.DRAW
        else:
            self.current_player = player.opponent
        return DropResult(True, col, row, player, self.status, blocked=col in threats and not line)


# ---------------------------------------------------------------------------
# Best-of-three match
# ---------------------------------------------------------------------------


class MatchOutcome(StrEnum):
    FLASH = "flash"
    LEO = "leo"
    TIE = "tie"


class QuattroMatch:
    """Up to three games; first to two wins. Draws count as played games."""

    def __init__(self, stage: Stage, mode: GameMode) -> None:
        self.stage = stage
        self.mode = mode
        self.results: list[Player] = []  # EMPTY = draw
        self.game = QuattroGame(stage, self._starter(0))
        self._recorded = False

    @staticmethod
    def _starter(index: int) -> Player:
        # Flash (the child) opens games 1 and 3; Leo opens game 2.
        return Player.FLASH if index % 2 == 0 else Player.LEO

    @property
    def game_index(self) -> int:
        return len(self.results)

    def wins(self, player: Player) -> int:
        return sum(1 for winner in self.results if winner == player)

    @property
    def over(self) -> bool:
        return (
            self.wins(Player.FLASH) >= WINS_FOR_MATCH
            or self.wins(Player.LEO) >= WINS_FOR_MATCH
            or len(self.results) >= GAMES_PER_MATCH
        )

    @property
    def outcome(self) -> MatchOutcome:
        flash, leo = self.wins(Player.FLASH), self.wins(Player.LEO)
        if flash > leo:
            return MatchOutcome.FLASH
        if leo > flash:
            return MatchOutcome.LEO
        return MatchOutcome.TIE

    def record_game(self) -> bool:
        """Store the finished current game's result once; True when stored."""

        if not self.game.finished or self._recorded:
            return False
        self.results.append(self.game.winner)
        self._recorded = True
        return True

    def next_game(self) -> QuattroGame:
        if self.over:
            raise RuntimeError("the match is over")
        self.game = QuattroGame(self.stage, self._starter(len(self.results)))
        self._recorded = False
        return self.game


# ---------------------------------------------------------------------------
# Difficulty ladder
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Ladder:
    """Persisted adaptive state: current stage and Leo-won-match streak."""

    stage: int = FIRST_STAGE
    loss_streak: int = 0


def adapt_stage(ladder: Ladder, outcome: MatchOutcome) -> Ladder:
    """Win a match -> next stage; lose two in a row -> one stage back."""

    if outcome is MatchOutcome.FLASH:
        return Ladder(min(LAST_STAGE, ladder.stage + 1), 0)
    if outcome is MatchOutcome.LEO:
        streak = ladder.loss_streak + 1
        if streak >= 2:
            return Ladder(max(FIRST_STAGE, ladder.stage - 1), 0)
        return Ladder(ladder.stage, streak)
    return ladder


def kindness_for(losses_in_a_row: int) -> int:
    """Games the child lost in a row -> how much Leo eases off (0..2)."""

    return max(0, min(MAX_KINDNESS, losses_in_a_row))


__all__ = [
    "DropResult",
    "EasyLeo",
    "Ladder",
    "LeoBrain",
    "MatchOutcome",
    "MediumLeo",
    "MoveRecord",
    "QuattroBoard",
    "QuattroGame",
    "QuattroMatch",
    "SmartLeo",
    "adapt_stage",
    "kindness_for",
    "leo_brain_for",
    "stage_for",
    "suggest_column",
]
