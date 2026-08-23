from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from greia_platform.customization import ResolvedTheme, ThemeStore
from greia_platform.ui_preferences import UiPreferences, UiPreferencesStore


class LauncherThemeController:
    """Caches profile visual state and display-sized wallpaper surfaces.

    Color/wallpaper and semantic interface-size preferences are deliberately
    separate stores but share one refresh boundary. The launcher therefore
    responds to My Greia changes without maintaining resolution-specific
    layouts or polling unbounded state every frame.
    """

    def __init__(
        self,
        store: ThemeStore,
        ui_store: UiPreferencesStore | None = None,
    ):
        self.store = store
        self.ui_store = ui_store or UiPreferencesStore(store.state_dir)
        self._token: tuple[int, int, int] | None = None
        self._theme: ResolvedTheme = store.resolve()
        self._ui_preferences: UiPreferences = self.ui_store.read()
        self._wallpaper_key: tuple[Path, int, int, int] | None = None
        self._wallpaper_surface: Any | None = None
        self._next_token_check = 0.0

    @property
    def theme(self) -> ResolvedTheme:
        self._refresh()
        return self._theme

    @property
    def ui_preferences(self) -> UiPreferences:
        self._refresh()
        return self._ui_preferences

    @property
    def interface_scale(self) -> float:
        return self.ui_preferences.scale

    def _refresh(self) -> None:
        now = time.monotonic()
        if now < self._next_token_check:
            return
        self._next_token_check = now + 0.25
        token = (*self.store.version_token(), self.ui_store.version_token())
        if token == self._token:
            return
        previous_ui = self._ui_preferences
        self._token = token
        self._theme = self.store.resolve()
        self._ui_preferences = self.ui_store.read()
        self._wallpaper_key = None
        self._wallpaper_surface = None
        # Font surfaces are owned by the launcher rather than this controller.
        # Consumers key fonts by effective pixel size, so no explicit callback
        # is needed when semantic size changes.
        _ = previous_ui

    def invalidate(self) -> None:
        self._next_token_check = 0.0
        self._token = None

    def draw_background(self, screen: Any, pygame: Any) -> ResolvedTheme:
        theme = self.theme
        screen.fill(theme.background)
        if theme.wallpaper_path is None:
            return theme
        surface = self.wallpaper_for(theme, screen.get_size(), pygame)
        if surface is not None:
            screen.blit(surface, (0, 0))
        return theme

    def wallpaper_for(
        self,
        theme: ResolvedTheme,
        size: tuple[int, int],
        pygame: Any,
    ) -> Any | None:
        """Return the display-sized cached wallpaper for `size`, or None.

        Shared by direct background painting and the launcher's pre-composited
        scene backdrop so both paths observe one decoded/scaled surface.
        Presentation stubs may omit ``wallpaper_path`` entirely.
        """

        wallpaper_path = getattr(theme, "wallpaper_path", None)
        if wallpaper_path is None:
            return None
        return self._scaled_wallpaper(wallpaper_path, size, pygame)

    def _scaled_wallpaper(
        self,
        path: Path,
        size: tuple[int, int],
        pygame: Any,
    ) -> Any | None:
        key = (path, size[0], size[1])
        if key == self._wallpaper_key:
            return self._wallpaper_surface
        try:
            if not path.is_file():
                return None
            source = pygame.image.load(str(path)).convert()
        except (OSError, pygame.error):
            self._wallpaper_key = key
            self._wallpaper_surface = None
            return None
        target_width, target_height = size
        scale = max(target_width / source.get_width(), target_height / source.get_height())
        scaled_size = (
            max(1, round(source.get_width() * scale)),
            max(1, round(source.get_height() * scale)),
        )
        scaled = pygame.transform.smoothscale(source, scaled_size)
        left = max(0, (scaled.get_width() - target_width) // 2)
        top = max(0, (scaled.get_height() - target_height) // 2)
        self._wallpaper_surface = scaled.subsurface(
            (left, top, target_width, target_height)
        ).copy()
        self._wallpaper_key = key
        return self._wallpaper_surface
