"""High-polish presentation renderer for Festa delle Rime."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .rhyme_art import RhymeArt
    from .rhyme_content import RhymeMode
    from .rhyme_model import REFERENCE_WIDTH, RhymeChallenge, RhymeSession
else:
    from rhyme_art import RhymeArt
    from rhyme_content import RhymeMode
    from rhyme_model import REFERENCE_WIDTH, RhymeChallenge, RhymeSession


REPLAY_RECT: Final[pygame.Rect] = pygame.Rect(80, 24, 180, 48)
TARGET_RECT: Final[pygame.Rect] = pygame.Rect(442, 85, 140, 150)


class RhymeRenderer:
    """Render the festival lanterns, prompt bar, replay button, and Leo mascot."""

    def __init__(
        self,
        art: RhymeArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources

        self._replay_label = typography.render(
            f"🔊 {resources.text('button.replay')}",
            FontRole.TITLE,
            20,
            (255, 255, 255),
        )

    def draw_scene(
        self,
        target: pygame.Surface,
        session: RhymeSession,
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

        # 1. Target Lantern (for match and alliteration)
        if current.target_item is not None:
            self._art.draw_lantern(
                target,
                TARGET_RECT,
                current.target_item,
                color_idx=0,
                is_lit=True,
                is_highlighted=True,
                is_hovered=hovered_target,
            )

        # 2. Prompt Text
        self._draw_prompt(target, current)

        # 3. Choice Lanterns
        self._draw_choices(
            target,
            current,
            wobble_x=wobble_x,
            highlight_index=highlight_index,
            hovered_choice_idx=hovered_choice_idx,
        )

        # 4. Top Controls
        self._draw_top_bar(target, session, is_replay_hovered=hovered_replay)

    def choice_rect_at(self, challenge: RhymeChallenge, index: int) -> pygame.Rect:
        count = len(challenge.choices)
        w, h = 154, 184
        y = 310
        if count == 2:
            cx = 360 if index == 0 else 664
        else:
            spacing = 240
            cx = 272 + index * spacing
        return pygame.Rect(cx - w // 2, y, w, h)

    def choice_at(self, point: tuple[int, int], challenge: RhymeChallenge) -> int | None:
        for idx in range(len(challenge.choices)):
            rect = self.choice_rect_at(challenge, idx)
            if rect.inflate(20, 20).collidepoint(point):
                return idx
        return None

    def replay_contains(self, point: tuple[int, int]) -> bool:
        return REPLAY_RECT.collidepoint(point)

    def target_contains(self, point: tuple[int, int]) -> bool:
        return TARGET_RECT.collidepoint(point)

    def _draw_choices(
        self,
        target: pygame.Surface,
        challenge: RhymeChallenge,
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
            self._art.draw_lantern(
                target,
                draw_rect,
                item,
                color_idx=idx + 1,
                is_lit=True,
                is_highlighted=is_highlighted,
                is_hovered=is_hovered,
            )

    def _draw_prompt(self, target: pygame.Surface, challenge: RhymeChallenge) -> None:
        if challenge.mode == RhymeMode.RHYME_MATCH:
            key = "prompt.rhyme"
        elif challenge.mode == RhymeMode.RHYME_ODD:
            key = "prompt.odd"
        else:
            key = "prompt.sound"

        text = self._resources.text(key)
        y = 250 if challenge.target_item is not None else 180
        surf = self._typography.render(text, FontRole.TITLE, 26, (254, 240, 138))
        p_x = REFERENCE_WIDTH // 2 - surf.get_width() // 2
        banner = pygame.Rect(p_x - 24, y - 6, surf.get_width() + 48, surf.get_height() + 12)
        pygame.draw.rect(target, (15, 23, 42, 200), banner, border_radius=16)
        pygame.draw.rect(target, (217, 119, 6), banner, width=2, border_radius=16)
        target.blit(surf, (p_x, y))

    def _draw_top_bar(
        self,
        target: pygame.Surface,
        session: RhymeSession,
        *,
        is_replay_hovered: bool = False,
    ) -> None:
        # Replay button with 3D bevel and hover lift
        r_draw = REPLAY_RECT.move(0, -4) if is_replay_hovered else REPLAY_RECT
        pygame.draw.rect(target, (10, 15, 25), REPLAY_RECT.move(0, 6), border_radius=22)

        btn_col = (2, 132, 199) if is_replay_hovered else (3, 105, 161)
        border_col = (56, 189, 248) if is_replay_hovered else (255, 255, 255)

        pygame.draw.rect(target, btn_col, r_draw, border_radius=22)
        pygame.draw.rect(target, border_col, r_draw, width=3, border_radius=22)

        # Highlight
        hl = r_draw.inflate(-16, -r_draw.height + 8).move(0, -r_draw.height // 2 + 8)
        pygame.draw.rect(target, (186, 230, 253, 100), hl, border_radius=4)

        target.blit(
            self._replay_label,
            (
                r_draw.centerx - self._replay_label.get_width() // 2,
                r_draw.centery - self._replay_label.get_height() // 2,
            ),
        )

        # Progress badge
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 200), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 240, 138), badge_rect, width=2, border_radius=22)

        txt = f"{session.challenge_index + 1} / 8"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 240, 138))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )

    def _draw_leo(self, target: pygame.Surface) -> None:
        if self._art.leo is not None:
            target.blit(self._art.leo, (30, 385))
