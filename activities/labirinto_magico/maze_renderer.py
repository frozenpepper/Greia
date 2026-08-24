from __future__ import annotations

import math
from typing import Any

import pygame

from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import FontRole, GreiaTypography

try:
    from maze_art import (
        get_flipped_asset,
        get_particle_surface,
        get_portal_rotation_frames,
        get_scaled_asset,
    )
    from maze_model import BIOMES, DIFFICULTIES, CollectibleStar, MazeState
except ImportError:
    from .maze_art import (
        get_flipped_asset,
        get_particle_surface,
        get_portal_rotation_frames,
        get_scaled_asset,
    )
    from .maze_model import BIOMES, DIFFICULTIES, CollectibleStar, MazeState


class MazeRenderer:
    def __init__(self, typography: GreiaTypography | None = None) -> None:
        self.typography = typography or GreiaTypography()
        self._text_cache: dict[tuple[str, FontRole, int, tuple[int, ...]], pygame.Surface] = {}
        self._hud_cache: dict[tuple[int, int, str, str], pygame.Surface] = {}

    def _render_text(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int],
    ) -> pygame.Surface:
        key = (text, role, size, color)
        if key not in self._text_cache:
            self._text_cache[key] = self.typography.render(text, role, size, color)
        return self._text_cache[key]

    def get_hud_layout(self, width: int, height: int, metrics: ChildUiMetrics) -> dict[str, pygame.Rect]:
        chrome = ActivitySystemChromeLayout.for_surface(width, height)
        protected = chrome.protected_region
        top_bar_h = max(metrics.toolbar_height, protected.height)
        btn_h = metrics.px(54)
        btn_y = max(4, (top_bar_h - btn_h) // 2)

        # Star counter pill
        star_x = protected.right + metrics.gap
        star_w = metrics.px(110)
        star_pill = pygame.Rect(star_x, btn_y, star_w, btn_h)

        # Difficulty button
        diff_x = star_pill.right + metrics.gap
        diff_w = metrics.px(160)
        diff_btn = pygame.Rect(diff_x, btn_y, diff_w, btn_h)

        # Biome button
        biome_x = diff_btn.right + metrics.gap
        biome_w = metrics.px(210)
        biome_btn = pygame.Rect(biome_x, btn_y, biome_w, btn_h)

        # New maze button at right
        new_w = metrics.px(130)
        new_x = width - metrics.margin - new_w
        new_btn = pygame.Rect(new_x, btn_y, new_w, btn_h)

        return {
            "star_pill": star_pill,
            "diff_btn": diff_btn,
            "biome_btn": biome_btn,
            "new_btn": new_btn,
        }

    def compute_maze_viewport(
        self,
        width: int,
        height: int,
        maze_w: int,
        maze_h: int,
        metrics: ChildUiMetrics,
    ) -> tuple[int, int, int, pygame.Rect]:
        """Calculate cell size and pixel offsets (cs, ox, oy, maze_rect) to fill the screen."""
        chrome = ActivitySystemChromeLayout.for_surface(width, height)
        top_bar_h = max(metrics.toolbar_height, chrome.protected_region.height)
        top_margin = top_bar_h + metrics.px(6)
        bottom_margin = metrics.margin
        side_margin = metrics.margin

        avail_w = max(100, width - side_margin * 2)
        avail_h = max(100, height - top_margin - bottom_margin)

        cs = max(8, min(avail_w // maze_w, avail_h // maze_h))
        real_w = maze_w * cs
        real_h = maze_h * cs

        ox = side_margin + (avail_w - real_w) // 2
        oy = top_margin + (avail_h - real_h) // 2
        maze_rect = pygame.Rect(ox, oy, real_w, real_h)

        return cs, ox, oy, maze_rect

    def draw(
        self,
        screen: pygame.Surface,
        state: MazeState,
        biome: dict[str, Any],
        diff: dict[str, Any],
        total_stars: int,
        baked_maze: pygame.Surface,
        ambient_particles: list[dict[str, Any]],
        celebration_particles: list[dict[str, Any]],
        metrics: ChildUiMetrics,
        t_now: float,
    ) -> None:
        w, h = screen.get_size()
        cs, ox, oy, maze_rect = self.compute_maze_viewport(w, h, state.cols, state.rows, metrics)

        # 1. Fill background
        screen.fill(biome["bg"])

        # 2. Ambient particles (using pre-rendered cached alpha surfaces)
        part_col = biome["particle_col"]
        for p in ambient_particles:
            p_surf = get_particle_surface(part_col, int(p["alpha"]), int(p["size"]))
            screen.blit(p_surf, (int(p["x"] - p["size"]), int(p["y"] - p["size"])))

        # 3. Outer tactile shadow & frame around maze
        frame_shadow = maze_rect.inflate(metrics.px(8), metrics.px(8)).move(0, metrics.px(4))
        pygame.draw.rect(screen, biome["wall_shadow"], frame_shadow, border_radius=metrics.radius + 2)
        pygame.draw.rect(screen, (255, 255, 255), maze_rect.inflate(metrics.px(4), metrics.px(4)), width=2, border_radius=metrics.radius)

        # 4. Blit pre-rendered static maze surface
        screen.blit(baked_maze, (ox, oy))

        # 5. Portal goal (using pre-rendered rotated frames lookup)
        portal_cx = int(ox + (state.exit_pos["c"] + 0.5) * cs)
        portal_cy = int(oy + (state.exit_pos["r"] + 0.5) * cs)
        portal_sz = max(20, int(cs * 1.35))
        portal_frames = get_portal_rotation_frames(portal_sz)
        frame_idx = int(t_now * 12.0) % len(portal_frames)
        rot_portal = portal_frames[frame_idx]
        screen.blit(rot_portal, rot_portal.get_rect(center=(portal_cx, portal_cy)))

        # 6. Collectible Crystal Stars
        star_sz = max(14, int(cs * 0.8))
        star_surf = get_scaled_asset("star_crystal.png", star_sz, star_sz)
        for star in state.collectibles:
            if not star.collected:
                scx = int(ox + (star.c + 0.5) * cs)
                scy = int(oy + (star.r + 0.5) * cs + math.sin(t_now * 4.0 + star.anim_t) * 2.0)
                if star_surf is not None:
                    screen.blit(star_surf, (scx - star_sz // 2, scy - star_sz // 2))
                else:
                    pygame.draw.circle(screen, (250, 204, 21), (scx, scy), star_sz // 2)

        # 7. Adventurer Character (Tito) - using cached flipped sprite
        tito_cx = int(ox + (state.player_x + 0.5) * cs)
        tito_cy = int(oy + (state.player_y + 0.5) * cs - math.sin(t_now * 8.0) * 2.0)
        tito_sz = max(18, int(cs * 1.25))
        if state.facing_right:
            char_img = get_scaled_asset("tito_adventurer.png", tito_sz, tito_sz)
        else:
            char_img = get_flipped_asset("tito_adventurer.png", tito_sz, tito_sz)

        if char_img is not None:
            screen.blit(char_img, (tito_cx - tito_sz // 2, tito_cy - tito_sz // 2))
        else:
            pygame.draw.circle(screen, (249, 115, 22), (tito_cx, tito_cy), tito_sz // 2)

        # 8. Celebration sparkle particles
        for p in celebration_particles:
            pygame.draw.circle(screen, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))

        # 9. Top HUD Controls
        hud = self.get_hud_layout(w, h, metrics)

        # 9a. Star Pill
        sp = hud["star_pill"]
        pygame.draw.rect(screen, (255, 255, 255), sp, border_radius=metrics.radius)
        pygame.draw.rect(screen, (234, 179, 8), sp, width=2, border_radius=metrics.radius)
        pygame.draw.circle(screen, (234, 179, 8), (sp.left + metrics.px(24), sp.centery), metrics.px(14))
        pygame.draw.circle(screen, (254, 240, 138), (sp.left + metrics.px(24), sp.centery), metrics.px(10))
        s_txt = self._render_text(str(total_stars), FontRole.DISPLAY, metrics.px(22), (180, 83, 9))
        screen.blit(s_txt, (sp.left + metrics.px(46), sp.centery - s_txt.get_height() // 2))

        # 9b. Difficulty Button
        db = hud["diff_btn"]
        pygame.draw.rect(screen, (255, 255, 255), db, border_radius=metrics.radius)
        pygame.draw.rect(screen, (56, 189, 248), db, width=2, border_radius=metrics.radius)
        d_txt = self._render_text(diff["label_it"], FontRole.DISPLAY, metrics.px(18), (3, 105, 161))
        screen.blit(d_txt, (db.centerx - d_txt.get_width() // 2, db.centery - d_txt.get_height() // 2))

        # 9c. Biome Switcher Button
        bb = hud["biome_btn"]
        pygame.draw.rect(screen, (255, 255, 255), bb, border_radius=metrics.radius)
        pygame.draw.rect(screen, biome["wall"], bb, width=2, border_radius=metrics.radius)
        b_txt = self._render_text(biome["name_it"], FontRole.DISPLAY, metrics.px(15), (30, 41, 59))
        screen.blit(b_txt, (bb.centerx - b_txt.get_width() // 2, bb.centery - b_txt.get_height() // 2))

        # 9d. New Maze Button
        nb = hud["new_btn"]
        pygame.draw.rect(screen, (251, 191, 36), nb, border_radius=metrics.radius)
        pygame.draw.rect(screen, (217, 119, 6), nb, width=2, border_radius=metrics.radius)
        n_txt = self._render_text("NUOVO 🔄", FontRole.DISPLAY, metrics.px(16), (120, 53, 15))
        screen.blit(n_txt, (nb.centerx - n_txt.get_width() // 2, nb.centery - n_txt.get_height() // 2))
