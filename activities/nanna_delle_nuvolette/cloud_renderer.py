"""Presentation renderer for Nanna delle Nuvolette."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .cloud_art import CloudArt
    from .cloud_content import BLANKETS, Blanket
    from .cloud_model import CloudFriend, NightScene, REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from cloud_art import CloudArt
    from cloud_content import BLANKETS, Blanket
    from cloud_model import CloudFriend, NightScene, REFERENCE_HEIGHT, REFERENCE_WIDTH


CLOUD_RECTS: Final[tuple[pygame.Rect, ...]] = (
    pygame.Rect(130, 150, 230, 160),
    pygame.Rect(396, 120, 230, 160),
    pygame.Rect(660, 150, 230, 160),
)

BLANKET_TRAY_Y: Final[int] = 480
BLANKET_CARD_SIZE: Final[tuple[int, int]] = (92, 76)

BASKET_RECT: Final[pygame.Rect] = pygame.Rect(880, 470, 110, 86)
MOON_RECT: Final[pygame.Rect] = pygame.Rect(850, 40, 130, 110)


class CloudRenderer:
    """Render the 3 cloud beds, blanket tray, star basket, and peaceful night sky."""

    def __init__(
        self,
        art: CloudArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources

        self._basket_label = typography.render(
            "⭐",
            FontRole.TITLE,
            20,
            (254, 240, 138),
        )
        self._new_night_label = typography.render(
            "🌙 ✨",
            FontRole.TITLE,
            24,
            (255, 255, 255),
        )

    def draw_scene(
        self,
        target: pygame.Surface,
        scene: NightScene,
        *,
        hovered_cloud_idx: int | None = None,
        hovered_blanket_idx: int | None = None,
        hovered_basket: bool = False,
        hovered_moon: bool = False,
        selected_blanket_idx: int | None = None,
        holding_star: bool = False,
        drag_pos: tuple[int, int] | None = None,
        yawn_progresses: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_momo(target)

        # 1. Draw 3 Cloud Friends
        for idx, (rect, cloud) in enumerate(zip(CLOUD_RECTS, scene.clouds)):
            is_hovered = (idx == hovered_cloud_idx)
            self._art.draw_cloud(
                target,
                rect,
                cloud,
                is_hovered=is_hovered,
                yawn_progress=yawn_progresses[idx],
            )

        # 2. Draw Blanket Tray (6 choices across bottom)
        self._draw_blanket_tray(
            target,
            hovered_blanket_idx=hovered_blanket_idx,
            selected_blanket_idx=selected_blanket_idx,
        )

        # 3. Draw Star Basket
        self._art.draw_star_basket(
            target,
            BASKET_RECT,
            scene.available_stars,
            is_hovered=hovered_basket,
            is_selected=holding_star,
        )
        target.blit(
            self._basket_label,
            (
                BASKET_RECT.centerx - self._basket_label.get_width() // 2,
                BASKET_RECT.bottom + 4,
            ),
        )

        # 4. If all clouds are asleep, draw Moon New Night button
        if scene.all_asleep:
            self._draw_new_night_button(target, is_hovered=hovered_moon)

        # 5. Draw active dragging / held item under cursor
        if drag_pos is not None:
            if selected_blanket_idx is not None and selected_blanket_idx < len(BLANKETS):
                b = BLANKETS[selected_blanket_idx]
                d_rect = pygame.Rect(drag_pos[0] - 46, drag_pos[1] - 38, 92, 76)
                self._art.draw_blanket_card(target, d_rect, b, is_selected=True)
            elif holding_star:
                self._art.draw_star(target, drag_pos, size=24)

    def blanket_rect_at(self, index: int) -> pygame.Rect:
        spacing = 110
        start_x = 140
        return pygame.Rect(start_x + index * spacing, BLANKET_TRAY_Y, BLANKET_CARD_SIZE[0], BLANKET_CARD_SIZE[1])

    def cloud_at(self, point: tuple[int, int]) -> int | None:
        for idx, rect in enumerate(CLOUD_RECTS):
            if rect.inflate(20, 20).collidepoint(point):
                return idx
        return None

    def blanket_at(self, point: tuple[int, int]) -> int | None:
        for idx in range(len(BLANKETS)):
            rect = self.blanket_rect_at(idx)
            if rect.collidepoint(point):
                return idx
        return None

    def basket_contains(self, point: tuple[int, int]) -> bool:
        return BASKET_RECT.collidepoint(point)

    def moon_contains(self, point: tuple[int, int]) -> bool:
        return MOON_RECT.collidepoint(point)

    def _draw_blanket_tray(
        self,
        target: pygame.Surface,
        *,
        hovered_blanket_idx: int | None = None,
        selected_blanket_idx: int | None = None,
    ) -> None:
        # Tray backing panel
        tray_rect = pygame.Rect(120, 466, 720, 104)
        pygame.draw.rect(target, (10, 14, 28, 80), tray_rect.move(0, 6), border_radius=22)
        pygame.draw.rect(target, (15, 23, 42, 220), tray_rect, border_radius=22)
        pygame.draw.rect(target, (51, 65, 85), tray_rect, width=2, border_radius=22)

        for idx, b in enumerate(BLANKETS):
            rect = self.blanket_rect_at(idx)
            is_hovered = (idx == hovered_blanket_idx)
            is_selected = (idx == selected_blanket_idx)
            self._art.draw_blanket_card(
                target,
                rect,
                b,
                is_selected=is_selected,
                is_hovered=is_hovered,
            )

    def _draw_new_night_button(self, target: pygame.Surface, *, is_hovered: bool = False) -> None:
        draw_rect = MOON_RECT.move(0, -4) if is_hovered else MOON_RECT
        pygame.draw.rect(target, (10, 14, 28), MOON_RECT.move(0, 6), border_radius=24)
        pygame.draw.rect(target, (2, 132, 199), draw_rect, border_radius=24)
        border_c = (56, 189, 248) if is_hovered else (254, 240, 138)
        pygame.draw.rect(target, border_c, draw_rect, width=3, border_radius=24)

        target.blit(
            self._new_night_label,
            (
                draw_rect.centerx - self._new_night_label.get_width() // 2,
                draw_rect.centery - self._new_night_label.get_height() // 2,
            ),
        )

    def _draw_momo(self, target: pygame.Surface) -> None:
        if self._art.momo is not None:
            target.blit(self._art.momo, (16, 425))
