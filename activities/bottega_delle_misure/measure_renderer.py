"""Low-allocation Pygame presentation for La Bottega delle Misure."""

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
    pygame.Rect(320, 470, 104, 76),
    pygame.Rect(460, 470, 104, 76),
    pygame.Rect(600, 470, 104, 76),
)

# Rail add/remove block buttons
BLOCK_TRAY_ADD: Final[pygame.Rect] = pygame.Rect(300, 470, 180, 76)
BLOCK_TRAY_REMOVE: Final[pygame.Rect] = pygame.Rect(510, 470, 100, 76)
CONFIRM_RECT: Final[pygame.Rect] = pygame.Rect(640, 470, 170, 76)


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

        # Cache numbers 1..8
        self._number_surfaces = {
            value: typography.render(str(value), FontRole.DISPLAY, 44, (255, 255, 255))
            for value in range(1, 10)
        }
        self._small_numbers = {
            value: typography.render(str(value), FontRole.BODY, 20, (120, 53, 15))
            for value in range(1, 10)
        }

        # Cache text labels
        self._confirm_label = typography.render(
            resources.text("button.confirm"),
            FontRole.TITLE,
            24,
            (255, 255, 255),
        )
        self._add_block_label = typography.render(
            "+ BLOCCHETTO",
            FontRole.TITLE,
            20,
            (120, 53, 15),
        )
        self._remove_block_label = typography.render(
            "RIMUOVI",
            FontRole.TITLE,
            18,
            (255, 255, 255),
        )

    def draw_scene(
        self,
        target: pygame.Surface,
        session: MeasureSession,
        *,
        wobble_x: int = 0,
        show_baseline: bool = False,
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_dani(target)

        current = session.current_challenge
        if current is None:
            return

        # 1. Draw Items according to Mode
        if current.mode == MeasureMode.COMPARE:
            self._draw_compare_items(target, current, wobble_x=wobble_x, show_baseline=show_baseline)
        elif current.mode == MeasureMode.ORDER:
            self._draw_order_items(target, current, session, wobble_x=wobble_x)
        elif current.mode in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            self._draw_measure_item_and_rail(target, current, session, wobble_x=wobble_x)

        # 2. Draw Prompt text
        self._draw_prompt(target, current)

        # 3. Draw Controls
        if current.mode in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            self._draw_measure_controls(target, current, session)

        # 4. Progress badge
        self._draw_progress_badge(target, session)

    def item_rect_at(self, challenge: MeasureChallenge, item_index: int) -> pygame.Rect:
        item = challenge.items[item_index]
        if challenge.mode == MeasureMode.COMPARE:
            if challenge.attribute == Attribute.LENGTH:
                w = item.units * UNIT_PX
                h = 68
                cx = 330 if item_index == 0 else 680
                return pygame.Rect(cx - w // 2, 340 - h, w, h)
            else:
                w = 88
                h = item.units * UNIT_H_PX
                cx = 350 if item_index == 0 else 660
                return pygame.Rect(cx - w // 2, 340 - h, w, h)

        if challenge.mode == MeasureMode.ORDER:
            count = len(challenge.items)
            spacing = 560 // max(1, count)
            cx = 280 + item_index * spacing
            if challenge.attribute == Attribute.LENGTH:
                w = item.units * (UNIT_PX - 6)
                h = 64
                return pygame.Rect(cx - w // 2, 340 - h, w, h)
            else:
                w = 80
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

    def add_block_contains(self, point: tuple[int, int]) -> bool:
        return BLOCK_TRAY_ADD.collidepoint(point)

    def remove_block_contains(self, point: tuple[int, int]) -> bool:
        return BLOCK_TRAY_REMOVE.collidepoint(point)

    def confirm_contains(self, point: tuple[int, int]) -> bool:
        return CONFIRM_RECT.collidepoint(point)

    def _draw_compare_items(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        *,
        wobble_x: int = 0,
        show_baseline: bool = False,
    ) -> None:
        if show_baseline:
            # Draw common baseline indicator
            if challenge.attribute == Attribute.LENGTH:
                pygame.draw.line(target, (234, 179, 8), (180, 200), (180, 340), 3)
            else:
                pygame.draw.line(target, (234, 179, 8), (200, 340), (820, 340), 3)

        for idx, item in enumerate(challenge.items):
            rect = self.item_rect_at(challenge, idx)
            draw_rect = rect.move(wobble_x, 0) if wobble_x != 0 else rect
            self._draw_parcel(target, draw_rect, item)

    def _draw_order_items(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        session: MeasureSession,
        *,
        wobble_x: int = 0,
    ) -> None:
        for idx, item in enumerate(challenge.items):
            rect = self.item_rect_at(challenge, idx)
            draw_rect = rect.move(wobble_x, 0) if wobble_x != 0 else rect
            self._draw_parcel(target, draw_rect, item)

            # Order badge if picked
            if item.item_id in session.selected_order_ids:
                order_num = session.selected_order_ids.index(item.item_id) + 1
                badge_center = (draw_rect.centerx, draw_rect.top - 18)
                pygame.draw.circle(target, (34, 197, 94), badge_center, 14)
                pygame.draw.circle(target, (255, 255, 255), badge_center, 14, 2)
                num_s = self._small_numbers.get(order_num)
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
        # Parcel to measure
        item = challenge.items[0]
        w = item.units * UNIT_PX
        h = 74
        parcel_rect = pygame.Rect(260 + wobble_x, 190, w, h)
        self._draw_parcel(target, parcel_rect, item)

        # Measuring rail below parcel
        rail_w = challenge.unit_capacity * UNIT_PX
        rail_rect = pygame.Rect(260, 274, rail_w, 46)
        pygame.draw.rect(target, (78, 48, 26), rail_rect, border_radius=8)
        pygame.draw.rect(target, (180, 83, 9), rail_rect, width=3, border_radius=8)

        # Draw rail unit slots and placed blocks
        for u in range(challenge.unit_capacity):
            slot_rect = pygame.Rect(260 + u * UNIT_PX, 274, UNIT_PX, 46)
            if u < session.placed_blocks:
                # Placed wooden block
                pygame.draw.rect(target, (253, 230, 138), slot_rect.inflate(-4, -4), border_radius=6)
                pygame.draw.rect(target, (180, 83, 9), slot_rect.inflate(-4, -4), width=2, border_radius=6)
                num_s = self._small_numbers.get(u + 1)
                if num_s:
                    target.blit(num_s, (slot_rect.centerx - num_s.get_width() // 2, slot_rect.centery - num_s.get_height() // 2))
            else:
                # Empty dashed slot
                pygame.draw.rect(target, (100, 60, 32), slot_rect.inflate(-6, -6), border_radius=4)

    def _draw_parcel(self, target: pygame.Surface, rect: pygame.Rect, item: MeasureItem) -> None:
        palette = PARCEL_PALETTES[item.color_index % len(PARCEL_PALETTES)]
        box_col, border_col, ribbon_col = palette

        pygame.draw.rect(target, box_col, rect, border_radius=12)
        pygame.draw.rect(target, border_col, rect, width=3, border_radius=12)

        # Ribbons
        if rect.width > rect.height:
            # Horizontal parcel -> center vertical ribbon
            pygame.draw.rect(target, ribbon_col, (rect.centerx - 8, rect.top, 16, rect.height))
            pygame.draw.circle(target, ribbon_col, (rect.centerx, rect.top), 10)
        else:
            # Vertical parcel -> center horizontal ribbon
            pygame.draw.rect(target, ribbon_col, (rect.left, rect.centery - 8, rect.width, 16))
            pygame.draw.circle(target, ribbon_col, (rect.centerx, rect.top), 10)

    def _draw_prompt(self, target: pygame.Surface, challenge: MeasureChallenge) -> None:
        text = self._resources.text(challenge.prompt_key)
        prompt_surf = self._typography.render(text, FontRole.TITLE, 26, (254, 243, 199))
        target.blit(
            prompt_surf,
            (REFERENCE_WIDTH // 2 - prompt_surf.get_width() // 2, 410),
        )

    def _draw_measure_controls(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        session: MeasureSession,
    ) -> None:
        # Choice buttons for number of blocks
        for rect, val in zip(CHOICE_RECTS, challenge.choice_values):
            pygame.draw.rect(target, (37, 99, 235), rect, border_radius=16)
            pygame.draw.rect(target, (255, 255, 255), rect, width=3, border_radius=16)
            num_surf = self._number_surfaces.get(val)
            if num_surf:
                target.blit(
                    num_surf,
                    (
                        rect.centerx - num_surf.get_width() // 2,
                        rect.centery - num_surf.get_height() // 2,
                    ),
                )

    def _draw_dani(self, target: pygame.Surface) -> None:
        if self._art.dani is not None:
            target.blit(self._art.dani, (24, 380))
        else:
            cx, cy = 90, 480
            pygame.draw.rect(target, (59, 130, 246), (cx - 40, cy - 40, 80, 80), border_radius=16)
            pygame.draw.circle(target, (255, 255, 255), (cx - 16, cy - 10), 10)
            pygame.draw.circle(target, (255, 255, 255), (cx + 16, cy - 10), 10)
            pygame.draw.arc(target, (255, 255, 255), (cx - 20, cy + 2, 40, 24), 3.4, 6.0, 4)

    def _draw_progress_badge(self, target: pygame.Surface, session: MeasureSession) -> None:
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 180), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 243, 199), badge_rect, width=2, border_radius=22)

        txt = f"{session.challenge_index + 1} / 5"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 243, 199))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )
