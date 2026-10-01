"""Pure logic simulation model for Corsa delle Bacche.

This module contains zero Pygame draw calls or rendering dependencies.
It models the grid, player movement, path snapping, critter AI,
power-ups, collision detection, and preschool-friendly recoverable failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Final

try:
    from corsa_content import (
        CELL_SIZE,
        GRID_COLS,
        GRID_ORIGIN_X,
        GRID_ORIGIN_Y,
        GRID_ROWS,
        LEVELS,
        BerryType,
        CritterConfig,
        CritterKind,
        Direction,
        LevelConfig,
    )
except ImportError:
    from .corsa_content import (
        CELL_SIZE,
        GRID_COLS,
        GRID_ORIGIN_X,
        GRID_ORIGIN_Y,
        GRID_ROWS,
        LEVELS,
        BerryType,
        CritterConfig,
        CritterKind,
        Direction,
        LevelConfig,
    )


def grid_to_world(col: int, row: int) -> tuple[float, float]:
    """Convert grid cell coordinates (col, row) to world center (x, y)."""
    x = GRID_ORIGIN_X + col * CELL_SIZE + CELL_SIZE / 2.0
    y = GRID_ORIGIN_Y + row * CELL_SIZE + CELL_SIZE / 2.0
    return x, y


def world_to_grid(x: float, y: float) -> tuple[int, int]:
    """Convert world (x, y) to closest grid cell (col, row)."""
    col = int((x - GRID_ORIGIN_X) // CELL_SIZE)
    row = int((y - GRID_ORIGIN_Y) // CELL_SIZE)
    return col, row


@dataclass
class Berry:
    col: int
    row: int
    x: float
    y: float
    berry_type: BerryType
    collected: bool = False
    sparkle_phase: float = 0.0

    @property
    def point_value(self) -> int:
        if self.berry_type == BerryType.BLUEBERRY:
            return 10
        if self.berry_type == BerryType.STRAWBERRY:
            return 20
        if self.berry_type == BerryType.GOLDEN_BERRY:
            return 50
        if self.berry_type == BerryType.RAINBOW_STAR:
            return 100
        return 10


@dataclass
class MomoPlayer:
    x: float
    y: float
    grid_col: int
    grid_row: int
    direction: Direction = Direction.NONE
    queued_direction: Direction = Direction.NONE
    facing_right: bool = True
    speed: float = 120.0
    wobble_timer: float = 0.0
    apple_munch_timer: float = 0.0
    start_pos: tuple[float, float] = (0.0, 0.0)

    @property
    def is_wobbling(self) -> bool:
        return self.wobble_timer > 0.0

    @property
    def is_munching_apple(self) -> bool:
        return self.apple_munch_timer > 0.0


@dataclass
class CritterState:
    kind: CritterKind
    x: float
    y: float
    grid_col: int
    grid_row: int
    direction: Direction
    speed: float
    nest_col: int
    nest_row: int
    is_dizzy: bool = False
    is_napping: bool = False
    nap_timer: float = 0.0
    next_nap_in: float = 4.0
    nap_interval: float = 4.0
    nap_duration: float = 2.5
    scurrying_home: bool = False
    facing_right: bool = True
    wing_phase: float = 0.0


@dataclass
class MovingBonusFruit:
    x: float
    y: float
    grid_col: int
    grid_row: int
    direction: Direction
    speed: float = 50.0
    active: bool = True
    bounce_timer: float = 0.0


class CorsaModel:
    """Pure domain logic and state machine for Corsa delle Bacche."""

    def __init__(self, level_index: int = 0) -> None:
        self.level_index: int = max(0, min(level_index, len(LEVELS) - 1))
        self.level_config: LevelConfig = LEVELS[self.level_index]
        self.walls: set[tuple[int, int]] = set()
        self.berries: list[Berry] = []
        self.critters: list[CritterState] = []
        self.bonus_fruit: MovingBonusFruit | None = None
        self.player: MomoPlayer = MomoPlayer(x=0.0, y=0.0, grid_col=1, grid_row=1)
        self.hearts: int = 3
        self.max_hearts: int = 3
        self.score: int = 0
        self.berries_collected: int = 0
        self.total_berries: int = 0
        self.rainbow_timer: float = 0.0
        self.level_complete: bool = False
        self.recent_events: list[str] = []

        self._load_level(self.level_config)

    @property
    def is_rainbow_active(self) -> bool:
        return self.rainbow_timer > 0.0

    @property
    def remaining_berries(self) -> int:
        return sum(1 for b in self.berries if not b.collected)

    def is_wall(self, col: int, row: int) -> bool:
        """Return True if the grid coordinate is out of bounds or a hedge wall."""
        if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
            return True
        return (col, row) in self.walls

    def can_move(self, col: int, row: int, direction: Direction) -> bool:
        """Check if stepping in direction from (col, row) is free."""
        target_c = col + direction.dx
        target_r = row + direction.dy
        return not self.is_wall(target_c, target_r)

    def _load_level(self, cfg: LevelConfig) -> None:
        self.level_config = cfg
        self.walls.clear()
        self.berries.clear()
        self.critters.clear()
        self.bonus_fruit = None
        self.level_complete = False
        self.rainbow_timer = 0.0

        layout = cfg.maze_layout
        momo_start_cell = cfg.momo_start

        for r in range(min(len(layout), GRID_ROWS)):
            row_str = layout[r]
            for c in range(min(len(row_str), GRID_COLS)):
                char = row_str[c]
                wx, wy = grid_to_world(c, r)

                if char == "#":
                    self.walls.add((c, r))
                elif char == ".":
                    # Alternate blueberries and strawberries for visual sweetness
                    btype = BerryType.STRAWBERRY if (c + r) % 3 == 0 else BerryType.BLUEBERRY
                    self.berries.append(Berry(col=c, row=r, x=wx, y=wy, berry_type=btype))
                elif char == "*":
                    self.berries.append(Berry(col=c, row=r, x=wx, y=wy, berry_type=BerryType.GOLDEN_BERRY))
                elif char == "@":
                    self.berries.append(Berry(col=c, row=r, x=wx, y=wy, berry_type=BerryType.RAINBOW_STAR))
                elif char == "M":
                    momo_start_cell = (c, r)
                    # Also put a berry at M
                    self.berries.append(Berry(col=c, row=r, x=wx, y=wy, berry_type=BerryType.STRAWBERRY))

        self.total_berries = len(self.berries)
        start_x, start_y = grid_to_world(momo_start_cell[0], momo_start_cell[1])
        self.player = MomoPlayer(
            x=start_x,
            y=start_y,
            grid_col=momo_start_cell[0],
            grid_row=momo_start_cell[1],
            direction=Direction.NONE,
            queued_direction=Direction.NONE,
            start_pos=(start_x, start_y),
            speed=125.0,
        )

        # Initialize critters from config
        for ccfg in cfg.critters:
            cx, cy = grid_to_world(ccfg.start_grid[0], ccfg.start_grid[1])
            self.critters.append(
                CritterState(
                    kind=ccfg.kind,
                    x=cx,
                    y=cy,
                    grid_col=ccfg.start_grid[0],
                    grid_row=ccfg.start_grid[1],
                    direction=Direction.LEFT if ccfg.kind == CritterKind.BAFFO else Direction.UP,
                    speed=ccfg.speed,
                    nest_col=ccfg.start_grid[0],
                    nest_row=ccfg.start_grid[1],
                    nap_interval=ccfg.nap_interval,
                    nap_duration=ccfg.nap_duration,
                    next_nap_in=ccfg.nap_interval,
                )
            )

        # Moving bonus fruit (levels 4 & 5)
        if cfg.has_bonus_fruit:
            bx, by = grid_to_world(9, 1)
            self.bonus_fruit = MovingBonusFruit(
                x=bx,
                y=by,
                grid_col=9,
                grid_row=1,
                direction=Direction.RIGHT,
                speed=45.0,
            )

    def request_direction(self, direction: Direction) -> None:
        """Queue a movement intent for Momo (arrow keys, swipes, D-pad)."""
        if direction == Direction.NONE:
            return
        self.player.queued_direction = direction

        # If currently stopped, immediately check if can move
        if self.player.direction == Direction.NONE:
            c, r = world_to_grid(self.player.x, self.player.y)
            if self.can_move(c, r, direction):
                self.player.direction = direction
                if direction in (Direction.LEFT, Direction.RIGHT):
                    self.player.facing_right = (direction == Direction.RIGHT)

    def update(self, dt: float) -> list[str]:
        """Advance domain simulation by dt seconds and return events."""
        events: list[str] = []
        if self.level_complete:
            return events

        # Handle munching restorative apple timer
        if self.player.is_munching_apple:
            self.player.apple_munch_timer -= dt
            if self.player.apple_munch_timer <= 0.0:
                self.player.apple_munch_timer = 0.0
            return events

        # Handle recovery wobble
        if self.player.is_wobbling:
            self.player.wobble_timer -= dt
            if self.player.wobble_timer < 0.0:
                self.player.wobble_timer = 0.0

        # Rainbow Star Powerup countdown
        if self.rainbow_timer > 0.0:
            prev_timer = self.rainbow_timer
            self.rainbow_timer -= dt
            if self.rainbow_timer <= 0.0:
                self.rainbow_timer = 0.0
                # Defrost critters
                for cr in self.critters:
                    if not cr.scurrying_home:
                        cr.is_dizzy = False

        # 1. Update Momo movement & grid snapping
        self._update_player(dt)

        # 2. Check berry collection
        berry_events = self._check_berry_collection()
        events.extend(berry_events)

        # 3. Update critters
        self._update_critters(dt)

        # 4. Update moving bonus fruit
        if self.bonus_fruit is not None and self.bonus_fruit.active:
            self._update_bonus_fruit(dt)
            # Check collision with player
            dist = math.hypot(self.player.x - self.bonus_fruit.x, self.player.y - self.bonus_fruit.y)
            if dist < 26.0:
                self.bonus_fruit.active = False
                self.score += 150
                events.append("chime")

        # 5. Check collision between Momo and Critters
        critter_events = self._check_critter_collisions()
        events.extend(critter_events)

        # 6. Check Level Completion
        if self.remaining_berries == 0 and not self.level_complete:
            self.level_complete = True
            events.append("level_clear")

        self.recent_events = events
        return events

    def _update_player(self, dt: float) -> None:
        p = self.player
        # Align with grid cell center on perpendicular axis
        curr_c, curr_r = world_to_grid(p.x, p.y)
        cell_center_x, cell_center_y = grid_to_world(curr_c, curr_r)

        # Check if queued direction can take effect
        if p.queued_direction != Direction.NONE and p.queued_direction != p.direction:
            q = p.queued_direction
            # 180 turn is always allowed
            if q == p.direction.opposite:
                p.direction = q
                p.queued_direction = Direction.NONE
                if q in (Direction.LEFT, Direction.RIGHT):
                    p.facing_right = (q == Direction.RIGHT)
            else:
                # Orthogonal turn: allowed when near cell center
                dx = abs(p.x - cell_center_x)
                dy = abs(p.y - cell_center_y)
                snap_threshold = 8.0
                if dx <= snap_threshold and dy <= snap_threshold:
                    if self.can_move(curr_c, curr_r, q):
                        # Snap to junction center and turn
                        p.x = cell_center_x
                        p.y = cell_center_y
                        p.direction = q
                        p.queued_direction = Direction.NONE
                        if q in (Direction.LEFT, Direction.RIGHT):
                            p.facing_right = (q == Direction.RIGHT)

        # Move along current direction
        if p.direction != Direction.NONE:
            step = p.speed * dt
            next_x = p.x + p.direction.dx * step
            next_y = p.y + p.direction.dy * step

            # Wall collision check ahead
            ahead_col = curr_c + p.direction.dx
            ahead_row = curr_r + p.direction.dy
            ahead_cx, ahead_cy = grid_to_world(ahead_col, ahead_row)

            if self.is_wall(ahead_col, ahead_row):
                # Clamp to current cell center
                if p.direction == Direction.RIGHT and next_x > cell_center_x:
                    next_x = cell_center_x
                    p.direction = Direction.NONE
                elif p.direction == Direction.LEFT and next_x < cell_center_x:
                    next_x = cell_center_x
                    p.direction = Direction.NONE
                elif p.direction == Direction.DOWN and next_y > cell_center_y:
                    next_y = cell_center_y
                    p.direction = Direction.NONE
                elif p.direction == Direction.UP and next_y < cell_center_y:
                    next_y = cell_center_y
                    p.direction = Direction.NONE

            p.x = next_x
            p.y = next_y

        p.grid_col, p.grid_row = world_to_grid(p.x, p.y)

    def _check_berry_collection(self) -> list[str]:
        events: list[str] = []
        p = self.player
        collect_radius = 20.0

        for b in self.berries:
            if not b.collected:
                dist = math.hypot(p.x - b.x, p.y - b.y)
                if dist <= collect_radius:
                    b.collected = True
                    self.berries_collected += 1
                    self.score += b.point_value

                    if b.berry_type == BerryType.RAINBOW_STAR:
                        self.rainbow_timer = self.level_config.powerup_duration
                        events.append("star_fanfare")
                        for cr in self.critters:
                            cr.is_dizzy = True
                    elif b.berry_type == BerryType.GOLDEN_BERRY:
                        events.append("chime")
                    else:
                        events.append("pop")

        return events

    def _update_critters(self, dt: float) -> None:
        for cr in self.critters:
            cr.wing_phase = (cr.wing_phase + dt * 25.0) % (2.0 * math.pi)

            # If returning to nest after dizzy rescue
            if cr.scurrying_home:
                nest_x, nest_y = grid_to_world(cr.nest_col, cr.nest_row)
                dist = math.hypot(nest_x - cr.x, nest_y - cr.y)
                if dist < 6.0:
                    cr.x, cr.y = nest_x, nest_y
                    cr.grid_col, cr.grid_row = cr.nest_col, cr.nest_row
                    cr.scurrying_home = False
                    cr.is_dizzy = False
                    cr.is_napping = True
                    cr.nap_timer = 3.0
                else:
                    step = (cr.speed * 1.3) * dt
                    angle = math.atan2(nest_y - cr.y, nest_x - cr.x)
                    cr.x += math.cos(angle) * step
                    cr.y += math.sin(angle) * step
                    cr.facing_right = (math.cos(angle) >= 0)
                continue

            # If dizzy during rainbow powerup, stay frozen
            if cr.is_dizzy:
                continue

            # If napping (Baffo)
            if cr.is_napping:
                cr.nap_timer -= dt
                if cr.nap_timer <= 0.0:
                    cr.is_napping = False
                    cr.next_nap_in = cr.nap_interval
                continue

            # Handle nap interval
            if cr.nap_interval > 0.0:
                cr.next_nap_in -= dt
                if cr.next_nap_in <= 0.0:
                    cr.is_napping = True
                    cr.nap_timer = cr.nap_duration
                    continue

            # Normal critter patrol
            curr_c, curr_r = world_to_grid(cr.x, cr.y)
            center_x, center_y = grid_to_world(curr_c, curr_r)

            # At junction center, decide route
            dx = abs(cr.x - center_x)
            dy = abs(cr.y - center_y)
            if dx <= 4.0 and dy <= 4.0:
                # Gather valid directions
                valid_dirs = [
                    d for d in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT)
                    if self.can_move(curr_c, curr_r, d)
                ]
                if valid_dirs:
                    # Prefer not turning back unless dead end
                    non_reverse = [d for d in valid_dirs if d != cr.direction.opposite]
                    candidates = non_reverse if non_reverse else valid_dirs

                    # Slight bias towards Momo for gentle chase
                    if candidates and random.random() < 0.35:
                        px, py = self.player.x, self.player.y
                        best_dir = min(
                            candidates,
                            key=lambda d: math.hypot(
                                (cr.x + d.dx * CELL_SIZE) - px,
                                (cr.y + d.dy * CELL_SIZE) - py,
                            ),
                        )
                        cr.direction = best_dir
                    elif cr.direction not in candidates:
                        cr.direction = random.choice(candidates)

                cr.x = center_x
                cr.y = center_y

            # Advance along direction
            step = cr.speed * dt
            cr.x += cr.direction.dx * step
            cr.y += cr.direction.dy * step
            if cr.direction in (Direction.LEFT, Direction.RIGHT):
                cr.facing_right = (cr.direction == Direction.RIGHT)
            cr.grid_col, cr.grid_row = world_to_grid(cr.x, cr.y)

    def _update_bonus_fruit(self, dt: float) -> None:
        bf = self.bonus_fruit
        if bf is None:
            return
        bf.bounce_timer = (bf.bounce_timer + dt * 4.0) % (2.0 * math.pi)
        curr_c, curr_r = world_to_grid(bf.x, bf.y)
        cx, cy = grid_to_world(curr_c, curr_r)

        if abs(bf.x - cx) <= 3.0 and abs(bf.y - cy) <= 3.0:
            valid_dirs = [
                d for d in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT)
                if self.can_move(curr_c, curr_r, d)
            ]
            non_reverse = [d for d in valid_dirs if d != bf.direction.opposite]
            choices = non_reverse if non_reverse else valid_dirs
            if choices and (bf.direction not in choices or random.random() < 0.25):
                bf.direction = random.choice(choices)
            bf.x = cx
            bf.y = cy

        step = bf.speed * dt
        bf.x += bf.direction.dx * step
        bf.y += bf.direction.dy * step
        bf.grid_col, bf.grid_row = world_to_grid(bf.x, bf.y)

    def _check_critter_collisions(self) -> list[str]:
        events: list[str] = []
        p = self.player
        hit_radius = 26.0

        for cr in self.critters:
            if cr.scurrying_home:
                continue
            dist = math.hypot(p.x - cr.x, p.y - cr.y)
            if dist <= hit_radius:
                if self.is_rainbow_active or cr.is_dizzy:
                    # Momo tags a dizzy critter! Gentle bonus rescue!
                    cr.is_dizzy = False
                    cr.scurrying_home = True
                    self.score += 100
                    events.append("dizzy_squeak")
                elif not p.is_wobbling and not cr.is_napping:
                    # Bump into active critter without rainbow power
                    self.hearts = max(0, self.hearts - 1)
                    p.wobble_timer = 1.0
                    events.append("bounce")

                    # Recoverable Failure: bounce safely back to lane start
                    p.x, p.y = p.start_pos
                    p.direction = Direction.NONE
                    p.queued_direction = Direction.NONE

                    # At 0 hearts: munch restorative apple, cheerfully restart
                    if self.hearts == 0:
                        p.apple_munch_timer = 1.4
                        self.hearts = self.max_hearts
                        events.append("apple_munch")

        return events

    def next_level(self) -> bool:
        """Advance to next level. Returns True if advanced, False if wrapped."""
        next_idx = self.level_index + 1
        if next_idx < len(LEVELS):
            self.level_index = next_idx
            self._load_level(LEVELS[self.level_index])
            return True
        else:
            self.level_index = 0
            self._load_level(LEVELS[0])
            return False

    def restart_level(self) -> None:
        """Restart the current level without changing difficulty."""
        self._load_level(LEVELS[self.level_index])
