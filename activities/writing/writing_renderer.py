"""Draw helpers and bounded caches for Writing.

Owns pre-scaled icons, bounded text caches and layout derivation.
No storage or event IO. Geometry is derived from the shared
ChildUiMetrics so the Activity stays inside Greia's safe content
area.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

import pygame

from greia_platform.activity_ui import draw_icon_button, draw_plus_symbol, draw_undo_symbol, load_icon, mix
from greia_platform.typography import FontRole, GreiaTypography, grapheme_spans

if __package__:
    from .writing_content import GALLERY_PAGE_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .writing_model import DocumentRecord
else:  # pragma: no cover - runtime/script fallback
    from writing_content import GALLERY_PAGE_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from writing_model import DocumentRecord

try:
    from greia_platform.activity_api import get_icon_path
except Exception:  # pragma: no cover - headless tests without display
    def get_icon_path(name: str, size: int = 64) -> str:  # type: ignore[no-redef]
        return name

_MAX_TEXT_CACHE = 64
_MAX_GALLERY_TEXT_CACHE = 64


@dataclass(frozen=True, slots=True)
class VisualLine:
    start: int
    end: int
    text: str


class WritingRenderer:
    """Own Writing presentation, geometry helpers and bounded caches.

    Static chrome (toolbar icons, empty-gallery star) is prepared once
    via ``load_icon`` / ``convert_alpha`` and invalidated on resize so a
    display-size change never leaves a stale scale. Per-frame font/scale
    work is avoided via small LRU caches.
    """

    def __init__(
        self,
        typography: GreiaTypography,
        metrics,
        theme,
        emoji_palette,
        font_size: int,
        small_font_size: int,
    ) -> None:
        self.typography = typography
        self.metrics = metrics
        self.theme = theme
        self.emoji_palette = emoji_palette
        self.font_size = font_size
        self.small_font_size = small_font_size
        # Bounded caches.
        self._book_icon: pygame.Surface | None = None
        self._empty_icon: pygame.Surface | None = None
        self._icon_converted = False
        self._layout_text: str | None = None
        self._lines: list[VisualLine] = []
        self._text_cache: dict[tuple[str, FontRole, int, tuple[int, int, int]], pygame.Surface] = {}
        self._text_order: list[tuple[str, FontRole, int, tuple[int, int, int]]] = []
        self._gallery_text_cache: dict[tuple[str, int], pygame.Surface] = {}
        self._gallery_order: list[tuple[str, int]] = []
        self._load_icons()

    # -- lifecycle / invalidation ----------------------------------------

    def _load_icons(self) -> None:
        try:
            icon_size = self.metrics.px(42)
            self._book_icon = load_icon(get_icon_path("book", 64), icon_size)
            self._empty_icon = load_icon(get_icon_path("yellow_star", 64), self.metrics.px(46))
            # load_icon already convert_alpha's via bounded global cache; ensure convert once.
            self._icon_converted = pygame.display.get_surface() is not None
        except Exception:
            # Headless test path where pygame display or icon assets are unavailable.
            self._book_icon = None
            self._empty_icon = None
            self._icon_converted = False

    def on_resize(self, metrics, font_size: int, small_font_size: int) -> None:
        """Invalidate display-dependent surfaces after a VIDEORESIZE."""
        self.metrics = metrics
        self.font_size = font_size
        self.small_font_size = small_font_size
        self._layout_text = None
        self._lines = []
        self._text_cache.clear()
        self._text_order.clear()
        self._gallery_text_cache.clear()
        self._gallery_order.clear()
        self._icon_converted = False
        self._load_icons()

    def _ensure_converted(self) -> None:
        if not self._icon_converted and pygame.display.get_surface() is not None:
            try:
                if self._book_icon is not None:
                    self._book_icon = self._book_icon.convert_alpha()
                if self._empty_icon is not None:
                    self._empty_icon = self._empty_icon.convert_alpha()
                self._icon_converted = True
            except pygame.error:
                pass

    # -- bounded text cache helpers --------------------------------------

    def _cached_text(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int],
    ) -> pygame.Surface:
        key = (text, role, size, color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        rendered = self.typography.render(text, role, size, color)
        if len(self._text_cache) >= _MAX_TEXT_CACHE:
            oldest = self._text_order.pop(0)
            self._text_cache.pop(oldest, None)
        self._text_cache[key] = rendered
        self._text_order.append(key)
        return rendered

    def _cached_gallery_text(self, text: str, color: tuple[int, int, int]) -> pygame.Surface:
        key = (text, self.small_font_size)
        cached = self._gallery_text_cache.get(key)
        if cached is not None:
            return cached
        rendered = self.typography.render(text, FontRole.BODY, self.small_font_size, color)
        if len(self._gallery_text_cache) >= _MAX_GALLERY_TEXT_CACHE:
            oldest = self._gallery_order.pop(0)
            self._gallery_text_cache.pop(oldest, None)
        self._gallery_text_cache[key] = rendered
        self._gallery_order.append(key)
        return rendered

    # -- layout -----------------------------------------------------------

    def layout(self, buffer_text: str, editor_rect: pygame.Rect) -> list[VisualLine]:
        """Derive wrapped visual lines for buffer_text inside editor_rect.

        Result is cached for the current buffer text; callers must pass
        the up-to-date editor_rect so a resize correctly re-wraps.
        """
        if self._layout_text == buffer_text and self._lines:
            return self._lines
        width = max(40, editor_rect.width - self.metrics.px(52))
        spans = grapheme_spans(buffer_text)
        starts = [span.start for span in spans]
        lines: list[VisualLine] = []
        line_start = 0
        line_width = 0
        last_space_end: int | None = None
        index = 0
        while index < len(spans):
            span = spans[index]
            if span.text == "\n":
                lines.append(VisualLine(line_start, span.start, buffer_text[line_start:span.start]))
                line_start = span.end
                line_width = 0
                last_space_end = None
                index += 1
                continue
            cluster_width = max(
                1,
                self.typography.measure(span.text, FontRole.BODY, self.font_size).width,
            )
            if span.text.isspace():
                last_space_end = span.end
            if line_width + cluster_width > width and span.start > line_start:
                wrap = last_space_end if last_space_end is not None and last_space_end > line_start else span.start
                lines.append(VisualLine(line_start, wrap, buffer_text[line_start:wrap].rstrip("\n")))
                line_start = wrap
                line_width = 0
                last_space_end = None
                index = bisect.bisect_left(starts, wrap)
                continue
            line_width += cluster_width
            index += 1
        lines.append(VisualLine(line_start, len(buffer_text), buffer_text[line_start:]))
        self._layout_text = buffer_text
        self._lines = lines
        return lines

    def invalidate_layout(self) -> None:
        self._layout_text = None
        self._lines = []

    def cursor_line(self, buffer_cursor: int, lines: list[VisualLine]) -> int:
        for idx in range(len(lines) - 1, -1, -1):
            line = lines[idx]
            if line.start <= buffer_cursor <= line.end:
                return idx
        return max(0, len(lines) - 1)

    # -- geometry helpers -------------------------------------------------

    @staticmethod
    def gallery_page_count(record_count: int) -> int:
        """Number of 3x2 gallery pages needed to reach every saved document."""
        return max(1, -(-int(record_count) // GALLERY_PAGE_SIZE))

    def _gallery_nav_height(self) -> int:
        return self.metrics.px(78)

    def gallery_nav_buttons(self, editor_rect: pygame.Rect) -> tuple[pygame.Rect, pygame.Rect]:
        """Big previous/next arrows along the bottom edge of the gallery."""
        height = self.metrics.px(62)
        width = self.metrics.px(96)
        y = editor_rect.bottom - height
        return (
            pygame.Rect(editor_rect.left, y, width, height),
            pygame.Rect(editor_rect.right - width, y, width, height),
        )

    def gallery_cards(
        self,
        editor_rect: pygame.Rect,
        records: list[DocumentRecord],
        page: int = 0,
    ) -> list[tuple[pygame.Rect, DocumentRecord]]:
        """Return the hit rectangles for one gallery page (default: first)."""
        area = editor_rect.copy()
        area.height -= self._gallery_nav_height()
        gap = self.metrics.px(18)
        card_w = (area.width - gap * 2) // 3
        card_h = (area.height - gap) // 2
        page = max(0, min(int(page), self.gallery_page_count(len(records)) - 1))
        first = page * GALLERY_PAGE_SIZE
        cards: list[tuple[pygame.Rect, DocumentRecord]] = []
        for index, record in enumerate(records[first:first + GALLERY_PAGE_SIZE]):
            row, col = divmod(index, 3)
            cards.append(
                (
                    pygame.Rect(
                        area.left + col * (card_w + gap),
                        area.top + row * (card_h + gap),
                        card_w,
                        card_h,
                    ),
                    record,
                )
            )
        return cards

    def emoji_picker_layout(
        self, editor_rect: pygame.Rect
    ) -> tuple[list[pygame.Rect], list[tuple[pygame.Rect, str]]]:
        area = editor_rect.inflate(-self.metrics.px(28), -self.metrics.px(24))
        gap = self.metrics.px(8)
        categories = self.emoji_palette.categories
        category_height = min(self.metrics.px(54), max(1, area.height // 6))
        category_width = max(
            1,
            min(self.metrics.px(58), (area.width - gap * (len(categories) - 1)) // len(categories)),
        )
        total_category_width = category_width * len(categories) + gap * (len(categories) - 1)
        category_left = area.centerx - total_category_width // 2
        category_rects = [
            pygame.Rect(
                category_left + index * (category_width + gap),
                area.top,
                category_width,
                category_height,
            )
            for index in range(len(categories))
        ]
        grid_top = area.top + category_height + self.metrics.px(18)
        emoji_count = len(self.emoji_palette.selected.emoji)
        columns = 6 if area.width >= self.metrics.px(500) else 5
        rows = max(1, (emoji_count + columns - 1) // columns)
        available_height = max(1, area.bottom - grid_top)
        cell = max(
            1,
            min(
                self.metrics.px(72),
                (area.width - gap * (columns - 1)) // columns,
                (available_height - gap * (rows - 1)) // rows,
            ),
        )
        total_width = columns * cell + gap * (columns - 1)
        total_height = rows * cell + gap * (rows - 1)
        grid_left = area.centerx - total_width // 2
        grid_top += max(0, (available_height - total_height) // 2)
        items: list[tuple[pygame.Rect, str]] = []
        for idx, cluster in enumerate(self.emoji_palette.selected.emoji):
            row, column = divmod(idx, columns)
            items.append(
                (
                    pygame.Rect(
                        grid_left + column * (cell + gap),
                        grid_top + row * (cell + gap),
                        cell,
                        cell,
                    ),
                    cluster,
                )
            )
        return category_rects, items

    # -- drawing ----------------------------------------------------------

    def draw_toolbar(
        self,
        screen: pygame.Surface,
        undo_history,
        emoji_picker_open: bool,
        mode: str,
        *,
        shared_available: bool = False,
        shared_state: str = "",
    ) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        self._ensure_converted()
        gallery = self.metrics.activity_toolbar_button(0, side="left")
        undo = self.metrics.activity_toolbar_button(1, side="left")
        emoji = self.metrics.activity_toolbar_button(2, side="left")
        new = self.metrics.activity_toolbar_button(0, side="right")
        shared = self.metrics.activity_toolbar_button(1, side="right")
        draw_icon_button(
            screen,
            gallery,
            fill=self.theme.panel,
            icon=self._book_icon,
            selected=mode == "gallery",
            outline=self.theme.accent,
        )
        undo_fill = (
            self.theme.panel if mode == "edit" and undo_history else mix(self.theme.panel, self.theme.background, 0.35)
        )
        draw_icon_button(screen, undo, fill=undo_fill)
        draw_undo_symbol(screen, undo, self.theme.text)
        emoji_fill = self.theme.accent if emoji_picker_open and mode == "edit" else self.theme.panel
        draw_icon_button(
            screen,
            emoji,
            fill=emoji_fill,
            selected=emoji_picker_open and mode == "edit",
            outline=self.theme.accent,
        )
        smile = self._cached_text("😊", FontRole.BODY, self.metrics.px(38), self.theme.text)
        screen.blit(smile, smile.get_rect(center=emoji.center))
        draw_icon_button(screen, new, fill=self.theme.accent)
        draw_plus_symbol(screen, new, self.theme.accent_text)
        if shared_available:
            active = shared_state in {"pending", "saved", "imported"}
            fill = (
                mix(self.theme.accent, self.theme.panel, 0.42)
                if active
                else self.theme.panel
            )
            draw_icon_button(
                screen,
                shared,
                fill=fill,
                selected=shared_state == "pending",
                outline=(210, 76, 76)
                if shared_state == "error"
                else self.theme.accent,
            )
            cx, cy = shared.center
            # Paper outline + direction arrow: up publishes, down imports.
            paper = pygame.Rect(
                cx - self.metrics.px(13),
                cy - self.metrics.px(10),
                self.metrics.px(26),
                self.metrics.px(23),
            )
            pygame.draw.rect(
                screen,
                self.theme.text,
                paper,
                width=max(2, self.metrics.px(2)),
                border_radius=max(2, self.metrics.px(3)),
            )
            direction = -1 if mode == "edit" else 1
            pygame.draw.line(
                screen,
                self.theme.text,
                (cx, cy - direction * self.metrics.px(16)),
                (cx, cy + direction * self.metrics.px(2)),
                max(3, self.metrics.px(3)),
            )
            tip_y = cy + direction * self.metrics.px(3)
            pygame.draw.lines(
                screen,
                self.theme.text,
                False,
                [
                    (
                        cx - self.metrics.px(7),
                        tip_y - direction * self.metrics.px(7),
                    ),
                    (cx, tip_y),
                    (
                        cx + self.metrics.px(7),
                        tip_y - direction * self.metrics.px(7),
                    ),
                ],
                max(3, self.metrics.px(3)),
            )
        return gallery, undo, emoji, new, shared

    def draw_editor(
        self,
        screen: pygame.Surface,
        editor_rect: pygame.Rect,
        lines: list[VisualLine],
        buffer_text: str,
        buffer_cursor: int,
        scroll_line: int,
    ) -> None:
        pygame.draw.rect(
            screen,
            mix(self.theme.panel, (255, 255, 255), 0.58),
            editor_rect,
            border_radius=self.metrics.radius,
        )
        cursor_line_idx = self.cursor_line(buffer_cursor, lines)
        line_height = self.typography.line_height(FontRole.BODY, self.font_size)
        x = editor_rect.left + self.metrics.px(26)
        y = editor_rect.top + self.metrics.px(18)
        visible = max(1, (editor_rect.height - self.metrics.px(34)) // line_height)
        visible_lines = lines[scroll_line : scroll_line + visible]
        for offset, line in enumerate(visible_lines):
            if line.text:
                rendered = self._cached_text(line.text, FontRole.BODY, self.font_size, self.theme.text)
                screen.blit(rendered, (x, y))
            if scroll_line + offset == cursor_line_idx:
                prefix = buffer_text[line.start : buffer_cursor]
                cursor_x = x + self.typography.prefix_width(prefix, len(prefix), FontRole.BODY, self.font_size)
                pygame.draw.line(
                    screen,
                    self.theme.accent,
                    (cursor_x, y + 4),
                    (cursor_x, y + line_height - 5),
                    max(2, self.metrics.px(3)),
                )
            y += line_height

    def draw_emoji_picker(self, screen: pygame.Surface, editor_rect: pygame.Rect) -> None:
        panel = editor_rect
        pygame.draw.rect(
            screen,
            mix(self.theme.panel, (255, 255, 255), 0.18),
            panel,
            border_radius=self.metrics.radius,
        )
        category_rects, items = self.emoji_picker_layout(editor_rect)
        for idx, rect in enumerate(category_rects):
            selected = idx == self.emoji_palette.selected_index
            pygame.draw.rect(
                screen,
                self.theme.accent if selected else self.theme.background,
                rect,
                border_radius=max(8, self.metrics.radius // 2),
            )
            icon = self._cached_text(
                self.emoji_palette.categories[idx].icon,
                FontRole.BODY,
                max(8, min(rect.height - self.metrics.px(8), self.metrics.px(34))),
                self.theme.text,
            )
            screen.blit(icon, icon.get_rect(center=rect.center))
        for rect, cluster in items:
            pygame.draw.rect(
                screen,
                self.theme.background,
                rect,
                border_radius=max(4, min(9, self.metrics.radius // 2)),
            )
            rendered = self._cached_text(
                cluster,
                FontRole.BODY,
                max(8, min(self.metrics.px(46), int(rect.height * 0.62))),
                self.theme.text,
            )
            screen.blit(rendered, rendered.get_rect(center=rect.center))

    def draw_gallery(
        self,
        screen: pygame.Surface,
        editor_rect: pygame.Rect,
        records: list[DocumentRecord],
        page: int = 0,
        focus_index: int | None = None,
        library_full: bool = False,
    ) -> None:
        page_count = self.gallery_page_count(len(records))
        page = max(0, min(int(page), page_count - 1))
        for rect, record in self.gallery_cards(editor_rect, records, page):
            pygame.draw.rect(screen, self.theme.panel, rect, border_radius=self.metrics.radius)
            if focus_index is not None and records[focus_index] is record:
                pygame.draw.rect(
                    screen, self.theme.accent, rect.inflate(self.metrics.px(8), self.metrics.px(8)),
                    width=max(3, self.metrics.px(5)), border_radius=self.metrics.radius + 4,
                )
            if not record.preview:
                if self._empty_icon is not None:
                    screen.blit(self._empty_icon, self._empty_icon.get_rect(center=rect.center))
                continue
            words = record.preview.split()
            line = ""
            y = rect.top + self.metrics.px(22)
            max_width = rect.width - self.metrics.px(30)
            line_height = self.typography.line_height(FontRole.BODY, self.small_font_size)
            for word in words:
                candidate = f"{line} {word}".strip()
                if (
                    line
                    and self.typography.measure(candidate, FontRole.BODY, self.small_font_size).width > max_width
                ):
                    screen.blit(
                        self._cached_gallery_text(line, self.theme.text),
                        (rect.left + self.metrics.px(16), y),
                    )
                    y += line_height
                    line = word
                    if y > rect.bottom - line_height * 2:
                        break
                else:
                    line = candidate
            if line and y < rect.bottom - line_height:
                screen.blit(
                    self._cached_gallery_text(line, self.theme.text),
                    (rect.left + self.metrics.px(16), y),
                )
        if page_count > 1 or library_full:
            self._draw_gallery_nav(screen, editor_rect, page, page_count, library_full)

    def _draw_gallery_nav(
        self,
        screen: pygame.Surface,
        editor_rect: pygame.Rect,
        page: int,
        page_count: int,
        library_full: bool,
    ) -> None:
        """Language-free pager: big arrows, one dot per page, full-shelf badge."""
        previous, following = self.gallery_nav_buttons(editor_rect)
        for rect, direction, enabled in (
            (previous, -1, page > 0),
            (following, 1, page < page_count - 1),
        ):
            fill = self.theme.accent if enabled else mix(self.theme.panel, self.theme.background, 0.35)
            pygame.draw.rect(screen, fill, rect, border_radius=self.metrics.radius)
            half_h = rect.height // 4
            half_w = rect.width // 6
            cx, cy = rect.center
            tip = cx + direction * half_w
            tail = cx - direction * half_w
            colour = self.theme.accent_text if enabled else mix(self.theme.text, self.theme.background, 0.6)
            pygame.draw.polygon(screen, colour, [(tip, cy), (tail, cy - half_h), (tail, cy + half_h)])
        badge = None
        if library_full:
            badge = pygame.Rect(0, 0, self.metrics.px(150), self.metrics.px(44))
            badge.midleft = (previous.right + self.metrics.px(14), previous.centery)
        # One dot per page; shrink the spacing so 20 pages (120 documents) fit.
        span_left = badge.right if badge is not None else previous.right
        room = following.left - span_left - self.metrics.px(40)
        dot = self.metrics.px(7)
        gap = max(self.metrics.px(3), min(self.metrics.px(12), (room - page_count * dot * 2) // max(1, page_count - 1)))
        total = page_count * dot * 2 + (page_count - 1) * gap
        x = (span_left + following.left) // 2 - total // 2 + dot
        for index in range(page_count):
            colour = self.theme.accent if index == page else mix(self.theme.panel, self.theme.text, 0.25)
            pygame.draw.circle(screen, colour, (x, previous.centery), dot if index == page else dot - 2)
            x += dot * 2 + gap
        if badge is not None:
            pygame.draw.rect(screen, (254, 226, 226), badge, border_radius=badge.height // 2)
            pygame.draw.rect(screen, (211, 61, 65), badge, width=3, border_radius=badge.height // 2)
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


__all__ = ["VisualLine", "WritingRenderer"]
