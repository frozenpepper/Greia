from __future__ import annotations

import collections
from dataclasses import dataclass, field
import random
from typing import Any

BIOMES: list[dict[str, Any]] = [
    {
        "id": "midnight_galaxy",
        "name_it": "🌌 Galassia di Mezzanotte",
        "name_en": "🌌 Midnight Galaxy",
        "bg": (15, 23, 42),
        "wall": (99, 102, 241),
        "wall_shadow": (2, 6, 23),
        "wall_top": (165, 180, 252),
        "path": (30, 41, 59),
        "hint": (253, 224, 71),
        "collectible_color": (251, 191, 36),
        "particle_col": (192, 132, 252),
    },
    {
        "id": "emerald_forest",
        "name_it": "🌲 Foresta Smeraldo",
        "name_en": "🌲 Emerald Forest",
        "bg": (6, 44, 28),
        "wall": (22, 163, 74),
        "wall_shadow": (2, 28, 16),
        "wall_top": (74, 222, 128),
        "path": (20, 83, 45),
        "hint": (251, 191, 36),
        "collectible_color": (250, 204, 21),
        "particle_col": (134, 239, 172),
    },
    {
        "id": "crystal_kingdom",
        "name_it": "💎 Regno dei Cristalli",
        "name_en": "💎 Crystal Kingdom",
        "bg": (24, 12, 48),
        "wall": (192, 38, 211),
        "wall_shadow": (10, 4, 22),
        "wall_top": (240, 171, 252),
        "path": (59, 7, 100),
        "hint": (56, 189, 248),
        "collectible_color": (244, 114, 182),
        "particle_col": (244, 114, 182),
    },
    {
        "id": "volcano_realm",
        "name_it": "🌋 Regno del Vulcano",
        "name_en": "🌋 Volcano Realm",
        "bg": (28, 25, 23),
        "wall": (234, 88, 12),
        "wall_shadow": (12, 10, 9),
        "wall_top": (251, 146, 60),
        "path": (68, 20, 10),
        "hint": (254, 240, 138),
        "collectible_color": (239, 68, 68),
        "particle_col": (251, 146, 60),
    },
]

HEROES: list[dict[str, Any]] = [
    {"id": "fox", "name": "Tito", "color": (249, 115, 22)},
    {"id": "bunny", "name": "Flash", "color": (248, 250, 252)},
    {"id": "unicorn", "name": "Lilli", "color": (244, 114, 182)},
    {"id": "kitty", "name": "Mimi", "color": (251, 146, 60)},
    {"id": "dragon", "name": "Drago", "color": (34, 197, 94)},
    {"id": "puppy", "name": "Cucciolo", "color": (217, 119, 6)},
]

# Six release-facing difficulty levels match manifest D1–D6. Keep the hardest
# maze bounded for child-readable cells on Greia's 1024×600 reference surface.
DIFFICULTIES: list[dict[str, Any]] = [
    {"id": "small", "label_it": "FACILE", "label_en": "EASY", "cols": 13, "rows": 9, "stars": 3},
    {"id": "medium", "label_it": "MEDIO", "label_en": "MEDIUM", "cols": 21, "rows": 13, "stars": 5},
    {"id": "large", "label_it": "GRANDE", "label_en": "LARGE", "cols": 29, "rows": 17, "stars": 8},
    {"id": "giant", "label_it": "GIGANTE", "label_en": "GIANT", "cols": 39, "rows": 21, "stars": 12},
    {"id": "epic", "label_it": "EPICO", "label_en": "EPIC", "cols": 49, "rows": 25, "stars": 16},
    {"id": "master", "label_it": "MAESTRO", "label_en": "MASTER", "cols": 59, "rows": 29, "stars": 20},
]


@dataclass
class CollectibleStar:
    r: int
    c: int
    collected: bool = False
    anim_t: float = 0.0


@dataclass
class MazeState:
    cols: int
    rows: int
    grid: list[list[int]]
    entrance: dict[str, int]
    exit_pos: dict[str, int]
    collectibles: list[CollectibleStar] = field(default_factory=list)
    player_r: int = 1
    player_c: int = 1
    player_x: float = 1.0
    player_y: float = 1.0
    facing_right: bool = True
    is_victory: bool = False
    sliding_waypoints: list[tuple[int, int]] = field(default_factory=list)
    sliding_progress: float = 0.0
    slide_speed: float = 18.0  # cells per second


class MazeEngine:
    @staticmethod
    def generate(
        cols: int,
        rows: int,
        num_stars: int = 3,
    ) -> tuple[list[list[int]], dict[str, int], dict[str, int], list[dict[str, Any]]]:
        # Ensure dimensions are odd
        if cols % 2 == 0:
            cols += 1
        if rows % 2 == 0:
            rows += 1

        grid = [[1 for _ in range(cols)] for _ in range(rows)]
        stack = [(1, 1)]
        grid[1][1] = 0

        while stack:
            cr, cc = stack[-1]
            neighbors = []
            for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                nr, nc = cr + dr, cc + dc
                if 1 <= nr < rows - 1 and 1 <= nc < cols - 1 and grid[nr][nc] == 1:
                    neighbors.append((nr, nc, cr + dr // 2, cc + dc // 2))

            if neighbors:
                nr, nc, wr, wc = random.choice(neighbors)
                grid[wr][wc] = 0
                grid[nr][nc] = 0
                stack.append((nr, nc))
            else:
                stack.pop()

        entrance = {"r": 1, "c": 1}
        exit_pos = {"r": rows - 2, "c": cols - 2}
        grid[exit_pos["r"]][exit_pos["c"]] = 0

        empty_cells = []
        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                if grid[r][c] == 0 and (r, c) not in [(1, 1), (exit_pos["r"], exit_pos["c"])]:
                    empty_cells.append((r, c))
        random.shuffle(empty_cells)
        collectibles = []
        for r, c in empty_cells[:num_stars]:
            collectibles.append({
                "r": r,
                "c": c,
                "collected": False,
                "anim_t": random.random() * 6.28,
            })

        return grid, entrance, exit_pos, collectibles

    @staticmethod
    def solve_bfs(
        grid: list[list[int]],
        start_r: int,
        start_c: int,
        goal_r: int,
        goal_c: int,
    ) -> list[tuple[int, int]]:
        rows = len(grid)
        cols = len(grid[0])
        queue = collections.deque([(start_r, start_c)])
        parent: dict[tuple[int, int], tuple[int, int] | None] = {(start_r, start_c): None}

        while queue:
            curr = queue.popleft()
            if curr == (goal_r, goal_c):
                path = []
                p: tuple[int, int] | None = curr
                while p is not None:
                    path.append(p)
                    p = parent[p]
                path.reverse()
                return path

            cr, cc = curr
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
                    if (nr, nc) not in parent:
                        parent[(nr, nc)] = curr
                        queue.append((nr, nc))

        return []

    @staticmethod
    def compute_slide_path(
        grid: list[list[int]],
        r: int,
        c: int,
        dr: int,
        dc: int,
        exit_pos: dict[str, int],
    ) -> list[tuple[int, int]]:
        """Compute continuous sliding path until reaching the exit, a wall, or an intersection."""
        rows = len(grid)
        cols = len(grid[0])
        path: list[tuple[int, int]] = []
        cr, cc = r, c

        while True:
            nr = cr + dr
            nc = cc + dc
            if not (0 <= nr < rows and 0 <= nc < cols) or grid[nr][nc] == 1:
                break
            path.append((nr, nc))
            cr, cc = nr, nc
            if cr == exit_pos["r"] and cc == exit_pos["c"]:
                break
            # Check decision point (intersection / crossing)
            choices = 0
            for cdr, cdc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ckr, ckc = cr + cdr, cc + cdc
                if 0 <= ckr < rows and 0 <= ckc < cols and grid[ckr][ckc] == 0:
                    choices += 1
            if choices > 2:
                break

        return path

    @staticmethod
    def resolve_click_direction(
        grid: list[list[int]],
        player_r: int,
        player_c: int,
        target_r: int,
        target_c: int,
        exit_pos: dict[str, int],
    ) -> tuple[int, int]:
        """Resolve a mouse click into the intended cardinal slide direction without pathfinding.

        Returns (dr, dc) for the primary open direction, or (0, 0) if no movement is possible.
        """
        dr_total = target_r - player_r
        dc_total = target_c - player_c

        if dr_total == 0 and dc_total == 0:
            return 0, 0

        # Determine primary and secondary axis
        if abs(dc_total) >= abs(dr_total):
            # Horizontal primary
            primary_dr = 0
            primary_dc = 1 if dc_total > 0 else -1
            secondary_dr = (1 if dr_total > 0 else -1) if dr_total != 0 else 0
            secondary_dc = 0
        else:
            # Vertical primary
            primary_dr = 1 if dr_total > 0 else -1
            primary_dc = 0
            secondary_dr = 0
            secondary_dc = (1 if dc_total > 0 else -1) if dc_total != 0 else 0

        # Check if primary direction has an open path
        primary_path = MazeEngine.compute_slide_path(grid, player_r, player_c, primary_dr, primary_dc, exit_pos)
        if primary_path:
            return primary_dr, primary_dc

        # If primary is blocked, try secondary if valid
        if secondary_dr != 0 or secondary_dc != 0:
            secondary_path = MazeEngine.compute_slide_path(grid, player_r, player_c, secondary_dr, secondary_dc, exit_pos)
            if secondary_path:
                return secondary_dr, secondary_dc
        else:
            # Axis was purely horizontal or vertical, but blocked directly.
            # Check perpendicular open turns (e.g. at a corner or intersection)
            if primary_dr == 0:  # Primary was horizontal, check vertical
                for alt_dr in (1, -1):
                    alt_path = MazeEngine.compute_slide_path(grid, player_r, player_c, alt_dr, 0, exit_pos)
                    if alt_path:
                        return alt_dr, 0
            else:  # Primary was vertical, check horizontal
                for alt_dc in (1, -1):
                    alt_path = MazeEngine.compute_slide_path(grid, player_r, player_c, 0, alt_dc, exit_pos)
                    if alt_path:
                        return 0, alt_dc

        return 0, 0
