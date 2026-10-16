"""Collection-first Greia Home presentation for the child Shell.

The normal child Home is a bounded set of semantic Collection destinations,
not an ``All Activities`` wall with filter tabs. This mixin changes only the
launcher presentation/navigation projection. Activity identity, registry,
permissions, lifecycle and storage remain owned by the existing launcher core.
"""

from __future__ import annotations

from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_effects import transformed_rect
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError
from greia_platform.ui_motion import InteractionVisualState

from greia_platform.responsive_layout import UiRect

from .catalogue_view import ALL_ACTIVITIES_ID, _category_title
from .collection_hues import COLLECTION_HUES, HUE_RGB
from .home_layout import (
    CollectionHomeLayout,
    achievement_button_rect,
    overlaps,
    portal_icon_rect,
    usage_pill_band,
)
from .main import HitTarget
from .shared_ui_presentation import CAPTION_CREAM, CAPTION_INK, draw_caption_pill


_COLLECTION_VISUAL_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)

# Collection hue per Home portal lives in one shared vocabulary
# (GREIA_SVG_AUTHORING_RULES §7). Kept under the historical private names for
# the Home layout tests; both are the shared tables, never copies.
_COLLECTION_PORTAL_HUES = COLLECTION_HUES
_FALLBACK_HUES = HUE_RGB


class CollectionFirstHomeMixin:
    """Present primary Collections as the child-facing Greia Home.

    ``ALL_ACTIVITIES_ID`` remains an internal catalogue projection, but when it
    is the current launcher location this mixin renders available primary
    Collections as large portal destinations. Entering a Collection reuses the
    already-proven Activity catalogue/card path. Local Back returns here.

    Home is laid out by :class:`~greia_launcher.home_layout.CollectionHomeLayout`
    (one responsive semantic layout) over the shared storybook scene. Each
    portal uses the ``ui.portal.collection`` art in its Collection hue; the
    focused portal adds ``ui.portal.collection_focus``. Both are optional and
    fail-soft: if a rendition is missing or corrupt, Home stays usable with a
    primitive tile fallback while the rest of the shared UI stays enabled.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._home_collection_selected = 0
        self._shared_collection_portal_disabled = False

    def _home_collections(self) -> tuple[Any, ...]:
        return tuple(
            collection
            for collection in self._catalogue.collections
            if collection.collection_id != ALL_ACTIVITIES_ID and collection.items
        )

    def _home_columns(self, pygame: Any) -> int:
        surface = pygame.display.get_surface()
        width = surface.get_width() if surface is not None else 1024
        height = surface.get_height() if surface is not None else 600
        if width >= height:
            # Landscape screens (480x320 up to 1280x800 and wider) show the six
            # Home destinations as three columns x two rows: shallow rows keep
            # every portal large instead of stacking three short rows.
            return 3 if width >= 480 else 2 if width >= 320 else 1
        if width >= 620:
            return 3
        if width >= 320:
            return 2
        return 1

    def _set_home_collection_selected(self, index: int) -> None:
        collections = self._home_collections()
        if not collections:
            self._home_collection_selected = 0
        else:
            self._home_collection_selected = min(max(0, index), len(collections) - 1)
        # The existing activities surface cache predates Collection-first Home;
        # explicitly invalidate it when keyboard/controller focus changes.
        self._cached_activities_key = None

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        """Every profile activation starts at Greia Home, never a stale Collection."""

        super()._activate_profile(profile, pygame)
        self._home_collection_selected = 0
        self._set_category(ALL_ACTIVITIES_ID)

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._mode != "activities" or self._category_id != ALL_ACTIVITIES_ID:
            return super()._handle_key(key, pygame)

        old_idx = getattr(self, "_home_collection_selected", 0)
        was_launch = key in {pygame.K_RETURN, pygame.K_SPACE}
        if was_launch:
            try:
                self._stop_spoken_labels()  # type: ignore[attr-defined]
            except Exception:
                pass
        self._last_result = None
        self._catalogue_error = False
        collections = self._home_collections()
        if collections:
            self._home_collection_selected = min(
                self._home_collection_selected, len(collections) - 1
            )

        if key == pygame.K_TAB and collections:
            self._set_home_collection_selected(
                (self._home_collection_selected + 1) % len(collections)
            )
        elif collections and key in {
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_UP,
            pygame.K_DOWN,
        }:
            columns = self._home_columns(pygame)
            if key == pygame.K_LEFT:
                delta = -1
            elif key == pygame.K_RIGHT:
                delta = 1
            elif key == pygame.K_UP:
                delta = -columns
            else:
                delta = columns
            self._set_home_collection_selected(self._home_collection_selected + delta)
        elif key in {pygame.K_RETURN, pygame.K_SPACE} and collections:
            cid = collections[self._home_collection_selected].collection_id
            self._set_category(cid)
            try:
                self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
            except Exception:
                pass
            return True
        elif key in {pygame.K_BACKSPACE, pygame.K_ESCAPE}:
            # At launcher root, Back returns to profile choice rather than
            # manufacturing an additional hidden hierarchy level.
            try:
                self._stop_spoken_labels()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._logout(pygame)
            return True
        elif self.allow_exit and key == pygame.K_q:
            try:
                self._stop_spoken_labels()  # type: ignore[attr-defined]
            except Exception:
                pass
            return False
        # Announce home collection selection changes
        try:
            if getattr(self, "_home_collection_selected", 0) != old_idx:
                cols = self._home_collections()
                if 0 <= self._home_collection_selected < len(cols):
                    cid = cols[self._home_collection_selected].collection_id
                    self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
        except Exception:
            pass
        return True

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        if self._mode == "activities" and self._category_id == ALL_ACTIVITIES_ID:
            for target in reversed(self._targets):
                if not target.rect.collidepoint(position):
                    continue
                if target.action == "home_collection":
                    self._last_result = None
                    self._catalogue_error = False
                    collection_id = str(target.value)
                    for index, collection in enumerate(self._home_collections()):
                        if collection.collection_id == collection_id:
                            self._home_collection_selected = index
                            break
                    try:
                        self._stop_spoken_labels()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    self._set_category(collection_id)
                    try:
                        self._spoken_labels.announce_collection(collection_id, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    return
        super()._handle_click(position, pygame)

    def _scroll_activity_rows(self, direction: int, pygame: Any) -> None:
        if self._category_id == ALL_ACTIVITIES_ID:
            return
        super()._scroll_activity_rows(direction, pygame)

    def _render_activities_content(self, screen: Any, theme: Any, pygame: Any) -> None:
        if self._category_id != ALL_ACTIVITIES_ID:
            super()._render_activities_content(screen, theme, pygame)
            return
        self._render_collection_home(screen, theme, pygame)

    def _home_reserved_rects(self, width: int, height: int) -> tuple[UiRect, ...]:
        """Return the protected corner controls the Home layout must not touch."""

        reserved: list[UiRect] = []
        if self._active_profile is not None:
            badge = self._home_profile_badge_size(height)
            reserved.append(UiRect(14, 10, badge, badge))
        # Achievement star (AchievementLibraryMixin) plus its count pill, or
        # the gentle error badge, occupy the same top-right corner.
        star = achievement_button_rect(width, height)
        reserved.append(UiRect(star.x, star.y, star.width + 4, star.height + 4))

        return tuple(reserved)

    @staticmethod
    def _home_profile_badge_size(height: int) -> int:
        return max(62, min(86, height // 7))

    def _render_collection_home(self, screen: Any, theme: Any, pygame: Any) -> None:
        width, height = screen.get_size()

        # Home stands directly on the storybook meadow (no big empty tray).
        draw_scene = getattr(self, "_draw_shell_scene_backdrop", None)
        if draw_scene is not None:
            draw_scene(screen, pygame, theme=theme)

        # Keep the same active-profile route available on top of Home framing.
        if self._active_profile is not None:
            badge_size = self._home_profile_badge_size(height)
            badge = pygame.Rect(14, 10, badge_size, badge_size)
            pygame.draw.rect(screen, theme.panel, badge, border_radius=22)
            pygame.draw.rect(screen, theme.accent, badge, width=5, border_radius=22)
            avatar = self._load_icon(
                self._active_profile.profile.avatar_id,
                badge_size - 12,
                pygame,
            )
            screen.blit(avatar, avatar.get_rect(center=badge.center))
            self._targets.append(HitTarget("switch_profile", None, badge))
            overlay_profile = getattr(self, "_overlay_active_profile_frame", None)
            if overlay_profile is not None:
                overlay_profile(
                    screen,
                    badge,
                    self._active_profile.profile,
                    theme,
                    pygame,
                )

        collections = self._home_collections()
        if not collections:
            self._draw_empty(screen, pygame)
            return
        self._home_collection_selected = min(
            self._home_collection_selected, len(collections) - 1
        )

        reserved = self._home_reserved_rects(width, height)
        layout = CollectionHomeLayout.compute(
            width, height, len(collections), self._home_columns(pygame), reserved=reserved
        )
        # On very small screens the portal grid reaches the top row; then keep
        # it clear of the time-left pill too (larger screens are unaffected).
        band = usage_pill_band(
            width, height, left_limit=14 + self._home_profile_badge_size(height)
        )
        if any(overlaps(band, hit) for hit in layout.hits):
            layout = CollectionHomeLayout.compute(
                width,
                height,
                len(collections),
                self._home_columns(pygame),
                reserved=(*reserved, band),
            )

        # The child's own cast friend greets them from the free margin.
        greeter = getattr(self, "_draw_profile_greeter", None)
        if layout.greeter is not None and greeter is not None:
            avatar_id = (
                self._active_profile.profile.avatar_id
                if self._active_profile is not None
                else None
            )
            greeter(screen, layout.greeter, avatar_id, "pose_cheer", pygame)

        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        compact = width <= 800

        for index, collection in enumerate(collections):
            portal = layout.portals[index]
            hit = layout.hits[index]
            portal_rect = pygame.Rect(portal.x, portal.y, portal.width, portal.height)
            hit_rect = pygame.Rect(hit.x, hit.y, hit.width, hit.height)
            focused = index == self._home_collection_selected
            hovered = pointer_active and hit_rect.collidepoint(pointer)
            # Hover lifts the portal; only the one focused portal (keyboard /
            # controller / last choice) wears the ring, so there is never more
            # than one selection marker on screen.
            state = InteractionVisualState(hovered=hovered or focused, selected=False)
            target = transformed_rect(portal_rect, self._HOVER.sample(state), pygame)

            self._draw_home_portal(
                screen, target, collection.collection_id, focused, theme, pygame
            )

            # Size from the untransformed portal so hover motion reuses the
            # cached icon; centre on the drawn art's cream window.
            icon_box = portal_icon_rect(
                UiRect(target.x, target.y, target.width, target.height)
            )
            icon_size = portal_icon_rect(portal).width
            icon = self._category_shadowed_icon(
                collection.icon_id or "backpack",
                icon_size,
                shadow_alpha=40,
                shadow_offset=max(2, icon_size // 28),
                pygame=pygame,
            )
            screen.blit(
                icon,
                icon.get_rect(
                    center=(
                        icon_box.x + icon_box.width // 2,
                        icon_box.y + icon_box.height // 2,
                    )
                ),
            )

            # A six-portal layout should not squeeze a long saved-work label
            # into unreadable miniature text on the 480-800px canvases.
            label_text = _category_title(
                collection.collection_id,
                self._active_locale,
                compact=compact,
            )
            self._draw_home_label(
                screen, layout.labels[index], label_text, layout.label_font_px,
                focused, theme, pygame,
            )
            self._targets.append(
                HitTarget("home_collection", collection.collection_id, hit_rect)
            )

        if (self._last_result and not self._last_result.succeeded) or self._catalogue_error:
            self._draw_error_badge(screen, pygame)

    def _draw_home_portal(
        self,
        screen: Any,
        rect: Any,
        collection_id: str,
        focused: bool,
        theme: Any,
        pygame: Any,
    ) -> None:
        """Draw one Collection portal tile (shared art, primitive fallback)."""

        hue = _COLLECTION_PORTAL_HUES.get(collection_id, "default")
        visual_cache = getattr(self, "_visual_cache", None)
        tile = ring = None
        if not self._shared_collection_portal_disabled and visual_cache is not None:
            try:
                tile = visual_cache.get(
                    "ui.portal.collection", variant=hue, size=rect.size
                )
                if focused:
                    ring = visual_cache.get(
                        "ui.portal.collection_focus", variant="default", size=rect.size
                    )
            except _COLLECTION_VISUAL_ERRORS:
                self._shared_collection_portal_disabled = True
                tile = ring = None
            except pygame.error:
                self._shared_collection_portal_disabled = True
                tile = ring = None
        if tile is not None:
            screen.blit(tile, rect)
            if ring is not None:
                screen.blit(ring, rect)
            return

        # Narrow fallback: keep Collection-first information architecture and a
        # visible focus even when only this optional artwork is broken.
        body = pygame.Rect(
            rect.x + round(rect.width * 28 / 288),
            rect.y + round(rect.height * 26 / 304),
            round(rect.width * 232 / 288),
            round(rect.height * 250 / 304),
        )
        radius = max(8, body.width // 4)
        pygame.draw.rect(
            screen, _FALLBACK_HUES.get(hue, theme.accent), body, border_radius=radius
        )
        pygame.draw.rect(screen, CAPTION_INK, body, width=3, border_radius=radius)
        window = body.width * 90 // 232
        pygame.draw.circle(screen, CAPTION_CREAM, body.center, window)
        if focused:
            pygame.draw.rect(
                screen, theme.accent, body.inflate(14, 14), width=5,
                border_radius=radius + 7,
            )

    def _draw_home_label(
        self,
        screen: Any,
        slot: UiRect,
        text: str,
        font_px: int,
        focused: bool,
        theme: Any,
        pygame: Any,
    ) -> None:
        """Draw a Collection caption on a cream pill that never overlaps a portal."""

        # Keep half the pill height as padding on each side of the text.
        max_text_w = max(24, slot.width - slot.height)
        size = font_px
        label = self._category_label_surface(text, size, theme.text, pygame)
        # Prefer a smaller real font size over squashing glyphs.
        while label.get_width() > max_text_w and size > 12:
            size -= 1
            label = self._category_label_surface(text, size, theme.text, pygame)
        if label.get_width() > max_text_w:
            label = pygame.transform.smoothscale(
                label,
                (
                    max_text_w,
                    max(1, round(label.get_height() * max_text_w / label.get_width())),
                ),
            )
        draw_caption_pill(
            screen,
            pygame,
            pygame.Rect(slot.x, slot.y, slot.width, slot.height),
            label,
            focused=focused,
        )
