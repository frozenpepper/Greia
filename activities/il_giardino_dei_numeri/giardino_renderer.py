"""Storybook visual renderer for Il Giardino dei Numeri."""

from __future__ import annotations

import math
from pathlib import Path

import pygame

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
    """Draws a warm, engaging, storybook toddler counting garden."""

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
                    img = pygame.image.load(str(path))
                    # Scale Dani to a friendly toddler-sized character (~170x170)
                    self._dani_images[mood] = pygame.transform.smoothscale(img, (170, 170))
                except Exception:
                    pass

    def render(self, model: GardenModel, anim_time: float) -> None:
        surf = self.canvas.surface

        # 1. Background sky, hills, fence and sunny meadow
        self._draw_background(surf, anim_time)

        # 2. Touch ripples from empty taps
        self._draw_ripples(surf, model.ripple_effects)

        # 3. Dani's picnic basket (grounded on grass)
        self._draw_basket(surf, model)

        # 4. Dani the Robot (standing on grass beside basket)
        self._draw_dani(surf, model, anim_time)

        # 5. Interactive countable items
        for item in model.items:
            self._draw_item(surf, item, anim_time)

        # 6. Top status / title banner
        self._draw_status(surf, model)

        # 7. Celebration sparkles when complete
        if model.celebrating:
            self._draw_celebration(surf, model, anim_time)

    def _draw_background(self, surf: pygame.Surface, anim_time: float) -> None:
        # Sky: soft pleasant toddler blue
        surf.fill((185, 225, 250))

        # Big warm smiling sun in top-right
        sun_x, sun_y = 930, 75
        pulse = 2.5 * math.sin(anim_time * 2.0)
        # Sun rays
        for i in range(12):
            angle = i * (math.pi / 6.0) + anim_time * 0.15
            rx1 = sun_x + math.cos(angle) * (52 + pulse)
            ry1 = sun_y + math.sin(angle) * (52 + pulse)
            rx2 = sun_x + math.cos(angle) * (66 + pulse)
            ry2 = sun_y + math.sin(angle) * (66 + pulse)
            pygame.draw.line(surf, (255, 230, 120), (int(rx1), int(ry1)), (int(rx2), int(ry2)), 4)
        pygame.draw.circle(surf, (255, 225, 90), (sun_x, sun_y), int(46 + pulse))
        pygame.draw.circle(surf, (255, 200, 50), (sun_x, sun_y), int(40 + pulse))

        # Soft drifting storybook clouds
        cloud_offsets = [
            (160.0 + (anim_time * 10.0) % 1150.0 - 120.0, 85.0, 1.0),
            (560.0 + (anim_time * 7.0) % 1150.0 - 120.0, 120.0, 0.85),
            (980.0 + (anim_time * 9.0) % 1150.0 - 120.0, 95.0, 0.75),
        ]
        for cx, cy, sc in cloud_offsets:
            c_rad = int(32 * sc)
            pygame.draw.circle(surf, (255, 255, 255), (int(cx), int(cy)), c_rad)
            pygame.draw.circle(surf, (255, 255, 255), (int(cx - 22 * sc), int(cy + 6 * sc)), int(24 * sc))
            pygame.draw.circle(surf, (255, 255, 255), (int(cx + 24 * sc), int(cy + 6 * sc)), int(26 * sc))
            pygame.draw.circle(surf, (255, 255, 255), (int(cx), int(cy + 10 * sc)), int(28 * sc))

        # Distant rolling hills (pastel sage green)
        pygame.draw.ellipse(surf, (160, 215, 135), (-120, 260, 750, 360))
        pygame.draw.ellipse(surf, (145, 205, 120), (320, 240, 850, 380))

        # Wooden garden fence posts along the horizon
        fence_y = 355
        for fx in range(60, REFERENCE_WIDTH - 40, 55):
            pygame.draw.rect(surf, (235, 210, 175), (fx, fence_y, 14, 55), border_radius=4)
            pygame.draw.polygon(surf, (235, 210, 175), [(fx, fence_y), (fx + 7, fence_y - 10), (fx + 14, fence_y)])
        pygame.draw.line(surf, (215, 190, 155), (40, fence_y + 18), (REFERENCE_WIDTH - 40, fence_y + 18), 5)
        pygame.draw.line(surf, (215, 190, 155), (40, fence_y + 38), (REFERENCE_WIDTH - 40, fence_y + 38), 5)

        # Foreground lush meadow ground
        pygame.draw.rect(surf, (120, 195, 80), (0, 390, REFERENCE_WIDTH, 210))

        # Gentle grass blades and daisies in foreground
        daisies = [(100, 540), (220, 480), (380, 560), (520, 490), (660, 550)]
        for dx, dy in daisies:
            # Grass blades
            pygame.draw.arc(surf, (90, 165, 55), (dx - 10, dy - 10, 20, 20), 0.5, 2.5, 3)
            pygame.draw.arc(surf, (90, 165, 55), (dx - 3, dy - 14, 20, 20), 0.8, 2.8, 3)
            # Daisy petals
            pygame.draw.circle(surf, (255, 255, 255), (dx, dy - 12), 4)
            pygame.draw.circle(surf, (255, 220, 60), (dx, dy - 12), 2)

    def _draw_ripples(self, surf: pygame.Surface, ripples: list[tuple[float, float, float]]) -> None:
        for rx, ry, age in ripples:
            alpha_ratio = max(0.0, 1.0 - (age / 0.6))
            radius = int(14 + age * 60)
            color = (255, 255, 255, int(180 * alpha_ratio))
            circle_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(circle_surf, color, (radius + 2, radius + 2), radius, width=4)
            surf.blit(circle_surf, (int(rx - radius - 2), int(ry - radius - 2)))

    def _draw_basket(self, surf: pygame.Surface, model: GardenModel) -> None:
        bx = int(BASKET_X)
        by = int(BASKET_Y)

        # Basket shadow grounded firmly on grass
        pygame.draw.ellipse(surf, (85, 145, 55), (bx - 65, by + 32, 130, 26))

        # Basket body (cozy warm woven basket)
        basket_rect = pygame.Rect(bx - 55, by - 10, 110, 50)
        pygame.draw.rect(surf, (215, 155, 90), basket_rect, border_radius=14)
        pygame.draw.rect(surf, (180, 120, 60), basket_rect, width=3, border_radius=14)

        # Cross weave pattern
        for ox in range(-40, 45, 16):
            pygame.draw.line(surf, (175, 115, 55), (bx + ox, by - 8), (bx + ox + 6, by + 36), 2)
            pygame.draw.line(surf, (175, 115, 55), (bx + ox + 6, by - 8), (bx + ox, by + 36), 2)

        # Red checkered cloth interior liner
        pygame.draw.ellipse(surf, (235, 75, 75), (bx - 48, by - 22, 96, 26))
        pygame.draw.ellipse(surf, (255, 255, 255), (bx - 42, by - 19, 84, 20), width=2)

        # Basket rim
        pygame.draw.ellipse(surf, (235, 180, 115), (bx - 58, by - 26, 116, 24))
        pygame.draw.ellipse(surf, (175, 115, 55), (bx - 58, by - 26, 116, 24), width=3)

        # Bright count badge on basket (e.g. 2/3)
        badge_rect = pygame.Rect(bx - 28, by + 12, 56, 30)
        pygame.draw.rect(surf, (255, 255, 255), badge_rect, border_radius=15)
        pygame.draw.rect(surf, (180, 120, 60), badge_rect, width=3, border_radius=15)
        num_str = f"{model.counted_count}/{model.target_count}"
        text_surf = self.typography.render(num_str, FontRole.TITLE, 18, (80, 45, 15))
        surf.blit(text_surf, text_surf.get_rect(center=badge_rect.center))

    def _draw_dani(self, surf: pygame.Surface, model: GardenModel, anim_time: float) -> None:
        # Dani stands on the meadow to the right of the basket
        dani_x = 910
        # When jumping with joy, offset vertically
        jump_offset = (
            -35.0 * math.sin(math.pi * min(1.0, (0.35 - model.dani_jump) / 0.35))
            if model.dani_jump > 0.0
            else 0.0
        )
        dani_y = 425 + jump_offset

        # Soft shadow under Dani on the ground
        shadow_scale = 1.0 - abs(jump_offset) / 60.0
        sw = int(90 * max(0.5, shadow_scale))
        sh = int(22 * max(0.5, shadow_scale))
        pygame.draw.ellipse(surf, (85, 145, 55), (dani_x - sw // 2, 495 - sh // 2, sw, sh))

        mood = model.dani_mood
        if mood not in self._dani_images:
            mood = "happy" if model.celebrating else "neutral"

        if mood in self._dani_images:
            img = self._dani_images[mood]
            # Gentle breathing motion
            breath_y = 2.5 * math.sin(anim_time * 3.0)
            surf.blit(img, (dani_x - img.get_width() // 2, int(dani_y - img.get_height() // 2 + breath_y)))
        else:
            # Fallback procedural body
            self._draw_procedural_dani(surf, dani_x, dani_y, mood, anim_time)

    def _draw_procedural_dani(
        self, surf: pygame.Surface, cx: float, cy: float, mood: str, anim_time: float
    ) -> None:
        head_rect = pygame.Rect(int(cx - 50), int(cy - 50), 100, 90)
        pygame.draw.rect(surf, (70, 195, 195), head_rect, border_radius=24)
        pygame.draw.rect(surf, (35, 145, 145), head_rect, width=4, border_radius=24)
        # Antenna
        pygame.draw.line(surf, (35, 145, 145), (int(cx), int(cy - 50)), (int(cx), int(cy - 78)), 5)
        pygame.draw.circle(surf, (255, 210, 50), (int(cx), int(cy - 82)), 12)
        # Screen
        face_rect = pygame.Rect(int(cx - 38), int(cy - 36), 76, 62)
        pygame.draw.rect(surf, (25, 45, 75), face_rect, border_radius=16)
        # Glowing eyes
        eye_col = (130, 235, 255)
        pygame.draw.circle(surf, eye_col, (int(cx - 18), int(cy - 6)), 8)
        pygame.draw.circle(surf, eye_col, (int(cx + 18), int(cy - 6)), 8)
        pygame.draw.arc(surf, eye_col, (int(cx - 14), int(cy + 4), 28, 16), 3.14, 6.28, 3)

    def _draw_item(self, surf: pygame.Surface, item: GardenItem, anim_time: float) -> None:
        cx, cy = item.current_pos

        # Bounce & wobble scaling
        scale = 1.0
        if item.pulse_timer > 0.0:
            scale = 1.0 + 0.38 * math.sin(math.pi * (item.pulse_timer / 0.5))
        elif item.giggle_timer > 0.0:
            scale = 1.0 + 0.18 * math.sin(math.pi * 4.0 * (item.giggle_timer / 0.3))
        else:
            scale = 1.0 + 0.04 * math.sin(anim_time * 2.5 + item.item_id)

        # Ground drop shadow while on the field
        if item.fly_progress <= 0.0:
            sw = int(72 * scale)
            sh = int(22 * scale)
            pygame.draw.ellipse(surf, (85, 145, 55), (int(cx - sw // 2), int(cy + 36 * scale), sw, sh))

        # Draw cute glowing backing circle
        backing_radius = int(48 * scale)
        backing_surf = pygame.Surface((backing_radius * 2 + 8, backing_radius * 2 + 8), pygame.SRCALPHA)
        bg_col = (255, 255, 255, 210) if not item.counted else (255, 245, 180, 240)
        border_col = (220, 200, 160) if not item.counted else (255, 180, 40)
        pygame.draw.circle(backing_surf, bg_col, (backing_radius + 4, backing_radius + 4), backing_radius)
        pygame.draw.circle(backing_surf, border_col, (backing_radius + 4, backing_radius + 4), backing_radius, width=3)
        surf.blit(backing_surf, (int(cx - backing_radius - 4), int(cy - backing_radius - 4)))

        # Render cute item emoji
        emoji_size = int(58 * scale)
        emoji_surf = self.typography.render(item.symbol, FontRole.DISPLAY, emoji_size, (40, 40, 40))
        surf.blit(emoji_surf, emoji_surf.get_rect(center=(int(cx), int(cy))))

        # Glowing Number Badge (shown when counted: 1, 2, 3...)
        if item.counted:
            self._draw_count_badge(surf, cx, cy - 42 * scale, item.order_counted)

    def _draw_count_badge(self, surf: pygame.Surface, cx: float, cy: float, count: int) -> None:
        badge_radius = 24
        # Glowing sunny badge
        pygame.draw.circle(surf, (255, 200, 40), (int(cx), int(cy)), badge_radius)
        pygame.draw.circle(surf, (255, 240, 120), (int(cx), int(cy)), badge_radius - 3)
        pygame.draw.circle(surf, (210, 130, 20), (int(cx), int(cy)), badge_radius, width=2)
        txt = self.typography.render(str(count), FontRole.DISPLAY, 26, (140, 50, 10))
        surf.blit(txt, txt.get_rect(center=(int(cx), int(cy))))

    def _draw_status(self, surf: pygame.Surface, model: GardenModel) -> None:
        # Title Banner in center (safe from top-left Home)
        banner_w, banner_h = 420, 54
        bx = (REFERENCE_WIDTH - banner_w) // 2
        by = 18

        pygame.draw.rect(surf, (255, 255, 255), (bx, by, banner_w, banner_h), border_radius=27)
        pygame.draw.rect(surf, (130, 195, 100), (bx, by, banner_w, banner_h), width=3, border_radius=27)

        if model.celebrating:
            title_text = self.resources.text("ui.well_done")
        else:
            title_text = self.resources.text("ui.touch_to_count")

        txt = self.typography.render(title_text, FontRole.TITLE, 24, (50, 120, 40))
        surf.blit(txt, txt.get_rect(center=(REFERENCE_WIDTH // 2, by + banner_h // 2)))

    def _draw_celebration(self, surf: pygame.Surface, model: GardenModel, anim_time: float) -> None:
        # Colorful celebration confetti & star bursts
        t = model.celebration_timer
        cx = int(BASKET_X)
        cy = int(BASKET_Y - 40)
        colors = [(255, 90, 90), (255, 210, 50), (90, 210, 120), (70, 170, 255), (220, 110, 240)]

        for i in range(24):
            angle = i * (2.0 * math.pi / 24.0) + (i * 0.2)
            speed = 80.0 + (i % 5) * 35.0
            dist = min(220.0, t * speed)
            px = cx + math.cos(angle) * dist
            py = cy + math.sin(angle) * dist + (t * 40.0)  # Gravity
            col = colors[i % len(colors)]
            size = max(3, int(8 - t * 2.0))
            pygame.draw.circle(surf, col, (int(px), int(py)), size)
