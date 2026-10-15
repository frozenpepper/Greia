"""High-polish presentation renderer for Officina dei Suoni."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .sound_art import SoundWorkshopArt
    from .sound_content import WordItem, WorkshopMode
    from .sound_workshop_model import REFERENCE_WIDTH, WorkshopChallenge, SoundSession
else:
    from sound_art import SoundWorkshopArt
    from sound_content import WordItem, WorkshopMode
    from sound_workshop_model import REFERENCE_WIDTH, WorkshopChallenge, SoundSession


REPLAY_RECT: Final[pygame.Rect] = pygame.Rect(80, 24, 180, 48)
TARGET_SOUND_RECT: Final[pygame.Rect] = pygame.Rect(452, 78, 120, 100)
TARGET_PICTURE_RECT: Final[pygame.Rect] = pygame.Rect(452, 68, 120, 120)


class SoundWorkshopRenderer:
    """Render the workshop scene, sound boxes, letter tiles, and Leo mascot."""

    def __init__(
        self,
        art: SoundWorkshopArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources

        self._replay_label = typography.render(
            f"🔊 {resources.text('button.listen')}",
            FontRole.TITLE,
            20,
            (255, 255, 255),
        )

    def draw_scene(
        self,
        target: pygame.Surface,
        session: SoundSession,
        *,
        wobble_x: int = 0,
        highlight_index: int | None = None,
        hovered_choice_idx: int | None = None,
        hovered_replay: bool = False,
        hovered_target: bool = False,
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_leo(target)

        current = session.current_challenge
        if current is None:
            return

        # 1. Target Presentation (Top Center)
        self._draw_target_area(target, current, is_hovered=hovered_target)

        # 2. Prompt Text
        self._draw_prompt(target, current)

        # 3. Choice Cards / Tiles
        self._draw_choices(
            target,
            current,
            wobble_x=wobble_x,
            highlight_index=highlight_index,
            hovered_choice_idx=hovered_choice_idx,
        )

        # 4. Top Controls
        self._draw_top_bar(target, session, is_replay_hovered=hovered_replay)

    def choice_rect_at(self, challenge: WorkshopChallenge, index: int) -> pygame.Rect:
        count = len(challenge.choices)
        y = 420
        if challenge.mode == WorkshopMode.FIND_SOUND:
            w, h = 150, 150
            spacing = 240
            cx = 272 + index * spacing
        else:
            w, h = 110, 110
            spacing = 180
            cx = 332 + index * spacing
        return pygame.Rect(cx - w // 2, y, w, h)

    def choice_at(self, point: tuple[int, int], challenge: WorkshopChallenge) -> int | None:
        for idx in range(len(challenge.choices)):
            rect = self.choice_rect_at(challenge, idx)
            if rect.inflate(20, 20).collidepoint(point):
                return idx
        return None

    def replay_contains(self, point: tuple[int, int]) -> bool:
        return REPLAY_RECT.collidepoint(point)

    def target_contains(self, point: tuple[int, int]) -> bool:
        return TARGET_SOUND_RECT.collidepoint(point) or TARGET_PICTURE_RECT.collidepoint(point)

    def _draw_target_area(
        self,
        target: pygame.Surface,
        challenge: WorkshopChallenge,
        *,
        is_hovered: bool = False,
    ) -> None:
        if challenge.mode == WorkshopMode.FIND_SOUND and challenge.target_unit is not None:
            draw_rect = TARGET_SOUND_RECT.move(0, -4) if is_hovered else TARGET_SOUND_RECT
            pygame.draw.rect(target, (10, 8, 6), TARGET_SOUND_RECT.move(0, 6), border_radius=22)
            pygame.draw.rect(target, (2, 132, 199), draw_rect, border_radius=22)
            border_c = (56, 189, 248) if is_hovered else (245, 158, 11)
            pygame.draw.rect(target, border_c, draw_rect, width=4, border_radius=22)

            letter_str = f"{challenge.target_unit.grapheme_upper} {challenge.target_unit.grapheme_lower}"
            l_surf = self._typography.render(letter_str, FontRole.DISPLAY, 38, (254, 240, 138))
            target.blit(
                l_surf,
                (
                    draw_rect.centerx - l_surf.get_width() // 2,
                    draw_rect.centery - l_surf.get_height() // 2,
                ),
            )

        elif challenge.target_word is not None:
            self._art.draw_picture_card(
                target,
                TARGET_PICTURE_RECT,
                challenge.target_word.symbol,
                is_hovered=is_hovered,
            )

            if challenge.mode == WorkshopMode.BUILD_WORD:
                self._draw_word_boxes(target, challenge.target_word)

    def _draw_word_boxes(self, target: pygame.Surface, word: WordItem) -> None:
        letters = [word.label[0]] + list(word.remainder)
        box_w, box_h = 64, 64
        total_w = len(letters) * (box_w + 14) - 14
        start_x = REFERENCE_WIDTH // 2 - total_w // 2
        y = 200

        initial_rect = pygame.Rect(start_x, y, box_w, box_h)
        self._art.draw_letter_tile(target, initial_rect, "?", is_empty_target=True)

        for i, ch in enumerate(word.remainder):
            r = pygame.Rect(start_x + (i + 1) * (box_w + 14), y, box_w, box_h)
            self._art.draw_letter_tile(target, r, ch)

    def _draw_choices(
        self,
        target: pygame.Surface,
        challenge: WorkshopChallenge,
        *,
        wobble_x: int = 0,
        highlight_index: int | None = None,
        hovered_choice_idx: int | None = None,
    ) -> None:
        for idx, item in enumerate(challenge.choices):
            rect = self.choice_rect_at(challenge, idx)
            is_hovered = (idx == hovered_choice_idx)
            draw_rect = rect.move(0, -6) if is_hovered else (rect.move(wobble_x, 0) if wobble_x != 0 else rect)
            is_highlighted = (highlight_index == idx)

            if isinstance(item, WordItem):
                self._art.draw_picture_card(
                    target,
                    draw_rect,
                    item.symbol,
                    is_hovered=is_hovered,
                )
            else:
                self._art.draw_letter_tile(
                    target,
                    draw_rect,
                    str(item),
                    is_highlighted=is_highlighted,
                    is_hovered=is_hovered,
                )

    def _draw_prompt(self, target: pygame.Surface, challenge: WorkshopChallenge) -> None:
        if challenge.mode == WorkshopMode.FIND_SOUND:
            text = "🔊 ➡️ 🖼️ ❓"
            y = 250
        elif challenge.mode == WorkshopMode.INITIAL_LETTER:
            text = "🖼️ ➡️ 🔤 ❓"
            y = 260
        else:
            text = "🔤 ➡️ 🧩 ❓"
            y = 285

        surf = self._typography.render(text, FontRole.DISPLAY, 36, (254, 240, 138))
        p_x = REFERENCE_WIDTH // 2 - surf.get_width() // 2
        banner = pygame.Rect(p_x - 24, y - 6, surf.get_width() + 48, surf.get_height() + 12)
        pygame.draw.rect(target, (15, 23, 42, 220), banner, border_radius=20)
        pygame.draw.rect(target, (217, 119, 6), banner, width=3, border_radius=20)
        target.blit(surf, (p_x, y))

    def _draw_top_bar(
        self,
        target: pygame.Surface,
        session: SoundSession,
        *,
        is_replay_hovered: bool = False,
    ) -> None:
        r_draw = REPLAY_RECT.move(0, -4) if is_replay_hovered else REPLAY_RECT
        pygame.draw.rect(target, (10, 15, 25), REPLAY_RECT.move(0, 6), border_radius=22)

        btn_col = (2, 132, 199) if is_replay_hovered else (3, 105, 161)
        border_col = (56, 189, 248) if is_replay_hovered else (255, 255, 255)

        pygame.draw.rect(target, btn_col, r_draw, border_radius=22)
        pygame.draw.rect(target, border_col, r_draw, width=3, border_radius=22)

        # Highlight
        hl = r_draw.inflate(-16, -r_draw.height + 8).move(0, -r_draw.height // 2 + 8)
        pygame.draw.rect(target, (186, 230, 253, 100), hl, border_radius=4)

        # Pre-rendered once from the Activity's localized `button.listen`; the
        # label must never be a literal in one language.
        speaker_icon = self._replay_label
        target.blit(
            speaker_icon,
            (
                r_draw.centerx - speaker_icon.get_width() // 2,
                r_draw.centery - speaker_icon.get_height() // 2,
            ),
        )

        # Progress badge
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 200), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 240, 138), badge_rect, width=2, border_radius=22)

        txt = f"{session.challenge_index + 1} / 6"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 240, 138))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )

    def _draw_leo(self, target: pygame.Surface) -> None:
        if self._art.leo is not None:
            target.blit(self._art.leo, (30, 385))
