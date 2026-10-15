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


# Caption pill tokens shared by Home portal labels and profile names
# (runtime/theme-defaults.toml cocoa-ink family + cast cream/gold).
CAPTION_INK = (75, 55, 47)
CAPTION_CREAM = (255, 251, 235)
CAPTION_FOCUS = (255, 194, 52)
CAPTION_SHADOW = (205, 186, 150)


def draw_caption_pill(screen: Any, pygame: Any, slot: Any, label: Any, *, focused: bool) -> None:
    """Draw ``label`` centred on a cream (focused: sunshine) pill inside ``slot``.

    The pill hugs the text but never exceeds ``slot``, so neighbouring
    captions keep their gap and never overlap a portal or another caption.
    """

    pill_w = min(slot.width, label.get_width() + max(16, slot.height))
    pill = pygame.Rect(0, 0, pill_w, slot.height)
    pill.center = slot.center
    radius = pill.height // 2
    pygame.draw.rect(screen, CAPTION_SHADOW, pill.move(0, 2), border_radius=radius)
    pygame.draw.rect(
        screen, CAPTION_FOCUS if focused else CAPTION_CREAM, pill, border_radius=radius
    )
    pygame.draw.rect(screen, CAPTION_INK, pill, width=2, border_radius=radius)
    screen.blit(label, label.get_rect(center=pill.center))


def draw_title_pill(
    screen: Any,
    pygame: Any,
    slot: Any,
    label: Any,
    *,
    focused: bool,
    min_height: int,
) -> Any:
    """Draw a one- or two-line title on the caption pill, hugging the text.

    The pill is top-aligned in ``slot`` (so a one-line title sits close to its
    card) and never exceeds the slot. Same tokens as :func:`draw_caption_pill`.
    Returns the drawn pill rectangle.
    """

    pad_y = max(3, min_height // 6)
    pill_h = min(slot.height, max(min_height, label.get_height() + 2 * pad_y))
    pill_w = min(slot.width, label.get_width() + max(16, min_height))
    pill = pygame.Rect(0, 0, pill_w, pill_h)
    pill.midtop = (slot.centerx, slot.top)
    radius = min(pill.height // 2, min_height // 2)
    pygame.draw.rect(screen, CAPTION_SHADOW, pill.move(0, 2), border_radius=radius)
    pygame.draw.rect(
        screen, CAPTION_FOCUS if focused else CAPTION_CREAM, pill, border_radius=radius
    )
    pygame.draw.rect(screen, CAPTION_INK, pill, width=2, border_radius=radius)
    screen.blit(label, label.get_rect(center=pill.center))
    return pill


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
    """Place the storybook scene and reviewed panel artwork behind Shell content.

    Every Shell surface stands on one cached backdrop: theme background colour,
    then the child's wallpaper or (by default) the transparent-sky
    ``bg.meadow_day.home`` scene, then optionally the large tray. The profile
    picker and Collection Home omit the tray; Collection pages keep it.
    The panel is visual framing only. Existing profile/activity layout, hit
    targets, category navigation and lifecycle remain authoritative in the base
    presentation. Missing/corrupt optional artwork falls back to the normal
    theme background without disabling the independently proven Activity cards.
    """

    _PANEL_SOURCE_WIDTH = 640
    _PANEL_SOURCE_HEIGHT = 420
    # Storybook meadow behind every Shell surface (transparent sky layer).
    _SCENE_ASSET_ID = "bg.meadow_day.home"
    _SCENE_SOURCE_SIZE = (1024, 600)

    def _render_profile_picker_content(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        # The picker shares the Home storybook meadow instead of a big empty
        # tray: profile cards stand directly on the scene. The base picker
        # then uses its panel-free layout (no stale panel bounds survive).
        self._draw_shell_scene_backdrop(screen, pygame, theme=theme)
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

        self._ensure_shared_panel_backdrop(
            screen,
            theme,
            pygame,
            top=top,
            bottom_margin=bottom_margin,
            max_width=max_width,
        )

    def _draw_shell_scene_backdrop(
        self, screen: Any, pygame: Any, *, theme: Any = None
    ) -> None:
        """Blit the cached storybook scene backdrop without the large tray.

        Used by surfaces whose content stands directly on the scene (profile
        picker, Collection Home). Clears the panel content bounds so callers
        never lay out against a tray that is not drawn.
        """

        self._shared_panel_inner_rect = None
        self._shell_panel_layout = None
        self._ensure_shared_panel_backdrop(screen, theme, pygame, panel=False)

    def _shell_scene_layer(self, size: tuple[int, int], pygame: Any) -> Any | None:
        """Return the meadow scene COVER-fitted to ``size`` (composition-time only).

        The 1024x600 rendition is decoded once through the bounded visual
        cache; cropping/scaling happens only while a backdrop is composed, and
        the composed backdrop is what every frame blits. Bottom-anchored so the
        ground stays visible on very wide screens. Missing or corrupt artwork
        disables only this decoration.
        """

        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None or getattr(self, "_shared_scene_disabled", False):
            return None
        try:
            source = visual_cache.get(
                self._SCENE_ASSET_ID,
                variant="default",
                size=self._SCENE_SOURCE_SIZE,
            )
        except _SHARED_VISUAL_ERRORS:
            self._shared_scene_disabled = True
            return None
        except pygame.error:
            self._shared_scene_disabled = True
            return None
        width, height = size
        source_w, source_h = source.get_size()
        scale = max(width / source_w, height / source_h)
        crop_w = max(1, min(source_w, int(round(width / scale))))
        crop_h = max(1, min(source_h, int(round(height / scale))))
        crop = pygame.Rect((source_w - crop_w) // 2, source_h - crop_h, crop_w, crop_h)
        try:
            region = source.subsurface(crop)
            if region.get_size() == (width, height):
                return region
            return pygame.transform.smoothscale(region, (width, height))
        except (ValueError, pygame.error):
            self._shared_scene_disabled = True
            return None

    @classmethod
    def compute_shell_panel_layout(
        cls,
        width: int,
        height: int,
        top: int = 72,
        bottom_margin: int = 18,
        max_width: int = 1180,
    ) -> tuple[UiRect, ShellPanelLayout]:
        """Compute the raw panel rect and visible ShellPanelLayout for a viewport."""
        top_c = max(0, min(top, height - 1))
        available_height = max(1, height - top_c - max(0, bottom_margin))
        available_width = max(1, min(width - 24, max_width))

        panel_height = available_height
        panel_width = int(
            round(
                panel_height
                * cls._PANEL_SOURCE_WIDTH
                / cls._PANEL_SOURCE_HEIGHT
            )
        )
        if panel_width > available_width:
            panel_width = available_width
            panel_height = int(
                round(
                    panel_width
                    * cls._PANEL_SOURCE_HEIGHT
                    / cls._PANEL_SOURCE_WIDTH
                )
            )

        panel_x = (width - panel_width) // 2
        panel_y = top_c + (available_height - panel_height) // 2
        raw_rect = UiRect(panel_x, panel_y, panel_width, panel_height)

        visible_left = panel_x + round(panel_width * 36 / cls._PANEL_SOURCE_WIDTH)
        visible_top = panel_y + round(panel_height * 28 / cls._PANEL_SOURCE_HEIGHT)
        visible_width = round(panel_width * 568 / cls._PANEL_SOURCE_WIDTH)
        visible_height = round(panel_height * 336 / cls._PANEL_SOURCE_HEIGHT)

        inner_left = panel_x + round(panel_width * 58 / cls._PANEL_SOURCE_WIDTH)
        inner_top = panel_y + round(panel_height * 52 / cls._PANEL_SOURCE_HEIGHT)
        inner_width = round(panel_width * 524 / cls._PANEL_SOURCE_WIDTH)
        inner_height = round(panel_height * 288 / cls._PANEL_SOURCE_HEIGHT)

        layout = ShellPanelLayout(
            outer_rect=UiRect(visible_left, visible_top, visible_width, visible_height),
            content_rect=UiRect(inner_left, inner_top, inner_width, inner_height),
        )
        return raw_rect, layout

    def _ensure_shared_panel_backdrop(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        *,
        top: int = 72,
        bottom_margin: int = 18,
        max_width: int = 1180,
        panel: bool = True,
    ) -> None:
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return

        width, height = screen.get_size()
        raw_rect, layout = self.compute_shell_panel_layout(
            width, height, top=top, bottom_margin=bottom_margin, max_width=max_width
        )
        panel_rect = pygame.Rect(raw_rect.x, raw_rect.y, raw_rect.width, raw_rect.height)

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
            (int(top), int(bottom_margin), int(max_width)) if panel else None,
            width,
            height,
        )
        backdrop = self._backdrop_cache.get(backdrop_key)
        if backdrop is None:
            panel_surface = None
            if panel:
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
                # A child-chosen wallpaper is personal: it replaces the scene.
                backdrop.blit(wallpaper, (0, 0))
            else:
                # Transparent sky: the child's background colour stays visible.
                scene = self._shell_scene_layer((width, height), pygame)
                if scene is not None:
                    backdrop.blit(scene, (0, 0))
            if panel_surface is not None:
                backdrop.blit(panel_surface, panel_rect)
            self._backdrop_cache[backdrop_key] = backdrop

        screen.blit(backdrop, (0, 0))
        self._last_scene_backdrop = backdrop
        if not panel:
            return

        self._shared_panel_inner_rect = pygame.Rect(
            layout.content_rect.x,
            layout.content_rect.y,
            layout.content_rect.width,
            layout.content_rect.height,
        )
        self._shell_panel_layout = layout


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
        from .catalogue_view import ActivityFolder

        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None or isinstance(activity, ActivityFolder):
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
            from .presentation import _launch_status_label

            launch_surf = launch_font.render(
                self._child_display_text(_launch_status_label(self._active_locale)),
                True, (255, 255, 255),
            )
            screen.blit(launch_surf, launch_surf.get_rect(center=badge_rect.center))

    def _activity_title_for_shared_card(self, activity: Any) -> str:
        from .presentation import _activity_title

        return _activity_title(activity, self._active_locale)
