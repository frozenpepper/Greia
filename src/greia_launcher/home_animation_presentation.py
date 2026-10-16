"""Interactive Home: wires :class:`HomeAnimator` into the child Shell.

Presentation only. The Collection Home layout, portals, hit targets, profile
and lifecycle authority stay where they are; this mixin

* takes the cast greeter out of the cached Home frame and lets the animator
  draw it (plus the meadow scenery effects) as an overlay after the cache
  blit, exactly like the achievement star;
* asks the animator for small dirty-rect frames from the Shell loop's
  ``_present_ambient_frame`` hook, restoring each rect from the cached Home
  frame (never rebuilding it per frame);
* routes taps on the greeter/tree/sun/clouds to the animator only after every
  real target missed (portals, profile badge and star always win);
* makes the greeter one more stop in the Home keyboard/controller focus cycle
  (Tab after the last portal, Left from a first-column portal; Enter/south
  button reacts).

Fail-soft: if any animator artwork is missing the greeter falls back to the
static baked pose and Home behaves exactly as before.
"""

from __future__ import annotations

import time
from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError
from greia_platform.responsive_layout import UiRect

from .catalogue_view import ALL_ACTIVITIES_ID
from .home_animator import HomeAnimator, HomeGreeterVoice, clip_rects
from .home_layout import achievement_button_rect, usage_pill_band
from .home_scenery import HomeSceneryLayout
from .profile_chrome_presentation import greeter_character_for


_ANIMATOR_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)

# Software pointer footprint (greia_platform.activity_ui.draw_activity_pointer).
_POINTER_RADIUS = 12


class HomeAnimationMixin:
    """Own the Home greeter/scenery overlay and its dirty-rect frames.

    Extension seam for other Shell presentation: :meth:`_home_react` makes the
    greeter react (``"surprised"``, ``"happy"``, ``"cheer"``, ``"wave"``) —
    for example from the achievement ceremony — without speech or grants.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Set before the base constructor: bootstrap may already render.
        self._home_animator: HomeAnimator | None = None
        self._home_animator_disabled = False
        self._home_rendering = False
        self._home_greeter_placed = False
        self._home_overlay_live = False
        self._home_greeter_focused = False
        self._home_greeter_return_index = 0
        super().__init__(*args, **kwargs)

    # ------------------------------------------------------------- helpers
    def _home_showing(self) -> bool:
        return (
            getattr(self, "_mode", None) == "activities"
            and getattr(self, "_category_id", None) == ALL_ACTIVITIES_ID
            and getattr(self, "_active_profile", None) is not None
        )

    def _home_interactive(self) -> bool:
        return (
            self._home_showing()
            and getattr(self, "_achievement_celebration", None) is None
            and getattr(self, "_launching_activity_id", None) is None
        )

    def _ensure_home_animator(self, pygame: Any) -> HomeAnimator | None:
        if self._home_animator_disabled:
            return None
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return None
        if self._home_animator is None:
            def load(asset_id: str, variant: str, size: tuple[int, int]) -> Any:
                return visual_cache.get(asset_id, variant=variant, size=size)

            voice = None
            labels = getattr(self, "_spoken_labels", None)
            if labels is not None:
                voice = HomeGreeterVoice(labels.root, labels.player, self._spoken_locale)
            self._home_animator = HomeAnimator(load, voice=voice)
        return self._home_animator

    def _disable_home_animator(self) -> None:
        self._home_animator_disabled = True
        if self._home_animator is not None:
            self._home_animator.reset()
        self._home_greeter_focused = False
        self._cached_activities_key = None

    def _home_react(self, kind: str) -> bool:
        """Public Shell seam: make the Home greeter react (no speech/grants)."""

        animator = self._home_animator
        if animator is None or self._home_animator_disabled:
            return False
        return animator.react(kind, time.monotonic())

    # ------------------------------------------------------------ rendering
    def _render_collection_home(self, screen: Any, theme: Any, pygame: Any) -> None:
        animator = self._ensure_home_animator(pygame)
        self._home_rendering = animator is not None
        self._home_greeter_placed = False
        try:
            super()._render_collection_home(screen, theme, pygame)
        finally:
            self._home_rendering = False
        if animator is None or self._home_animator_disabled:
            return
        if not self._home_greeter_placed:
            animator.clear_greeter()
            self._home_greeter_focused = False
        try:
            animator.layout_scenery(self._home_scenery_layout(screen, theme, animator))
        except _ANIMATOR_ERRORS:
            animator.layout_scenery(None)
        except pygame.error:
            animator.layout_scenery(None)

    def _home_scenery_layout(
        self, screen: Any, theme: Any, animator: HomeAnimator
    ) -> HomeSceneryLayout | None:
        if getattr(theme, "wallpaper_path", None) is not None:
            return None  # a child wallpaper replaces the meadow
        if getattr(self, "_shared_scene_disabled", False):
            return None
        width, height = screen.get_size()
        star = achievement_button_rect(width, height)
        badge = self._home_profile_badge_size(height)
        blocked = [UiRect(t.rect.x, t.rect.y, t.rect.width, t.rect.height) for t in self._targets]
        blocked.extend(self._home_reserved_rects(width, height))
        blocked.append(usage_pill_band(width, height, left_limit=14 + badge))
        blocked.append(UiRect(0, 0, width, star.y + star.height + 10))
        greeter = animator.greeter_rect
        if greeter is not None:
            hop = max(8, greeter.height // 6)
            blocked.append(UiRect(greeter.x, greeter.y - hop, greeter.width, greeter.height + hop))
        return HomeSceneryLayout.compute((width, height), blocked)

    def _draw_profile_greeter(
        self, screen: Any, rect: UiRect, avatar_id: str | None, pose: str, pygame: Any
    ) -> bool:
        """On Home, hand the greeter to the animator instead of baking it."""

        if self._home_rendering:
            animator = self._home_animator
            if animator is not None:
                try:
                    animator.place_greeter(
                        rect, greeter_character_for(avatar_id), time.monotonic()
                    )
                    self._home_greeter_placed = True
                    return True
                except _ANIMATOR_ERRORS:
                    self._disable_home_animator()
                except pygame.error:
                    self._disable_home_animator()
        return super()._draw_profile_greeter(screen, rect, avatar_id, pose, pygame)

    def _draw_shell_scene_backdrop(
        self, screen: Any, pygame: Any, *, theme: Any = None, sky_clouds: bool = True
    ) -> None:
        # Home draws its own (drifting) clouds over a clear sky.
        if self._home_rendering:
            sky_clouds = False
        super()._draw_shell_scene_backdrop(
            screen, pygame, theme=theme, sky_clouds=sky_clouds
        )

    def _draw(self, screen: Any, pygame: Any) -> None:
        self._home_overlay_live = False
        super()._draw(screen, pygame)

    def _draw_activities(self, screen: Any, theme: Any, pygame: Any) -> None:
        super()._draw_activities(screen, theme, pygame)
        animator = self._home_animator
        if animator is None or self._home_animator_disabled or not self._home_showing():
            return
        now = time.monotonic()
        animator.set_focused(self._home_greeter_focused)
        animator.update(now, self._last_input_monotonic)
        animator.draw(screen)
        animator.mark_frame(now)
        self._home_overlay_live = True

    # ---------------------------------------------------- ambient frame loop
    def _ambient_wait_seconds(self, now: float) -> float | None:
        animator = self._home_animator
        if animator is None or not self._home_overlay_live:
            return super()._ambient_wait_seconds(now)
        return animator.seconds_until_due(now)

    def _present_ambient_frame(self, screen: Any, pygame: Any, now: float) -> bool:
        animator = self._home_animator
        if (
            animator is None
            or self._home_animator_disabled
            or not self._home_overlay_live
            or not self._home_showing()
        ):
            return super()._present_ambient_frame(screen, pygame, now)
        wait = animator.seconds_until_due(now)
        if wait is None or wait > 0:
            return False
        celebrating = getattr(self, "_achievement_celebration", None) is not None
        if getattr(self, "_launching_activity_id", None) is not None:
            return False
        # While the achievement ceremony owns the screen only the greeter
        # moves (it reacts to the badge); clouds hold still.
        animator.update(now, self._last_input_monotonic, drift=not celebrating)
        rects = clip_rects(animator.dirty_rects(pygame), screen.get_rect())
        animator.mark_frame(now)
        if not rects:
            return False
        restore = getattr(self, "_cached_activities_surface", None)
        if restore is None or restore.get_size() != screen.get_size():
            return False
        if celebrating and any(
            rect.colliderect(self._home_celebration_zone(screen, pygame)) for rect in rects
        ):
            # Never repaint under the ceremony card; the pending change is
            # presented once the card is gone (presented state is unchanged).
            return False
        animator.draw_dirty(screen, rects, restore)
        if self._is_pointer_active(pygame):
            px, py = self._pointer_pos(pygame)
            box = pygame.Rect(
                px - _POINTER_RADIUS, py - _POINTER_RADIUS,
                2 * _POINTER_RADIUS + 1, 2 * _POINTER_RADIUS + 1,
            )
            if box.collidelist(rects) != -1:
                self._draw_pointer(screen, pygame)
                rects.append(box.clip(screen.get_rect()))
        pygame.display.update(rects)
        return True

    @staticmethod
    def _home_celebration_zone(screen: Any, pygame: Any) -> Any:
        """Conservative screen area the achievement ceremony may paint.

        The card is centred and the badge flies to the top-right star; the
        greeter's bottom-left corner stays outside this zone on landscape
        screens of 1024 px and wider.
        """

        width, height = screen.get_size()
        left = width // 5
        return pygame.Rect(left, 0, width - left, height)

    # ---------------------------------------------------------------- input
    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        if self._home_interactive():
            if any(target.rect.collidepoint(position) for target in self._targets):
                self._leave_greeter_focus()
            else:
                animator = self._home_animator
                hit = animator.hit(position) if animator is not None else None
                if hit is not None:
                    animator.tap(hit, time.monotonic(), pygame)
                    return
        super()._handle_click(position, pygame)

    def _enter_greeter_focus(self) -> None:
        self._home_greeter_return_index = max(0, self._home_collection_selected)
        self._home_greeter_focused = True
        # No portal wears the focus ring while the greeter has focus.
        self._home_collection_selected = -1
        self._cached_activities_key = None

    def _leave_greeter_focus(self, index: int | None = None) -> None:
        if not self._home_greeter_focused:
            return
        self._home_greeter_focused = False
        self._home_collection_selected = (
            self._home_greeter_return_index if index is None else index
        )
        self._cached_activities_key = None

    def _handle_key(self, key: int, pygame: Any) -> bool:
        animator = self._home_animator
        if (
            not self._home_interactive()
            or animator is None
            or animator.greeter_rect is None
        ):
            self._home_greeter_focused = False
            return super()._handle_key(key, pygame)
        collections = self._home_collections()
        if self._home_greeter_focused:
            if key in {pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER}:
                animator.tap("greeter", time.monotonic(), pygame)
                return True
            if key in {pygame.K_TAB, pygame.K_RIGHT}:
                # Tab wraps to the first portal; Right steps to the portal
                # beside the greeter (first column of the bottom row).
                columns = max(1, self._home_columns(pygame))
                beside = ((len(collections) - 1) // columns) * columns if collections else 0
                self._leave_greeter_focus(0 if key == pygame.K_TAB else beside)
                self._announce_selected_home_collection(pygame)
                return True
            if key == pygame.K_UP:
                self._leave_greeter_focus()
                self._announce_selected_home_collection(pygame)
                return True
            if key in {pygame.K_LEFT, pygame.K_DOWN}:
                return True
            self._leave_greeter_focus()
            return super()._handle_key(key, pygame)
        if collections:
            selected = min(max(0, self._home_collection_selected), len(collections) - 1)
            columns = max(1, self._home_columns(pygame))
            if (key == pygame.K_TAB and selected == len(collections) - 1) or (
                key == pygame.K_LEFT and selected % columns == 0
            ):
                self._enter_greeter_focus()
                return True
        return super()._handle_key(key, pygame)

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        self._home_greeter_focused = False
        super()._activate_profile(profile, pygame)

    def _logout(self, pygame: Any) -> None:
        self._home_greeter_focused = False
        super()._logout(pygame)
