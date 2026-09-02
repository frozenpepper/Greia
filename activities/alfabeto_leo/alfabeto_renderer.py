"""Renderer for L'Alfabeto di Leo (Toddler Alphabet Activity)."""

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
    from .alfabeto_model import (
        AlfabetoModel,
        GameMode,
        LETTERS_CATALOGUE,
        LetterItem,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
else:
    from alfabeto_model import (
        AlfabetoModel,
        GameMode,
        LETTERS_CATALOGUE,
        LetterItem,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEO_ASSET_DIR = PROJECT_ROOT / "assets" / "visual" / "runtime" / "v1" / "characters"


class AlfabetoRenderer:
    """Renders Leo's cozy alphabet treehouse and letter cards."""

    def __init__(
        self,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self._leo_images: dict[str, pygame.Surface] = {}
        self._load_character_assets()

    def _load_character_assets(self) -> None:
        moods = ["neutral", "happy", "surprised", "blink"]
        for mood in moods:
            path = LEO_ASSET_DIR / f"leo_{mood}.png"
            if path.is_file():
                try:
                    img = pygame.image.load(str(path)).convert_alpha()
                    self._leo_images[mood] = pygame.transform.smoothscale(img, (140, 140))
                except Exception:
                    pass

    def render(self, model: AlfabetoModel, anim_time: float) -> None:
        surf = self.canvas.surface

        # 1. Background cozy treehouse
        self._draw_background(surf, anim_time)

        # 2. Leo the Owl
        self._draw_leo(surf, model, anim_time)

        # 3. Top controls & Mode switcher
        self._draw_top_bar(surf, model)

        # 4. Mode-specific content
        if model.mode == GameMode.EXPLORE:
            self._draw_explore_mode(surf, model, anim_time)
        else:
            self._draw_guess_mode(surf, model, anim_time)

        # 5. Celebration sparkles
        if model.celebrating:
            self._draw_celebration_effects(surf, anim_time)

    def _draw_background(self, surf: pygame.Surface, anim_time: float) -> None:
        # Cozy warm parchment / honey wood background
        surf.fill((252, 246, 235))

        # Soft window to sunny sky in background
        window_rect = pygame.Rect(720, 40, 240, 180)
        pygame.draw.rect(surf, (195, 230, 255), window_rect, border_radius=24)
        pygame.draw.rect(surf, (220, 175, 125), window_rect, width=6, border_radius=24)
        # Gentle sun in window
        pygame.draw.circle(surf, (255, 225, 100), (880, 90), 30)

        # Wooden shelf / play desk surface at bottom
        shelf_rect = pygame.Rect(0, 470, REFERENCE_WIDTH, 130)
        pygame.draw.rect(surf, (235, 205, 160), shelf_rect)
        pygame.draw.line(surf, (200, 165, 120), (0, 470), (REFERENCE_WIDTH, 470), 4)

        # Subtle decorative polka dots or wallpaper stars
        dot_color = (245, 235, 218)
        for x in range(80, REFERENCE_WIDTH, 90):
            for y in range(80, 450, 90):
                pygame.draw.circle(surf, dot_color, (x, y), 5)

    def _draw_leo(self, surf: pygame.Surface, model: AlfabetoModel, anim_time: float) -> None:
        leo_x = 130
        jump_offset = -24.0 * math.sin(math.pi * min(1.0, (0.35 - model.leo_jump) / 0.35)) if model.leo_jump > 0.0 else 0.0
        leo_y = 190 + jump_offset

        mood = model.leo_mood
        if mood not in self._leo_images:
            mood = "neutral"

        if mood in self._leo_images:
            img = self._leo_images[mood]
            wobble = 2.5 * math.sin(anim_time * 2.5)
            surf.blit(img, (leo_x - 70, int(leo_y - 70 + wobble)))
        else:
            self._draw_procedural_leo(surf, leo_x, leo_y + jump_offset, mood, anim_time)

    def _draw_procedural_leo(
        self, surf: pygame.Surface, cx: float, cy: float, mood: str, anim_time: float
    ) -> None:
        # Body / Bean shape (soft warm amber/brown)
        body_rect = pygame.Rect(int(cx - 45), int(cy - 45), 90, 95)
        pygame.draw.ellipse(surf, (185, 125, 75), body_rect)

        # Belly patch (creamy white)
        belly_rect = pygame.Rect(int(cx - 28), int(cy - 15), 56, 55)
        pygame.draw.ellipse(surf, (255, 245, 220), belly_rect)

        # Round glasses (dark brown wire)
        pygame.draw.circle(surf, (255, 255, 255), (int(cx - 18), int(cy - 12)), 16)
        pygame.draw.circle(surf, (255, 255, 255), (int(cx + 18), int(cy - 12)), 16)
        pygame.draw.circle(surf, (85, 50, 25), (int(cx - 18), int(cy - 12)), 16, width=3)
        pygame.draw.circle(surf, (85, 50, 25), (int(cx + 18), int(cy - 12)), 16, width=3)
        pygame.draw.line(surf, (85, 50, 25), (int(cx - 2), int(cy - 12)), (int(cx + 2), int(cy - 12)), 3)

        # Eyes inside glasses
        if mood == "blink":
            pygame.draw.line(surf, (85, 50, 25), (int(cx - 25), int(cy - 12)), (int(cx - 11), int(cy - 12)), 3)
            pygame.draw.line(surf, (85, 50, 25), (int(cx + 11), int(cy - 12)), (int(cx + 25), int(cy - 12)), 3)
        else:
            pygame.draw.circle(surf, (50, 30, 15), (int(cx - 18), int(cy - 12)), 6)
            pygame.draw.circle(surf, (50, 30, 15), (int(cx + 18), int(cy - 12)), 6)

        # Cute small beak (orange triangle)
        pygame.draw.polygon(surf, (245, 140, 30), [(int(cx - 6), int(cy - 2)), (int(cx + 6), int(cy - 2)), (int(cx), int(cy + 8))])

    def _draw_top_bar(self, surf: pygame.Surface, model: AlfabetoModel) -> None:
        # Title Banner in center (safe from top-left Home)
        banner_w, banner_h = 420, 52
        bx = (REFERENCE_WIDTH - banner_w) // 2
        by = 20

        pygame.draw.rect(surf, (255, 255, 255), (bx, by, banner_w, banner_h), border_radius=26)
        pygame.draw.rect(surf, (225, 190, 140), (bx, by, banner_w, banner_h), width=3, border_radius=26)

        if model.mode == GameMode.EXPLORE:
            title_text = self.resources.text("ui.mode_explore_title")
        else:
            title_text = self.resources.text("ui.mode_guess_title")

        txt = self.typography.render(title_text, FontRole.TITLE, 22, (100, 60, 30))
        surf.blit(txt, txt.get_rect(center=(REFERENCE_WIDTH // 2, by + banner_h // 2)))

        # Mode switch button in top-right
        btn_w, btn_h = 170, 48
        btn_x = REFERENCE_WIDTH - btn_w - 30
        btn_y = 22

        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surf, (255, 255, 255), btn_rect, border_radius=24)
        pygame.draw.rect(surf, (120, 180, 230), btn_rect, width=3, border_radius=24)

        next_mode_label = (
            self.resources.text("ui.switch_to_guess")
            if model.mode == GameMode.EXPLORE
            else self.resources.text("ui.switch_to_explore")
        )
        mode_txt = self.typography.render(next_mode_label, FontRole.TITLE, 16, (50, 110, 170))
        surf.blit(mode_txt, mode_txt.get_rect(center=btn_rect.center))

    def _draw_explore_mode(self, surf: pygame.Surface, model: AlfabetoModel, anim_time: float) -> None:
        letter = model.active_letter
        card_w, card_h = 320, 310
        cx = REFERENCE_WIDTH // 2
        cy = 240

        # Bounce on reveal
        scale = 1.0
        if model.reveal_timer > 0.0:
            scale = 1.0 + 0.15 * math.sin(math.pi * (model.reveal_timer / 0.6))
        
        w = int(card_w * scale)
        h = int(card_h * scale)
        card_rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)

        # Card Shadow
        pygame.draw.rect(surf, (220, 205, 185), (card_rect.x + 4, card_rect.y + 8, card_rect.w, card_rect.h), border_radius=32)

        # Card Base (White with letter's themed border)
        pygame.draw.rect(surf, (255, 255, 255), card_rect, border_radius=32)
        pygame.draw.rect(surf, letter.color, card_rect, width=6, border_radius=32)

        # GIANT Capital Letter
        letter_surf = self.typography.render(letter.char, FontRole.DISPLAY, int(88 * scale), letter.color)
        surf.blit(letter_surf, letter_surf.get_rect(center=(cx - int(70 * scale), cy - int(45 * scale))))

        # Cute Object Symbol / Emoji
        symbol_surf = self.typography.render(letter.symbol, FontRole.DISPLAY, int(76 * scale), (40, 40, 40))
        surf.blit(symbol_surf, symbol_surf.get_rect(center=(cx + int(70 * scale), cy - int(45 * scale))))

        # Object Word (Capitalized)
        word = letter.word_for(model.locale)
        word_formatted = display_text(word)
        word_surf = self.typography.render(word_formatted, FontRole.TITLE, int(36 * scale), (60, 60, 60))
        surf.blit(word_surf, word_surf.get_rect(center=(cx, cy + int(70 * scale))))

        # Bottom letter carousel buttons (7 letters centered around current)
        self._draw_letter_strip(surf, model)

    def _draw_letter_strip(self, surf: pygame.Surface, model: AlfabetoModel) -> None:
        strip_y = 500
        btn_size = 64
        spacing = 16
        cur_idx = model.current_index
        total = len(LETTERS_CATALOGUE)

        # Previous button
        prev_rect = pygame.Rect(140, strip_y, 48, btn_size)
        pygame.draw.rect(surf, (255, 255, 255), prev_rect, border_radius=18)
        pygame.draw.rect(surf, (210, 180, 140), prev_rect, width=3, border_radius=18)
        p_txt = self.typography.render("◀", FontRole.TITLE, 22, (120, 80, 40))
        surf.blit(p_txt, p_txt.get_rect(center=prev_rect.center))

        # 7 visible letter slots
        start_x = 210
        visible_count = 7
        half = visible_count // 2
        for i in range(visible_count):
            offset = i - half
            idx = (cur_idx + offset) % total
            item = LETTERS_CATALOGUE[idx]
            bx = start_x + i * (btn_size + spacing)
            brect = pygame.Rect(bx, strip_y, btn_size, btn_size)

            is_selected = (idx == cur_idx)
            bg_color = (255, 255, 255) if not is_selected else item.color
            text_color = item.color if not is_selected else (255, 255, 255)

            pygame.draw.rect(surf, bg_color, brect, border_radius=20)
            pygame.draw.rect(surf, item.color, brect, width=4 if is_selected else 2, border_radius=20)

            c_txt = self.typography.render(item.char, FontRole.TITLE, 28, text_color)
            surf.blit(c_txt, c_txt.get_rect(center=brect.center))

        # Next button
        next_rect = pygame.Rect(start_x + visible_count * (btn_size + spacing), strip_y, 48, btn_size)
        pygame.draw.rect(surf, (255, 255, 255), next_rect, border_radius=18)
        pygame.draw.rect(surf, (210, 180, 140), next_rect, width=3, border_radius=18)
        n_txt = self.typography.render("▶", FontRole.TITLE, 22, (120, 80, 40))
        surf.blit(n_txt, n_txt.get_rect(center=next_rect.center))

    def _draw_guess_mode(self, surf: pygame.Surface, model: AlfabetoModel, anim_time: float) -> None:
        target = model.target_letter
        word = target.word_for(model.locale)

        # Target card in upper middle
        t_w, t_h = 240, 180
        tx = (REFERENCE_WIDTH - t_w) // 2
        ty = 110
        t_rect = pygame.Rect(tx, ty, t_w, t_h)

        pygame.draw.rect(surf, (255, 255, 255), t_rect, border_radius=28)
        pygame.draw.rect(surf, (230, 190, 140), t_rect, width=4, border_radius=28)

        # Big Target Symbol / Emoji
        sym_surf = self.typography.render(target.symbol, FontRole.DISPLAY, 68, (40, 40, 40))
        surf.blit(sym_surf, sym_surf.get_rect(center=(tx + t_w // 2, ty + 65)))

        # Prompt Word: e.g. "S COME SOLE" / "S FOR SUN"
        if model.guess_solved:
            prompt = f"{target.char}! {word}!"
        else:
            prompt = self.resources.text("ui.guess_prompt", {"char": target.char})
        
        prompt_txt = self.typography.render(display_text(prompt), FontRole.TITLE, 24, (120, 60, 20))
        surf.blit(prompt_txt, prompt_txt.get_rect(center=(tx + t_w // 2, ty + 140)))

        # 3 Big Choice Cards
        card_w, card_h = 140, 160
        spacing = 40
        total_w = 3 * card_w + 2 * spacing
        start_x = (REFERENCE_WIDTH - total_w) // 2
        card_y = 350

        for i, choice in enumerate(model.guess_choices):
            cx = start_x + i * (card_w + spacing)
            cy = card_y

            # Wobble animation on wrong tap
            wobble_x = 0.0
            if model.wobble_card == choice.char and model.wobble_timer > 0.0:
                wobble_x = 12.0 * math.sin(model.wobble_timer * 25.0)

            crect = pygame.Rect(int(cx + wobble_x), cy, card_w, card_h)

            is_correct_and_solved = (model.guess_solved and choice.char == target.char)
            bg_col = (255, 255, 255) if not is_correct_and_solved else (255, 240, 180)
            border_col = choice.color if not is_correct_and_solved else (240, 160, 30)

            pygame.draw.rect(surf, bg_col, crect, border_radius=26)
            pygame.draw.rect(surf, border_col, crect, width=5 if is_correct_and_solved else 3, border_radius=26)

            # Big Letter
            char_surf = self.typography.render(choice.char, FontRole.DISPLAY, 58, choice.color)
            surf.blit(char_surf, char_surf.get_rect(center=crect.center))

    def _draw_celebration_effects(self, surf: pygame.Surface, anim_time: float) -> None:
        # Confetti sparkles across the stage
        for i in range(16):
            ang = (i / 16.0) * 2 * math.pi + anim_time * 3.0
            dist = 180 + 40 * math.sin(anim_time * 4.0 + i)
            sx = int(REFERENCE_WIDTH // 2 + math.cos(ang) * dist)
            sy = int(240 + math.sin(ang) * dist * 0.6)
            color = (
                (255, 100, 100) if i % 4 == 0 else
                (100, 200, 255) if i % 4 == 1 else
                (255, 220, 80) if i % 4 == 2 else
                (140, 220, 100)
            )
            size = int(8 + 3 * math.sin(anim_time * 6.0 + i))
            pygame.draw.circle(surf, color, (sx, sy), size)
