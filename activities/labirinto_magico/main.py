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
from greia_platform.activity_ui import ChildUiMetrics, is_home_clicked
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
ASSETS_DIR = Path(__file__).parent / "assets" / "runtime"

BIOMES = [
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

HEROES = [
    {"id": "fox", "name": "Tito", "color": (249, 115, 22)},
    {"id": "bunny", "name": "Flash", "color": (248, 250, 252)},
    {"id": "unicorn", "name": "Lilli", "color": (244, 114, 182)},
    {"id": "kitty", "name": "Mimi", "color": (251, 146, 60)},
    {"id": "dragon", "name": "Drago", "color": (34, 197, 94)},
    {"id": "puppy", "name": "Cucciolo", "color": (217, 119, 6)},
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
        step_samples = []
        for i in range(int(rate * 0.05)):
            t = i / rate
            env = math.exp(-35.0 * t)
            val = math.sin(2.0 * math.pi * 320.0 * t)
            step_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["step"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(step_samples)))

        star_samples = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-8.0 * t)
            val = math.sin(2.0 * math.pi * (880.0 + 440.0 * t) * t)
            star_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["star"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(star_samples)))

        win_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50]
        for i in range(int(rate * 0.65)):
            t = i / rate
            env = math.exp(-2.5 * t)
            n_idx = min(3, int(t / 0.15))
            val = math.sin(2.0 * math.pi * notes[n_idx] * t)
            win_samples.append(int(32767.0 * 0.35 * env * val))
        self._sounds["win"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


MazeAudio = LabyrinthAudio


class MazeEngine:
    @staticmethod
    def generate(cols: int, rows: int, num_stars: int = 3) -> tuple[list[list[int]], dict[str, int], dict[str, int], list[dict[str, Any]]]:
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
            collectibles.append({"r": r, "c": c, "collected": False, "anim_t": random.random() * 6.28})

        return grid, entrance, exit_pos, collectibles

    @staticmethod
    def solve_bfs(grid: list[list[int]], start_r: int, start_c: int, goal_r: int, goal_c: int) -> list[tuple[int, int]]:
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
    def compute_slide_path(grid: list[list[int]], r: int, c: int, dr: int, dc: int, exit_pos: dict[str, int]) -> list[tuple[int, int]]:
        rows = len(grid)
        cols = len(grid[0])
        path = []
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
            # Check decision point
            choices = 0
            for cdr, cdc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ckr, ckc = cr + cdr, cc + cdc
                if 0 <= ckr < rows and 0 <= ckc < cols and grid[ckr][ckc] == 0:
                    choices += 1
            if choices > 2:
                break

        return path


# Surface and Scale Cache
_IMAGE_CACHE: dict[str, pygame.Surface] = {}
_SCALE_CACHE: dict[tuple[str, int, int], pygame.Surface] = {}


def _load_asset_surface(filename: str) -> pygame.Surface | None:
    if filename not in _IMAGE_CACHE:
        p = ASSETS_DIR / filename
        if p.exists():
            try:
                _IMAGE_CACHE[filename] = pygame.image.load(str(p)).convert_alpha()
            except Exception:
                _IMAGE_CACHE[filename] = None
        else:
            _IMAGE_CACHE[filename] = None
    return _IMAGE_CACHE[filename]


def _get_scaled_asset(filename: str, width: int, height: int) -> pygame.Surface | None:
    key = (filename, width, height)
    if key not in _SCALE_CACHE:
        orig = _load_asset_surface(filename)
        if orig is not None:
            _SCALE_CACHE[key] = pygame.transform.smoothscale(orig, (width, height))
        else:
            _SCALE_CACHE[key] = None
    return _SCALE_CACHE[key]


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

    storage = get_storage()
    saved_data = storage.kv_get(STORAGE_KEY) if storage else {}
    if not isinstance(saved_data, dict):
        saved_data = {}
    total_stars = saved_data.get("stars", 0)

    biome_idx = 0
    diff_idx = 0
    hero_idx = 0
    is_victory = False

    grid: list[list[int]] = []
    entrance = {"r": 1, "c": 1}
    exit_pos = {"r": 1, "c": 1}
    player_r = 1
    player_c = 1
    player_x = 1.0
    player_y = 1.0
    facing_right = True

    collectibles: list[dict[str, Any]] = []
    ambient_particles: list[dict[str, Any]] = []
    celebration_particles: list[dict[str, Any]] = []

    def start_game() -> None:
        nonlocal grid, entrance, exit_pos, player_r, player_c, player_x, player_y, collectibles, is_victory
        diff = DIFFICULTIES[diff_idx]
        grid, entrance, exit_pos, collectibles = MazeEngine.generate(diff["cols"], diff["rows"], diff["stars"])
        player_r, player_c = entrance["r"], entrance["c"]
        player_x, player_y = float(player_c), float(player_r)
        is_victory = False

    start_game()
    mark_activity_ready()

    for _ in range(25):
        ambient_particles.append({
            "x": random.uniform(50, REFERENCE_WIDTH - 50),
            "y": random.uniform(50, REFERENCE_HEIGHT - 50),
            "vx": random.uniform(-0.4, 0.4),
            "vy": random.uniform(-0.5, -0.1),
            "size": random.uniform(2, 5),
            "alpha": random.uniform(80, 200),
        })

    running = True
    while running and not activity_stop_requested():
        dt = clock.tick(30) / 1000.0
        t_now = time.time()
        biome = BIOMES[biome_idx]
        diff = DIFFICULTIES[diff_idx]

        maze_w = diff["cols"]
        maze_h = diff["rows"]
        avail_w = 640
        avail_h = 420
        cs = min(avail_w // maze_w, avail_h // maze_h)
        ox = 80 + (avail_w - maze_w * cs) // 2
        oy = 90 + (avail_h - maze_h * cs) // 2

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif not is_victory:
                    dr, dc = 0, 0
                    if event.key in (pygame.K_UP, pygame.K_w):
                        dr = -1
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        dr = 1
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        dc = -1
                        facing_right = False
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        dc = 1
                        facing_right = True

                    if (dr != 0 or dc != 0):
                        nr = player_r + dr
                        nc = player_c + dc
                        if 0 <= nr < maze_h and 0 <= nc < maze_w and grid[nr][nc] == 0:
                            player_r = nr
                            player_c = nc
                            sounds.play("step")

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_home_clicked(screen, event.pos):
                    running = False
                    continue
                pointer = canvas.pointer(event.pos)
                if pointer is None:
                    continue
                mx, my = int(pointer[0]), int(pointer[1])

                if not _is_safe_point(screen, event.pos):
                    continue

                if is_victory:
                    play_again_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 140, REFERENCE_HEIGHT // 2 + 70, 280, 64)
                    if play_again_btn.collidepoint(mx, my):
                        start_game()
                    continue

                biome_btn = pygame.Rect(REFERENCE_WIDTH - 280, 16, 250, 56)
                if biome_btn.collidepoint(mx, my):
                    biome_idx = (biome_idx + 1) % len(BIOMES)
                    continue

                diff_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 80, 16, 160, 56)
                if diff_btn.collidepoint(mx, my):
                    diff_idx = (diff_idx + 1) % len(DIFFICULTIES)
                    start_game()
                    continue

                pad_cx, pad_cy = 875, 330
                btn_sz = 60
                btn_up = pygame.Rect(pad_cx - btn_sz // 2, pad_cy - 85, btn_sz, btn_sz)
                btn_down = pygame.Rect(pad_cx - btn_sz // 2, pad_cy + 25, btn_sz, btn_sz)
                btn_left = pygame.Rect(pad_cx - 85, pad_cy - btn_sz // 2, btn_sz, btn_sz)
                btn_right = pygame.Rect(pad_cx + 25, pad_cy - btn_sz // 2, btn_sz, btn_sz)

                dr, dc = 0, 0
                if btn_up.collidepoint(mx, my):
                    dr = -1
                elif btn_down.collidepoint(mx, my):
                    dr = 1
                elif btn_left.collidepoint(mx, my):
                    dc = -1
                    facing_right = False
                elif btn_right.collidepoint(mx, my):
                    dc = 1
                    facing_right = True

                if (dr != 0 or dc != 0):
                    nr = player_r + dr
                    nc = player_c + dc
                    if 0 <= nr < maze_h and 0 <= nc < maze_w and grid[nr][nc] == 0:
                        player_r = nr
                        player_c = nc
                        sounds.play("step")

        player_x += (player_c - player_x) * 0.45
        player_y += (player_r - player_y) * 0.45

        for star in collectibles:
            if not star["collected"] and star["r"] == player_r and star["c"] == player_c:
                star["collected"] = True
                sounds.play("star")
                total_stars += 1
                if storage:
                    storage.kv_set(STORAGE_KEY, {"stars": total_stars})
                for _ in range(12):
                    celebration_particles.append({
                        "x": ox + (star["c"] + 0.5) * cs,
                        "y": oy + (star["r"] + 0.5) * cs,
                        "vx": random.uniform(-3, 3),
                        "vy": random.uniform(-3, 3),
                        "color": (254, 240, 138),
                        "size": random.uniform(6, 12),
                    })

        if not is_victory and player_r == exit_pos["r"] and player_c == exit_pos["c"]:
            is_victory = True
            sounds.play("win")
            total_stars += 5
            if storage:
                storage.kv_set(STORAGE_KEY, {"stars": total_stars})
            try:
                emit_activity_event("maze.completed", {"biome": biome["id"], "difficulty": diff["id"], "stars": total_stars})
            except Exception:
                pass

        for p in ambient_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["y"] < 20:
                p["y"] = REFERENCE_HEIGHT - 20
                p["x"] = random.uniform(50, REFERENCE_WIDTH - 50)

        surviving_cp = []
        for p in celebration_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["size"] = max(1.0, p["size"] - 0.2)
            if p["size"] > 1.0:
                surviving_cp.append(p)
        celebration_particles = surviving_cp

        surf = canvas.surface

        # 1. Background
        surf.fill(biome["bg"])

        for p in ambient_particles:
            alpha_surf = pygame.Surface((int(p["size"] * 2), int(p["size"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(alpha_surf, (*biome["particle_col"], int(p["alpha"])), (int(p["size"]), int(p["size"])), int(p["size"]))
            surf.blit(alpha_surf, (p["x"] - p["size"], p["y"] - p["size"]))

        # 2. Maze Grid with 3D Depth Walls
        for r in range(maze_h):
            for c in range(maze_w):
                rx = ox + c * cs
                ry = oy + r * cs
                cell_rect = pygame.Rect(rx, ry, cs, cs)

                if grid[r][c] == 1:
                    pygame.draw.rect(surf, biome["wall_shadow"], cell_rect)
                    wall_inner = pygame.Rect(rx + 2, ry + 2, max(2, cs - 4), max(2, cs - 4))
                    pygame.draw.rect(surf, biome["wall"], wall_inner, border_radius=max(2, cs // 6))
                    pygame.draw.rect(surf, biome["wall_top"], (rx + 4, ry + 4, max(2, cs - 8), max(2, cs // 4)), border_radius=max(1, cs // 8))
                else:
                    pygame.draw.rect(surf, biome["path"], cell_rect)
                    pygame.draw.circle(surf, biome["bg"], (rx + cs // 2, ry + cs // 2), max(1, cs // 8))

        # 3. Portal Goal
        portal_cx = int(ox + (exit_pos["c"] + 0.5) * cs)
        portal_cy = int(oy + (exit_pos["r"] + 0.5) * cs)
        portal_sz = max(24, int(cs * 1.3))
        portal_surf = _get_scaled_asset("portal_goal.png", portal_sz, portal_sz)
        if portal_surf is not None:
            rot_portal = pygame.transform.rotate(portal_surf, (t_now * 45.0) % 360)
            surf.blit(rot_portal, rot_portal.get_rect(center=(portal_cx, portal_cy)))
        else:
            pygame.draw.circle(surf, (168, 85, 247), (portal_cx, portal_cy), portal_sz // 2)
            pygame.draw.circle(surf, (254, 240, 138), (portal_cx, portal_cy), portal_sz // 3)

        # 4. Collectible Crystal Stars
        star_sz = max(18, int(cs * 0.75))
        star_surf = _get_scaled_asset("star_crystal.png", star_sz, star_sz)
        for star in collectibles:
            if not star["collected"]:
                scx = int(ox + (star["c"] + 0.5) * cs)
                scy = int(oy + (star["r"] + 0.5) * cs + math.sin(t_now * 4.0 + star["anim_t"]) * 3.0)
                if star_surf is not None:
                    surf.blit(star_surf, (scx - star_sz // 2, scy - star_sz // 2))
                else:
                    pygame.draw.circle(surf, (250, 204, 21), (scx, scy), star_sz // 2)

        # 5. Adventurer Tito the Fox Mascot
        tito_cx = int(ox + (player_x + 0.5) * cs)
        tito_cy = int(oy + (player_y + 0.5) * cs - math.sin(t_now * 8.0) * 2.5)
        tito_sz = max(24, int(cs * 1.15))
        tito_surf = _get_scaled_asset("tito_adventurer.png", tito_sz, tito_sz)
        if tito_surf is not None:
            char_img = tito_surf if facing_right else pygame.transform.flip(tito_surf, True, False)
            surf.blit(char_img, (tito_cx - tito_sz // 2, tito_cy - tito_sz // 2))
        else:
            pygame.draw.circle(surf, (249, 115, 22), (tito_cx, tito_cy), tito_sz // 2)

        # 6. D-Pad Arrow Controls
        pad_cx, pad_cy = 875, 330
        btn_sz = 64
        arrow_raw = _get_scaled_asset("arrow_btn.png", btn_sz, btn_sz)

        btn_up = pygame.Rect(pad_cx - btn_sz // 2, pad_cy - 85, btn_sz, btn_sz)
        if arrow_raw is not None:
            surf.blit(arrow_raw, btn_up.topleft)
        btn_down = pygame.Rect(pad_cx - btn_sz // 2, pad_cy + 25, btn_sz, btn_sz)
        if arrow_raw is not None:
            surf.blit(pygame.transform.rotate(arrow_raw, 180), btn_down.topleft)
        btn_left = pygame.Rect(pad_cx - 85, pad_cy - btn_sz // 2, btn_sz, btn_sz)
        if arrow_raw is not None:
            surf.blit(pygame.transform.rotate(arrow_raw, 90), btn_left.topleft)
        btn_right = pygame.Rect(pad_cx + 25, pad_cy - btn_sz // 2, btn_sz, btn_sz)
        if arrow_raw is not None:
            surf.blit(pygame.transform.rotate(arrow_raw, 270), btn_right.topleft)

        # 7. Top HUD (Star Pill, Difficulty & Biome Switcher)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surf, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        s_txt = typography.render(str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 58, star_pill.centery - s_txt.get_height() // 2))

        diff_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 90, 16, 180, 56)
        pygame.draw.rect(surf, (255, 255, 255), diff_btn, border_radius=18)
        pygame.draw.rect(surf, (56, 189, 248), diff_btn, width=3, border_radius=18)
        d_txt = typography.render(diff["label_it"], FontRole.DISPLAY, 20, (3, 105, 161))
        surf.blit(d_txt, (diff_btn.centerx - d_txt.get_width() // 2, diff_btn.centery - d_txt.get_height() // 2))

        biome_btn = pygame.Rect(REFERENCE_WIDTH - 280, 16, 250, 56)
        pygame.draw.rect(surf, (255, 255, 255), biome_btn, border_radius=18)
        pygame.draw.rect(surf, biome["wall"], biome_btn, width=3, border_radius=18)
        b_txt = typography.render(biome["name_it"], FontRole.DISPLAY, 18, (30, 41, 59))
        surf.blit(b_txt, (biome_btn.centerx - b_txt.get_width() // 2, biome_btn.centery - b_txt.get_height() // 2))

        # 8. Celebration Particles
        for p in celebration_particles:
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))

        # 9. Victory Modal Card
        if is_victory:
            overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            overlay.fill((15, 23, 42, 215))
            surf.blit(overlay, (0, 0))

            card = pygame.Rect(REFERENCE_WIDTH // 2 - 250, REFERENCE_HEIGHT // 2 - 160, 500, 320)
            pygame.draw.rect(surf, (255, 252, 245), card, border_radius=28)
            pygame.draw.rect(surf, (234, 179, 8), card, width=5, border_radius=28)

            vic_title = typography.render("PORTALE RAGGIUNTO! 🌀", FontRole.DISPLAY, 34, (180, 83, 9))
            surf.blit(vic_title, (card.centerx - vic_title.get_width() // 2, card.top + 36))

            vic_sub = typography.render("Tito ha trovato l'uscita magica!", FontRole.BODY, 22, (71, 85, 105))
            surf.blit(vic_sub, (card.centerx - vic_sub.get_width() // 2, card.top + 95))

            for s_idx in range(5):
                sx = card.centerx - 100 + s_idx * 50
                sy = card.top + 160
                pygame.draw.circle(surf, (234, 179, 8), (sx, sy), 18)
                pygame.draw.circle(surf, (254, 240, 138), (sx, sy), 14)

            play_btn = pygame.Rect(card.centerx - 140, card.top + 215, 280, 64)
            pygame.draw.rect(surf, (34, 197, 94), play_btn, border_radius=20)
            pygame.draw.rect(surf, (22, 101, 52), play_btn, width=3, border_radius=20)
            btn_txt = typography.render("NUOVO LABIRINTO 🔄", FontRole.DISPLAY, 24, (255, 255, 255))
            surf.blit(btn_txt, (play_btn.centerx - btn_txt.get_width() // 2, play_btn.centery - btn_txt.get_height() // 2))

        canvas.present()
        pygame.display.flip()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
