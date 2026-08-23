"""Shared tactile navigation chrome for the production Greia child Shell.

This mixin changes presentation only. Page selection, category identity, scroll
math and hit targets remain the existing launcher authority. The reviewed
``ui.button.icon`` artwork is optional and fails back to the proven primitive
controls without disabling other shared visual families.
"""

from __future__ import annotations

from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError


_SHARED_NAVIGATION_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)


class SharedUiNavigationChromeMixin:
    """Use one reviewed icon-button frame for Shell-local navigation controls."""

    def _icon_button_surface(self, size: int, pygame: Any) -> Any | None:
        if getattr(self, "_shared_icon_buttons_disabled", False):
            return None
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return None
        try:
            return visual_cache.get(
                "ui.button.icon",
                variant="default",
                size=(size, size),
            )
        except _SHARED_NAVIGATION_ERRORS:
            self._shared_icon_buttons_disabled = True
            return None
        except pygame.error:
            self._shared_icon_buttons_disabled = True
            return None

    def _draw_page_controls(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        page: Any,
        *,
        previous_action: str,
        next_action: str,
        total: int,
    ) -> None:
        if page.page_count <= 1:
            return

        size = max(54, min(72, screen.get_height() // 8))
        frame = self._icon_button_surface(size, pygame)
        if frame is None:
            super()._draw_page_controls(
                screen,
                theme,
                pygame,
                page,
                previous_action=previous_action,
                next_action=next_action,
                total=total,
            )
            return

        from .main import HitTarget

        center_y = screen.get_height() // 2 + 24
        controls = (
            (
                "previous",
                pygame.Rect(14, center_y - size // 2, size, size),
                previous_action,
            ),
            (
                "next",
                pygame.Rect(
                    screen.get_width() - size - 14,
                    center_y - size // 2,
                    size,
                    size,
                ),
                next_action,
            ),
        )
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)

        for direction, rect, action in controls:
            enabled = (
                page.page_index > 0
                if direction == "previous"
                else page.page_index + 1 < page.page_count
            )
            if not enabled:
                continue
            hovered = pointer_active and rect.collidepoint(pointer)
            drawn = rect.move(0, -2 if hovered else 0)
            screen.blit(frame, drawn)

            inset = max(13, drawn.width // 4)
            if direction == "previous":
                points = (
                    (drawn.right - inset, drawn.top + inset),
                    (drawn.left + inset, drawn.centery),
                    (drawn.right - inset, drawn.bottom - inset),
                )
                target_index = max(0, page.start - page.page_size)
            else:
                points = (
                    (drawn.left + inset, drawn.top + inset),
                    (drawn.right - inset, drawn.centery),
                    (drawn.left + inset, drawn.bottom - inset),
                )
                target_index = min(total - 1, page.stop)
            pygame.draw.polygon(
                screen,
                theme.accent if hovered else theme.text,
                points,
            )
            self._targets.append(HitTarget(action, target_index, rect))

    def _draw_scroll_controls(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        window: Any,
        columns: int,
    ) -> None:
        super()._draw_scroll_controls(screen, theme, pygame, window, columns)

    def _draw_category_header(self, screen: Any, theme: Any, pygame: Any) -> None:
        from .catalogue_view import ALL_ACTIVITIES_ID, _category_title
        from .main import HitTarget
        from .presentation import _mix

        collections = tuple(
            item
            for item in self._catalogue.collections
            if item.collection_id != ALL_ACTIVITIES_ID
        )
        left = 112 if self._active_profile is not None else 20
        height = max(46, min(56, screen.get_height() // 10))
        frame = self._icon_button_surface(height, pygame)

        back_rect = pygame.Rect(left, 16, height, height)
        hovered = (
            back_rect.collidepoint(self._pointer_pos(pygame))
            and self._is_pointer_active(pygame)
        )
        drawn = back_rect.move(0, -2 if hovered else 0)

        if frame is not None:
            screen.blit(frame, drawn)
        else:
            pygame.draw.rect(screen, theme.panel, drawn, border_radius=height // 2)
            pygame.draw.rect(
                screen,
                theme.accent if hovered else _mix(theme.text, theme.panel, 0.72),
                drawn,
                width=3 if hovered else 2,
                border_radius=height // 2,
            )

        from greia_platform.activity_ui import draw_back_symbol

        arrow_color = theme.accent if hovered else theme.text
        symbol_rect = drawn.move(0, -2 if frame is not None else 0)
        draw_back_symbol(screen, symbol_rect, arrow_color)
        self._targets.append(
            HitTarget("activity_category_back", ALL_ACTIVITIES_ID, back_rect)
        )

        # Category Switcher Strip
        x = back_rect.right + 14
        error_active = (
            (self._last_result and not self._last_result.succeeded)
            or self._catalogue_error
        )
        right = screen.get_width() - (76 if error_active else 20)
        gap = 8
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)

        for col in collections:
            is_active = (col.collection_id == self._category_id)
            label_text = _category_title(col.collection_id, self._active_locale)
            count = len(col.items)
            display_text = f"{label_text} ({count})" if is_active else label_text
            font_size = max(15, min(19, height // 2))
            label = self._category_label_surface(display_text, font_size, theme.text, pygame)
            icon_size = max(24, height - 16)

            if is_active:
                chip_width = min(220, max(110, label.get_width() + icon_size + 28))
            else:
                chip_width = min(150, max(46, label.get_width() + icon_size + 24)) if (right - x > len(collections) * 80) else height

            if x + chip_width > right:
                break

            chip_rect = pygame.Rect(x, 16, chip_width, height)
            h_chip = pointer_active and chip_rect.collidepoint(pointer)

            bg_color = _mix(theme.panel, theme.accent, 0.12) if is_active else theme.panel
            outline_color = theme.accent if (is_active or h_chip) else _mix(theme.text, theme.panel, 0.75)
            outline_width = 3 if is_active else (2 if h_chip else 1)

            pygame.draw.rect(screen, bg_color, chip_rect, border_radius=height // 2)
            pygame.draw.rect(screen, outline_color, chip_rect, width=outline_width, border_radius=height // 2)

            cat_icon = self._category_shadowed_icon(
                col.icon_id or "backpack",
                icon_size,
                shadow_alpha=48 if is_active else 30,
                shadow_offset=2,
                pygame=pygame,
            )

            if chip_width > height:
                icon_center = (chip_rect.left + 12 + icon_size // 2, chip_rect.centery)
                screen.blit(cat_icon, cat_icon.get_rect(center=icon_center))
                label_rect = label.get_rect(midleft=(chip_rect.left + 16 + icon_size, chip_rect.centery))
                screen.blit(label, label_rect)
            else:
                screen.blit(cat_icon, cat_icon.get_rect(center=chip_rect.center))

            if not is_active:
                self._targets.append(
                    HitTarget("activity_category", col.collection_id, chip_rect)
                )

            x += chip_width + gap
