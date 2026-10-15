"""Draw helpers, geometry and bounded caches for Writing.

Owns the desk background, the ruled paper page in its chosen colour, the
wrapped text and caret, the emoji/paper/delete sheet geometry, the gallery
cards, the word-free save status and the short feedback FX. Static surfaces
(background, page, card faces, paper icons, status icons) are prepared once
and invalidated on resize or content change; nothing in a frame decodes,
scales or constructs fonts except the bounded first use of a text line.

Interactive controls are kit controls (``writing_controls``); this module
only provides their rectangles and the Activity-drawn art beneath them.
Geometry derives from the shared ``ChildUiMetrics`` so the Activity stays
inside Greia's safe content area outside the protected Home/Back chrome.
"""

from __future__ import annotations

import bisect
from collections import OrderedDict
from dataclasses import dataclass
import time

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit, ControlTheme, mix
from greia_platform.typography import FontRole, GreiaTypography, grapheme_spans, is_emoji_cluster

if __package__:
    from .writing_content import CARD_TEXT_SIZE, GALLERY_PAGE_SIZE, PAPER_TINTS, tint_rgb
    from .writing_model import DocumentRecord, card_badge
else:  # pragma: no cover - runtime/script fallback
    from writing_content import CARD_TEXT_SIZE, GALLERY_PAGE_SIZE, PAPER_TINTS, tint_rgb
    from writing_model import DocumentRecord, card_badge

try:
    from greia_platform.activity_api import get_icon_path
except Exception:  # pragma: no cover - headless tests without display
    def get_icon_path(name: str, size: int = 64) -> str:  # type: ignore[no-redef]
        return name

INK = (75, 55, 47)
PAPER = (255, 255, 255)
DESK_TOP = (252, 246, 232)
DESK_BOTTOM = (246, 236, 214)
CORAL = (244, 111, 97)
LEAF = (89, 184, 106)
SUNSHINE = (255, 194, 52)
RULE = (120, 160, 205)

_MAX_TEXT_CACHE = 64
_MAX_CARD_FACES = 24


@dataclass(frozen=True, slots=True)
class VisualLine:
    start: int
    end: int
    text: str


class FxBurst:
    """One short shared-library FX animation (frames scaled once)."""

    DURATION = 0.7

    def __init__(self, frames: list[pygame.Surface], center: tuple[int, int], *, clock=time.monotonic) -> None:
        self._frames = frames
        self._center = center
        self._clock = clock
        self._start = clock()

    @property
    def done(self) -> bool:
        return self._clock() - self._start >= self.DURATION

    def draw(self, target: pygame.Surface) -> None:
        if not self._frames or self.done:
            return
        progress = (self._clock() - self._start) / self.DURATION
        frame = self._frames[min(len(self._frames) - 1, int(progress * len(self._frames) * 2) % len(self._frames))]
        target.blit(frame, frame.get_rect(center=self._center))


class WritingRenderer:
    """Own Writing presentation, geometry helpers and bounded caches.

    ``on_resize`` drops every display-dependent product so no stale scale
    survives a display size change. Text line surfaces, card faces and paper
    pages are LRU/size bounded; the emoji glyph cache itself is owned by the
    shared ``GreiaTypography``.
    """

    def __init__(
        self,
        typography: GreiaTypography,
        metrics,
        theme,
        emoji_palette,
        font_size: int,
        small_font_size: int,
        *,
        kit: ControlKit | None = None,
    ) -> None:
        self.typography = typography
        self.metrics = metrics
        self.theme = theme
        self.emoji_palette = emoji_palette
        self.font_size = font_size
        self.small_font_size = small_font_size
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("coral"))
        self._book_icon: pygame.Surface | None = None
        self._layout_text: str | None = None
        self._layout_width = 0
        self._lines: list[VisualLine] = []
        self._text_cache: OrderedDict[tuple[str, int], pygame.Surface] = OrderedDict()
        self._card_faces: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._pages: dict[tuple, pygame.Surface] = {}
        self._paper_icons: dict[tuple[str, int], pygame.Surface] = {}
        self._status_icons: dict[str, pygame.Surface] = {}
        self._fx_frames: dict[tuple[str, int], list[pygame.Surface]] = {}
        self._background: pygame.Surface | None = None
        self._dim: pygame.Surface | None = None
        self._load_icons()
        self._prepare()

    # -- lifecycle / invalidation ----------------------------------------

    def _load_icons(self) -> None:
        try:
            from greia_platform.activity_ui import load_icon

            self._book_icon = load_icon(get_icon_path("book", 64), self.metrics.px(40))
        except Exception:
            # Headless test path where icon assets are unavailable.
            self._book_icon = None

    def _prepare(self) -> None:
        self._status_icons = {key: self._build_status_icon(key) for key in ("saved", "saving", "error")}
        self._background = None
        self._dim = None

    def on_resize(self, metrics, font_size: int, small_font_size: int) -> None:
        """Invalidate display-dependent surfaces after a VIDEORESIZE."""
        self.metrics = metrics
        self.font_size = font_size
        self.small_font_size = small_font_size
        self.invalidate_layout()
        self._text_cache.clear()
        self._card_faces.clear()
        self._pages.clear()
        self._paper_icons.clear()
        self._fx_frames.clear()
        self._load_icons()
        self._prepare()

    @property
    def book_icon(self) -> pygame.Surface | None:
        return self._book_icon

    # -- bounded text cache ---------------------------------------------

    def _line_surface(self, text: str) -> pygame.Surface:
        key = (text, self.font_size)
        cached = self._text_cache.get(key)
        if cached is not None:
            self._text_cache.move_to_end(key)
            return cached
        rendered = self.typography.render(text, FontRole.BODY, self.font_size, INK)
        self._text_cache[key] = rendered
        while len(self._text_cache) > _MAX_TEXT_CACHE:
            self._text_cache.popitem(last=False)
        return rendered

    # -- layout -----------------------------------------------------------

    def text_origin(self, editor_rect: pygame.Rect) -> tuple[int, int]:
        """Top-left of the first text line inside the page."""
        return editor_rect.left + self.metrics.px(26), editor_rect.top + self.metrics.px(18)

    def line_height(self) -> int:
        return self.typography.line_height(FontRole.BODY, self.font_size)

    def visible_line_count(self, view_rect: pygame.Rect) -> int:
        return max(1, (view_rect.height - self.metrics.px(34)) // self.line_height())

    def layout(self, buffer_text: str, editor_rect: pygame.Rect) -> list[VisualLine]:
        """Derive wrapped visual lines for buffer_text inside editor_rect.

        Result is cached for the current buffer text and width, so a resize
        correctly re-wraps.
        """
        width = max(40, editor_rect.width - self.metrics.px(52))
        if self._layout_text == buffer_text and self._layout_width == width and self._lines:
            return self._lines
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
        self._layout_width = width
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

    # -- toolbar geometry -------------------------------------------------

    def toolbar_rect(self, name: str) -> pygame.Rect:
        slots = {"gallery": (0, "left"), "undo": (1, "left"), "emoji": (2, "left"), "new": (0, "right")}
        index, side = slots[name]
        return self.metrics.activity_toolbar_button(index, side=side)

    def status_rect(self) -> pygame.Rect:
        anchor = self.toolbar_rect("new")
        size = self.metrics.px(30)
        rect = pygame.Rect(0, 0, size, size)
        rect.midright = (anchor.left - self.metrics.px(14), anchor.centery)
        return rect

    def shared_export_button(self) -> pygame.Rect | None:
        """Child-sized share/import slot in the free centre of the safe toolbar."""
        left = self.toolbar_rect("emoji")
        right = self.status_rect()
        size = self.metrics.button_size
        candidate = pygame.Rect((self.metrics.width - size) // 2, left.y, size, size)
        if candidate.left <= left.right + self.metrics.gap or candidate.right >= right.left - self.metrics.gap:
            return None
        return candidate

    # -- sheet geometry ---------------------------------------------------

    def emoji_sheet_rects(
        self, editor_rect: pygame.Rect
    ) -> tuple[pygame.Rect, list[pygame.Rect], list[pygame.Rect]]:
        """Panel along the bottom of the page: category row, then 9x2 emoji.

        The grid starts right under the category row (no dead gap) and the
        text above the panel stays visible, so a child sees each emoji land.
        """
        metrics = self.metrics
        categories = len(self.emoji_palette.categories)
        count = max(len(category.emoji) for category in self.emoji_palette.categories)
        columns = 9
        rows = max(1, -(-count // columns))
        gap = metrics.px(8)
        pad = metrics.px(14)
        divider = metrics.px(14)
        tile = min(
            metrics.px(62),
            (editor_rect.width - metrics.px(24) - 2 * pad - (columns - 1) * gap) // columns,
        )
        tile = max(8, tile)
        width = max(columns * tile + (columns - 1) * gap, categories * tile + (categories - 1) * gap) + 2 * pad
        height = pad + tile + divider + rows * tile + (rows - 1) * gap + pad + metrics.px(4)
        panel = pygame.Rect(0, 0, width, height)
        panel.midbottom = (editor_rect.centerx, editor_rect.bottom - metrics.px(10))
        cat_width = categories * tile + (categories - 1) * gap
        cat_left = panel.centerx - cat_width // 2
        category_rects = [
            pygame.Rect(cat_left + index * (tile + gap), panel.top + pad, tile, tile) for index in range(categories)
        ]
        grid_width = columns * tile + (columns - 1) * gap
        grid_left = panel.centerx - grid_width // 2
        grid_top = panel.top + pad + tile + divider
        emoji_rects = [
            pygame.Rect(grid_left + col * (tile + gap), grid_top + row * (tile + gap), tile, tile)
            for row in range(rows)
            for col in range(columns)
        ]
        return panel, category_rects, emoji_rects

    def text_view_rect(self, editor_rect: pygame.Rect, emoji_open: bool) -> pygame.Rect:
        """The part of the page where text lines are visible."""
        if not emoji_open:
            return editor_rect
        panel, _cats, _items = self.emoji_sheet_rects(editor_rect)
        view = editor_rect.copy()
        view.height = max(self.line_height() + self.metrics.px(34), panel.top - editor_rect.top - self.metrics.px(4))
        return view

    def paper_sheet_rects(self, editor_rect: pygame.Rect) -> tuple[pygame.Rect, list[pygame.Rect]]:
        """Panel over the page with one big paper tile per colour."""
        metrics = self.metrics
        count = len(PAPER_TINTS)
        gap = metrics.px(14)
        pad = metrics.px(18)
        tile = min(metrics.px(104), (editor_rect.width - metrics.px(40) - 2 * pad - (count - 1) * gap) // count)
        columns, rows = count, 1
        if tile < metrics.px(80):
            columns, rows = 3, 2
            tile = min(metrics.px(104), (editor_rect.width - metrics.px(40) - 2 * pad - 2 * gap) // 3)
        width = columns * tile + (columns - 1) * gap + 2 * pad
        height = rows * tile + (rows - 1) * gap + 2 * pad
        panel = pygame.Rect(0, 0, width, height)
        panel.center = editor_rect.center
        tiles = [
            pygame.Rect(panel.left + pad + col * (tile + gap), panel.top + pad + row * (tile + gap), tile, tile)
            for row in range(rows)
            for col in range(columns)
        ]
        return panel, tiles[:count]

    def delete_dialog_rects(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        """Panel, cancel and confirm rects for the delete confirmation."""
        area = self.metrics.activity_safe_rect()
        width = min(area.width - self.metrics.px(40), self.metrics.px(520))
        height = min(area.height - self.metrics.px(20), self.metrics.px(420))
        panel = pygame.Rect(0, 0, width, height)
        panel.center = area.center
        button = self.metrics.px(78)
        gap = self.metrics.px(40)
        y = panel.bottom - self.metrics.px(20) - button
        cancel = pygame.Rect(panel.centerx - gap // 2 - button, y, button, button)
        confirm = pygame.Rect(panel.centerx + gap // 2, y, button, button)
        return panel, cancel, confirm

    def delete_preview_rect(self, panel: pygame.Rect) -> pygame.Rect:
        _panel, cancel, _confirm = self.delete_dialog_rects()
        top = panel.top + self.metrics.px(22)
        trash_room = self.metrics.px(64)
        height = max(self.metrics.px(40), cancel.top - self.metrics.px(16) - trash_room - top)
        width = min(panel.width - self.metrics.px(48), int(height * 1.45))
        rect = pygame.Rect(0, 0, width, height)
        rect.midtop = (panel.centerx, top)
        return rect

    # -- gallery geometry -------------------------------------------------

    @staticmethod
    def gallery_page_count(record_count: int) -> int:
        """Number of 3x2 gallery pages needed to reach every saved document."""
        return max(1, -(-int(record_count) // GALLERY_PAGE_SIZE))

    def _gallery_nav_height(self) -> int:
        return self.metrics.px(82)

    def gallery_strip(self, editor_rect: pygame.Rect) -> pygame.Rect:
        height = self._gallery_nav_height() - self.metrics.px(8)
        return pygame.Rect(editor_rect.left, editor_rect.bottom - height, editor_rect.width, height)

    def gallery_nav_buttons(self, editor_rect: pygame.Rect) -> tuple[pygame.Rect, pygame.Rect]:
        """Big previous/next arrows at the ends of the gallery strip."""
        strip = self.gallery_strip(editor_rect)
        height = self.metrics.px(62)
        width = self.metrics.px(96)
        y = strip.centery - height // 2
        inset = self.metrics.px(8)
        return (
            pygame.Rect(strip.left + inset, y, width, height),
            pygame.Rect(strip.right - inset - width, y, width, height),
        )

    def gallery_delete_button(self, editor_rect: pygame.Rect) -> pygame.Rect:
        """Delete tile for the focused card, well away from the page arrows."""
        strip = self.gallery_strip(editor_rect)
        size = self.metrics.px(62)
        _previous, following = self.gallery_nav_buttons(editor_rect)
        rect = pygame.Rect(0, 0, size, size)
        rect.midright = (following.left - self.metrics.px(56), strip.centery)
        return rect

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
        top_pad = self.metrics.px(6)
        card_w = (area.width - gap * 2) // 3
        card_h = (area.height - top_pad - gap) // 2
        page = max(0, min(int(page), self.gallery_page_count(len(records)) - 1))
        first = page * GALLERY_PAGE_SIZE
        cards: list[tuple[pygame.Rect, DocumentRecord]] = []
        for index, record in enumerate(records[first:first + GALLERY_PAGE_SIZE]):
            row, col = divmod(index, 3)
            cards.append(
                (
                    pygame.Rect(
                        area.left + col * (card_w + gap),
                        area.top + top_pad + row * (card_h + gap),
                        card_w,
                        card_h,
                    ),
                    record,
                )
            )
        return cards

    # -- art --------------------------------------------------------------

    def paper_icon(self, tint_id: str, size: int) -> pygame.Surface:
        """A small sheet of ruled paper in ``tint_id`` (2x supersampled, cached)."""
        key = (tint_id, int(size))
        cached = self._paper_icons.get(key)
        if cached is not None:
            return cached
        s = 2
        big = pygame.Surface((size * s, size * s), pygame.SRCALPHA)
        w = int(size * s * 0.70)
        h = int(size * s * 0.86)
        left = (size * s - w) // 2
        top = (size * s - h) // 2
        fold = w // 4
        outline = max(2, size * s // 22)
        body = [
            (left, top), (left + w - fold, top), (left + w, top + fold), (left + w, top + h), (left, top + h),
        ]
        pygame.draw.polygon(big, tint_rgb(tint_id), body)
        pygame.draw.polygon(big, INK, body, outline)
        flap = [(left + w - fold, top), (left + w - fold, top + fold), (left + w, top + fold)]
        pygame.draw.polygon(big, mix(tint_rgb(tint_id), INK, 0.18), flap)
        pygame.draw.polygon(big, INK, flap, outline)
        for k in range(3):
            y = top + int(h * (0.42 + 0.17 * k))
            pygame.draw.line(big, mix(RULE, PAPER, 0.15), (left + w // 6, y), (left + w - w // 6, y), max(2, outline - 1))
        surface = pygame.transform.smoothscale(big, (size, size))
        if len(self._paper_icons) >= 24:
            self._paper_icons.pop(next(iter(self._paper_icons)))
        self._paper_icons[key] = surface
        return surface

    def fx_frames(self, asset_id: str, size: int) -> list[pygame.Surface]:
        key = (asset_id, int(size))
        frames = self._fx_frames.get(key)
        if frames is None:
            frames = []
            for variant in ("default", "frame_2", "frame_3"):
                image = self.kit.art.image(asset_id, int(size), variant=variant)
                if image is not None:
                    frames.append(image)
            self._fx_frames[key] = frames
        return frames

    def _panel(self, size: tuple[int, int], fill=(255, 251, 240), *, contour: int = 4) -> pygame.Surface:
        """Kit panel body with a slim ink contour (large panels stay light)."""
        return self.kit.painter.body(
            BodyShape.PANEL, size, fill, lip=self.metrics.px(4), highlight=False,
            contour_width=max(2, self.metrics.px(contour)),
        )

    def _rule_offset(self) -> int:
        try:
            ascent = self.typography.font(FontRole.BODY, self.font_size).get_ascent()
        except Exception:  # noqa: BLE001 - degraded typography still gets rules
            ascent = int(self.font_size * 0.95)
        return ascent + self.metrics.px(8)

    def _page_surface(self, size: tuple[int, int], tint_id: str) -> pygame.Surface:
        """Paper in its colour with faint writing rules, built once per size."""
        line_height = self.line_height()
        key = (size, tint_id, line_height)
        cached = self._pages.get(key)
        if cached is not None:
            return cached
        page = self._panel(size, tint_rgb(tint_id), contour=3).copy()
        rule = mix(RULE, tint_rgb(tint_id), 0.62)
        y = self.metrics.px(18) + self._rule_offset()
        left = self.metrics.px(20)
        right = size[0] - self.metrics.px(20)
        while y < size[1] - self.metrics.px(18):
            pygame.draw.line(page, rule, (left, y), (right, y), max(1, self.metrics.px(2)))
            y += line_height
        if len(self._pages) >= 8:
            self._pages.pop(next(iter(self._pages)))
        self._pages[key] = page
        return page

    # -- drawing ----------------------------------------------------------

    def draw_background(self, screen: pygame.Surface) -> None:
        size = screen.get_size()
        if self._background is None or self._background.get_size() != size:
            background = pygame.Surface(size)
            if pygame.display.get_surface() is not None:
                background = background.convert()
            span = max(1, size[1] - 1)
            for row in range(size[1]):
                pygame.draw.line(background, mix(DESK_TOP, DESK_BOTTOM, row / span), (0, row), (size[0], row))
            self._background = background
        screen.blit(self._background, (0, 0))

    def draw_editor(
        self,
        screen: pygame.Surface,
        editor_rect: pygame.Rect,
        view_rect: pygame.Rect,
        lines: list[VisualLine],
        buffer_text: str,
        buffer_cursor: int,
        scroll_line: int,
        *,
        tint: str,
        caret_visible: bool = True,
    ) -> None:
        screen.blit(self._page_surface(editor_rect.size, tint), editor_rect.topleft)
        cursor_line_idx = self.cursor_line(buffer_cursor, lines)
        line_height = self.line_height()
        x, y = self.text_origin(editor_rect)
        visible = self.visible_line_count(view_rect)
        clip = screen.get_clip()
        screen.set_clip(view_rect.clip(clip) if clip else view_rect)
        try:
            for offset, line in enumerate(lines[scroll_line : scroll_line + visible]):
                if line.text:
                    screen.blit(self._line_surface(line.text), (x, y))
                if caret_visible and scroll_line + offset == cursor_line_idx:
                    prefix = buffer_text[line.start : buffer_cursor]
                    cursor_x = x + self.typography.prefix_width(prefix, len(prefix), FontRole.BODY, self.font_size)
                    caret = pygame.Rect(0, 0, max(3, self.metrics.px(4)), line_height - self.metrics.px(10))
                    caret.midtop = (cursor_x, y + self.metrics.px(5))
                    pygame.draw.rect(screen, CORAL, caret, border_radius=caret.width // 2)
                y += line_height
        finally:
            screen.set_clip(clip)

    def draw_sheet_panel(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        screen.blit(self._panel(panel.size), panel.topleft)

    def draw_emoji_panel(self, screen: pygame.Surface, panel: pygame.Rect, category_rects: list[pygame.Rect]) -> None:
        """Sheet body plus a soft divider between categories and emoji."""
        self.draw_sheet_panel(screen, panel)
        if category_rects:
            y = category_rects[0].bottom + self.metrics.px(7)
            pygame.draw.line(
                screen, (230, 214, 186),
                (panel.left + self.metrics.px(18), y), (panel.right - self.metrics.px(18), y),
                max(1, self.metrics.px(2)),
            )

    def draw_dim(self, screen: pygame.Surface) -> None:
        size = screen.get_size()
        if self._dim is None or self._dim.get_size() != size:
            self._dim = pygame.Surface(size, pygame.SRCALPHA)
            self._dim.fill((61, 44, 31, 120))
        screen.blit(self._dim, (0, 0))

    def draw_status(self, screen: pygame.Surface, state: str) -> None:
        icon = self._status_icons.get(state)
        if icon is not None:
            screen.blit(icon, icon.get_rect(center=self.status_rect().center))

    def _build_status_icon(self, state: str) -> pygame.Surface:
        """Word-free save state: green tick, amber dots or coral "!" (2x supersampled)."""
        size = self.metrics.px(30)
        s = 2
        big = pygame.Surface((size * s, size * s), pygame.SRCALPHA)
        c = size * s // 2
        fill = {"saved": LEAF, "saving": SUNSHINE, "error": CORAL}[state]
        pygame.draw.circle(big, INK, (c, c), c)
        pygame.draw.circle(big, fill, (c, c), c - max(2, size * s // 12))
        white = (255, 255, 255)
        u = size * s / 30
        if state == "saved":
            pygame.draw.lines(big, white, False, [(c - 7 * u, c), (c - 2 * u, c + 5 * u), (c + 7 * u, c - 5 * u)], max(2, int(4 * u)))
        elif state == "saving":
            for dx in (-7, 0, 7):
                pygame.draw.circle(big, white, (int(c + dx * u), c), max(1, int(2.6 * u)))
        else:
            pygame.draw.rect(big, white, (int(c - 2 * u), int(c - 9 * u), int(4 * u), int(11 * u)), border_radius=int(2 * u))
            pygame.draw.circle(big, white, (c, int(c + 7 * u)), max(1, int(2.4 * u)))
        return pygame.transform.smoothscale(big, (size, size))

    # -- gallery ------------------------------------------------------------

    def card_face(self, record: DocumentRecord, size: tuple[int, int]) -> pygame.Surface:
        """One page card: its paper colour, a big identity glyph, the first words.

        Composed once per (record content, size) into a bounded LRU so the
        gallery never measures or wraps words per frame.
        """
        key = (record.document_id, record.preview, record.tint, size)
        cached = self._card_faces.get(key)
        if cached is not None:
            self._card_faces.move_to_end(key)
            return cached
        metrics = self.metrics
        face = self.kit.painter.body(
            BodyShape.TILE, size, tint_rgb(record.tint), lip=metrics.px(5), highlight=False,
            contour_width=max(2, metrics.px(4)),
        ).copy()
        inner = pygame.Rect(metrics.px(14), metrics.px(12), size[0] - metrics.px(28), size[1] - metrics.px(30))
        badge = card_badge(record.preview)
        y = inner.top
        if badge:
            glyph_size = metrics.px(60)
            role = FontRole.BODY if is_emoji_cluster(badge) else FontRole.DISPLAY
            glyph = self.typography.render(badge, role, glyph_size, CORAL if role is FontRole.DISPLAY else INK)
            face.blit(glyph, (inner.left, y))
            y += max(glyph.get_height(), metrics.px(62)) + metrics.px(2)
        else:
            icon = self.paper_icon(record.tint, metrics.px(56))
            face.blit(icon, (inner.left, y))
            y += icon.get_height() + metrics.px(2)
        text_size = metrics.px(CARD_TEXT_SIZE)
        line_height = self.typography.line_height(FontRole.BODY, text_size)
        rule = mix(RULE, tint_rgb(record.tint), 0.62)
        for line in self._wrap(record.preview, inner.width, text_size):
            if y + line_height > inner.bottom:
                break
            face.blit(self.typography.render(line, FontRole.BODY, text_size, INK), (inner.left, y), area=pygame.Rect(0, 0, inner.width, line_height))
            pygame.draw.line(face, rule, (inner.left, y + line_height - metrics.px(3)), (inner.right, y + line_height - metrics.px(3)), 1)
            y += line_height
        self._card_faces[key] = face
        while len(self._card_faces) > _MAX_CARD_FACES:
            self._card_faces.popitem(last=False)
        return face

    def _wrap(self, text: str, width: int, size: int) -> list[str]:
        """Greedy word wrap; an over-long word is cut at a grapheme boundary."""
        lines: list[str] = []
        line = ""
        for word in text.split():
            candidate = f"{line} {word}".strip()
            if self.typography.measure(candidate, FontRole.BODY, size).width <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
            line = ""
            for span in grapheme_spans(word):
                candidate = line + span.text
                if line and self.typography.measure(candidate, FontRole.BODY, size).width > width:
                    lines.append(line)
                    line = span.text
                else:
                    line = candidate
            if len(lines) >= 6:
                break
        if line:
            lines.append(line)
        return lines[:6]

    def invalidate_card(self, document_id: str) -> None:
        for key in [key for key in self._card_faces if key[0] == document_id]:
            self._card_faces.pop(key, None)

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
        strip = self.gallery_strip(editor_rect)
        screen.blit(self._panel((strip.width, strip.height + self.metrics.px(4))), strip.topleft)
        if not records:
            self._draw_empty_gallery(screen, editor_rect)
        for rect, record in self.gallery_cards(editor_rect, records, page):
            if focus_index is not None and 0 <= focus_index < len(records) and records[focus_index] is record:
                ring = rect.inflate(self.metrics.px(10), self.metrics.px(10))
                pygame.draw.rect(screen, INK, ring, border_radius=self.metrics.radius + 6)
                pygame.draw.rect(screen, SUNSHINE, ring.inflate(-max(2, self.metrics.px(3)) * 2, -max(2, self.metrics.px(3)) * 2), border_radius=self.metrics.radius + 4)
            screen.blit(self.card_face(record, rect.size), rect.topleft)
        self._draw_page_dots(screen, editor_rect, page, page_count, library_full)

    def _draw_empty_gallery(self, screen: pygame.Surface, editor_rect: pygame.Rect) -> None:
        """An empty shelf shows one waiting blank page."""
        area = editor_rect.copy()
        area.height -= self._gallery_nav_height()
        card = pygame.Rect(0, 0, area.width // 3, (area.height * 2) // 3)
        card.center = area.center
        screen.blit(self.kit.painter.body(BodyShape.TILE, card.size, (255, 251, 240), lip=self.metrics.px(5)), card.topleft)
        icon = self.paper_icon("cream", min(card.width, card.height) // 2)
        screen.blit(icon, icon.get_rect(center=card.center))

    def _draw_page_dots(
        self, screen: pygame.Surface, editor_rect: pygame.Rect, page: int, page_count: int, library_full: bool,
    ) -> None:
        """Language-free pager dots plus the full-shelf pictogram."""
        previous, _following = self.gallery_nav_buttons(editor_rect)
        delete = self.gallery_delete_button(editor_rect)
        left = previous.right + self.metrics.px(16)
        if library_full:
            self._draw_full_badge(screen, left, previous.centery)
            left += self.metrics.px(150) + self.metrics.px(16)
        if page_count <= 1:
            return
        span = delete.left - self.metrics.px(16) - left
        dot = self.metrics.px(9)
        # Shrink spacing (and then dots) so 20 pages (120 documents) still fit.
        gap = max(self.metrics.px(3), min(self.metrics.px(12), (span - page_count * dot * 2) // max(1, page_count - 1)))
        if page_count * dot * 2 + (page_count - 1) * gap > span:
            dot = max(2, (span - (page_count - 1) * gap) // (page_count * 2))
        total = page_count * dot * 2 + (page_count - 1) * gap
        x = left + max(0, (span - total) // 2) + dot
        for index in range(page_count):
            current = index == page
            radius = dot if current else max(2, dot - 2)
            pygame.draw.circle(screen, INK, (x, previous.centery), radius)
            pygame.draw.circle(screen, CORAL if current else (236, 224, 200), (x, previous.centery), max(1, radius - max(1, self.metrics.px(2))))
            x += dot * 2 + gap

    def _draw_full_badge(self, screen: pygame.Surface, left: int, centery: int) -> None:
        badge = pygame.Rect(0, 0, self.metrics.px(150), self.metrics.px(48))
        badge.midleft = (left, centery)
        screen.blit(self.kit.painter.body(BodyShape.PILL, badge.size, (250, 214, 208), lip=0, highlight=False), badge.topleft)
        cell = self.metrics.px(11)
        x0 = badge.left + self.metrics.px(20)
        for index in range(6):
            row, col = divmod(index, 3)
            pygame.draw.rect(
                screen, CORAL,
                (x0 + col * (cell + 3), badge.centery - cell - 1 + row * (cell + 3), cell, cell),
                border_radius=2,
            )
        cx = badge.right - self.metrics.px(30)
        pygame.draw.circle(screen, INK, (cx, badge.centery), self.metrics.px(15))
        pygame.draw.circle(screen, CORAL, (cx, badge.centery), self.metrics.px(13))
        pygame.draw.rect(screen, PAPER, (cx - self.metrics.px(2), badge.centery - self.metrics.px(8), self.metrics.px(5), self.metrics.px(10)), border_radius=2)
        pygame.draw.circle(screen, PAPER, (cx, badge.centery + self.metrics.px(7)), self.metrics.px(2) + 1)

    def draw_delete_dialog(self, screen: pygame.Surface, panel: pygame.Rect, preview: pygame.Surface | None) -> None:
        """Dim + panel with the page card itself, so the child sees *what* would go."""
        self.draw_dim(screen)
        screen.blit(self._panel(panel.size), panel.topleft)
        face = panel.inflate(-self.metrics.px(28), -self.metrics.px(28))
        thumb_rect = self.delete_preview_rect(panel)
        if preview is not None:
            screen.blit(preview, preview.get_rect(center=thumb_rect.center))
        trash = self.kit.glyph("trash", min(face.height - thumb_rect.height, self.metrics.px(60)))
        if trash is not None:
            screen.blit(trash, trash.get_rect(midtop=(face.centerx, thumb_rect.bottom + self.metrics.px(4))))


__all__ = ["FxBurst", "VisualLine", "WritingRenderer"]
