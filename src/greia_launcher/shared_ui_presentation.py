"""Shared Greia UI artwork consumption for the production child Shell.

This module is deliberately narrow: it consumes already-generated semantic UI
assets through the launcher-owned bounded visual cache. It does not discover
source artwork, rasterize SVG, or own Activity/lifecycle authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_effects import transformed_rect
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError
from greia_platform.responsive_layout import UiRect


@dataclass(frozen=True, slots=True)
class ShellPanelLayout:
    """Formal layout seam exposing both outer panel framing and inner content bounds."""

    outer_rect: UiRect
    content_rect: UiRect


_SHARED_VISUAL_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)


class SharedUiCategoryButtonMixin:
    """Render root Activity-category controls with shared button artwork.

    This changes presentation only. Category IDs, hit rectangles, ordering,
    navigation and in-category Back behavior remain owned by the base launcher.
    If the optional button rendition fails, only this category-button treatment
    is disabled; the independently accepted shared panel/card paths remain live.
    """

    def _draw_category_bar(self, screen: Any, theme: Any, pygame: Any) -> None:
        from .catalogue_view import ALL_ACTIVITIES_ID, _category_title
        from .main import HitTarget

        if (
            getattr(self, "_shared_category_buttons_disabled", False)
            or getattr(self, "_visual_cache", None) is None
        ):
            super()._draw_category_bar(screen, theme, pygame)
            return
        if not self._catalogue.category_ids:
            return
        if self._category_id != ALL_ACTIVITIES_ID:
            super()._draw_category_bar(screen, theme, pygame)
            return

        collections = tuple(
            item
            for item in self._catalogue.collections
            if item.collection_id != ALL_ACTIVITIES_ID
        )
        if not collections:
            return

        left = 112 if self._active_profile is not None else 20
        error_active = (
            (self._last_result and not self._last_result.succeeded)
            or self._catalogue_error
        )
        right = screen.get_width() - (76 if error_active else 20)
        gap = 9
        height = max(42, min(52, screen.get_height() // 11))
        available = max(0, right - left)
        show_labels = available >= len(collections) * 112
        x = left
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        pending_targets: list[Any] = []

        for collection in collections:
            label_text = _category_title(collection.collection_id, self._active_locale)
            font_size = max(18, min(22, height // 2))
            label = self._category_label_surface(
                label_text, font_size, theme.text, pygame
            )
            icon_size = max(26, height - 14)
            if show_labels:
                width = min(174, max(88, label.get_width() + icon_size + 32))
            else:
                width = height
            if x + width > right:
                break

            rect = pygame.Rect(x, 18, width, height)
            hovered = pointer_active and rect.collidepoint(pointer)
            try:
                button_surface = self._visual_cache.get(
                    "ui.button.primary",
                    variant="hover" if hovered else "default",
                    size=rect.size,
                )
            except _SHARED_VISUAL_ERRORS:
                self._shared_category_buttons_disabled = True
                super()._draw_category_bar(screen, theme, pygame)
                return
            except pygame.error:
                self._shared_category_buttons_disabled = True
                super()._draw_category_bar(screen, theme, pygame)
                return

            screen.blit(button_surface, rect)
            category_icon = self._category_shadowed_icon(
                collection.icon_id or "backpack",
                icon_size,
                shadow_alpha=40,
                shadow_offset=2,
                pygame=pygame,
            )
            if show_labels:
                icon_center = (rect.left + 12 + icon_size // 2, rect.centery)
                screen.blit(
                    category_icon,
                    category_icon.get_rect(center=icon_center),
                )
                label_rect = label.get_rect(
                    midleft=(rect.left + 20 + icon_size, rect.centery)
                )
                screen.blit(label, label_rect)
            else:
                screen.blit(
                    category_icon,
                    category_icon.get_rect(center=rect.center),
                )

            pending_targets.append(
                HitTarget("activity_category", collection.collection_id, rect)
            )
            x += width + gap

        self._targets.extend(pending_targets)


class SharedUiShellPanelMixin:
    """Place reviewed shared panel artwork behind real Shell content.

    The panel is visual framing only. Existing profile/activity layout, hit
    targets, category navigation and lifecycle remain authoritative in the base
    presentation. Missing/corrupt optional artwork falls back to the normal
    theme background without disabling the independently proven Activity cards.
    """

    _PANEL_SOURCE_WIDTH = 640
    _PANEL_SOURCE_HEIGHT = 420

    def _render_profile_picker_content(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        height = screen.get_height()
        header_size = max(70, min(100, height // 6))
        self._draw_shared_shell_panel(
            screen,
            pygame,
            top=header_size + 4,
            bottom_margin=14,
            max_width=940,
            theme=theme,
        )
        super()._render_profile_picker_content(screen, theme, pygame)

    def _render_activities_content(self, screen: Any, theme: Any, pygame: Any) -> None:
        height = screen.get_height()
        width = screen.get_width()
        panel_top = max(52, min(62, height // 10))
        self._draw_shared_shell_panel(
            screen,
            pygame,
            top=panel_top,
            bottom_margin=4,
            max_width=width - 24,
            theme=theme,
        )
        super()._render_activities_content(screen, theme, pygame)

    def _draw_shared_shell_panel(
        self,
        screen: Any,
        pygame: Any,
        *,
        top: int,
        bottom_margin: int,
        max_width: int,
        theme: Any = None,
    ) -> None:
        """Blit the pre-composited scene backdrop behind real Shell content.

        The backdrop (background fill + optional wallpaper + shared panel
        artwork) is composed once per theme/geometry and reused as one opaque,
        fast-blitting surface. This keeps per-frame cost independent of the
        large alpha-blended panel artwork on low-resource devices, and exposes
        the composed surface for incremental tile repairs. Panel identity,
        layout and hit targets remain owned by the base launcher.
        """

        self._shared_panel_inner_rect = None
        self._shell_panel_layout: ShellPanelLayout | None = None
        self._last_scene_backdrop = None
        if getattr(self, "_shared_panel_disabled", False):
            return
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return

        width, height = screen.get_size()
        top = max(0, min(top, height - 1))
        available_height = max(1, height - top - max(0, bottom_margin))
        available_width = max(1, min(width - 24, max_width))

        panel_height = available_height
        panel_width = int(
            round(
                panel_height
                * self._PANEL_SOURCE_WIDTH
                / self._PANEL_SOURCE_HEIGHT
            )
        )
        if panel_width > available_width:
            panel_width = available_width
            panel_height = int(
                round(
                    panel_width
                    * self._PANEL_SOURCE_HEIGHT
                    / self._PANEL_SOURCE_WIDTH
                )
            )

        panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
        panel_rect.centerx = width // 2
        panel_rect.top = top + (available_height - panel_height) // 2

        if theme is None:
            theme = self.theme_controller.theme

        wallpaper_token = None
        wallpaper_path = getattr(theme, "wallpaper_path", None)
        if wallpaper_path is not None:
            try:
                stat = wallpaper_path.stat()
                wallpaper_token = (str(wallpaper_path), stat.st_mtime_ns)
            except OSError:
                return

        backdrop_key = (
            "scene",
            theme.background,
            wallpaper_token,
            int(top),
            int(bottom_margin),
            int(max_width),
            width,
            height,
        )
        backdrop = self._backdrop_cache.get(backdrop_key)
        if backdrop is None:
            try:
                panel_surface = visual_cache.get(
                    "ui.panel.base",
                    variant="default",
                    size=panel_rect.size,
                )
            except _SHARED_VISUAL_ERRORS:
                self._shared_panel_disabled = True
                return
            except pygame.error:
                self._shared_panel_disabled = True
                return

            backdrop = pygame.Surface((width, height)).convert()
            backdrop.fill(theme.background)
            wallpaper = self.theme_controller.wallpaper_for(
                theme, (width, height), pygame
            )
            if wallpaper is not None:
                backdrop.blit(wallpaper, (0, 0))
            backdrop.blit(panel_surface, panel_rect)
            self._backdrop_cache[backdrop_key] = backdrop

        screen.blit(backdrop, (0, 0))
        self._last_scene_backdrop = backdrop

        inner_left = panel_rect.left + round(panel_rect.width * 58 / self._PANEL_SOURCE_WIDTH)
        inner_top = panel_rect.top + round(panel_rect.height * 52 / self._PANEL_SOURCE_HEIGHT)
        inner_width = round(panel_rect.width * 524 / self._PANEL_SOURCE_WIDTH)
        inner_height = round(panel_rect.height * 288 / self._PANEL_SOURCE_HEIGHT)
        self._shared_panel_inner_rect = pygame.Rect(inner_left, inner_top, inner_width, inner_height)
        self._shell_panel_layout = ShellPanelLayout(
            outer_rect=UiRect(panel_rect.left, panel_rect.top, panel_rect.width, panel_rect.height),
            content_rect=UiRect(inner_left, inner_top, inner_width, inner_height),
        )


class SharedUiActivityCardMixin:
    """Render launcher Activity tiles with the shared Greia card artwork.

    The existing primitive renderer remains the fail-soft fallback. The shared
    card is purely presentation: hit targets, selection/navigation, catalogue
    semantics and launch lifecycle stay owned by ``GreiaLauncherPresentation``.
    """

    _CARD_SOURCE_WIDTH = 360
    _CARD_SOURCE_HEIGHT = 430

    def _draw_activity_tile_content(
        self,
        screen: Any,
        rect: Any,
        activity: Any,
        state: Any,
        theme: Any,
        pygame: Any,
    ) -> None:
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            super()._draw_activity_tile_content(
                screen, rect, activity, state, theme, pygame
            )
            return

        motion = (
            self._LAUNCH.sample(time.monotonic() - self._launch_animation_started)
            if state.launching
            else self._HOVER.sample(state)
        )
        target = transformed_rect(rect, motion, pygame)

        card_height = max(1, target.height)
        card_width = max(
            1,
            min(
                target.width,
                int(round(card_height * self._CARD_SOURCE_WIDTH / self._CARD_SOURCE_HEIGHT)),
            ),
        )
        card_rect = pygame.Rect(0, 0, card_width, card_height)
        card_rect.center = target.center
        variant = "focused" if state.emphasized or state.launching else "default"

        try:
            card_surface = visual_cache.get(
                "ui.card.activity",
                variant=variant,
                size=card_rect.size,
            )
        except _SHARED_VISUAL_ERRORS:
            super()._draw_activity_tile_content(
                screen, rect, activity, state, theme, pygame
            )
            return
        except pygame.error:
            super()._draw_activity_tile_content(
                screen, rect, activity, state, theme, pygame
            )
            return

        screen.blit(card_surface, card_rect)

        content_rect = pygame.Rect(
            card_rect.left + round(card_rect.width * 45 / self._CARD_SOURCE_WIDTH),
            card_rect.top + round(card_rect.height * 43 / self._CARD_SOURCE_HEIGHT),
            max(1, round(card_rect.width * 270 / self._CARD_SOURCE_WIDTH)),
            max(1, round(card_rect.height * 236 / self._CARD_SOURCE_HEIGHT)),
        )
        label_rect = pygame.Rect(
            card_rect.left + round(card_rect.width * 28 / self._CARD_SOURCE_WIDTH),
            card_rect.top + round(card_rect.height * 272 / self._CARD_SOURCE_HEIGHT),
            max(1, round(card_rect.width * 304 / self._CARD_SOURCE_WIDTH)),
            max(1, round(card_rect.height * 118 / self._CARD_SOURCE_HEIGHT)),
        )

        icon_size = max(
            56,
            min(
                int(round(content_rect.width * 0.92)),
                int(round(content_rect.height * 0.92)),
            ),
        )
        icon = self._activity_icon(activity, icon_size, pygame)
        screen.blit(icon, icon.get_rect(center=content_rect.center))

        title = self._render_activity_label(
            self._child_display_text(self._activity_title_for_shared_card(activity)),
            max_width=max(28, label_rect.width - 6),
            max_height=max(22, label_rect.height - 4),
            pygame=pygame,
            color=theme.text,
            preferred_size=max(13, min(16, card_rect.height // 10)),
        )
        screen.blit(title, title.get_rect(center=label_rect.center))


        if state.launching:
            badge_h = max(24, min(32, card_rect.height // 5))
            badge_w = max(70, min(100, int(card_rect.width * 0.72)))
            badge_rect = pygame.Rect(0, 0, badge_w, badge_h)
            badge_rect.center = (card_rect.centerx, card_rect.top + int(card_rect.height * 0.28))
            pygame.draw.rect(screen, (239, 77, 83), badge_rect, border_radius=badge_h // 2)
            pygame.draw.rect(screen, (255, 255, 255), badge_rect, width=2, border_radius=badge_h // 2)
            launch_font = self._font(max(12, min(15, badge_h - 10)), pygame)
            launch_surf = launch_font.render(
                self._child_display_text("Avvio..."), True, (255, 255, 255)
            )
            screen.blit(launch_surf, launch_surf.get_rect(center=badge_rect.center))

    def _activity_title_for_shared_card(self, activity: Any) -> str:
        from .presentation import _activity_title

        return _activity_title(activity, self._active_locale)
