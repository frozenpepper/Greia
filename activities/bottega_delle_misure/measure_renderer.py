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
    pygame.Rect(290, 460, 130, 92),
    pygame.Rect(446, 460, 130, 92),
    pygame.Rect(602, 460, 130, 92),
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
        self._block_numbers = {
            value: typography.render(str(value), FontRole.TITLE, 22, (255, 255, 255))
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

        # 1. Top Goal Placard (Clear, unmistakable goal)
        self._draw_goal_placard(target, current)

        # 2. Draw Items according to Mode
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

        # 3. Draw Numerical Choices in Measure / Shelf mode
        if current.mode in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            self._draw_measure_controls(target, current, hovered_choice_idx=hovered_choice_idx)

        # 4. Progress badge
        self._draw_progress_badge(target, session)

    def item_rect_at(self, challenge: MeasureChallenge, item_index: int) -> pygame.Rect:
        item = challenge.items[item_index]
        if challenge.mode == MeasureMode.COMPARE:
            if challenge.attribute == Attribute.LENGTH:
                w = item.units * UNIT_PX
                h = 76
                cx = 360 if item_index == 0 else 660
                return pygame.Rect(cx - w // 2, 335 - h, w, h)
            else:
                w = 100
                h = item.units * UNIT_H_PX
                cx = 360 if item_index == 0 else 660
                return pygame.Rect(cx - w // 2, 335 - h, w, h)

        if challenge.mode == MeasureMode.ORDER:
            count = len(challenge.items)
            spacing = 220
            start_x = 512 - ((count - 1) * spacing) // 2
            cx = start_x + item_index * spacing
            if challenge.attribute == Attribute.LENGTH:
                w = item.units * 42
                h = 68
                return pygame.Rect(cx - w // 2, 320 - h, w, h)
            else:
                w = 88
                h = item.units * 36
                return pygame.Rect(cx - w // 2, 320 - h, w, h)

        return pygame.Rect(0, 0, 0, 0)

    def item_at(self, point: tuple[int, int], challenge: MeasureChallenge) -> str | None:
        for idx, item in enumerate(challenge.items):
            rect = self.item_rect_at(challenge, idx)
            if rect.inflate(24, 24).collidepoint(point):
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

    def _draw_goal_placard(self, target: pygame.Surface, challenge: MeasureChallenge) -> None:
        """Draw the high-contrast goal placard at top center."""
        p_y = 20
        if challenge.mode == MeasureMode.COMPARE:
            if challenge.attribute == Attribute.LENGTH:
                text = "🎯 PIÙ LUNGO 📦" if "longer" in challenge.prompt_key else "🎯 PIÙ CORTO 📦"
            else:
                text = "🎯 PIÙ ALTO 📦" if "taller" in challenge.prompt_key else "🎯 PIÙ BASSO 📦"
        elif challenge.mode == MeasureMode.ORDER:
            text = "🎯 ORDINA: 1 - 2 - 3"
        elif challenge.mode == MeasureMode.MEASURE:
            text = "🎯 CONTA I BLOCCHI 📏"
        elif challenge.mode == MeasureMode.SHELF:
            text = "🎯 QUALE ENTRA? 🚪"
        else:
            text = "🎯 MISURA 📏"

        surf = self._typography.render(text, FontRole.TITLE, 22, (254, 240, 138))
        p_x = REFERENCE_WIDTH // 2 - surf.get_width() // 2
        banner = pygame.Rect(p_x - 20, p_y, surf.get_width() + 40, 44)

        # Drop shadow and gold framed placard
        pygame.draw.rect(target, (10, 8, 6), banner.move(0, 4), border_radius=16)
        pygame.draw.rect(target, (15, 23, 42), banner, border_radius=16)
        pygame.draw.rect(target, (245, 158, 11), banner, width=3, border_radius=16)

        target.blit(surf, (p_x, p_y + 8))

    def _draw_compare_items(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        *,
        wobble_x: int = 0,
        show_baseline: bool = False,
        hovered_item_id: str | None = None,
    ) -> None:
        # Golden alignment baseline on table
        pygame.draw.line(target, (245, 158, 11), (200, 336), (820, 336), 4)

        for idx, item in enumerate(challenge.items):
            rect = self.item_rect_at(challenge, idx)
            is_hovered = (item.item_id == hovered_item_id)
            draw_rect = rect.move(0, -8) if is_hovered else (rect.move(wobble_x, 0) if wobble_x != 0 else rect)
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
        count = len(challenge.items)
        spacing = 220
        start_x = 512 - ((count - 1) * spacing) // 2

        # Draw Numbered Pedestals / Podiums on the counter
        for idx in range(count):
            cx = start_x + idx * spacing
            ped_rect = pygame.Rect(cx - 50, 330, 100, 24)
            is_next = (len(session.selected_order_ids) == idx)

            # Shadow & Pedestal Body
            pygame.draw.rect(target, (20, 15, 10), ped_rect.move(0, 4), border_radius=8)
            ped_col = (2, 132, 199) if is_next else (78, 48, 26)
            border_col = (56, 189, 248) if is_next else (217, 119, 6)
            pygame.draw.rect(target, ped_col, ped_rect, border_radius=8)
            pygame.draw.rect(target, border_col, ped_rect, width=2, border_radius=8)

            # Pedestal label (#1, #2, #3)
            p_label = self._typography.render(f"#{idx + 1}", FontRole.TITLE, 14, (254, 240, 138))
            target.blit(p_label, (ped_rect.centerx - p_label.get_width() // 2, ped_rect.centery - p_label.get_height() // 2))

        # Draw Parcels
        for idx, item in enumerate(challenge.items):
            rect = self.item_rect_at(challenge, idx)
            is_hovered = (item.item_id == hovered_item_id)
            draw_rect = rect.move(0, -8) if is_hovered else (rect.move(wobble_x, 0) if wobble_x != 0 else rect)
            self._draw_parcel(target, draw_rect, item, is_hovered=is_hovered)

            if item.item_id in session.selected_order_ids:
                order_num = session.selected_order_ids.index(item.item_id) + 1
                badge_center = (draw_rect.centerx, draw_rect.top - 20)
                pygame.draw.circle(target, (10, 20, 30), (badge_center[0], badge_center[1] + 3), 18)
                pygame.draw.circle(target, (22, 163, 74), badge_center, 18)
                pygame.draw.circle(target, (255, 255, 255), badge_center, 18, 3)
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
        start_x = REFERENCE_WIDTH // 2 - w // 2
        parcel_rect = pygame.Rect(start_x + wobble_x, 150, w, h)
        self._draw_parcel(target, parcel_rect, item)

        # Measuring rail directly below parcel
        rail_w = challenge.unit_capacity * UNIT_PX
        rail_rect = pygame.Rect(start_x, 240, rail_w, 56)
        pygame.draw.rect(target, (25, 15, 8), rail_rect.move(0, 6), border_radius=12)
        pygame.draw.rect(target, (78, 48, 26), rail_rect, border_radius=12)
        pygame.draw.rect(target, (217, 119, 6), rail_rect, width=3, border_radius=12)

        # Fill with Wooden Orange Unit Blocks
        for u in range(challenge.unit_capacity):
            slot_rect = pygame.Rect(start_x + u * UNIT_PX, 240, UNIT_PX, 56)
            block_rect = slot_rect.inflate(-6, -6)

            # 3D Wooden Block
            pygame.draw.rect(target, (180, 83, 9), block_rect.move(0, 2), border_radius=8)
            pygame.draw.rect(target, (245, 158, 11), block_rect, border_radius=8)
            pygame.draw.rect(target, (254, 240, 138), block_rect, width=2, border_radius=8)

            # Block Gloss Highlight
            hl = block_rect.inflate(-6, -block_rect.height + 6).move(0, -block_rect.height // 2 + 5)
            pygame.draw.rect(target, (255, 255, 255, 140), hl, border_radius=3)

            # Block Number (1, 2, 3, 4...)
            num_s = self._block_numbers.get(u + 1)
            if num_s:
                target.blit(num_s, (block_rect.centerx - num_s.get_width() // 2, block_rect.centery - num_s.get_height() // 2))

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
        pygame.draw.rect(target, (10, 8, 6, 90), rect.move(0, 8), border_radius=14)

        # Gift box body
        pygame.draw.rect(target, box_col, rect, border_radius=14)
        border_c = (56, 189, 248) if is_hovered else border_col
        border_w = 5 if is_hovered else 3
        pygame.draw.rect(target, border_c, rect, width=border_w, border_radius=14)

        # Satin glossy highlight on box
        hl = rect.inflate(-8, -rect.height + 6).move(0, -rect.height // 2 + 6)
        pygame.draw.rect(target, (255, 255, 255, 140), hl, border_radius=3)

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

    def _draw_measure_controls(
        self,
        target: pygame.Surface,
        challenge: MeasureChallenge,
        *,
        hovered_choice_idx: int | None = None,
    ) -> None:
        """Draw 3 large choice buttons with number and block icon."""
        for idx, (rect, val) in enumerate(zip(CHOICE_RECTS, challenge.choice_values)):
            is_hovered = (idx == hovered_choice_idx)
            draw_rect = rect.move(0, -6) if is_hovered else rect

            # Drop shadow
            pygame.draw.rect(target, (10, 8, 6), rect.move(0, 8), border_radius=22)

            btn_col = (2, 132, 199) if is_hovered else (3, 105, 161)
            border_c = (56, 189, 248) if is_hovered else (245, 158, 11)
            pygame.draw.rect(target, btn_col, draw_rect, border_radius=22)
            pygame.draw.rect(target, border_c, draw_rect, width=4, border_radius=22)

            # Highlight
            hl = draw_rect.inflate(-16, -draw_rect.height + 8).move(0, -draw_rect.height // 2 + 8)
            pygame.draw.rect(target, (186, 230, 253, 100), hl, border_radius=4)

            # Number + Block Icon: e.g. "4 🟧"
            label_str = f"{val} 🟧"
            num_surf = self._typography.render(label_str, FontRole.DISPLAY, 38, (255, 255, 255))
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
        badge_rect = pygame.Rect(870, 20, 130, 48)
        pygame.draw.rect(target, (15, 23, 42, 220), badge_rect, border_radius=24)
        pygame.draw.rect(target, (254, 240, 138), badge_rect, width=3, border_radius=24)

        txt = f"{session.challenge_index + 1} / 5"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 240, 138))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )
