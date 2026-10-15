"""Visual renderer for Il Bosco dei Numeri di Tito."""

from __future__ import annotations

import math
from pathlib import Path

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .bosco_content import (
        CAROUSEL_ARROW_RADIUS,
        CAROUSEL_BUTTON_SIZE,
        CAROUSEL_NEXT_X,
        CAROUSEL_PREV_X,
        CAROUSEL_SPACING,
        CAROUSEL_START_X,
        CAROUSEL_Y,
        NUMBERS_1_TO_10,
    )
    from .bosco_model import BoscoModel, CountableForestItem
else:
    from bosco_content import (
        CAROUSEL_ARROW_RADIUS,
        CAROUSEL_BUTTON_SIZE,
        CAROUSEL_NEXT_X,
        CAROUSEL_PREV_X,
        CAROUSEL_SPACING,
        CAROUSEL_START_X,
        CAROUSEL_Y,
        NUMBERS_1_TO_10,
    )
    from bosco_model import BoscoModel, CountableForestItem

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TITO_ASSET_DIR = PROJECT_ROOT / "assets" / "visual" / "runtime" / "v1" / "characters"


class BoscoRenderer:
    """Renders the storybook forest glade and Ten-Frame visual math."""

    def __init__(
        self,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self._tito_images: dict[str, pygame.Surface] = {}
        self._load_character_assets()

    def _load_character_assets(self) -> None:
        moods = ["neutral", "happy", "surprised", "blink"]
        for mood in moods:
            path = TITO_ASSET_DIR / f"tito_{mood}.png"
            if path.is_file():
                try:
                    img = pygame.image.load(str(path))
                    self._tito_images[mood] = pygame.transform.smoothscale(img, (180, 180))
                except Exception:
                    pass

    def render(self, model: BoscoModel, anim_time: float) -> None:
        surf = self.canvas.surface

        # 1. Background forest clearing
        self._draw_forest_background(surf, anim_time)

        # 2. Touch ripples
        self._draw_ripples(surf, model.ripple_effects)

        # 3. Tito the Explorer Bear
        self._draw_tito(surf, model, anim_time)

        # 4. Mode-specific content
        if model.mode == "count":
            # Ten-frame counting rack
            self._draw_ten_frame(surf, model)
            # Countable items
            for item in model.items:
                self._draw_item(surf, item, anim_time)
            # Top number carousel (1..10)
            self._draw_number_carousel(surf, model)
        else:
            # Guess mode challenge cards
            self._draw_guess_challenge(surf, model, anim_time)

        # 5. Top mode toggle button
        self._draw_mode_toggle(surf, model)

        # 6. Celebration burst
        if model.celebrating:
            self._draw_celebration(surf, anim_time)

    def _draw_forest_background(self, surf: pygame.Surface, anim_time: float) -> None:
        # Warm sky gradient
        surf.fill((215, 242, 255))
        pygame.draw.rect(surf, (190, 230, 250), (0, 0, 1024, 180))

        # Distant soft clouds
        cloud_x = (anim_time * 12.0) % 1150 - 80
        pygame.draw.circle(surf, (255, 255, 255, 220), (int(cloud_x), 65), 38)
        pygame.draw.circle(surf, (255, 255, 255, 220), (int(cloud_x + 35), 55), 48)
        pygame.draw.circle(surf, (255, 255, 255, 220), (int(cloud_x + 75), 65), 36)

        # Distant green hills
        pygame.draw.ellipse(surf, (160, 215, 130), (-80, 140, 680, 360))
        pygame.draw.ellipse(surf, (140, 200, 110), (480, 150, 660, 340))

        # Main sunny forest glade
        pygame.draw.ellipse(surf, (120, 185, 85), (-60, 210, 1140, 520))

        # Woodland canopy leaves at top edges
        pygame.draw.ellipse(surf, (80, 150, 60), (-40, -40, 220, 120))
        pygame.draw.ellipse(surf, (95, 170, 70), (120, -50, 180, 100))
        pygame.draw.ellipse(surf, (80, 150, 60), (760, -45, 200, 110))
        pygame.draw.ellipse(surf, (95, 170, 70), (890, -40, 180, 120))

        # Tiny daisies in the grass
        flowers = [(130, 410), (280, 425), (420, 415), (710, 420), (850, 430)]
        for fx, fy in flowers:
            pygame.draw.circle(surf, (255, 255, 255), (fx, fy), 5)
            pygame.draw.circle(surf, (255, 220, 50), (fx, fy), 2)

    def _draw_tito(self, surf: pygame.Surface, model: BoscoModel, anim_time: float) -> None:
        tito_x = 905
        jump_offset = (
            -36.0 * math.sin(math.pi * min(1.0, (0.35 - model.tito_jump) / 0.35))
            if model.tito_jump > 0.0
            else 0.0
        )
        tito_y = 350 + jump_offset

        # Drop shadow on the meadow
        sw = int(96 * max(0.5, 1.0 - abs(jump_offset) / 60.0))
        sh = int(24 * max(0.5, 1.0 - abs(jump_offset) / 60.0))
        pygame.draw.ellipse(surf, (75, 135, 50), (tito_x - sw // 2, 430 - sh // 2, sw, sh))

        mood = model.tito_mood
        if mood not in self._tito_images:
            mood = "happy" if model.celebrating else "neutral"

        if mood in self._tito_images:
            img = self._tito_images[mood]
            breath_y = 2.5 * math.sin(anim_time * 3.0)
            surf.blit(img, (tito_x - img.get_width() // 2, int(tito_y - img.get_height() // 2 + breath_y)))

    def _draw_ten_frame(self, surf: pygame.Surface, model: BoscoModel) -> None:
        """Ten-Frame wooden rack with 2 rows of 5 slots."""
        frame_rect = pygame.Rect(180, 420, 580, 160)
        # Wooden backing
        pygame.draw.rect(surf, (215, 165, 105), frame_rect, border_radius=20)
        pygame.draw.rect(surf, (150, 95, 45), frame_rect, width=4, border_radius=20)

        # Slot definitions
        start_x = 240.0
        slot_spacing_x = 95.0
        row_y_top = 460.0
        row_y_bottom = 530.0

        for idx in range(10):
            row = 0 if idx < 5 else 1
            col = idx % 5
            sx = int(start_x + col * slot_spacing_x)
            sy = int(row_y_top if row == 0 else row_y_bottom)

            slot_rect = pygame.Rect(sx - 38, sy - 28, 76, 56)
            # Indented slot
            pygame.draw.rect(surf, (185, 135, 80), slot_rect, border_radius=12)
            pygame.draw.rect(surf, (135, 85, 35), slot_rect, width=2, border_radius=12)

            # Slot number label (1..10)
            num_label = str(idx + 1)
            text_surf = self.typography.render(num_label, FontRole.BODY, 16, (140, 95, 50))
            surf.blit(text_surf, text_surf.get_rect(center=(sx, sy)))

        # Progress counter badge on the left of the rack
        badge_rect = pygame.Rect(95, 465, 75, 70)
        pygame.draw.rect(surf, (255, 255, 255), badge_rect, border_radius=16)
        pygame.draw.rect(surf, (75, 150, 45), badge_rect, width=3, border_radius=16)
        c_surf = self.typography.render(
            f"{model.counted_count}", FontRole.TITLE, 28, (45, 110, 25)
        )
        surf.blit(c_surf, c_surf.get_rect(center=(badge_rect.centerx, badge_rect.centery - 12)))
        tot_surf = self.typography.render(
            f"/ {model.current_number}", FontRole.SECONDARY, 14, (100, 100, 100)
        )
        surf.blit(tot_surf, tot_surf.get_rect(center=(badge_rect.centerx, badge_rect.centery + 16)))

    def _draw_item(self, surf: pygame.Surface, item: CountableForestItem, anim_time: float) -> None:
        cx, cy = item.current_pos
        scale = 1.0
        if item.pulse_timer > 0.0:
            scale = 1.0 + 0.35 * math.sin(math.pi * (item.pulse_timer / 0.5))
        elif item.giggle_timer > 0.0:
            scale = 1.0 + 0.16 * math.sin(math.pi * 4.0 * (item.giggle_timer / 0.3))
        elif not item.counted:
            scale = 1.0 + 0.05 * math.sin(anim_time * 2.5 + item.item_id)

        # Ground shadow if in clearing
        if item.fly_progress <= 0.0:
            sw = int(64 * scale)
            sh = int(20 * scale)
            pygame.draw.ellipse(surf, (75, 135, 50), (int(cx - sw // 2), int(cy + 30 * scale), sw, sh))

        # Circular glowing badge
        radius = int(item.radius * scale)
        backing_surf = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
        bcx, bcy = radius + 5, radius + 5

        # Glowing border
        pygame.draw.circle(backing_surf, (255, 255, 255, 230), (bcx, bcy), radius)
        ring_col = (75, 175, 55) if not item.counted else (255, 195, 45)
        pygame.draw.circle(backing_surf, ring_col, (bcx, bcy), radius, width=3)
        surf.blit(backing_surf, (int(cx - bcx), int(cy - bcy)))

        # Emoji symbol
        sym = item.kind.symbol
        font_size = int(38 * scale)
        emoji_surf = self.typography.render(sym, FontRole.TITLE, font_size, (20, 20, 20))
        surf.blit(emoji_surf, emoji_surf.get_rect(center=(int(cx), int(cy))))

        # Order number badge on placed items in the Ten-Frame
        if item.counted:
            order_badge = pygame.Rect(int(cx + 12), int(cy - 26), 22, 22)
            pygame.draw.circle(surf, (255, 180, 30), order_badge.center, 12)
            pygame.draw.circle(surf, (255, 255, 255), order_badge.center, 12, width=2)
            order_txt = self.typography.render(str(item.order_counted), FontRole.SECONDARY, 12, (255, 255, 255))
            surf.blit(order_txt, order_txt.get_rect(center=order_badge.center))

    def _draw_number_carousel(self, surf: pygame.Surface, model: BoscoModel) -> None:
        """Top bar displaying numbers 1 to 10 with Prev/Next arrows."""
        y = CAROUSEL_Y
        radius = CAROUSEL_ARROW_RADIUS
        half = CAROUSEL_BUTTON_SIZE // 2

        # Left chevron arrow button
        pygame.draw.circle(surf, (255, 255, 255), (CAROUSEL_PREV_X, y), radius)
        pygame.draw.circle(surf, (120, 80, 40), (CAROUSEL_PREV_X, y), radius, width=3)
        pygame.draw.polygon(
            surf,
            (100, 65, 30),
            [(CAROUSEL_PREV_X + 6, y - 12), (CAROUSEL_PREV_X - 10, y), (CAROUSEL_PREV_X + 6, y + 12)],
        )

        # Number pill buttons 1 to 10
        for idx in range(10):
            num = idx + 1
            btn_x = CAROUSEL_START_X + idx * CAROUSEL_SPACING
            is_active = num == model.current_number

            rect = pygame.Rect(btn_x - half, y - half, CAROUSEL_BUTTON_SIZE, CAROUSEL_BUTTON_SIZE)
            bg_col = (255, 215, 60) if is_active else (255, 255, 255)
            border_col = (195, 125, 20) if is_active else (180, 180, 180)
            text_col = (90, 50, 10) if is_active else (80, 80, 80)

            pygame.draw.rect(surf, bg_col, rect, border_radius=16)
            pygame.draw.rect(surf, border_col, rect, width=3 if is_active else 2, border_radius=16)

            txt = self.typography.render(str(num), FontRole.TITLE, 22 if is_active else 18, text_col)
            surf.blit(txt, txt.get_rect(center=rect.center))

        # Right chevron arrow button
        pygame.draw.circle(surf, (255, 255, 255), (CAROUSEL_NEXT_X, y), radius)
        pygame.draw.circle(surf, (120, 80, 40), (CAROUSEL_NEXT_X, y), radius, width=3)
        pygame.draw.polygon(
            surf,
            (100, 65, 30),
            [(CAROUSEL_NEXT_X - 6, y - 12), (CAROUSEL_NEXT_X + 10, y), (CAROUSEL_NEXT_X - 6, y + 12)],
        )

    def _draw_mode_toggle(self, surf: pygame.Surface, model: BoscoModel) -> None:
        """Draw the localized mode-switch control."""
        toggle_rect = pygame.Rect(870, 30, 135, 45)
        pygame.draw.rect(surf, (255, 255, 255), toggle_rect, border_radius=22)
        pygame.draw.rect(surf, (100, 160, 60), toggle_rect, width=3, border_radius=22)

        key = "ui.mode_guess" if model.mode == "count" else "ui.mode_count"
        mode_text = self.resources.text(key)
        txt = self.typography.render(mode_text, FontRole.CONTROL, 18, (50, 110, 30))
        surf.blit(txt, txt.get_rect(center=toggle_rect.center))

    def _draw_guess_challenge(self, surf: pygame.Surface, model: BoscoModel, anim_time: float) -> None:
        """Prompt and 3 large cards for the find-the-number game."""
        instr = self.resources.text("ui.guess_prompt", {"num": model.guess_target})
        banner_rect = pygame.Rect(260, 80, 460, 60)
        pygame.draw.rect(surf, (255, 255, 255), banner_rect, border_radius=24)
        pygame.draw.rect(surf, (255, 175, 45), banner_rect, width=4, border_radius=24)
        b_txt = self.typography.render(instr, FontRole.TITLE, 26, (120, 65, 15))
        surf.blit(b_txt, b_txt.get_rect(center=banner_rect.center))

        # 3 Cards
        card_xs = [280, 490, 700]
        for idx, num in enumerate(model.guess_options):
            cx = card_xs[idx]
            cy = 280

            wobble = 0.0
            if model.guess_wobble_card == num:
                wobble = 14.0 * math.sin(anim_time * 24.0)

            card_rect = pygame.Rect(int(cx - 75 + wobble), cy - 90, 150, 180)
            is_target_and_solved = model.guess_solved and num == model.guess_target
            bg = (255, 245, 175) if is_target_and_solved else (255, 255, 255)
            border = (65, 180, 65) if is_target_and_solved else (220, 140, 45)

            pygame.draw.rect(surf, bg, card_rect, border_radius=28)
            pygame.draw.rect(surf, border, card_rect, width=5, border_radius=28)

            # Big numeral
            num_surf = self.typography.render(str(num), FontRole.DISPLAY, 58, (80, 45, 15))
            surf.blit(num_surf, num_surf.get_rect(center=(card_rect.centerx, card_rect.centery - 20)))

            # Matching symbol icon
            sym = NUMBERS_1_TO_10[num - 1].kind.symbol
            sym_surf = self.typography.render(sym, FontRole.TITLE, 30, (20, 20, 20))
            surf.blit(sym_surf, sym_surf.get_rect(center=(card_rect.centerx, card_rect.centery + 45)))

    def _draw_celebration(self, surf: pygame.Surface, anim_time: float) -> None:
        """Sparkles and rainbow confetti on full count completion."""
        for i in range(24):
            ang = i * (2.0 * math.pi / 24.0) + anim_time * 1.5
            dist = 90.0 + 60.0 * math.sin(anim_time * 3.0 + i)
            sx = int(480 + dist * math.cos(ang))
            sy = int(280 + dist * math.sin(ang) * 0.7)
            col = (255, 215, 50) if i % 2 == 0 else (255, 95, 125)
            pygame.draw.circle(surf, col, (sx, sy), 7)

    def _draw_ripples(self, surf: pygame.Surface, ripples: list[tuple[float, float, float]]) -> None:
        for x, y, age in ripples:
            radius = int(8 + age * 80)
            alpha = max(0, int(220 * (1.0 - age / 0.4)))
            rip_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(rip_surf, (255, 255, 255, alpha), (radius + 2, radius + 2), radius, width=3)
            surf.blit(rip_surf, (int(x - radius - 2), int(y - radius - 2)))
