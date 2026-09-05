"""Shared profile-identity artwork for the production Greia child Shell.

This module intentionally owns presentation only. Profile selection, profile
storage, hit targets, Activity lifecycle and theme authority remain in the base
launcher. The shared avatar frame is optional and fail-soft.
"""

from __future__ import annotations

from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError

from .presentation import _mix
from .system_chrome import resolve_trusted_action_minimum_px


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
            return

        frame_rect = pygame.Rect(0, 0, frame_size, frame_size)
        pointer = pygame.mouse.get_pos()
        pointer_active = pygame.mouse.get_focused()
        hovered = pointer_active and rect.collidepoint(pointer)

        selected_idx = getattr(self, "_profile_selected", None)
        is_selected = False
        if hasattr(self, "profiles") and selected_idx is not None and 0 <= selected_idx < len(self.profiles):
            is_selected = self.profiles[selected_idx].profile_id == profile.profile_id

        is_highlighted = is_selected or hovered
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
        outline_width = 6 if is_selected else (3 if hovered else 2)
        pygame.draw.rect(
            screen,
            outline_color,
            drawn,
            width=outline_width,
            border_radius=26,
        )

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
