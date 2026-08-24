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
    r = size // 4
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
    h = size // 2
    pygame.draw.ellipse(surf, col, (cx - w // 2, cy - h // 2, w, h))
    tail_pts = [(cx + w // 3, cy), (cx + w // 2 + 4, cy - h // 2), (cx + w // 2 + 4, cy + h // 2)]
    pygame.draw.polygon(surf, col, tail_pts)
    pygame.draw.circle(surf, (255, 255, 255), (cx - w // 4, cy - 2), max(2, size // 8))
    pygame.draw.circle(surf, (15, 23, 42), (cx - w // 4 - 1, cy - 2), max(1, size // 14))


def _draw_vector_ball(surf: pygame.Surface, cx: int, cy: int, r: int) -> None:
    """Draw a 4-color beach ball icon at (cx, cy)."""
    pygame.draw.circle(surf, (244, 63, 94), (cx, cy), r)
    pygame.draw.circle(surf, (250, 204, 21), (cx, cy), r, draw_top_right=True)
    pygame.draw.circle(surf, (56, 189, 248), (cx, cy), r, draw_bottom_left=True)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), r, draw_bottom_right=True)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), r, width=2)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), max(2, r // 3))


def _draw_vector_music(surf: pygame.Surface, cx: int, cy: int, size: int, col: tuple[int, int, int]) -> None:
    """Draw twin musical eighth notes at (cx, cy)."""
    nr = max(3, size // 6)
    pygame.draw.ellipse(surf, col, (cx - size // 3, cy + size // 4, nr * 2, nr * 2 - 2))
    pygame.draw.line(surf, col, (cx - size // 3 + nr * 2 - 1, cy + size // 4 + nr), (cx - size // 3 + nr * 2 - 1, cy - size // 3), 2)
    pygame.draw.ellipse(surf, col, (cx + size // 6, cy + size // 6, nr * 2, nr * 2 - 2))
    pygame.draw.line(surf, col, (cx + size // 6 + nr * 2 - 1, cy + size // 6 + nr), (cx + size // 6 + nr * 2 - 1, cy - size // 2), 2)
    pygame.draw.line(surf, col, (cx - size // 3 + nr * 2 - 1, cy - size // 3), (cx + size // 6 + nr * 2 - 1, cy - size // 2), 3)


def _draw_vector_moon(surf: pygame.Surface, cx: int, cy: int, r: int, col: tuple[int, int, int]) -> None:
    """Draw a glowing crescent moon and star at (cx, cy)."""
    pygame.draw.circle(surf, col, (cx, cy), r)
    pygame.draw.circle(surf, (15, 23, 42), (cx + r // 2, cy - r // 3), int(r * 0.85))
    sx, sy = cx + r // 2 + 4, cy + r // 3
    pygame.draw.polygon(surf, (255, 255, 255), [(sx, sy - 4), (sx + 1, sy - 1), (sx + 4, sy), (sx + 1, sy + 1), (sx, sy + 4), (sx - 1, sy + 1), (sx - 4, sy), (sx - 1, sy - 1)])


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

        if night_mode:
            # Deep Arctic Aurora Night Sky
            for y in range(0, int(WATER_SURFACE_Y), 3):
                r = y / WATER_SURFACE_Y
                cr = int(10 + (25 - 10) * r)
                cg = int(15 + (45 - 15) * r)
                cb = int(45 + (85 - 45) * r)
                pygame.draw.rect(surf, (cr, cg, cb), (0, y, REFERENCE_WIDTH, 3))

            # Shimmering Aurora Borealis ribbons
            aurora_points_1 = [
                (0, 70), (180, 45), (420, 95), (650, 50), (880, 80), (REFERENCE_WIDTH, 55),
                (REFERENCE_WIDTH, 140), (820, 160), (580, 130), (320, 170), (120, 135), (0, 150)
            ]
            aurora_surf = pygame.Surface((REFERENCE_WIDTH, int(WATER_SURFACE_Y)), pygame.SRCALPHA)
            pygame.draw.polygon(aurora_surf, (52, 211, 153, 90), aurora_points_1)
            pygame.draw.polygon(aurora_surf, (167, 139, 250, 75), [(x, y - 20) for x, y in aurora_points_1])
            surf.blit(aurora_surf, (0, 0))

            # Distant Snowy Glaciers (Night Tint)
            pygame.draw.polygon(surf, (30, 41, 59), [(40, int(WATER_SURFACE_Y)), (160, 110), (280, int(WATER_SURFACE_Y))])
            pygame.draw.polygon(surf, (51, 65, 85), [(160, 110), (195, 145), (280, int(WATER_SURFACE_Y))])
            pygame.draw.polygon(surf, (71, 85, 105), [(140, 125), (160, 110), (185, 130)])

            pygame.draw.polygon(surf, (30, 41, 59), [(220, int(WATER_SURFACE_Y)), (380, 90), (540, int(WATER_SURFACE_Y))])
            pygame.draw.polygon(surf, (51, 65, 85), [(380, 90), (430, 135), (540, int(WATER_SURFACE_Y))])

            pygame.draw.polygon(surf, (30, 41, 59), [(600, int(WATER_SURFACE_Y)), (760, 105), (920, int(WATER_SURFACE_Y))])
            pygame.draw.polygon(surf, (51, 65, 85), [(760, 105), (810, 140), (920, int(WATER_SURFACE_Y))])

            # Deep Bioluminescent Fjord Ocean
            for y in range(int(WATER_SURFACE_Y), REFERENCE_HEIGHT, 3):
                r = (y - WATER_SURFACE_Y) / (REFERENCE_HEIGHT - WATER_SURFACE_Y)
                cr = int(12 + (8 - 12) * r)
                cg = int(24 + (16 - 24) * r)
                cb = int(68 + (45 - 68) * r)
                pygame.draw.rect(surf, (cr, cg, cb), (0, y, REFERENCE_WIDTH, 3))

            # Luminous water edge line
            pygame.draw.line(surf, (52, 211, 153), (0, int(WATER_SURFACE_Y)), (REFERENCE_WIDTH, int(WATER_SURFACE_Y)), 3)

        else:
            # Bright Crisp Arctic Sky
            for y in range(0, int(WATER_SURFACE_Y), 3):
                r = y / WATER_SURFACE_Y
                cr = int(224 + (186 - 224) * r)
                cg = int(242 + (230 - 242) * r)
                cb = int(254 + (253 - 254) * r)
                pygame.draw.rect(surf, (cr, cg, cb), (0, y, REFERENCE_WIDTH, 3))

            # Distant Majestic Snow Glaciers
            # Mountain 1
            pygame.draw.polygon(surf, (148, 163, 184), [(30, int(WATER_SURFACE_Y)), (160, 100), (290, int(WATER_SURFACE_Y))])
            pygame.draw.polygon(surf, (241, 245, 249), [(160, 100), (120, 150), (160, 140), (200, 150)])
            # Mountain 2 (Hero Central Peak)
            pygame.draw.polygon(surf, (203, 213, 225), [(200, int(WATER_SURFACE_Y)), (380, 75), (560, int(WATER_SURFACE_Y))])
            pygame.draw.polygon(surf, (255, 255, 255), [(380, 75), (320, 135), (380, 120), (440, 135)])
            # Mountain 3
            pygame.draw.polygon(surf, (148, 163, 184), [(580, int(WATER_SURFACE_Y)), (740, 95), (900, int(WATER_SURFACE_Y))])
            pygame.draw.polygon(surf, (241, 245, 249), [(740, 95), (690, 145), (740, 130), (790, 145)])

            # Azure Crystal Ocean Water
            for y in range(int(WATER_SURFACE_Y), REFERENCE_HEIGHT, 3):
                r = (y - WATER_SURFACE_Y) / (REFERENCE_HEIGHT - WATER_SURFACE_Y)
                cr = int(14 + (3 - 14) * r)
                cg = int(165 + (105 - 165) * r)
                cb = int(233 + (160 - 233) * r)
                pygame.draw.rect(surf, (cr, cg, cb), (0, y, REFERENCE_WIDTH, 3))

            # Sparkling water edge line
            pygame.draw.line(surf, (255, 255, 255), (0, int(WATER_SURFACE_Y)), (REFERENCE_WIDTH, int(WATER_SURFACE_Y)), 3)

        # Sandy seafloor with smooth rocks
        sand_h = 75
        sand_y = REFERENCE_HEIGHT - sand_h
        sand_col = (30, 27, 46) if night_mode else (254, 243, 199)
        pygame.draw.rect(surf, sand_col, (0, sand_y, REFERENCE_WIDTH, sand_h))
        pygame.draw.line(surf, (147, 51, 234) if night_mode else (217, 119, 6), (0, sand_y), (REFERENCE_WIDTH, sand_y), 3)

        # Ambient Shells & Starfish on sand
        shell_col = (250, 204, 21) if night_mode else (244, 114, 182)
        for sx in (140, 320, 510, 720, 890):
            pygame.draw.circle(surf, shell_col, (sx, sand_y + 24), 10)
            pygame.draw.circle(surf, (255, 255, 255), (sx, sand_y + 24), 4)

        self._bg_cache[night_mode] = surf
        return surf

    def draw_orca(self, surface: pygame.Surface, orca: OrcaEntity, night_mode: bool) -> None:
        """Render a cute, expressive orca with smooth posture, fins, patches and facial expressions."""
        cx = int(orca.x)
        cy = int(orca.y)
        sc = orca.scale
        f = orca.facing
        state = orca.state

        # Base body colors
        body_col = (26, 36, 54) if not night_mode else (15, 23, 42)
        white_col = (255, 255, 255)
        saddle_col = (100, 116, 139)

        # Swimming tail wag
        wag = math.sin(orca.swim_phase) * (14.0 * sc)

        # 1. Tail Fluke (drawn behind body)
        fluke_x = cx - int(f * 52 * sc)
        fluke_y = cy + int(wag * 0.3)
        fluke_pts = [
            (fluke_x, fluke_y),
            (fluke_x - int(f * 26 * sc), fluke_y - int(18 * sc)),
            (fluke_x - int(f * 20 * sc), fluke_y),
            (fluke_x - int(f * 26 * sc), fluke_y + int(18 * sc)),
        ]
        pygame.draw.polygon(surface, body_col, fluke_pts)

        # 2. Main Sleek Body (Smooth Ellipse)
        body_w = int(115 * sc)
        body_h = int(64 * sc)
        body_rect = pygame.Rect(cx - body_w // 2, cy - body_h // 2, body_w, body_h)
        pygame.draw.ellipse(surface, body_col, body_rect)

        # 3. Dorsal Fin (Top)
        fin_base_x = cx - int(f * 6 * sc)
        fin_tip_x = cx - int(f * 18 * sc) if orca.id != "kiko" else cx - int(f * 10 * sc)
        fin_h = int(42 * sc) if orca.id == "oskar" else int(30 * sc)
        fin_pts = [
            (fin_base_x, cy - int(24 * sc)),
            (fin_tip_x, cy - int(24 * sc) - fin_h),
            (fin_base_x + int(f * 20 * sc), cy - int(24 * sc)),
        ]
        pygame.draw.polygon(surface, body_col, fin_pts)

        # 4. Grey Saddle Patch (Behind dorsal fin)
        saddle_rect = pygame.Rect(cx - int(f * 18 * sc) - int(14 * sc), cy - int(20 * sc), int(28 * sc), int(16 * sc))
        pygame.draw.ellipse(surface, saddle_col, saddle_rect)

        # 5. White Belly & Lower Jaw Patch
        if state == OrcaState.CUDDLE_BELLY:
            # Fully visible adorable white tummy when cuddled!
            tummy_w = int(76 * sc)
            tummy_h = int(36 * sc)
            pygame.draw.ellipse(surface, white_col, (cx - tummy_w // 2, cy - tummy_h // 2 + int(4 * sc), tummy_w, tummy_h))
        else:
            # Classic lower chin / belly curve
            belly_w = int(72 * sc)
            belly_h = int(24 * sc)
            pygame.draw.ellipse(surface, white_col, (cx + int(f * 8 * sc) - belly_w // 2, cy + int(12 * sc), belly_w, belly_h))

        # 6. Pectoral Side Flipper (Bottom Front)
        flip_x = cx + int(f * 12 * sc)
        flip_pts = [
            (flip_x, cy + int(14 * sc)),
            (flip_x + int(f * 18 * sc), cy + int(36 * sc)),
            (flip_x - int(f * 4 * sc), cy + int(32 * sc)),
        ]
        pygame.draw.polygon(surface, body_col, flip_pts)

        # 7. Iconic White Eye Patch (Above and behind eye)
        patch_x = cx + int(f * 22 * sc)
        patch_y = cy - int(12 * sc)
        pygame.draw.ellipse(surface, white_col, (patch_x - int(12 * sc), patch_y - int(7 * sc), int(24 * sc), int(14 * sc)))

        # 8. Animated Eye & Catchlight
        eye_x = cx + int(f * 36 * sc)
        eye_y = cy - int(2 * sc)

        if orca.is_blinking or state in (OrcaState.CUDDLE_BELLY, OrcaState.SLEEPING):
            # Happy smiling / sleeping closed eye arc ^_^
            pygame.draw.arc(surface, (255, 255, 255) if not night_mode else (226, 232, 240), (eye_x - int(7 * sc), eye_y - int(6 * sc), int(14 * sc), int(12 * sc)), 0, math.pi, 3)
        else:
            # Big adorable glossy eye with white twinkle catchlight
            pygame.draw.circle(surface, (15, 23, 42), (eye_x, eye_y), max(3, int(6 * sc)))
            pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y), max(3, int(6 * sc)), 1)
            pygame.draw.circle(surface, (255, 255, 255), (eye_x + int(f * 2 * sc), eye_y - int(2 * sc)), max(1, int(2.2 * sc)))

        # Rosy Cheerful Cheek (Blushing pink)
        pygame.draw.ellipse(surface, (251, 113, 133), (eye_x - int(f * 4 * sc) - int(6 * sc), eye_y + int(8 * sc) - int(4 * sc), int(12 * sc), int(8 * sc)))

        # 9. Mouth / Smile
        mouth_x = cx + int(f * 44 * sc)
        mouth_y = cy + int(10 * sc)
        pygame.draw.arc(surface, (15, 23, 42), (mouth_x - int(10 * sc), mouth_y - int(6 * sc), int(20 * sc), int(12 * sc)), 0, math.pi, 2)

        # 10. Cute Blowhole notch on top
        blow_x = cx + int(f * 14 * sc)
        blow_y = cy - int(28 * sc)
        pygame.draw.ellipse(surface, (15, 23, 42), (blow_x - 3, blow_y - 2, 6, 4))

        # 11. Thought Bubble (If craving food in swimming mode)
        if state == OrcaState.SWIMMING and cy > WATER_SURFACE_Y + 20:
            bubble_x = cx + int(f * 35 * sc)
            bubble_y = cy - int(60 * sc)
            pygame.draw.circle(surface, (255, 255, 255), (cx + int(f * 18 * sc), cy - int(38 * sc)), 4)
            pygame.draw.circle(surface, (255, 255, 255), (cx + int(f * 24 * sc), cy - int(48 * sc)), 7)
            pygame.draw.ellipse(surface, (255, 255, 255), (bubble_x - 22, bubble_y - 18, 44, 36))
            pygame.draw.ellipse(surface, (56, 189, 248), (bubble_x - 22, bubble_y - 18, 44, 36), 2)
            _draw_vector_fish(surface, bubble_x, bubble_y, 22, (249, 115, 22))

    def draw_food(self, surface: pygame.Surface, food: FoodEntity) -> None:
        """Render tasty fish treats tossing through the air or sinking in water."""
        fx = int(food.x)
        fy = int(food.y)
        kind = food.kind

        if kind == "salmon":
            _draw_vector_fish(surface, fx, fy, 26, (244, 63, 94))
        elif kind == "squid":
            pygame.draw.ellipse(surface, (168, 85, 247), (fx - 10, fy - 10, 20, 20))
            for tx in range(-8, 9, 4):
                pygame.draw.line(surface, (192, 132, 252), (fx + tx, fy + 8), (fx + tx + 2, fy + 16), 2)
            pygame.draw.circle(surface, (255, 255, 255), (fx - 3, fy - 2), 2)
            pygame.draw.circle(surface, (255, 255, 255), (fx + 3, fy - 2), 2)
        elif kind == "ice":
            pygame.draw.circle(surface, (186, 230, 253), (fx, fy), 11)
            pygame.draw.circle(surface, (255, 255, 255), (fx, fy), 11, width=2)
            pygame.draw.line(surface, (56, 189, 248), (fx - 7, fy), (fx + 7, fy), 2)
            pygame.draw.line(surface, (56, 189, 248), (fx, fy - 7), (fx, fy + 7), 2)
        else:
            _draw_vector_fish(surface, fx, fy, 24, (148, 163, 184))

    def draw_toys(self, surface: pygame.Surface, toys: list[ToyEntity], night_mode: bool) -> None:
        """Render floating beach ball and rainbow jump hoop."""
        for toy in toys:
            tx = int(toy.x)
            ty = int(toy.y)
            if toy.kind == "ball":
                _draw_vector_ball(surface, tx, ty, int(26 * toy.scale))
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
