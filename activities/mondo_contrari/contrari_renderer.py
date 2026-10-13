"""Visual rendering and scene animation for Mondo Contrari."""

from __future__ import annotations

import math
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .contrari_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ContrariModel,
        ContrariParticle,
        OppositeCategory,
    )
else:
    from contrari_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ContrariModel,
        ContrariParticle,
        OppositeCategory,
    )

# Colors
COLOR_SKY_TOP: Final = (144, 202, 249)
COLOR_SKY_BOT: Final = (227, 242, 253)
COLOR_GRASS: Final = (102, 187, 106)
COLOR_GRASS_DARK: Final = (76, 175, 80)

COLOR_FLASH_WHITE: Final = (255, 255, 255)
COLOR_FLASH_PINK: Final = (255, 182, 193)
COLOR_DANI_BLUE: Final = (38, 166, 154)
COLOR_DANI_DARK: Final = (0, 121, 107)

# The five concepts and their two spoken/visible state keys are the same
# semantic lesson concepts across every UI language.
CATEGORY_OPPOSITE_KEYS: Final = {
    OppositeCategory.UP_DOWN: ("up", "down"),
    OppositeCategory.BIG_SMALL: ("big", "small"),
    OppositeCategory.IN_OUT: ("in", "out"),
    OppositeCategory.OPEN_CLOSED: ("open", "closed"),
    OppositeCategory.FAST_SLOW: ("fast", "slow"),
}

# Neutral standalone-renderer defaults are pictograms, not another language.
NEUTRAL_STATE_SYMBOLS: Final = {
    "up": "↑", "down": "↓", "big": "＋", "small": "−",
    "in": "↘", "out": "↗", "open": "○", "closed": "●",
    "fast": "»", "slow": "·",
}

CATEGORY_ICONS: Final = {
    OppositeCategory.UP_DOWN: "🎈",
    OppositeCategory.BIG_SMALL: "🫧",
    OppositeCategory.IN_OUT: "📦",
    OppositeCategory.OPEN_CLOSED: "🚪",
    OppositeCategory.FAST_SLOW: "⚡",
}


class ContrariRenderer:
    """Render opposite concepts with lively animations and giant toddler touch targets."""

    def __init__(
        self,
        locale: str = "it",
        resources: LocalizedResources | None = None,
        typography: GreiaTypography | None = None,
    ) -> None:
        # Keep the historical locale argument for existing embedder callers.
        # Locale choice itself belongs to the composition root and resources.
        self._locale = locale
        self._typography = typography or GreiaTypography()
        self._state_labels = {
            state: resources.text(f"opposite.{state}") if resources else symbol
            for state, symbol in NEUTRAL_STATE_SYMBOLS.items()
        }
        self._toolbar_labels = {
            category: (
                f"{CATEGORY_ICONS[category]} "
                f"{self._state_labels[first]} / {self._state_labels[second]}"
                if resources else CATEGORY_ICONS[category]
            )
            for category, (first, second) in CATEGORY_OPPOSITE_KEYS.items()
        }
        self._toolbar_surfaces: dict[tuple[OppositeCategory, bool], pygame.Surface] = {}
        self._status_surfaces: dict[tuple[str, tuple[int, int, int]], pygame.Surface] = {}
        self._reference_surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))

        # Top Toolbar buttons (5 categories)
        btn_w, btn_h, spacing = 176, 56, 12
        start_x = (REFERENCE_WIDTH - (5 * btn_w + 4 * spacing)) // 2
        self.category_buttons: dict[OppositeCategory, pygame.Rect] = {
            cat: pygame.Rect(start_x + idx * (btn_w + spacing), 18, btn_w, btn_h)
            for idx, cat in enumerate(OppositeCategory)
        }

        # Central active play area (large generous hitbox)
        self.play_surface_rect = pygame.Rect(100, 90, 824, 480)

    def render(self, target_surface: pygame.Surface, model: ContrariModel) -> None:
        ref = self._reference_surf

        # 1. Cheerful Meadow Background
        self._render_background(ref)

        # 2. Current Opposite Scene
        if model.category == OppositeCategory.UP_DOWN:
            self._render_scene_up_down(ref, model)
        elif model.category == OppositeCategory.BIG_SMALL:
            self._render_scene_big_small(ref, model)
        elif model.category == OppositeCategory.IN_OUT:
            self._render_scene_in_out(ref, model)
        elif model.category == OppositeCategory.OPEN_CLOSED:
            self._render_scene_open_closed(ref, model)
        elif model.category == OppositeCategory.FAST_SLOW:
            self._render_scene_fast_slow(ref, model)

        # 3. Dynamic Particles
        self._render_particles(ref, model)

        # 4. Top Category Toolbar & Labels
        self._render_toolbar(ref, model)

        # Scale to physical window
        sw, sh = target_surface.get_size()
        if (sw, sh) == (REFERENCE_WIDTH, REFERENCE_HEIGHT):
            target_surface.blit(ref, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(ref, (sw, sh))
            target_surface.blit(scaled, (0, 0))

    def _render_background(self, surf: pygame.Surface) -> None:
        # Sky gradient
        for y in range(0, 420, 10):
            frac = y / 420.0
            r = int(COLOR_SKY_TOP[0] + (COLOR_SKY_BOT[0] - COLOR_SKY_TOP[0]) * frac)
            g = int(COLOR_SKY_TOP[1] + (COLOR_SKY_BOT[1] - COLOR_SKY_TOP[1]) * frac)
            b = int(COLOR_SKY_TOP[2] + (COLOR_SKY_BOT[2] - COLOR_SKY_TOP[2]) * frac)
            pygame.draw.rect(surf, (r, g, b), (0, y, REFERENCE_WIDTH, 10))

        # Green Hills
        pygame.draw.ellipse(surf, COLOR_GRASS_DARK, (-60, 370, 600, 300))
        pygame.draw.ellipse(surf, COLOR_GRASS, (400, 360, 700, 320))
        pygame.draw.rect(surf, COLOR_GRASS, (0, 460, REFERENCE_WIDTH, 140))

        # Little flowers on grass
        for fx, fy in [(120, 490), (280, 520), (740, 500), (890, 530)]:
            pygame.draw.circle(surf, (255, 235, 59), (fx, fy), 5)
            pygame.draw.circle(surf, (255, 255, 255), (fx - 4, fy), 3)
            pygame.draw.circle(surf, (255, 255, 255), (fx + 4, fy), 3)

    # ------------------ 1. SCENE: UP / DOWN ------------------
    def _render_scene_up_down(self, surf: pygame.Surface, model: ContrariModel) -> None:
        bx = 512
        by = int(model.balloon_y)

        # Fluffy clouds around
        self._draw_cloud(surf, 200, 150, 1.2)
        self._draw_cloud(surf, 800, 180, 1.0)

        # Balloon
        balloon_r = 54
        pygame.draw.circle(surf, (239, 83, 80), (bx, by - balloon_r), balloon_r)
        # Gold stripe
        pygame.draw.ellipse(surf, (255, 215, 0), (bx - 20, by - balloon_r * 2, 40, balloon_r * 2))
        # Highlight
        pygame.draw.circle(surf, (255, 180, 180), (bx - 18, by - balloon_r - 18), 12)

        # Basket & ropes
        pygame.draw.line(surf, (120, 80, 40), (bx - 25, by - 4), (bx - 12, by + 28), 2)
        pygame.draw.line(surf, (120, 80, 40), (bx + 25, by - 4), (bx + 12, by + 28), 2)
        pygame.draw.rect(surf, (185, 120, 60), (bx - 20, by + 28, 40, 26), border_radius=4)

        # Flash Rabbit in basket
        self._draw_flash_rabbit(surf, bx, by + 18, scale=0.85)

        # Big Toddler Label Banner
        banner_text = self._state_labels["up" if model.is_up else "down"]
        banner_col = (76, 175, 80) if model.is_up else (255, 152, 0)
        self._draw_status_banner(surf, banner_text, banner_col)

    # ------------------ 2. SCENE: BIG / SMALL ------------------
    def _render_scene_big_small(self, surf: pygame.Surface, model: ContrariModel) -> None:
        # Dani Robot on left pumping
        self._draw_dani_robot(surf, 260, 390)

        # Bubble in center
        cx, cy = 560, 310
        base_r = 120
        cur_r = int(base_r * model.bubble_scale)

        # Shimmering Bubble
        bubble_surf = pygame.Surface((cur_r * 2 + 20, cur_r * 2 + 20), pygame.SRCALPHA)
        # Translucent bubble body
        pygame.draw.circle(bubble_surf, (129, 212, 250, 110), (cur_r + 10, cur_r + 10), cur_r)
        # Iridescent rim
        pygame.draw.circle(bubble_surf, (0, 229, 255, 200), (cur_r + 10, cur_r + 10), cur_r, max(2, int(cur_r * 0.05)))
        # Highlight arcs
        pygame.draw.circle(bubble_surf, (255, 255, 255, 220), (cur_r + 10 - int(cur_r * 0.35), cur_r + 10 - int(cur_r * 0.35)), max(3, int(cur_r * 0.15)))
        surf.blit(bubble_surf, (cx - cur_r - 10, cy - cur_r - 10))

        banner_text = self._state_labels["big" if model.is_big else "small"]
        banner_col = (156, 39, 176) if model.is_big else (3, 169, 244)
        self._draw_status_banner(surf, banner_text, banner_col)

    # ------------------ 3. SCENE: IN / OUT ------------------
    def _render_scene_in_out(self, surf: pygame.Surface, model: ContrariModel) -> None:
        box_x, box_y = 512, 380
        rx = box_x
        ry = int(model.box_rabbit_y)

        # Flash Rabbit jumping or hiding
        self._draw_flash_rabbit(surf, rx, ry, scale=1.0)

        # Big Toy Box (front)
        bw, bh = 170, 130
        pygame.draw.rect(surf, (244, 67, 54), (box_x - bw // 2, box_y - bh // 2, bw, bh), border_radius=12)
        # Yellow ribbons on box
        pygame.draw.rect(surf, (255, 235, 59), (box_x - 14, box_y - bh // 2, 28, bh))
        pygame.draw.rect(surf, (255, 235, 59), (box_x - bw // 2, box_y - 12, bw, 24))

        # Box lid
        lid_y = box_y - bh // 2 - 12 if model.is_in else box_y - bh // 2 - 40
        pygame.draw.rect(surf, (211, 47, 47), (box_x - bw // 2 - 10, lid_y, bw + 20, 24), border_radius=6)

        banner_text = self._state_labels["in" if model.is_in else "out"]
        banner_col = (233, 30, 99) if model.is_in else (0, 150, 136)
        self._draw_status_banner(surf, banner_text, banner_col)

    # ------------------ 4. SCENE: OPEN / CLOSED ------------------
    def _render_scene_open_closed(self, surf: pygame.Surface, model: ContrariModel) -> None:
        wx, wy = 512, 290
        ww, wh = 200, 220

        # Cottage Wall / Window Frame (timber brown)
        pygame.draw.rect(surf, (141, 110, 99), (wx - ww // 2 - 16, wy - wh // 2 - 16, ww + 32, wh + 32), border_radius=16)
        # Inside Window Room / Sky
        pygame.draw.rect(surf, (255, 249, 196), (wx - ww // 2, wy - wh // 2, ww, wh), border_radius=8)

        # Inside view when open: Cute singing bluebird & warm sun!
        if model.shutter_open_ratio > 0.1:
            pygame.draw.circle(surf, (255, 215, 0), (wx + 40, wy - 40), 28)
            # Bluebird
            pygame.draw.circle(surf, (66, 165, 245), (wx - 20, wy + 20), 20)
            pygame.draw.circle(surf, (255, 255, 255), (wx - 25, wy + 16), 4)
            pygame.draw.polygon(surf, (255, 167, 38), [(wx - 36, wy + 20), (wx - 45, wy + 18), (wx - 36, wy + 26)])

        # Window Shutters (Left & Right)
        half_w = ww // 2
        shutter_w = int(half_w * (1.0 - model.shutter_open_ratio * 0.85))
        # Left shutter
        pygame.draw.rect(surf, (67, 160, 71), (wx - half_w, wy - wh // 2, max(6, shutter_w), wh), border_radius=4)
        pygame.draw.rect(surf, (46, 125, 50), (wx - half_w, wy - wh // 2, max(6, shutter_w), wh), 3, border_radius=4)
        # Right shutter
        pygame.draw.rect(surf, (67, 160, 71), (wx + half_w - shutter_w, wy - wh // 2, max(6, shutter_w), wh), border_radius=4)
        pygame.draw.rect(surf, (46, 125, 50), (wx + half_w - shutter_w, wy - wh // 2, max(6, shutter_w), wh), 3, border_radius=4)

        banner_text = self._state_labels["open" if model.is_open else "closed"]
        banner_col = (76, 175, 80) if model.is_open else (121, 85, 72)
        self._draw_status_banner(surf, banner_text, banner_col)

    # ------------------ 5. SCENE: FAST / SLOW ------------------
    def _render_scene_fast_slow(self, surf: pygame.Surface, model: ContrariModel) -> None:
        # Track line
        pygame.draw.line(surf, (200, 230, 200), (120, 360), (900, 360), 4)
        pygame.draw.line(surf, (200, 230, 200), (120, 440), (900, 440), 4)

        # Upper lane: Flash the Rabbit
        rx = int(model.runner_x)
        self._draw_flash_rabbit(surf, rx, 310, scale=0.9, running=model.is_fast)

        # Lower lane: The Friendly Snail
        sx = int(model.snail_x)
        self._draw_snail(surf, sx, 420)

        banner_text = self._state_labels["fast" if model.is_fast else "slow"]
        banner_col = (255, 160, 0) if model.is_fast else (139, 195, 74)
        self._draw_status_banner(surf, banner_text, banner_col)

    # ------------------ CHARACTER HELPERS ------------------
    def _draw_flash_rabbit(self, surf: pygame.Surface, x: int, y: int, scale: float = 1.0, running: bool = False) -> None:
        ear_tilt = 12 if running else 0
        # Ears
        pygame.draw.ellipse(surf, COLOR_FLASH_WHITE, (x - 22 + ear_tilt, y - 65, 18, 48))
        pygame.draw.ellipse(surf, COLOR_FLASH_PINK, (x - 18 + ear_tilt, y - 56, 10, 34))
        pygame.draw.ellipse(surf, COLOR_FLASH_WHITE, (x + 4 + ear_tilt, y - 65, 18, 48))
        pygame.draw.ellipse(surf, COLOR_FLASH_PINK, (x + 8 + ear_tilt, y - 56, 10, 34))

        # Head & Body
        pygame.draw.circle(surf, COLOR_FLASH_WHITE, (x, y), int(30 * scale))
        # Eyes
        pygame.draw.circle(surf, (40, 40, 40), (x - 10, y - 4), 5)
        pygame.draw.circle(surf, (40, 40, 40), (x + 10, y - 4), 5)
        pygame.draw.circle(surf, (255, 255, 255), (x - 12, y - 6), 2)
        pygame.draw.circle(surf, (255, 255, 255), (x + 8, y - 6), 2)
        # Nose & cute smile
        pygame.draw.circle(surf, COLOR_FLASH_PINK, (x, y + 5), 4)
        pygame.draw.arc(surf, (60, 60, 60), (x - 8, y + 4, 16, 12), math.pi * 1.1, math.pi * 1.9, 2)

    def _draw_dani_robot(self, surf: pygame.Surface, x: int, y: int) -> None:
        # Head & Antenna
        pygame.draw.line(surf, COLOR_DANI_DARK, (x, y - 40), (x, y - 60), 3)
        pygame.draw.circle(surf, (255, 215, 0), (x, y - 64), 6)
        pygame.draw.rect(surf, COLOR_DANI_BLUE, (x - 26, y - 40, 52, 42), border_radius=8)
        # Robot Eyes
        pygame.draw.circle(surf, (255, 255, 255), (x - 12, y - 20), 8)
        pygame.draw.circle(surf, (255, 255, 255), (x + 12, y - 20), 8)
        pygame.draw.circle(surf, (0, 229, 255), (x - 12, y - 20), 4)
        pygame.draw.circle(surf, (0, 229, 255), (x + 12, y - 20), 4)
        # Robot smile
        pygame.draw.line(surf, (255, 255, 255), (x - 10, y - 6), (x + 10, y - 6), 3)

        # Body
        pygame.draw.rect(surf, COLOR_DANI_BLUE, (x - 22, y + 6, 44, 48), border_radius=6)
        # Pump in hand
        pygame.draw.rect(surf, (255, 87, 34), (x + 24, y + 10, 16, 36), border_radius=4)
        pygame.draw.line(surf, (120, 120, 120), (x + 32, y + 28), (x + 75, y + 10), 3)

    def _draw_snail(self, surf: pygame.Surface, x: int, y: int) -> None:
        # Snail shell
        pygame.draw.circle(surf, (255, 138, 128), (x, y), 22)
        pygame.draw.circle(surf, (239, 83, 80), (x, y), 14, 3)
        # Soft body
        pygame.draw.ellipse(surf, (255, 224, 130), (x - 25, y + 8, 55, 18))
        # Eyestalks
        pygame.draw.line(surf, (255, 224, 130), (x + 22, y + 10), (x + 28, y - 8), 3)
        pygame.draw.circle(surf, (40, 40, 40), (x + 28, y - 9), 3)

    def _draw_cloud(self, surf: pygame.Surface, x: int, y: int, scale: float) -> None:
        col = (255, 255, 255)
        pygame.draw.circle(surf, col, (x - int(25 * scale), y), int(22 * scale))
        pygame.draw.circle(surf, col, (x, y - int(10 * scale)), int(30 * scale))
        pygame.draw.circle(surf, col, (x + int(25 * scale), y), int(22 * scale))
        pygame.draw.rect(surf, col, (x - int(25 * scale), y - int(6 * scale), int(50 * scale), int(16 * scale)))

    def _draw_status_banner(self, surf: pygame.Surface, text: str, accent: tuple[int, int, int]) -> None:
        banner_rect = pygame.Rect(512 - 130, 490, 260, 68)
        pygame.draw.rect(surf, (255, 255, 255), banner_rect, border_radius=34)
        pygame.draw.rect(surf, accent, banner_rect, 5, border_radius=34)
        cache_key = (text, accent)
        lbl = self._status_surfaces.get(cache_key)
        if lbl is None:
            for font_size in (40, 36, 32, 28, 24, 20):
                if self._typography.measure(text, FontRole.DISPLAY, font_size).width <= banner_rect.width - 24:
                    break
            lbl = self._typography.render(text, FontRole.DISPLAY, font_size, accent)
            self._status_surfaces[cache_key] = lbl
        surf.blit(lbl, lbl.get_rect(center=banner_rect.center))

    def _render_toolbar(self, surf: pygame.Surface, model: ContrariModel) -> None:
        for cat, rect in self.category_buttons.items():
            is_active = model.category == cat
            bg = (255, 255, 255) if is_active else (245, 245, 250)
            border_col = (255, 112, 67) if is_active else (180, 195, 215)
            pygame.draw.rect(surf, bg, rect, border_radius=18)
            pygame.draw.rect(surf, border_col, rect, 4 if is_active else 2, border_radius=18)

            cached_key = (cat, is_active)
            text_surf = self._toolbar_surfaces.get(cached_key)
            if text_surf is None:
                label = self._toolbar_labels[cat]
                for font_size in (19, 17, 15, 13):
                    if self._typography.measure(label, FontRole.CONTROL, font_size).width <= rect.width - 12:
                        break
                text_surf = self._typography.render(
                    label,
                    FontRole.CONTROL,
                    font_size,
                    (40, 40, 40) if is_active else (100, 100, 100),
                )
                self._toolbar_surfaces[cached_key] = text_surf
            surf.blit(text_surf, text_surf.get_rect(center=rect.center))

    def _render_particles(self, surf: pygame.Surface, model: ContrariModel) -> None:
        for p in model.particles:
            if p.kind == "sparkle":
                pygame.draw.circle(surf, p.color, (int(p.x), int(p.y)), max(1, int(p.size * p.life)))
            elif p.kind == "speedline":
                pygame.draw.line(surf, p.color, (int(p.x), int(p.y)), (int(p.x + p.size), int(p.y)), 3)
