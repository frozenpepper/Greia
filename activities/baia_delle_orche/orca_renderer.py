from __future__ import annotations

import math
from typing import Sequence

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

try:
    from orca_model import (
        FoodEntity,
        FoodType,
        OrcaEntity,
        OrcaPod,
        OrcaState,
        ParticleEntity,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ToyEntity,
        WATER_SURFACE_Y,
    )
except ImportError:
    from .orca_model import (
        FoodEntity,
        FoodType,
        OrcaEntity,
        OrcaPod,
        OrcaState,
        ParticleEntity,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ToyEntity,
        WATER_SURFACE_Y,
    )


def _draw_vector_heart(surf: pygame.Surface, cx: int, cy: int, size: int, col: tuple[int, int, int]) -> None:
    """Draw a smooth cute heart shape at (cx, cy)."""
    r = max(2, size // 4)
    pygame.draw.circle(surf, col, (cx - r, cy - r // 2), r)
    pygame.draw.circle(surf, col, (cx + r, cy - r // 2), r)
    pts = [
        (cx - 2 * r, cy - r // 4),
        (cx + 2 * r, cy - r // 4),
        (cx, cy + size // 2),
    ]
    pygame.draw.polygon(surf, col, pts)


def _draw_vector_fish(surf: pygame.Surface, cx: int, cy: int, size: int, col: tuple[int, int, int]) -> None:
    """Draw a cute swimming fish icon at (cx, cy)."""
    w = size
    h = max(4, size // 2)
    pygame.draw.ellipse(surf, col, (cx - w // 2, cy - h // 2, w, h))
    tail_pts = [(cx + w // 3, cy), (cx + w // 2 + 4, cy - h // 2), (cx + w // 2 + 4, cy + h // 2)]
    pygame.draw.polygon(surf, col, tail_pts)
    pygame.draw.circle(surf, (255, 255, 255), (cx - w // 4, cy - 2), max(2, size // 8))
    pygame.draw.circle(surf, (15, 23, 42), (cx - w // 4 - 1, cy - 2), max(1, size // 14))


def _draw_vector_ball(surf: pygame.Surface, cx: int, cy: int, r: int, rotation: float = 0.0) -> None:
    """Draw a rich 3D-shaded 4-color beach ball at (cx, cy)."""
    r = max(6, r)
    pygame.draw.circle(surf, (244, 63, 94), (cx, cy), r)
    pygame.draw.circle(surf, (250, 204, 21), (cx, cy), r, draw_top_right=True)
    pygame.draw.circle(surf, (56, 189, 248), (cx, cy), r, draw_bottom_left=True)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), r, draw_bottom_right=True)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), r, width=2)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), max(3, r // 3))
    pygame.draw.circle(surf, (255, 255, 255), (cx - r // 3, cy - r // 3), max(2, r // 4))


def _draw_vector_music(surf: pygame.Surface, cx: int, cy: int, size: int, col: tuple[int, int, int]) -> None:
    """Draw twin musical eighth notes at (cx, cy)."""
    nr = max(3, size // 6)
    pygame.draw.ellipse(surf, col, (cx - size // 3, cy + size // 4, nr * 2, nr * 2 - 2))
    pygame.draw.line(surf, col, (cx - size // 3 + nr * 2 - 1, cy + size // 4 + nr), (cx - size // 3 + nr * 2 - 1, cy - size // 3), 2)
    pygame.draw.ellipse(surf, col, (cx + size // 6, cy + size // 6, nr * 2, nr * 2 - 2))
    pygame.draw.line(surf, col, (cx + size // 6 + nr * 2 - 1, cy + size // 6 + nr), (cx + size // 6 + nr * 2 - 1, cy - size // 2), 2)
    pygame.draw.line(surf, col, (cx - size // 3 + nr * 2 - 1, cy - size // 3), (cx + size // 6 + nr * 2 - 1, cy - size // 2), 3)


def _draw_vector_moon(surf: pygame.Surface, cx: int, cy: int, r: int, col: tuple[int, int, int]) -> None:
    """Draw a glowing crescent moon and twinkling star at (cx, cy)."""
    pygame.draw.circle(surf, col, (cx, cy), r)
    pygame.draw.circle(surf, (15, 23, 42), (cx + r // 2, cy - r // 3), int(r * 0.85))
    sx, sy = cx + r // 2 + 4, cy + r // 3
    pygame.draw.polygon(surf, (255, 255, 255), [(sx, sy - 4), (sx + 1, sy - 1), (sx + 4, sy), (sx + 1, sy + 1), (sx, sy + 4), (sx - 1, sy + 1), (sx - 4, sy), (sx - 1, sy - 1)])


from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets" / "runtime"
_IMAGE_CACHE: dict[str, pygame.Surface | None] = {}
_SCALE_CACHE: dict[tuple[str, int, int, bool, int], pygame.Surface | None] = {}


def _load_asset(filename: str) -> pygame.Surface | None:
    if filename not in _IMAGE_CACHE:
        p = ASSETS_DIR / filename
        if p.exists():
            try:
                if pygame.display.get_surface() is not None:
                    _IMAGE_CACHE[filename] = pygame.image.load(str(p)).convert_alpha()
                else:
                    _IMAGE_CACHE[filename] = pygame.image.load(str(p))
            except Exception:
                try:
                    _IMAGE_CACHE[filename] = pygame.image.load(str(p))
                except Exception:
                    _IMAGE_CACHE[filename] = None
        else:
            _IMAGE_CACHE[filename] = None
    return _IMAGE_CACHE[filename]


def _get_scaled_asset(filename: str, width: int, height: int, facing_right: bool = True, angle_deg: int = 0) -> pygame.Surface | None:
    # Quantize angle to nearest 2 degrees for cache efficiency
    quant_angle = int(round(angle_deg / 2.0) * 2) % 360
    key = (filename, width, height, facing_right, quant_angle)
    if key not in _SCALE_CACHE:
        orig = _load_asset(filename)
        if orig is not None:
            scaled = pygame.transform.smoothscale(orig, (width, height))
            if not facing_right:
                scaled = pygame.transform.flip(scaled, True, False)
            if quant_angle != 0:
                scaled = pygame.transform.rotozoom(scaled, quant_angle, 1.0)
            _SCALE_CACHE[key] = scaled
        else:
            _SCALE_CACHE[key] = None
    return _SCALE_CACHE[key]


class OrcaRenderer:
    """Draws the rich Arctic fjord bay, orca pod, interactive toys, food, and UI."""

    def __init__(self, typography: GreiaTypography, resources: LocalizedResources) -> None:
        self.typography = typography
        self.resources = resources

        # Bounded static background caches
        self._bg_cache: dict[bool, pygame.Surface] = {}
        self._tool_font = typography.font(FontRole.TITLE, 13)
        self._badge_font = typography.font(FontRole.DISPLAY, 18)
        self._note_font = typography.font(FontRole.DISPLAY, 16)
        self._time_counter = 0.0

        # Pre-calculated toolbar buttons (5 large child buttons at bottom)
        btn_w, btn_h = 165, 72
        spacing = 15
        start_x = (REFERENCE_WIDTH - (5 * btn_w + 4 * spacing)) // 2
        btn_y = REFERENCE_HEIGHT - 82

        self.tool_rects: list[tuple[pygame.Rect, int, tuple[int, int, int], str, str]] = [
            (pygame.Rect(start_x + 0 * (btn_w + spacing), btn_y, btn_w, btn_h), 0, (249, 115, 22), "feed", "tool.feed"),
            (pygame.Rect(start_x + 1 * (btn_w + spacing), btn_y, btn_w, btn_h), 1, (244, 63, 94), "cuddle", "tool.cuddle"),
            (pygame.Rect(start_x + 2 * (btn_w + spacing), btn_y, btn_w, btn_h), 2, (56, 189, 248), "play", "tool.play"),
            (pygame.Rect(start_x + 3 * (btn_w + spacing), btn_y, btn_w, btn_h), 3, (168, 85, 247), "sing", "tool.sing"),
            (pygame.Rect(start_x + 4 * (btn_w + spacing), btn_y, btn_w, btn_h), 4, (16, 185, 129), "aurora", "tool.aurora"),
        ]

        # 4 Floating musical bells on water surface
        bell_spacing = 110
        b_start_x = 340
        self.bell_rects: list[tuple[pygame.Rect, int, tuple[int, int, int], str]] = [
            (pygame.Rect(b_start_x + 0 * bell_spacing, int(WATER_SURFACE_Y - 35), 68, 68), 0, (239, 68, 68), "DO"),
            (pygame.Rect(b_start_x + 1 * bell_spacing, int(WATER_SURFACE_Y - 35), 68, 68), 1, (234, 179, 8), "MI"),
            (pygame.Rect(b_start_x + 2 * bell_spacing, int(WATER_SURFACE_Y - 35), 68, 68), 2, (59, 130, 246), "SOL"),
            (pygame.Rect(b_start_x + 3 * bell_spacing, int(WATER_SURFACE_Y - 35), 68, 68), 3, (168, 85, 247), "DO⁺"),
        ]

    def _get_background(self, night_mode: bool) -> pygame.Surface:
        if night_mode in self._bg_cache:
            return self._bg_cache[night_mode]

        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        sky_h = int(WATER_SURFACE_Y)

        if night_mode:
            # Polar Night: Deep Velvet Midnight Sky with Aurora borealis hints
            for y in range(sky_h):
                r = y / max(1, sky_h)
                cr = int(8 + (18 - 8) * r)
                cg = int(14 + (36 - 14) * r)
                cb = int(32 + (68 - 32) * r)
                pygame.draw.line(surf, (cr, cg, cb), (0, y), (REFERENCE_WIDTH, y))

            # Twinkling Stars
            stars = [
                (70, 45), (140, 95), (220, 35), (310, 80), (450, 40),
                (560, 110), (670, 30), (760, 85), (860, 50), (940, 90),
                (180, 130), (510, 140), (810, 130), (910, 145),
            ]
            for sx, sy in stars:
                pygame.draw.circle(surf, (255, 255, 255), (sx, sy), 2)
                pygame.draw.circle(surf, (186, 230, 253), (sx, sy), 3, 1)

            # Glowing Golden Crescent Moon
            _draw_vector_moon(surf, 870, 75, 22, (254, 240, 138))

        else:
            # Sunny Arctic Day: Soft Sky Blue
            for y in range(sky_h):
                r = y / max(1, sky_h)
                cr = int(186 + (224 - 186) * r)
                cg = int(230 + (242 - 230) * r)
                cb = int(253 + (254 - 253) * r)
                pygame.draw.line(surf, (cr, cg, cb), (0, y), (REFERENCE_WIDTH, y))

            # Fluffy clouds
            clouds = [(180, 75, 70), (480, 60, 95), (820, 85, 80)]
            for cx, cy, cw in clouds:
                pygame.draw.ellipse(surf, (255, 255, 255), (cx - cw // 2, cy - 14, cw, 28))
                pygame.draw.circle(surf, (255, 255, 255), (cx - 18, cy - 8), 20)
                pygame.draw.circle(surf, (255, 255, 255), (cx + 12, cy - 12), 24)

        # Distant Mountain Range
        m_col_far = (30, 45, 72) if night_mode else (175, 195, 215)
        snow_col_far = (130, 160, 205) if night_mode else (240, 248, 255)
        far_mountains = [
            ([(0, sky_h), (110, 110), (250, sky_h)], [(110, 110), (140, 150), (80, 150)]),
            ([(190, sky_h), (370, 70), (560, sky_h)], [(370, 70), (415, 125), (320, 125)]),
            ([(510, sky_h), (730, 90), (920, sky_h)], [(730, 90), (775, 140), (680, 140)]),
            ([(780, sky_h), (960, 125), (1024, sky_h)], [(960, 125), (985, 160), (935, 160)]),
        ]
        for base_pts, snow_pts in far_mountains:
            pygame.draw.polygon(surf, m_col_far, base_pts)
            pygame.draw.polygon(surf, snow_col_far, snow_pts)

        # Near Fjord Mountains
        m_col_near = (22, 34, 56) if night_mode else (145, 165, 185)
        snow_col_near = (160, 195, 235) if night_mode else (255, 255, 255)
        near_mountains = [
            ([(0, sky_h), (180, 130), (380, sky_h)], [(180, 130), (220, 175), (140, 175)]),
            ([(310, sky_h), (540, 105), (770, sky_h)], [(540, 105), (590, 155), (490, 155)]),
            ([(680, sky_h), (880, 120), (1024, sky_h)], [(880, 120), (920, 165), (840, 165)]),
        ]
        for base_pts, snow_pts in near_mountains:
            pygame.draw.polygon(surf, m_col_near, base_pts)
            pygame.draw.polygon(surf, snow_col_near, snow_pts)

        # Floating Iceberg on Horizon
        ice_col = (56, 189, 248) if not night_mode else (38, 78, 140)
        ice_pts = [(740, sky_h), (765, sky_h - 22), (810, sky_h - 18), (835, sky_h)]
        pygame.draw.polygon(surf, (240, 249, 255), ice_pts)
        pygame.draw.polygon(surf, ice_col, [(750, sky_h), (765, sky_h - 22), (790, sky_h)])

        # High-Contrast Glowing Ocean Gradient
        ocean_h = REFERENCE_HEIGHT - sky_h
        for y_off in range(ocean_h):
            y = sky_h + y_off
            r = y_off / max(1, ocean_h)
            if night_mode:
                # Vibrant bioluminescent sapphire water with cyan undertone
                cr = int(14 + (8 - 14) * r)
                cg = int(55 + (35 - 55) * r)
                cb = int(105 + (70 - 105) * r)
            else:
                cr = int(2 + (3 - 2) * r)
                cg = int(132 + (105 - 132) * r)
                cb = int(199 + (161 - 199) * r)
            pygame.draw.line(surf, (cr, cg, cb), (0, y), (REFERENCE_WIDTH, y))

        # Seafloor
        sand_h = 70
        sand_y = REFERENCE_HEIGHT - sand_h
        sand_col = (16, 32, 54) if night_mode else (253, 230, 138)
        pygame.draw.rect(surf, sand_col, (0, sand_y, REFERENCE_WIDTH, sand_h))
        pygame.draw.line(surf, (56, 189, 248) if night_mode else (217, 119, 6), (0, sand_y), (REFERENCE_WIDTH, sand_y), 3 if night_mode else 3)

        # Pebbles & Starfish on sand
        pebble_col = (56, 189, 248) if night_mode else (244, 114, 182)
        for sx in (120, 290, 470, 680, 890):
            pygame.draw.ellipse(surf, pebble_col, (sx, sand_y + 18, 24, 14))
            pygame.draw.circle(surf, (255, 255, 255), (sx + 8, sand_y + 22), 3)

        self._bg_cache[night_mode] = surf
        return surf

    def draw_orca(self, surface: pygame.Surface, orca: OrcaEntity, night_mode: bool) -> None:
        """Render a cute, expressive orca with storybook artwork, smooth posture, and animations."""
        cx = int(orca.x)
        cy = int(orca.y)
        sc = orca.scale
        facing_right = orca.facing > 0
        state = orca.state

        # Base sprite dimensions (scaled proportionally)
        if orca.id == "kiko":
            base_w, base_h = int(140 * sc), int(88 * sc)
            kind = "baby"
        elif orca.id == "oskar":
            base_w, base_h = int(240 * sc), int(150 * sc)
            kind = "elder"
        else:  # luna
            base_w, base_h = int(200 * sc), int(125 * sc)
            kind = "acrobat"

        # Determine state-dependent sprite
        is_happy = state in (OrcaState.CUDDLE_BELLY, OrcaState.SINGING) or orca.is_happy
        if night_mode:
            sprite_name = f"orca_{kind}_night_happy.png" if is_happy else f"orca_{kind}_night.png"
        else:
            sprite_name = f"orca_{kind}_happy.png" if is_happy else f"orca_{kind}_day.png"

        # Angle rotation: in Pygame rotozoom, positive is counterclockwise.
        # If facing right: -angle (radians to degrees)
        # If facing left: angle
        rot_deg = int(-math.degrees(orca.angle)) if facing_right else int(math.degrees(orca.angle))

        # If cuddle belly roll: roll on belly (+180 deg)
        if state == OrcaState.CUDDLE_BELLY:
            rot_deg += 180

        sprite = _get_scaled_asset(sprite_name, base_w, base_h, facing_right=facing_right, angle_deg=rot_deg)
        if sprite is not None:
            rect = sprite.get_rect(center=(cx, cy))
            surface.blit(sprite, rect)

        # Draw thought bubble when hungry/craving food
        if state == OrcaState.SWIMMING and cy > WATER_SURFACE_Y + 25:
            f = orca.facing
            bubble_x = cx + int(f * 38 * sc)
            bubble_y = cy - int(64 * sc)
            pygame.draw.circle(surface, (255, 255, 255), (cx + int(f * 20 * sc), cy - int(40 * sc)), 4)
            pygame.draw.circle(surface, (255, 255, 255), (cx + int(f * 28 * sc), cy - int(50 * sc)), 7)
            pygame.draw.ellipse(surface, (255, 255, 255), (bubble_x - 24, bubble_y - 20, 48, 40))
            pygame.draw.ellipse(surface, (56, 189, 248), (bubble_x - 24, bubble_y - 20, 48, 40), 2)
            self._draw_food_icon(surface, bubble_x, bubble_y, orca.craved_food.value)

    def _draw_food_icon(self, surface: pygame.Surface, cx: int, cy: int, kind: str) -> None:
        """Helper to draw food in thought bubble or ocean."""
        if kind == "salmon":
            _draw_vector_fish(surface, cx, cy, 26, (244, 63, 94))
        elif kind == "squid":
            pygame.draw.ellipse(surface, (168, 85, 247), (cx - 10, cy - 10, 20, 20))
            for tx in range(-8, 9, 4):
                pygame.draw.line(surface, (192, 132, 252), (cx + tx, cy + 8), (cx + tx + 2, cy + 16), 2)
            pygame.draw.circle(surface, (255, 255, 255), (cx - 3, cy - 2), 2)
            pygame.draw.circle(surface, (255, 255, 255), (cx + 3, cy - 2), 2)
        elif kind == "shrimp":
            pygame.draw.arc(surface, (251, 146, 60), (cx - 10, cy - 10, 20, 20), 0, math.pi * 1.5, 4)
            pygame.draw.circle(surface, (255, 255, 255), (cx + 4, cy - 6), 2)
        elif kind == "ice":
            pygame.draw.circle(surface, (186, 230, 253), (cx, cy), 11)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 11, width=2)
            pygame.draw.line(surface, (56, 189, 248), (cx - 7, cy), (cx + 7, cy), 2)
            pygame.draw.line(surface, (56, 189, 248), (cx, cy - 7), (cx, cy + 7), 2)
        else:
            _draw_vector_fish(surface, cx, cy, 24, (249, 115, 22))

    def draw_food(self, surface: pygame.Surface, food: FoodEntity) -> None:
        """Render tasty fish treats tossing through the air or sinking in water."""
        self._draw_food_icon(surface, int(food.x), int(food.y), food.kind)

    def draw_toys(self, surface: pygame.Surface, toys: list[ToyEntity], night_mode: bool) -> None:
        """Render floating beach ball and rainbow jump hoop."""
        for toy in toys:
            tx = int(toy.x)
            ty = int(toy.y)
            if toy.kind == "ball":
                _draw_vector_ball(surface, tx, ty, int(26 * toy.scale), toy.rotation)
            elif toy.kind == "ring":
                rw, rh = int(54 * toy.scale), int(88 * toy.scale)
                pygame.draw.ellipse(surface, (244, 63, 94), (tx - rw // 2, ty - rh // 2, rw, rh), 6)
                pygame.draw.ellipse(surface, (250, 204, 21), (tx - rw // 2 + 3, ty - rh // 2 + 3, rw - 6, rh - 6), 4)
                pygame.draw.ellipse(surface, (56, 189, 248), (tx - rw // 2 + 6, ty - rh // 2 + 6, rw - 12, rh - 12), 4)

    def draw_bells(self, surface: pygame.Surface, night_mode: bool) -> None:
        """Render 4 musical sea bells floating on the surface."""
        for rect, idx, col, label in self.bell_rects:
            glow_surf = pygame.Surface((rect.width + 12, rect.height + 12), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*col, 70), (glow_surf.get_width() // 2, glow_surf.get_height() // 2), rect.width // 2 + 4)
            surface.blit(glow_surf, (rect.x - 6, rect.y - 6))

            pygame.draw.circle(surface, col, rect.center, rect.width // 2)
            pygame.draw.circle(surface, (255, 255, 255), rect.center, rect.width // 2, 3)

            note_surf = self._note_font.render(label, True, (255, 255, 255))
            surface.blit(note_surf, (rect.centerx - note_surf.get_width() // 2, rect.centery - note_surf.get_height() // 2))

    def draw_particles(self, surface: pygame.Surface, particles: list[ParticleEntity]) -> None:
        """Render dynamic particles: water splashes, bubbles, mist hearts, and musical notes."""
        for p in particles:
            px = int(p.x)
            py = int(p.y)
            if p.kind == "heart":
                _draw_vector_heart(surface, px, py, max(6, int(p.size * p.life)), p.color)
            elif p.kind == "note":
                _draw_vector_music(surface, px, py, max(8, int(p.size * p.life)), p.color)
            else:
                sz = max(2, int(p.size * p.life))
                pygame.draw.circle(surface, p.color, (px, py), sz)
                if p.kind == "bubble":
                    pygame.draw.circle(surface, (255, 255, 255), (px - 1, py - 1), max(1, sz // 2))

    def draw_ui(self, surface: pygame.Surface, active_tool: int, pod: OrcaPod) -> None:
        """Render the child-safe bottom toolbar with large, high-contrast buttons and crisp vector icons."""
        for rect, tool_idx, col, icon_kind, label_key in self.tool_rects:
            is_active = (active_tool == tool_idx)

            if is_active:
                pygame.draw.rect(surface, (255, 255, 255), rect.inflate(8, 8), border_radius=20)
                btn_col = col
            else:
                btn_col = (col[0] // 2 + 40, col[1] // 2 + 40, col[2] // 2 + 40)

            pygame.draw.rect(surface, btn_col, rect, border_radius=16)
            pygame.draw.rect(surface, (255, 255, 255), rect, width=3, border_radius=16)

            # Draw crisp vector icon in top half of button
            icon_cy = rect.top + 24
            if icon_kind == "feed":
                _draw_vector_fish(surface, rect.centerx, icon_cy, 28, (255, 255, 255))
            elif icon_kind == "cuddle":
                _draw_vector_heart(surface, rect.centerx, icon_cy, 22, (255, 255, 255))
            elif icon_kind == "play":
                _draw_vector_ball(surface, rect.centerx, icon_cy, 12)
            elif icon_kind == "sing":
                _draw_vector_music(surface, rect.centerx, icon_cy, 22, (255, 255, 255))
            elif icon_kind == "aurora":
                _draw_vector_moon(surface, rect.centerx, icon_cy, 12, (254, 240, 138))

            # Text label in bottom half
            label_text = self.resources.text(label_key) if label_key else ""
            lbl_surf = self._tool_font.render(label_text, True, (255, 255, 255))
            surface.blit(
                lbl_surf,
                (rect.centerx - lbl_surf.get_width() // 2, rect.bottom - lbl_surf.get_height() - 8),
            )

        # Top Right Activity Badges (Fed & Cuddled counters)
        badge_y = 20
        badge_x = REFERENCE_WIDTH - 210
        badge_surf = pygame.Surface((190, 48), pygame.SRCALPHA)
        pygame.draw.rect(badge_surf, (15, 23, 42, 180), (0, 0, 190, 48), border_radius=24)
        pygame.draw.rect(badge_surf, (255, 255, 255, 200), (0, 0, 190, 48), width=2, border_radius=24)
        surface.blit(badge_surf, (badge_x, badge_y))

        # Fish counter
        _draw_vector_fish(surface, badge_x + 28, badge_y + 24, 22, (249, 115, 22))
        fed_txt = self._badge_font.render(str(pod.total_fed), True, (255, 255, 255))
        surface.blit(fed_txt, (badge_x + 46, badge_y + 24 - fed_txt.get_height() // 2))

        # Heart counter
        _draw_vector_heart(surface, badge_x + 118, badge_y + 24, 18, (244, 63, 94))
        cuddle_txt = self._badge_font.render(str(pod.total_cuddled), True, (255, 255, 255))
        surface.blit(cuddle_txt, (badge_x + 134, badge_y + 24 - cuddle_txt.get_height() // 2))

    def render_frame(self, canvas_surface: pygame.Surface, pod: OrcaPod) -> None:
        """Compose all layers into a complete, beautiful presentable frame."""
        self._time_counter += 0.033

        # 1. Background (Fjord Sky, Mountains, Ocean Gradient, Seafloor)
        bg = self._get_background(pod.night_mode)
        canvas_surface.blit(bg, (0, 0))

        # 2. Musical bells if Song tool is selected
        if pod.active_tool == 3:
            self.draw_bells(canvas_surface, pod.night_mode)

        # 3. Interactive Toys
        self.draw_toys(canvas_surface, pod.toys, pod.night_mode)

        # 4. Swimming Orca Pod (Sorted by scale / depth)
        sorted_orcas = sorted(pod.orcas, key=lambda o: o.scale)
        for orca in sorted_orcas:
            self.draw_orca(canvas_surface, orca, pod.night_mode)

        # 5. Food Treats
        for food in pod.foods:
            self.draw_food(canvas_surface, food)

        # 6. Particles (Splashes, hearts, notes, bubbles)
        self.draw_particles(canvas_surface, pod.particles)

        # 7. UI Toolbar & HUD Counters
        self.draw_ui(canvas_surface, pod.active_tool, pod)
