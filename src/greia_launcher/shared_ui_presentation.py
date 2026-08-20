"""Shared Greia UI artwork consumption for the production child Shell.

This module is deliberately narrow: it consumes already-generated semantic UI
assets through the launcher-owned bounded visual cache. It does not discover
source artwork, rasterize SVG, or own Activity/lifecycle authority.
"""

from __future__ import annotations

import time
from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_effects import transformed_rect
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError


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

        # The reviewed shared card is intentionally portrait (360:430). Keep
        # that authored ratio instead of stretching it into the launcher's
        # square logical hit target. The surrounding target remains unchanged.
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
        except (
            VisualSurfaceCacheError,
            AssetCatalogueError,
            KeyError,
            FileNotFoundError,
            OSError,
            ValueError,
            pygame.error,
        ):
            # Shared visuals are optional presentation. Disable the optional
            # cache for this process and retain the already-proven primitive
            # tile path instead of turning one bad PNG into a Shell failure.
            self._visual_cache = None
            super()._draw_activity_tile_content(
                screen, rect, activity, state, theme, pygame
            )
            return

        screen.blit(card_surface, card_rect)

        # Map authored source regions into the scaled card. The SVG reserves a
        # large illustration well and a dedicated lower label band.
        content_rect = pygame.Rect(
            card_rect.left + round(card_rect.width * 45 / self._CARD_SOURCE_WIDTH),
            card_rect.top + round(card_rect.height * 43 / self._CARD_SOURCE_HEIGHT),
            max(1, round(card_rect.width * 270 / self._CARD_SOURCE_WIDTH)),
            max(1, round(card_rect.height * 236 / self._CARD_SOURCE_HEIGHT)),
        )
        label_rect = pygame.Rect(
            card_rect.left + round(card_rect.width * 48 / self._CARD_SOURCE_WIDTH),
            card_rect.top + round(card_rect.height * 300 / self._CARD_SOURCE_HEIGHT),
            max(1, round(card_rect.width * 264 / self._CARD_SOURCE_WIDTH)),
            max(1, round(card_rect.height * 57 / self._CARD_SOURCE_HEIGHT)),
        )

        icon_size = max(
            44,
            min(
                int(round(content_rect.width * 0.66)),
                int(round(content_rect.height * 0.68)),
            ),
        )
        icon = self._activity_icon(activity, icon_size, pygame)
        screen.blit(icon, icon.get_rect(center=content_rect.center))

        title = self._render_activity_label(
            self._activity_title_for_shared_card(activity),
            max_width=max(28, label_rect.width - 12),
            max_height=max(22, label_rect.height - 8),
            pygame=pygame,
            color=theme.text,
            preferred_size=max(16, min(24, card_rect.height // 8)),
        )
        screen.blit(title, title.get_rect(center=label_rect.center))

    def _activity_title_for_shared_card(self, activity: Any) -> str:
        # Keep title resolution in one place without duplicating the launcher's
        # localization logic or exposing another semantic source of truth.
        from .presentation import _activity_title

        return _activity_title(activity, self._active_locale)
