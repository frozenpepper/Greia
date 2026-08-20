"""Shared loading/error/empty-state artwork for the production child Shell.

This layer is presentation-only. Activity lifecycle, error semantics, catalogue
state and hit actions remain owned by the existing launcher. Each optional
shared visual fails independently back to the proven base presentation.
"""

from __future__ import annotations

from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError


_SHARED_FEEDBACK_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)


class SharedUiFeedbackMixin:
    """Consume reviewed shared feedback visuals without taking semantic authority."""

    def _feedback_surface(
        self,
        asset_id: str,
        size: tuple[int, int],
        pygame: Any,
        *,
        disable_flag: str,
    ) -> Any | None:
        if getattr(self, disable_flag, False):
            return None
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return None
        try:
            return visual_cache.get(asset_id, variant="default", size=size)
        except _SHARED_FEEDBACK_ERRORS:
            setattr(self, disable_flag, True)
            return None
        except pygame.error:
            setattr(self, disable_flag, True)
            return None

    def _draw_shared_launch_overlay(self, pygame: Any, *, text: str) -> bool:
        """Draw the shared launch treatment and return whether it was consumed."""

        screen = pygame.display.get_surface()
        if screen is None:
            return False

        width, height = screen.get_size()
        orbit_size = max(112, min(180, height // 3))
        orbit = self._feedback_surface(
            "ui.loading.orbit",
            (orbit_size, orbit_size),
            pygame,
            disable_flag="_shared_loading_disabled",
        )
        if orbit is None:
            return False

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((255, 250, 240, 238))
        screen.blit(overlay, (0, 0))

        center_x = width // 2
        center_y = height // 2 - max(12, orbit_size // 8)
        screen.blit(orbit, orbit.get_rect(center=(center_x, center_y)))

        from greia_platform.typography import FontRole

        scale = self.theme_controller.interface_scale
        control_size = max(22, min(54, int(round(30 * scale))))
        label = self._typography.font(FontRole.CONTROL, control_size).render(
            text,
            True,
            (61, 44, 31),
        )
        label_rect = label.get_rect(
            center=(center_x, center_y + orbit_size // 2 + max(26, control_size))
        )
        screen.blit(label, label_rect)
        return True

    def _draw_error_badge(self, screen: Any, pygame: Any) -> None:
        width, height = screen.get_size()
        badge_width = max(84, min(116, width // 9))
        badge_height = max(1, round(badge_width * 260 / 360))
        cloud = self._feedback_surface(
            "ui.error.gentle",
            (badge_width, badge_height),
            pygame,
            disable_flag="_shared_error_disabled",
        )
        if cloud is None:
            super()._draw_error_badge(screen, pygame)
            return

        from .main import HitTarget

        rect = pygame.Rect(
            width - badge_width - 10,
            max(8, min(18, height // 40)),
            badge_width,
            badge_height,
        )
        screen.blit(cloud, rect)
        self._targets.append(HitTarget("error_badge_dismiss", None, rect))

    def _draw_empty(self, screen: Any, pygame: Any) -> None:
        # The basket is a semantic "nothing here yet" state for the Activity
        # catalogue. The profile picker retains its existing Greia identity
        # fallback because "no profiles" is a different platform condition.
        if getattr(self, "_mode", None) != "activities":
            super()._draw_empty(screen, pygame)
            return

        width, height = screen.get_size()
        basket_width = max(150, min(280, width // 3, int(height * 0.46)))
        basket_height = max(1, round(basket_width * 300 / 360))
        basket = self._feedback_surface(
            "ui.empty.basket",
            (basket_width, basket_height),
            pygame,
            disable_flag="_shared_empty_disabled",
        )
        if basket is None:
            super()._draw_empty(screen, pygame)
            return

        rect = basket.get_rect(center=(width // 2, height // 2 + height // 18))
        screen.blit(basket, rect)
