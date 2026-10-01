"""Pure logic domain model for Quattro Amici in Fila.

Zero Pygame dependencies. Fully decoupled and unit-testable.
Handles board matrix, gravity drop simulation, win and draw detection,
turn management, and multi-tier AI opponent move generation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Sequence

if __package__:
    from .quattro_content import (
        LEVEL_CONFIGS,
        GameMode,
        GameStatus,
        LevelConfig,
        Player,
    )
else:
    from quattro_content import (
        LEVEL_CONFIGS,
        GameMode,
        GameStatus,
        LevelConfig,
        Player,
    )


@dataclass
class MoveRecord:
    """Historical record of an individual token drop."""
    col: int
    row: int
    player: Player


class QuattroBoard:
    """Matrix representation of the vertical connect drop-grid."""

    def __init__(self, cols: int, rows: int, target_in_a_row: int) -> None:
        self.cols = cols
        self.rows = rows
        self.target = target_in_a_row
        # grid[row][col]: row 0 is TOP, row (rows - 1) is BOTTOM
        self.grid: list[list[Player]] = [
            [Player.EMPTY for _ in range(cols)] for _ in range(rows)
        ]

    def can_drop(self, col: int) -> bool:
        """Return True if column index is within bounds and has space."""
        if not (0 <= col < self.cols):
            return False
        return self.grid[0][col] == Player.EMPTY

    def valid_columns(self) -> list[int]:
        """Return sorted list of non-full column indices."""
        return [c for c in range(self.cols) if self.can_drop(c)]

    def drop_token(self, col: int, player: Player) -> int:
        """Simulate gravity drop down the slot.

        Returns landing row index (0 to rows-1), or -1 if column is full.
        """
        if not self.can_drop(col):
            return -1
        # Start from bottom (rows - 1) up to top (0)
        for r in range(self.rows - 1, -1, -1):
            if self.grid[r][col] == Player.EMPTY:
                self.grid[r][col] = player
                return r
        return -1

    def undo_drop(self, col: int) -> int:
        """Remove topmost token in column. Returns cleared row, or -1 if empty."""
        if not (0 <= col < self.cols):
            return -1
        for r in range(self.rows):
            if self.grid[r][col] != Player.EMPTY:
                self.grid[r][col] = Player.EMPTY
                return r
        return -1

    def is_full(self) -> bool:
        """Return True if every column is full."""
        return all(self.grid[0][c] != Player.EMPTY for c in range(self.cols))

    def check_win(self, target: int | None = None) -> tuple[Player, list[tuple[int, int]]]:
        """Check for horizontal, vertical, or diagonal consecutive lines.

        Returns (winning_player, winning_coordinates) or (Player.EMPTY, []).
        """
        req = target if target is not None else self.target
        winning_cells: set[tuple[int, int]] = set()
        winner = Player.EMPTY

        # 1. Horizontal lines
        for r in range(self.rows):
            for c in range(self.cols - req + 1):
                p = self.grid[r][c]
                if p != Player.EMPTY and all(self.grid[r][c + i] == p for i in range(req)):
                    winner = p
                    winning_cells.update((r, c + i) for i in range(req))

        # 2. Vertical lines
        for c in range(self.cols):
            for r in range(self.rows - req + 1):
                p = self.grid[r][c]
                if p != Player.EMPTY and all(self.grid[r + i][c] == p for i in range(req)):
                    winner = p
                    winning_cells.update((r + i, c) for i in range(req))

        # 3. Diagonal down-right (\)
        for r in range(self.rows - req + 1):
            for c in range(self.cols - req + 1):
                p = self.grid[r][c]
                if p != Player.EMPTY and all(self.grid[r + i][c + i] == p for i in range(req)):
                    winner = p
                    winning_cells.update((r + i, c + i) for i in range(req))

        # 4. Diagonal up-right (/)
        for r in range(req - 1, self.rows):
            for c in range(self.cols - req + 1):
                p = self.grid[r][c]
                if p != Player.EMPTY and all(self.grid[r - i][c + i] == p for i in range(req)):
                    winner = p
                    winning_cells.update((r - i, c + i) for i in range(req))

        return winner, sorted(winning_cells)

    def clone(self) -> QuattroBoard:
        """Create an independent copy of this board."""
        copy_board = QuattroBoard(self.cols, self.rows, self.target)
        copy_board.grid = [row[:] for row in self.grid]
        return copy_board


@dataclass
class QuattroModel:
    """Complete game match and state manager."""
    difficulty: int = 2
    mode: GameMode = GameMode.VS_CPU
    rng: random.Random = field(default_factory=random.Random)
    board: QuattroBoard = field(init=False)
    current_player: Player = Player.FLASH
    status: GameStatus = GameStatus.IN_PROGRESS
    winner: Player = Player.EMPTY
    winning_cells: list[tuple[int, int]] = field(default_factory=list)
    history: list[MoveRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reset()

    @property
    def level_config(self) -> LevelConfig:
        return LEVEL_CONFIGS.get(self.difficulty, LEVEL_CONFIGS[2])

    def reset(self) -> None:
        """Reset board for a new game with current difficulty and mode."""
        cfg = self.level_config
        self.board = QuattroBoard(cfg.cols, cfg.rows, cfg.target_in_a_row)
        self.current_player = Player.FLASH
        self.status = GameStatus.IN_PROGRESS
        self.winner = Player.EMPTY
        self.winning_cells.clear()
        self.history.clear()

    def set_difficulty(self, diff: int) -> None:
        """Change difficulty level and start a fresh game."""
        if diff in LEVEL_CONFIGS and diff != self.difficulty:
            self.difficulty = diff
            self.reset()

    def set_mode(self, mode: GameMode) -> None:
        """Change gameplay mode (Solo vs Leo or Two Players)."""
        if mode != self.mode:
            self.mode = mode
            self.reset()

    def can_drop(self, col: int) -> bool:
        """Return True if token can be dropped in column."""
        if self.status != GameStatus.IN_PROGRESS:
            return False
        return self.board.can_drop(col)

    def drop_token(self, col: int) -> tuple[bool, int]:
        """Perform a drop for the current player.

        Returns (success, landed_row).
        """
        if self.status != GameStatus.IN_PROGRESS:
            return False, -1

        player = self.current_player
        row = self.board.drop_token(col, player)
        if row < 0:
            return False, -1

        self.history.append(MoveRecord(col=col, row=row, player=player))

        # Check win condition
        winner, win_cells = self.board.check_win()
        if winner != Player.EMPTY:
            self.status = GameStatus.WON
            self.winner = winner
            self.winning_cells = win_cells
            return True, row

        # Check draw condition
        if self.board.is_full():
            self.status = GameStatus.DRAW
            self.winner = Player.EMPTY
            return True, row

        # Alternate turn
        self.current_player = self.current_player.opponent
        return True, row

    def cpu_choose_move(self) -> int:
        """Select a column move for Leo (CPU) based on level intelligence."""
        val_cols = self.board.valid_columns()
        if not val_cols:
            return -1

        intel = self.level_config.cpu_intelligence
        cpu_player = Player.LEO
        child_player = Player.FLASH

        # Center preference helper for natural play
        center = (self.board.cols - 1) / 2.0
        val_cols_center_sorted = sorted(val_cols, key=lambda c: abs(c - center))

        # Tier 1: Silly (Age 3-4) - Playful random moves
        if intel == "silly":
            return self.rng.choice(val_cols)

        # Tier 2: Defensive (Age 4) - Take immediate wins, block obvious wins
        if intel == "defensive":
            # 1. Check if CPU can win in 1 move
            for c in val_cols:
                r = self.board.drop_token(c, cpu_player)
                w, _ = self.board.check_win()
                self.board.undo_drop(c)
                if w == cpu_player:
                    return c

            # 2. Check if Child can win in 1 move; block it!
            for c in val_cols:
                r = self.board.drop_token(c, child_player)
                w, _ = self.board.check_win()
                self.board.undo_drop(c)
                if w == child_player:
                    return c

            # 3. Otherwise pick with center bias
            weights = [1.0 / (1.0 + abs(c - center)) for c in val_cols]
            return self.rng.choices(val_cols, weights=weights, k=1)[0]

        # Tier 3: Smart (Age 4-5) - Avoid giving away wins, seek lines of 2/3
        if intel == "smart":
            # 1. Take winning move
            for c in val_cols:
                self.board.drop_token(c, cpu_player)
                w, _ = self.board.check_win()
                self.board.undo_drop(c)
                if w == cpu_player:
                    return c

            # 2. Block child's winning move
            for c in val_cols:
                self.board.drop_token(c, child_player)
                w, _ = self.board.check_win()
                self.board.undo_drop(c)
                if w == child_player:
                    return c

            # 3. Filter out moves that give the child an immediate win directly above!
            safe_cols: list[int] = []
            for c in val_cols:
                r = self.board.drop_token(c, cpu_player)
                is_safe = True
                if self.board.can_drop(c):
                    self.board.drop_token(c, child_player)
                    w, _ = self.board.check_win()
                    self.board.undo_drop(c)
                    if w == child_player:
                        is_safe = False
                self.board.undo_drop(c)
                if is_safe:
                    safe_cols.append(c)

            candidates = safe_cols if safe_cols else val_cols
            # Score candidate positions based on line alignment
            best_col = candidates[0]
            best_score = -9999.0
            for c in candidates:
                score = self._score_heuristic_move(c, cpu_player, child_player)
                if score > best_score:
                    best_score = score
                    best_col = c
            return best_col

        # Tier 4: Strategic (Age 5+) - 3-ply Minimax evaluation
        return self._minimax_best_move(depth=3, cpu=cpu_player, opp=child_player)

    def _score_heuristic_move(self, col: int, me: Player, opp: Player) -> float:
        """Evaluate a move by analyzing lines formed."""
        center = (self.board.cols - 1) / 2.0
        score = 10.0 - abs(col - center) * 2.0

        r = self.board.drop_token(col, me)
        # Check sub-lines formed
        for length in range(2, self.board.target):
            _, cells = self.board.check_win(target=length)
            score += len(cells) * (5.0 ** (length - 1))
        self.board.undo_drop(col)
        return score

    def _minimax_best_move(self, depth: int, cpu: Player, opp: Player) -> int:
        """Minimax with alpha-beta pruning."""
        val_cols = self.board.valid_columns()
        if not val_cols:
            return -1

        # Center sort
        center = (self.board.cols - 1) / 2.0
        val_cols.sort(key=lambda c: abs(c - center))

        best_score = -100000.0
        best_col = val_cols[0]
        alpha = -100000.0
        beta = 100000.0

        for col in val_cols:
            self.board.drop_token(col, cpu)
            score = self._minimax(depth - 1, False, alpha, beta, cpu, opp)
            self.board.undo_drop(col)
            if score > best_score:
                best_score = score
                best_col = col
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return best_col

    def _minimax(
        self, depth: int, is_max: bool, alpha: float, beta: float, cpu: Player, opp: Player
    ) -> float:
        winner, _ = self.board.check_win()
        if winner == cpu:
            return 1000.0 + depth * 10.0
        if winner == opp:
            return -1000.0 - depth * 10.0
        if self.board.is_full() or depth <= 0:
            return self._evaluate_board(cpu, opp)

        val_cols = self.board.valid_columns()
        center = (self.board.cols - 1) / 2.0
        val_cols.sort(key=lambda c: abs(c - center))

        if is_max:
            val = -100000.0
            for col in val_cols:
                self.board.drop_token(col, cpu)
                val = max(val, self._minimax(depth - 1, False, alpha, beta, cpu, opp))
                self.board.undo_drop(col)
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
            return val
        else:
            val = 100000.0
            for col in val_cols:
                self.board.drop_token(col, opp)
                val = min(val, self._minimax(depth - 1, True, alpha, beta, cpu, opp))
                self.board.undo_drop(col)
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return val

    def _evaluate_board(self, cpu: Player, opp: Player) -> float:
        """Heuristic evaluation for leaf nodes."""
        center = (self.board.cols - 1) / 2.0
        score = 0.0
        for r in range(self.board.rows):
            for c in range(self.board.cols):
                p = self.board.grid[r][c]
                if p == cpu:
                    score += 4.0 - abs(c - center)
                elif p == opp:
                    score -= 4.0 - abs(c - center)
        return score
