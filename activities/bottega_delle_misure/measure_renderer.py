"""Low-allocation, high-polish Pygame presentation for La Bottega delle Misure."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .measure_art import (
        PARCEL_PALETTES,
        UNIT_H_PX,
        UNIT_PX,
        MeasureArt,
    )
    from .measure_model import (
        Attribute,
        MeasureChallenge,
        MeasureItem,
        MeasureMode,
        MeasureSession,
        REFERENCE_WIDTH,
    )
else:
    from measure_art import (
        PARCEL_PALETTES,
        UNIT_H_PX,
        UNIT_PX,
        MeasureArt,
    )
    from measure_model import (
        Attribute,
        MeasureChallenge,
        MeasureItem,
        MeasureMode,
        MeasureSession,
        REFERENCE_WIDTH,
    )


# Choice buttons for numerical answers
CHOICE_RECTS: Final[tuple[pygame.Rect, ...]] = (
    pygame.Rect(310, 480, 116, 80),
    pygame.Rect(454, 480, 116, 80),
    pygame.Rect(598, 480, 116, 80),
)


class MeasureRenderer:
    """Render parcels, measuring rail, unit blocks, Dani, and touch controls."""

    def __init__(
        self,
        art: MeasureArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources

        # Cache numbers 1..9
        self._number_surfaces = {
            value: typography.render(str(value), FontRole.DISPLAY, 46, (255, 255, 255))
            for value in range(1, 10)
        }
        self._small_numbers = {
            value: typography.render(str(value), FontRole.TITLE, 18, (120, 53, 15))
            for value in range(1, 10)
        }

    def draw_scene(
        self,
        target: pygame.Surface,
        session: MeasureSession,
        *,
        wobble_x: int = 0,
        show_baseline: bool = False,
        hovered_item_id: str | None = None,
        hovered_choice_idx: int | None = None,
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_dani(target)

        current = session.current_challenge
        if current is None:
            return

        # 1. Draw Items according to Mode
        if current.mode == MeasureMode.COMPARE:
            self._draw_compare_items(
                target,
                current,
                wobble_x=wobble_x,
                show_baseline=show_baseline,
                hovered_item_id=hovered_item_id,
            )
        elif current.mode == MeasureMode.ORDER:
            self._draw_order_items(
                target,
                current,
                session,
                wobble_x=wobble_x,
                hovered_item_id=hovered_item_id,
            )
        elif current.mode in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            self._draw_measure_item_and_rail(target, current, session, wobble_x=wobble_x)

        # 2. Draw Prompt text
        self._draw_prompt(target, current)

        # 3. Draw Controls
        if current.mode in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            self._draw_measure_controls(target, current, hovered_choice_idx=hovered_choice_idx)

        # 4. Progress badge
        self._draw_progress_badge(target, session)

    def item_rect_at(self, challenge: MeasureChallenge, item_index: int) -> pygame.Rect:
        item = challenge.items[item_index]
        if challenge.mode == MeasureMode.COMPARE:
            if challenge.attribute == Attribute.LENGTH:
                w = item.units * UNIT_PX
                h = 72
                cx = 330 if item_index == 0 else 680
                return pygame.Rect(cx - w // 2, 340 - h, w, h)
            else:
                w = 96
                h = item.units * UNIT_H_PX
                cx = 350 if item_index == 0 else 660
                return pygame.Rect(cx - w // 2, 340 - h, w, h)

        if challenge.mode == MeasureMode.ORDER:
            count = len(challenge.items)
            spacing = 560 // max(1, count)
            cx = 280 + item_index * spacing
            if challenge.attribute == Attribute.LENGTH:
                w = item.units * (UNIT_PX - 6)
                h = 68
                return pygame.Rect(cx - w // 2, 340 - h, w, h)
            else:
                w = 88
                h = item.units * UNIT_H_PX
                return pygame.Rect(cx - w // 2, 340 - h, w, h)

        return pygame.Rect(0, 0, 0, 0)

    def item_at(self, point: tuple[int, int], challenge: MeasureChallenge) -> str | None:
        for idx, item in enumerate(challenge.items):
            rect = self.item_rect_at(challenge, idx)
            if rect.inflate(20, 20).collidepoint(point):
                return item.item_id
        return None

    def choice_at(self, point: tuple[int, int], challenge: MeasureChallenge) -> int | None:
        if challenge.mode not in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            return None
        for rect, val in zip(CHOICE_RECTS, challenge.choice_values):
            if rect.collidepoint(point):
                return val
        return None

    def choice_index_at(self, point: tuple[int, int], challenge: MeasureChallenge) -> int | None:
        if challenge.mode not in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            return None
        for idx, rect in enumerate(CHOICE_RECTS):
            if rect.collidepoint(point):
                return idx
        return None

    def _draw_compare_items(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        *,
        wobble_x: int = 0,
        show_baseline: bool = False,
        hovered_item_id: str | None = None,
    ) -> None:
        if show_baseline:
            if challenge.attribute == Attribute.LENGTH:
                pygame.draw.line(target, (245, 158, 11), (180, 180), (180, 340), 4)
            else:
                pygame.draw.line(target, (245, 158, 11), (200, 340), (820, 340), 4)

        for idx, item in enumerate(challenge.items):
            rect = self.item_rect_at(challenge, idx)
            is_hovered = (item.item_id == hovered_item_id)
            draw_rect = rect.move(0, -6) if is_hovered else (rect.move(wobble_x, 0) if wobble_x != 0 else rect)
            self._draw_parcel(target, draw_rect, item, is_hovered=is_hovered)

    def _draw_order_items(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        session: MeasureSession,
        *,
        wobble_x: int = 0,
        hovered_item_id: str | None = None,
    ) -> None:
        for idx, item in enumerate(challenge.items):
            rect = self.item_rect_at(challenge, idx)
            is_hovered = (item.item_id == hovered_item_id)
            draw_rect = rect.move(0, -6) if is_hovered else (rect.move(wobble_x, 0) if wobble_x != 0 else rect)
            self._draw_parcel(target, draw_rect, item, is_hovered=is_hovered)

            if item.item_id in session.selected_order_ids:
                order_num = session.selected_order_ids.index(item.item_id) + 1
                badge_center = (draw_rect.centerx, draw_rect.top - 18)
                pygame.draw.circle(target, (22, 163, 74), badge_center, 16)
                pygame.draw.circle(target, (255, 255, 255), badge_center, 16, 3)
                num_s = self._number_surfaces.get(order_num)
                if num_s:
                    target.blit(num_s, (badge_center[0] - num_s.get_width() // 2, badge_center[1] - num_s.get_height() // 2))

    def _draw_measure_item_and_rail(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        session: MeasureSession,
        *,
        wobble_x: int = 0,
    ) -> None:
        item = challenge.items[0]
        w = item.units * UNIT_PX
        h = 76
        parcel_rect = pygame.Rect(260 + wobble_x, 190, w, h)
        self._draw_parcel(target, parcel_rect, item)

        # Measuring rail below parcel
        rail_w = challenge.unit_capacity * UNIT_PX
        rail_rect = pygame.Rect(260, 276, rail_w, 48)
        pygame.draw.rect(target, (45, 25, 12), rail_rect.move(0, 4), border_radius=10)
        pygame.draw.rect(target, (120, 75, 42), rail_rect, border_radius=10)
        pygame.draw.rect(target, (217, 119, 6), rail_rect, width=3, border_radius=10)

        for u in range(challenge.unit_capacity):
            slot_rect = pygame.Rect(260 + u * UNIT_PX, 276, UNIT_PX, 48)
            if u < session.placed_blocks:
                pygame.draw.rect(target, (254, 240, 138), slot_rect.inflate(-4, -4), border_radius=8)
                pygame.draw.rect(target, (217, 119, 6), slot_rect.inflate(-4, -4), width=2, border_radius=8)
                num_s = self._small_numbers.get(u + 1)
                if num_s:
                    target.blit(num_s, (slot_rect.centerx - num_s.get_width() // 2, slot_rect.centery - num_s.get_height() // 2))
            else:
                pygame.draw.rect(target, (78, 48, 26), slot_rect.inflate(-6, -6), border_radius=6)

    def _draw_parcel(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        item: MeasureItem,
        *,
        is_hovered: bool = False,
    ) -> None:
        palette = PARCEL_PALETTES[item.color_index % len(PARCEL_PALETTES)]
        box_col, border_col, ribbon_col = palette

        # Drop shadow
        pygame.draw.rect(target, (10, 8, 6, 80), rect.move(0, 6), border_radius=14)

        # Gift box body
        pygame.draw.rect(target, box_col, rect, border_radius=14)
        border_c = (56, 189, 248) if is_hovered else border_col
        border_w = 5 if is_hovered else 3
        pygame.draw.rect(target, border_c, rect, width=border_w, border_radius=14)

        # Satin glossy highlight on box
        hl = rect.inflate(-8, -rect.height + 6).move(0, -rect.height // 2 + 6)
        pygame.draw.rect(target, (255, 255, 255, 120), hl, border_radius=3)

        # Ribbons
        if rect.width > rect.height:
            pygame.draw.rect(target, ribbon_col, (rect.centerx - 10, rect.top, 20, rect.height))
            # Bow on top
            pygame.draw.circle(target, ribbon_col, (rect.centerx - 10, rect.top - 4), 10)
            pygame.draw.circle(target, ribbon_col, (rect.centerx + 10, rect.top - 4), 10)
            pygame.draw.circle(target, (255, 255, 255), (rect.centerx, rect.top - 2), 6)
        else:
            pygame.draw.rect(target, ribbon_col, (rect.left, rect.centery - 10, rect.width, 20))
            pygame.draw.circle(target, ribbon_col, (rect.centerx - 10, rect.top - 4), 10)
            pygame.draw.circle(target, ribbon_col, (rect.centerx + 10, rect.top - 4), 10)
            pygame.draw.circle(target, (255, 255, 255), (rect.centerx, rect.top - 2), 6)

    def _draw_prompt(self, target: pygame.Surface, challenge: MeasureChallenge) -> None:
        text = self._resources.text(challenge.prompt_key)
        prompt_surf = self._typography.render(text, FontRole.TITLE, 26, (254, 240, 138))
        p_x = REFERENCE_WIDTH // 2 - prompt_surf.get_width() // 2
        p_y = 412
        banner = pygame.Rect(p_x - 24, p_y - 6, prompt_surf.get_width() + 48, prompt_surf.get_height() + 12)
        pygame.draw.rect(target, (15, 23, 42, 200), banner, border_radius=16)
        pygame.draw.rect(target, (217, 119, 6), banner, width=2, border_radius=16)
        target.blit(prompt_surf, (p_x, p_y))

    def _draw_measure_controls(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        *,
        hovered_choice_idx: int | None = None,
    ) -> None:
        for idx, (rect, val) in enumerate(zip(CHOICE_RECTS, challenge.choice_values)):
            is_hovered = (idx == hovered_choice_idx)
            draw_rect = rect.move(0, -4) if is_hovered else rect

            # Drop shadow
            pygame.draw.rect(target, (10, 8, 6), rect.move(0, 6), border_radius=20)

            border_c = (56, 189, 248) if is_hovered else (245, 158, 11)
            pygame.draw.rect(target, (2, 132, 199), draw_rect, border_radius=20)
            pygame.draw.rect(target, border_c, draw_rect, width=4, border_radius=20)

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
            target.blit(self._art.dani, (24, 380))

    def _draw_progress_badge(self, target: pygame.Surface, session: MeasureSession) -> None:
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 200), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 240, 138), badge_rect, width=2, border_radius=22)

        txt = f"{session.challenge_index + 1} / 5"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 240, 138))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )
