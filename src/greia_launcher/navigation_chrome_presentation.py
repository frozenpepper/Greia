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

from .system_chrome import resolve_trusted_action_minimum_px


_SHARED_NAVIGATION_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)


class SharedUiNavigationChromeMixin:
    """Use one reviewed icon-button frame for Shell-local navigation controls.

    Essential navigation targets (page arrows, category back/chips) enforce
    the shared physical floor from :mod:`greia_launcher.system_chrome` through
    :func:`resolve_trusted_action_minimum_px`. Display metrics arrive only via
    the injected ``_display_metrics`` attribute owned by the composition layer
    (``None`` means unknown: existing conservative pixels apply). Nothing here
    probes hardware, parses configuration, or scales decoration and gaps.
    """

    def _chrome_metrics(self) -> Any:
        """Return injected display metrics, or ``None`` when unknown."""
        return getattr(self, "_display_metrics", None)

    def _icon_button_surface(
        self, size: int, pygame: Any, variant: str = "default"
    ) -> Any | None:
        if getattr(self, "_shared_icon_buttons_disabled", False):
            return None
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return None
        candidates = (variant, "default") if variant != "default" else ("default",)
        for candidate in candidates:
            try:
                return visual_cache.get(
                    "ui.button.icon",
                    variant=candidate,
                    size=(size, size),
                )
            except _SHARED_NAVIGATION_ERRORS:
                continue
            except pygame.error:
                continue
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
        page_action: str | None = None,
    ) -> None:
        from .main import HitTarget
        from .navigation_layout import PageControlsState, resolve_page_controls_layout
        from .presentation import _mix
        from greia_platform.responsive_layout import Viewport

        if isinstance(page, PageControlsState):
            page_state = page
        else:
            page_state = PageControlsState.from_grid_page(page, total=total)

        if page_state.page_count <= 1:
            return

        resolved_page_action = page_action
        if resolved_page_action is None:
            if previous_action == "profile_page":
                resolved_page_action = "profile_page"
            elif previous_action == "presented_activity_page_prev":
                resolved_page_action = "presented_activity_page"
            else:
                resolved_page_action = previous_action.replace("_prev", "")

        viewport = Viewport(screen.get_width(), screen.get_height())
        panel_layout = getattr(self, "_shell_panel_layout", None)
        panel_outer = panel_layout.outer_rect if panel_layout else None
        panel_content = (
            getattr(self, "_page_content_rect", None)
            or (panel_layout.content_rect if panel_layout else None)
        )

        if panel_outer is not None:
            left_gutter = panel_outer.x
            right_gutter = screen.get_width() - panel_outer.right
            if left_gutter >= 88 and right_gutter >= 88:
                # Wide gutter mode (e.g. 1024x600): generous, prominent child-sized disc
                preferred_size = min(72, min(left_gutter, right_gutter) - 20)
            elif left_gutter >= 70 and right_gutter >= 70:
                # Moderate gutter mode (e.g. 800x600 profile picker): clean outer gutter buttons
                preferred_size = min(56, min(left_gutter, right_gutter) - 16)
            elif panel_content is not None:
                left_rail = panel_content.x - panel_outer.x
                right_rail = panel_outer.right - panel_content.right
                preferred_size = max(50, min(58, min(left_rail, right_rail) - 10))
            else:
                preferred_size = 56
        elif panel_content is not None:
            left_gutter = panel_content.x
            right_gutter = screen.get_width() - panel_content.right
            if left_gutter >= 88 and right_gutter >= 88:
                preferred_size = min(72, min(left_gutter, right_gutter) - 20)
            else:
                preferred_size = max(50, min(58, min(left_gutter, right_gutter) - 16))
        else:
            preferred_size = max(56, min(72, screen.get_height() // 8))

        size = resolve_trusted_action_minimum_px(
            self._chrome_metrics(), fallback_px=preferred_size
        )

        layout = resolve_page_controls_layout(
            viewport,
            page_state,
            panel_outer_rect=panel_outer,
            panel_content_rect=panel_content,
            button_size=size,
        )

        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)

        # 1. Previous and Next buttons
        controls = (
            (
                "previous",
                pygame.Rect(
                    layout.previous_rect.x,
                    layout.previous_rect.y,
                    layout.previous_rect.width,
                    layout.previous_rect.height,
                ),
                previous_action,
                page_state.previous_value,
                page_state.can_go_previous,
            ),
            (
                "next",
                pygame.Rect(
                    layout.next_rect.x,
                    layout.next_rect.y,
                    layout.next_rect.width,
                    layout.next_rect.height,
                ),
                next_action,
                page_state.next_value,
                page_state.can_go_next,
            ),
        )

        for direction, rect, action, target_val, enabled in controls:
            if not enabled:
                continue
            hovered = pointer_active and rect.collidepoint(pointer)
            self._draw_page_arrow_button(
                screen, theme, pygame, direction, rect, hovered
            )
            self._targets.append(HitTarget(action, target_val, rect))

        # 2. Bottom Pagination Capsule Pill
        if layout.visible_dot_count > 0 and layout.indicator_rect.width > 0:
            pill_rect = pygame.Rect(
                layout.indicator_rect.x,
                layout.indicator_rect.y,
                layout.indicator_rect.width,
                layout.indicator_rect.height,
            )
            # Soft shadow
            shadow_rect = pill_rect.move(0, 2)
            pygame.draw.rect(
                screen,
                _mix(theme.background, (0, 0, 0), 0.12),
                shadow_rect,
                border_radius=pill_rect.height // 2,
            )
            # Capsule fill
            pygame.draw.rect(
                screen,
                _mix(theme.panel, theme.accent, 0.08),
                pill_rect,
                border_radius=pill_rect.height // 2,
            )
            # Capsule outline
            pygame.draw.rect(
                screen,
                _mix(theme.text, theme.panel, 0.8),
                pill_rect,
                width=1,
                border_radius=pill_rect.height // 2,
            )

            # Dots
            total_pages = page_state.page_count
            if total_pages <= len(layout.dot_rects):
                window_start = 0
            else:
                half = len(layout.dot_rects) // 2
                window_start = max(
                    0,
                    min(
                        page_state.page_index - half,
                        total_pages - len(layout.dot_rects),
                    ),
                )

            for i, dot_ui in enumerate(layout.dot_rects):
                target_p = window_start + i
                is_active = i == layout.active_dot_index
                cx = dot_ui.x + dot_ui.width // 2
                cy = dot_ui.y + dot_ui.height // 2
                if is_active:
                    dot_r = pygame.Rect(cx - 8, cy - 4, 16, 8)
                    pygame.draw.rect(screen, theme.accent, dot_r, border_radius=4)
                else:
                    pygame.draw.circle(
                        screen,
                        _mix(theme.text, theme.panel, 0.5),
                        (cx, cy),
                        4,
                    )
                dot_hit = pygame.Rect(
                    dot_ui.x - 4, dot_ui.y - 6, dot_ui.width + 8, dot_ui.height + 12
                )
                dot_target_value = (
                    target_p * page_state.page_size
                    if resolved_page_action in ("profile_page", "activity_page")
                    else target_p
                )
                self._targets.append(
                    HitTarget(resolved_page_action, dot_target_value, dot_hit)
                )

            # Counter text
            label_text = f"{page_state.page_index + 1} / {page_state.page_count}"
            font = self._font(14, pygame)
            label_surf = font.render(
                label_text, True, _mix(theme.text, theme.panel, 0.4)
            )
            last_dot = layout.dot_rects[-1]
            screen.blit(
                label_surf,
                label_surf.get_rect(
                    midleft=(last_dot.right + 10, pill_rect.centery)
                ),
            )

    def _draw_page_arrow_button(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        direction: str,
        rect: Any,
        hovered: bool,
    ) -> None:
        from .presentation import _mix

        drawn = rect.move(0, -2 if hovered else 0)

        # Try semantic asset with hover fallback chain
        frame = self._icon_button_surface(
            drawn.width, pygame, variant="hover" if hovered else "default"
        )
        if frame is not None:
            screen.blit(frame, drawn)
        else:
            # Procedural circular tactile button fallback
            cx, cy = drawn.center
            radius = drawn.width // 2
            shadow_cy = cy + 3
            pygame.draw.circle(screen, (61, 44, 31, 40), (cx, shadow_cy), radius)
            fill = (255, 255, 255) if hovered else (255, 253, 248)
            pygame.draw.circle(screen, fill, (cx, cy), radius)
            ring_color = (255, 214, 110) if hovered else (242, 230, 212)
            pygame.draw.circle(screen, ring_color, (cx, cy), radius - 3, width=2)
            border_color = (
                theme.accent if hovered else _mix(theme.text, theme.panel, 0.72)
            )
            pygame.draw.circle(
                screen,
                border_color,
                (cx, cy),
                radius,
                width=3 if hovered else 2,
            )
            sheen = (255, 255, 255)
            pygame.draw.line(
                screen,
                sheen,
                (cx - int(radius * 0.55), cy - radius + 4),
                (cx + int(radius * 0.55), cy - radius + 4),
                width=2,
            )

        # Chunky Greia directional arrow glyph (shaft + rounded arrowhead)
        cx, cy = drawn.center
        scale = drawn.width / 52.0
        optical_shift = max(1, int(round(1.5 * scale)))
        if direction == "previous":
            cx += optical_shift
        else:
            cx -= optical_shift
        shaft_len = max(8, int(15 * scale))
        shaft_h = max(6, int(10 * scale))
        head_len = max(8, int(13 * scale))
        head_half_h = max(7, int(13 * scale))
        corner_r = max(2, int(2.5 * scale))

        glyph_color = (
            _mix(theme.accent, (40, 20, 10), 0.30) if hovered else theme.text
        )

        if direction == "previous":
            tip_x = cx - int(13 * scale)
            base_x = tip_x + head_len
            shaft_x = base_x - int(2 * scale)
            shaft_rect = pygame.Rect(shaft_x, cy - shaft_h // 2, shaft_len, shaft_h)
            head_pts = ((tip_x, cy), (base_x, cy - head_half_h), (base_x, cy + head_half_h))
        else:
            tip_x = cx + int(13 * scale)
            base_x = tip_x - head_len
            shaft_x = base_x - shaft_len + int(2 * scale)
            shaft_rect = pygame.Rect(shaft_x, cy - shaft_h // 2, shaft_len, shaft_h)
            head_pts = ((tip_x, cy), (base_x, cy - head_half_h), (base_x, cy + head_half_h))

        # Soft optical drop shadow
        shadow_shaft = shaft_rect.move(0, 1)
        shadow_pts = tuple((p[0], p[1] + 1) for p in head_pts)
        shadow_color = _mix(theme.background, (0, 0, 0), 0.16)
        pygame.draw.rect(screen, shadow_color, shadow_shaft, border_radius=corner_r)
        pygame.draw.polygon(screen, shadow_color, shadow_pts)
        for p in shadow_pts:
            pygame.draw.circle(screen, shadow_color, p, corner_r)

        # Foreground glyph
        pygame.draw.rect(screen, glyph_color, shaft_rect, border_radius=corner_r)
        pygame.draw.polygon(screen, glyph_color, head_pts)
        for p in head_pts:
            pygame.draw.circle(screen, glyph_color, p, corner_r)

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
        base_height = max(46, min(56, screen.get_height() // 10))
        height = resolve_trusted_action_minimum_px(
            self._chrome_metrics(), fallback_px=base_height
        )
        back_rect = pygame.Rect(left, 16, height, height)
        hovered = (
            back_rect.collidepoint(self._pointer_pos(pygame))
            and self._is_pointer_active(pygame)
        )
        drawn = back_rect.move(0, -2 if hovered else 0)
        frame = self._icon_button_surface(
            height, pygame, variant="hover" if hovered else "default"
        )

        if frame is not None:
            screen.blit(frame, drawn)
        else:
            shadow_rect = drawn.move(0, 3)
            pygame.draw.circle(
                screen, (0, 0, 0, 35), shadow_rect.center, drawn.width // 2
            )
            pygame.draw.circle(screen, theme.panel, drawn.center, drawn.width // 2)
            border_color = (
                theme.accent if hovered else _mix(theme.text, theme.panel, 0.72)
            )
            pygame.draw.circle(
                screen,
                border_color,
                drawn.center,
                drawn.width // 2,
                width=3 if hovered else 2,
            )

        from greia_platform.activity_ui import draw_back_symbol

        arrow_color = (
            _mix(theme.accent, (40, 20, 10), 0.30) if hovered else theme.text
        )
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
        has_topright_badge = (
            error_active
            or getattr(self, "_achievement_service", None) is not None
            or getattr(self, "_achievement_snapshot", None) is not None
        )
        right = screen.get_width() - (96 if has_topright_badge else 20)
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
            is_highlighted = is_active or h_chip
            drawn_chip = chip_rect.move(0, -1 if is_highlighted else 0)

            # Grounding drop shadow
            shadow_rect = drawn_chip.move(0, 2 if is_highlighted else 1)
            shadow_color = _mix(theme.background, (0, 0, 0), 0.12 if is_active else 0.07)
            pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=height // 2)

            # Pill background fill
            if is_active:
                bg_color = _mix(theme.panel, theme.accent, 0.15)
            elif h_chip:
                bg_color = _mix(theme.panel, (255, 255, 255), 0.35)
            else:
                bg_color = theme.panel
            pygame.draw.rect(screen, bg_color, drawn_chip, border_radius=height // 2)

            # Subtle top sheen highlight line
            sheen_color = _mix(bg_color, (255, 255, 255), 0.55)
            pygame.draw.line(
                screen,
                sheen_color,
                (drawn_chip.left + height // 3, drawn_chip.top + 1),
                (drawn_chip.right - height // 3, drawn_chip.top + 1),
                width=1,
            )

            # Outline
            outline_color = theme.accent if (is_active or h_chip) else _mix(theme.text, theme.panel, 0.75)
            outline_width = 3 if is_active else (2 if h_chip else 1)
            pygame.draw.rect(screen, outline_color, drawn_chip, width=outline_width, border_radius=height // 2)

            cat_icon = self._category_shadowed_icon(
                col.icon_id or "backpack",
                icon_size,
                shadow_alpha=48 if is_active else 30,
                shadow_offset=2,
                pygame=pygame,
            )

            if chip_width > height:
                icon_center = (drawn_chip.left + 12 + icon_size // 2, drawn_chip.centery)
                screen.blit(cat_icon, cat_icon.get_rect(center=icon_center))
                label_rect = label.get_rect(midleft=(drawn_chip.left + 16 + icon_size, drawn_chip.centery))
                screen.blit(label, label_rect)
            else:
                screen.blit(cat_icon, cat_icon.get_rect(center=drawn_chip.center))

            if not is_active:
                self._targets.append(
                    HitTarget("activity_category", col.collection_id, chip_rect)
                )

            x += chip_width + gap
