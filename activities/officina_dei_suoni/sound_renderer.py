"""Presentation renderer for Officina dei Suoni."""

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


REPLAY_RECT: Final[pygame.Rect] = pygame.Rect(80, 24, 160, 44)
TARGET_SOUND_RECT: Final[pygame.Rect] = pygame.Rect(462, 85, 100, 95)
TARGET_PICTURE_RECT: Final[pygame.Rect] = pygame.Rect(457, 75, 110, 110)


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
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_leo(target)

        current = session.current_challenge
        if current is None:
            return

        # 1. Target Presentation (Top Center)
        self._draw_target_area(target, current)

        # 2. Prompt Text
        self._draw_prompt(target, current)

        # 3. Choice Cards / Tiles
        self._draw_choices(target, current, wobble_x=wobble_x, highlight_index=highlight_index)

        # 4. Top Controls
        self._draw_top_bar(target, session)

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

    def _draw_target_area(self, target: pygame.Surface, challenge: WorkshopChallenge) -> None:
        if challenge.mode == WorkshopMode.FIND_SOUND and challenge.target_unit is not None:
            # Golden sound speaker button with uppercase/lowercase letter
            pygame.draw.rect(target, (2, 132, 199), TARGET_SOUND_RECT, border_radius=22)
            pygame.draw.rect(target, (56, 189, 248), TARGET_SOUND_RECT, width=3, border_radius=22)

            letter_str = f"{challenge.target_unit.grapheme_upper} {challenge.target_unit.grapheme_lower}"
            l_surf = self._typography.render(letter_str, FontRole.DISPLAY, 36, (254, 240, 138))
            target.blit(
                l_surf,
                (
                    TARGET_SOUND_RECT.centerx - l_surf.get_width() // 2,
                    TARGET_SOUND_RECT.centery - l_surf.get_height() // 2,
                ),
            )

        elif challenge.target_word is not None:
            # Target picture card
            self._art.draw_picture_card(
                target,
                TARGET_PICTURE_RECT,
                challenge.target_word.symbol,
                is_highlighted=True,
            )

            # In L3 (build word): Draw connected sound boxes [ ? ][ E ][ L ][ A ]
            if challenge.mode == WorkshopMode.BUILD_WORD:
                self._draw_word_boxes(target, challenge.target_word)

    def _draw_word_boxes(self, target: pygame.Surface, word: WordItem) -> None:
        letters = [word.label[0]] + list(word.remainder)
        box_w, box_h = 60, 60
        total_w = len(letters) * (box_w + 12) - 12
        start_x = REFERENCE_WIDTH // 2 - total_w // 2
        y = 200

        # Initial box [ ? ]
        initial_rect = pygame.Rect(start_x, y, box_w, box_h)
        self._art.draw_letter_tile(target, initial_rect, "?", is_empty_target=True)

        # Remaining letters
        for i, ch in enumerate(word.remainder):
            r = pygame.Rect(start_x + (i + 1) * (box_w + 12), y, box_w, box_h)
            self._art.draw_letter_tile(target, r, ch)

    def _draw_choices(
        self,
        target: pygame.Surface,
        challenge: WorkshopChallenge,
        *,
        wobble_x: int = 0,
        highlight_index: int | None = None,
    ) -> None:
        for idx, item in enumerate(challenge.choices):
            rect = self.choice_rect_at(challenge, idx)
            draw_rect = rect.move(wobble_x, 0) if wobble_x != 0 else rect
            is_highlighted = (highlight_index == idx)

            if isinstance(item, WordItem):
                self._art.draw_picture_card(
                    target,
                    draw_rect,
                    item.symbol,
                    is_highlighted=is_highlighted,
                )
            else:
                self._art.draw_letter_tile(
                    target,
                    draw_rect,
                    str(item),
                    is_highlighted=is_highlighted,
                )

    def _draw_prompt(self, target: pygame.Surface, challenge: WorkshopChallenge) -> None:
        if challenge.mode == WorkshopMode.FIND_SOUND:
            key = "prompt.find_sound"
            y = 250
        elif challenge.mode == WorkshopMode.INITIAL_LETTER:
            key = "prompt.first_sound"
            y = 260
        else:
            key = "prompt.build_word"
            y = 280

        text = self._resources.text(key)
        surf = self._typography.render(text, FontRole.TITLE, 24, (254, 240, 138))
        target.blit(surf, (REFERENCE_WIDTH // 2 - surf.get_width() // 2, y))

    def _draw_top_bar(self, target: pygame.Surface, session: SoundSession) -> None:
        # Replay button
        pygame.draw.rect(target, (3, 105, 161), REPLAY_RECT, border_radius=22)
        pygame.draw.rect(target, (56, 189, 248), REPLAY_RECT, width=2, border_radius=22)
        target.blit(
            self._replay_label,
            (
                REPLAY_RECT.centerx - self._replay_label.get_width() // 2,
                REPLAY_RECT.centery - self._replay_label.get_height() // 2,
            ),
        )

        # Progress badge
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 180), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 240, 138), badge_rect, width=2, border_radius=22)

        txt = f"{session.challenge_index + 1} / 6"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 240, 138))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )

    def _draw_leo(self, target: pygame.Surface) -> None:
        if self._art.leo is not None:
            target.blit(self._art.leo, (30, 390))
        else:
            cx, cy = 90, 480
            pygame.draw.rect(target, (2, 132, 199), (cx - 40, cy - 40, 80, 80), border_radius=16)
            pygame.draw.circle(target, (255, 255, 255), (cx - 16, cy - 10), 10)
            pygame.draw.circle(target, (255, 255, 255), (cx + 16, cy - 10), 10)
            pygame.draw.arc(target, (255, 255, 255), (cx - 20, cy + 2, 40, 24), 3.4, 6.0, 4)
