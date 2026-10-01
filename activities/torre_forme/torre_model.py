from __future__ import annotations

"""Pure domain logic for La Torre delle Forme.

Zero Pygame dependencies. Models the tower grid matrix, falling shapes,
rotation, collision checking, line clears, free-build snapping, milestones,
and positive celebration closure.
"""

from dataclasses import dataclass, field
import random
from typing import Any

if __package__:
    from .torre_content import (
        CHALLENGE_SHAPES,
        FREE_BUILD_SHAPES,
        GRID_COLS,
        GRID_ROWS,
        SHAPES,
        SLOW_FALL_SHAPES,
        ShapeDefinition,
        TowerMode,
    )
else:
    from torre_content import (
        CHALLENGE_SHAPES,
        FREE_BUILD_SHAPES,
        GRID_COLS,
        GRID_ROWS,
        SHAPES,
        SLOW_FALL_SHAPES,
        ShapeDefinition,
        TowerMode,
    )


def rotate_blocks(blocks: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    """Rotate relative coordinates 90 degrees clockwise and normalize to origin."""
    rotated = [(-y, x) for x, y in blocks]
    min_x = min(x for x, y in rotated)
    min_y = min(y for x, y in rotated)
    return tuple(sorted((x - min_x, y - min_y) for x, y in rotated))


@dataclass(frozen=True)
class GridCell:
    color: tuple[int, int, int]
    shape_id: str
    is_rainbow: bool = False


@dataclass
class BlueprintSocket:
    shape_id: str
    anchor_col: int
    anchor_row: int
    blocks: tuple[tuple[int, int], ...]
    is_filled: bool = False


@dataclass
class StepOutcome:
    audio_cues: list[str] = field(default_factory=list)
    cleared_rows: list[int] = field(default_factory=list)
    cleared_coords: list[tuple[int, int]] = field(default_factory=list)
    snap_coords: list[tuple[int, int]] = field(default_factory=list)
    celebration_triggered: bool = False
    milestone_reached: bool = False
    milestone_height: int = 0
    lines_count: int = 0


class TorreModel:
    """Pure domain logic for the child-friendly spatial tower stacking game."""

    def __init__(
        self,
        mode: TowerMode = TowerMode.FREE_BUILD,
        total_stars: int = 0,
        rng: random.Random | None = None,
    ) -> None:
        self.rng = rng or random.Random()
        self.mode = mode
        self.total_stars = max(0, total_stars)
        self.score = 0
        self.lines_cleared = 0
        self.celebration_milestone = 0
        self.is_celebrating = False
        self.highest_milestone = 0

        # Grid is 10 rows (0 at top, 9 at bottom) by 8 cols (0 at left, 7 at right)
        self.grid: list[list[GridCell | None]] = [
            [None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)
        ]

        # Active falling piece
        self.active_shape: ShapeDefinition | None = None
        self.active_blocks: tuple[tuple[int, int], ...] = ()
        self.active_col: int = 0
        self.active_row: int = 0
        self.shape_counter: int = 0

        # Free build shelf and blueprint sockets
        self.shelf_shapes: list[ShapeDefinition] = []
        self.selected_shelf_idx: int | None = None
        self.blueprints: list[BlueprintSocket] = []

        # Falling timer
        self.fall_accum: float = 0.0
        self._init_mode(mode)

    @property
    def fall_interval(self) -> float:
        if self.mode == TowerMode.SLOW_FALL:
            return 1.4
        elif self.mode == TowerMode.TOWER_CHALLENGE:
            # Gentle progression based on lines cleared
            return max(0.65, 0.90 - (self.lines_cleared // 4) * 0.05)
        return 999.0  # In free build, no auto-fall

    @property
    def current_height(self) -> int:
        """Height of blocks in the tower from ground up (0 to 10)."""
        for r in range(GRID_ROWS):
            if any(cell is not None for cell in self.grid[r]):
                return GRID_ROWS - r
        return 0

    def set_mode(self, mode: TowerMode) -> None:
        self.mode = mode
        self._init_mode(mode)

    def _init_mode(self, mode: TowerMode) -> None:
        self.active_shape = None
        self.active_blocks = ()
        self.is_celebrating = False
        self.fall_accum = 0.0

        if mode == TowerMode.FREE_BUILD:
            self._refresh_shelf()
            self._generate_blueprints()
        else:
            self._spawn_shape()

    def _refresh_shelf(self) -> None:
        """Fill the shelf with 3 friendly toy shapes."""
        self.shelf_shapes = [
            SHAPES[self.rng.choice(FREE_BUILD_SHAPES)] for _ in range(3)
        ]
        self.selected_shelf_idx = 0

    def _generate_blueprints(self) -> None:
        """Create silhouette sockets at the bottom of the tower for matching."""
        self.blueprints.clear()
        # Generate 2-3 target sockets near the bottom
        avail_shapes = [s for s in FREE_BUILD_SHAPES if s != "square" and s != "arch_bridge"]
        shape_id1 = "square"
        shape_id2 = self.rng.choice(avail_shapes)
        s1 = SHAPES[shape_id1]
        s2 = SHAPES[shape_id2]

        # Socket 1 at bottom left: col 1, row 8
        self.blueprints.append(
            BlueprintSocket(
                shape_id=s1.shape_id,
                anchor_col=1,
                anchor_row=GRID_ROWS - 2,
                blocks=s1.blocks,
            )
        )
        # Socket 2 at bottom right: col 4, row 8
        self.blueprints.append(
            BlueprintSocket(
                shape_id=s2.shape_id,
                anchor_col=4,
                anchor_row=GRID_ROWS - 2,
                blocks=s2.blocks,
            )
        )

    def _spawn_shape(self) -> bool:
        """Spawn a new active falling shape at the top of the tower."""
        self.shape_counter += 1
        if self.mode == TowerMode.TOWER_CHALLENGE and self.shape_counter % 7 == 0:
            shape = SHAPES["rainbow_star"]
        elif self.mode == TowerMode.SLOW_FALL:
            shape = SHAPES[self.rng.choice(SLOW_FALL_SHAPES)]
        else:
            shape = SHAPES[self.rng.choice(CHALLENGE_SHAPES)]

        self.active_shape = shape
        self.active_blocks = shape.blocks
        # Center the shape at top
        max_dx = max(x for x, y in self.active_blocks)
        self.active_col = (GRID_COLS - (max_dx + 1)) // 2
        self.active_row = 0

        # Check if spawn immediately collides -> tower reached top
        if not self._is_valid_position(self.active_col, self.active_row, self.active_blocks):
            self.active_shape = None
            self.is_celebrating = True
            return False
        return True

    def _is_valid_position(
        self, col: int, row: int, blocks: tuple[tuple[int, int], ...]
    ) -> bool:
        for dx, dy in blocks:
            c = col + dx
            r = row + dy
            if c < 0 or c >= GRID_COLS or r < 0 or r >= GRID_ROWS:
                return False
            if self.grid[r][c] is not None:
                return False
        return True

    def select_shelf_shape(self, index: int) -> None:
        if 0 <= index < len(self.shelf_shapes):
            self.selected_shelf_idx = index

    def place_free_shape(self, target_col: int, target_row: int) -> StepOutcome:
        """Place the selected shelf shape onto the tower grid in Free Build mode."""
        outcome = StepOutcome()
        if self.mode != TowerMode.FREE_BUILD or self.selected_shelf_idx is None:
            return outcome
        if self.selected_shelf_idx >= len(self.shelf_shapes):
            return outcome

        shape = self.shelf_shapes[self.selected_shelf_idx]
        blocks = shape.blocks

        # 1. Check if placement is near a matching blueprint socket (forgiving snap!)
        snapped = False
        for bp in self.blueprints:
            if not bp.is_filled and bp.shape_id == shape.shape_id:
                # If target is within 1 cell of blueprint anchor
                if abs(target_col - bp.anchor_col) <= 1 and abs(target_row - bp.anchor_row) <= 1:
                    target_col = bp.anchor_col
                    target_row = bp.anchor_row
                    snapped = True
                    bp.is_filled = True
                    break

        # Check validity
        if not self._is_valid_position(target_col, target_row, blocks):
            # Try nudging onto ground or nearby valid cell
            valid = False
            for dy in range(GRID_ROWS):
                check_r = GRID_ROWS - 1 - dy
                if self._is_valid_position(target_col, check_r, blocks):
                    target_row = check_r
                    valid = True
                    break
            if not valid:
                return outcome

        # Place the blocks into grid
        placed_coords: list[tuple[int, int]] = []
        for dx, dy in blocks:
            c = target_col + dx
            r = target_row + dy
            self.grid[r][c] = GridCell(shape.color, shape.shape_id, shape.is_rainbow)
            placed_coords.append((c, r))

        outcome.snap_coords = placed_coords
        if snapped:
            outcome.audio_cues.append("snap")
            self.score += 50
            self.total_stars += 1
        else:
            outcome.audio_cues.append("clack")
            self.score += 20

        # Replace used shape on shelf with a new one
        self.shelf_shapes[self.selected_shelf_idx] = SHAPES[
            self.rng.choice(FREE_BUILD_SHAPES)
        ]

        # Check line clears
        clears = self._check_and_clear_lines()
        outcome.cleared_rows = clears.cleared_rows
        outcome.cleared_coords = clears.cleared_coords
        outcome.lines_count = len(clears.cleared_rows)
        if clears.audio_cues:
            outcome.audio_cues.extend(clears.audio_cues)

        # Check if all blueprints filled
        if self.blueprints and all(bp.is_filled for bp in self.blueprints):
            outcome.audio_cues.append("fanfare")
            outcome.celebration_triggered = True
            self.total_stars += 2
            self._generate_blueprints()

        self._check_height_milestones(outcome)
        return outcome

    def move_left(self) -> bool:
        if self.active_shape is None or self.is_celebrating:
            return False
        if self._is_valid_position(self.active_col - 1, self.active_row, self.active_blocks):
            self.active_col -= 1
            return True
        return False

    def move_right(self) -> bool:
        if self.active_shape is None or self.is_celebrating:
            return False
        if self._is_valid_position(self.active_col + 1, self.active_row, self.active_blocks):
            self.active_col += 1
            return True
        return False

    def rotate_active(self) -> bool:
        if self.active_shape is None or self.is_celebrating:
            return False
        if not self.active_shape.can_rotate:
            return False
        new_blocks = rotate_blocks(self.active_blocks)
        # Test direct position
        if self._is_valid_position(self.active_col, self.active_row, new_blocks):
            self.active_blocks = new_blocks
            return True
        # Wall kick: try shifting 1 left or 1 right
        for offset in (-1, 1, -2, 2):
            if self._is_valid_position(self.active_col + offset, self.active_row, new_blocks):
                self.active_col += offset
                self.active_blocks = new_blocks
                return True
        return False

    def drop_down(self) -> StepOutcome:
        """Drop the active shape down one step immediately."""
        outcome = StepOutcome()
        if self.active_shape is None or self.is_celebrating:
            return outcome

        if self._is_valid_position(self.active_col, self.active_row + 1, self.active_blocks):
            self.active_row += 1
        else:
            # Lock the shape in place!
            self._lock_active_shape(outcome)
        return outcome

    def hard_drop(self) -> StepOutcome:
        """Slam active shape down to the bottom surface."""
        outcome = StepOutcome()
        if self.active_shape is None or self.is_celebrating:
            return outcome

        while self._is_valid_position(self.active_col, self.active_row + 1, self.active_blocks):
            self.active_row += 1
        self._lock_active_shape(outcome)
        return outcome

    def _lock_active_shape(self, outcome: StepOutcome) -> None:
        assert self.active_shape is not None
        shape = self.active_shape
        placed_coords: list[tuple[int, int]] = []

        for dx, dy in self.active_blocks:
            c = self.active_col + dx
            r = self.active_row + dy
            if 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS:
                self.grid[r][c] = GridCell(shape.color, shape.shape_id, shape.is_rainbow)
                placed_coords.append((c, r))

        outcome.snap_coords = placed_coords
        self.active_shape = None

        if shape.is_rainbow:
            # Rainbow Star special block: clear the row it landed on!
            outcome.audio_cues.append("rainbow")
            landed_row = min(r for c, r in placed_coords) if placed_coords else GRID_ROWS - 1
            self._clear_single_row(landed_row, outcome)
            self.total_stars += 1
            self.score += 100
        else:
            outcome.audio_cues.append("clack")
            self.score += 10

        # Check standard line clears
        clears = self._check_and_clear_lines()
        outcome.cleared_rows.extend(clears.cleared_rows)
        outcome.cleared_coords.extend(clears.cleared_coords)
        outcome.lines_count += len(clears.cleared_rows)
        if clears.audio_cues:
            outcome.audio_cues.extend(clears.audio_cues)

        self._check_height_milestones(outcome)

        # Check if tower reached top
        if self.current_height >= GRID_ROWS:
            self.is_celebrating = True
            outcome.celebration_triggered = True
            outcome.audio_cues.append("fanfare")
        else:
            # Spawn next piece
            spawned = self._spawn_shape()
            if not spawned:
                outcome.celebration_triggered = True
                outcome.audio_cues.append("fanfare")

    def _clear_single_row(self, row: int, outcome: StepOutcome) -> None:
        """Clear a single row (used by rainbow star)."""
        coords = [(c, row) for c in range(GRID_COLS) if self.grid[row][c] is not None]
        outcome.cleared_coords.extend(coords)
        outcome.cleared_rows.append(row)
        for c in range(GRID_COLS):
            self.grid[row][c] = None
        # Drop rows above down by 1
        for r in range(row, 0, -1):
            for c in range(GRID_COLS):
                self.grid[r][c] = self.grid[r - 1][c]
        for c in range(GRID_COLS):
            self.grid[0][c] = None
        self.lines_cleared += 1

    def _check_and_clear_lines(self) -> StepOutcome:
        outcome = StepOutcome()
        rows_to_clear: list[int] = []

        for r in range(GRID_ROWS):
            if all(self.grid[r][c] is not None for c in range(GRID_COLS)):
                rows_to_clear.append(r)

        if not rows_to_clear:
            return outcome

        outcome.audio_cues.append("line_clear")
        outcome.cleared_rows = rows_to_clear

        for r in rows_to_clear:
            for c in range(GRID_COLS):
                outcome.cleared_coords.append((c, r))
                self.grid[r][c] = None

        # Compact grid downwards
        new_grid: list[list[GridCell | None]] = [
            [None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)
        ]
        target_r = GRID_ROWS - 1
        for r in range(GRID_ROWS - 1, -1, -1):
            if r not in rows_to_clear:
                new_grid[target_r] = self.grid[r]
                target_r -= 1

        self.grid = new_grid
        self.lines_cleared += len(rows_to_clear)
        self.total_stars += len(rows_to_clear)
        self.score += len(rows_to_clear) * 100
        return outcome

    def _check_height_milestones(self, outcome: StepOutcome) -> None:
        h = self.current_height
        milestones = [3, 6, 8, 10]
        for m in milestones:
            if h >= m > self.highest_milestone:
                self.highest_milestone = m
                outcome.milestone_reached = True
                outcome.milestone_height = m
                self.total_stars += 1
                if m == 10:
                    outcome.celebration_triggered = True
                    outcome.audio_cues.append("fanfare")
                break

    def step_time(self, dt: float) -> StepOutcome:
        """Step real time forward. Drops active falling piece when interval elapses."""
        outcome = StepOutcome()
        if self.mode == TowerMode.FREE_BUILD or self.is_celebrating or self.active_shape is None:
            return outcome

        self.fall_accum += dt
        if self.fall_accum >= self.fall_interval:
            self.fall_accum = 0.0
            return self.drop_down()
        return outcome

    def restart_after_celebration(self) -> None:
        """Reset the tower for a fresh playful build."""
        self.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.is_celebrating = False
        self.highest_milestone = 0
        self._init_mode(self.mode)
