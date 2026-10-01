"""Storybook vector art renderer for Corsa delle Bacche.

Renders charming hedges, colorful berries, animated Momo, critters, and HUD.
Strictly respects the Greia system chrome protected area (0..160, 0..50).
"""

from __future__ import annotations

import math
import random
from typing import Final

import pygame

try:
    from corsa_content import (
        CELL_SIZE,
        COLOR_BAFFO_BELLY,
        COLOR_BAFFO_BROWN,
        COLOR_BAFFO_NOSE,
        COLOR_BEE_STRIPE,
        COLOR_BEE_WING,
        COLOR_BEE_YELLOW,
        COLOR_BG_GARDEN,
        COLOR_BLUEBERRY,
        COLOR_GOLDEN_BERRY,
        COLOR_HEART,
        COLOR_HEDGE,
        COLOR_HEDGE_FLOWER,
        COLOR_HEDGE_LIGHT,
        COLOR_HEDGE_SHADOW,
        COLOR_HUD_TEXT,
        COLOR_MOMO_BELLY,
        COLOR_MOMO_DARK,
        COLOR_MOMO_INNER_EAR,
        COLOR_MOMO_ORANGE,
        COLOR_MOMO_TAIL,
        COLOR_PATH,
        COLOR_PATH_BORDER,
        COLOR_RAINBOW,
        COLOR_STAR_GOLD,
        COLOR_STRAWBERRY,
        COLOR_STRAWBERRY_LEAF,
        COLOR_STRAWBERRY_SEED,
        GRID_COLS,
        GRID_ORIGIN_X,
        GRID_ORIGIN_Y,
        GRID_ROWS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        BerryType,
        CritterKind,
    )
    from corsa_model import CorsaModel, CritterState, MomoPlayer, grid_to_world
except ImportError:
    from .corsa_content import (
        CELL_SIZE,
        COLOR_BAFFO_BELLY,
        COLOR_BAFFO_BROWN,
        COLOR_BAFFO_NOSE,
        COLOR_BEE_STRIPE,
        COLOR_BEE_WING,
        COLOR_BEE_YELLOW,
        COLOR_BG_GARDEN,
        COLOR_BLUEBERRY,
        COLOR_GOLDEN_BERRY,
        COLOR_HEART,
        COLOR_HEDGE,
        COLOR_HEDGE_FLOWER,
        COLOR_HEDGE_LIGHT,
        COLOR_HEDGE_SHADOW,
        COLOR_HUD_TEXT,
        COLOR_MOMO_BELLY,
        COLOR_MOMO_DARK,
        COLOR_MOMO_INNER_EAR,
        COLOR_MOMO_ORANGE,
        COLOR_MOMO_TAIL,
        COLOR_PATH,
        COLOR_PATH_BORDER,
        COLOR_RAINBOW,
        COLOR_STAR_GOLD,
        COLOR_STRAWBERRY,
        COLOR_STRAWBERRY_LEAF,
        COLOR_STRAWBERRY_SEED,
        GRID_COLS,
        GRID_ORIGIN_X,
        GRID_ORIGIN_Y,
        GRID_ROWS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        BerryType,
        CritterKind,
    )
    from .corsa_model import CorsaModel, CritterState, MomoPlayer, grid_to_world


class CorsaRenderer:
    """Renders the game state onto the reference 1024x600 surface."""

    def __init__(self) -> None:
        pygame.font.init()
        # Clean typography for HUD
        self.hud_font = pygame.font.Font(None, 28)
        self.big_font = pygame.font.Font(None, 44)
        self.banner_font = pygame.font.Font(None, 52)

        # Particle effects for sparkles and star trails
        self.particles: list[dict[str, float | tuple[int, int, int]]] = []
        self._anim_timer: float = 0.0

    def render(self, surface: pygame.Surface, model: CorsaModel, dt: float) -> None:
        """Render one complete frame onto surface."""
        self._anim_timer = (self._anim_timer + dt) % 1000.0
        self._update_particles(dt)

        # 1. Background Garden Lawn
        surface.fill(COLOR_BG_GARDEN)

        # 2. Paths (walkable garden stone/sand)
        self._draw_paths(surface, model)

        # 3. Hedges (leafy labyrinth walls with depth and flowers)
        self._draw_hedges(surface, model)

        # 4. Berries and Collectibles
        self._draw_berries(surface, model)

        # 5. Moving Bonus Fruit (if active)
        if model.bonus_fruit is not None and model.bonus_fruit.active:
            self._draw_bonus_fruit(surface, model.bonus_fruit)

        # 6. Garden Critters (Baffo and Bumblebee)
        for critter in model.critters:
            self._draw_critter(surface, critter, model.is_rainbow_active)

        # 7. Momo the Squirrel
        self._draw_momo(surface, model.player, model.is_rainbow_active)

        # 8. Particle System (sparkles, rainbow trail)
        self._draw_particles(surface)

        # 9. HUD (Hearts, Berries, Score, Level, Rainbow Aura)
        # Safely located at x >= 180 to never overlap (0..160, 0..50)
        self._draw_hud(surface, model)

        # 10. Level Clear Banner / Restorative Apple Banner
        if model.level_complete:
            self._draw_completion_banner(surface, model)
        elif model.player.is_munching_apple:
            self._draw_apple_banner(surface)

    def _draw_paths(self, surface: pygame.Surface, model: CorsaModel) -> None:
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if not model.is_wall(c, r):
                    x = GRID_ORIGIN_X + c * CELL_SIZE
                    y = GRID_ORIGIN_Y + r * CELL_SIZE
                    # Outer soft border
                    pygame.draw.rect(
                        surface,
                        COLOR_PATH_BORDER,
                        (x - 1, y - 1, CELL_SIZE + 2, CELL_SIZE + 2),
                    )
                    # Main path fill
                    pygame.draw.rect(
                        surface,
                        COLOR_PATH,
                        (x, y, CELL_SIZE, CELL_SIZE),
                    )

    def _draw_hedges(self, surface: pygame.Surface, model: CorsaModel) -> None:
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if model.is_wall(c, r):
                    x = GRID_ORIGIN_X + c * CELL_SIZE
                    y = GRID_ORIGIN_Y + r * CELL_SIZE
                    # Shadow at bottom of hedge
                    pygame.draw.rect(
                        surface,
                        COLOR_HEDGE_SHADOW,
                        (x + 2, y + 4, CELL_SIZE - 4, CELL_SIZE - 4),
                        border_radius=8,
                    )
                    # Main hedge block
                    pygame.draw.rect(
                        surface,
                        COLOR_HEDGE,
                        (x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 6),
                        border_radius=8,
                    )
                    # Sunlight leaf highlight on top edge
                    pygame.draw.rect(
                        surface,
                        COLOR_HEDGE_LIGHT,
                        (x + 4, y + 3, CELL_SIZE - 8, 8),
                        border_radius=4,
                    )
                    # Occasional cute hedge blossom
                    if (c * 7 + r * 13) % 9 == 0:
                        fl_x = x + CELL_SIZE // 2
                        fl_y = y + CELL_SIZE // 2 - 2
                        pygame.draw.circle(surface, COLOR_HEDGE_FLOWER, (fl_x, fl_y), 4)
                        pygame.draw.circle(surface, (255, 180, 70), (fl_x, fl_y), 2)

    def _draw_berries(self, surface: pygame.Surface, model: CorsaModel) -> None:
        t = self._anim_timer
        for b in model.berries:
            if b.collected:
                continue

            bx, by = b.x, b.y

            if b.berry_type == BerryType.BLUEBERRY:
                # Plump blue berry with white gleam
                pygame.draw.circle(surface, (45, 65, 160), (int(bx), int(by) + 2), 6)
                pygame.draw.circle(surface, COLOR_BLUEBERRY, (int(bx), int(by)), 6)
                pygame.draw.circle(surface, (255, 255, 255), (int(bx) - 2, int(by) - 2), 2)

            elif b.berry_type == BerryType.STRAWBERRY:
                # Little heart-shaped red strawberry
                pts = [
                    (bx, by + 7),
                    (bx - 6, by),
                    (bx - 5, by - 5),
                    (bx, by - 4),
                    (bx + 5, by - 5),
                    (bx + 6, by),
                ]
                pygame.draw.polygon(surface, COLOR_STRAWBERRY, [(int(px), int(py)) for px, py in pts])
                # Tiny green crown
                pygame.draw.circle(surface, COLOR_STRAWBERRY_LEAF, (int(bx), int(by) - 5), 2)
                # Seed dot
                pygame.draw.circle(surface, COLOR_STRAWBERRY_SEED, (int(bx), int(by) + 1), 1)

            elif b.berry_type == BerryType.GOLDEN_BERRY:
                # Sparkling golden berry with pulsing halo
                pulse = 1.0 + 0.15 * math.sin(t * 5.0 + b.col)
                rad = int(7 * pulse)
                pygame.draw.circle(surface, (255, 240, 150), (int(bx), int(by)), rad + 3, width=1)
                pygame.draw.circle(surface, COLOR_GOLDEN_BERRY, (int(bx), int(by)), rad)
                pygame.draw.circle(surface, (255, 255, 255), (int(bx) - 2, int(by) - 2), 2)

            elif b.berry_type == BerryType.RAINBOW_STAR:
                # Glowing rainbow star berry
                col_idx = int(t * 8.0) % len(COLOR_RAINBOW)
                r_col = COLOR_RAINBOW[col_idx]
                halo_rad = int(12 + 3 * math.sin(t * 6.0))
                # Soft glowing aura
                halo_surf = pygame.Surface((halo_rad * 2, halo_rad * 2), pygame.SRCALPHA)
                pygame.draw.circle(halo_surf, (*r_col, 90), (halo_rad, halo_rad), halo_rad)
                surface.blit(halo_surf, (int(bx) - halo_rad, int(by) - halo_rad))

                # Multi-point star
                star_pts = []
                for i in range(10):
                    angle = (i * math.pi / 5.0) - (math.pi / 2.0) + t * 2.0
                    dist = 9 if i % 2 == 0 else 4.5
                    star_pts.append((bx + math.cos(angle) * dist, by + math.sin(angle) * dist))
                pygame.draw.polygon(surface, r_col, [(int(px), int(py)) for px, py in star_pts])
                pygame.draw.circle(surface, (255, 255, 255), (int(bx), int(by)), 3)

    def _draw_bonus_fruit(self, surface: pygame.Surface, fruit: object) -> None:
        fx, fy = getattr(fruit, "x", 0.0), getattr(fruit, "y", 0.0)
        bounce = math.sin(getattr(fruit, "bounce_timer", 0.0)) * 4.0
        by = fy - bounce
        # Pear / golden fruit
        pygame.draw.circle(surface, (245, 185, 40), (int(fx), int(by) + 4), 10)
        pygame.draw.circle(surface, (255, 215, 60), (int(fx), int(by) - 2), 7)
        # Leaf
        pygame.draw.circle(surface, (65, 185, 65), (int(fx) + 4, int(by) - 9), 3)

    def _draw_momo(self, surface: pygame.Surface, momo: MomoPlayer, rainbow_active: bool) -> None:
        mx, my = momo.x, momo.y

        # Rainbow Aura if star power is active
        if rainbow_active:
            r_idx = int(self._anim_timer * 12.0) % len(COLOR_RAINBOW)
            aura_col = COLOR_RAINBOW[r_idx]
            aura = pygame.Surface((56, 56), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*aura_col, 110), (28, 28), 26)
            surface.blit(aura, (int(mx) - 28, int(my) - 28))

            # Spawn rainbow trail particles
            if random.random() < 0.35:
                self.particles.append({
                    "x": mx + random.uniform(-10, 10),
                    "y": my + random.uniform(-10, 10),
                    "vx": random.uniform(-20, 20),
                    "vy": random.uniform(-20, 20),
                    "life": 0.45,
                    "color": random.choice(COLOR_RAINBOW),
                    "size": random.uniform(3, 6),
                })

        # Wobble offset if in recovery
        wobble_dx = math.sin(momo.wobble_timer * 25.0) * 5.0 if momo.is_wobbling else 0.0
        mx += wobble_dx

        flip = not momo.facing_right
        facing_dir = -1 if flip else 1

        # 1. Fluffy Squirrel Tail (behind body)
        tail_bob = math.sin(self._anim_timer * 8.0) * 4.0
        tail_tip_x = mx - (18 * facing_dir)
        tail_tip_y = my - 14 + tail_bob
        pygame.draw.circle(surface, COLOR_MOMO_TAIL, (int(tail_tip_x), int(tail_tip_y)), 10)
        pygame.draw.circle(surface, (255, 220, 185), (int(tail_tip_x), int(tail_tip_y) - 2), 6)

        # 2. Main Body
        pygame.draw.ellipse(surface, COLOR_MOMO_ORANGE, (int(mx) - 12, int(my) - 10, 24, 22))
        # Cream chest/belly
        belly_x = int(mx) + (1 * facing_dir) - 5
        pygame.draw.ellipse(surface, COLOR_MOMO_BELLY, (belly_x, int(my) - 6, 12, 16))

        # 3. Head
        head_x = int(mx) + (4 * facing_dir)
        head_y = int(my) - 6
        pygame.draw.circle(surface, COLOR_MOMO_ORANGE, (head_x, head_y), 12)

        # 4. Cute Perky Ears
        ear_x = head_x - (4 * facing_dir)
        pygame.draw.circle(surface, COLOR_MOMO_ORANGE, (ear_x, head_y - 12), 5)
        pygame.draw.circle(surface, COLOR_MOMO_INNER_EAR, (ear_x, head_y - 12), 3)

        # 5. Eyes with Sparkle
        eye_x = head_x + (4 * facing_dir)
        eye_y = head_y - 2
        pygame.draw.circle(surface, COLOR_MOMO_DARK, (eye_x, eye_y), 3)
        pygame.draw.circle(surface, (255, 255, 255), (eye_x - (1 * facing_dir), eye_y - 1), 1)

        # 6. Pink Nose & Rosy Cheek
        nose_x = head_x + (8 * facing_dir)
        pygame.draw.circle(surface, (240, 115, 135), (nose_x, head_y + 1), 2)
        pygame.draw.circle(surface, (255, 175, 165), (eye_x - (2 * facing_dir), eye_y + 4), 3)

        # 7. Restorative Apple in paws if munching
        if momo.is_munching_apple:
            app_x = head_x + (6 * facing_dir)
            app_y = head_y + 7
            pygame.draw.circle(surface, (225, 45, 45), (app_x, app_y), 5)
            pygame.draw.circle(surface, (80, 180, 80), (app_x, app_y - 4), 2)

    def _draw_critter(self, surface: pygame.Surface, cr: CritterState, rainbow_active: bool) -> None:
        cx, cy = cr.x, cr.y
        flip = not cr.facing_right
        f_dir = -1 if flip else 1

        if cr.kind == CritterKind.BAFFO:
            # Baffo the Grumpy Sleepy Hedgehog
            # Rounded prickly body
            pygame.draw.circle(surface, (100, 65, 40), (int(cx), int(cy) + 2), 14)
            pygame.draw.circle(surface, COLOR_BAFFO_BROWN, (int(cx), int(cy)), 13)

            # Belly / Snout
            snout_x = int(cx) + (7 * f_dir)
            pygame.draw.circle(surface, COLOR_BAFFO_BELLY, (snout_x, int(cy) + 2), 8)
            # Nose
            pygame.draw.circle(surface, COLOR_BAFFO_NOSE, (snout_x + (4 * f_dir), int(cy) + 1), 3)

            # Sleepy Eyes
            eye_x = snout_x - (2 * f_dir)
            eye_y = int(cy)
            if cr.is_napping:
                # Closed sleeping slit
                pygame.draw.line(surface, (40, 30, 20), (eye_x - 3, eye_y), (eye_x + 3, eye_y), 2)
                # Floating "Zzz"
                z_offset = (self._anim_timer * 15.0) % 20.0
                z_surf = self.hud_font.render("z", True, (130, 150, 220))
                surface.blit(z_surf, (int(cx) - 4, int(cy) - 22 - int(z_offset)))
            else:
                pygame.draw.circle(surface, (40, 30, 20), (eye_x, eye_y), 2)

        elif cr.kind == CritterKind.BEE:
            # Buzzing Bumblebee
            wing_bob = math.sin(cr.wing_phase) * 5.0
            # Translucent wings
            wing_surf = pygame.Surface((20, 14), pygame.SRCALPHA)
            pygame.draw.ellipse(wing_surf, COLOR_BEE_WING, (0, 0, 20, 14))
            surface.blit(wing_surf, (int(cx) - 10, int(cy) - 16 + int(wing_bob)))

            # Striped oval body
            pygame.draw.ellipse(surface, COLOR_BEE_YELLOW, (int(cx) - 11, int(cy) - 9, 22, 18))
            # Black stripes
            pygame.draw.rect(surface, COLOR_BEE_STRIPE, (int(cx) - 3, int(cy) - 8, 4, 16))
            pygame.draw.rect(surface, COLOR_BEE_STRIPE, (int(cx) + 3, int(cy) - 8, 4, 16))

            # Bee eyes
            pygame.draw.circle(surface, (20, 20, 20), (int(cx) + (7 * f_dir), int(cy) - 2), 3)
            pygame.draw.circle(surface, (255, 255, 255), (int(cx) + (6 * f_dir), int(cy) - 3), 1)

        # Dizzy Spirals if frozen by Rainbow Star Berry
        if cr.is_dizzy or rainbow_active:
            spiral_angle = self._anim_timer * 10.0
            sp_x = cx + math.cos(spiral_angle) * 7.0
            sp_y = cy - 20 + math.sin(spiral_angle) * 4.0
            pygame.draw.circle(surface, (255, 215, 40), (int(sp_x), int(sp_y)), 3)
            sp_x2 = cx + math.cos(spiral_angle + math.pi) * 7.0
            sp_y2 = cy - 20 + math.sin(spiral_angle + math.pi) * 4.0
            pygame.draw.circle(surface, (80, 210, 255), (int(sp_x2), int(sp_y2)), 3)

    def _draw_particles(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            col = p["color"]
            x = int(p["x"])
            y = int(p["y"])
            rad = max(1, int(p["size"]))
            pygame.draw.circle(surface, col, (x, y), rad)

    def _update_particles(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0.0:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                alive.append(p)
        self.particles = alive

    def _draw_hud(self, surface: pygame.Surface, model: CorsaModel) -> None:
        """Draw HUD safely starting at x=180, never touching (0..160, 0..50)."""
        hud_bar_y = 16

        # 1. Hearts (3 cute red strawberries / hearts)
        for i in range(model.max_hearts):
            hx = 185 + i * 36
            hy = hud_bar_y + 16
            if i < model.hearts:
                # Active red heart
                pygame.draw.circle(surface, COLOR_HEART, (hx - 6, hy - 4), 7)
                pygame.draw.circle(surface, COLOR_HEART, (hx + 6, hy - 4), 7)
                pts = [(hx - 12, hy - 2), (hx + 12, hy - 2), (hx, hy + 12)]
                pygame.draw.polygon(surface, COLOR_HEART, pts)
                pygame.draw.circle(surface, (255, 170, 185), (hx - 6, hy - 6), 2)
            else:
                # Empty heart outline
                pygame.draw.circle(surface, (190, 195, 185), (hx - 6, hy - 4), 7, width=2)
                pygame.draw.circle(surface, (190, 195, 185), (hx + 6, hy - 4), 7, width=2)

        # 2. Berry Counter
        bx = 330
        by = hud_bar_y + 16
        # Strawberry mini icon
        pygame.draw.circle(surface, COLOR_STRAWBERRY, (bx, by), 9)
        pygame.draw.circle(surface, COLOR_STRAWBERRY_LEAF, (bx, by - 8), 3)
        berry_text = f"{model.berries_collected} / {model.total_berries}"
        berry_surf = self.hud_font.render(berry_text, True, COLOR_HUD_TEXT)
        surface.blit(berry_surf, (bx + 16, hud_bar_y + 6))

        # 3. Score Stars
        sx = 490
        star_surf = self.hud_font.render(f"★ {model.score}", True, (215, 155, 20))
        surface.blit(star_surf, (sx, hud_bar_y + 6))

        # 4. Level Indicator
        lx = 640
        lvl_surf = self.hud_font.render(f"🌱 L{model.level_config.level_number}", True, (60, 110, 50))
        surface.blit(lvl_surf, (lx, hud_bar_y + 6))

        # 5. Rainbow Aura Active Meter
        if model.is_rainbow_active:
            rx = 770
            fraction = model.rainbow_timer / model.level_config.powerup_duration
            bar_w = int(140 * fraction)
            # Background slot
            pygame.draw.rect(surface, (210, 220, 210), (rx, hud_bar_y + 8, 140, 18), border_radius=9)
            # Rainbow fill
            r_idx = int(self._anim_timer * 10.0) % len(COLOR_RAINBOW)
            pygame.draw.rect(surface, COLOR_RAINBOW[r_idx], (rx, hud_bar_y + 8, bar_w, 18), border_radius=9)
            star_label = self.hud_font.render("✨", True, (255, 255, 255))
            surface.blit(star_label, (rx + bar_w - 14, hud_bar_y + 6))

    def _draw_completion_banner(self, surface: pygame.Surface, model: CorsaModel) -> None:
        """Cheerful congratulatory banner when all berries in level are harvested."""
        banner_w, banner_h = 560, 100
        bx = (REFERENCE_WIDTH - banner_w) // 2
        by = (REFERENCE_HEIGHT - banner_h) // 2

        # Soft shadow
        pygame.draw.rect(surface, (30, 60, 30, 80), (bx + 6, by + 6, banner_w, banner_h), border_radius=24)
        # Main rounded card
        pygame.draw.rect(surface, (255, 252, 240), (bx, by, banner_w, banner_h), border_radius=24)
        pygame.draw.rect(surface, COLOR_GOLDEN_BERRY, (bx, by, banner_w, banner_h), width=4, border_radius=24)

        text_surf = self.banner_font.render("🍓 Livello Completato! 🎉", True, (50, 120, 50))
        tx = bx + (banner_w - text_surf.get_width()) // 2
        ty = by + 28
        surface.blit(text_surf, (tx, ty))

    def _draw_apple_banner(self, surface: pygame.Surface) -> None:
        """Gentle cheer when Momo eats an apple after 0 hearts."""
        banner_w, banner_h = 520, 80
        bx = (REFERENCE_WIDTH - banner_w) // 2
        by = (REFERENCE_HEIGHT - banner_h) // 2

        pygame.draw.rect(surface, (255, 252, 240), (bx, by, banner_w, banner_h), border_radius=20)
        pygame.draw.rect(surface, (220, 70, 70), (bx, by, banner_w, banner_h), width=3, border_radius=20)

        text_surf = self.big_font.render("🍎 Momo mangia una mela e riparte!", True, (180, 50, 50))
        tx = bx + (banner_w - text_surf.get_width()) // 2
        ty = by + 22
        surface.blit(text_surf, (tx, ty))
