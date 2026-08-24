"""Low-allocation, high-polish Pygame presentation for La Casa del Dieci."""

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
        pygame.Rect(236 + i * 114, 122, 98, 104)
        for i in range(5)
    ]
    + [
        pygame.Rect(236 + (i - 5) * 114, 268, 98, 104)
        for i in range(5, 10)
    ]
)

# Choice buttons for Operation modes
CHOICE_RECTS: Final[tuple[pygame.Rect, ...]] = (
    pygame.Rect(290, 480, 120, 84),
    pygame.Rect(452, 480, 120, 84),
    pygame.Rect(614, 480, 120, 84),
)

# Confirm button for Compose mode
CONFIRM_RECT: Final[pygame.Rect] = pygame.Rect(402, 480, 220, 84)


class TenHouseRenderer:
    """Render the 10-room townhouse, Dani guide, prompt, and interactive controls."""

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
            value: typography.render(str(value), FontRole.DISPLAY, 50, (255, 255, 255))
            for value in range(11)
        }
        self._small_numbers = {
            value: typography.render(str(value), FontRole.TITLE, 16, (180, 83, 9))
            for value in range(1, 11)
        }

        # Cache Confirm label
        self._confirm_label = typography.render(
            resources.text("button.confirm"),
            FontRole.TITLE,
            24,
            (255, 255, 255),
        )

    def draw_scene(
        self,
        target: pygame.Surface,
        session: TenHouseSession,
        *,
        wobble_x: int = 0,
        highlight_rooms: bool = False,
        hovered_room: int | None = None,
        hovered_choice: int | None = None,
        hovered_confirm: bool = False,
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_dani(target)

        current = session.current_challenge
        if current is None:
            return

        # 1. Draw 10 Rooms
        for idx, (rect, is_lit) in enumerate(zip(ROOM_RECTS, session.room_states)):
            is_focused = (not session.focus_in_choices and session.focused_room == idx)
            is_hovered = (idx == hovered_room)
            self._draw_room(
                target,
                rect,
                is_lit,
                idx + 1,
                is_focused=is_focused,
                is_hovered=is_hovered,
                highlight=highlight_rooms,
            )

        # 2. Draw Prompt / Equation
        self._draw_prompt(target, current, session)

        # 3. Draw Controls (Choices or Confirm)
        if current.mode == OperationMode.COMPOSE:
            self._draw_confirm_button(target, session, is_hovered=hovered_confirm)
        else:
            self._draw_choice_buttons(
                target,
                current,
                session,
                wobble_x=wobble_x,
                hovered_idx=hovered_choice,
            )

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

    def choice_index_at(self, point: tuple[int, int], challenge: TenHouseChallenge) -> int | None:
        if challenge.mode == OperationMode.COMPOSE:
            return None
        for idx, rect in enumerate(CHOICE_RECTS):
            if rect.collidepoint(point):
                return idx
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
        is_hovered: bool = False,
        highlight: bool = False,
    ) -> None:
        # Window frame shadow
        pygame.draw.rect(target, (15, 23, 42, 60), rect.move(0, 4), border_radius=12)

        # Outer wooden window frame
        frame_color = (56, 189, 248) if (is_focused or is_hovered) else (217, 119, 6)
        pygame.draw.rect(target, frame_color, rect, width=4, border_radius=12)

        inner = rect.inflate(-8, -8)
        if is_lit:
            # Lit warm golden yellow window with cozy glow
            pygame.draw.rect(target, (254, 240, 138), inner, border_radius=8)
            # Window mullions
            pygame.draw.line(target, (245, 158, 11), (inner.centerx, inner.top + 2), (inner.centerx, inner.bottom - 2), 3)
            pygame.draw.line(target, (245, 158, 11), (inner.left + 2, inner.centery), (inner.right - 2, inner.centery), 3)
            # Warm glowing lamp
            pygame.draw.circle(target, (255, 255, 255), inner.center, 14)
            pygame.draw.circle(target, (251, 191, 36), inner.center, 9)
        else:
            # Unlit dark cozy room
            pygame.draw.rect(target, (30, 41, 59), inner, border_radius=8)
            pygame.draw.line(target, (51, 65, 85), (inner.centerx, inner.top + 2), (inner.centerx, inner.bottom - 2), 2)
            pygame.draw.line(target, (51, 65, 85), (inner.left + 2, inner.centery), (inner.right - 2, inner.centery), 2)
            # Little sleeping star
            pygame.draw.circle(target, (100, 116, 139), inner.center, 3)

        # Room index tag
        badge_rect = pygame.Rect(rect.left + 6, rect.top + 6, 20, 20)
        pygame.draw.rect(target, (255, 251, 235), badge_rect, border_radius=6)
        num_surf = self._small_numbers.get(room_num)
        if num_surf:
            target.blit(num_surf, (badge_rect.centerx - num_surf.get_width() // 2, badge_rect.centery - num_surf.get_height() // 2))

        # Highlight on retry
        if highlight and is_lit:
            pygame.draw.rect(target, (234, 179, 8), rect.inflate(6, 6), width=4, border_radius=14)

    def _draw_prompt(
        self,
        target: pygame.Surface,
        challenge: TenHouseChallenge,
        session: TenHouseSession,
    ) -> None:
        p_y = 412
        if challenge.mode == OperationMode.COMPOSE:
            # Giant visual target number + live counter pill
            target_str = f"🎯 {challenge.target}"
            t_surf = self._typography.render(target_str, FontRole.DISPLAY, 36, (254, 240, 138))

            count_str = f"💡 {session.lit_count} / {challenge.target}"
            match_col = (134, 239, 172) if session.lit_count == challenge.target else (255, 255, 255)
            c_surf = self._typography.render(count_str, FontRole.TITLE, 26, match_col)

            total_w = t_surf.get_width() + c_surf.get_width() + 48
            p_x = REFERENCE_WIDTH // 2 - total_w // 2
            banner = pygame.Rect(p_x - 20, p_y - 6, total_w + 40, 52)
            pygame.draw.rect(target, (15, 23, 42, 220), banner, border_radius=20)
            b_col = (34, 197, 94) if session.lit_count == challenge.target else (217, 119, 6)
            pygame.draw.rect(target, b_col, banner, width=3, border_radius=20)

            target.blit(t_surf, (p_x, p_y + 2))
            target.blit(c_surf, (p_x + t_surf.get_width() + 32, p_y + 8))
            return

        elif challenge.mode == OperationMode.ADD:
            text = f"{challenge.starting_lit} 💡 + {challenge.delta} 💡 = ❓"
        elif challenge.mode == OperationMode.TAKE_AWAY:
            text = f"{challenge.starting_lit} 💡 - {challenge.delta} 💡 = ❓"
        elif challenge.mode == OperationMode.MISSING_PART:
            text = f"{challenge.starting_lit} 💡 + ❓ = {challenge.target} 💡"
        else:
            text = f"🎯 {challenge.target}"

        prompt_surf = self._typography.render(text, FontRole.DISPLAY, 34, (254, 240, 138))
        p_x = REFERENCE_WIDTH // 2 - prompt_surf.get_width() // 2
        banner = pygame.Rect(p_x - 24, p_y - 6, prompt_surf.get_width() + 48, prompt_surf.get_height() + 12)
        pygame.draw.rect(target, (15, 23, 42, 220), banner, border_radius=20)
        pygame.draw.rect(target, (217, 119, 6), banner, width=3, border_radius=20)
        target.blit(prompt_surf, (p_x, p_y))

    def _draw_confirm_button(
        self,
        target: pygame.Surface,
        session: TenHouseSession,
        *,
        is_hovered: bool = False,
    ) -> None:
        is_focused = (session.focus_in_choices and session.focused_choice == 0)
        is_ready = session.lit_count > 0
        draw_rect = CONFIRM_RECT.move(0, -4) if (is_hovered or is_focused) else CONFIRM_RECT

        # Shadow
        pygame.draw.rect(target, (10, 20, 30), CONFIRM_RECT.move(0, 6), border_radius=22)

        bg_col = (22, 163, 74) if is_ready else (71, 85, 105)
        border_col = (56, 189, 248) if (is_focused or is_hovered) else (134, 239, 172) if is_ready else (100, 116, 139)

        pygame.draw.rect(target, bg_col, draw_rect, border_radius=22)
        pygame.draw.rect(target, border_col, draw_rect, width=4, border_radius=22)

        # Highlight line
        if is_ready:
            hl = draw_rect.inflate(-16, -draw_rect.height + 8).move(0, -draw_rect.height // 2 + 8)
            pygame.draw.rect(target, (187, 247, 208, 120), hl, border_radius=4)

        # Big OK Checkmark label
        confirm_surf = self._typography.render("OK ✅", FontRole.TITLE, 30, (255, 255, 255))
        target.blit(
            confirm_surf,
            (
                draw_rect.centerx - confirm_surf.get_width() // 2,
                draw_rect.centery - confirm_surf.get_height() // 2,
            ),
        )

    def _draw_choice_buttons(
        self,
        target: pygame.Surface,
        challenge: TenHouseChallenge,
        session: TenHouseSession,
        *,
        wobble_x: int = 0,
        hovered_idx: int | None = None,
    ) -> None:
        for idx, (rect, val) in enumerate(zip(CHOICE_RECTS, challenge.choice_values)):
            is_focused = (session.focus_in_choices and session.focused_choice == idx)
            is_hovered = (idx == hovered_idx)
            draw_rect = rect.move(0, -4) if (is_hovered or is_focused) else rect
            if wobble_x != 0 and is_focused:
                draw_rect = draw_rect.move(wobble_x, 0)

            # Drop shadow
            pygame.draw.rect(target, (10, 20, 30), rect.move(0, 6), border_radius=22)

            border_col = (56, 189, 248) if (is_focused or is_hovered) else (245, 158, 11)

            pygame.draw.rect(target, (2, 132, 199), draw_rect, border_radius=22)
            pygame.draw.rect(target, border_col, draw_rect, width=4, border_radius=22)

            # Highlight
            hl = draw_rect.inflate(-16, -draw_rect.height + 8).move(0, -draw_rect.height // 2 + 8)
            pygame.draw.rect(target, (186, 230, 253, 100), hl, border_radius=4)

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
            target.blit(self._art.dani, (20, 385))

    def _draw_progress_badge(self, target: pygame.Surface, session: TenHouseSession) -> None:
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 200), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 240, 138), badge_rect, width=2, border_radius=22)

        txt = f"{session.challenge_index + 1} / 6"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 240, 138))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )
