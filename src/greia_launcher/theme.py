from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from greia_platform.customization import ResolvedTheme, ThemeStore


class LauncherThemeController:
    """Caches resolved theme state and display-sized wallpaper surfaces."""

    def __init__(self, store: ThemeStore):
        self.store = store
        self._token: tuple[int, int] | None = None
        self._theme: ResolvedTheme = store.resolve()
        self._wallpaper_key: tuple[Path, int, int, int] | None = None
        self._wallpaper_surface: Any | None = None
        self._next_token_check = 0.0

    @property
    def theme(self) -> ResolvedTheme:
        now = time.monotonic()
        if now < self._next_token_check:
            return self._theme
        self._next_token_check = now + 0.25
        token = self.store.version_token()
        if token != self._token:
            self._token = token
            self._theme = self.store.resolve()
            self._wallpaper_key = None
            self._wallpaper_surface = None
        return self._theme

    def invalidate(self) -> None:
        self._next_token_check = 0.0
        self._token = None

    def draw_background(self, screen: Any, pygame: Any) -> ResolvedTheme:
        theme = self.theme
        screen.fill(theme.background)
        if theme.wallpaper_path is None:
            return theme
        surface = self._scaled_wallpaper(theme.wallpaper_path, screen.get_size(), pygame)
        if surface is not None:
            screen.blit(surface, (0, 0))
        return theme

    def _scaled_wallpaper(
        self,
        path: Path,
        size: tuple[int, int],
        pygame: Any,
    ) -> Any | None:
        try:
            mtime = path.stat().st_mtime_ns
        except OSError:
            return None
        key = (path, size[0], size[1], mtime)
        if key == self._wallpaper_key:
            return self._wallpaper_surface
        try:
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
        self._wallpaper_surface = scaled.subsurface((left, top, target_width, target_height)).copy()
        self._wallpaper_key = key
        return self._wallpaper_surface
