"""Shared profile-identity artwork for the production Greia child Shell.

This module intentionally owns presentation only. Profile selection, profile
storage, hit targets, Activity lifecycle and theme authority remain in the base
launcher. The shared avatar frame is optional and fail-soft.
"""

from __future__ import annotations

from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError


_SHARED_PROFILE_VISUAL_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)


class SharedUiProfileChromeMixin:
    """Overlay reviewed shared avatar framing on real Shell profile identity.

    The base presentation is drawn first. The shared frame then replaces only
    the visual avatar treatment while retaining the exact profile-card and
    active-profile hit rectangles already owned by the launcher.
    """

    _FRAME_SOURCE_SIZE = 260
    _FRAME_INNER_CENTER_Y = 123 / 260

    def _render_profile_picker_content(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        target_start = len(self._targets)
        super()._render_profile_picker_content(screen, theme, pygame)

        if getattr(self, "_shared_profile_frame_disabled", False):
            return
        if getattr(self, "_visual_cache", None) is None:
            return

        for target in self._targets[target_start:]:
            if target.action != "profile":
                continue
            self._overlay_profile_frame(
                screen,
                target.rect,
                target.value,
                theme,
                pygame,
            )

    def _render_activities_content(self, screen: Any, theme: Any, pygame: Any) -> None:
        super()._render_activities_content(screen, theme, pygame)

        if getattr(self, "_shared_profile_frame_disabled", False):
            return
        if getattr(self, "_visual_cache", None) is None:
            return
        if self._active_profile is None:
            return

        height = screen.get_height()
        badge_size = max(62, min(86, height // 7))
        badge = pygame.Rect(14, 10, badge_size, badge_size)
        self._overlay_active_profile_frame(
            screen,
            badge,
            self._active_profile.profile,
            theme,
            pygame,
        )

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

    def _overlay_profile_frame(
        self,
        screen: Any,
        rect: Any,
        profile: Any,
        theme: Any,
        pygame: Any,
    ) -> None:
        frame_size = max(
            56,
            min(
                int(round(rect.width * 0.82)),
                int(round(rect.height * 0.78)),
            ),
        )
        frame_surface = self._avatar_frame_surface(frame_size, pygame)
        if frame_surface is None:
            return

        frame_rect = pygame.Rect(0, 0, frame_size, frame_size)
        frame_rect.center = (
            rect.centerx,
            int(round(rect.top + rect.height * 0.40)),
        )

        selected_idx = getattr(self, "_profile_selected", None)
        is_selected = False
        if hasattr(self, "profiles") and selected_idx is not None and 0 <= selected_idx < len(self.profiles):
            is_selected = self.profiles[selected_idx].profile_id == profile.profile_id

        pygame.draw.rect(screen, theme.panel, rect, border_radius=26)
        outline_color = theme.accent if is_selected else tuple(
            int(c1 * 0.72 + c2 * 0.28) for c1, c2 in zip(theme.text[:3], theme.panel[:3])
        )
        pygame.draw.rect(
            screen,
            outline_color,
            rect,
            width=8 if is_selected else 3,
            border_radius=26,
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

        font_size = max(23, min(38, rect.height // 6))
        max_name_width = rect.width - 18
        name = self._profile_name_surface(
            profile.display_name, font_size, max_name_width, theme.text, pygame
        )
        screen.blit(name, name.get_rect(center=(rect.centerx, rect.bottom - rect.height * 0.15)))

        if profile.has_secret:
            lock = self._load_icon("yellow_star", max(26, rect.width // 7), pygame)
            screen.blit(lock, lock.get_rect(topright=(rect.right - 8, rect.top + 8)))

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
