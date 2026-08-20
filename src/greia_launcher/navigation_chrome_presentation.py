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
        if not window.can_scroll_backward and not window.can_scroll_forward:
            return

        size = max(48, min(62, screen.get_height() // 9))
        frame = self._icon_button_surface(size, pygame)
        if frame is None:
            super()._draw_scroll_controls(
                screen,
                theme,
                pygame,
                window,
                columns,
            )
            return

        from .main import HitTarget

        x = screen.get_width() - size - 12
        center_y = screen.get_height() // 2 + 36
        controls = (
            (
                -1,
                pygame.Rect(x, center_y - size - 8, size, size),
                window.can_scroll_backward,
            ),
            (
                1,
                pygame.Rect(x, center_y + 8, size, size),
                window.can_scroll_forward,
            ),
        )
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)

        for direction, rect, enabled in controls:
            if not enabled:
                continue
            hovered = pointer_active and rect.collidepoint(pointer)
            drawn = rect.move(0, -2 if hovered else 0)
            screen.blit(frame, drawn)
            inset = max(12, drawn.width // 4)
            if direction < 0:
                points = (
                    (drawn.left + inset, drawn.bottom - inset),
                    (drawn.centerx, drawn.top + inset),
                    (drawn.right - inset, drawn.bottom - inset),
                )
            else:
                points = (
                    (drawn.left + inset, drawn.top + inset),
                    (drawn.centerx, drawn.bottom - inset),
                    (drawn.right - inset, drawn.top + inset),
                )
            pygame.draw.polygon(
                screen,
                theme.accent if hovered else theme.text,
                points,
            )
            target = min(
                max(0, self._selected + direction * columns),
                len(self._presented_activities) - 1,
            )
            self._targets.append(
                HitTarget("presented_activity_select", target, rect)
            )

    def _draw_category_header(self, screen: Any, theme: Any, pygame: Any) -> None:
        from .catalogue_view import ALL_ACTIVITIES_ID, _category_title
        from .main import HitTarget

        collection = self._catalogue.collection(self._category_id)
        left = 112 if self._active_profile is not None else 20
        height = max(46, min(58, screen.get_height() // 10))
        frame = self._icon_button_surface(height, pygame)
        if frame is None:
            super()._draw_category_header(screen, theme, pygame)
            return

        back_rect = pygame.Rect(left, 16, height, height)
        hovered = (
            back_rect.collidepoint(self._pointer_pos(pygame))
            and self._is_pointer_active(pygame)
        )
        drawn = back_rect.move(0, -2 if hovered else 0)
        screen.blit(frame, drawn)

        arrow_inset = max(12, drawn.height // 4)
        arrow_x = drawn.left + arrow_inset
        arrow_tip_x = drawn.left + drawn.height // 3
        arrow_right = drawn.right - arrow_inset
        arrow_color = theme.accent if hovered else theme.text
        pygame.draw.line(
            screen,
            arrow_color,
            (arrow_tip_x, drawn.centery),
            (arrow_right, drawn.centery),
            width=max(3, drawn.height // 12),
        )
        pygame.draw.lines(
            screen,
            arrow_color,
            False,
            (
                (arrow_x + drawn.height // 8, drawn.centery - drawn.height // 6),
                (arrow_tip_x, drawn.centery),
                (arrow_x + drawn.height // 8, drawn.centery + drawn.height // 6),
            ),
            width=max(3, drawn.height // 12),
        )
        self._targets.append(
            HitTarget("activity_category_back", ALL_ACTIVITIES_ID, back_rect)
        )

        icon_size = max(38, height - 2)
        category_icon = self._category_shadowed_icon(
            collection.icon_id or "backpack",
            icon_size,
            shadow_alpha=48,
            shadow_offset=max(2, icon_size // 24),
            pygame=pygame,
        )
        icon_center = (back_rect.right + 14 + icon_size // 2, back_rect.centery)
        screen.blit(category_icon, category_icon.get_rect(center=icon_center))

        label_text = _category_title(collection.collection_id, self._active_locale)
        label_size = max(22, min(30, height // 2))
        label = self._category_label_surface(
            label_text,
            label_size,
            theme.text,
            pygame,
        )
        screen.blit(
            label,
            label.get_rect(
                midleft=(
                    icon_center[0] + icon_size // 2 + 12,
                    back_rect.centery,
                )
            ),
        )
