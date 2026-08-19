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
STORAGE_KEY = "labirinto_magico.progress.v1"

# --- BIOMES DEFINITION ---
BIOMES = [
    {
        "id": "forest",
        "name_it": "Bosco Incantato 🌲",
        "name_en": "Enchanted Forest 🌲",
        "bg": (20, 32, 24),
        "path": (38, 62, 45),
        "wall": (85, 138, 97),
        "wall_top": (118, 178, 132),
        "wall_shadow": (45, 78, 54),
        "hint": (254, 240, 138),
        "particle": (134, 239, 172),
        "collectible_name": "star",
        "collectible_color": (254, 202, 87),
    },
    {
        "id": "castle",
        "name_it": "Castello Cristallo 💎",
        "name_en": "Crystal Castle 💎",
        "bg": (21, 18, 46),
        "path": (40, 32, 77),
        "wall": (107, 91, 149),
        "wall_top": (155, 142, 194),
        "wall_shadow": (60, 50, 90),
        "hint": (216, 180, 254),
        "particle": (192, 132, 252),
        "collectible_name": "gem",
        "collectible_color": (168, 85, 247),
    },
    {
        "id": "candy",
        "name_it": "Valle Dolciumi 🍭",
        "name_en": "Candy Valley 🍭",
        "bg": (46, 19, 32),
        "path": (77, 34, 55),
        "wall": (199, 101, 137),
        "wall_top": (252, 165, 194),
        "wall_shadow": (120, 50, 80),
        "hint": (254, 205, 211),
        "particle": (244, 114, 182),
        "collectible_name": "candy",
        "collectible_color": (251, 146, 60),
    },
    {
        "id": "space",
        "name_it": "Spazio Stellare 🚀",
        "name_en": "Starry Cosmos 🚀",
        "bg": (10, 13, 31),
        "path": (22, 28, 59),
        "wall": (59, 91, 148),
        "wall_top": (109, 160, 240),
        "wall_shadow": (30, 48, 85),
        "hint": (147, 197, 253),
        "particle": (96, 165, 250),
        "collectible_name": "comet",
        "collectible_color": (56, 189, 248),
    },
]

HEROES = [
    {"id": "unicorn", "name_it": "Unicorno 🦄", "name_en": "Unicorn 🦄", "color": (244, 114, 182)},
    {"id": "bunny", "name_it": "Coniglietto 🐰", "name_en": "Bunny 🐰", "color": (248, 250, 252)},
    {"id": "kitty", "name_it": "Gattino 🐱", "name_en": "Kitty 🐱", "color": (251, 146, 60)},
    {"id": "fox", "name_it": "Volpina 🦊", "name_en": "Fox 🦊", "color": (249, 115, 22)},
    {"id": "panda", "name_it": "Pandino 🐼", "name_en": "Panda 🐼", "color": (226, 232, 240)},
    {"id": "dragon", "name_it": "Draghetto 🐲", "name_en": "Dragon 🐲", "color": (16, 185, 129)},
]

DIFFICULTIES = [
    {"id": "easy", "name_it": "Piccolo", "name_en": "Small", "cols": 11, "rows": 7, "stars": 3},
    {"id": "medium", "name_it": "Avventura", "name_en": "Adventure", "cols": 17, "rows": 11, "stars": 5},
    {"id": "hard", "name_it": "Maestro", "name_en": "Master", "cols": 23, "rows": 13, "stars": 7},
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
        # Step sound
        step_samples = []
        for i in range(int(rate * 0.04)):
            t = i / rate
            env = math.exp(-8.0 * (i / (rate * 0.04)))
            val = (2.0 / math.pi) * math.asin(math.sin(2.0 * math.pi * 340.0 * t))
            step_samples.append(int(32767.0 * 0.20 * env * val))
        snd_step = pygame.mixer.Sound(io.BytesIO(_synth_wav(step_samples)))
        self._sounds["step"] = snd_step

        # Bump sound
        bump_samples = []
        for i in range(int(rate * 0.06)):
            t = i / rate
            env = math.exp(-12.0 * (i / (rate * 0.06)))
            val = math.sin(2.0 * math.pi * 120.0 * t)
            bump_samples.append(int(32767.0 * 0.25 * env * val))
        snd_bump = pygame.mixer.Sound(io.BytesIO(_synth_wav(bump_samples)))
        self._sounds["bump"] = snd_bump

        # Star chime
        star_samples = []
        for i in range(int(rate * 0.18)):
            t = i / rate
            env = math.exp(-4.0 * (i / (rate * 0.18)))
            val = math.sin(2.0 * math.pi * 880.0 * t)
            star_samples.append(int(32767.0 * 0.25 * env * val))
        snd_star = pygame.mixer.Sound(io.BytesIO(_synth_wav(star_samples)))
        self._sounds["star"] = snd_star

        # Hint chime
        hint_samples = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-3.0 * (i / (rate * 0.25)))
            val = math.sin(2.0 * math.pi * 660.0 * t)
            hint_samples.append(int(32767.0 * 0.22 * env * val))
        snd_hint = pygame.mixer.Sound(io.BytesIO(_synth_wav(hint_samples)))
        self._sounds["hint"] = snd_hint

        # Win fanfare
        win_samples = []
        for i in range(int(rate * 0.40)):
            t = i / rate
            env = math.exp(-2.0 * (i / (rate * 0.40)))
            freq = 523.0 if t < 0.10 else (659.0 if t < 0.20 else (784.0 if t < 0.30 else 1046.0))
            val = math.sin(2.0 * math.pi * freq * t)
            win_samples.append(int(32767.0 * 0.30 * env * val))
        snd_win = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))
        self._sounds["win"] = snd_win

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


# --- MAZE GENERATOR ENGINE ---
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

    try:
        storage = get_storage()
    except Exception:
        storage = None

    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"

    def t(key: str, default: str) -> str:
        if resources is not None:
            try:
                res = resources.string(key)
                if res:
                    return res
            except Exception:
                pass
        return default

    # Load saved preferences
    saved_data: dict[str, Any] = {}
    if storage is not None:
        try:
            raw = storage.kv_get(STORAGE_KEY, {})
            if isinstance(raw, dict):
                saved_data = raw
        except Exception:
            pass

    hero_idx = saved_data.get("hero_idx", 0) % len(HEROES)
    biome_idx = saved_data.get("biome_idx", 0) % len(BIOMES)
    diff_idx = saved_data.get("diff_idx", 0) % len(DIFFICULTIES)

    grid: list[list[int]] = []
    entrance: dict[str, int] = {}
    exit_pos: dict[str, int] = {}
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
    victory_timer = 0.0

    def start_new_game() -> None:
        nonlocal grid, entrance, exit_pos, collectibles
        nonlocal player_r, player_c, player_x, player_y, waypoints
        nonlocal firefly_active, firefly_path, particles, stars_collected, is_victory, victory_timer
        diff = DIFFICULTIES[diff_idx]
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
        victory_timer = 0.0

    start_new_game()

    def move_step(dr: int, dc: int) -> None:
        nonlocal player_r, player_c, is_victory, stars_collected
        if is_victory:
            return
        nr, nc = player_r + dr, player_c + dc
        rows = len(grid)
        cols = len(grid[0])
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
            player_r = nr
            player_c = nc
            sounds.play("step")

            # Collectibles check
            for item in collectibles:
                if not item["collected"] and item["r"] == player_r and item["c"] == player_c:
                    item["collected"] = True
                    stars_collected += 1
                    sounds.play("star")
                    try:
                        emit_activity_event("maze.star_collected", {"stars": stars_collected})
                    except Exception:
                        pass
                    # Add star explosion particles
                    biome = BIOMES[biome_idx]
                    px = ox + (player_c + 0.5) * cs
                    py = oy + (player_r + 0.5) * cs
                    for _ in range(14):
                        ang = random.uniform(0, 6.28)
                        spd = random.uniform(1.5, 4.0)
                        particles.append({
                            "x": px,
                            "y": py,
                            "vx": math.cos(ang) * spd,
                            "vy": math.sin(ang) * spd,
                            "color": biome["collectible_color"],
                            "size": random.uniform(4.0, 7.0),
                            "life": 1.0,
                            "decay": 0.04,
                        })

            # Check exit
            if player_r == exit_pos["r"] and player_c == exit_pos["c"]:
                if not is_victory:
                    is_victory = True
                    sounds.play("win")
                    try:
                        emit_activity_event("maze.completed", {"stars": stars_collected})
                    except Exception:
                        pass
                    # Victory confetti
                    for _ in range(60):
                        particles.append({
                            "x": random.uniform(50, REFERENCE_WIDTH - 50),
                            "y": random.uniform(50, 200),
                            "vx": random.uniform(-2.0, 2.0),
                            "vy": random.uniform(1.0, 3.5),
                            "color": random.choice([(244, 114, 182), (254, 202, 87), (96, 165, 250), (52, 211, 153), (168, 85, 247)]),
                            "size": random.uniform(5.0, 9.0),
                            "life": 1.0,
                            "decay": 0.015,
                        })
        else:
            sounds.play("bump")

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        # Calculate maze grid metrics
        cols = len(grid[0]) if grid else 11
        rows = len(grid) if grid else 7
        hud_top = 70
        hud_bottom = 60
        avail_w = REFERENCE_WIDTH - 40
        avail_h = REFERENCE_HEIGHT - (hud_top + hud_bottom)
        cell_w = avail_w // cols
        cell_h = avail_h // rows
        cs = max(24, min(cell_w, cell_h, 64))
        maze_w = cols * cs
        maze_h = rows * cs
        ox = (REFERENCE_WIDTH - maze_w) // 2
        oy = hud_top + (avail_h - maze_h) // 2

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    waypoints.clear()
                    move_step(0, -1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    waypoints.clear()
                    move_step(0, 1)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    waypoints.clear()
                    move_step(-1, 0)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    waypoints.clear()
                    move_step(1, 0)
                elif event.key == pygame.K_h:
                    if not is_victory:
                        path = MazeEngine.solve_bfs(grid, player_r, player_c, exit_pos["r"], exit_pos["c"])
                        if path:
                            firefly_active = True
                            firefly_path = path
                            firefly_timer = 4.0
                            firefly_index = 0
                            firefly_pos = (float(player_c), float(player_r))
                            sounds.play("hint")
                elif event.key == pygame.K_n:
                    start_new_game()

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                mx, my = logical

                if is_victory:
                    btn_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 80, 240, 52)
                    if btn_rect.collidepoint(mx, my):
                        start_new_game()
                        continue

                # Top HUD Buttons
                # Hint button
                hint_btn = pygame.Rect(REFERENCE_WIDTH - 150, 15, 130, 42)
                if hint_btn.collidepoint(mx, my):
                    if not is_victory:
                        path = MazeEngine.solve_bfs(grid, player_r, player_c, exit_pos["r"], exit_pos["c"])
                        if path:
                            firefly_active = True
                            firefly_path = path
                            firefly_timer = 4.0
                            firefly_index = 0
                            firefly_pos = (float(player_c), float(player_r))
                            sounds.play("hint")
                    continue

                # New Maze button
                new_btn = pygame.Rect(REFERENCE_WIDTH - 290, 15, 130, 42)
                if new_btn.collidepoint(mx, my):
                    start_new_game()
                    continue

                # Bottom HUD Buttons
                # Hero button
                hero_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 180, REFERENCE_HEIGHT - 50, 110, 40)
                if hero_btn.collidepoint(mx, my):
                    hero_idx = (hero_idx + 1) % len(HEROES)
                    continue

                # Biome button
                biome_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 55, REFERENCE_HEIGHT - 50, 110, 40)
                if biome_btn.collidepoint(mx, my):
                    biome_idx = (biome_idx + 1) % len(BIOMES)
                    continue

                # Difficulty button
                diff_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 70, REFERENCE_HEIGHT - 50, 110, 40)
                if diff_btn.collidepoint(mx, my):
                    diff_idx = (diff_idx + 1) % len(DIFFICULTIES)
                    start_new_game()
                    continue

                # Click path navigation
                if not is_victory and cs > 0:
                    c = int((mx - ox) // cs)
                    r = int((my - oy) // cs)
                    if 0 <= r < rows and 0 <= c < cols and grid[r][c] == 0:
                        path = MazeEngine.solve_bfs(grid, player_r, player_c, r, c)
                        if path and len(path) > 1:
                            waypoints.clear()
                            for step in path[1:]:
                                waypoints.append(step)

        # Player position smooth interpolation
        target_x = float(player_c)
        target_y = float(player_r)
        dx = target_x - player_x
        dy = target_y - player_y
        dist = math.hypot(dx, dy)
        if dist > 0.01:
            player_x += dx * 0.30
            player_y += dy * 0.30
        else:
            player_x = target_x
            player_y = target_y
            if waypoints and not is_victory:
                next_r, next_c = waypoints.popleft()
                move_step(next_r - player_r, next_c - player_c)

        # Update firefly hint
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
                    fdist = math.hypot(fdx, fdy)
                    if fdist < 0.1:
                        firefly_index += 1
                    else:
                        firefly_pos = (fx + fdx * 0.25, fy + fdy * 0.25)
                        # Spawn firefly sparkles
                        px = ox + (fx + 0.5) * cs
                        py = oy + (fy + 0.5) * cs
                        biome = BIOMES[biome_idx]
                        particles.append({
                            "x": px + random.uniform(-4, 4),
                            "y": py + random.uniform(-4, 4),
                            "vx": random.uniform(-0.3, 0.3),
                            "vy": random.uniform(-0.3, 0.3),
                            "color": biome["hint"],
                            "size": random.uniform(3.0, 6.0),
                            "life": 1.0,
                            "decay": 0.03,
                        })

        # Update particles
        surviving = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= p["decay"]
            if p["life"] > 0:
                surviving.append(p)
        particles = surviving

        # RENDER TO CANVAS
        surf = canvas.surface
        biome = BIOMES[biome_idx]
        hero = HEROES[hero_idx]
        diff = DIFFICULTIES[diff_idx]

        # 1. Background
        surf.fill(biome["bg"])

        # 2. Draw Maze Tiles
        for r in range(rows):
            for c in range(cols):
                rx = ox + c * cs
                ry = oy + r * cs
                rect = pygame.Rect(rx, ry, cs, cs)
                if grid[r][c] == 1:
                    pygame.draw.rect(surf, biome["wall_shadow"], rect)
                    top_rect = pygame.Rect(rx + 2, ry + 2, cs - 4, cs - 6)
                    pygame.draw.rect(surf, biome["wall"], top_rect, border_radius=4)
                    highlight = pygame.Rect(rx + 3, ry + 3, cs - 6, (cs - 6) // 3)
                    pygame.draw.rect(surf, biome["wall_top"], highlight, border_radius=3)
                else:
                    pygame.draw.rect(surf, biome["path"], rect)
                    pygame.draw.circle(surf, biome["bg"], (rx + cs // 2, ry + cs // 2), max(1, cs // 12))

        # 3. Firefly Hint
        if firefly_active and firefly_path:
            alpha = min(1.0, firefly_timer / 1.0)
            hint_color = biome["hint"]
            for step_r, step_c in firefly_path:
                px = ox + (step_c + 0.5) * cs
                py = oy + (step_r + 0.5) * cs
                radius = int(cs * 0.22 * alpha)
                if radius > 0:
                    pygame.draw.circle(surf, hint_color, (int(px), int(py)), radius, 2)

        # 4. Collectibles
        t_now = time.time()
        for item in collectibles:
            if not item["collected"]:
                cx = ox + (item["c"] + 0.5) * cs
                cy = oy + (item["r"] + 0.5) * cs + math.sin(t_now * 4.0 + item["anim_t"]) * 3.0
                r_star = cs * 0.28
                pygame.draw.circle(surf, biome["collectible_color"], (int(cx), int(cy)), int(r_star))
                pygame.draw.circle(surf, (255, 255, 255), (int(cx), int(cy)), max(2, int(r_star * 0.4)))

        # 5. Entrance & Castle Exit
        en_x = ox + (entrance["c"] + 0.5) * cs
        en_y = oy + (entrance["r"] + 0.5) * cs
        pygame.draw.circle(surf, (120, 80, 50), (int(en_x), int(en_y)), int(cs * 0.35))

        ex_x = ox + (exit_pos["c"] + 0.5) * cs
        ex_y = oy + (exit_pos["r"] + 0.5) * cs
        pulse = 1.0 + math.sin(t_now * 5.0) * 0.08
        exit_r = int(cs * 0.42 * pulse)
        pygame.draw.circle(surf, (254, 202, 87), (int(ex_x), int(ex_y)), exit_r + 3, 2)
        pygame.draw.circle(surf, (239, 68, 68), (int(ex_x), int(ex_y)), exit_r)
        pygame.draw.polygon(surf, (254, 240, 138), [
            (ex_x, ex_y - exit_r * 0.8),
            (ex_x - exit_r * 0.5, ex_y + exit_r * 0.5),
            (ex_x + exit_r * 0.5, ex_y + exit_r * 0.5),
        ])

        # 6. Player Character
        char_px = ox + (player_x + 0.5) * cs
        char_py = oy + (player_y + 0.5) * cs - math.sin(t_now * 6.0) * 2.0
        char_r = int(cs * 0.40)
        pygame.draw.ellipse(surf, (10, 10, 15), pygame.Rect(char_px - char_r, oy + (player_y + 0.5) * cs + char_r * 0.4, char_r * 2, char_r * 0.6))
        pygame.draw.circle(surf, hero["color"], (int(char_px), int(char_py)), char_r)
        pygame.draw.circle(surf, (30, 30, 45), (int(char_px), int(char_py)), char_r, 2)
        eye_offset = char_r * 0.35
        pygame.draw.circle(surf, (20, 20, 30), (int(char_px - eye_offset), int(char_py - 2)), max(2, int(char_r * 0.18)))
        pygame.draw.circle(surf, (20, 20, 30), (int(char_px + eye_offset), int(char_py - 2)), max(2, int(char_r * 0.18)))
        pygame.draw.circle(surf, (255, 255, 255), (int(char_px - eye_offset + 1), int(char_py - 3)), max(1, int(char_r * 0.08)))
        pygame.draw.circle(surf, (255, 255, 255), (int(char_px + eye_offset + 1), int(char_py - 3)), max(1, int(char_r * 0.08)))

        # 7. Firefly Sprite
        if firefly_active:
            fx = ox + (firefly_pos[0] + 0.5) * cs
            fy = oy + (firefly_pos[1] + 0.5) * cs
            pygame.draw.circle(surf, (254, 240, 138), (int(fx), int(fy)), int(cs * 0.28))
            pygame.draw.circle(surf, (255, 255, 255), (int(fx), int(fy)), int(cs * 0.15))

        # 8. Particles
        for p in particles:
            cur_sz = max(1.5, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # 9. Top HUD
        title_surf = typography.render(t("activity.title", "Il Labirinto Magico"), FontRole.DISPLAY, 24, (255, 255, 255))
        surf.blit(title_surf, (80, 20))

        stars_text = f"★ {stars_collected}/{len(collectibles)}"
        stars_surf = typography.render(stars_text, FontRole.TITLE, 22, (254, 202, 87))
        surf.blit(stars_surf, (340, 22))

        # Hint Button
        hint_btn = pygame.Rect(REFERENCE_WIDTH - 150, 15, 130, 42)
        pygame.draw.rect(surf, (234, 179, 8), hint_btn, border_radius=12)
        hint_txt = typography.render(t("btn.hint", "✨ Lucciola"), FontRole.CONTROL, 18, (20, 20, 30))
        surf.blit(hint_txt, (hint_btn.centerx - hint_txt.get_width() // 2, hint_btn.centery - hint_txt.get_height() // 2))

        # New Maze Button
        new_btn = pygame.Rect(REFERENCE_WIDTH - 290, 15, 130, 42)
        pygame.draw.rect(surf, (71, 85, 105), new_btn, border_radius=12)
        new_txt = typography.render(t("btn.new_maze", "🔄 Nuovo"), FontRole.CONTROL, 18, (255, 255, 255))
        surf.blit(new_txt, (new_btn.centerx - new_txt.get_width() // 2, new_btn.centery - new_txt.get_height() // 2))

        # 10. Bottom HUD Selectors
        hero_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 180, REFERENCE_HEIGHT - 50, 110, 40)
        pygame.draw.rect(surf, (51, 65, 85), hero_btn, border_radius=10)
        hero_name = hero["name_it"] if active_locale == "it" else hero["name_en"]
        hero_lbl = typography.render("🐾 " + hero_name.split()[0], FontRole.BODY, 15, (255, 255, 255))
        surf.blit(hero_lbl, (hero_btn.centerx - hero_lbl.get_width() // 2, hero_btn.centery - hero_lbl.get_height() // 2))

        biome_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 55, REFERENCE_HEIGHT - 50, 110, 40)
        pygame.draw.rect(surf, (51, 65, 85), biome_btn, border_radius=10)
        biome_name = biome["name_it"] if active_locale == "it" else biome["name_en"]
        biome_lbl = typography.render("🎨 " + biome_name.split()[0], FontRole.BODY, 15, (255, 255, 255))
        surf.blit(biome_lbl, (biome_btn.centerx - biome_lbl.get_width() // 2, biome_btn.centery - biome_lbl.get_height() // 2))

        diff_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 70, REFERENCE_HEIGHT - 50, 110, 40)
        pygame.draw.rect(surf, (51, 65, 85), diff_btn, border_radius=10)
        diff_name = diff["name_it"] if active_locale == "it" else diff["name_en"]
        diff_lbl = typography.render("⚡ " + diff_name, FontRole.BODY, 15, (255, 255, 255))
        surf.blit(diff_lbl, (diff_btn.centerx - diff_lbl.get_width() // 2, diff_btn.centery - diff_lbl.get_height() // 2))

        # 11. Victory Modal
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 30, 200))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 200, REFERENCE_HEIGHT // 2 - 140, 400, 280)
            pygame.draw.rect(surf, (30, 41, 59), card, border_radius=20)
            pygame.draw.rect(surf, (254, 202, 87), card, width=3, border_radius=20)

            v_title = typography.render(t("victory.title", "Evviva! Sei al Castello! 🏰"), FontRole.DISPLAY, 24, (254, 202, 87))
            surf.blit(v_title, (card.centerx - v_title.get_width() // 2, card.top + 30))

            v_sub = typography.render(t("victory.subtitle", "Hai completato il labirinto!"), FontRole.BODY, 18, (241, 245, 249))
            surf.blit(v_sub, (card.centerx - v_sub.get_width() // 2, card.top + 75))

            for i in range(3):
                star_x = card.centerx - 50 + i * 50
                star_y = card.top + 130
                col = (254, 202, 87) if (i < stars_collected or len(collectibles) == 0) else (100, 116, 139)
                pygame.draw.circle(surf, col, (star_x, star_y), 18)

            again_btn = pygame.Rect(card.centerx - 110, card.bottom - 65, 220, 46)
            pygame.draw.rect(surf, (34, 197, 94), again_btn, border_radius=14)
            again_lbl = typography.render(t("btn.play_again", "🎉 Gioca Ancora!"), FontRole.CONTROL, 20, (255, 255, 255))
            surf.blit(again_lbl, (again_btn.centerx - again_lbl.get_width() // 2, again_btn.centery - again_lbl.get_height() // 2))

        # Present Canvas
        canvas.present(clear=theme.background)

        # Star pointer cursor
        if pygame.mouse.get_focused():
            mpos = pygame.mouse.get_pos()
            pygame.draw.circle(screen, (254, 202, 87), mpos, metrics.px(10))
            pygame.draw.circle(screen, (255, 255, 255), mpos, metrics.px(5))

        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "hero_idx": hero_idx,
                "biome_idx": biome_idx,
                "diff_idx": diff_idx,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
