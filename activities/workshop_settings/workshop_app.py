"""Lifecycle owner for workshop_settings.

Owns screen/canvas/metrics, domain model, renderer and input
routing. Delegates rules to the pure model and presentation to
the renderer. Publishes READY after the first flip in the same loop.
Keeps the experience parent-only, fast and bounded.
"""

from __future__ import annotations

import time
from pathlib import Path

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    disable_wallpaper,
    get_active_profile,
    get_profile_avatar_choices,
    get_theme,
    get_theme_palette,
    get_ui_preferences,
    import_wallpaper,
    list_wallpaper_candidates,
    mark_activity_ready,
    set_active_profile_avatar,
    set_interface_size,
    set_theme_color,
)
from greia_platform.ui_preferences import InterfaceSize

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_content import (
        MAX_THUMBNAIL_CACHE,
        MAX_THUMBNAIL_PIXELS,
        MODE_ICONS,
        MODES,
        SCAN_INTERVAL_SECONDS,
    )
    from .workshop_model import WorkshopModel
    from .workshop_renderer import HitTarget, WorkshopRenderer
except ImportError:
    from workshop_content import (  # type: ignore[no-redef]
        MAX_THUMBNAIL_CACHE,
        MAX_THUMBNAIL_PIXELS,
        MODE_ICONS,
        MODES,
        SCAN_INTERVAL_SECONDS,
    )
    from workshop_model import WorkshopModel  # type: ignore[no-redef]
    from workshop_renderer import HitTarget, WorkshopRenderer  # type: ignore[no-redef]


class WorkshopApp:
    """Coordinate workshop lifecycle without owning rendering details."""

    SCAN_INTERVAL_SECONDS = SCAN_INTERVAL_SECONDS
    MAX_THUMBNAIL_CACHE = MAX_THUMBNAIL_CACHE
    MAX_THUMBNAIL_PIXELS = MAX_THUMBNAIL_PIXELS
    MODES = MODES
    MODE_ICONS = MODE_ICONS

    def __init__(
        self,
        screen: pygame.Surface,
        model: WorkshopModel | None = None,
        renderer: WorkshopRenderer | None = None,
    ) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        if model is None:
            # Composition fallback: build model from Greia platform.
            model = WorkshopModel(
                profile=get_active_profile(),
                avatar_choices=get_profile_avatar_choices(),
                palette=get_theme_palette(),
                theme=get_theme(),
                ui_preferences=get_ui_preferences(),
            )
        self.model = model
        # Ensure palette/theme are current even if model was injected.
        try:
            self.model.palette = get_theme_palette()
        except Exception:
            pass
        try:
            self.model.theme = get_theme()
        except Exception:
            pass
        try:
            self.model.ui_preferences = get_ui_preferences()
        except Exception:
            pass
        if renderer is None:
            renderer = WorkshopRenderer(screen, tuple(self.model.avatar_choices))
        else:
            renderer.screen = screen
        self.renderer = renderer
        self.targets: list[HitTarget] = []
        self.running = True

    # -- lifecycle ---------------------------------------------------------

    def run(self) -> int:
        ready_published = False
        while self.running and not activity_stop_requested():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL and self.model.mode == "wallpapers":
                    self.change_wallpaper_page(-event.y)
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event)
            self._step_frame()
            self._draw()
            pygame.display.flip()
            if not ready_published:
                # READY means Greia can actually present a usable parent frame,
                # not merely that pygame initialized successfully.
                mark_activity_ready()
                ready_published = True
            self.clock.tick(30)
        pygame.quit()
        return 0

    def _step_frame(self) -> None:
        if self.model.mode == "wallpapers":
            self._rescan_media()

    # -- input routing -----------------------------------------------------

    def handle_key(self, key: int) -> None:
        if key in {pygame.K_ESCAPE, pygame.K_BACKSPACE}:
            self.running = False
        elif key == pygame.K_TAB:
            index = MODES.index(self.model.mode)
            self.model.mode = MODES[(index + 1) % len(MODES)]
        elif self.model.mode == "wallpapers" and key in {pygame.K_LEFT, pygame.K_PAGEUP}:
            self.change_wallpaper_page(-1)
        elif self.model.mode == "wallpapers" and key in {pygame.K_RIGHT, pygame.K_PAGEDOWN}:
            self.change_wallpaper_page(1)
        elif self.model.mode == "size" and key in {pygame.K_LEFT, pygame.K_RIGHT}:
            sizes = tuple(InterfaceSize)
            current = sizes.index(self.model.ui_preferences.interface_size)  # type: ignore[union-attr]
            delta = -1 if key == pygame.K_LEFT else 1
            self._apply_size(sizes[(current + delta) % len(sizes)])

    def handle_click(self, position: tuple[int, int]) -> None:
        for target in reversed(self.targets):
            if not target.rect.collidepoint(position):
                continue
            try:
                if target.action == "mode":
                    self.model.mode = str(target.value)
                elif target.action == "color":
                    kind, swatch_id = target.value  # type: ignore[misc]
                    set_theme_color(str(kind), str(swatch_id))
                    self.model.theme = get_theme()
                    self.model.success()
                elif target.action == "size":
                    self._apply_size(target.value)  # type: ignore[arg-type]
                elif target.action == "avatar":
                    self.model.profile = set_active_profile_avatar(str(target.value))
                    self.model.success()
                elif target.action == "wallpaper":
                    candidate = target.value
                    if candidate is None:
                        disable_wallpaper()
                        self.model.selected_wallpaper_source = None
                    else:
                        import_wallpaper(candidate)  # type: ignore[arg-type]
                        self.model.selected_wallpaper_source = candidate.path  # type: ignore[union-attr]
                    self.model.theme = get_theme()
                    self.model.success()
                elif target.action == "wallpaper_page":
                    self.change_wallpaper_page(int(target.value))
            except (OSError, PermissionError, RuntimeError, ValueError):
                self.model.error()
            return

    def handle_resize(self, event: pygame.event.Event) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.renderer.on_resize(self.screen)

    def change_wallpaper_page(self, delta: int) -> None:
        maximum = self.renderer._maximum_wallpaper_page(tuple(self.model.candidates))  # type: ignore[arg-type]
        self.model.change_wallpaper_page(delta, maximum)

    # -- internal helpers --------------------------------------------------

    def _apply_size(self, size: InterfaceSize) -> None:
        self.model.ui_preferences = set_interface_size(size)
        self.model.success()

    def _rescan_media(self) -> None:
        now = time.monotonic()
        if not self.model.should_rescan(now):
            return
        self.model.note_scanned(now)
        try:
            updated = list_wallpaper_candidates()
        except (OSError, PermissionError, RuntimeError, ValueError):
            updated = ()
        previous_paths = {candidate.path for candidate in self.model.candidates}  # type: ignore[union-attr]
        self.model.candidates = tuple(updated)
        current_paths = {candidate.path for candidate in self.model.candidates}  # type: ignore[union-attr]
        if self.model.selected_wallpaper_source not in current_paths:
            self.model.selected_wallpaper_source = None
        if current_paths != previous_paths:
            maximum = self.renderer._maximum_wallpaper_page(tuple(self.model.candidates))  # type: ignore[arg-type]
            self.model.clamp_wallpaper_page(maximum)
            self.renderer.prune_thumbnails(current_paths)

    def _draw(self) -> None:
        # Keep theme live so external changes are visible without restart.
        try:
            self.model.theme = get_theme()
        except Exception:
            pass
        try:
            self.model.ui_preferences = get_ui_preferences()
        except Exception:
            pass
        self.renderer.draw(self.model, self.targets)

    # Compatibility for tests that instantiate via object.__new__(MyGreiaSettings)
    # and expect _thumbnail / thumbnail_cache without a full renderer.
    def _thumbnail(self, candidate, size):
        # Prefer renderer when available (normal lifecycle).
        if hasattr(self, "renderer") and hasattr(self.renderer, "_thumbnail"):
            try:
                return self.renderer._thumbnail(candidate, size)
            except Exception:
                pass
        # Fallback pure logic for bare-instance tests (removable media gone).
        width, height = max(1, size[0]), max(1, size[1])
        try:
            mtime = candidate.path.stat().st_mtime_ns
        except OSError:
            return None
        key = (candidate.path, mtime, width, height)
        cache = self.__dict__.get("_fallback_thumbnail_cache")
        if cache is None and "thumbnail_cache" not in self.__dict__:
            return None
        fb = self.__dict__.get("_fallback_thumbnail_cache", {})
        if key in fb:
            return fb[key]
        return None

    @property
    def thumbnail_cache(self):
        if hasattr(self, "renderer") and hasattr(self.renderer, "thumbnail_cache"):
            fb = self.__dict__.get("_fallback_thumbnail_cache")
            if fb is not None and fb is not self.renderer.thumbnail_cache:
                self.renderer.thumbnail_cache = fb
            return self.renderer.thumbnail_cache
        return self.__dict__.get("_fallback_thumbnail_cache", {})

    @thumbnail_cache.setter
    def thumbnail_cache(self, value):
        self.__dict__["_fallback_thumbnail_cache"] = value
        if hasattr(self, "renderer") and hasattr(self.renderer, "thumbnail_cache"):
            try:
                self.renderer.thumbnail_cache = value
            except Exception:
                pass


__all__ = ["WorkshopApp"]
