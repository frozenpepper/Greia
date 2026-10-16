"""Shared loading/error/empty-state artwork for the production child Shell.

This layer is presentation-only. Activity lifecycle, error semantics, catalogue
state and hit actions remain owned by the existing launcher. Each optional
shared visual fails independently back to the proven base presentation.
"""

from __future__ import annotations

from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError

from .home_layout import achievement_button_rect


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
        """Draw the shared launch treatment and return whether it was consumed.

        Preferred: the storybook wait screen (scene, the Activity's own card,
        the child's cast friend and a localized status pill). It is composed
        once per launch into one opaque surface; each 0.1 s pre-READY tick
        only re-blits it and moves three small dots, so the transient wait
        never decodes, scales or allocates per frame. Falls back to the
        reviewed loading orbit, then to the primitive overlay.
        """

        screen = pygame.display.get_surface()
        if screen is None:
            return False
        if self._draw_storybook_launch_overlay(screen, pygame, text=text):
            return True

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
            self._child_display_text(text),
            True,
            (61, 44, 31),
        )
        label_rect = label.get_rect(
            center=(center_x, center_y + orbit_size // 2 + max(26, control_size))
        )
        screen.blit(label, label_rect)
        return True

    def _launch_selected(self, pygame: Any) -> None:
        """Run the launch lifecycle, then release the composed wait screen.

        The storybook wait screen is a full-display opaque surface (about
        2.4 MB at 1024x600). It is only useful before READY of the launch that
        composed it, so it is dropped as soon as that lifecycle returns rather
        than being retained behind Home until the next launch.
        """

        try:
            super()._launch_selected(pygame)  # type: ignore[misc]
        finally:
            self._launch_overlay_cache = None

    def _launching_manifest(self) -> Any | None:
        """The Activity being started (the base launch indexes the registry)."""

        activities = getattr(self, "_activities", ())
        index = getattr(self, "_selected", -1)
        if 0 <= index < len(activities):
            return activities[index]
        return None

    def _draw_storybook_launch_overlay(self, screen: Any, pygame: Any, *, text: str) -> bool:
        if getattr(self, "_storybook_launch_disabled", False):
            return False
        if getattr(self, "_visual_cache", None) is None:
            return False
        manifest = self._launching_manifest()
        if manifest is None:
            return False
        size = screen.get_size()
        label = self._child_display_text(text)
        key = (manifest.activity_id, getattr(manifest, "version", ""), size, label,
               getattr(self, "_category_id", None), getattr(self, "_subcollection_id", None))
        cache = getattr(self, "_launch_overlay_cache", None)
        if cache is None or cache[0] != key:
            try:
                composed = self._compose_launch_overlay(size, manifest, label, pygame)
            except (_SHARED_FEEDBACK_ERRORS + (pygame.error, AttributeError)):
                self._storybook_launch_disabled = True
                return False
            cache = (key, composed)
            # Bounded: at most one composed wait screen is retained, and only
            # for the duration of one launch (see ``_launch_selected``).
            self._launch_overlay_cache = cache
        surface, dots_center, dot_radius = cache[1]
        screen.blit(surface, (0, 0))
        self._draw_launch_dots(screen, dots_center, dot_radius, pygame)
        return True

    def _compose_launch_overlay(
        self, size: tuple[int, int], manifest: Any, label: str, pygame: Any
    ) -> tuple[Any, tuple[int, int], int]:
        from greia_platform.responsive_layout import UiRect

        from .collection_hues import collection_hue
        from .collection_page_layout import card_art_height, card_face_rect
        from .home_layout import greeter_rect, layout_scale
        from .presentation import _activity_title
        from .shared_ui_presentation import CAPTION_INK, draw_caption_pill, draw_title_pill

        width, height = size
        scale = layout_scale(width, height)
        surface = pygame.Surface(size).convert()
        theme = self.theme_controller.theme
        surface.fill(theme.background)
        draw_scene = getattr(self, "_draw_shell_scene_backdrop", None)
        if draw_scene is not None:
            draw_scene(surface, pygame, theme=theme)
        veil = pygame.Surface(size, pygame.SRCALPHA)
        veil.fill((255, 251, 235, 96))
        surface.blit(veil, (0, 0))

        card_w = max(96, min(int(round(height * 0.40)), int(round(250 * scale))))
        card = pygame.Rect(0, 0, card_w, card_art_height(card_w))
        card.midtop = (width // 2, max(12, int(round(height * 0.12))))
        hue = collection_hue(
            getattr(self, "_category_id", None),
            group_id=getattr(self, "_subcollection_id", None),
        )
        art = self._visual_cache.get("ui.card.activity_tile", variant=hue, size=card.size)
        surface.blit(art, card)
        face = card_face_rect(UiRect(card.x, card.y, card.width, card.height))
        face_icon = getattr(self, "_card_face_icon", None)
        icon = (
            face_icon(manifest, face.width, pygame)
            if face_icon is not None
            else self._activity_icon(manifest, face.width, pygame)
        )
        surface.blit(icon, icon.get_rect(center=(face.x + face.width // 2, face.y + face.height // 2)))

        font_px = max(16, min(30, int(round(24 * scale))))
        title = self._render_activity_label(
            self._child_display_text(_activity_title(manifest, self._active_locale)),
            max_width=min(width - 40, int(card_w * 1.8)),
            max_height=int(font_px * 2.9),
            pygame=pygame,
            color=CAPTION_INK,
            preferred_size=font_px,
        )
        min_pill = font_px + 14
        slot = pygame.Rect(0, card.bottom + 6, min(width - 24, title.get_width() + 2 * min_pill), title.get_height() + 16)
        slot.centerx = width // 2
        title_pill = draw_title_pill(surface, pygame, slot, title, focused=False, min_height=min_pill)

        status_px = max(15, min(26, int(round(20 * scale))))
        status = self._category_label_surface(label, status_px, CAPTION_INK, pygame)
        pill_h = status_px + 16
        status_slot = pygame.Rect(0, title_pill.bottom + max(8, int(10 * scale)),
                                  status.get_width() + 2 * pill_h, pill_h)
        status_slot.centerx = width // 2
        draw_caption_pill(surface, pygame, status_slot, status, focused=True)

        greeter = getattr(self, "_draw_profile_greeter", None)
        if greeter is not None:
            spot = greeter_rect(width, height, free_right_edge=max(0, min(card.left, title_pill.left) - 8))
            if spot is not None:
                profile = getattr(self, "_active_profile", None)
                avatar = profile.profile.avatar_id if profile is not None else None
                greeter(surface, spot, avatar, "pose_cheer", pygame)

        dot_radius = max(5, int(round(7 * scale)))
        dots_center = (width // 2, min(height - dot_radius - 6, status_slot.bottom + dot_radius * 3))
        return surface, dots_center, dot_radius

    @staticmethod
    def _draw_launch_dots(screen: Any, center: tuple[int, int], radius: int, pygame: Any) -> None:
        """Three sunshine dots taking turns to grow: a calm 'working' cue."""

        import time

        from pygame import gfxdraw

        from .shared_ui_presentation import CAPTION_FOCUS, CAPTION_INK

        now = time.monotonic()
        step = radius * 4
        for index in range(3):
            phase = (now * 1.6 - index * 0.33) % 1.0
            grow = max(0.0, 1.0 - abs(phase - 0.5) * 4.0)
            r = int(round(radius * (0.8 + 0.45 * grow)))
            cx = center[0] + (index - 1) * step
            gfxdraw.aacircle(screen, cx, center[1], r + 2, CAPTION_INK)
            pygame.draw.circle(screen, CAPTION_INK, (cx, center[1]), r + 2)
            pygame.draw.circle(screen, CAPTION_FOCUS, (cx, center[1]), r)

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

        # Below the top-right HUD row (badge star + time-left pill), so the
        # gentle error cloud never covers the time readout.
        hud_row = achievement_button_rect(width, height)
        rect = pygame.Rect(
            width - badge_width - 10,
            hud_row.y + hud_row.height + 6,
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
