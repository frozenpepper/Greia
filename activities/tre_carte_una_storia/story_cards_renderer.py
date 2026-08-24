"""Presentation renderer for Tre Carte Una Storia."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .story_cards_art import CARD_BG, CARD_BORDER, StoryArt
    from .story_cards_content import STORY_SEEDS_BY_ID, StoryCard, StorySeed
    from .story_cards_model import (
        MAX_GRAPHEMES,
        MAX_SAVED_STORIES,
        SavedStory,
        StoryLibrary,
        StoryRound,
        StoryStage,
    )
else:
    from story_cards_art import CARD_BG, CARD_BORDER, StoryArt
    from story_cards_content import STORY_SEEDS_BY_ID, StoryCard, StorySeed
    from story_cards_model import (
        MAX_GRAPHEMES,
        MAX_SAVED_STORIES,
        SavedStory,
        StoryLibrary,
        StoryRound,
        StoryStage,
    )


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

CHECK_BTN_RECT: Final[pygame.Rect] = pygame.Rect(392, 490, 240, 54)
GALLERY_BTN_RECT: Final[pygame.Rect] = pygame.Rect(700, 490, 240, 54)
SAVE_BTN_RECT: Final[pygame.Rect] = pygame.Rect(392, 510, 240, 54)
BACK_TO_GAME_RECT: Final[pygame.Rect] = pygame.Rect(80, 24, 240, 52)


class StoryRenderer:
    """Render story sequencing puzzle, caption composer, and saved library."""

    def __init__(
        self,
        art: StoryArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources

    def draw_round(
        self,
        target: pygame.Surface,
        round_state: StoryRound,
        library: StoryLibrary,
        *,
        cursor_visible: bool = True,
    ) -> None:
        target.blit(self._art.background, (0, 0))

        if round_state.stage == StoryStage.SEQUENCE:
            self._draw_sequence_stage(target, round_state, library)
        else:
            self._draw_caption_stage(target, round_state, cursor_visible=cursor_visible)

    def draw_gallery(
        self,
        target: pygame.Surface,
        library: StoryLibrary,
        *,
        selected_story_id: str | None = None,
        confirm_delete: bool = False,
    ) -> None:
        target.blit(self._art.background, (0, 0))

        # Top Return Button
        pygame.draw.rect(target, (2, 132, 199), BACK_TO_GAME_RECT, border_radius=22)
        b_txt = self._typography.render(
            self._resources.text("button.new_story"),
            FontRole.TITLE,
            20,
            (255, 255, 255),
        )
        target.blit(
            b_txt,
            (
                BACK_TO_GAME_RECT.centerx - b_txt.get_width() // 2,
                BACK_TO_GAME_RECT.centery - b_txt.get_height() // 2,
            ),
        )

        # Header Badge
        header = f"{self._resources.text('button.saved')} ({library.count}/{MAX_SAVED_STORIES})"
        h_surf = self._typography.render(header, FontRole.TITLE, 24, (254, 240, 138))
        target.blit(h_surf, (REFERENCE_WIDTH // 2 - h_surf.get_width() // 2, 34))

        if library.count == 0:
            empty_txt = self._typography.render("Nessuna storia ancora!", FontRole.BODY, 24, (148, 163, 184))
            target.blit(empty_txt, (REFERENCE_WIDTH // 2 - empty_txt.get_width() // 2, 280))
            return

        for idx, story in enumerate(library.stories):
            rect = self.gallery_item_rect_at(idx)
            is_selected = (story.story_id == selected_story_id)
            self._draw_gallery_item(target, rect, story, is_selected=is_selected)

        if selected_story_id is not None:
            story = library.get(selected_story_id)
            if story is not None:
                self._draw_story_modal(target, story, confirm_delete=confirm_delete)

    def draw_full_dialog(self, target: pygame.Surface) -> None:
        """Render polite full-library sheet."""
        overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 210))
        target.blit(overlay, (0, 0))

        sheet = pygame.Rect(REFERENCE_WIDTH // 2 - 260, REFERENCE_HEIGHT // 2 - 140, 520, 280)
        pygame.draw.rect(target, (255, 251, 235), sheet, border_radius=28)
        pygame.draw.rect(target, (217, 119, 6), sheet, width=4, border_radius=28)

        t_surf = self._typography.render(
            self._resources.text("dialog.full_title"),
            FontRole.DISPLAY,
            28,
            (180, 83, 9),
        )
        target.blit(t_surf, (sheet.centerx - t_surf.get_width() // 2, sheet.top + 32))

        lines = self._resources.text("dialog.full_body").split("\n")
        for i, line in enumerate(lines):
            b_surf = self._typography.render(
                line,
                FontRole.BODY,
                20,
                (71, 85, 105),
            )
            target.blit(b_surf, (sheet.centerx - b_surf.get_width() // 2, sheet.top + 85 + i * 30))

        ok_rect = pygame.Rect(sheet.centerx - 90, sheet.bottom - 74, 180, 50)
        pygame.draw.rect(target, (2, 132, 199), ok_rect, border_radius=18)
        ok_txt = self._typography.render("OK", FontRole.TITLE, 22, (255, 255, 255))
        target.blit(
            ok_txt,
            (ok_rect.centerx - ok_txt.get_width() // 2, ok_rect.centery - ok_txt.get_height() // 2),
        )

    # --- Interaction hit testing ---
    def slot_rect_at(self, slot_index: int) -> pygame.Rect:
        x = 92 + slot_index * 290
        y = 125
        return pygame.Rect(x, y, 260, 330)

    def slot_at(self, point: tuple[int, int]) -> int | None:
        for idx in range(3):
            if self.slot_rect_at(idx).collidepoint(point):
                return idx
        return None

    def check_contains(self, point: tuple[int, int]) -> bool:
        return CHECK_BTN_RECT.collidepoint(point)

    def gallery_contains(self, point: tuple[int, int]) -> bool:
        return GALLERY_BTN_RECT.collidepoint(point)

    def save_contains(self, point: tuple[int, int]) -> bool:
        return SAVE_BTN_RECT.collidepoint(point)

    def back_to_game_contains(self, point: tuple[int, int]) -> bool:
        return BACK_TO_GAME_RECT.collidepoint(point)

    def caption_preset_rect_at(self, index: int) -> pygame.Rect:
        y = 205 + index * 60
        return pygame.Rect(112, y, 800, 52)

    def caption_preset_at(self, point: tuple[int, int]) -> int | None:
        for idx in range(3):
            if self.caption_preset_rect_at(idx).collidepoint(point):
                return idx
        return None

    def custom_caption_rect(self) -> pygame.Rect:
        return pygame.Rect(112, 395, 800, 54)

    def custom_caption_contains(self, point: tuple[int, int]) -> bool:
        return self.custom_caption_rect().collidepoint(point)

    def gallery_item_rect_at(self, index: int) -> pygame.Rect:
        col = index % 4
        row = index // 4
        x = 92 + col * 220
        y = 100 + row * 140
        return pygame.Rect(x, y, 200, 120)

    def gallery_item_at(self, point: tuple[int, int], count: int) -> int | None:
        for idx in range(count):
            if self.gallery_item_rect_at(idx).collidepoint(point):
                return idx
        return None

    def delete_btn_rect(self) -> pygame.Rect:
        return pygame.Rect(REFERENCE_WIDTH // 2 - 190, 500, 170, 48)

    def cancel_btn_rect(self) -> pygame.Rect:
        return pygame.Rect(REFERENCE_WIDTH // 2 + 20, 500, 170, 48)

    # --- Internal drawing helpers ---
    def _draw_sequence_stage(
        self,
        target: pygame.Surface,
        round_state: StoryRound,
        library: StoryLibrary,
    ) -> None:
        # Prompt
        p_surf = self._typography.render(
            self._resources.text("prompt.sequence"),
            FontRole.TITLE,
            24,
            (254, 240, 138),
        )
        target.blit(p_surf, (REFERENCE_WIDTH // 2 - p_surf.get_width() // 2, 45))

        # 3 Card Slots
        for idx, card in enumerate(round_state.current_order):
            rect = self.slot_rect_at(idx)
            is_selected = (idx == round_state.selected_slot)
            is_hinted = (round_state.hint_revealed and idx == 0 and card.card_id == round_state.target_order[0])

            # Draw card in slot
            self._art.draw_card(
                target,
                rect,
                card,
                is_selected=is_selected,
                is_hinted=is_hinted,
                slot_number=idx + 1,
            )

            # Slot label under card (Prima / Poi / Infine)
            label = self._resources.text(f"slot.{idx + 1}")
            l_surf = self._typography.render(label, FontRole.TITLE, 20, (203, 213, 225))
            target.blit(l_surf, (rect.centerx - l_surf.get_width() // 2, rect.bottom + 12))

        # Mascot Lilli at bottom-left
        target.blit(self._art.mascot, (60, 465))

        # Check Order Button
        pygame.draw.rect(target, (22, 163, 74), CHECK_BTN_RECT, border_radius=20)
        pygame.draw.rect(target, (134, 239, 172), CHECK_BTN_RECT, width=3, border_radius=20)
        c_txt = self._typography.render(
            self._resources.text("button.check"),
            FontRole.TITLE,
            22,
            (255, 255, 255),
        )
        target.blit(
            c_txt,
            (
                CHECK_BTN_RECT.centerx - c_txt.get_width() // 2,
                CHECK_BTN_RECT.centery - c_txt.get_height() // 2,
            ),
        )

        # Saved Stories Button
        pygame.draw.rect(target, (2, 132, 199), GALLERY_BTN_RECT, border_radius=20)
        g_label = f"{self._resources.text('button.saved')} ({library.count})"
        g_txt = self._typography.render(g_label, FontRole.TITLE, 20, (255, 255, 255))
        target.blit(
            g_txt,
            (
                GALLERY_BTN_RECT.centerx - g_txt.get_width() // 2,
                GALLERY_BTN_RECT.centery - g_txt.get_height() // 2,
            ),
        )

    def _draw_caption_stage(
        self,
        target: pygame.Surface,
        round_state: StoryRound,
        *,
        cursor_visible: bool = True,
    ) -> None:
        # Prompt
        p_surf = self._typography.render(
            self._resources.text("prompt.caption"),
            FontRole.TITLE,
            24,
            (254, 240, 138),
        )
        target.blit(p_surf, (REFERENCE_WIDTH // 2 - p_surf.get_width() // 2, 20))

        # 3 Mini Ordered Cards across top
        for idx, card in enumerate(round_state.current_order):
            mini_rect = pygame.Rect(232 + idx * 195, 60, 170, 120)
            self._art.draw_card(target, mini_rect, card, slot_number=idx + 1)

        # 3 Preset Caption Option Rows
        for idx in range(3):
            row_rect = self.caption_preset_rect_at(idx)
            is_active = (round_state.caption_mode == f"preset_{idx}")

            if is_active:
                pygame.draw.rect(target, (254, 240, 138), row_rect, border_radius=16)
                pygame.draw.rect(target, (234, 179, 8), row_rect, width=3, border_radius=16)
                text_color = (120, 53, 15)
            else:
                pygame.draw.rect(target, (30, 41, 59), row_rect, border_radius=16)
                pygame.draw.rect(target, (71, 85, 105), row_rect, width=2, border_radius=16)
                text_color = (241, 245, 249)

            key = round_state.seed.caption_keys[idx]
            sentence = self._resources.text(key)
            s_surf = self._typography.render(f"{idx + 1}.  {sentence}", FontRole.TITLE, 20, text_color)
            target.blit(s_surf, (row_rect.left + 24, row_rect.centery - s_surf.get_height() // 2))

        # Custom Caption Input Box
        c_rect = self.custom_caption_rect()
        is_custom = (round_state.caption_mode == "custom")
        if is_custom:
            pygame.draw.rect(target, (255, 251, 235), c_rect, border_radius=16)
            pygame.draw.rect(target, (56, 189, 248), c_rect, width=3, border_radius=16)
        else:
            pygame.draw.rect(target, (30, 41, 59), c_rect, border_radius=16)
            pygame.draw.rect(target, (71, 85, 105), c_rect, width=2, border_radius=16)

        if round_state.custom_caption:
            c_surf = self._typography.render(
                round_state.custom_caption,
                FontRole.TITLE,
                20,
                (30, 41, 59) if is_custom else (203, 213, 225),
            )
            target.blit(c_surf, (c_rect.left + 24, c_rect.centery - c_surf.get_height() // 2))

            if is_custom and cursor_visible:
                before = round_state.custom_caption[:round_state.cursor]
                cx = c_rect.left + 24 + (
                    self._typography.render(before, FontRole.TITLE, 20, (0, 0, 0)).get_width()
                    if before
                    else 0
                )
                pygame.draw.line(target, (2, 132, 199), (cx, c_rect.top + 12), (cx, c_rect.bottom - 12), 3)
        else:
            ph_surf = self._typography.render(
                self._resources.text("prompt.caption_placeholder"),
                FontRole.BODY,
                20,
                (148, 163, 184),
            )
            target.blit(ph_surf, (c_rect.left + 24, c_rect.centery - ph_surf.get_height() // 2))
            if is_custom and cursor_visible:
                pygame.draw.line(
                    target,
                    (2, 132, 199),
                    (c_rect.left + 24, c_rect.top + 12),
                    (c_rect.left + 24, c_rect.bottom - 12),
                    3,
                )

        # Save Button
        pygame.draw.rect(target, (22, 163, 74), SAVE_BTN_RECT, border_radius=20)
        pygame.draw.rect(target, (134, 239, 172), SAVE_BTN_RECT, width=3, border_radius=20)
        sv_txt = self._typography.render(
            self._resources.text("button.save"),
            FontRole.TITLE,
            22,
            (255, 255, 255),
        )
        target.blit(
            sv_txt,
            (
                SAVE_BTN_RECT.centerx - sv_txt.get_width() // 2,
                SAVE_BTN_RECT.centery - sv_txt.get_height() // 2,
            ),
        )

    def _draw_gallery_item(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        story: SavedStory,
        *,
        is_selected: bool = False,
    ) -> None:
        pygame.draw.rect(target, CARD_BG, rect, border_radius=14)
        if is_selected:
            pygame.draw.rect(target, (56, 189, 248), rect, width=4, border_radius=14)
        else:
            pygame.draw.rect(target, (217, 119, 6), rect, width=2, border_radius=14)

        seed = STORY_SEEDS_BY_ID.get(story.seed_id)
        if seed is not None:
            # 3 miniature symbols
            for i, card in enumerate(seed.cards):
                s_surf = self._typography.render(card.symbol, FontRole.DISPLAY, 28, (255, 255, 255))
                target.blit(s_surf, (rect.left + 15 + i * 55, rect.top + 12))

            # Title
            title = self._resources.text(seed.title_key)
            t_surf = self._typography.render(title[:16], FontRole.TITLE, 16, (120, 53, 15))
            target.blit(t_surf, (rect.left + 12, rect.bottom - 30))

    def _draw_story_modal(
        self,
        target: pygame.Surface,
        story: SavedStory,
        *,
        confirm_delete: bool = False,
    ) -> None:
        overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 210))
        target.blit(overlay, (0, 0))

        modal_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 380, 50, 760, 420)
        pygame.draw.rect(target, (255, 251, 235), modal_rect, border_radius=24)
        pygame.draw.rect(target, (217, 119, 6), modal_rect, width=4, border_radius=24)

        seed = STORY_SEEDS_BY_ID.get(story.seed_id)
        if seed is not None:
            # Title
            t_surf = self._typography.render(
                self._resources.text(seed.title_key),
                FontRole.DISPLAY,
                26,
                (120, 53, 15),
            )
            target.blit(t_surf, (modal_rect.centerx - t_surf.get_width() // 2, modal_rect.top + 24))

            # 3 Cards
            for i, card in enumerate(seed.cards):
                c_rect = pygame.Rect(modal_rect.left + 50 + i * 225, modal_rect.top + 75, 210, 180)
                self._art.draw_card(target, c_rect, card, slot_number=i + 1)

        # Caption
        cap_surf = self._typography.render(story.caption_text, FontRole.TITLE, 22, (30, 41, 59))
        target.blit(cap_surf, (modal_rect.centerx - cap_surf.get_width() // 2, modal_rect.bottom - 90))

        # Controls
        if confirm_delete:
            del_rect = self.delete_btn_rect()
            pygame.draw.rect(target, (225, 29, 72), del_rect, border_radius=18)
            d_txt = self._typography.render(
                self._resources.text("button.delete"),
                FontRole.TITLE,
                20,
                (255, 255, 255),
            )
            target.blit(
                d_txt,
                (del_rect.centerx - d_txt.get_width() // 2, del_rect.centery - d_txt.get_height() // 2),
            )

            can_rect = self.cancel_btn_rect()
            pygame.draw.rect(target, (51, 65, 85), can_rect, border_radius=18)
            c_txt = self._typography.render(
                self._resources.text("button.cancel"),
                FontRole.TITLE,
                20,
                (255, 255, 255),
            )
            target.blit(
                c_txt,
                (can_rect.centerx - c_txt.get_width() // 2, can_rect.centery - c_txt.get_height() // 2),
            )
        else:
            del_rect = self.delete_btn_rect()
            pygame.draw.rect(target, (225, 29, 72), del_rect, border_radius=18)
            d_txt = self._typography.render(
                self._resources.text("button.delete"),
                FontRole.TITLE,
                20,
                (255, 255, 255),
            )
            target.blit(
                d_txt,
                (del_rect.centerx - d_txt.get_width() // 2, del_rect.centery - d_txt.get_height() // 2),
            )

            close_rect = self.cancel_btn_rect()
            pygame.draw.rect(target, (2, 132, 199), close_rect, border_radius=18)
            cl_txt = self._typography.render("CHIUDI", FontRole.TITLE, 20, (255, 255, 255))
            target.blit(
                cl_txt,
                (
                    close_rect.centerx - cl_txt.get_width() // 2,
                    close_rect.centery - cl_txt.get_height() // 2,
                ),
            )
