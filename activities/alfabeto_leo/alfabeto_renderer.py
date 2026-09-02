"""Storybook visual renderer for L'Alfabeto di Leo."""

from __future__ import annotations

import math
from pathlib import Path

import pygame

from greia_platform.localization import LocalizedResources, display_text
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .alfabeto_model import (
        LETTERS_CATALOGUE,
        AlfabetoModel,
        GameMode,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
else:
    from alfabeto_model import (
        LETTERS_CATALOGUE,
        AlfabetoModel,
        GameMode,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEO_ASSET_DIR = PROJECT_ROOT / "assets" / "visual" / "runtime" / "v1" / "characters"


class AlfabetoRenderer:
    """Draws Leo's cozy treehouse library and giant letter cards."""

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
                    img = pygame.image.load(str(path))
                    # Scale Leo to a friendly character size (~180x180)
                    self._leo_images[mood] = pygame.transform.smoothscale(img, (180, 180))
                except Exception:
                    pass

    def render(self, model: AlfabetoModel, anim_time: float) -> None:
        surf = self.canvas.surface

        # 1. Warm cozy treehouse room & window
        self._draw_background(surf, anim_time)

        # 2. Leo the Owl (on his cozy perch on the left)
        self._draw_leo(surf, model, anim_time)

        # 3. Top Banner & Mode Toggle
        self._draw_top_bar(surf, model)

        # 4. Mode-specific content
        if model.mode == GameMode.EXPLORE:
            self._draw_explore_mode(surf, model, anim_time)
        else:
            self._draw_guess_mode(surf, model, anim_time)

        # 5. Celebration sparkles on correct guess
        if model.celebrating:
            self._draw_celebration(surf, anim_time)

    def _draw_background(self, surf: pygame.Surface, anim_time: float) -> None:
        # Cozy warm cream wall
        surf.fill((253, 246, 235))

        # Festive pastel bunting flags across top
        bunting_colors = [(245, 110, 110), (100, 180, 245), (255, 210, 70), (120, 215, 130), (220, 140, 230)]
        flag_w, flag_h = 44, 38
        for i in range(12):
            fx = 150 + i * 60
            fy = 6
            col = bunting_colors[i % len(bunting_colors)]
            pygame.draw.polygon(surf, col, [(fx, fy), (fx + flag_w, fy), (fx + flag_w // 2, fy + flag_h)])
        pygame.draw.line(surf, (205, 180, 150), (140, 6), (880, 6), 2)

        # Arched window in upper-right with blue sky and sun
        wx, wy, ww, wh = 750, 60, 220, 250
        # Window frame shadow & base
        pygame.draw.rect(surf, (200, 230, 255), (wx, wy, ww, wh), border_radius=30)
        pygame.draw.rect(surf, (220, 175, 120), (wx, wy, ww, wh), width=6, border_radius=30)
        # Outside scenery through window: warm sun & little cloud
        sun_pulse = 2.0 * math.sin(anim_time * 2.0)
        pygame.draw.circle(surf, (255, 220, 70), (wx + 155, wy + 70), int(34 + sun_pulse))
        pygame.draw.circle(surf, (255, 255, 255), (wx + 65, wy + 110), 22)
        pygame.draw.circle(surf, (255, 255, 255), (wx + 85, wy + 110), 26)
        pygame.draw.circle(surf, (255, 255, 255), (wx + 105, wy + 110), 20)
        # Window mullions
        pygame.draw.line(surf, (220, 175, 120), (wx + ww // 2, wy), (wx + ww // 2, wy + wh), 4)
        pygame.draw.line(surf, (220, 175, 120), (wx, wy + wh // 2), (wx + ww, wy + wh // 2), 4)

        # Warm wooden floor at bottom
        pygame.draw.rect(surf, (230, 195, 150), (0, 480, REFERENCE_WIDTH, 120))
        pygame.draw.line(surf, (205, 165, 120), (0, 480), (REFERENCE_WIDTH, 480), 4)
        for px in range(120, REFERENCE_WIDTH, 180):
            pygame.draw.line(surf, (215, 175, 130), (px, 480), (px, 600), 2)

    def _draw_leo(self, surf: pygame.Surface, model: AlfabetoModel, anim_time: float) -> None:
        cx = 125
        cy = 235

        # Cozy wooden branch perch for Leo
        pygame.draw.rect(surf, (165, 115, 65), (20, cy + 65, 170, 22), border_radius=10)
        pygame.draw.rect(surf, (135, 90, 45), (20, cy + 65, 170, 22), width=3, border_radius=10)
        # Green leaves sprouting from branch
        pygame.draw.circle(surf, (95, 185, 75), (170, cy + 60), 14)
        pygame.draw.circle(surf, (115, 205, 90), (185, cy + 72), 12)

        # Gentle breathing motion
        breathe_y = 3.0 * math.sin(anim_time * 2.8)

        # Check character PNG
        mood = "happy" if model.celebrating else ("blink" if int(anim_time * 2.0) % 7 == 0 else "neutral")
        if mood not in self._leo_images:
            mood = "neutral"

        if mood in self._leo_images:
            img = self._leo_images[mood]
            surf.blit(img, (cx - img.get_width() // 2, int(cy - img.get_height() // 2 + breathe_y)))
        else:
            # Fallback procedural owl
            self._draw_procedural_leo(surf, cx, cy + breathe_y, mood)

    def _draw_procedural_leo(self, surf: pygame.Surface, cx: float, cy: float, mood: str) -> None:
        # Body
        pygame.draw.ellipse(surf, (185, 125, 75), (cx - 50, cy - 55, 100, 110))
        # Belly
        pygame.draw.ellipse(surf, (250, 235, 205), (cx - 35, cy - 25, 70, 75))
        # Round glasses
        pygame.draw.circle(surf, (255, 255, 255), (int(cx - 20), int(cy - 20)), 18)
        pygame.draw.circle(surf, (255, 255, 255), (int(cx + 20), int(cy - 20)), 18)
        pygame.draw.circle(surf, (70, 40, 20), (int(cx - 20), int(cy - 20)), 18, width=3)
        pygame.draw.circle(surf, (70, 40, 20), (int(cx + 20), int(cy - 20)), 18, width=3)
        pygame.draw.line(surf, (70, 40, 20), (int(cx - 2), int(cy - 20)), (int(cx + 2), int(cy - 20)), 3)
        # Eyes
        pygame.draw.circle(surf, (50, 30, 15), (int(cx - 18), int(cy - 20)), 6)
        pygame.draw.circle(surf, (50, 30, 15), (int(cx + 18), int(cy - 20)), 6)
        # Beak
        pygame.draw.polygon(surf, (245, 140, 30), [(int(cx - 6), int(cy - 8)), (int(cx + 6), int(cy - 8)), (int(cx), int(cy + 2))])

    def _draw_top_bar(self, surf: pygame.Surface, model: AlfabetoModel) -> None:
        # Title Banner in center (safe from top-left Home)
        banner_w, banner_h = 420, 52
        bx = (REFERENCE_WIDTH - banner_w) // 2
        by = 18

        pygame.draw.rect(surf, (255, 255, 255), (bx, by, banner_w, banner_h), border_radius=26)
        pygame.draw.rect(surf, (220, 180, 130), (bx, by, banner_w, banner_h), width=3, border_radius=26)

        if model.mode == GameMode.EXPLORE:
            title_text = self.resources.text("ui.mode_explore_title")
        else:
            title_text = self.resources.text("ui.mode_guess_title")

        txt = self.typography.render(title_text, FontRole.TITLE, 22, (95, 55, 25))
        surf.blit(txt, txt.get_rect(center=(REFERENCE_WIDTH // 2, by + banner_h // 2)))

        # Mode switch button in top-right
        btn_w, btn_h = 175, 48
        btn_x = REFERENCE_WIDTH - btn_w - 30
        btn_y = 20

        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surf, (255, 255, 255), btn_rect, border_radius=24)
        pygame.draw.rect(surf, (110, 175, 230), btn_rect, width=3, border_radius=24)

        next_mode_label = (
            self.resources.text("ui.switch_to_guess")
            if model.mode == GameMode.EXPLORE
            else self.resources.text("ui.switch_to_explore")
        )
        mode_txt = self.typography.render(next_mode_label, FontRole.TITLE, 17, (45, 105, 170))
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
        pygame.draw.rect(surf, (215, 200, 180), (card_rect.x + 5, card_rect.y + 8, card_rect.w, card_rect.h), border_radius=32)

        # Card Base
        pygame.draw.rect(surf, (255, 255, 255), card_rect, border_radius=32)
        pygame.draw.rect(surf, letter.color, card_rect, width=6, border_radius=32)

        # GIANT Capital Letter
        letter_surf = self.typography.render(letter.char, FontRole.DISPLAY, int(88 * scale), letter.color)
        surf.blit(letter_surf, letter_surf.get_rect(center=(cx - int(70 * scale), cy - int(45 * scale))))

        # Cute Object Symbol / Emoji matching child language
        symbol = letter.symbol_for(model.locale)
        symbol_surf = self.typography.render(symbol, FontRole.DISPLAY, int(76 * scale), (40, 40, 40))
        surf.blit(symbol_surf, symbol_surf.get_rect(center=(cx + int(70 * scale), cy - int(45 * scale))))

        # Object Word (Capitalized)
        word = letter.word_for(model.locale)
        word_formatted = display_text(word)
        word_surf = self.typography.render(word_formatted, FontRole.TITLE, int(36 * scale), (60, 60, 60))
        surf.blit(word_surf, word_surf.get_rect(center=(cx, cy + int(70 * scale))))

        # Bottom letter carousel strip
        self._draw_letter_strip(surf, model)

    def _draw_letter_strip(self, surf: pygame.Surface, model: AlfabetoModel) -> None:
        strip_y = 505
        btn_size = 64
        spacing = 16
        cur_idx = model.current_index
        total = len(LETTERS_CATALOGUE)

        # Previous button (drawn triangle instead of tofu font)
        prev_rect = pygame.Rect(135, strip_y, 52, btn_size)
        pygame.draw.rect(surf, (255, 255, 255), prev_rect, border_radius=18)
        pygame.draw.rect(surf, (210, 175, 130), prev_rect, width=3, border_radius=18)
        px, py = prev_rect.center
        pygame.draw.polygon(surf, (130, 85, 40), [(px + 8, py - 12), (px - 10, py), (px + 8, py + 12)])

        # 7 visible letter buttons
        start_x = 205
        visible_count = 7
        half = visible_count // 2
        for i in range(visible_count):
            offset = i - half
            idx = (cur_idx + offset) % total
            item = LETTERS_CATALOGUE[idx]
            bx = start_x + i * (btn_size + spacing)
            brect = pygame.Rect(bx, strip_y, btn_size, btn_size)

            is_current = (offset == 0)
            bg_color = item.color if is_current else (255, 255, 255)
            text_color = (255, 255, 255) if is_current else item.color
            border_color = (40, 40, 40) if is_current else (215, 210, 200)

            pygame.draw.rect(surf, bg_color, brect, border_radius=20)
            pygame.draw.rect(surf, border_color, brect, width=3 if is_current else 2, border_radius=20)

            c_txt = self.typography.render(item.char, FontRole.TITLE, 28, text_color)
            surf.blit(c_txt, c_txt.get_rect(center=brect.center))

        # Next button (drawn triangle instead of tofu font)
        next_rect = pygame.Rect(start_x + visible_count * (btn_size + spacing), strip_y, 52, btn_size)
        pygame.draw.rect(surf, (255, 255, 255), next_rect, border_radius=18)
        pygame.draw.rect(surf, (210, 175, 130), next_rect, width=3, border_radius=18)
        nx, ny = next_rect.center
        pygame.draw.polygon(surf, (130, 85, 40), [(nx - 8, ny - 12), (nx + 10, ny), (nx - 8, ny + 12)])

    def _draw_guess_mode(self, surf: pygame.Surface, model: AlfabetoModel, anim_time: float) -> None:
        target = model.target_letter
        word = target.word_for(model.locale)
        symbol = target.symbol_for(model.locale)

        # Target card in upper middle
        t_w, t_h = 240, 180
        tx = (REFERENCE_WIDTH - t_w) // 2
        ty = 110
        t_rect = pygame.Rect(tx, ty, t_w, t_h)

        pygame.draw.rect(surf, (255, 255, 255), t_rect, border_radius=28)
        pygame.draw.rect(surf, (230, 185, 130), t_rect, width=4, border_radius=28)

        # Big Target Symbol / Emoji
        sym_surf = self.typography.render(symbol, FontRole.DISPLAY, 72, (40, 40, 40))
        surf.blit(sym_surf, sym_surf.get_rect(center=(tx + t_w // 2, ty + 65)))

        # Prompt Word: e.g. "S COME SOLE" / "WHERE IS S?"
        if model.guess_solved:
            prompt = f"{target.char}! {word}!"
        else:
            prompt = self.resources.text("ui.guess_prompt", {"char": target.char})

        prompt_txt = self.typography.render(display_text(prompt), FontRole.TITLE, 24, (120, 60, 20))
        surf.blit(prompt_txt, prompt_txt.get_rect(center=(tx + t_w // 2, ty + 140)))

        # 3 Big Choice Cards
        card_w, card_h = 145, 165
        spacing = 40
        total_w = 3 * card_w + 2 * spacing
        start_x = (REFERENCE_WIDTH - total_w) // 2
        card_y = 330

        for i, choice in enumerate(model.guess_choices):
            cx = start_x + i * (card_w + spacing)
            cy = card_y

            # Wobble animation on wrong tap
            wobble_x = 0.0
            if model.wobble_card == choice.char and model.wobble_timer > 0.0:
                wobble_x = 14.0 * math.sin(model.wobble_timer * 28.0)

            crect = pygame.Rect(int(cx + wobble_x), cy, card_w, card_h)

            is_correct_and_solved = (model.guess_solved and choice.char == target.char)
            bg_col = (255, 255, 255) if not is_correct_and_solved else (255, 245, 180)
            border_col = choice.color if not is_correct_and_solved else (240, 160, 30)

            pygame.draw.rect(surf, bg_col, crect, border_radius=28)
            pygame.draw.rect(surf, border_col, crect, width=5 if is_correct_and_solved else 3, border_radius=28)

            txt = self.typography.render(choice.char, FontRole.DISPLAY, 80, choice.color)
            surf.blit(txt, txt.get_rect(center=crect.center))

    def _draw_celebration(self, surf: pygame.Surface, anim_time: float) -> None:
        colors = [(255, 80, 80), (255, 210, 50), (90, 215, 120), (70, 175, 255), (225, 110, 240)]
        for i in range(20):
            ang = i * (2.0 * math.pi / 20.0) + anim_time * 2.0
            rad = 80 + int(40 * math.sin(anim_time * 6.0 + i))
            px = int(REFERENCE_WIDTH // 2 + math.cos(ang) * rad)
            py = int(240 + math.sin(ang) * rad)
            col = colors[i % len(colors)]
            pygame.draw.circle(surf, col, (px, py), 6)
