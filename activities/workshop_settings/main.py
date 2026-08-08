from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pygame
from PIL import Image, ImageOps, UnidentifiedImageError

from greia_platform.activity_api import (
    disable_wallpaper,
    get_active_profile,
    get_icon_path,
    get_profile_avatar_choices,
    get_theme,
    get_theme_palette,
    import_wallpaper,
    list_wallpaper_candidates,
    set_active_profile_avatar,
    set_theme_color,
)
from greia_platform.customization import ColorSwatch, WallpaperCandidate


@dataclass(frozen=True, slots=True)
class HitTarget:
    action: str
    value: object
    rect: pygame.Rect


class WorkshopSettings:
    SCAN_INTERVAL_SECONDS = 1.5
    MAX_THUMBNAIL_CACHE = 20
    MAX_THUMBNAIL_PIXELS = 12_000_000

    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Workshop Settings")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.palette = get_theme_palette()
        self.theme = get_theme()
        self.mode = "colors"
        self.modes = ("colors", "wallpapers", "avatar")
        self.profile = get_active_profile()
        self.avatar_choices = get_profile_avatar_choices()
        self.running = True
        self.targets: list[HitTarget] = []
        self.candidates: tuple[WallpaperCandidate, ...] = ()
        self.selected_wallpaper: WallpaperCandidate | None = None
        self.selected_solid = False
        self.wallpaper_page = 0
        self.next_scan = 0.0
        self.thumbnail_cache: dict[tuple[Path, int, int, int], pygame.Surface | None] = {}
        self.feedback_until = 0.0
        self.feedback_error = False
        self.icons = {
            name: pygame.image.load(str(get_icon_path(name, 128))).convert_alpha()
            for name in (
                "close_button",
                "palette",
                "notebook",
                "yellow_star",
                "abc_blocks",
                "check",
                "x_mark",
                *self.avatar_choices,
            )
        }

    def run(self) -> int:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    self._handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._handle_click(event.pos)
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.get_surface() or self.screen
                    self.thumbnail_cache.clear()
            if self.mode == "wallpapers":
                self._rescan_media()
            self._draw()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()
        return 0

    def _handle_key(self, key: int) -> None:
        if key in {pygame.K_ESCAPE, pygame.K_BACKSPACE}:
            self.running = False
        elif key == pygame.K_TAB:
            self.mode = self.modes[(self.modes.index(self.mode) + 1) % len(self.modes)]
        elif self.mode == "wallpapers" and key in {pygame.K_LEFT, pygame.K_PAGEUP}:
            self.wallpaper_page = max(0, self.wallpaper_page - 1)
        elif self.mode == "wallpapers" and key in {pygame.K_RIGHT, pygame.K_PAGEDOWN}:
            self.wallpaper_page = min(self._maximum_page(), self.wallpaper_page + 1)
        elif self.mode == "wallpapers" and key in {pygame.K_RETURN, pygame.K_SPACE}:
            self._apply_wallpaper_selection()

    def _handle_click(self, position: tuple[int, int]) -> None:
        for target in reversed(self.targets):
            if not target.rect.collidepoint(position):
                continue
            if target.action == "close":
                self.running = False
            elif target.action == "mode":
                self.mode = str(target.value)
            elif target.action == "color":
                kind, swatch_id = target.value  # type: ignore[misc]
                set_theme_color(kind, swatch_id)
                self.theme = get_theme()
            elif target.action == "avatar":
                updated = set_active_profile_avatar(str(target.value))
                self.profile = updated
                self.feedback_error = False
                self.feedback_until = time.monotonic() + 1.2
            elif target.action == "candidate":
                self.selected_wallpaper = target.value  # type: ignore[assignment]
                self.selected_solid = False
            elif target.action == "solid":
                self.selected_wallpaper = None
                self.selected_solid = True
            elif target.action == "apply":
                self._apply_wallpaper_selection()
            elif target.action == "previous":
                self.wallpaper_page = max(0, self.wallpaper_page - 1)
            elif target.action == "next":
                self.wallpaper_page = min(self._maximum_page(), self.wallpaper_page + 1)
            return

    def _apply_wallpaper_selection(self) -> None:
        try:
            if self.selected_solid:
                disable_wallpaper()
            elif self.selected_wallpaper is not None:
                import_wallpaper(self.selected_wallpaper)
            else:
                return
            self.theme = get_theme()
            self.feedback_error = False
            self.feedback_until = time.monotonic() + 1.2
        except (OSError, PermissionError, ValueError):
            self.feedback_error = True
            self.feedback_until = time.monotonic() + 2.0

    def _rescan_media(self) -> None:
        now = time.monotonic()
        if now < self.next_scan:
            return
        self.next_scan = now + self.SCAN_INTERVAL_SECONDS
        previous_paths = {candidate.path for candidate in self.candidates}
        self.candidates = list_wallpaper_candidates()
        current_paths = {candidate.path for candidate in self.candidates}
        if self.selected_wallpaper and self.selected_wallpaper.path not in current_paths:
            self.selected_wallpaper = None
        if current_paths != previous_paths:
            self.wallpaper_page = min(self.wallpaper_page, self._maximum_page())
            self.thumbnail_cache = {
                key: value for key, value in self.thumbnail_cache.items() if key[0] in current_paths
            }

    def _draw(self) -> None:
        self.theme = get_theme()
        self.screen.fill(self.theme.background)
        self.targets.clear()
        self._draw_top_bar()
        if self.mode == "colors":
            self._draw_color_editor()
        elif self.mode == "wallpapers":
            self._draw_wallpaper_editor()
        else:
            self._draw_avatar_editor()
        self._draw_feedback()
        self._draw_pointer()

    def _draw_top_bar(self) -> None:
        width, height = self.screen.get_size()
        button = max(66, min(92, height // 7))
        close_rect = pygame.Rect(16, 12, button, button)
        self._blit_icon("close_button", close_rect)
        self.targets.append(HitTarget("close", None, close_rect))

        tab_size = button
        gap = 18
        tabs = (("colors", "palette"), ("wallpapers", "notebook"), ("avatar", "unicorn"))
        total_width = len(tabs) * tab_size + (len(tabs) - 1) * gap
        first_x = (width - total_width) // 2
        for index, (mode, icon) in enumerate(tabs):
            rect = pygame.Rect(first_x + index * (tab_size + gap), 12, tab_size, tab_size)
            selected = self.mode == mode
            pygame.draw.rect(self.screen, self.theme.panel, rect, border_radius=20)
            pygame.draw.rect(
                self.screen,
                self.theme.accent if selected else _mix(self.theme.text, self.theme.panel, 0.72),
                rect,
                width=7 if selected else 3,
                border_radius=20,
            )
            self._blit_icon(icon, rect.inflate(-14, -14))
            self.targets.append(HitTarget("mode", mode, rect))

    def _draw_color_editor(self) -> None:
        width, height = self.screen.get_size()
        top = max(112, height // 6)
        available = height - top - 18
        rows = (
            ("background", self.palette.backgrounds, self.theme.preferences.background, "palette"),
            ("accent", self.palette.accents, self.theme.preferences.accent, "yellow_star"),
            ("text", self.palette.texts, self.theme.preferences.text, "abc_blocks"),
        )
        row_height = available // len(rows)
        icon_size = min(78, row_height - 24)
        left = max(92, width // 9)
        right_margin = 22
        swatch_area = width - left - right_margin
        cell_width = swatch_area / max(len(row[1]) for row in rows)

        for row_index, (kind, swatches, selected_id, icon_id) in enumerate(rows):
            y = top + row_index * row_height
            icon_rect = pygame.Rect(12, y + (row_height - icon_size) // 2, icon_size, icon_size)
            self._blit_icon(icon_id, icon_rect)
            for index, swatch in enumerate(swatches):
                size = min(int(cell_width * 0.76), row_height - 30, 78)
                x = int(left + index * cell_width + (cell_width - size) / 2)
                rect = pygame.Rect(x, y + (row_height - size) // 2, size, size)
                self._draw_swatch(rect, swatch, kind, swatch.swatch_id == selected_id)
                self.targets.append(HitTarget("color", (kind, swatch.swatch_id), rect.inflate(10, 10)))

    def _draw_swatch(self, rect: pygame.Rect, swatch: ColorSwatch, kind: str, selected: bool) -> None:
        pygame.draw.rect(self.screen, swatch.color, rect, border_radius=max(12, rect.width // 5))
        outline = self.theme.accent if selected else _mix(self.theme.text, self.theme.panel, 0.55)
        pygame.draw.rect(
            self.screen,
            outline,
            rect,
            width=7 if selected else 2,
            border_radius=max(12, rect.width // 5),
        )
        if kind == "text":
            font = pygame.font.Font(None, max(28, rect.height // 2))
            sample = font.render("Aa", True, swatch.color)
            sample_panel = pygame.Rect(0, 0, int(rect.width * 0.72), int(rect.height * 0.55))
            sample_panel.center = rect.center
            pygame.draw.rect(self.screen, self.theme.panel, sample_panel, border_radius=8)
            self.screen.blit(sample, sample.get_rect(center=sample_panel.center))
        if selected:
            check_size = max(24, rect.width // 3)
            check = pygame.transform.smoothscale(self.icons["check"], (check_size, check_size))
            self.screen.blit(check, check.get_rect(bottomright=rect.bottomright))

    def _draw_avatar_editor(self) -> None:
        width, height = self.screen.get_size()
        top = max(112, height // 6)
        area = pygame.Rect(24, top, width - 48, height - top - 22)
        columns = 4 if width >= 900 else 3
        rows = max(1, (len(self.avatar_choices) + columns - 1) // columns)
        gap = 14
        tile_width = (area.width - gap * (columns - 1)) // columns
        tile_height = min(150, (area.height - gap * (rows - 1)) // rows)
        total_height = rows * tile_height + (rows - 1) * gap
        origin_y = area.top + max(0, (area.height - total_height) // 2)
        selected_avatar = str(self.profile.get("avatar_id", ""))
        for index, avatar_id in enumerate(self.avatar_choices):
            column = index % columns
            row = index // columns
            rect = pygame.Rect(
                area.left + column * (tile_width + gap),
                origin_y + row * (tile_height + gap),
                tile_width,
                tile_height,
            )
            selected = avatar_id == selected_avatar
            pygame.draw.rect(self.screen, self.theme.panel, rect, border_radius=20)
            pygame.draw.rect(
                self.screen,
                self.theme.accent if selected else _mix(self.theme.text, self.theme.panel, 0.65),
                rect,
                width=7 if selected else 3,
                border_radius=20,
            )
            icon_size = min(rect.width - 18, rect.height - 18)
            icon = pygame.transform.smoothscale(self.icons[avatar_id], (icon_size, icon_size))
            self.screen.blit(icon, icon.get_rect(center=rect.center))
            self.targets.append(HitTarget("avatar", avatar_id, rect))

    def _draw_wallpaper_editor(self) -> None:
        width, height = self.screen.get_size()
        top = max(112, height // 6)
        bottom_bar = max(82, height // 7)
        area = pygame.Rect(18, top, width - 36, height - top - bottom_bar - 10)
        columns = 4 if width >= 900 else 3
        rows = 2
        gap = 14
        tile_width = (area.width - gap * (columns - 1)) // columns
        tile_height = (area.height - gap * (rows - 1)) // rows

        items: list[WallpaperCandidate | None] = [None]
        maximum_tiles = columns * rows
        page_capacity = max(1, maximum_tiles - 1)
        start = self.wallpaper_page * page_capacity
        items.extend(self.candidates[start : start + page_capacity])
        items = items[:maximum_tiles]

        for index, candidate in enumerate(items):
            column = index % columns
            row = index // columns
            rect = pygame.Rect(
                area.left + column * (tile_width + gap),
                area.top + row * (tile_height + gap),
                tile_width,
                tile_height,
            )
            selected = self.selected_solid if candidate is None else (
                self.selected_wallpaper is not None and self.selected_wallpaper.path == candidate.path
            )
            self._draw_wallpaper_tile(rect, candidate, selected)
            self.targets.append(HitTarget("solid" if candidate is None else "candidate", candidate, rect))

        if len(items) == 1 and not self.candidates:
            self._draw_insert_media_hint(area)

        navigation_y = height - bottom_bar + 8
        nav_size = min(66, bottom_bar - 14)
        if self.wallpaper_page > 0:
            previous = pygame.Rect(width // 2 - nav_size - 20, navigation_y, nav_size, nav_size)
            self._draw_triangle_button(previous, left=True)
            self.targets.append(HitTarget("previous", None, previous))
        if self.wallpaper_page < self._maximum_page():
            next_rect = pygame.Rect(width // 2 + 20, navigation_y, nav_size, nav_size)
            self._draw_triangle_button(next_rect, left=False)
            self.targets.append(HitTarget("next", None, next_rect))

        if self.selected_solid or self.selected_wallpaper is not None:
            apply_rect = pygame.Rect(width - nav_size - 18, navigation_y, nav_size, nav_size)
            pygame.draw.rect(self.screen, self.theme.panel, apply_rect, border_radius=20)
            pygame.draw.rect(self.screen, self.theme.accent, apply_rect, width=6, border_radius=20)
            self._blit_icon("check", apply_rect.inflate(-8, -8))
            self.targets.append(HitTarget("apply", None, apply_rect))

    def _draw_wallpaper_tile(
        self,
        rect: pygame.Rect,
        candidate: WallpaperCandidate | None,
        selected: bool,
    ) -> None:
        pygame.draw.rect(self.screen, self.theme.panel, rect, border_radius=18)
        inner = rect.inflate(-10, -10)
        if candidate is None:
            pygame.draw.rect(self.screen, self.theme.background, inner, border_radius=14)
            self._blit_icon("x_mark", inner.inflate(-inner.width // 3, -inner.height // 3))
        else:
            thumbnail = self._thumbnail(candidate, inner.size)
            if thumbnail is None:
                pygame.draw.rect(self.screen, _mix(self.theme.text, self.theme.panel, 0.82), inner, border_radius=14)
                self._blit_icon("notebook", inner.inflate(-inner.width // 3, -inner.height // 3))
            else:
                self.screen.blit(thumbnail, inner.topleft)
        border = self.theme.accent if selected else _mix(self.theme.text, self.theme.panel, 0.65)
        pygame.draw.rect(self.screen, border, rect, width=7 if selected else 3, border_radius=18)

    def _thumbnail(self, candidate: WallpaperCandidate, size: tuple[int, int]) -> pygame.Surface | None:
        try:
            mtime = candidate.path.stat().st_mtime_ns
        except OSError:
            return None
        key = (candidate.path, size[0], size[1], mtime)
        if key in self.thumbnail_cache:
            return self.thumbnail_cache[key]
        try:
            Image.MAX_IMAGE_PIXELS = WallpaperImporter.MAX_PIXELS
            with Image.open(candidate.path) as opened:
                if opened.width * opened.height > WallpaperImporter.MAX_PIXELS:
                    raise ValueError("thumbnail source exceeds pixel limit")
                opened.draft("RGB", size)
                image = ImageOps.exif_transpose(opened).convert("RGB")
                scale = max(size[0] / image.width, size[1] / image.height)
                scaled_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
                image = image.resize(scaled_size, Image.Resampling.LANCZOS)
                left = max(0, (image.width - size[0]) // 2)
                top = max(0, (image.height - size[1]) // 2)
                image = image.crop((left, top, left + size[0], top + size[1]))
                surface = pygame.image.fromstring(image.tobytes(), image.size, "RGB").convert()
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            surface = None
        while len(self.thumbnail_cache) >= self.MAX_THUMBNAIL_CACHE:
            self.thumbnail_cache.pop(next(iter(self.thumbnail_cache)))
        self.thumbnail_cache[key] = surface
        return surface

    def _draw_insert_media_hint(self, area: pygame.Rect) -> None:
        center = (area.centerx, area.centery)
        width = min(140, area.width // 5)
        height = max(52, width // 2)
        body = pygame.Rect(0, 0, width, height)
        body.center = center
        pygame.draw.rect(self.screen, self.theme.accent, body, border_radius=14)
        plug = pygame.Rect(body.right - 4, body.centery - height // 5, width // 4, height * 2 // 5)
        pygame.draw.rect(self.screen, self.theme.text, plug, border_radius=5)
        pygame.draw.circle(self.screen, self.theme.panel, (body.left + width // 4, body.centery), max(5, height // 9))

    def _draw_triangle_button(self, rect: pygame.Rect, *, left: bool) -> None:
        pygame.draw.rect(self.screen, self.theme.panel, rect, border_radius=20)
        pygame.draw.rect(self.screen, self.theme.accent, rect, width=5, border_radius=20)
        margin = rect.width // 4
        if left:
            points = ((rect.right - margin, rect.top + margin), (rect.left + margin, rect.centery), (rect.right - margin, rect.bottom - margin))
        else:
            points = ((rect.left + margin, rect.top + margin), (rect.right - margin, rect.centery), (rect.left + margin, rect.bottom - margin))
        pygame.draw.polygon(self.screen, self.theme.text, points)

    def _draw_feedback(self) -> None:
        if time.monotonic() >= self.feedback_until:
            return
        size = max(72, min(112, self.screen.get_height() // 5))
        name = "close_button" if self.feedback_error else "check"
        icon = pygame.transform.smoothscale(self.icons[name], (size, size))
        self.screen.blit(icon, icon.get_rect(center=self.screen.get_rect().center))

    def _draw_pointer(self) -> None:
        if not pygame.mouse.get_focused():
            return
        size = max(34, min(52, self.screen.get_height() // 12))
        cursor = pygame.transform.smoothscale(self.icons["yellow_star"], (size, size))
        self.screen.blit(cursor, cursor.get_rect(center=pygame.mouse.get_pos()))

    def _blit_icon(self, name: str, rect: pygame.Rect) -> None:
        icon = pygame.transform.smoothscale(self.icons[name], rect.size)
        self.screen.blit(icon, rect)

    def _maximum_page(self) -> int:
        if not self.candidates:
            return 0
        columns = 4 if self.screen.get_width() >= 900 else 3
        page_capacity = max(1, columns * 2 - 1)
        return max(0, (len(self.candidates) - 1) // page_capacity)


def _mix(left: tuple[int, int, int], right: tuple[int, int, int], right_weight: float) -> tuple[int, int, int]:
    return tuple(round(a * (1.0 - right_weight) + b * right_weight) for a, b in zip(left, right))  # type: ignore[return-value]


def main() -> int:
    return WorkshopSettings().run()


if __name__ == "__main__":
    raise SystemExit(main())
