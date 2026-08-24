from __future__ import annotations

import time
from typing import Any

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
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.typography import GreiaTypography

from .maze_art import MazeArt
from .maze_audio import LabyrinthAudio
from .maze_model import (
    BIOMES,
    DIFFICULTIES,
    HEROES,
    CollectibleStar,
    MazeEngine,
    MazeState,
)
from .maze_renderer import MazeRenderer

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "labirinto_magico.progress.v2"


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class MazeApp:
    def __init__(self) -> None:
        self.running = False
        self.biome_idx = 0
        self.diff_idx = 0
        self.hero_idx = 0
        self.total_stars = 0
        self.storage = get_storage()
        self.sounds = LabyrinthAudio()
        self.typography = GreiaTypography()
        self.renderer = MazeRenderer(self.typography)
        self.state: MazeState | None = None
        self.baked_maze: pygame.Surface | None = None
        self.ambient_particles: list[dict[str, Any]] = []
        self.celebration_particles: list[dict[str, Any]] = []
        self._load_saved_progress()

    def _load_saved_progress(self) -> None:
        if self.storage:
            saved = self.storage.kv_get(STORAGE_KEY)
            if isinstance(saved, dict):
                self.total_stars = saved.get("stars", 0)

    def _save_progress(self) -> None:
        if self.storage:
            self.storage.kv_set(STORAGE_KEY, {"stars": self.total_stars})

    def start_game(self, screen: pygame.Surface, metrics: ChildUiMetrics) -> None:
        diff = DIFFICULTIES[self.diff_idx]
        biome = BIOMES[self.biome_idx]
        raw_grid, entrance, exit_pos, raw_collectibles = MazeEngine.generate(
            diff["cols"],
            diff["rows"],
            diff["stars"],
        )
        stars = [
            CollectibleStar(r=c["r"], c=c["c"], collected=False, anim_t=c.get("anim_t", 0.0))
            for c in raw_collectibles
        ]
        self.state = MazeState(
            cols=diff["cols"],
            rows=diff["rows"],
            grid=raw_grid,
            entrance=entrance,
            exit_pos=exit_pos,
            collectibles=stars,
            player_r=entrance["r"],
            player_c=entrance["c"],
            player_x=float(entrance["c"]),
            player_y=float(entrance["r"]),
            facing_right=True,
            is_victory=False,
            sliding_waypoints=[],
            slide_speed=18.0,
        )
        self._rebake_maze_surface(screen, metrics)

    def _rebake_maze_surface(self, screen: pygame.Surface, metrics: ChildUiMetrics) -> None:
        if self.state is None:
            return
        w, h = screen.get_size()
        cs, _, _, _ = self.renderer.compute_maze_viewport(w, h, self.state.cols, self.state.rows, metrics)
        biome = BIOMES[self.biome_idx]
        self.baked_maze = MazeArt.bake_static_maze(
            self.state.grid,
            biome,
            cs,
            self.state.cols,
            self.state.rows,
        )

    def trigger_move(self, dr: int, dc: int) -> None:
        if self.state is None or self.state.is_victory:
            return

        # Facing direction
        if dc < 0:
            self.state.facing_right = False
        elif dc > 0:
            self.state.facing_right = True

        path = MazeEngine.compute_slide_path(
            self.state.grid,
            self.state.player_r,
            self.state.player_c,
            dr,
            dc,
            self.state.exit_pos,
        )
        if path:
            self.state.sliding_waypoints = path
            self.sounds.play("step")
        else:
            self.sounds.play("bump")

    def handle_click(
        self,
        mx: int,
        my: int,
        screen: pygame.Surface,
        metrics: ChildUiMetrics,
    ) -> None:
        if self.state is None:
            return

        w, h = screen.get_size()

        # 1. Victory modal click
        if self.state.is_victory:
            card_w = min(metrics.px(520), w - 40)
            card_h = min(metrics.px(330), h - 40)
            card = pygame.Rect(w // 2 - card_w // 2, h // 2 - card_h // 2, card_w, card_h)
            play_btn = pygame.Rect(
                card.centerx - metrics.px(130),
                card.top + metrics.px(190),
                metrics.px(260),
                metrics.px(56),
            )
            if play_btn.collidepoint(mx, my):
                self.start_game(screen, metrics)
            return

        # 2. Top HUD buttons
        hud = self.renderer.get_hud_layout(w, h, metrics)
        if hud["diff_btn"].collidepoint(mx, my):
            self.diff_idx = (self.diff_idx + 1) % len(DIFFICULTIES)
            self.start_game(screen, metrics)
            return
        if hud["biome_btn"].collidepoint(mx, my):
            self.biome_idx = (self.biome_idx + 1) % len(BIOMES)
            self._rebake_maze_surface(screen, metrics)
            return
        if hud["new_btn"].collidepoint(mx, my):
            self.start_game(screen, metrics)
            return

        # 3. Direct click inside maze
        cs, ox, oy, maze_rect = self.renderer.compute_maze_viewport(
            w,
            h,
            self.state.cols,
            self.state.rows,
            metrics,
        )
        if maze_rect.collidepoint(mx, my):
            target_c = (mx - ox) // cs
            target_r = (my - oy) // cs
            dr, dc = MazeEngine.resolve_click_direction(
                self.state.grid,
                self.state.player_r,
                self.state.player_c,
                target_r,
                target_c,
                self.state.exit_pos,
            )
            if dr != 0 or dc != 0:
                self.trigger_move(dr, dc)
            else:
                self.sounds.play("bump")

    def update(self, dt: float, screen: pygame.Surface, metrics: ChildUiMetrics) -> None:
        if self.state is None:
            return

        # Update sliding animation
        if self.state.sliding_waypoints:
            next_r, next_c = self.state.sliding_waypoints[0]
            dx = float(next_c) - self.state.player_x
            dy = float(next_r) - self.state.player_y
            dist = (dx * dx + dy * dy) ** 0.5
            step = self.state.slide_speed * dt

            if dist <= step or dist < 0.05:
                # Arrived at next cell
                self.state.player_r = next_r
                self.state.player_c = next_c
                self.state.player_x = float(next_c)
                self.state.player_y = float(next_r)
                self.state.sliding_waypoints.pop(0)

                # Check star pickup
                w, h = screen.get_size()
                cs, ox, oy, _ = self.renderer.compute_maze_viewport(
                    w,
                    h,
                    self.state.cols,
                    self.state.rows,
                    metrics,
                )
                for star in self.state.collectibles:
                    if not star.collected and star.r == self.state.player_r and star.c == self.state.player_c:
                        star.collected = True
                        self.total_stars += 1
                        self.sounds.play("star")
                        self._save_progress()
                        star_px = ox + (star.c + 0.5) * cs
                        star_py = oy + (star.r + 0.5) * cs
                        self.celebration_particles.extend(
                            MazeArt.create_star_burst(star_px, star_py, (254, 240, 138), 14)
                        )
                        try:
                            emit_activity_event("maze.star_collected", {"stars": self.total_stars})
                        except Exception:
                            pass

                # Check victory
                if not self.state.is_victory and self.state.player_r == self.state.exit_pos["r"] and self.state.player_c == self.state.exit_pos["c"]:
                    self.state.is_victory = True
                    self.state.sliding_waypoints.clear()
                    self.total_stars += 5
                    self.sounds.play("win")
                    self._save_progress()
                    biome = BIOMES[self.biome_idx]
                    diff = DIFFICULTIES[self.diff_idx]
                    try:
                        emit_activity_event(
                            "maze.completed",
                            {"biome": biome["id"], "difficulty": diff["id"], "stars": self.total_stars},
                        )
                    except Exception:
                        pass
            else:
                # Interpolate towards next cell
                self.state.player_x += (dx / dist) * step
                self.state.player_y += (dy / dist) * step
        else:
            # Idle smooth centering
            self.state.player_x += (self.state.player_c - self.state.player_x) * 0.45
            self.state.player_y += (self.state.player_r - self.state.player_y) * 0.45

        # Update particles
        w, h = screen.get_size()
        MazeArt.update_ambient_particles(self.ambient_particles, w, h)
        self.celebration_particles = MazeArt.update_celebration_particles(self.celebration_particles)

    def run(self) -> int:
        pygame.init()
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        pygame.mouse.set_visible(False)
        clock = pygame.time.Clock()
        metrics = ChildUiMetrics.for_size(*screen.get_size())
        canvas = PygameReferenceCanvas(screen)

        self.ambient_particles = MazeArt.init_ambient_particles(screen.get_width(), screen.get_height(), 25)
        self.start_game(canvas.surface, metrics)
        first_frame_ready = False

        self.running = True
        while self.running and not activity_stop_requested():
            dt = clock.tick(30) / 1000.0
            t_now = time.time()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.trigger_move(-1, 0)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.trigger_move(1, 0)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.trigger_move(0, -1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.trigger_move(0, 1)

                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.get_surface() or screen
                    metrics = ChildUiMetrics.for_size(*screen.get_size())
                    canvas = PygameReferenceCanvas(screen)
                    self._rebake_maze_surface(canvas.surface, metrics)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if is_home_clicked(screen, event.pos):
                        self.running = False
                        continue
                    pointer = canvas.pointer(event.pos)
                    if pointer is None:
                        continue
                    mx, my = int(pointer[0]), int(pointer[1])
                    if not _is_safe_point(screen, event.pos):
                        continue
                    self.handle_click(mx, my, canvas.surface, metrics)

            self.update(dt, canvas.surface, metrics)

            if self.state is not None and self.baked_maze is not None:
                biome = BIOMES[self.biome_idx]
                diff = DIFFICULTIES[self.diff_idx]
                self.renderer.draw(
                    canvas.surface,
                    self.state,
                    biome,
                    diff,
                    self.total_stars,
                    self.baked_maze,
                    self.ambient_particles,
                    self.celebration_particles,
                    metrics,
                    t_now,
                )

            canvas.present()
            pygame.display.flip()

            if not first_frame_ready:
                mark_activity_ready()
                first_frame_ready = True

        return 0
