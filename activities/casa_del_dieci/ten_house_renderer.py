"""Low-allocation Pygame presentation for La Casa del Dieci."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .ten_house_art import TenHouseArt
    from .ten_house_model import OperationMode, TenHouseChallenge, TenHouseSession, REFERENCE_WIDTH
else:
    from ten_house_art import TenHouseArt
    from ten_house_model import OperationMode, TenHouseChallenge, TenHouseSession, REFERENCE_WIDTH


# 2x5 Window rects
ROOM_RECTS: Final[tuple[pygame.Rect, ...]] = tuple(
    [
        pygame.Rect(236 + i * 114, 120, 98, 104)
        for i in range(5)
    ]
    + [
        pygame.Rect(236 + (i - 5) * 114, 264, 98, 104)
        for i in range(5, 10)
    ]
)

# Choice buttons for Operation modes
CHOICE_RECTS: Final[tuple[pygame.Rect, ...]] = (
    pygame.Rect(300, 480, 114, 80),
    pygame.Rect(455, 480, 114, 80),
    pygame.Rect(610, 480, 114, 80),
)

# Confirm button for Compose mode
CONFIRM_RECT: Final[pygame.Rect] = pygame.Rect(412, 480, 200, 76)


class TenHouseRenderer:
    """Render the 10-room house, Dani guide, prompt, and interactive controls."""

    def __init__(
        self,
        art: TenHouseArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources

        # Cache numbers 0..10
        self._number_surfaces = {
            value: typography.render(str(value), FontRole.DISPLAY, 48, (255, 255, 255))
            for value in range(11)
        }
        self._small_numbers = {
            value: typography.render(str(value), FontRole.BODY, 20, (148, 163, 184))
            for value in range(1, 11)
        }

        # Cache Confirm label
        self._confirm_label = typography.render(
            resources.text("button.confirm"),
            FontRole.TITLE,
            26,
            (255, 255, 255),
        )

    def draw_scene(
        self,
        target: pygame.Surface,
        session: TenHouseSession,
        *,
        wobble_x: int = 0,
        highlight_rooms: bool = False,
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_dani(target)

        current = session.current_challenge
        if current is None:
            return

        # 1. Draw 10 Rooms
        for idx, (rect, is_lit) in enumerate(zip(ROOM_RECTS, session.room_states)):
            is_focused = (not session.focus_in_choices and session.focused_room == idx)
            self._draw_room(target, rect, is_lit, idx + 1, is_focused=is_focused, highlight=highlight_rooms)

        # 2. Draw Prompt / Equation
        self._draw_prompt(target, current, session)

        # 3. Draw Controls (Choices or Confirm)
        if current.mode == OperationMode.COMPOSE:
            self._draw_confirm_button(target, session)
        else:
            self._draw_choice_buttons(target, current, session, wobble_x=wobble_x)

        # 4. Progress badge (e.g. 1/6 .. 6/6)
        self._draw_progress_badge(target, session)

    def room_at(self, point: tuple[int, int]) -> int | None:
        for idx, rect in enumerate(ROOM_RECTS):
            if rect.collidepoint(point):
                return idx
        return None

    def choice_at(self, point: tuple[int, int], challenge: TenHouseChallenge) -> int | None:
        if challenge.mode == OperationMode.COMPOSE:
            return None
        for rect, val in zip(CHOICE_RECTS, challenge.choice_values):
            if rect.collidepoint(point):
                return val
        return None

    def confirm_contains(self, point: tuple[int, int]) -> bool:
        return CONFIRM_RECT.collidepoint(point)

    def _draw_room(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        is_lit: bool,
        room_num: int,
        *,
        is_focused: bool = False,
        highlight: bool = False,
    ) -> None:
        if is_lit:
            # Lit warm golden yellow room
            pygame.draw.rect(target, (254, 240, 138), rect, border_radius=10)
            pygame.draw.rect(target, (245, 158, 11), rect, width=4, border_radius=10)
            # Cozy soft window panes
            pygame.draw.line(target, (217, 119, 6), (rect.centerx, rect.top + 6), (rect.centerx, rect.bottom - 6), 2)
            pygame.draw.line(target, (217, 119, 6), (rect.left + 6, rect.centery), (rect.right - 6, rect.centery), 2)
            # Lit lamp glow circle
            pygame.draw.circle(target, (255, 255, 255), rect.center, 12)
            pygame.draw.circle(target, (251, 191, 36), rect.center, 8)
        else:
            # Unlit dark room
            pygame.draw.rect(target, (51, 65, 85), rect, border_radius=10)
            pygame.draw.rect(target, (30, 41, 59), rect, width=4, border_radius=10)
            # Subtle closed window panes
            pygame.draw.line(target, (71, 85, 105), (rect.centerx, rect.top + 6), (rect.centerx, rect.bottom - 6), 2)
            pygame.draw.line(target, (71, 85, 105), (rect.left + 6, rect.centery), (rect.right - 6, rect.centery), 2)

        # Room index number at top left of window
        num_surf = self._small_numbers.get(room_num)
        if num_surf:
            target.blit(num_surf, (rect.left + 6, rect.top + 4))

        # Focus / Highlight outline
        if is_focused:
            pygame.draw.rect(target, (56, 189, 248), rect.inflate(8, 8), width=3, border_radius=14)
        elif highlight and is_lit:
            pygame.draw.rect(target, (234, 179, 8), rect.inflate(6, 6), width=3, border_radius=12)

    def _draw_prompt(
        self,
        target: pygame.Surface,
        challenge: TenHouseChallenge,
        session: TenHouseSession,
    ) -> None:
        if challenge.mode == OperationMode.COMPOSE:
            if challenge.target == 1:
                text = self._resources.text("prompt.compose_one")
            else:
                text = self._resources.text("prompt.compose", {"target": str(challenge.target)})
        elif challenge.mode == OperationMode.ADD:
            text = f"{challenge.starting_lit} + {challenge.delta} = ?"
        elif challenge.mode == OperationMode.TAKE_AWAY:
            text = f"{challenge.starting_lit} - {challenge.delta} = ?"
        elif challenge.mode == OperationMode.MISSING_PART:
            text = self._resources.text("prompt.missing_part", {"target": str(challenge.target)})

        prompt_surf = self._typography.render(text, FontRole.TITLE, 28, (254, 243, 199))
        target.blit(
            prompt_surf,
            (REFERENCE_WIDTH // 2 - prompt_surf.get_width() // 2, 420),
        )

    def _draw_confirm_button(self, target: pygame.Surface, session: TenHouseSession) -> None:
        is_focused = (session.focus_in_choices and session.focused_choice == 0)
        is_ready = session.lit_count > 0

        bg_col = (34, 197, 94) if is_ready else (100, 116, 139)
        border_col = (255, 255, 255) if is_focused else (22, 101, 52) if is_ready else (71, 85, 105)

        if is_focused:
            pygame.draw.rect(target, (56, 189, 248), CONFIRM_RECT.inflate(8, 8), border_radius=22)

        pygame.draw.rect(target, bg_col, CONFIRM_RECT, border_radius=18)
        pygame.draw.rect(target, border_col, CONFIRM_RECT, width=3, border_radius=18)

        target.blit(
            self._confirm_label,
            (
                CONFIRM_RECT.centerx - self._confirm_label.get_width() // 2,
                CONFIRM_RECT.centery - self._confirm_label.get_height() // 2,
            ),
        )

    def _draw_choice_buttons(
        self,
        target: pygame.Surface,
        challenge: TenHouseChallenge,
        session: TenHouseSession,
        *,
        wobble_x: int = 0,
    ) -> None:
        for idx, (rect, val) in enumerate(zip(CHOICE_RECTS, challenge.choice_values)):
            is_focused = (session.focus_in_choices and session.focused_choice == idx)
            draw_rect = rect.move(wobble_x, 0) if (wobble_x != 0 and is_focused) else rect

            if is_focused:
                pygame.draw.rect(target, (56, 189, 248), draw_rect.inflate(8, 8), border_radius=22)

            pygame.draw.rect(target, (37, 99, 235), draw_rect, border_radius=18)
            pygame.draw.rect(target, (255, 255, 255), draw_rect, width=3, border_radius=18)

            num_surf = self._number_surfaces.get(val)
            if num_surf:
                target.blit(
                    num_surf,
                    (
                        draw_rect.centerx - num_surf.get_width() // 2,
                        draw_rect.centery - num_surf.get_height() // 2,
                    ),
                )

    def _draw_dani(self, target: pygame.Surface) -> None:
        if self._art.dani is not None:
            target.blit(self._art.dani, (20, 390))
        else:
            # Fallback cute robot shape
            cx, cy = 90, 480
            pygame.draw.rect(target, (59, 130, 246), (cx - 40, cy - 40, 80, 80), border_radius=16)
            pygame.draw.circle(target, (255, 255, 255), (cx - 16, cy - 10), 10)
            pygame.draw.circle(target, (255, 255, 255), (cx + 16, cy - 10), 10)
            pygame.draw.circle(target, (15, 23, 42), (cx - 16, cy - 10), 5)
            pygame.draw.circle(target, (15, 23, 42), (cx + 16, cy - 10), 5)
            pygame.draw.arc(target, (255, 255, 255), (cx - 20, cy + 2, 40, 24), 3.4, 6.0, 4)

    def _draw_progress_badge(self, target: pygame.Surface, session: TenHouseSession) -> None:
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 180), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 243, 199), badge_rect, width=2, border_radius=22)

        txt = f"{session.challenge_index + 1} / 6"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 243, 199))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )
