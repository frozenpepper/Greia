"""Visual rendering and animation for Il Grande Albero delle Stagioni."""

from __future__ import annotations

import math
from typing import Final

import pygame

if __package__:
    from .tree_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Apple,
        Particle,
        Season,
        TreeModel,
        WeatherMode,
    )
else:
    from tree_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Apple,
        Particle,
        Season,
        TreeModel,
        WeatherMode,
    )

# Colors
COLOR_DAY_SKY_TOP: Final = (110, 190, 245)
COLOR_DAY_SKY_BOTTOM: Final = (245, 240, 215)
COLOR_NIGHT_SKY_TOP: Final = (15, 23, 48)
COLOR_NIGHT_SKY_BOTTOM: Final = (35, 45, 75)

COLOR_SUN: Final = (255, 215, 0)
COLOR_SUN_AURA: Final = (255, 235, 120, 90)
COLOR_MOON: Final = (245, 245, 230)
COLOR_MOON_AURA: Final = (230, 240, 255, 70)

# Hill colors per season
HILL_COLORS: Final = {
    Season.SPRING: ((90, 190, 85), (70, 160, 65)),
    Season.SUMMER: ((60, 175, 70), (45, 145, 55)),
    Season.AUTUMN: ((195, 140, 50), (160, 110, 40)),
    Season.WINTER: ((230, 240, 250), (195, 215, 235)),
}

# Foliage colors per season
FOLIAGE_COLORS: Final = {
    Season.SPRING: (140, 215, 120),
    Season.SUMMER: (46, 170, 65),
    Season.AUTUMN: (230, 100, 30),
    Season.WINTER: (220, 235, 245),
}


class TreeRenderer:
    """Render the scenic seasons tree, day/night cycle, weather particles, and Tito."""

    def __init__(self) -> None:
        self._reference_surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        self._sky_surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        self._stars: list[tuple[float, float, float]] = [
            (
                (i * 137.5) % REFERENCE_WIDTH,
                (i * 73.1) % (REFERENCE_HEIGHT * 0.55),
                (i % 5 + 1) * 0.6,
            )
            for i in range(70)
        ]
        # Predefined UI hitboxes (in 1024x600 reference space)
        # Weather selector: top right
        self.weather_buttons: dict[WeatherMode, pygame.Rect] = {
            WeatherMode.SUN: pygame.Rect(560, 24, 76, 76),
            WeatherMode.RAIN: pygame.Rect(650, 24, 76, 76),
            WeatherMode.WIND: pygame.Rect(740, 24, 76, 76),
            WeatherMode.SNOW: pygame.Rect(830, 24, 76, 76),
        }
        # Sun / Moon interactive disc
        self.celestial_rect = pygame.Rect(80, 40, 100, 100)
        # Tito clickable hitbox
        self.tito_rect = pygame.Rect(180, 370, 120, 160)
        # Season selector: bottom center
        btn_w, btn_h, spacing = 135, 68, 14
        start_x = (REFERENCE_WIDTH - (4 * btn_w + 3 * spacing)) // 2
        self.season_buttons: dict[Season, pygame.Rect] = {
            Season.SPRING: pygame.Rect(start_x, 514, btn_w, btn_h),
            Season.SUMMER: pygame.Rect(start_x + (btn_w + spacing), 514, btn_w, btn_h),
            Season.AUTUMN: pygame.Rect(start_x + 2 * (btn_w + spacing), 514, btn_w, btn_h),
            Season.WINTER: pygame.Rect(start_x + 3 * (btn_w + spacing), 514, btn_w, btn_h),
        }
        # Tree center
        self.tree_center_x = 560
        self.tree_center_y = 310

    def render(self, target_surface: pygame.Surface, model: TreeModel) -> None:
        ref = self._reference_surf

        # 1. Sky & Celestial bodies
        self._render_sky(ref, model)
        self._render_stars(ref, model)
        self._render_celestial(ref, model)
        self._render_clouds(ref, model)

        # 2. Hills & Scenery
        self._render_hills(ref, model)

        # 3. Big Magic Tree
        self._render_tree(ref, model)

        # 4. Seasonal special props
        if model.season == Season.SUMMER:
            self._render_basket(ref, model)
        elif model.season == Season.WINTER:
            self._render_snowman(ref, model)

        # 5. Tito Mascotte
        self._render_tito(ref, model)

        # 6. Weather & ambient particles
        self._render_particles(ref, model)

        # 7. Pre-reader UI Controls
        self._render_ui(ref, model)

        # Scale to fit actual physical window smoothly
        sw, sh = target_surface.get_size()
        if (sw, sh) == (REFERENCE_WIDTH, REFERENCE_HEIGHT):
            target_surface.blit(ref, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(ref, (sw, sh))
            target_surface.blit(scaled, (0, 0))

    def _render_sky(self, surf: pygame.Surface, model: TreeModel) -> None:
        dr = model.day_ratio
        # Interpolate sky top and bottom colors
        r_top = int(COLOR_NIGHT_SKY_TOP[0] + (COLOR_DAY_SKY_TOP[0] - COLOR_NIGHT_SKY_TOP[0]) * dr)
        g_top = int(COLOR_NIGHT_SKY_TOP[1] + (COLOR_DAY_SKY_TOP[1] - COLOR_NIGHT_SKY_TOP[1]) * dr)
        b_top = int(COLOR_NIGHT_SKY_TOP[2] + (COLOR_DAY_SKY_TOP[2] - COLOR_NIGHT_SKY_TOP[2]) * dr)

        r_bot = int(COLOR_NIGHT_SKY_BOTTOM[0] + (COLOR_DAY_SKY_BOTTOM[0] - COLOR_NIGHT_SKY_BOTTOM[0]) * dr)
        g_bot = int(COLOR_NIGHT_SKY_BOTTOM[1] + (COLOR_DAY_SKY_BOTTOM[1] - COLOR_NIGHT_SKY_BOTTOM[1]) * dr)
        b_bot = int(COLOR_NIGHT_SKY_BOTTOM[2] + (COLOR_DAY_SKY_BOTTOM[2] - COLOR_NIGHT_SKY_BOTTOM[2]) * dr)

        # Draw fast gradient in blocks of 6px
        step = 6
        for y in range(0, 420, step):
            frac = y / 420.0
            r = int(r_top + (r_bot - r_top) * frac)
            g = int(g_top + (g_bot - g_top) * frac)
            b = int(b_top + (b_bot - b_top) * frac)
            pygame.draw.rect(surf, (r, g, b), (0, y, REFERENCE_WIDTH, step))

    def _render_stars(self, surf: pygame.Surface, model: TreeModel) -> None:
        night_frac = 1.0 - model.day_ratio
        if night_frac <= 0.05:
            return
        t = model.tito_anim_timer
        for i, (sx, sy, base_r) in enumerate(self._stars):
            twinkle = 0.5 + 0.5 * math.sin(t * 3.0 + i)
            alpha_val = int(240 * night_frac * twinkle)
            if alpha_val > 10:
                color = (alpha_val, alpha_val, int(alpha_val * 0.85))
                pygame.draw.circle(surf, color, (int(sx), int(sy)), max(1, int(base_r)))

    def _render_celestial(self, surf: pygame.Surface, model: TreeModel) -> None:
        dr = model.day_ratio
        cx, cy = self.celestial_rect.center
        t = model.tito_anim_timer

        # Sun
        if dr > 0.05:
            sun_alpha = dr
            # Pulse rays
            ray_len = 16 + math.sin(t * 4.0) * 4
            num_rays = 8
            for i in range(num_rays):
                angle = (i / num_rays) * math.pi * 2 + t * 0.5
                rx1 = cx + math.cos(angle) * 44
                ry1 = cy + math.sin(angle) * 44
                rx2 = cx + math.cos(angle) * (44 + ray_len)
                ry2 = cy + math.sin(angle) * (44 + ray_len)
                ray_color = (
                    min(255, int(COLOR_SUN[0] * sun_alpha)),
                    min(255, int(COLOR_SUN[1] * sun_alpha)),
                    int(80 * sun_alpha),
                )
                pygame.draw.line(surf, ray_color, (int(rx1), int(ry1)), (int(rx2), int(ry2)), 4)

            # Outer sun disc
            pygame.draw.circle(surf, COLOR_SUN, (cx, cy), 40)
            # Happy smiling face on the sun!
            eye_color = (200, 110, 10)
            pygame.draw.circle(surf, eye_color, (cx - 12, cy - 6), 4)
            pygame.draw.circle(surf, eye_color, (cx + 12, cy - 6), 4)
            pygame.draw.arc(surf, eye_color, (cx - 16, cy - 8, 32, 28), math.pi * 1.1, math.pi * 1.9, 3)

        # Moon
        night_frac = 1.0 - dr
        if night_frac > 0.05:
            # Moon crescent
            moon_color = (
                int(COLOR_MOON[0] * night_frac),
                int(COLOR_MOON[1] * night_frac),
                int(COLOR_MOON[2] * night_frac),
            )
            pygame.draw.circle(surf, moon_color, (cx, cy), 36)
            # Shadow cutout to make crescent
            sky_col = (
                int(COLOR_NIGHT_SKY_TOP[0] * night_frac),
                int(COLOR_NIGHT_SKY_TOP[1] * night_frac),
                int(COLOR_NIGHT_SKY_TOP[2] * night_frac),
            )
            pygame.draw.circle(surf, sky_col, (cx + 16, cy - 8), 30)

    def _render_clouds(self, surf: pygame.Surface, model: TreeModel) -> None:
        cloud_color = (255, 255, 255) if model.weather != WeatherMode.RAIN else (180, 190, 205)
        for c in model.clouds:
            self._draw_cloud_shape(surf, int(c.x), int(c.y), c.scale, cloud_color)

    def _draw_cloud_shape(self, surf: pygame.Surface, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
        r1 = int(24 * scale)
        r2 = int(32 * scale)
        r3 = int(22 * scale)
        pygame.draw.circle(surf, color, (x - int(24 * scale), y), r1)
        pygame.draw.circle(surf, color, (x, y - int(10 * scale)), r2)
        pygame.draw.circle(surf, color, (x + int(24 * scale), y), r3)
        pygame.draw.rect(surf, color, (x - int(24 * scale), y - int(6 * scale), int(48 * scale), int(16 * scale)))

    def _render_hills(self, surf: pygame.Surface, model: TreeModel) -> None:
        c_front, c_back = HILL_COLORS[model.season]

        # Back hill (left to center)
        pygame.draw.ellipse(surf, c_back, (-80, 360, 680, 380))
        # Front hill (right, where tree sits)
        pygame.draw.ellipse(surf, c_front, (260, 340, 840, 420))
        # Left ground
        pygame.draw.rect(surf, c_front, (0, 460, REFERENCE_WIDTH, 140))

        # Flowers in Spring
        if model.season == Season.SPRING:
            self._render_spring_ground_flowers(surf, model)

    def _render_spring_ground_flowers(self, surf: pygame.Surface, model: TreeModel) -> None:
        flower_spots = [(120, 470), (160, 495), (280, 480), (390, 490), (780, 475), (860, 490)]
        for fx, fy in flower_spots:
            # Petals
            pygame.draw.circle(surf, (255, 182, 193), (fx - 4, fy), 4)
            pygame.draw.circle(surf, (255, 182, 193), (fx + 4, fy), 4)
            pygame.draw.circle(surf, (255, 182, 193), (fx, fy - 4), 4)
            pygame.draw.circle(surf, (255, 182, 193), (fx, fy + 4), 4)
            # Center
            pygame.draw.circle(surf, (255, 235, 59), (fx, fy), 3)

    def _render_tree(self, surf: pygame.Surface, model: TreeModel) -> None:
        tx, ty = self.tree_center_x, self.tree_center_y

        # Trunk & Branches
        trunk_col = (110, 58, 25)
        # Main trunk
        points = [
            (tx - 35, ty + 180),
            (tx - 24, ty + 20),
            (tx + 24, ty + 20),
            (tx + 40, ty + 180),
        ]
        pygame.draw.polygon(surf, trunk_col, points)
        # Left & right main boughs
        pygame.draw.line(surf, trunk_col, (tx - 10, ty + 40), (tx - 90, ty - 30), 22)
        pygame.draw.line(surf, trunk_col, (tx + 10, ty + 30), (tx + 85, ty - 35), 20)

        # Canopy
        foliage_col = FOLIAGE_COLORS[model.season]

        # Winter bare branches with snow caps
        if model.season == Season.WINTER:
            # Bare branches
            pygame.draw.line(surf, trunk_col, (tx - 90, ty - 30), (tx - 140, ty - 80), 14)
            pygame.draw.line(surf, trunk_col, (tx - 90, ty - 30), (tx - 60, ty - 95), 12)
            pygame.draw.line(surf, trunk_col, (tx + 85, ty - 35), (tx + 130, ty - 85), 14)
            pygame.draw.line(surf, trunk_col, (tx + 85, ty - 35), (tx + 60, ty - 100), 12)
            pygame.draw.line(surf, trunk_col, (tx, ty + 20), (tx, ty - 80), 16)
            # Snow mounds on branches
            snow_col = (245, 250, 255)
            pygame.draw.ellipse(surf, snow_col, (tx - 150, ty - 92, 70, 22))
            pygame.draw.ellipse(surf, snow_col, (tx - 70, ty - 106, 55, 20))
            pygame.draw.ellipse(surf, snow_col, (tx + 75, ty - 96, 68, 22))
            pygame.draw.ellipse(surf, snow_col, (tx + 35, ty - 110, 52, 18))
            pygame.draw.ellipse(surf, snow_col, (tx - 25, ty - 90, 50, 20))
            return

        # Lush foliage clusters for Spring, Summer, Autumn
        clusters = [
            (tx - 90, ty - 40, 75),
            (tx + 90, ty - 45, 72),
            (tx, ty - 85, 85),
            (tx - 45, ty - 70, 70),
            (tx + 50, ty - 65, 70),
            (tx, ty - 30, 78),
        ]
        # Darker shading behind
        shade_col = (
            max(0, foliage_col[0] - 30),
            max(0, foliage_col[1] - 30),
            max(0, foliage_col[2] - 30),
        )
        for cx, cy, rad in clusters:
            pygame.draw.circle(surf, shade_col, (cx, cy + 8), rad)
        for cx, cy, rad in clusters:
            pygame.draw.circle(surf, foliage_col, (cx, cy), rad)

        # Spring Blossoms
        if model.season == Season.SPRING:
            blossoms = [
                (tx - 110, ty - 50),
                (tx - 65, ty - 100),
                (tx + 20, ty - 110),
                (tx + 80, ty - 80),
                (tx + 120, ty - 30),
                (tx - 30, ty - 40),
                (tx + 40, ty - 30),
            ]
            for bx, by in blossoms:
                pygame.draw.circle(surf, (255, 192, 203), (bx, by), 9)
                pygame.draw.circle(surf, (255, 255, 255), (bx, by), 5)
                pygame.draw.circle(surf, (255, 225, 70), (bx, by), 2)

        # Summer Apples
        elif model.season == Season.SUMMER:
            for apple in model.apples:
                if not apple.in_basket:
                    ax = tx + int(apple.tree_rel_x)
                    ay = ty + int(apple.tree_rel_y + apple.fall_y)
                    self._draw_apple(surf, ax, ay)

    def _draw_apple(self, surf: pygame.Surface, x: int, y: int) -> None:
        # Cute bright red apple
        pygame.draw.circle(surf, (225, 40, 40), (x, y), 13)
        # Highlight
        pygame.draw.circle(surf, (255, 130, 130), (x - 4, y - 4), 4)
        # Little green leaf
        pygame.draw.ellipse(surf, (76, 175, 80), (x + 2, y - 16, 8, 5))
        # Little brown stem
        pygame.draw.line(surf, (90, 50, 20), (x, y - 12), (x + 2, y - 17), 2)

    def _render_basket(self, surf: pygame.Surface, model: TreeModel) -> None:
        bx, by = self.tree_center_x + 90, 470
        # Woven basket
        pygame.draw.polygon(
            surf,
            (185, 120, 60),
            [(bx - 26, by), (bx + 26, by), (bx + 20, by + 32), (bx - 20, by + 32)],
        )
        pygame.draw.ellipse(surf, (150, 95, 45), (bx - 26, by - 6, 52, 12))
        # Apples inside basket
        apples_in = [a for a in model.apples if a.in_basket]
        for i, _ in enumerate(apples_in):
            ox = (i % 3 - 1) * 12
            oy = -8 - (i // 3) * 8
            self._draw_apple(surf, bx + ox, by + oy)

    def _render_snowman(self, surf: pygame.Surface, model: TreeModel) -> None:
        if model.snowman_stage <= 0:
            return
        sx, sy = 760, 440

        # Stage 1: Big base snowball
        pygame.draw.circle(surf, (245, 250, 255), (sx, sy), 38)
        pygame.draw.circle(surf, (215, 230, 245), (sx, sy), 38, 2)

        # Stage 2: Middle snowball & twig arms
        if model.snowman_stage >= 2:
            pygame.draw.circle(surf, (245, 250, 255), (sx, sy - 46), 28)
            pygame.draw.circle(surf, (215, 230, 245), (sx, sy - 46), 28, 2)
            # Twig arms
            pygame.draw.line(surf, (100, 60, 30), (sx - 26, sy - 46), (sx - 52, sy - 58), 3)
            pygame.draw.line(surf, (100, 60, 30), (sx + 26, sy - 46), (sx + 52, sy - 58), 3)
            # Coal buttons
            pygame.draw.circle(surf, (40, 40, 40), (sx, sy - 52), 3)
            pygame.draw.circle(surf, (40, 40, 40), (sx, sy - 40), 3)

        # Stage 3: Head with carrot nose, eyes, smile and red scarf!
        if model.snowman_stage >= 3:
            pygame.draw.circle(surf, (245, 250, 255), (sx, sy - 84), 20)
            pygame.draw.circle(surf, (215, 230, 245), (sx, sy - 84), 20, 2)
            # Eyes
            pygame.draw.circle(surf, (40, 40, 40), (sx - 6, sy - 88), 3)
            pygame.draw.circle(surf, (40, 40, 40), (sx + 6, sy - 88), 3)
            # Carrot nose
            pygame.draw.polygon(
                surf,
                (255, 120, 20),
                [(sx, sy - 84), (sx + 14, sy - 82), (sx, sy - 80)],
            )
            # Smile
            pygame.draw.arc(surf, (40, 40, 40), (sx - 8, sy - 86, 16, 14), math.pi * 1.1, math.pi * 1.9, 2)
            # Red scarf
            pygame.draw.rect(surf, (220, 40, 40), (sx - 16, sy - 68, 32, 8), border_radius=4)
            pygame.draw.rect(surf, (220, 40, 40), (sx + 4, sy - 64, 8, 18), border_radius=3)

    def _render_tito(self, surf: pygame.Surface, model: TreeModel) -> None:
        # Tito the Fox Mascot
        tx = self.tito_rect.centerx
        ty = self.tito_rect.bottom - int(model.tito_hop_offset)
        t = model.tito_anim_timer

        fox_orange = (235, 95, 30)
        fox_white = (255, 250, 245)
        fox_nose = (40, 30, 30)

        # 1. Bushy Tail behind body (gentle wag)
        wag = math.sin(t * 4.0) * 12
        tail_points = [
            (tx - 24, ty - 45),
            (tx - 65 + wag, ty - 60),
            (tx - 75 + wag, ty - 40),
            (tx - 40, ty - 25),
        ]
        pygame.draw.polygon(surf, fox_orange, tail_points)
        # Tail white tip
        tip_points = [
            (tx - 65 + wag, ty - 60),
            (tx - 75 + wag, ty - 40),
            (tx - 60 + wag, ty - 45),
        ]
        pygame.draw.polygon(surf, fox_white, tip_points)

        # 2. Body
        pygame.draw.ellipse(surf, fox_orange, (tx - 30, ty - 75, 60, 65))
        # White chest patch
        pygame.draw.ellipse(surf, fox_white, (tx - 18, ty - 68, 36, 45))

        # 3. Feet
        pygame.draw.ellipse(surf, fox_orange, (tx - 26, ty - 16, 22, 16))
        pygame.draw.ellipse(surf, fox_orange, (tx + 4, ty - 16, 22, 16))

        # 4. Head
        hy = ty - 98
        pygame.draw.circle(surf, fox_orange, (tx, hy), 28)
        # White cheeks
        pygame.draw.circle(surf, fox_white, (tx - 15, hy + 8), 14)
        pygame.draw.circle(surf, fox_white, (tx + 15, hy + 8), 14)

        # 5. Ears
        left_ear = [(tx - 22, hy - 14), (tx - 30, hy - 46), (tx - 6, hy - 24)]
        right_ear = [(tx + 22, hy - 14), (tx + 30, hy - 46), (tx + 6, hy - 24)]
        pygame.draw.polygon(surf, fox_orange, left_ear)
        pygame.draw.polygon(surf, fox_orange, right_ear)
        # Inner ear
        pygame.draw.polygon(surf, (255, 180, 160), [(tx - 20, hy - 18), (tx - 26, hy - 40), (tx - 10, hy - 24)])
        pygame.draw.polygon(surf, (255, 180, 160), [(tx + 20, hy - 18), (tx + 26, hy - 40), (tx + 10, hy - 24)])

        # 6. Face: Eyes, Nose, Mouth
        is_sleeping = model.day_ratio < 0.2
        if is_sleeping:
            # Sleeping curved eyes
            pygame.draw.arc(surf, fox_nose, (tx - 18, hy - 4, 12, 10), math.pi * 0.1, math.pi * 0.9, 2)
            pygame.draw.arc(surf, fox_nose, (tx + 6, hy - 4, 12, 10), math.pi * 0.1, math.pi * 0.9, 2)
            # Sleepy nightcap
            cap_points = [(tx - 20, hy - 22), (tx + 20, hy - 22), (tx + 45, hy - 50)]
            pygame.draw.polygon(surf, (70, 130, 220), cap_points)
            pygame.draw.circle(surf, (255, 255, 255), (tx + 46, hy - 50), 7)
            # Zzz bubbles
            self._render_zzz(surf, tx + 35, hy - 30, t)
        else:
            # Bright open eyes
            pygame.draw.circle(surf, fox_nose, (tx - 11, hy + 2), 4)
            pygame.draw.circle(surf, fox_nose, (tx + 11, hy + 2), 4)
            # Catchlight
            pygame.draw.circle(surf, (255, 255, 255), (tx - 12, hy), 1)
            pygame.draw.circle(surf, (255, 255, 255), (tx + 10, hy), 1)

        # Black button nose
        pygame.draw.polygon(surf, fox_nose, [(tx - 5, hy + 12), (tx + 5, hy + 12), (tx, hy + 16)])

        # 7. Rain: Yellow umbrella in hand
        if model.weather == WeatherMode.RAIN:
            ux, uy = tx + 32, hy - 25
            pygame.draw.arc(surf, (255, 215, 0), (ux - 35, uy - 35, 70, 50), 0, math.pi, 24)
            pygame.draw.line(surf, (160, 130, 40), (ux, uy - 10), (ux - 12, ty - 45), 4)

    def _render_zzz(self, surf: pygame.Surface, x: int, y: int, t: float) -> None:
        # Gentle floating Zzz letters
        for i in range(3):
            zy = y - i * 16 - int((t * 20.0 + i * 8) % 30)
            zx = x + int(math.sin(t * 2.0 + i) * 8) + i * 10
            alpha_col = (200, 220, 255)
            # Draw simple Z shape with lines
            sz = 6 + i * 3
            pygame.draw.line(surf, alpha_col, (zx, zy), (zx + sz, zy), 2)
            pygame.draw.line(surf, alpha_col, (zx + sz, zy), (zx, zy + sz), 2)
            pygame.draw.line(surf, alpha_col, (zx, zy + sz), (zx + sz, zy + sz), 2)

    def _render_particles(self, surf: pygame.Surface, model: TreeModel) -> None:
        for p in model.particles:
            if p.kind == "rain":
                pygame.draw.line(surf, p.color, (int(p.x), int(p.y)), (int(p.x + p.vx * 0.04), int(p.y + p.vy * 0.04)), 2)
            elif p.kind == "snow":
                pygame.draw.circle(surf, p.color, (int(p.x), int(p.y)), int(p.size))
            elif p.kind == "leaf":
                # Rotated oval leaf
                leaf_rect = pygame.Rect(int(p.x - p.size), int(p.y - p.size * 0.6), int(p.size * 2), int(p.size * 1.2))
                pygame.draw.ellipse(surf, p.color, leaf_rect)
            elif p.kind == "sparkle":
                sz = int(p.size * p.life)
                if sz > 1:
                    pygame.draw.circle(surf, p.color, (int(p.x), int(p.y)), sz)
            elif p.kind == "butterfly":
                self._draw_butterfly(surf, int(p.x), int(p.y), p.color, model.tito_anim_timer)

    def _draw_butterfly(self, surf: pygame.Surface, x: int, y: int, color: tuple[int, int, int], t: float) -> None:
        wing_span = int(12 * abs(math.sin(t * 8.0))) + 2
        # Left wing
        pygame.draw.ellipse(surf, color, (x - wing_span - 2, y - 8, wing_span, 16))
        # Right wing
        pygame.draw.ellipse(surf, color, (x + 2, y - 8, wing_span, 16))
        # Body
        pygame.draw.rect(surf, (40, 30, 20), (x - 1, y - 6, 3, 12))

    def _render_ui(self, surf: pygame.Surface, model: TreeModel) -> None:
        # 1. Celestial button hint ring
        cx, cy = self.celestial_rect.center
        pulse = math.sin(model.tito_anim_timer * 3.0) * 3
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), int(52 + pulse), 3)

        # 2. Weather Buttons (Top Right)
        weather_icons = {
            WeatherMode.SUN: "☀️",
            WeatherMode.RAIN: "🌧️",
            WeatherMode.WIND: "💨",
            WeatherMode.SNOW: "❄️",
        }
        for mode, rect in self.weather_buttons.items():
            is_active = model.weather == mode
            bg_col = (255, 245, 220) if is_active else (255, 255, 255)
            border_col = (255, 160, 0) if is_active else (200, 210, 225)
            pygame.draw.rect(surf, bg_col, rect, border_radius=20)
            pygame.draw.rect(surf, border_col, rect, 4 if is_active else 2, border_radius=20)
            self._draw_weather_icon(surf, mode, rect.centerx, rect.centery, is_active)

        # 3. Season Buttons (Bottom Center)
        season_labels = {
            Season.SPRING: "PRIMAVERA",
            Season.SUMMER: "ESTATE",
            Season.AUTUMN: "AUTUNNO",
            Season.WINTER: "INVERNO",
        }
        season_accent = {
            Season.SPRING: (255, 105, 180),
            Season.SUMMER: (76, 175, 80),
            Season.AUTUMN: (245, 124, 0),
            Season.WINTER: (33, 150, 243),
        }
        font = pygame.font.Font(None, 24)
        for season, rect in self.season_buttons.items():
            is_active = model.season == season
            accent = season_accent[season]
            bg_col = (255, 255, 255) if is_active else (240, 244, 248)
            border_col = accent if is_active else (180, 195, 210)
            pygame.draw.rect(surf, bg_col, rect, border_radius=18)
            pygame.draw.rect(surf, border_col, rect, 4 if is_active else 2, border_radius=18)

            # Seasonal symbol & title
            self._draw_season_symbol(surf, season, rect.centerx, rect.centery - 12)
            lbl = font.render(season_labels[season], True, accent if is_active else (80, 95, 110))
            surf.blit(lbl, lbl.get_rect(center=(rect.centerx, rect.centery + 18)))

    def _draw_weather_icon(self, surf: pygame.Surface, mode: WeatherMode, cx: int, cy: int, active: bool) -> None:
        if mode == WeatherMode.SUN:
            pygame.draw.circle(surf, (255, 180, 0), (cx, cy), 16)
            for i in range(8):
                ang = i * (math.pi / 4)
                x1 = cx + math.cos(ang) * 19
                y1 = cy + math.sin(ang) * 19
                x2 = cx + math.cos(ang) * 25
                y2 = cy + math.sin(ang) * 25
                pygame.draw.line(surf, (255, 180, 0), (int(x1), int(y1)), (int(x2), int(y2)), 3)
        elif mode == WeatherMode.RAIN:
            # Cloud + 3 raindrops
            self._draw_cloud_shape(surf, cx, cy - 4, 0.6, (140, 175, 210))
            for ox in (-10, 0, 10):
                pygame.draw.line(surf, (65, 140, 240), (cx + ox, cy + 10), (cx + ox - 3, cy + 18), 3)
        elif mode == WeatherMode.WIND:
            # Swirling wind lines
            col = (70, 180, 210)
            pygame.draw.arc(surf, col, (cx - 18, cy - 14, 32, 16), 0, math.pi * 1.5, 3)
            pygame.draw.arc(surf, col, (cx - 14, cy - 2, 28, 14), math.pi * 0.5, math.pi * 2.0, 3)
        elif mode == WeatherMode.SNOW:
            # Crisp snowflake
            col = (90, 170, 235)
            for i in range(3):
                ang = i * (math.pi / 3)
                dx = math.cos(ang) * 18
                dy = math.sin(ang) * 18
                pygame.draw.line(surf, col, (int(cx - dx), int(cy - dy)), (int(cx + dx), int(cy + dy)), 3)

    def _draw_season_symbol(self, surf: pygame.Surface, season: Season, cx: int, cy: int) -> None:
        if season == Season.SPRING:
            # Pink flower
            for i in range(5):
                ang = i * (math.pi * 2 / 5)
                px = cx + math.cos(ang) * 9
                py = cy + math.sin(ang) * 9
                pygame.draw.circle(surf, (255, 130, 180), (int(px), int(py)), 6)
            pygame.draw.circle(surf, (255, 230, 80), (cx, cy), 5)
        elif season == Season.SUMMER:
            # Shiny red apple
            self._draw_apple(surf, cx, cy)
        elif season == Season.AUTUMN:
            # Orange maple/oak leaf
            pygame.draw.ellipse(surf, (245, 110, 20), (cx - 10, cy - 12, 20, 24))
            pygame.draw.line(surf, (150, 60, 10), (cx, cy - 12), (cx, cy + 14), 2)
        elif season == Season.WINTER:
            # Little cute snowman
            pygame.draw.circle(surf, (200, 225, 245), (cx, cy + 6), 11)
            pygame.draw.circle(surf, (200, 225, 245), (cx, cy - 7), 8)
            pygame.draw.circle(surf, (40, 40, 40), (cx - 3, cy - 8), 2)
            pygame.draw.circle(surf, (40, 40, 40), (cx + 3, cy - 8), 2)
            pygame.draw.polygon(surf, (255, 130, 20), [(cx, cy - 6), (cx + 6, cy - 5), (cx, cy - 4)])
