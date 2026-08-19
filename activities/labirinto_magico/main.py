from __future__ import annotations

import collections
import io
import math
from pathlib import Path
import random
import struct
import time
from typing import Any
import wave

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.typography import FontRole, GreiaTypography

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "labirinto_magico.progress.v2"

BIOMES = [
    {
        "id": "midnight_galaxy",
        "bg": (15, 23, 42),          # Deep midnight navy
        "wall": (99, 102, 241),       # Luminous electric indigo
        "wall_shadow": (2, 6, 23),    # Dark midnight shadow
        "wall_top": (165, 180, 252),  # Glowing lilac top highlight
        "path": (30, 41, 59),         # Twilight dark slate path
        "hint": (253, 224, 71),       # Neon gold hint
        "collectible_color": (251, 191, 36),
    },
    {
        "id": "emerald_forest",
        "bg": (6, 44, 28),            # Deep dark forest
        "wall": (22, 163, 74),        # Rich emerald stone
        "wall_shadow": (2, 28, 16),   # Forest shadows
        "wall_top": (74, 222, 128),   # Bright leaf highlight
        "path": (20, 83, 45),         # Mossy earthen path
        "hint": (251, 191, 36),       # Firefly glow
        "collectible_color": (250, 204, 21),
    },
    {
        "id": "crystal_kingdom",
        "bg": (24, 12, 48),           # Deep royal purple
        "wall": (192, 38, 211),       # Luminous amethyst magenta
        "wall_shadow": (10, 4, 22),   # Deep shadow purple
        "wall_top": (240, 171, 252),  # Sparkling fuchsia
        "path": (59, 7, 100),         # Dark crystal stone
        "hint": (56, 189, 248),       # Cyan sparkle
        "collectible_color": (244, 114, 182),
    },
    {
        "id": "volcano_realm",
        "bg": (28, 25, 23),           # Obsidian dark
        "wall": (234, 88, 12),        # Glowing amber magma
        "wall_shadow": (12, 10, 9),   # Charred stone
        "wall_top": (251, 146, 60),   # Radiant orange flare
        "path": (68, 20, 10),         # Dark volcanic floor
        "hint": (254, 240, 138),      # Sunbeam glow
        "collectible_color": (239, 68, 68),
    },
]

HEROES = [
    {"id": "unicorn", "color": (244, 114, 182)},
    {"id": "bunny", "color": (248, 250, 252)},
    {"id": "kitty", "color": (251, 146, 60)},
    {"id": "fox", "color": (249, 115, 22)},
    {"id": "dragon", "color": (34, 197, 94)},
    {"id": "puppy", "color": (217, 119, 6)},
]

DIFFICULTIES = [
    {"id": "small", "label_it": "FACILE", "label_en": "EASY", "cols": 9, "rows": 7, "stars": 3},
    {"id": "medium", "label_it": "MEDIO", "label_en": "MEDIUM", "cols": 13, "rows": 9, "stars": 5},
    {"id": "large", "label_it": "GRANDE", "label_en": "LARGE", "cols": 17, "rows": 11, "stars": 7},
    {"id": "giant", "label_it": "GIGANTE", "label_en": "GIANT", "cols": 21, "rows": 13, "stars": 9},
    {"id": "epic", "label_it": "EPICO", "label_en": "EPIC", "cols": 25, "rows": 15, "stars": 12},
    {"id": "master", "label_it": "MAESTRO", "label_en": "MASTER", "cols": 29, "rows": 17, "stars": 15},
    {"id": "titan", "label_it": "TITANO", "label_en": "TITAN", "cols": 37, "rows": 21, "stars": 20},
    {"id": "colossal", "label_it": "COLOSSALE", "label_en": "COLOSSAL", "cols": 45, "rows": 25, "stars": 25},
    {"id": "infinite", "label_it": "INFINITO", "label_en": "INFINITE", "cols": 53, "rows": 27, "stars": 30},
]


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = bytearray()
        for s in samples:
            clamped = max(-32768, min(32767, int(s)))
            raw.extend(struct.pack("<h", clamped))
        w.writeframes(raw)
    return buf.getvalue()


class LabyrinthAudio:
    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._init_sounds()
        except Exception:
            pass

    def _init_sounds(self) -> None:
        rate = 22050
        # Step
        step_samples = []
        for i in range(int(rate * 0.04)):
            t = i / rate
            env = math.exp(-8.0 * (i / (rate * 0.04)))
            val = (2.0 / math.pi) * math.asin(math.sin(2.0 * math.pi * 340.0 * t))
            step_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["step"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(step_samples)))

        # Star chime
        star_samples = []
        for i in range(int(rate * 0.18)):
            t = i / rate
            env = math.exp(-4.0 * t)
            val = math.sin(2.0 * math.pi * 880.0 * t)
            star_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["star"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(star_samples)))

        # Win fanfare
        win_samples = []
        for i in range(int(rate * 0.45)):
            t = i / rate
            env = math.exp(-2.0 * t)
            freq = 523.0 if t < 0.10 else (659.0 if t < 0.20 else (784.0 if t < 0.30 else 1046.0))
            val = math.sin(2.0 * math.pi * freq * t)
            win_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["win"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


class MazeEngine:
    @staticmethod
    def generate(cols: int, rows: int, star_target: int) -> tuple[list[list[int]], dict[str, int], dict[str, int], list[dict[str, Any]]]:
        c = cols if cols % 2 == 1 else cols + 1
        r = rows if rows % 2 == 1 else rows + 1
        grid = [[1 for _ in range(c)] for _ in range(r)]
        stack = [(1, 1)]
        grid[1][1] = 0

        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                nx, ny = cx + dx, cy + dy
                if 1 <= nx < c - 1 and 1 <= ny < r - 1 and grid[ny][nx] == 1:
                    neighbors.append((nx, ny, dx, dy))
            if neighbors:
                nx, ny, dx, dy = random.choice(neighbors)
                grid[cy + dy // 2][cx + dx // 2] = 0
                grid[ny][nx] = 0
                stack.append((nx, ny))
            else:
                stack.pop()

        entrance = {"r": 0, "c": 1}
        grid[0][1] = 0
        exit_pos = {"r": r - 1, "c": c - 2}
        grid[r - 1][c - 2] = 0
        if grid[r - 2][c - 2] == 1:
            grid[r - 2][c - 2] = 0

        collectibles: list[dict[str, Any]] = []
        attempts = 0
        while len(collectibles) < star_target and attempts < 300:
            attempts += 1
            sr = random.randint(1, r - 2)
            sc = random.randint(1, c - 2)
            if grid[sr][sc] == 0:
                if (sr, sc) != (entrance["r"], entrance["c"]) and (sr, sc) != (exit_pos["r"], exit_pos["c"]):
                    if not any(item["r"] == sr and item["c"] == sc for item in collectibles):
                        collectibles.append({"r": sr, "c": sc, "collected": False, "anim_t": random.random() * 6.28})

        return grid, entrance, exit_pos, collectibles

    @staticmethod
    def solve_bfs(grid: list[list[int]], start_r: int, start_c: int, goal_r: int, goal_c: int) -> list[tuple[int, int]]:
        rows = len(grid)
        cols = len(grid[0])
        queue: collections.deque[tuple[int, int, list[tuple[int, int]]]] = collections.deque([(start_r, start_c, [(start_r, start_c)])])
        visited = set([(start_r, start_c)])

        while queue:
            curr_r, curr_c, path = queue.popleft()
            if curr_r == goal_r and curr_c == goal_c:
                return path
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = curr_r + dr, curr_c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited and grid[nr][nc] == 0:
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [(nr, nc)]))
        return []


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


def main() -> int:
    pygame.init()
    pygame.key.set_repeat(160, 80)
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    sounds = LabyrinthAudio()

    profile_lang = get_profile_locale() or "it"
    is_italian = profile_lang.startswith("it")

    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}
    total_stars = saved_data.get("stars", 0)

    hero_idx = 0
    biome_idx = 0
    diff_idx = 0

    grid: list[list[int]] = []
    entrance = {"r": 0, "c": 1}
    exit_pos = {"r": 6, "c": 9}
    collectibles: list[dict[str, Any]] = []

    player_r = 0
    player_c = 0
    player_x = 0.0
    player_y = 0.0
    waypoints: collections.deque[tuple[int, int]] = collections.deque()

    firefly_active = False
    firefly_path: list[tuple[int, int]] = []
    firefly_timer = 0.0
    firefly_index = 0
    firefly_pos = (0.0, 0.0)

    particles: list[dict[str, Any]] = []
    stars_collected = 0
    is_victory = False

    def start_new_game() -> None:
        nonlocal grid, entrance, exit_pos, collectibles
        nonlocal player_r, player_c, player_x, player_y, waypoints
        nonlocal firefly_active, firefly_path, particles, stars_collected, is_victory
        diff = DIFFICULTIES[diff_idx % len(DIFFICULTIES)]
        grid, entrance, exit_pos, collectibles = MazeEngine.generate(diff["cols"], diff["rows"], diff["stars"])
        player_r = entrance["r"]
        player_c = entrance["c"]
        player_x = float(player_c)
        player_y = float(player_r)
        waypoints.clear()
        firefly_active = False
        firefly_path.clear()
        particles.clear()
        stars_collected = 0
        is_victory = False

    start_new_game()

    def move_step(dr: int, dc: int) -> None:
        nonlocal player_r, player_c, is_victory, stars_collected, total_stars
        if is_victory:
            return
        nr, nc = player_r + dr, player_c + dc
        rows = len(grid)
        cols = len(grid[0])
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
            player_r = nr
            player_c = nc
            sounds.play("step")

            for item in collectibles:
                if not item["collected"] and item["r"] == player_r and item["c"] == player_c:
                    item["collected"] = True
                    stars_collected += 1
                    total_stars += 1
                    sounds.play("star")
                    if storage:
                        storage.kv_set(STORAGE_KEY, {"stars": total_stars})
                    try:
                        emit_activity_event("maze.star_collected", {"stars": stars_collected})
                    except Exception:
                        pass

            if player_r == exit_pos["r"] and player_c == exit_pos["c"]:
                if not is_victory:
                    is_victory = True
                    sounds.play("win")
                    try:
                        emit_activity_event("maze.completed", {"stars": stars_collected})
                    except Exception:
                        pass

    def compute_maze_metrics() -> tuple[int, int, int, int, int]:
        m_cols = len(grid[0]) if grid else 9
        m_rows = len(grid) if grid else 7
        hud_top = 80
        hud_bottom = 80
        avail_w = REFERENCE_WIDTH - 60
        avail_h = REFERENCE_HEIGHT - (hud_top + hud_bottom)
        cell_w = avail_w // m_cols
        cell_h = avail_h // m_rows
        m_cs = max(12, min(cell_w, cell_h, 60))
        maze_w = m_cols * m_cs
        maze_h = m_rows * m_cs
        m_ox = (REFERENCE_WIDTH - maze_w) // 2
        m_oy = hud_top + (avail_h - maze_h) // 2
        return m_cols, m_rows, m_cs, m_ox, m_oy

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        cols, rows, cs, ox, oy = compute_maze_metrics()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.KEYDOWN:
                if is_victory:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_r):
                        start_new_game()
                        cols, rows, cs, ox, oy = compute_maze_metrics()
                    continue

                if event.key in (pygame.K_UP, pygame.K_w):
                    waypoints.clear()
                    move_step(-1, 0)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    waypoints.clear()
                    move_step(1, 0)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    waypoints.clear()
                    move_step(0, -1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    waypoints.clear()
                    move_step(0, 1)
                elif event.key in (pygame.K_SPACE, pygame.K_h):
                    path = MazeEngine.solve_bfs(grid, player_r, player_c, exit_pos["r"], exit_pos["c"])
                    if path:
                        firefly_active = True
                        firefly_path = path
                        firefly_timer = 4.0
                        firefly_index = 0
                        firefly_pos = (float(player_c), float(player_r))
                        sounds.play("star")
                elif event.key in (pygame.K_TAB, pygame.K_d):
                    diff_idx = (diff_idx + 1) % len(DIFFICULTIES)
                    start_new_game()
                    cols, rows, cs, ox, oy = compute_maze_metrics()
                elif event.key == pygame.K_e:
                    hero_idx = (hero_idx + 1) % len(HEROES)
                elif event.key in (pygame.K_b, pygame.K_m):
                    biome_idx = (biome_idx + 1) % len(BIOMES)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pointer = canvas.pointer(event.pos)
                if pointer is None:
                    continue
                mx, my = int(pointer[0]), int(pointer[1])

                if not _is_safe_point(screen, event.pos):
                    continue

                if is_victory:
                    play_again_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 70, 240, 60)
                    if play_again_btn.collidepoint(mx, my):
                        start_new_game()
                        cols, rows, cs, ox, oy = compute_maze_metrics()
                    continue

                # Firefly Hint Button
                hint_btn = pygame.Rect(REFERENCE_WIDTH - 150, 14, 130, 58)
                if hint_btn.collidepoint(mx, my) and not is_victory:
                    path = MazeEngine.solve_bfs(grid, player_r, player_c, exit_pos["r"], exit_pos["c"])
                    if path:
                        firefly_active = True
                        firefly_path = path
                        firefly_timer = 4.0
                        firefly_index = 0
                        firefly_pos = (float(player_c), float(player_r))
                        sounds.play("star")
                    continue

                # Bottom Controls
                hero_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 270, REFERENCE_HEIGHT - 72, 160, 64)
                if hero_btn.collidepoint(mx, my):
                    hero_idx = (hero_idx + 1) % len(HEROES)
                    continue

                biome_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 80, REFERENCE_HEIGHT - 72, 160, 64)
                if biome_btn.collidepoint(mx, my):
                    biome_idx = (biome_idx + 1) % len(BIOMES)
                    continue

                diff_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 110, REFERENCE_HEIGHT - 72, 160, 64)
                if diff_btn.collidepoint(mx, my):
                    diff_idx = (diff_idx + 1) % len(DIFFICULTIES)
                    start_new_game()
                    cols, rows, cs, ox, oy = compute_maze_metrics()
                    continue

                # Direct Tap to Navigate Path
                if not is_victory and cs > 0:
                    c = int((mx - ox) // cs)
                    r = int((my - oy) // cs)
                    if 0 <= r < rows and 0 <= c < cols and grid[r][c] == 0:
                        path = MazeEngine.solve_bfs(grid, player_r, player_c, r, c)
                        if path and len(path) > 1:
                            waypoints.clear()
                            for step in path[1:]:
                                waypoints.append(step)

        # Re-verify maze metrics before physics and rendering
        cols, rows, cs, ox, oy = compute_maze_metrics()

        # Smooth Player Movement
        target_x = float(player_c)
        target_y = float(player_r)
        dx = target_x - player_x
        dy = target_y - player_y
        dist = math.hypot(dx, dy)
        if dist > 0.01:
            player_x += dx * 0.35
            player_y += dy * 0.35
        else:
            player_x = target_x
            player_y = target_y
            if waypoints and not is_victory:
                next_r, next_c = waypoints.popleft()
                move_step(next_r - player_r, next_c - player_c)

        # Update Firefly Hint
        if firefly_active:
            firefly_timer -= 0.033
            if firefly_timer <= 0:
                firefly_active = False
            else:
                if firefly_path and firefly_index < len(firefly_path):
                    target_fc, target_fr = firefly_path[firefly_index]
                    fx, fy = firefly_pos
                    fdx = float(target_fc) - fx
                    fdy = float(target_fr) - fy
                    if math.hypot(fdx, fdy) < 0.15:
                        firefly_index += 1
                    else:
                        firefly_pos = (fx + fdx * 0.30, fy + fdy * 0.30)

        # RENDER TO CANVAS
        surf = canvas.surface
        biome = BIOMES[biome_idx]
        hero = HEROES[hero_idx]
        t_now = time.time()

        # 1. Background
        surf.fill(biome["bg"])

        # 2. Maze Grid
        for r in range(rows):
            for c in range(cols):
                rx = ox + c * cs
                ry = oy + r * cs
                rect = pygame.Rect(rx, ry, cs, cs)
                if grid[r][c] == 1:
                    pygame.draw.rect(surf, biome["wall_shadow"], rect)
                    wall_inner = pygame.Rect(rx + 1, ry + 1, max(2, cs - 2), max(2, cs - 2))
                    pygame.draw.rect(surf, biome["wall"], wall_inner, border_radius=max(1, cs // 8))
                else:
                    pygame.draw.rect(surf, biome["path"], rect)
                    pygame.draw.circle(surf, biome["bg"], (rx + cs // 2, ry + cs // 2), max(1, cs // 10))

        # 3. Firefly Hint
        if firefly_active and firefly_path:
            for step_r, step_c in firefly_path:
                px = ox + (step_c + 0.5) * cs
                py = oy + (step_r + 0.5) * cs
                pygame.draw.circle(surf, biome["hint"], (int(px), int(py)), max(2, int(cs * 0.20)), 2)

        # 4. Collectible Stars
        for item in collectibles:
            if not item["collected"]:
                cx = ox + (item["c"] + 0.5) * cs
                cy = oy + (item["r"] + 0.5) * cs + math.sin(t_now * 4.0 + item["anim_t"]) * 3.0
                r_star = max(3, int(cs * 0.32))
                pygame.draw.circle(surf, biome["collectible_color"], (int(cx), int(cy)), r_star)
                pygame.draw.circle(surf, (255, 255, 255), (int(cx), int(cy)), max(1, r_star // 3))

        # 5. Exit Castle
        ex_x = ox + (exit_pos["c"] + 0.5) * cs
        ex_y = oy + (exit_pos["r"] + 0.5) * cs
        exit_r = max(5, int(cs * 0.40))
        pygame.draw.circle(surf, (234, 179, 8), (int(ex_x), int(ex_y)), exit_r + 2, 2)
        pygame.draw.circle(surf, (239, 68, 68), (int(ex_x), int(ex_y)), exit_r)

        # 6. Hero Character with Cute Ears and Expression
        char_px = ox + (player_x + 0.5) * cs
        char_py = oy + (player_y + 0.5) * cs - math.sin(t_now * 6.0) * 2.0
        char_r = max(4, int(cs * 0.38))
        # Hero outer glow
        pygame.draw.circle(surf, (255, 255, 255), (int(char_px), int(char_py)), char_r + 2)
        # Hero body
        pygame.draw.circle(surf, hero["color"], (int(char_px), int(char_py)), char_r)
        # Ears based on hero type
        h_id = hero["id"]
        if h_id in ("bunny", "kitty", "fox", "puppy"):
            pygame.draw.circle(surf, hero["color"], (int(char_px - char_r * 0.6), int(char_py - char_r * 0.7)), max(2, int(char_r * 0.45)))
            pygame.draw.circle(surf, hero["color"], (int(char_px + char_r * 0.6), int(char_py - char_r * 0.7)), max(2, int(char_r * 0.45)))
            pygame.draw.circle(surf, (244, 114, 182), (int(char_px - char_r * 0.6), int(char_py - char_r * 0.7)), max(1, int(char_r * 0.25)))
            pygame.draw.circle(surf, (244, 114, 182), (int(char_px + char_r * 0.6), int(char_py - char_r * 0.7)), max(1, int(char_r * 0.25)))
        elif h_id == "unicorn":
            # Golden horn
            pygame.draw.polygon(surf, (250, 204, 21), [(int(char_px - max(2, char_r // 3)), int(char_py - char_r * 0.7)), (int(char_px + max(2, char_r // 3)), int(char_py - char_r * 0.7)), (int(char_px), int(char_py - char_r * 1.5))])
        # Cute sparkling eyes
        eye_off = max(1, int(char_r * 0.35))
        pygame.draw.circle(surf, (15, 23, 42), (int(char_px - eye_off), int(char_py - max(1, char_r // 6))), max(1, int(char_r * 0.22)))
        pygame.draw.circle(surf, (15, 23, 42), (int(char_px + eye_off), int(char_py - max(1, char_r // 6))), max(1, int(char_r * 0.22)))
        pygame.draw.circle(surf, (255, 255, 255), (int(char_px - eye_off - 1), int(char_py - max(1, char_r // 4))), max(1, int(char_r * 0.10)))
        pygame.draw.circle(surf, (255, 255, 255), (int(char_px + eye_off - 1), int(char_py - max(1, char_r // 4))), max(1, int(char_r * 0.10)))
        # Cheeks
        pygame.draw.circle(surf, (251, 113, 133), (int(char_px - eye_off), int(char_py + max(1, char_r // 3))), max(1, int(char_r * 0.15)))
        pygame.draw.circle(surf, (251, 113, 133), (int(char_px + eye_off), int(char_py + max(1, char_r // 3))), max(1, int(char_r * 0.15)))

        # 7. Firefly Sprite
        if firefly_active:
            fx = ox + (firefly_pos[0] + 0.5) * cs
            fy = oy + (firefly_pos[1] + 0.5) * cs
            pygame.draw.circle(surf, (254, 240, 138), (int(fx), int(fy)), max(6, int(cs * 0.36)))
            pygame.draw.circle(surf, (255, 255, 255), (int(fx), int(fy)), max(3, int(cs * 0.20)))

        # 8. Top Star Progress (Zero-Text Star Pill)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 58, star_pill.centery - s_txt.get_height() // 2))

        # Hint Button (Top Right: Giant Glowing Star/Firefly Icon + Text)
        hint_btn = pygame.Rect(REFERENCE_WIDTH - 150, 14, 130, 58)
        pygame.draw.rect(surf, (254, 240, 138), hint_btn, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), hint_btn, width=3, border_radius=18)
        hx = hint_btn.left + 30
        hy = hint_btn.centery
        pygame.draw.circle(surf, (251, 191, 36), (hx, hy), 14)
        pygame.draw.circle(surf, (255, 255, 255), (hx, hy), 6)
        h_txt = typography.render("AIUTO" if is_italian else "HINT", FontRole.DISPLAY, 18, (180, 83, 9))
        surf.blit(h_txt, (hint_btn.left + 52, hint_btn.centery - h_txt.get_height() // 2))

        # 9. Bottom Controls (Giant Chunky 160x64px Buttons with Icon + Text)
        # Hero Button
        h_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 270, REFERENCE_HEIGHT - 72, 160, 64)
        pygame.draw.rect(surf, (255, 255, 255), h_btn, border_radius=20)
        pygame.draw.rect(surf, hero["color"], h_btn, width=4, border_radius=20)
        h_cx = h_btn.left + 32
        h_cy = h_btn.centery
        pygame.draw.circle(surf, hero["color"], (h_cx, h_cy), 16)
        pygame.draw.circle(surf, (244, 114, 182), (h_cx - 8, h_cy - 12), 4)
        pygame.draw.circle(surf, (244, 114, 182), (h_cx + 8, h_cy - 12), 4)
        pygame.draw.circle(surf, (20, 20, 30), (h_cx - 5, h_cy - 2), 2)
        pygame.draw.circle(surf, (20, 20, 30), (h_cx + 5, h_cy - 2), 2)
        ht_txt = typography.render("EROE" if is_italian else "HERO", FontRole.DISPLAY, 18, (30, 41, 59))
        surf.blit(ht_txt, (h_btn.left + 60, h_btn.centery - ht_txt.get_height() // 2))

        # Biome Button
        b_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 80, REFERENCE_HEIGHT - 72, 160, 64)
        pygame.draw.rect(surf, (255, 255, 255), b_btn, border_radius=20)
        pygame.draw.rect(surf, biome["wall"], b_btn, width=4, border_radius=20)
        b_cx = b_btn.left + 32
        b_cy = b_btn.centery
        pygame.draw.circle(surf, biome["wall"], (b_cx, b_cy), 16)
        pygame.draw.ellipse(surf, biome["wall_top"], pygame.Rect(b_cx - 20, b_cy - 5, 40, 10), 2)
        pygame.draw.circle(surf, (255, 255, 255), (b_cx - 4, b_cy - 4), 4)
        bt_txt = typography.render("MONDO" if is_italian else "WORLD", FontRole.DISPLAY, 18, (30, 41, 59))
        surf.blit(bt_txt, (b_btn.left + 58, b_btn.centery - bt_txt.get_height() // 2))

        # Difficulty Button
        d_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 110, REFERENCE_HEIGHT - 72, 160, 64)
        pygame.draw.rect(surf, (255, 255, 255), d_btn, border_radius=20)
        pygame.draw.rect(surf, (234, 179, 8), d_btn, width=4, border_radius=20)
        cur_diff = DIFFICULTIES[diff_idx % len(DIFFICULTIES)]
        d_cx = d_btn.left + 28
        d_cy = d_btn.centery
        pygame.draw.circle(surf, (234, 179, 8), (d_cx, d_cy), 14)
        pygame.draw.circle(surf, (254, 240, 138), (d_cx, d_cy), 7)
        dt_label = cur_diff["label_it"] if is_italian else cur_diff["label_en"]
        dt_txt = typography.render(dt_label, FontRole.DISPLAY, 18, (180, 83, 9))
        surf.blit(dt_txt, (d_btn.left + 52, d_btn.centery - dt_txt.get_height() // 2))

        # 10. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 210))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 250, REFERENCE_HEIGHT // 2 - 160, 500, 320)
            pygame.draw.rect(surf, (255, 252, 245), card, border_radius=28)
            pygame.draw.rect(surf, (234, 179, 8), card, width=5, border_radius=28)

            v_title = typography.render("LABIRINTO SUPERATO!" if is_italian else "MAZE COMPLETED!", FontRole.DISPLAY, 28, (217, 119, 6))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 35))

            for i in range(5):
                sx = card.centerx - 100 + i * 50
                sy = card.top + 130
                pygame.draw.circle(surf, (234, 179, 8), (sx, sy), 22)
                pygame.draw.circle(surf, (254, 240, 138), (sx, sy), 10)

            again_btn = pygame.Rect(card.centerx - 120, card.bottom - 80, 240, 60)
            pygame.draw.rect(surf, (34, 197, 94), again_btn, border_radius=20)
            again_lbl = typography.render("🔄 NUOVO LABIRINTO" if is_italian else "🔄 PLAY AGAIN", FontRole.DISPLAY, 20, (255, 255, 255))
            surf.blit(again_lbl, (again_btn.centerx - again_lbl.get_width() // 2, again_btn.centery - again_lbl.get_height() // 2))

        # Present Canvas
        canvas.present()
        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(60)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
