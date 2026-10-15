"""Draw helpers and bounded caches for Painting.

Owns pre-scaled icons, background surface and thumbnail cache.
Static chrome is prepared once via ``convert()`` / ``convert_alpha()``
and invalidated on resize so a display-size change never leaves a
stale scale. Per-frame ``smoothscale`` / ``image.load`` / font
construction is avoided.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
import pygame

from greia_platform.activity_ui import draw_activity_pointer, load_icon, mix
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .painting_content import BRUSH_SIZES, COLORS, GALLERY_PAGE_SIZE
else:  # pragma: no cover - runtime/script fallback
    from painting_content import BRUSH_SIZES, COLORS, GALLERY_PAGE_SIZE

try:
    from greia_platform.activity_api import get_icon_path
except Exception:  # pragma: no cover - headless
    def get_icon_path(name: str, size: int = 64) -> str:  # type: ignore[no-redef]
        return name


class PaintingRenderer:
    """Own Painting presentation, geometry helpers and bounded caches.

    All expensive image/scale/font work is prepared once in
    ``_precompute_ui_resources`` / ``_load_assets``. ``on_resize``
    re-keys the caches so no stale ``smoothscale`` result survives a
    display size change. Thumbnail decoding is bounded by the gallery
    window (6 visible) and the library bound (48).
    """

    def __init__(self, metrics, theme, screen: pygame.Surface, *, status_labels: dict[str, str] | None = None) -> None:
        self.metrics = metrics
        self.theme = theme
        self.screen = screen
        # Bounded caches - small fixed sets, not growing with frames.
        self.assets: dict[str, pygame.Surface] = {}
        self._scaled_tool_icons: dict[str, pygame.Surface] = {}
        self._scaled_tool_icons_disabled: dict[str, pygame.Surface] = {}
        self._scaled_brush_icons: dict[int, pygame.Surface] = {}
        self._scaled_dish: pygame.Surface | None = None
        self._scaled_card_frame: pygame.Surface | None = None
        self._background_surface: pygame.Surface | None = None
        # Pure semantic status IDs remain stable; locale text is supplied by
        # the Activity's already resolved profile context. Standalone/legacy
        # renderer construction uses language-neutral visual symbols.
        self._status_text = dict(status_labels) if status_labels is not None else {
            "saved": "✓", "saving": "…", "error": "!",
        }
        self._status_labels: dict[str, pygame.Surface] = {}
        self._typography = GreiaTypography()
        self.empty_icon: pygame.Surface | None = None
        # Thumbnail cache is naturally bounded by MAX_PAINTINGS (48) and
        # the visible gallery window (6). Use dict with explicit limit.
        self.thumbnail_cache: dict[str, pygame.Surface] = {}
        self._load_assets()
        self._precompute_ui_resources()

    # -- lifecycle / invalidation ----------------------------------------

    def _load_assets(self) -> None:
        assets_dir = Path(__file__).parent / "assets" / "runtime"
        asset_names = [
            "tool_gallery",
            "tool_undo",
            "tool_new",
            "tool_eraser",
            "brush_small",
            "brush_medium",
            "brush_large",
            "canvas_card_frame",
            "color_well_dish",
        ]
        for name in asset_names:
            p = assets_dir / f"{name}.png"
            if p.exists():
                try:
                    surf = pygame.image.load(str(p)).convert_alpha()
                    self.assets[name] = surf
                except Exception:
                    pass
        # Load fallback rainbow icon for empty gallery
        try:
            self.empty_icon = load_icon(get_icon_path("rainbow", 64), self.metrics.px(52))
        except Exception:
            self.empty_icon = pygame.Surface((self.metrics.px(52), self.metrics.px(52)), pygame.SRCALPHA)

    def _precompute_ui_resources(self) -> None:
        # Pre-scale tool icons (bounded: 4 keys)
        icon_sz = self.metrics.px(36)
        self._scaled_tool_icons = {}
        self._scaled_tool_icons_disabled = {}
        for name in ("tool_gallery", "tool_undo", "tool_new", "tool_eraser"):
            icon = self.assets.get(name)
            if icon is not None:
                scaled = pygame.transform.smoothscale(icon, (icon_sz, icon_sz))
                self._scaled_tool_icons[name] = scaled
                disabled = scaled.copy()
                disabled.set_alpha(100)
                self._scaled_tool_icons_disabled[name] = disabled

        # Pre-scale color dish (single)
        dish_sz = self.metrics.px(46) + self.metrics.px(6)
        well_dish = self.assets.get("color_well_dish")
        if well_dish is not None:
            self._scaled_dish = pygame.transform.smoothscale(well_dish, (dish_sz, dish_sz))
        else:
            self._scaled_dish = None

        # Pre-scale brush icons (bounded: 3 keys)
        brush_keys = ["brush_small", "brush_medium", "brush_large"]
        brush_sz = self.metrics.px(34)
        self._scaled_brush_icons = {}
        for idx, key in enumerate(brush_keys):
            b_icon = self.assets.get(key)
            if b_icon is not None:
                self._scaled_brush_icons[idx] = pygame.transform.smoothscale(b_icon, (brush_sz, brush_sz))

        # Pre-scale gallery card frame (single, sized to current canvas_rect)
        card_frame = self.assets.get("canvas_card_frame")
        area = self.canvas_rect
        gap = self.metrics.px(18)
        card_w = max(1, (area.width - gap * 2) // 3)
        card_h = max(1, (area.height - gap) // 2)
        if card_frame is not None:
            self._scaled_card_frame = pygame.transform.smoothscale(card_frame, (card_w, card_h))
        else:
            self._scaled_card_frame = None

        # Pre-render studio background surface (single, convert() once)
        bg_top = (252, 248, 238)
        bg_bottom = (245, 238, 224)
        w, h = self.screen.get_size()
        bg_surf = pygame.Surface((w, h)).convert()
        bg_surf.fill(bg_top)
        band_h = h // 3
        band_rect = pygame.Rect(0, h - band_h, w, band_h)
        pygame.draw.rect(bg_surf, bg_bottom, band_rect)
        line_y = self.canvas_rect.top - self.metrics.px(8)
        if line_y > 0:
            pygame.draw.line(bg_surf, (235, 226, 208), (0, line_y), (w, line_y), 2)
        self._background_surface = bg_surf

        # Pre-render status labels once (bounded: 3 labels) through the shared
        # typography so glyph fallback matches the rest of Greia.
        self._status_labels = {
            key: self._typography.render(value, FontRole.CONTROL, self.metrics.px(17), (100, 116, 139))
            for key, value in self._status_text.items()
        }

    def on_resize(self, metrics, screen: pygame.Surface) -> None:
        """Invalidate display-dependent surfaces after a resize."""
        self.metrics = metrics
        self.screen = screen
        self._scaled_tool_icons.clear()
        self._scaled_tool_icons_disabled.clear()
        self._scaled_brush_icons.clear()
        self._scaled_dish = None
        self._scaled_card_frame = None
        self._background_surface = None
        self._status_labels.clear()
        # Keep thumbnail_cache but re-validate size on next get (size key)
        self._load_assets()
        self._precompute_ui_resources()

    # -- geometry helpers -------------------------------------------------

    @property
    def palette_height(self) -> int:
        return self.metrics.px(82)

    @property
    def canvas_rect(self) -> pygame.Rect:
        return self.metrics.activity_content_rect(top_gap=2, bottom_reserve=self.palette_height)

    def _color_buttons(self) -> list[tuple[pygame.Rect, int]]:
        safe = self.metrics.activity_safe_rect()
        left = safe.left + self.metrics.margin + self.metrics.px(10)
        y = safe.bottom - self.metrics.margin - self.palette_height // 2
        diameter = self.metrics.px(46)
        gap = self.metrics.px(8)
        return [
            (pygame.Rect(left + i * (diameter + gap), y - diameter // 2, diameter, diameter), i)
            for i in range(len(COLORS))
        ]

    def _size_buttons(self) -> list[tuple[pygame.Rect, int]]:
        safe = self.metrics.activity_safe_rect()
        size = self.metrics.px(48)
        gap = self.metrics.px(6)
        right = safe.right - self.metrics.margin
        y = safe.bottom - self.metrics.margin - self.palette_height // 2
        result = []
        for order, brush_index in enumerate(reversed(range(len(BRUSH_SIZES)))):
            result.append((pygame.Rect(right - (order + 1) * size - order * gap, y - size // 2, size, size), brush_index))
        return result

    @staticmethod
    def gallery_page_count(record_count: int) -> int:
        """Number of 3x2 gallery pages needed to reach every saved painting."""
        return max(1, -(-int(record_count) // GALLERY_PAGE_SIZE))

    def gallery_cards(self, records, page: int = 0) -> list[tuple[pygame.Rect, object]]:
        """Return the hit rectangles for one gallery page (default: first)."""
        area = self.canvas_rect
        gap = self.metrics.px(18)
        card_w = (area.width - gap * 2) // 3
        card_h = (area.height - gap) // 2
        page = max(0, min(int(page), self.gallery_page_count(len(records)) - 1))
        first = page * GALLERY_PAGE_SIZE
        cards = []
        for index, record in enumerate(records[first:first + GALLERY_PAGE_SIZE]):
            row, col = divmod(index, 3)
            cards.append((pygame.Rect(area.left + col * (card_w + gap), area.top + row * (card_h + gap), card_w, card_h), record))
        return cards

    def gallery_nav_buttons(self) -> tuple[pygame.Rect, pygame.Rect]:
        """Big previous/next arrows in the (otherwise unused) palette strip."""
        safe = self.metrics.activity_safe_rect()
        height = self.metrics.px(66)
        width = self.metrics.px(96)
        y = safe.bottom - self.metrics.margin - self.palette_height // 2 - height // 2
        left = safe.left + self.metrics.margin + self.metrics.px(10)
        right = safe.right - self.metrics.margin - self.metrics.px(10) - width
        return pygame.Rect(left, y, width, height), pygame.Rect(right, y, width, height)

    def thumbnail(self, record, size: tuple[int, int], repository) -> pygame.Surface | None:
        cached = self.thumbnail_cache.get(record.painting_id)
        if cached is not None and cached.get_size() == size:
            return cached
        try:
            surface = _decode_png(repository.load_png(record.painting_id), size)
        except (RuntimeError, ValueError, OSError):
            return None
        # Bounded: at most MAX_PAINTINGS entries (48)
        if len(self.thumbnail_cache) >= 48:
            # Evict oldest (insertion order)
            oldest = next(iter(self.thumbnail_cache))
            self.thumbnail_cache.pop(oldest, None)
        self.thumbnail_cache[record.painting_id] = surface
        return surface

    def invalidate_thumbnail(self, painting_id: str) -> None:
        self.thumbnail_cache.pop(painting_id, None)

    # -- drawing ----------------------------------------------------------

    def draw_studio_background(self, screen: pygame.Surface) -> None:
        if self._background_surface is not None:
            screen.blit(self._background_surface, (0, 0))
            return
        bg_top = (252, 248, 238)
        bg_bottom = (245, 238, 224)
        h = screen.get_height()
        w = screen.get_width()
        screen.fill(bg_top)
        band_h = h // 3
        band_rect = pygame.Rect(0, h - band_h, w, band_h)
        pygame.draw.rect(screen, bg_bottom, band_rect)
        line_y = self.canvas_rect.top - self.metrics.px(8)
        if line_y > 0:
            pygame.draw.line(screen, (235, 226, 208), (0, line_y), (w, line_y), 2)

    def shared_export_button(self) -> pygame.Rect | None:
        """Child-sized share/import slot in the free center of the safe toolbar."""
        left = self.metrics.activity_toolbar_button(1, side="left")
        right = self.metrics.activity_toolbar_button(1, side="right")
        size = self.metrics.button_size
        candidate = pygame.Rect((self.metrics.width-size)//2,left.y,size,size)
        if candidate.left <= left.right+self.metrics.gap or candidate.right >= right.left-self.metrics.gap:
            return None
        return candidate

    def draw_toolbar(
        self,
        screen: pygame.Surface,
        mode: str,
        history,
        eraser: bool,
        dirty: bool,
        save_error: bool,
        *,
        shared_available: bool = False,
        shared_feedback: str = "",
        shared_import_state: str = "",
    ) -> None:
        gallery = self.metrics.activity_toolbar_button(0, side="left")
        undo = self.metrics.activity_toolbar_button(1, side="left")
        new = self.metrics.activity_toolbar_button(0, side="right")
        eraser_rect = self.metrics.activity_toolbar_button(1, side="right")

        self._draw_tactile_button(
            screen,
            gallery,
            icon_key="tool_gallery",
            active=mode == "gallery",
            base_color=(255, 255, 255),
            active_color=(254, 240, 138),
            fallback_symbol="grid",
        )
        can_undo = mode == "paint" and bool(history.items)
        self._draw_tactile_button(
            screen,
            undo,
            icon_key="tool_undo",
            active=False,
            base_color=(255, 255, 255) if can_undo else (241, 245, 249),
            fallback_symbol="undo",
            disabled=not can_undo,
        )
        self._draw_tactile_button(
            screen,
            new,
            icon_key="tool_new",
            active=False,
            base_color=(251, 191, 36),
            fallback_symbol="plus",
        )
        self._draw_tactile_button(
            screen,
            eraser_rect,
            icon_key="tool_eraser",
            active=eraser,
            base_color=(255, 255, 255),
            active_color=(254, 226, 226),
            fallback_symbol="eraser",
        )

        # Deliberate publication is independent from per-stroke autosave.
        # The center remains visually quiet on unsupported/narrow viewports.
        shared = self.shared_export_button() if shared_available else None
        if shared is not None and mode == "paint":
            self._draw_tactile_button(
                screen, shared, icon_key="tool_share",
                active=shared_feedback == "saved",
                base_color=(225, 246, 228),
                active_color=(171, 231, 186),
                fallback_symbol="share",
            )
            if shared_feedback == "error":
                pygame.draw.rect(screen,(211,61,65),shared,width=max(3,self.metrics.px(4)),border_radius=self.metrics.radius)
        elif shared is not None and mode == "gallery":
            self._draw_tactile_button(
                screen, shared, icon_key="tool_import",
                active=shared_import_state == "pending",
                base_color=(221, 235, 252),
                active_color=(165, 211, 247),
                fallback_symbol="import",
                disabled=shared_import_state == "pending",
            )
            if shared_import_state == "error":
                pygame.draw.rect(screen,(211,61,65),shared,width=max(3,self.metrics.px(4)),border_radius=self.metrics.radius)

        # Status Pill Indicator
        pill_h = self.metrics.px(28)
        # Measure once from pre-rendered labels, retaining complete French and
        # Spanish words instead of overlapping/cropping them.
        widest_label = max((item.get_width() for item in self._status_labels.values()), default=0)
        pill_w = max(self.metrics.px(72), pill_h + self.metrics.px(12) + widest_label)
        pill_x = eraser_rect.left - pill_w - self.metrics.px(10)
        pill_y = eraser_rect.centery - pill_h // 2
        pill_rect = pygame.Rect(pill_x, pill_y, pill_w, pill_h)
        pygame.draw.rect(screen, (255, 255, 255), pill_rect, border_radius=pill_h // 2)
        pygame.draw.rect(screen, (226, 232, 240), pill_rect, width=2, border_radius=pill_h // 2)
        status_color = (239, 68, 68) if save_error else ((245, 158, 11) if dirty else (34, 197, 94))
        pygame.draw.circle(screen, status_color, (pill_rect.left + pill_h // 2, pill_rect.centery), self.metrics.px(5))
        if not dirty and not save_error:
            cx = pill_rect.left + pill_h // 2
            cy = pill_rect.centery
            pygame.draw.lines(screen, (255, 255, 255), False, [(cx - 3, cy), (cx - 1, cy + 2), (cx + 3, cy - 2)], 2)
        status_key = "error" if save_error else ("saving" if dirty else "saved")
        txt = self._status_labels[status_key]
        screen.blit(txt, (pill_rect.left + pill_h + 2, pill_rect.centery - txt.get_height() // 2))

    def _draw_tactile_button(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        icon_key: str,
        active: bool = False,
        base_color: tuple[int, int, int] = (255, 255, 255),
        active_color: tuple[int, int, int] = (254, 240, 138),
        fallback_symbol: str = "",
        disabled: bool = False,
    ) -> None:
        radius = self.metrics.radius
        shadow_rect = rect.move(0, self.metrics.px(3))
        pygame.draw.rect(screen, (203, 213, 225), shadow_rect, border_radius=radius)
        fill = active_color if active else base_color
        if disabled:
            fill = (241, 245, 249)
        pygame.draw.rect(screen, fill, rect, border_radius=radius)
        border_col = (234, 88, 12) if active else (226, 232, 240)
        border_w = max(2, self.metrics.px(3)) if active else max(1, self.metrics.px(2))
        pygame.draw.rect(screen, border_col, rect, width=border_w, border_radius=radius)
        scaled_icon = (
            self._scaled_tool_icons_disabled.get(icon_key) if disabled else self._scaled_tool_icons.get(icon_key)
        )
        if scaled_icon is not None:
            screen.blit(scaled_icon, scaled_icon.get_rect(center=rect.center))
        else:
            col = (148, 163, 184) if disabled else (51, 65, 85)
            if fallback_symbol == "grid":
                for r_idx in range(2):
                    for c_idx in range(2):
                        dot_r = pygame.Rect(rect.centerx - 12 + c_idx * 14, rect.centery - 12 + r_idx * 14, 10, 10)
                        pygame.draw.rect(screen, col, dot_r, border_radius=3)
            elif fallback_symbol == "undo":
                pygame.draw.circle(screen, col, rect.center, 12, width=3)
            elif fallback_symbol == "plus":
                pygame.draw.line(screen, (255, 255, 255), (rect.centerx, rect.centery - 12), (rect.centerx, rect.centery + 12), 4)
                pygame.draw.line(screen, (255, 255, 255), (rect.centerx - 12, rect.centery), (rect.centerx + 12, rect.centery), 4)
            elif fallback_symbol == "eraser":
                pygame.draw.rect(screen, col, pygame.Rect(rect.centerx - 12, rect.centery - 8, 24, 16), border_radius=4)
            elif fallback_symbol in {"share", "import"}:
                # The same picture glyph with an unambiguous arrow direction:
                # up = publish to My Creations, down = bring one into Painting.
                cx, cy = rect.center
                pygame.draw.rect(screen,col,(cx-16,cy-2,32,21),width=3,border_radius=4)
                pygame.draw.circle(screen,col,(cx+8,cy+3),3)
                pygame.draw.lines(screen,col,False,[(cx-12,cy+13),(cx-5,cy+7),(cx+1,cy+12)],3)
                if fallback_symbol == "share":
                    pygame.draw.line(screen,col,(cx,cy-16),(cx,cy+1),4)
                    pygame.draw.lines(screen,col,False,[(cx-8,cy-9),(cx,cy-17),(cx+8,cy-9)],4)
                else:
                    pygame.draw.line(screen,col,(cx,cy-17),(cx,cy+1),4)
                    pygame.draw.lines(screen,col,False,[(cx-8,cy-7),(cx,cy+1),(cx+8,cy-7)],4)

    def draw_canvas(self, screen: pygame.Surface, canvas: pygame.Surface) -> None:
        crect = self.canvas_rect
        shadow_rect = crect.inflate(self.metrics.px(8), self.metrics.px(8)).move(0, self.metrics.px(4))
        pygame.draw.rect(screen, (214, 204, 188), shadow_rect, border_radius=self.metrics.radius + 4)
        mat_rect = crect.inflate(self.metrics.px(6), self.metrics.px(6))
        pygame.draw.rect(screen, (250, 246, 238), mat_rect, border_radius=self.metrics.radius + 2)
        pygame.draw.rect(screen, (226, 218, 202), mat_rect, width=2, border_radius=self.metrics.radius + 2)
        screen.blit(canvas, crect)
        pygame.draw.rect(screen, (241, 235, 222), crect, width=1, border_radius=self.metrics.radius)

    def draw_palette(
        self,
        screen: pygame.Surface,
        selected_color: int,
        eraser: bool,
        selected_size: int,
    ) -> None:
        safe = self.metrics.activity_safe_rect()
        panel = pygame.Rect(
            safe.left + self.metrics.margin,
            safe.bottom - self.metrics.margin - self.palette_height,
            safe.width - self.metrics.margin * 2,
            self.palette_height,
        )
        tray_shadow = panel.move(0, self.metrics.px(3))
        pygame.draw.rect(screen, (214, 204, 188), tray_shadow, border_radius=self.metrics.radius + 4)
        pygame.draw.rect(screen, (255, 255, 255), panel, border_radius=self.metrics.radius)
        pygame.draw.rect(screen, (226, 218, 202), panel, width=2, border_radius=self.metrics.radius)

        scaled_dish = self._scaled_dish
        for rect, index in self._color_buttons():
            if scaled_dish is not None:
                screen.blit(scaled_dish, scaled_dish.get_rect(center=rect.center))
            else:
                dish_sz = rect.width + self.metrics.px(6)
                pygame.draw.circle(screen, (241, 245, 249), rect.center, dish_sz // 2)
                pygame.draw.circle(screen, (203, 213, 225), rect.center, dish_sz // 2, 2)
            col = COLORS[index]
            r = rect.width // 2 - self.metrics.px(2)
            pygame.draw.circle(screen, col, rect.center, r)
            pygame.draw.ellipse(screen, (255, 255, 255, 120), (rect.centerx - r // 2, rect.centery - r + 3, r, r // 2))
            if index == selected_color and not eraser:
                glow_r = rect.width // 2 + self.metrics.px(4)
                pygame.draw.circle(screen, (251, 191, 36), rect.center, glow_r, max(2, self.metrics.px(3)))
                pygame.draw.circle(screen, (255, 255, 255), rect.center, glow_r - 2, 1)

        first_size_btn = self._size_buttons()[-1][0]
        sep_x = first_size_btn.left - self.metrics.px(14)
        pygame.draw.line(screen, (226, 232, 240), (sep_x, panel.top + self.metrics.px(10)), (sep_x, panel.bottom - self.metrics.px(10)), 2)

        for rect, index in self._size_buttons():
            is_active = index == selected_size
            btn_bg = (254, 240, 138) if is_active else (248, 250, 252)
            pygame.draw.rect(screen, btn_bg, rect, border_radius=self.metrics.radius)
            b_border = (245, 158, 11) if is_active else (226, 232, 240)
            pygame.draw.rect(screen, b_border, rect, width=2, border_radius=self.metrics.radius)
            scaled_b = self._scaled_brush_icons.get(index)
            if scaled_b is not None:
                screen.blit(scaled_b, scaled_b.get_rect(center=rect.center))
            else:
                dot_r = max(self.metrics.px(3), self.metrics.px(BRUSH_SIZES[index]) // 2)
                dot_col = (245, 158, 11) if is_active else (51, 65, 85)
                pygame.draw.circle(screen, dot_col, rect.center, dot_r)

    def draw_gallery(
        self,
        screen: pygame.Surface,
        records,
        repository,
        page: int = 0,
        focus_index: int | None = None,
        library_full: bool = False,
    ) -> None:
        page_count = self.gallery_page_count(len(records))
        page = max(0, min(int(page), page_count - 1))
        scaled_frame = self._scaled_card_frame
        if not records and self.empty_icon is not None:
            screen.blit(self.empty_icon, self.empty_icon.get_rect(center=self.canvas_rect.center))
        for rect, record in self.gallery_cards(records, page):
            if scaled_frame is not None and scaled_frame.get_size() == rect.size:
                screen.blit(scaled_frame, rect)
            else:
                pygame.draw.rect(screen, (255, 255, 255), rect, border_radius=self.metrics.radius)
                pygame.draw.rect(screen, (226, 232, 240), rect, width=2, border_radius=self.metrics.radius)
            inner = rect.inflate(-self.metrics.px(24), -self.metrics.px(24))
            thumb = self.thumbnail(record, inner.size, repository)
            if thumb is None:
                if self.empty_icon is not None:
                    screen.blit(self.empty_icon, self.empty_icon.get_rect(center=rect.center))
            else:
                screen.blit(thumb, inner)
                pygame.draw.rect(screen, (226, 232, 240), inner, width=1, border_radius=self.metrics.radius // 2)
            if focus_index is not None and records[focus_index] is record:
                pygame.draw.rect(
                    screen, (234, 88, 12), rect.inflate(self.metrics.px(8), self.metrics.px(8)),
                    width=max(3, self.metrics.px(5)), border_radius=self.metrics.radius + 4,
                )
        if page_count > 1 or library_full:
            self._draw_gallery_nav(screen, page, page_count, library_full)

    def _draw_gallery_nav(self, screen: pygame.Surface, page: int, page_count: int, library_full: bool) -> None:
        """Language-free pager: big arrows, one dot per page, full-shelf badge."""
        previous, following = self.gallery_nav_buttons()
        for rect, direction, enabled in (
            (previous, -1, page > 0),
            (following, 1, page < page_count - 1),
        ):
            fill = (254, 240, 138) if enabled else (241, 245, 249)
            pygame.draw.rect(screen, (203, 213, 225), rect.move(0, self.metrics.px(3)), border_radius=self.metrics.radius)
            pygame.draw.rect(screen, fill, rect, border_radius=self.metrics.radius)
            pygame.draw.rect(screen, (245, 158, 11) if enabled else (226, 232, 240), rect, width=2, border_radius=self.metrics.radius)
            half_h = rect.height // 4
            half_w = rect.width // 6
            cx, cy = rect.center
            tip = cx + direction * half_w
            tail = cx - direction * half_w
            colour = (51, 65, 85) if enabled else (203, 213, 225)
            pygame.draw.polygon(screen, colour, [(tip, cy), (tail, cy - half_h), (tail, cy + half_h)])
        badge = None
        if library_full:
            badge = pygame.Rect(0, 0, self.metrics.px(150), self.metrics.px(44))
            badge.midleft = (previous.right + self.metrics.px(14), previous.centery)
        # One dot per page (at most 8 pages for 48 paintings).
        span_left = badge.right if badge is not None else previous.right
        dot = self.metrics.px(9)
        gap = self.metrics.px(14)
        total = page_count * dot * 2 + (page_count - 1) * gap
        x = (span_left + following.left) // 2 - total // 2 + dot
        for index in range(page_count):
            colour = (245, 158, 11) if index == page else (203, 213, 225)
            pygame.draw.circle(screen, colour, (x, previous.centery), dot if index == page else dot - 2)
            x += dot * 2 + gap
        if badge is not None:
            pygame.draw.rect(screen, (254, 226, 226), badge, border_radius=badge.height // 2)
            pygame.draw.rect(screen, (211, 61, 65), badge, width=3, border_radius=badge.height // 2)
            # Full-shelf pictogram: a 3x2 grid of filled cards and an alert dot.
            cell = self.metrics.px(10)
            left = badge.left + self.metrics.px(18)
            for index in range(6):
                row, col = divmod(index, 3)
                pygame.draw.rect(
                    screen, (211, 61, 65),
                    (left + col * (cell + 3), badge.centery - cell - 1 + row * (cell + 3), cell, cell),
                    border_radius=2,
                )
            pygame.draw.circle(screen, (211, 61, 65), (badge.right - self.metrics.px(32), badge.centery), self.metrics.px(14))
            pygame.draw.rect(screen, (255, 255, 255), (badge.right - self.metrics.px(35), badge.centery - self.metrics.px(8), self.metrics.px(6), self.metrics.px(10)), border_radius=2)
            pygame.draw.circle(screen, (255, 255, 255), (badge.right - self.metrics.px(32), badge.centery + self.metrics.px(8)), self.metrics.px(3))


# -- PNG helpers (shared with app, keeps per-frame encode at save boundary only) --

def _encode_png(surface: pygame.Surface) -> bytes:
    image = Image.frombytes("RGBA", surface.get_size(), pygame.image.tostring(surface, "RGBA"))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def _decode_png(payload: bytes, target_size: tuple[int, int]) -> pygame.Surface:
    with Image.open(io.BytesIO(payload)) as image:
        converted = image.convert("RGB")
        if converted.size != target_size:
            converted.thumbnail(target_size, Image.Resampling.BILINEAR)
            background = Image.new("RGB", target_size, (255, 255, 255))
            background.paste(converted, ((target_size[0] - converted.width) // 2, (target_size[1] - converted.height) // 2))
            converted = background
        return pygame.image.fromstring(converted.tobytes(), converted.size, "RGB").convert()


__all__ = ["PaintingRenderer", "_encode_png", "_decode_png"]
