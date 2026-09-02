"""Renderer for Il Giardino dei Numeri."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.child_text import display_text
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .giardino_model import (
        BASKET_RADIUS,
        BASKET_X,
        BASKET_Y,
        GardenItem,
        GardenModel,
        ItemKind,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
else:
    from giardino_model import (
        BASKET_RADIUS,
        BASKET_X,
        BASKET_Y,
        GardenItem,
        GardenModel,
        ItemKind,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DANI_ASSET_DIR = PROJECT_ROOT / "assets" / "visual" / "runtime" / "v1" / "characters"


class GiardinoRenderer:
    """Draws the sunny toddler counting garden."""

    def __init__(
        self,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self._dani_images: dict[str, pygame.Surface] = {}
        self._load_character_assets()

    def _load_character_assets(self) -> None:
        moods = ["neutral", "happy", "surprised", "blink"]
        for mood in moods:
            path = DANI_ASSET_DIR / f"dani_{mood}.png"
            if path.is_file():
                try:
                    img = pygame.image.load(str(path)).convert_alpha()
                    # Scale Dani nicely for toddler view (~150x150)
                    self._dani_images[mood] = pygame.transform.smoothscale(img, (150, 150))
                except Exception:
                    pass

    def render(self, model: GardenModel, anim_time: float) -> None:
        surf = self.canvas.surface

        # 1. Background sky and sunny meadow
        self._draw_background(surf, anim_time)

        # 2. Touch ripples
        self._draw_ripples(surf, model.ripple_effects)

        # 3. Dani's basket
        self._draw_basket(surf, model)

        # 4. Dani the Robot
        self._draw_dani(surf, model, anim_time)

        # 5. Countable garden items
        for item in model.items:
            self._draw_item(surf, item, anim_time)

        # 6. Top status / prompt (visual and capital text)
        self._draw_status(surf, model)

        # 7. Celebration overlay and sparkles
        if model.celebrating:
            self._draw_celebration(surf, model, anim_time)

    def _draw_background(self, surf: pygame.Surface, anim_time: float) -> None:
        # Sky gradient / pastel sky
        surf.fill((190, 230, 255))

        # Drifting soft clouds
        cloud_offsets = [
            (200.0 + (anim_time * 12.0) % 1100.0 - 100.0, 90.0),
            (650.0 + (anim_time * 8.0) % 1100.0 - 100.0, 130.0),
        ]
        for cx, cy in cloud_offsets:
            pygame.draw.circle(surf, (245, 250, 255), (int(cx), int(cy)), 36)
            pygame.draw.circle(surf, (245, 250, 255), (int(cx - 24), int(cy + 6)), 26)
            pygame.draw.circle(surf, (245, 250, 255), (int(cx + 26), int(cy + 6)), 28)
            pygame.draw.circle(surf, (245, 250, 255), (int(cx), int(cy + 10)), 32)

        # Warm smiling sun in top-right
        sun_x, sun_y = 940, 80
        pulse = 2.0 * math.sin(anim_time * 2.5)
        pygame.draw.circle(surf, (255, 230, 110), (sun_x, sun_y), int(48 + pulse))
        pygame.draw.circle(surf, (255, 205, 70), (sun_x, sun_y), int(42 + pulse))

        # Soft rolling grassy hills
        # Distant hill
        pygame.draw.ellipse(surf, (150, 215, 120), (-100, 310, 800, 400))
        # Foreground hill
        pygame.draw.ellipse(surf, (130, 200, 95), (250, 280, 900, 440))
        # Ground base
        pygame.draw.rect(surf, (120, 195, 85), (0, 420, REFERENCE_WIDTH, 180))

        # Gentle grass tufts
        tufts = [(120, 520), (280, 490), (450, 530), (620, 480), (760, 540)]
        for tx, ty in tufts:
            pygame.draw.arc(surf, (95, 170, 65), (tx - 12, ty - 12, 24, 24), 0.5, 2.5, 3)
            pygame.draw.arc(surf, (95, 170, 65), (tx - 4, ty - 16, 24, 24), 0.8, 2.8, 3)

    def _draw_ripples(self, surf: pygame.Surface, ripples: list[tuple[float, float, float]]) -> None:
        for rx, ry, age in ripples:
            alpha_ratio = max(0.0, 1.0 - (age / 0.6))
            radius = int(12 + age * 65)
            color = (255, 255, 255, int(160 * alpha_ratio))
            # Draw anti-aliased expanding circle
            circle_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(
                circle_surf,
                (255, 255, 220, int(150 * alpha_ratio)),
                (radius + 2, radius + 2),
                radius,
                width=3,
            )
            surf.blit(circle_surf, (int(rx - radius - 2), int(ry - radius - 2)))

    def _draw_basket(self, surf: pygame.Surface, model: GardenModel) -> None:
        bx, by = int(BASKET_X), int(BASKET_Y)
        # Basket shadow
        pygame.draw.ellipse(surf, (80, 140, 55), (bx - 70, by + 45, 140, 30))

        # Basket body (warm wicker basket)
        basket_rect = pygame.Rect(bx - 60, by - 15, 120, 65)
        pygame.draw.ellipse(surf, (210, 150, 85), basket_rect)
        pygame.draw.rect(surf, (190, 130, 70), (bx - 55, by, 110, 45), border_radius=12)

        # Wicker cross stripes
        for ox in range(-40, 50, 20):
            pygame.draw.line(surf, (165, 105, 50), (bx + ox, by), (bx + ox + 8, by + 42), 2)
            pygame.draw.line(surf, (165, 105, 50), (bx + ox + 8, by), (bx + ox, by + 42), 2)

        # Basket rim
        pygame.draw.ellipse(surf, (230, 175, 105), (bx - 62, by - 18, 124, 28))
        pygame.draw.ellipse(surf, (170, 110, 55), (bx - 62, by - 18, 124, 28), width=3)

        # Checkered cloth rim
        pygame.draw.ellipse(surf, (240, 80, 80), (bx - 45, by - 12, 90, 16))

        # Count badge on basket
        badge_rect = pygame.Rect(bx - 26, by + 18, 52, 28)
        pygame.draw.rect(surf, (255, 255, 255), badge_rect, border_radius=14)
        pygame.draw.rect(surf, (190, 130, 70), badge_rect, width=2, border_radius=14)
        num_str = f"{model.counted_count}/{model.target_count}"
        text_surf = self.typography.render(num_str, FontRole.SECONDARY, 18, (80, 50, 20))
        surf.blit(text_surf, text_surf.get_rect(center=badge_rect.center))

    def _draw_dani(self, surf: pygame.Surface, model: GardenModel, anim_time: float) -> None:
        # Dani position: right side, next to basket
        dani_x = 880
        jump_offset = -30.0 * math.sin(math.pi * min(1.0, (0.35 - model.dani_jump) / 0.35)) if model.dani_jump > 0.0 else 0.0
        dani_y = 290 + jump_offset

        # Check if runtime PNG is available
        mood = model.dani_mood
        if mood not in self._dani_images:
            mood = "neutral"

        if mood in self._dani_images:
            img = self._dani_images[mood]
            # Add gentle breathing wobble
            wobble_y = 3.0 * math.sin(anim_time * 3.0)
            surf.blit(img, (dani_x - 75, int(dani_y - 75 + wobble_y)))
        else:
            # Procedural fallback for Dani
            self._draw_procedural_dani(surf, dani_x, dani_y + jump_offset, mood, anim_time)

    def _draw_procedural_dani(
        self, surf: pygame.Surface, cx: float, cy: float, mood: str, anim_time: float
    ) -> None:
        # Head (rounded teal/mint rectangle)
        head_rect = pygame.Rect(int(cx - 45), int(cy - 40), 90, 80)
        pygame.draw.rect(surf, (70, 190, 190), head_rect, border_radius=20)
        pygame.draw.rect(surf, (40, 140, 140), head_rect, width=3, border_radius=20)

        # Antenna with glowing tip
        antenna_glow = (255, 230, 80) if mood in ("happy", "surprised") else (255, 190, 60)
        pygame.draw.line(surf, (40, 140, 140), (int(cx), int(cy - 40)), (int(cx), int(cy - 65)), 4)
        pygame.draw.circle(surf, antenna_glow, (int(cx), int(cy - 68)), 10)

        # Face screen (soft dark blue)
        face_rect = pygame.Rect(int(cx - 35), int(cy - 28), 70, 56)
        pygame.draw.rect(surf, (25, 45, 75), face_rect, border_radius=12)

        # Eyes (digital light blue)
        eye_color = (130, 230, 255)
        if mood == "blink":
            pygame.draw.line(surf, eye_color, (int(cx - 22), int(cy)), (int(cx - 8), int(cy)), 3)
            pygame.draw.line(surf, eye_color, (int(cx + 8), int(cy)), (int(cx + 22), int(cy)), 3)
        elif mood == "happy":
            # Curved happy eyes
            pygame.draw.arc(surf, eye_color, (int(cx - 24), int(cy - 12), 18, 18), 0.2, 2.9, 3)
            pygame.draw.arc(surf, eye_color, (int(cx + 6), int(cy - 12), 18, 18), 0.2, 2.9, 3)
        else:
            # Round glowing eyes
            pygame.draw.circle(surf, eye_color, (int(cx - 15), int(cy - 2)), 6)
            pygame.draw.circle(surf, eye_color, (int(cx + 15), int(cy - 2)), 6)

        # Smile
        pygame.draw.arc(surf, eye_color, (int(cx - 10), int(cy + 6), 20, 12), 3.14, 6.28, 2)

    def _draw_item(self, surf: pygame.Surface, item: GardenItem, anim_time: float) -> None:
        cx, cy = item.current_pos

        # Wobble / pulse scaling
        scale = 1.0
        if item.pulse_timer > 0.0:
            # Big tactile bounce
            scale = 1.0 + 0.35 * math.sin(math.pi * (item.pulse_timer / 0.5))
        elif item.giggle_timer > 0.0:
            scale = 1.0 + 0.15 * math.sin(math.pi * 4.0 * (item.giggle_timer / 0.3))
        else:
            # Soft idling float
            scale = 1.0 + 0.04 * math.sin(anim_time * 2.5 + item.item_id)

        # Item shadow on ground
        if item.fly_progress <= 0.0:
            shadow_w = int(item.radius * 1.5 * scale)
            shadow_h = int(item.radius * 0.5 * scale)
            pygame.draw.ellipse(
                surf,
                (90, 160, 65),
                (int(cx - shadow_w * 0.5), int(cy + item.radius * 0.7), shadow_w, shadow_h),
            )

        # Draw specific item shape
        radius = item.radius * scale
        if item.kind == ItemKind.APPLE:
            self._draw_apple(surf, cx, cy, radius)
        elif item.kind == ItemKind.STRAWBERRY:
            self._draw_strawberry(surf, cx, cy, radius)
        elif item.kind == ItemKind.FLOWER:
            self._draw_flower(surf, cx, cy, radius, anim_time)
        elif item.kind == ItemKind.BUTTERFLY:
            self._draw_butterfly(surf, cx, cy, radius, anim_time)
        elif item.kind == ItemKind.DUCKLING:
            self._draw_duckling(surf, cx, cy, radius)
        else:
            self._draw_star(surf, cx, cy, radius, anim_time)

        # Number Badge (Appears when item is counted)
        if item.counted:
            self._draw_count_badge(surf, cx, cy - radius * 0.9, item.order_counted)

    def _draw_apple(self, surf: pygame.Surface, cx: float, cy: float, r: float) -> None:
        # Stem
        pygame.draw.arc(surf, (110, 70, 30), (int(cx - 8), int(cy - r * 1.4), 16, int(r * 0.9)), 0.5, 2.2, 4)
        # Leaf
        pygame.draw.ellipse(surf, (70, 180, 50), (int(cx + 2), int(cy - r * 1.25), int(r * 0.6), int(r * 0.35)))
        # Body (two slightly overlapping red spheres for cute apple dip)
        pygame.draw.circle(surf, (235, 55, 55), (int(cx - r * 0.3), int(cy)), int(r * 0.8))
        pygame.draw.circle(surf, (235, 55, 55), (int(cx + r * 0.3), int(cy)), int(r * 0.8))
        # Specular shine
        pygame.draw.ellipse(surf, (255, 150, 150), (int(cx - r * 0.6), int(cy - r * 0.5), int(r * 0.35), int(r * 0.2)))
        # Cheerful face dots
        pygame.draw.circle(surf, (70, 20, 20), (int(cx - r * 0.2), int(cy + 2)), 3)
        pygame.draw.circle(surf, (70, 20, 20), (int(cx + r * 0.2), int(cy + 2)), 3)
        pygame.draw.arc(surf, (70, 20, 20), (int(cx - r * 0.15), int(cy + 4), int(r * 0.3), int(r * 0.2)), 3.14, 6.28, 2)

    def _draw_strawberry(self, surf: pygame.Surface, cx: float, cy: float, r: float) -> None:
        # Berry body
        pts = [
            (cx, cy + r * 1.05),
            (cx - r * 0.85, cy - r * 0.3),
            (cx - r * 0.5, cy - r * 0.8),
            (cx + r * 0.5, cy - r * 0.8),
            (cx + r * 0.85, cy - r * 0.3),
        ]
        pygame.draw.polygon(surf, (240, 45, 65), [(int(x), int(y)) for x, y in pts])
        pygame.draw.circle(surf, (240, 45, 65), (int(cx), int(cy - r * 0.3)), int(r * 0.75))

        # Green leafy crown
        crown_pts = [
            (cx - r * 0.7, cy - r * 0.75),
            (cx - r * 0.2, cy - r * 0.55),
            (cx, cy - r * 0.95),
            (cx + r * 0.2, cy - r * 0.55),
            (cx + r * 0.7, cy - r * 0.75),
            (cx, cy - r * 0.6),
        ]
        pygame.draw.polygon(surf, (65, 175, 55), [(int(x), int(y)) for x, y in crown_pts])

        # Seeds
        seeds = [(-0.3, 0.0), (0.3, 0.0), (0.0, 0.3), (-0.2, 0.5), (0.2, 0.5)]
        for sx, sy in seeds:
            pygame.draw.circle(surf, (255, 240, 140), (int(cx + sx * r), int(cy + sy * r)), 2)

    def _draw_flower(self, surf: pygame.Surface, cx: float, cy: float, r: float, anim_time: float) -> None:
        # Petals (soft sunny daisy)
        petal_color = (255, 235, 100)
        num_petals = 6
        for i in range(num_petals):
            ang = (i / num_petals) * 2 * math.pi
            px = cx + math.cos(ang) * (r * 0.55)
            py = cy + math.sin(ang) * (r * 0.55)
            pygame.draw.circle(surf, petal_color, (int(px), int(py)), int(r * 0.42))
        # Orange/yellow center
        pygame.draw.circle(surf, (255, 160, 40), (int(cx), int(cy)), int(r * 0.46))
        # Smiling center
        pygame.draw.circle(surf, (80, 40, 10), (int(cx - r * 0.15), int(cy - 2)), 3)
        pygame.draw.circle(surf, (80, 40, 10), (int(cx + r * 0.15), int(cy - 2)), 3)
        pygame.draw.arc(surf, (80, 40, 10), (int(cx - r * 0.15), int(cy), int(r * 0.3), int(r * 0.2)), 3.14, 6.28, 2)

    def _draw_butterfly(self, surf: pygame.Surface, cx: float, cy: float, r: float, anim_time: float) -> None:
        # Flap angle
        flap = 0.85 + 0.15 * math.sin(anim_time * 6.0)
        wing_color = (130, 200, 255)
        # Upper wings
        pygame.draw.ellipse(surf, wing_color, (int(cx - r * 0.95 * flap), int(cy - r * 0.8), int(r * 0.9 * flap), int(r * 0.9)))
        pygame.draw.ellipse(surf, wing_color, (int(cx + r * 0.05), int(cy - r * 0.8), int(r * 0.9 * flap), int(r * 0.9)))
        # Lower wings
        pygame.draw.ellipse(surf, (160, 220, 255), (int(cx - r * 0.75 * flap), int(cy - r * 0.1), int(r * 0.7 * flap), int(r * 0.7)))
        pygame.draw.ellipse(surf, (160, 220, 255), (int(cx + r * 0.05), int(cy - r * 0.1), int(r * 0.7 * flap), int(r * 0.7)))
        # Body
        pygame.draw.ellipse(surf, (100, 70, 150), (int(cx - r * 0.15), int(cy - r * 0.7), int(r * 0.3), int(r * 1.2)))
        # Antennae
        pygame.draw.line(surf, (80, 50, 120), (int(cx - 3), int(cy - r * 0.6)), (int(cx - r * 0.4), int(cy - r * 0.95)), 2)
        pygame.draw.line(surf, (80, 50, 120), (int(cx + 3), int(cy - r * 0.6)), (int(cx + r * 0.4), int(cy - r * 0.95)), 2)

    def _draw_duckling(self, surf: pygame.Surface, cx: float, cy: float, r: float) -> None:
        # Body
        pygame.draw.ellipse(surf, (255, 220, 50), (int(cx - r * 0.8), int(cy - r * 0.2), int(r * 1.5), int(r * 1.0)))
        # Head
        pygame.draw.circle(surf, (255, 230, 60), (int(cx - r * 0.3), int(cy - r * 0.45)), int(r * 0.55))
        # Beak
        pygame.draw.polygon(surf, (255, 140, 30), [(int(cx - r * 0.75), int(cy - r * 0.45)), (int(cx - r * 1.15), int(cy - r * 0.4)), (int(cx - r * 0.75), int(cy - r * 0.25))])
        # Eye
        pygame.draw.circle(surf, (30, 30, 30), (int(cx - r * 0.4), int(cy - r * 0.5)), 4)
        pygame.draw.circle(surf, (255, 255, 255), (int(cx - r * 0.42), int(cy - r * 0.52)), 1)
        # Wing
        pygame.draw.ellipse(surf, (245, 205, 30), (int(cx - r * 0.2), int(cy - r * 0.05), int(r * 0.75), int(r * 0.55)))

    def _draw_star(self, surf: pygame.Surface, cx: float, cy: float, r: float, anim_time: float) -> None:
        pts = []
        outer_r = r * 1.0
        inner_r = r * 0.45
        rot = anim_time * 0.8
        for i in range(10):
            cur_r = outer_r if i % 2 == 0 else inner_r
            ang = rot + (i / 10.0) * 2 * math.pi - math.pi * 0.5
            pts.append((cx + math.cos(ang) * cur_r, cy + math.sin(ang) * cur_r))
        pygame.draw.polygon(surf, (255, 225, 60), [(int(x), int(y)) for x, y in pts])
        pygame.draw.polygon(surf, (245, 185, 30), [(int(x), int(y)) for x, y in pts], width=3)
        # Face
        pygame.draw.circle(surf, (60, 40, 10), (int(cx - r * 0.2), int(cy - 2)), 3)
        pygame.draw.circle(surf, (60, 40, 10), (int(cx + r * 0.2), int(cy - 2)), 3)
        pygame.draw.arc(surf, (60, 40, 10), (int(cx - r * 0.15), int(cy), int(r * 0.3), int(r * 0.2)), 3.14, 6.28, 2)

    def _draw_count_badge(self, surf: pygame.Surface, bx: float, by: float, number: int) -> None:
        badge_r = 24
        # Glowing outer halo
        pygame.draw.circle(surf, (255, 255, 255), (int(bx), int(by)), badge_r + 4)
        pygame.draw.circle(surf, (255, 180, 50), (int(bx), int(by)), badge_r)
        pygame.draw.circle(surf, (255, 245, 140), (int(bx), int(by)), badge_r - 3)

        # Bold Capital Numeral
        num_surf = self.typography.render(str(number), FontRole.TITLE, 28, (130, 40, 10))
        surf.blit(num_surf, num_surf.get_rect(center=(int(bx), int(by))))

    def _draw_status(self, surf: pygame.Surface, model: GardenModel) -> None:
        # Central toddler banner: large, cheerful, capitals
        # Positioned at top-center, safely away from top-left Home/Back area
        bar_w = 420
        bar_h = 56
        bar_x = (REFERENCE_WIDTH - bar_w) // 2
        bar_y = 20

        pygame.draw.rect(surf, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), border_radius=28)
        pygame.draw.rect(surf, (150, 210, 100), (bar_x, bar_y, bar_w, bar_h), width=3, border_radius=28)

        # Spoken / display prompt
        remaining = model.target_count - model.counted_count
        if model.celebrating:
            msg = self.resources.text("ui.well_done")
        elif model.counted_count == 0:
            msg = self.resources.text("ui.touch_to_count")
        else:
            msg = self.resources.text("ui.keep_counting")

        text_surf = self.typography.render(msg, FontRole.TITLE, 24, (45, 120, 35))
        surf.blit(text_surf, text_surf.get_rect(center=(REFERENCE_WIDTH // 2, bar_y + bar_h // 2)))

    def _draw_celebration(self, surf: pygame.Surface, model: GardenModel, anim_time: float) -> None:
        # Celebration banner + gentle floating stars
        for i in range(12):
            ang = (i / 12.0) * 2 * math.pi + anim_time * 2.0
            dist = 160 + 35 * math.sin(anim_time * 3.0 + i)
            sx = int(BASKET_X + math.cos(ang) * dist)
            sy = int(BASKET_Y + math.sin(ang) * dist * 0.7)
            star_size = int(8 + 4 * math.sin(anim_time * 5.0 + i))
            pygame.draw.circle(surf, (255, 240, 100), (sx, sy), star_size)

        # Large forward button for manual continue
        btn_w, btn_h = 220, 64
        btn_x = (REFERENCE_WIDTH - btn_w) // 2
        btn_y = 510
        pulse = 4.0 * math.sin(anim_time * 4.0)

        btn_rect = pygame.Rect(int(btn_x - pulse), int(btn_y - pulse * 0.5), int(btn_w + pulse * 2), int(btn_h + pulse))
        pygame.draw.rect(surf, (255, 200, 50), btn_rect, border_radius=32)
        pygame.draw.rect(surf, (255, 255, 255), btn_rect, width=4, border_radius=32)

        cont_msg = self.resources.text("ui.next")
        txt = self.typography.render(cont_msg, FontRole.TITLE, 24, (110, 50, 10))
        surf.blit(txt, txt.get_rect(center=btn_rect.center))
