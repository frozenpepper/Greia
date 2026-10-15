"""Low-allocation Pygame scene presentation for La Casa del Dieci.

The renderer owns the house, windows and cast; interactive controls (prompt,
answers, OK, progress) are shared control-kit controls owned by
``ten_house_controls.TenHouseControls`` (ADR 0037).
"""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_feedback import CastFeedback
from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .ten_house_art import TenHouseArt
    from .ten_house_model import (
        OperationMode,
        REFERENCE_WIDTH,
        ROOM_COUNT,
        TenHouseChallenge,
        TenHouseSession,
    )
else:
    from ten_house_art import TenHouseArt
    from ten_house_model import (
        OperationMode,
        REFERENCE_WIDTH,
        ROOM_COUNT,
        TenHouseChallenge,
        TenHouseSession,
    )


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

# Dani stands on the lawn at the left; feet midpoint in logical space.
DANI_MIDBOTTOM: Final[tuple[int, int]] = (105, 572)
DANI_HEIGHT: Final = 190


class TenHouseRenderer:
    """Render the 10-room townhouse, the Dani guide and room states.

    Controls are drawn afterwards by the shared ``ControlLayer``; the kit also
    draws the focus ring around the focused window.
    """

    def __init__(
        self,
        art: TenHouseArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
        *,
        cast: CastFeedback | None = None,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources
        self.cast = cast
        self._small_numbers = {
            value: typography.render(str(value), FontRole.TITLE, 16, (180, 83, 9))
            for value in range(1, 11)
        }

    def draw_scene(
        self,
        target: pygame.Surface,
        session: TenHouseSession,
        *,
        highlight_rooms: bool = False,
        hovered_room: int | None = None,
        is_celebrating: bool = False,
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_dani(target)

        current = session.current_challenge
        if current is None:
            return
        for idx, (rect, is_lit) in enumerate(zip(ROOM_RECTS, session.room_states)):
            self._draw_room(
                target,
                rect,
                is_lit,
                idx + 1,
                is_hovered=(idx == hovered_room),
                highlight=highlight_rooms or is_celebrating,
            )
        if is_celebrating:
            self._draw_celebration_badge(target)

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
        is_hovered: bool = False,
        highlight: bool = False,
    ) -> None:
        pygame.draw.rect(target, (15, 23, 42), rect.move(0, 4), border_radius=12)
        frame_color = (56, 189, 248) if is_hovered else (217, 119, 6)
        pygame.draw.rect(target, frame_color, rect, width=4, border_radius=12)

        inner = rect.inflate(-8, -8)
        if is_lit:
            pygame.draw.rect(target, (254, 240, 138), inner, border_radius=8)
            pygame.draw.line(target, (245, 158, 11), (inner.centerx, inner.top + 2), (inner.centerx, inner.bottom - 2), 3)
            pygame.draw.line(target, (245, 158, 11), (inner.left + 2, inner.centery), (inner.right - 2, inner.centery), 3)
            pygame.draw.circle(target, (255, 255, 255), inner.center, 14)
            pygame.draw.circle(target, (251, 191, 36), inner.center, 9)
        else:
            pygame.draw.rect(target, (30, 41, 59), inner, border_radius=8)
            pygame.draw.line(target, (51, 65, 85), (inner.centerx, inner.top + 2), (inner.centerx, inner.bottom - 2), 2)
            pygame.draw.line(target, (51, 65, 85), (inner.left + 2, inner.centery), (inner.right - 2, inner.centery), 2)
            pygame.draw.circle(target, (100, 116, 139), inner.center, 3)

        badge_rect = pygame.Rect(rect.left + 6, rect.top + 6, 20, 20)
        pygame.draw.rect(target, (255, 251, 235), badge_rect, border_radius=6)
        num_surf = self._small_numbers.get(room_num)
        if num_surf:
            target.blit(num_surf, num_surf.get_rect(center=badge_rect.center))

        if highlight and is_lit:
            pygame.draw.rect(target, (234, 179, 8), rect.inflate(6, 6), width=4, border_radius=14)

    def _draw_celebration_badge(self, target: pygame.Surface) -> None:
        cx, cy = REFERENCE_WIDTH // 2, 70
        pygame.draw.circle(target, (10, 20, 30), (cx, cy + 3), 28)
        pygame.draw.circle(target, (34, 197, 94), (cx, cy), 28)
        pygame.draw.circle(target, (255, 255, 255), (cx, cy), 28, 4)
        check_pts = [(cx - 12, cy), (cx - 4, cy + 10), (cx + 12, cy - 9)]
        pygame.draw.lines(target, (255, 255, 255), False, check_pts, 5)

    def _draw_dani(self, target: pygame.Surface) -> None:
        if self.cast is not None and self.cast.available:
            self.cast.draw(target, DANI_MIDBOTTOM)
        elif self._art.dani is not None:
            target.blit(self._art.dani, (20, 385))
