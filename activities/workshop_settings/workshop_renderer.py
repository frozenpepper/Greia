"""Draw helpers and bounded caches for workshop_settings.

Owns pre-converted icons, scaled icon cache and thumbnail cache.
All expensive surfaces are prepared once via ``convert()`` /
``convert_alpha()`` and invalidated on resize so a display-size
change never leaves a stale scale. Per-frame ``smoothscale`` /
``image.load`` / font construction is avoided.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pygame
from PIL import Image, ImageOps, UnidentifiedImageError

from greia_platform.activity_api import get_icon_path
from greia_platform.activity_ui import draw_activity_pointer
from greia_platform.activity_viewport import ActivityViewport
from greia_platform.customization import ColorSwatch, WallpaperCandidate
from greia_platform.responsive_layout import AdaptiveGridPolicy, UiRect, Viewport
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.ui_preferences import InterfaceSize

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_content import (
        MAX_THUMBNAIL_CACHE,
        MAX_THUMBNAIL_PIXELS,
        MODE_ICONS,
        MODES,
    )
except ImportError:
    from workshop_content import (  # type: ignore[no-redef]
        MAX_THUMBNAIL_CACHE,
        MAX_THUMBNAIL_PIXELS,
        MODE_ICONS,
        MODES,
    )


@dataclass(frozen=True, slots=True)
class HitTarget:
    action: str
    value: object
    rect: pygame.Rect


def settings_safe_ui_rect(width: int, height: int) -> UiRect:
    """Return the parent-settings region outside Greia-owned Home/Back chrome."""

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


def _mix(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
    right_weight: float,
) -> tuple[int, int, int]:
    return tuple(
        round(a * (1.0 - right_weight) + b * right_weight)
        for a, b in zip(left, right)
    )  # type: ignore[return-value]


class WorkshopRenderer:
    """Own workshop presentation, geometry helpers and bounded caches.

    Icons are ``convert_alpha()`` once at construction. Scaled variants
    and thumbnails are cached with explicit bounds and invalidated on
    resize. No image decode, scale or font construction occurs in hot
    draw loops beyond a bounded cache miss.
    """

    def __init__(self, screen: pygame.Surface, avatar_choices: tuple[str, ...]) -> None:
        self.screen = screen
        self.avatar_choices = tuple(avatar_choices)
        # Bounded caches - small fixed sets.
        self.thumbnail_cache: dict[tuple[Path, int, int, int], pygame.Surface | None] = {}
        self._scaled_icon_cache: dict[tuple[str, int, int], pygame.Surface] = {}
        self._check_cache: dict[int, pygame.Surface] = {}
        self.icons: dict[str, pygame.Surface] = {}
        self._load_icons()

    # -- lifecycle / invalidation -----------------------------------------

    def _load_icons(self) -> None:
        icon_ids = {
            *MODE_ICONS.values(),
            "yellow_star",
            "check",
            "x_mark",
            *self.avatar_choices,
        }
        for icon_id in icon_ids:
            try:
                surf = pygame.image.load(str(get_icon_path(icon_id, 128))).convert_alpha()
            except Exception:
                # Headless / missing asset fallback - small placeholder.
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                surf.fill((200, 200, 200, 255))
            self.icons[icon_id] = surf

    def on_resize(self, screen: pygame.Surface) -> None:
        """Invalidate display-dependent surfaces after a resize."""
        self.screen = screen
        self._scaled_icon_cache.clear()
        self._check_cache.clear()
        # Thumbnail sizes are keyed by (path, mtime, w, h) so stale sizes
        # naturally miss; clear to bound growth across many resizes.
        self.thumbnail_cache.clear()

    # -- geometry helpers -------------------------------------------------

    def _viewport(self) -> Viewport:
        return Viewport(*self.screen.get_size())

    def _safe_ui_rect(self) -> UiRect:
        return settings_safe_ui_rect(*self.screen.get_size())

    def _margin(self) -> int:
        safe = self._safe_ui_rect()
        return Viewport(safe.width, safe.height).bounded_px(18, minimum=10, maximum=28)

    def _top_bar_height(self) -> int:
        safe = self._safe_ui_rect()
        return Viewport(safe.width, safe.height).bounded_px(82, minimum=60, maximum=96)

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
        return policy.layout(UiRect(area.x, area.y, area.width, area.height), item_count)

    def _wallpaper_geometry(self) -> tuple[pygame.Rect, int, int]:
        safe = self._safe_ui_rect()
        footer = Viewport(safe.width, safe.height).bounded_px(64, minimum=48, maximum=72)
        area = self._content_rect(footer=footer)
        probe = self._grid_layout(area, 8, rows=2, columns=4)
        capacity = max(1, probe.capacity)
        page_capacity = max(1, capacity - 1)
        return area, footer, page_capacity

    def _maximum_wallpaper_page(self, candidates: tuple[WallpaperCandidate, ...]) -> int:
        _, _, page_capacity = self._wallpaper_geometry()
        return max(0, (len(candidates) + page_capacity - 1) // page_capacity - 1)

    # -- thumbnail (bounded) ----------------------------------------------

    def _thumbnail(
        self,
        candidate: WallpaperCandidate,
        size: tuple[int, int],
    ) -> pygame.Surface | None:
        width, height = max(1, size[0]), max(1, size[1])
        try:
            mtime = candidate.path.stat().st_mtime_ns
        except OSError:
            return None
        key = (candidate.path, mtime, width, height)
        if key in self.thumbnail_cache:
            return self.thumbnail_cache[key]
        if len(self.thumbnail_cache) >= MAX_THUMBNAIL_CACHE:
            self.thumbnail_cache.pop(next(iter(self.thumbnail_cache)))
        try:
            Image.MAX_IMAGE_PIXELS = MAX_THUMBNAIL_PIXELS
            with Image.open(candidate.path) as opened:
                if opened.width * opened.height > MAX_THUMBNAIL_PIXELS:
                    raise ValueError("too many pixels")
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.thumbnail((width, height), Image.Resampling.LANCZOS)
                surface = pygame.image.fromstring(image.tobytes(), image.size, image.mode).convert()
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            surface = None
        self.thumbnail_cache[key] = surface
        return surface

    def prune_thumbnails(self, current_paths: set[Path]) -> None:
        self.thumbnail_cache = {
            key: value for key, value in self.thumbnail_cache.items() if key[0] in current_paths
        }

    # -- icon helpers (bounded) -------------------------------------------

    def _blit_icon(self, icon_id: str, rect: pygame.Rect) -> None:
        source = self.icons.get(icon_id)
        if source is None:
            return
        size = (max(1, rect.width), max(1, rect.height))
        key = (icon_id, size[0], size[1])
        cached = self._scaled_icon_cache.get(key)
        if cached is None:
            if source.get_size() == size:
                cached = source
            else:
                cached = pygame.transform.smoothscale(source, size)
                # Bounded: at most ~64 distinct icon sizes.
                if len(self._scaled_icon_cache) >= 64:
                    self._scaled_icon_cache.pop(next(iter(self._scaled_icon_cache)))
                self._scaled_icon_cache[key] = cached
        self.screen.blit(cached, cached.get_rect(center=rect.center))

    def _selection_check(self, rect: pygame.Rect) -> None:
        size = max(22, min(38, min(rect.width, rect.height) // 3))
        cached = self._check_cache.get(size)
        if cached is None:
            source = self.icons.get("check")
            if source is None:
                return
            cached = pygame.transform.smoothscale(source, (size, size))
            if len(self._check_cache) >= 16:
                self._check_cache.pop(next(iter(self._check_cache)))
            self._check_cache[size] = cached
        self.screen.blit(cached, cached.get_rect(bottomright=(rect.right - 4, rect.bottom - 4)))

    # -- drawing ----------------------------------------------------------

    def draw(self, model, targets: list[HitTarget]) -> None:
        # model is WorkshopModel; duck-typed to avoid circular import.
        self.screen.fill(model.theme.background)  # type: ignore[union-attr]
        targets.clear()
        self._draw_mode_bar(model, targets)
        if model.mode == "colors":
            self._draw_colors(model, targets)
        elif model.mode == "wallpapers":
            self._draw_wallpapers(model, targets)
        elif model.mode == "size":
            self._draw_sizes(model, targets)
        else:
            self._draw_avatars(model, targets)
        self._draw_feedback(model)
        self._draw_pointer()

    def _draw_mode_bar(self, model, targets: list[HitTarget]) -> None:
        safe = self._safe_ui_rect()
        margin = self._margin()
        bar_height = self._top_bar_height()
        button = min(bar_height, max(46, (safe.width - margin * 2) // 7))
        gap = max(8, min(18, (safe.width - button * len(MODES)) // (len(MODES) + 1)))
        total = button * len(MODES) + gap * (len(MODES) - 1)
        x = safe.x + max(margin, (safe.width - total) // 2)
        y = safe.y + margin
        pointer = pygame.mouse.get_pos()
        for mode in MODES:
            rect = pygame.Rect(x, y, button, button)
            selected = mode == model.mode
            hovered = pygame.mouse.get_focused() and rect.collidepoint(pointer)
            pygame.draw.rect(
                self.screen,
                model.theme.panel,  # type: ignore[union-attr]
                rect,
                border_radius=max(14, button // 4),
            )
            pygame.draw.rect(
                self.screen,
                model.theme.accent  # type: ignore[union-attr]
                if selected or hovered
                else _mix(model.theme.text, model.theme.panel, 0.72),  # type: ignore[union-attr]
                rect,
                width=6 if selected else 3,
                border_radius=max(14, button // 4),
            )
            self._blit_icon(MODE_ICONS[mode], rect.inflate(-12, -12))
            targets.append(HitTarget("mode", mode, rect))
            x += button + gap

    def _draw_colors(self, model, targets: list[HitTarget]) -> None:
        area = self._content_rect()
        rows = (
            ("background", model.palette.backgrounds, model.theme.preferences.background, "palette"),  # type: ignore[union-attr]
            ("accent", model.palette.accents, model.theme.preferences.accent, "yellow_star"),  # type: ignore[union-attr]
            ("text", model.palette.texts, model.theme.preferences.text, "abc_blocks"),  # type: ignore[union-attr]
        )
        row_height = max(1, area.height // len(rows))
        label_reserve = min(86, max(54, area.width // 10))
        for row_index, (kind, swatches, selected_id, icon_id) in enumerate(rows):
            row = pygame.Rect(area.left, area.top + row_index * row_height, area.width, row_height)
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
                self._draw_swatch(model, rect, swatch, kind, swatch.swatch_id == selected_id)
                targets.append(HitTarget("color", (kind, swatch.swatch_id), rect.inflate(6, 6)))

    def _draw_swatch(
        self,
        model,
        rect: pygame.Rect,
        swatch: ColorSwatch,
        kind: str,
        selected: bool,
    ) -> None:
        pygame.draw.rect(self.screen, swatch.color, rect, border_radius=max(10, rect.width // 4))
        pygame.draw.rect(
            self.screen,
            model.theme.accent if selected else _mix(model.theme.text, model.theme.panel, 0.6),  # type: ignore[union-attr]
            rect,
            width=6 if selected else 2,
            border_radius=max(10, rect.width // 4),
        )
        if kind == "text":
            panel = rect.inflate(-max(8, rect.width // 4), -max(8, rect.height // 3))
            pygame.draw.rect(self.screen, model.theme.panel, panel, border_radius=max(5, panel.height // 4))  # type: ignore[union-attr]
            pygame.draw.line(
                self.screen,
                swatch.color,
                (panel.left + 5, panel.centery),
                (panel.right - 5, panel.centery),
                width=max(3, panel.height // 4),
            )
        if selected:
            self._selection_check(rect)

    def _draw_sizes(self, model, targets: list[HitTarget]) -> None:
        area = self._content_rect()
        layout = self._grid_layout(area, len(tuple(InterfaceSize)), rows=1, columns=3)
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
            selected = size == model.ui_preferences.interface_size  # type: ignore[union-attr]
            self._draw_choice_panel(model, rect, selected)
            sample_size = max(32, min(rect.width, rect.height) * samples[size])
            icon_size = int(sample_size)
            icon_rect = pygame.Rect(0, 0, icon_size, icon_size)
            icon_rect.center = rect.center
            self._blit_icon("abc_blocks", icon_rect)
            if selected:
                self._selection_check(rect)
            targets.append(HitTarget("size", size, rect))

    def _draw_avatars(self, model, targets: list[HitTarget]) -> None:
        area = self._content_rect()
        layout = self._grid_layout(area, len(model.avatar_choices), rows=3, columns=5)
        selected_avatar = str(model.profile.get("avatar_id", ""))
        for index in range(min(layout.capacity, len(model.avatar_choices))):
            avatar_id = model.avatar_choices[index]
            cell = layout.cell(index)
            rect = pygame.Rect(cell.x, cell.y, cell.width, cell.height)
            selected = avatar_id == selected_avatar
            self._draw_choice_panel(model, rect, selected)
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
            targets.append(HitTarget("avatar", avatar_id, rect))

    def _draw_wallpapers(self, model, targets: list[HitTarget]) -> None:
        safe = self._safe_ui_rect()
        area, footer, page_capacity = self._wallpaper_geometry()
        start = model.wallpaper_page * page_capacity
        items: list[WallpaperCandidate | None] = [None]
        items.extend(model.candidates[start : start + page_capacity])  # type: ignore[union-attr]
        layout = self._grid_layout(area, len(items), rows=2, columns=4)
        for index, candidate in enumerate(items[: layout.capacity]):
            cell = layout.cell(index)
            rect = pygame.Rect(cell.x, cell.y, cell.width, cell.height)
            selected = (candidate is None and model.theme.wallpaper_path is None) or (  # type: ignore[union-attr]
                candidate is not None and model.selected_wallpaper_source == candidate.path
            )
            self._draw_wallpaper_tile(model, rect, candidate, selected)
            targets.append(HitTarget("wallpaper", candidate, rect))

        if len(items) == 1:
            hint_size = min(78, max(42, area.height // 5))
            hint = pygame.Rect(0, 0, hint_size, hint_size)
            hint.midbottom = (area.centerx, area.bottom - 6)
            self._blit_icon("notebook", hint)

        maximum = self._maximum_wallpaper_page(tuple(model.candidates))  # type: ignore[arg-type]
        if maximum > 0:
            nav_y = safe.bottom - self._margin() - footer // 2
            nav_size = min(54, footer - 6)
            if model.wallpaper_page > 0:
                previous = pygame.Rect(area.centerx - nav_size - 12, nav_y - nav_size // 2, nav_size, nav_size)
                self._draw_arrow(model, previous, left=True)
                targets.append(HitTarget("wallpaper_page", -1, previous))
            if model.wallpaper_page < maximum:
                next_rect = pygame.Rect(area.centerx + 12, nav_y - nav_size // 2, nav_size, nav_size)
                self._draw_arrow(model, next_rect, left=False)
                targets.append(HitTarget("wallpaper_page", 1, next_rect))

    def _draw_wallpaper_tile(
        self,
        model,
        rect: pygame.Rect,
        candidate: WallpaperCandidate | None,
        selected: bool,
    ) -> None:
        self._draw_choice_panel(model, rect, selected)
        inner = rect.inflate(-10, -10)
        if candidate is None:
            pygame.draw.rect(self.screen, model.theme.background, inner, border_radius=max(10, inner.width // 8))  # type: ignore[union-attr]
            inset = max(12, min(inner.width, inner.height) // 4)
            self._blit_icon("x_mark", inner.inflate(-inset, -inset))
        else:
            thumbnail = self._thumbnail(candidate, inner.size)
            if thumbnail is None:
                pygame.draw.rect(self.screen, _mix(model.theme.text, model.theme.panel, 0.84), inner, border_radius=12)  # type: ignore[union-attr]
                self._blit_icon("notebook", inner.inflate(-inner.width // 3, -inner.height // 3))
            else:
                self.screen.blit(thumbnail, thumbnail.get_rect(center=inner.center))
        if selected:
            self._selection_check(rect)

    def _draw_choice_panel(self, model, rect: pygame.Rect, selected: bool) -> None:
        pygame.draw.rect(
            self.screen,
            model.theme.panel,  # type: ignore[union-attr]
            rect,
            border_radius=max(16, min(rect.width, rect.height) // 6),
        )
        pygame.draw.rect(
            self.screen,
            model.theme.accent if selected else _mix(model.theme.text, model.theme.panel, 0.70),  # type: ignore[union-attr]
            rect,
            width=6 if selected else 3,
            border_radius=max(16, min(rect.width, rect.height) // 6),
        )

    def _draw_arrow(self, model, rect: pygame.Rect, *, left: bool) -> None:
        self._draw_choice_panel(model, rect, False)
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
        pygame.draw.polygon(self.screen, model.theme.text, points)  # type: ignore[union-attr]

    def _draw_feedback(self, model) -> None:
        if time.monotonic() >= model.feedback_until:
            return
        safe = self._safe_ui_rect()
        size = Viewport(safe.width, safe.height).bounded_px(52, minimum=38, maximum=62)
        rect = pygame.Rect(safe.right - size - self._margin(), safe.bottom - size - self._margin(), size, size)
        self._blit_icon("x_mark" if model.feedback_error else "check", rect)

    def _draw_pointer(self) -> None:
        draw_activity_pointer(self.screen)


__all__ = ["HitTarget", "WorkshopRenderer", "settings_safe_ui_rect", "_mix"]
