from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pygame
from PIL import Image, ImageOps, UnidentifiedImageError

from greia_platform.activity_api import (
    activity_stop_requested,
    disable_wallpaper,
    get_active_profile,
    get_icon_path,
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
from greia_platform.activity_ui import (
    draw_activity_pointer,
    draw_system_chrome_overlay,
    is_home_clicked,
)
from greia_platform.activity_viewport import ActivityViewport
from greia_platform.customization import ColorSwatch, WallpaperCandidate
from greia_platform.responsive_layout import AdaptiveGridPolicy, UiRect, Viewport
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.ui_preferences import InterfaceSize


@dataclass(frozen=True, slots=True)
class HitTarget:
    action: str
    value: object
    rect: pygame.Rect


def settings_safe_ui_rect(width: int, height: int) -> UiRect:
    """Return the child-settings region outside Greia-owned Home/Back chrome."""

    chrome = ActivitySystemChromeLayout.for_surface(width, height)
    protected = chrome.protected_region
    viewport = ActivityViewport.for_size(
        width,
        height,
        protected_regions=(
            UiRect(protected.x, protected.y, protected.width, protected.height),
        ),
    )
    return viewport.safe_ui_rect()


class MyGreiaSettings:
    """Child-facing visual customization Activity.

    This is deliberately not a general system-settings panel. It teaches the
    settings concept through immediate, reversible, profile-scoped visual
    choices while Parent/system authority stays elsewhere.
    """

    SCAN_INTERVAL_SECONDS = 1.5
    MAX_THUMBNAIL_CACHE = 20
    MAX_THUMBNAIL_PIXELS = 12_000_000
    MODES = ("colors", "wallpapers", "size", "avatar")
    MODE_ICONS = {
        "colors": "palette",
        "wallpapers": "notebook",
        "size": "abc_blocks",
        "avatar": "unicorn",
    }

    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("My Greia")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.palette = get_theme_palette()
        self.theme = get_theme()
        self.ui_preferences = get_ui_preferences()
        self.profile = get_active_profile()
        self.avatar_choices = get_profile_avatar_choices()
        self.mode = "colors"
        self.running = True
        self.targets: list[HitTarget] = []
        self.candidates: tuple[WallpaperCandidate, ...] = ()
        self.selected_wallpaper_source: Path | None = None
        self.wallpaper_page = 0
        self.next_scan = 0.0
        self.thumbnail_cache: dict[tuple[Path, int, int, int], pygame.Surface | None] = {}
        self.feedback_until = 0.0
        self.feedback_error = False
        icon_ids = {
            *self.MODE_ICONS.values(),
            "yellow_star",
            "check",
            "x_mark",
            *self.avatar_choices,
        }
        self.icons = {
            icon_id: pygame.image.load(str(get_icon_path(icon_id, 128))).convert_alpha()
            for icon_id in icon_ids
        }

    def run(self) -> int:
        ready_published = False
        while self.running and not activity_stop_requested():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._handle_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL and self.mode == "wallpapers":
                    self._change_wallpaper_page(-event.y)
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.get_surface() or self.screen
                    self.thumbnail_cache.clear()
            if self.mode == "wallpapers":
                self._rescan_media()
            self._draw()
            pygame.display.flip()
            if not ready_published:
                # READY means Greia can actually present a usable child frame,
                # not merely that pygame initialized successfully.
                mark_activity_ready()
                ready_published = True
            self.clock.tick(30)
        pygame.quit()
        return 0

    def _handle_key(self, key: int) -> None:
        if key in {pygame.K_ESCAPE, pygame.K_BACKSPACE}:
            self.running = False
        elif key == pygame.K_TAB:
            index = self.MODES.index(self.mode)
            self.mode = self.MODES[(index + 1) % len(self.MODES)]
        elif self.mode == "wallpapers" and key in {pygame.K_LEFT, pygame.K_PAGEUP}:
            self._change_wallpaper_page(-1)
        elif self.mode == "wallpapers" and key in {pygame.K_RIGHT, pygame.K_PAGEDOWN}:
            self._change_wallpaper_page(1)
        elif self.mode == "size" and key in {pygame.K_LEFT, pygame.K_RIGHT}:
            sizes = tuple(InterfaceSize)
            current = sizes.index(self.ui_preferences.interface_size)
            delta = -1 if key == pygame.K_LEFT else 1
            self._apply_size(sizes[(current + delta) % len(sizes)])

    def _handle_click(self, position: tuple[int, int]) -> None:
        if is_home_clicked(self.screen, position):
            self.running = False
            return
        for target in reversed(self.targets):
            if not target.rect.collidepoint(position):
                continue
            try:
                if target.action == "mode":
                    self.mode = str(target.value)
                elif target.action == "color":
                    kind, swatch_id = target.value  # type: ignore[misc]
                    set_theme_color(str(kind), str(swatch_id))
                    self.theme = get_theme()
                    self._success()
                elif target.action == "size":
                    self._apply_size(target.value)  # type: ignore[arg-type]
                elif target.action == "avatar":
                    self.profile = set_active_profile_avatar(str(target.value))
                    self._success()
                elif target.action == "wallpaper":
                    candidate = target.value
                    if candidate is None:
                        disable_wallpaper()
                        self.selected_wallpaper_source = None
                    else:
                        import_wallpaper(candidate)  # type: ignore[arg-type]
                        self.selected_wallpaper_source = candidate.path  # type: ignore[union-attr]
                    self.theme = get_theme()
                    self._success()
                elif target.action == "wallpaper_page":
                    self._change_wallpaper_page(int(target.value))
            except (OSError, PermissionError, RuntimeError, ValueError):
                self._error()
            return

    def _apply_size(self, size: InterfaceSize) -> None:
        self.ui_preferences = set_interface_size(size)
        self._success()

    def _success(self) -> None:
        self.feedback_error = False
        self.feedback_until = time.monotonic() + 0.8

    def _error(self) -> None:
        self.feedback_error = True
        self.feedback_until = time.monotonic() + 1.8

    def _change_wallpaper_page(self, delta: int) -> None:
        maximum = self._maximum_wallpaper_page()
        self.wallpaper_page = min(maximum, max(0, self.wallpaper_page + delta))

    def _rescan_media(self) -> None:
        now = time.monotonic()
        if now < self.next_scan:
            return
        self.next_scan = now + self.SCAN_INTERVAL_SECONDS
        try:
            updated = list_wallpaper_candidates()
        except (OSError, PermissionError, RuntimeError, ValueError):
            updated = ()
        previous_paths = {candidate.path for candidate in self.candidates}
        self.candidates = tuple(updated)
        current_paths = {candidate.path for candidate in self.candidates}
        if self.selected_wallpaper_source not in current_paths:
            self.selected_wallpaper_source = None
        if current_paths != previous_paths:
            self.wallpaper_page = min(self.wallpaper_page, self._maximum_wallpaper_page())
            self.thumbnail_cache = {
                key: value
                for key, value in self.thumbnail_cache.items()
                if key[0] in current_paths
            }

    def _viewport(self) -> Viewport:
        return Viewport(*self.screen.get_size())

    def _safe_ui_rect(self) -> UiRect:
        return settings_safe_ui_rect(*self.screen.get_size())

    def _margin(self) -> int:
        safe = self._safe_ui_rect()
        return Viewport(safe.width, safe.height).bounded_px(
            18, minimum=10, maximum=28
        )

    def _top_bar_height(self) -> int:
        safe = self._safe_ui_rect()
        return Viewport(safe.width, safe.height).bounded_px(
            82, minimum=60, maximum=96
        )

    def _content_rect(self, *, footer: int = 0) -> pygame.Rect:
        safe = self._safe_ui_rect()
        margin = self._margin()
        top = safe.y + margin + self._top_bar_height() + margin
        return pygame.Rect(
            safe.x + margin,
            top,
            max(1, safe.width - margin * 2),
            max(1, safe.bottom - top - margin - footer),
        )

    def _draw(self) -> None:
        self.theme = get_theme()
        self.ui_preferences = get_ui_preferences()
        # Background is decorative and may fill the complete Activity surface;
        # all interactive settings geometry below is constrained to safe UI.
        self.screen.fill(self.theme.background)
        self.targets.clear()
        self._draw_mode_bar()
        if self.mode == "colors":
            self._draw_colors()
        elif self.mode == "wallpapers":
            self._draw_wallpapers()
        elif self.mode == "size":
            self._draw_sizes()
        else:
            self._draw_avatars()
        self._draw_feedback()
        draw_system_chrome_overlay(self.screen)
        self._draw_pointer()

    def _draw_mode_bar(self) -> None:
        safe = self._safe_ui_rect()
        margin = self._margin()
        bar_height = self._top_bar_height()
        button = min(bar_height, max(46, (safe.width - margin * 2) // 7))
        gap = max(
            8,
            min(
                18,
                (safe.width - button * len(self.MODES)) // (len(self.MODES) + 1),
            ),
        )
        total = button * len(self.MODES) + gap * (len(self.MODES) - 1)
        x = safe.x + max(margin, (safe.width - total) // 2)
        y = safe.y + margin
        pointer = pygame.mouse.get_pos()
        for mode in self.MODES:
            rect = pygame.Rect(x, y, button, button)
            selected = mode == self.mode
            hovered = pygame.mouse.get_focused() and rect.collidepoint(pointer)
            pygame.draw.rect(
                self.screen,
                self.theme.panel,
                rect,
                border_radius=max(14, button // 4),
            )
            pygame.draw.rect(
                self.screen,
                self.theme.accent
                if selected or hovered
                else _mix(self.theme.text, self.theme.panel, 0.72),
                rect,
                width=6 if selected else 3,
                border_radius=max(14, button // 4),
            )
            self._blit_icon(self.MODE_ICONS[mode], rect.inflate(-12, -12))
            self.targets.append(HitTarget("mode", mode, rect))
            x += button + gap

    def _draw_colors(self) -> None:
        area = self._content_rect()
        rows = (
            (
                "background",
                self.palette.backgrounds,
                self.theme.preferences.background,
                "palette",
            ),
            (
                "accent",
                self.palette.accents,
                self.theme.preferences.accent,
                "yellow_star",
            ),
            ("text", self.palette.texts, self.theme.preferences.text, "abc_blocks"),
        )
        row_height = max(1, area.height // len(rows))
        label_reserve = min(86, max(54, area.width // 10))
        for row_index, (kind, swatches, selected_id, icon_id) in enumerate(rows):
            row = pygame.Rect(
                area.left,
                area.top + row_index * row_height,
                area.width,
                row_height,
            )
            icon_size = min(64, max(36, row.height - 24), label_reserve - 12)
            self._blit_icon(
                icon_id,
                pygame.Rect(
                    row.left + (label_reserve - icon_size) // 2,
                    row.centery - icon_size // 2,
                    icon_size,
                    icon_size,
                ),
            )
            usable = max(1, row.width - label_reserve)
            gap = max(4, min(12, usable // max(1, len(swatches) * 8)))
            cell = max(1, usable // max(1, len(swatches)))
            size = min(72, row.height - 24, max(24, cell - gap * 2))
            for index, swatch in enumerate(swatches):
                rect = pygame.Rect(
                    row.left + label_reserve + index * cell + (cell - size) // 2,
                    row.centery - size // 2,
                    size,
                    size,
                )
                self._draw_swatch(
                    rect, swatch, kind, swatch.swatch_id == selected_id
                )
                self.targets.append(
                    HitTarget("color", (kind, swatch.swatch_id), rect.inflate(6, 6))
                )

    def _draw_swatch(
        self,
        rect: pygame.Rect,
        swatch: ColorSwatch,
        kind: str,
        selected: bool,
    ) -> None:
        pygame.draw.rect(
            self.screen,
            swatch.color,
            rect,
            border_radius=max(10, rect.width // 4),
        )
        pygame.draw.rect(
            self.screen,
            self.theme.accent
            if selected
            else _mix(self.theme.text, self.theme.panel, 0.6),
            rect,
            width=6 if selected else 2,
            border_radius=max(10, rect.width // 4),
        )
        if kind == "text":
            panel = rect.inflate(
                -max(8, rect.width // 4), -max(8, rect.height // 3)
            )
            pygame.draw.rect(
                self.screen,
                self.theme.panel,
                panel,
                border_radius=max(5, panel.height // 4),
            )
            pygame.draw.line(
                self.screen,
                swatch.color,
                (panel.left + 5, panel.centery),
                (panel.right - 5, panel.centery),
                width=max(3, panel.height // 4),
            )
        if selected:
            self._selection_check(rect)

    def _grid_layout(
        self,
        area: pygame.Rect,
        item_count: int,
        *,
        rows: int = 3,
        columns: int = 6,
    ):
        policy = AdaptiveGridPolicy(
            minimum_item_px=72,
            preferred_item_px=132,
            maximum_item_px=170,
            minimum_gap_px=8,
            maximum_gap_px=18,
            maximum_columns=columns,
            maximum_rows=rows,
        )
        return policy.layout(
            UiRect(area.x, area.y, area.width, area.height), item_count
        )

    def _draw_sizes(self) -> None:
        area = self._content_rect()
        layout = self._grid_layout(
            area, len(tuple(InterfaceSize)), rows=1, columns=3
        )
        samples = {
            InterfaceSize.COMPACT: 0.50,
            InterfaceSize.NORMAL: 0.66,
            InterfaceSize.LARGE: 0.82,
        }
        for index, size in enumerate(InterfaceSize):
            if index >= layout.capacity:
                break
            cell = layout.cell(index)
            rect = pygame.Rect(cell.x, cell.y, cell.width, cell.height)
            selected = size == self.ui_preferences.interface_size
            self._draw_choice_panel(rect, selected)
            sample_size = max(32, min(rect.width, rect.height) * samples[size])
            icon_size = int(sample_size)
            icon_rect = pygame.Rect(0, 0, icon_size, icon_size)
            icon_rect.center = rect.center
            self._blit_icon("abc_blocks", icon_rect)
            if selected:
                self._selection_check(rect)
            self.targets.append(HitTarget("size", size, rect))

    def _draw_avatars(self) -> None:
        area = self._content_rect()
        layout = self._grid_layout(
            area, len(self.avatar_choices), rows=3, columns=5
        )
        selected_avatar = str(self.profile.get("avatar_id", ""))
        for index in range(min(layout.capacity, len(self.avatar_choices))):
            avatar_id = self.avatar_choices[index]
            cell = layout.cell(index)
            rect = pygame.Rect(cell.x, cell.y, cell.width, cell.height)
            selected = avatar_id == selected_avatar
            self._draw_choice_panel(rect, selected)
            icon_size = max(32, min(rect.width, rect.height) - 18)
            self._blit_icon(
                avatar_id,
                pygame.Rect(
                    rect.centerx - icon_size // 2,
                    rect.centery - icon_size // 2,
                    icon_size,
                    icon_size,
                ),
            )
            if selected:
                self._selection_check(rect)
            self.targets.append(HitTarget("avatar", avatar_id, rect))

    def _wallpaper_geometry(self) -> tuple[pygame.Rect, int, int]:
        safe = self._safe_ui_rect()
        footer = Viewport(safe.width, safe.height).bounded_px(
            64, minimum=48, maximum=72
        )
        area = self._content_rect(footer=footer)
        probe = self._grid_layout(area, 8, rows=2, columns=4)
        capacity = max(1, probe.capacity)
        page_capacity = max(1, capacity - 1)
        return area, footer, page_capacity

    def _maximum_wallpaper_page(self) -> int:
        _, _, page_capacity = self._wallpaper_geometry()
        return max(
            0,
            (len(self.candidates) + page_capacity - 1) // page_capacity - 1,
        )

    def _draw_wallpapers(self) -> None:
        safe = self._safe_ui_rect()
        area, footer, page_capacity = self._wallpaper_geometry()
        start = self.wallpaper_page * page_capacity
        items: list[WallpaperCandidate | None] = [None]
        items.extend(self.candidates[start : start + page_capacity])
        layout = self._grid_layout(area, len(items), rows=2, columns=4)
        for index, candidate in enumerate(items[: layout.capacity]):
            cell = layout.cell(index)
            rect = pygame.Rect(cell.x, cell.y, cell.width, cell.height)
            selected = (
                candidate is None and self.theme.wallpaper_path is None
            ) or (
                candidate is not None
                and self.selected_wallpaper_source == candidate.path
            )
            self._draw_wallpaper_tile(rect, candidate, selected)
            self.targets.append(HitTarget("wallpaper", candidate, rect))

        if len(items) == 1:
            hint_size = min(78, max(42, area.height // 5))
            hint = pygame.Rect(0, 0, hint_size, hint_size)
            hint.midbottom = (area.centerx, area.bottom - 6)
            self._blit_icon("notebook", hint)

        maximum = self._maximum_wallpaper_page()
        if maximum > 0:
            nav_y = safe.bottom - self._margin() - footer // 2
            nav_size = min(54, footer - 6)
            if self.wallpaper_page > 0:
                previous = pygame.Rect(
                    area.centerx - nav_size - 12,
                    nav_y - nav_size // 2,
                    nav_size,
                    nav_size,
                )
                self._draw_arrow(previous, left=True)
                self.targets.append(HitTarget("wallpaper_page", -1, previous))
            if self.wallpaper_page < maximum:
                next_rect = pygame.Rect(
                    area.centerx + 12,
                    nav_y - nav_size // 2,
                    nav_size,
                    nav_size,
                )
                self._draw_arrow(next_rect, left=False)
                self.targets.append(HitTarget("wallpaper_page", 1, next_rect))

    def _draw_wallpaper_tile(
        self,
        rect: pygame.Rect,
        candidate: WallpaperCandidate | None,
        selected: bool,
    ) -> None:
        self._draw_choice_panel(rect, selected)
        inner = rect.inflate(-10, -10)
        if candidate is None:
            pygame.draw.rect(
                self.screen,
                self.theme.background,
                inner,
                border_radius=max(10, inner.width // 8),
            )
            inset = max(12, min(inner.width, inner.height) // 4)
            self._blit_icon("x_mark", inner.inflate(-inset, -inset))
        else:
            thumbnail = self._thumbnail(candidate, inner.size)
            if thumbnail is None:
                pygame.draw.rect(
                    self.screen,
                    _mix(self.theme.text, self.theme.panel, 0.84),
                    inner,
                    border_radius=12,
                )
                self._blit_icon(
                    "notebook",
                    inner.inflate(-inner.width // 3, -inner.height // 3),
                )
            else:
                self.screen.blit(
                    thumbnail, thumbnail.get_rect(center=inner.center)
                )
        if selected:
            self._selection_check(rect)

    def _thumbnail(
        self,
        candidate: WallpaperCandidate,
        size: tuple[int, int],
    ) -> pygame.Surface | None:
        width, height = max(1, size[0]), max(1, size[1])
        try:
            mtime = candidate.path.stat().st_mtime_ns
        except OSError:
            # Removable media can disappear between the bounded scan and the
            # next draw frame. A stale candidate is a normal transient state,
            # not a reason to crash the child-facing Activity.
            return None
        key = (candidate.path, mtime, width, height)
        if key in self.thumbnail_cache:
            return self.thumbnail_cache[key]
        if len(self.thumbnail_cache) >= self.MAX_THUMBNAIL_CACHE:
            self.thumbnail_cache.pop(next(iter(self.thumbnail_cache)))
        try:
            Image.MAX_IMAGE_PIXELS = self.MAX_THUMBNAIL_PIXELS
            with Image.open(candidate.path) as opened:
                if opened.width * opened.height > self.MAX_THUMBNAIL_PIXELS:
                    raise ValueError("too many pixels")
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.thumbnail((width, height), Image.Resampling.LANCZOS)
                surface = pygame.image.fromstring(
                    image.tobytes(), image.size, image.mode
                ).convert()
        except (
            OSError,
            ValueError,
            UnidentifiedImageError,
            Image.DecompressionBombError,
        ):
            surface = None
        self.thumbnail_cache[key] = surface
        return surface

    def _draw_choice_panel(self, rect: pygame.Rect, selected: bool) -> None:
        pygame.draw.rect(
            self.screen,
            self.theme.panel,
            rect,
            border_radius=max(16, min(rect.width, rect.height) // 6),
        )
        pygame.draw.rect(
            self.screen,
            self.theme.accent
            if selected
            else _mix(self.theme.text, self.theme.panel, 0.70),
            rect,
            width=6 if selected else 3,
            border_radius=max(16, min(rect.width, rect.height) // 6),
        )

    def _selection_check(self, rect: pygame.Rect) -> None:
        size = max(22, min(38, min(rect.width, rect.height) // 3))
        icon = pygame.transform.smoothscale(self.icons["check"], (size, size))
        self.screen.blit(
            icon,
            icon.get_rect(bottomright=(rect.right - 4, rect.bottom - 4)),
        )

    def _draw_arrow(self, rect: pygame.Rect, *, left: bool) -> None:
        self._draw_choice_panel(rect, False)
        inset = max(10, rect.width // 4)
        if left:
            points = (
                (rect.right - inset, rect.top + inset),
                (rect.left + inset, rect.centery),
                (rect.right - inset, rect.bottom - inset),
            )
        else:
            points = (
                (rect.left + inset, rect.top + inset),
                (rect.right - inset, rect.centery),
                (rect.left + inset, rect.bottom - inset),
            )
        pygame.draw.polygon(self.screen, self.theme.text, points)

    def _draw_feedback(self) -> None:
        if time.monotonic() >= self.feedback_until:
            return
        safe = self._safe_ui_rect()
        size = Viewport(safe.width, safe.height).bounded_px(
            52, minimum=38, maximum=62
        )
        rect = pygame.Rect(
            safe.right - size - self._margin(),
            safe.bottom - size - self._margin(),
            size,
            size,
        )
        self._blit_icon("x_mark" if self.feedback_error else "check", rect)

    def _draw_pointer(self) -> None:
        draw_activity_pointer(self.screen)

    def _blit_icon(self, icon_id: str, rect: pygame.Rect) -> None:
        source = self.icons[icon_id]
        size = (max(1, rect.width), max(1, rect.height))
        image = (
            source
            if source.get_size() == size
            else pygame.transform.smoothscale(source, size)
        )
        self.screen.blit(image, image.get_rect(center=rect.center))


def _mix(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
    right_weight: float,
) -> tuple[int, int, int]:
    return tuple(
        round(a * (1.0 - right_weight) + b * right_weight)
        for a, b in zip(left, right)
    )  # type: ignore[return-value]


def main() -> int:
    return MyGreiaSettings().run()


if __name__ == "__main__":
    raise SystemExit(main())