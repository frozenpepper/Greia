"""Shared profile-identity artwork for the production Greia child Shell.

This module intentionally owns presentation only. Profile selection, profile
storage, hit targets, Activity lifecycle and theme authority remain in the base
launcher. The shared avatar frame is optional and fail-soft.
"""

from __future__ import annotations

from typing import Any
import zlib

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_effects import transformed_rect
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError
from greia_platform.ui_motion import InteractionVisualState

from greia_platform.responsive_layout import UiRect

from .home_layout import (
    PORTAL_ART_HEIGHT,
    PORTAL_ART_WIDTH,
    greeter_rect,
    layout_scale,
    portal_icon_rect,
)
from .presentation import _mix
from .shared_ui_presentation import draw_caption_pill
from .system_chrome import resolve_trusted_action_minimum_px


_SHARED_PROFILE_VISUAL_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)

# Profile avatar IDs that are canonical cast faces (core_icons_v1.toml):
# the Home greeter is that same character, so the child sees "their" friend.
_AVATAR_CAST_CHARACTER = {
    "unicorn": "lilli",
    "robot": "dani",
    "owl": "leo",
    "green_monster": "momo",
}
# Leo is the cast's thoughtful guide: he greets on the profile picker and for
# non-cast avatars (dinosaur, wizard, future IDs).
_DEFAULT_GREETER_CHARACTER = "leo"


# Profile cards reuse the Collection portal art. Each child keeps one stable
# hue (derived from the opaque profile ID, never its position) so a card does
# not change colour when siblings are added.
_PROFILE_PORTAL_HUES = ("grape", "ocean", "coral", "leaf", "orange", "default")


def profile_portal_hue(profile_id: str) -> str:
    """Return the stable ``ui.portal.collection`` variant for a profile card."""

    return _PROFILE_PORTAL_HUES[zlib.crc32(profile_id.encode("utf-8")) % len(_PROFILE_PORTAL_HUES)]


def greeter_character_for(avatar_id: str | None) -> str:
    """Return the canonical cast ID that greets a profile with ``avatar_id``."""

    return _AVATAR_CAST_CHARACTER.get(avatar_id or "", _DEFAULT_GREETER_CHARACTER)


class SharedUiProfileChromeMixin:
    """Overlay reviewed shared avatar framing on real Shell profile identity.

    The base presentation is drawn first. The shared frame then replaces only
    the visual avatar treatment while retaining the exact profile-card and
    active-profile hit rectangles already owned by the launcher.

    Essential profile targets (picker frames, active-profile badge) enforce
    the shared physical floor from :mod:`greia_launcher.system_chrome`.
    Display metrics arrive only via the injected ``_display_metrics``
    attribute owned by the composition layer (``None`` means unknown:
    existing conservative pixels apply). Nothing here probes hardware, parses
    configuration, or scales decoration, gaps, or typography.
    """

    _FRAME_SOURCE_SIZE = 260
    _FRAME_INNER_CENTER_Y = 123 / 260

    def _chrome_metrics(self) -> Any:
        """Return injected display metrics, or ``None`` when unknown."""
        return getattr(self, "_display_metrics", None)

    def _render_activities_content(self, screen: Any, theme: Any, pygame: Any) -> None:
        super()._render_activities_content(screen, theme, pygame)

        if getattr(self, "_shared_profile_frame_disabled", False):
            return
        if getattr(self, "_visual_cache", None) is None:
            return
        if self._active_profile is None:
            return

        height = screen.get_height()
        base_badge = max(62, min(86, height // 7))
        badge_size = resolve_trusted_action_minimum_px(
            self._chrome_metrics(), fallback_px=base_badge
        )
        badge = pygame.Rect(14, 10, badge_size, badge_size)
        self._overlay_active_profile_frame(
            screen,
            badge,
            self._active_profile.profile,
            theme,
            pygame,
        )

    def _render_profile_picker_content(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        super()._render_profile_picker_content(screen, theme, pygame)
        if not self.profiles:
            return
        if any(target.action == "profile_page" for target in self._targets):
            # Paging arrows own the side margins; the greeter steps aside.
            return
        content = getattr(self, "_page_content_rect", None)
        if content is None:
            return
        rect = greeter_rect(
            screen.get_width(), screen.get_height(), free_right_edge=content.x
        )
        if rect is not None:
            self._draw_profile_greeter(screen, rect, None, "pose_point", pygame)

    def _draw_profile_greeter(
        self,
        screen: Any,
        rect: UiRect,
        avatar_id: str | None,
        pose: str,
        pygame: Any,
    ) -> bool:
        """Blit the canonical cast greeter for ``avatar_id`` into ``rect``.

        Presentation only: a cached shared ``character.<id>`` pose rendition.
        It owns no hit target and is fail-soft (returns False when the
        optional artwork is unavailable).
        """

        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None or getattr(self, "_shared_greeter_disabled", False):
            return False
        character = greeter_character_for(avatar_id)
        try:
            surface = visual_cache.get(
                f"character.{character}",
                variant=pose,
                size=(rect.width, rect.height),
            )
        except _SHARED_PROFILE_VISUAL_ERRORS:
            self._shared_greeter_disabled = True
            return False
        except pygame.error:
            self._shared_greeter_disabled = True
            return False
        screen.blit(surface, (rect.x, rect.y))
        return True

    def _avatar_frame_surface(self, size: int, pygame: Any) -> Any | None:
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return None
        try:
            return visual_cache.get(
                "ui.avatar.frame",
                variant="default",
                size=(size, size),
            )
        except _SHARED_PROFILE_VISUAL_ERRORS:
            self._shared_profile_frame_disabled = True
            return None
        except pygame.error:
            self._shared_profile_frame_disabled = True
            return None

    def _draw_profile_card(
        self,
        screen: Any,
        rect: Any,
        profile: Any,
        selected: bool,
        hovered: bool,
        theme: Any,
        pygame: Any,
    ) -> None:
        """Polymorphic profile card presentation with framed avatar artwork."""
        if getattr(self, "_shared_profile_frame_disabled", False) or getattr(self, "_visual_cache", None) is None:
            super()._draw_profile_card(screen, rect, profile, selected, hovered, theme, pygame)
            return
        if self._draw_profile_portal_card(
            screen, rect, profile, selected, hovered, theme, pygame
        ):
            return

        frame_size = max(
            56,
            min(
                int(round(rect.width * 0.82)),
                int(round(rect.height * 0.78)),
            ),
        )
        frame_size = resolve_trusted_action_minimum_px(
            self._chrome_metrics(), fallback_px=frame_size
        )
        # The profile card itself stays the authoritative target: the frame is
        # artwork inside it, so the physical floor never grows the frame past
        # the card that owns the hit rectangle. Enlarging the card geometry
        # belongs to the base launcher layout, not this presentation overlay.
        frame_size = min(frame_size, int(rect.width), int(rect.height))
        frame_surface = self._avatar_frame_surface(frame_size, pygame)
        if frame_surface is None:
            super()._draw_profile_card(screen, rect, profile, selected, hovered, theme, pygame)
            return

        is_highlighted = selected or hovered
        drawn = rect.move(0, -2 if is_highlighted else 0)

        # Grounding drop shadow
        shadow_rect = drawn.move(0, 4 if is_highlighted else 2)
        shadow_color = _mix(theme.background, (0, 0, 0), 0.14 if is_highlighted else 0.08)
        pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=26)

        # Card fill
        card_bg = _mix(theme.panel, (255, 255, 255), 0.35) if is_highlighted else theme.panel
        pygame.draw.rect(screen, card_bg, drawn, border_radius=26)

        # Subtle top sheen highlight line
        sheen_color = _mix(card_bg, (255, 255, 255), 0.60)
        pygame.draw.line(
            screen,
            sheen_color,
            (drawn.left + 24, drawn.top + 2),
            (drawn.right - 24, drawn.top + 2),
            width=1,
        )

        # Outline
        outline_color = theme.accent if is_highlighted else _mix(theme.text, theme.panel, 0.72)
        outline_width = 6 if selected else (3 if hovered else 2)
        pygame.draw.rect(
            screen,
            outline_color,
            drawn,
            width=outline_width,
            border_radius=26,
        )

        frame_rect = pygame.Rect(0, 0, frame_size, frame_size)
        frame_rect.center = (
            drawn.centerx,
            int(round(drawn.top + drawn.height * 0.40)),
        )
        screen.blit(frame_surface, frame_rect)

        avatar_size = max(30, int(round(frame_size * 0.53)))
        avatar = self._load_icon(profile.avatar_id, avatar_size, pygame)
        avatar_center = (
            frame_rect.centerx,
            frame_rect.top
            + int(round(frame_rect.height * self._FRAME_INNER_CENTER_Y)),
        )
        screen.blit(avatar, avatar.get_rect(center=avatar_center))

        font_size = max(23, min(38, drawn.height // 6))
        max_name_width = drawn.width - 18
        name = self._profile_name_surface(
            self._child_display_text(profile.display_name),
            font_size,
            max_name_width,
            theme.text,
            pygame,
        )
        screen.blit(name, name.get_rect(center=(drawn.centerx, drawn.bottom - drawn.height * 0.15)))

        if profile.has_secret:
            lock = self._load_icon("yellow_star", max(26, drawn.width // 7), pygame)
            screen.blit(lock, lock.get_rect(topright=(drawn.right - 8, drawn.top + 8)))

    def _draw_profile_portal_card(
        self,
        screen: Any,
        rect: Any,
        profile: Any,
        selected: bool,
        hovered: bool,
        theme: Any,
        pygame: Any,
    ) -> bool:
        """Draw a picker card in the Home portal family; False means fall back.

        The card rectangle stays the authoritative hit target. Inside it the
        portal tile (in the profile's stable hue) carries the avatar in its
        cream window and the name sits on the same caption pill as Home
        labels, so choosing yourself looks like choosing a Home destination.
        """

        if getattr(self, "_shared_profile_portal_disabled", False):
            return False
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return False
        # Same scale family as the Home portals: one card never dwarfs the
        # screen on 480x320 nor shrinks below a Home portal on 1280x800.
        scale = layout_scale(screen.get_width(), screen.get_height())
        font_size = max(16, min(32, int(round(26 * scale)), rect.height // 7))
        pill_h = font_size + max(8, int(round(12 * scale)))
        gap = max(3, int(round(5 * scale)))
        art_h = rect.height - pill_h - gap
        art_w = min(
            rect.width,
            int(round(168 * scale)),
            int(round(art_h * PORTAL_ART_WIDTH / PORTAL_ART_HEIGHT)),
        )
        art_h = int(round(art_w * PORTAL_ART_HEIGHT / PORTAL_ART_WIDTH))
        if art_w < 40:
            return False
        group_top = rect.top + max(0, (rect.height - art_h - gap - pill_h) // 2)
        art = pygame.Rect(0, 0, art_w, art_h)
        art.midtop = (rect.centerx, group_top)
        state = InteractionVisualState(hovered=selected or hovered)
        drawn = transformed_rect(art, self._HOVER.sample(state), pygame)
        try:
            tile = visual_cache.get(
                "ui.portal.collection",
                variant=profile_portal_hue(profile.profile_id),
                size=drawn.size,
            )
            ring = (
                visual_cache.get(
                    "ui.portal.collection_focus", variant="default", size=drawn.size
                )
                if selected
                else None
            )
        except _SHARED_PROFILE_VISUAL_ERRORS:
            self._shared_profile_portal_disabled = True
            return False
        except pygame.error:
            self._shared_profile_portal_disabled = True
            return False
        screen.blit(tile, drawn)
        if ring is not None:
            screen.blit(ring, drawn)

        window = portal_icon_rect(UiRect(drawn.x, drawn.y, drawn.width, drawn.height))
        # Avatars are whole characters, so they fill a little more of the window.
        avatar_size = max(24, int(round(art_w * 0.56)))
        avatar = self._load_icon(profile.avatar_id, avatar_size, pygame)
        screen.blit(
            avatar,
            avatar.get_rect(
                center=(window.x + window.width // 2, window.y + window.height // 2)
            ),
        )

        slot = pygame.Rect(rect.left, art.bottom + gap, rect.width, pill_h)
        name = self._profile_name_surface(
            self._child_display_text(profile.display_name),
            font_size,
            max(24, rect.width - pill_h - 8),
            theme.text,
            pygame,
        )
        draw_caption_pill(screen, pygame, slot, name, focused=selected)

        if profile.has_secret:
            lock = self._load_icon("yellow_star", max(22, art_w // 6), pygame)
            screen.blit(
                lock,
                lock.get_rect(
                    center=(
                        drawn.right - drawn.width * 40 // PORTAL_ART_WIDTH,
                        drawn.top + drawn.height * 44 // PORTAL_ART_HEIGHT,
                    )
                ),
            )
        return True

    def _overlay_active_profile_frame(
        self,
        screen: Any,
        badge: Any,
        profile: Any,
        theme: Any,
        pygame: Any,
    ) -> None:
        frame_size = min(badge.width, badge.height)
        frame_surface = self._avatar_frame_surface(frame_size, pygame)
        if frame_surface is None:
            return

        clear_rect = badge.inflate(16, 16)
        # Restore the exact composed scene behind the badge when available so
        # wallpaper themes keep correct pixels; plain background otherwise.
        backdrop = getattr(self, "_last_scene_backdrop", None)
        if backdrop is not None:
            restore = clear_rect.clip(backdrop.get_rect())
            screen.blit(backdrop, restore.topleft, restore)
        else:
            pygame.draw.rect(screen, theme.background, clear_rect)

        frame_rect = frame_surface.get_rect(center=badge.center)
        screen.blit(frame_surface, frame_rect)

        avatar_size = max(28, int(round(frame_size * 0.51)))
        avatar = self._load_icon(profile.avatar_id, avatar_size, pygame)
        avatar_center = (
            frame_rect.centerx,
            frame_rect.top
            + int(round(frame_rect.height * self._FRAME_INNER_CENTER_Y)),
        )
        screen.blit(avatar, avatar.get_rect(center=avatar_center))
