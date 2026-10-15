"""Draw helpers, geometry and bounded caches for Painting.

Owns the studio background, the canvas frame, the paint tray, the gallery
cards, the word-free save status, stamp art, colouring-page outlines and the
short feedback FX. Static surfaces are prepared once and invalidated on
resize; nothing in a draw call decodes, scales or constructs fonts except the
bounded first use of a thumbnail/stamp size.

Interactive controls are kit controls (``painting_controls``); this module
only provides their rectangles and the Activity-drawn art beneath them.
"""

from __future__ import annotations

from collections import OrderedDict
import io
from pathlib import Path
import time

from PIL import Image
import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlKit, ControlTheme, mix
from greia_platform.typography import GreiaTypography

if __package__:
    from .painting_content import COLORS, COLOURING_PAGES, GALLERY_PAGE_SIZE, STAMP_SIZES
    from .painting_model import Stamp, Stroke
else:  # pragma: no cover - runtime/script fallback
    from painting_content import COLORS, COLOURING_PAGES, GALLERY_PAGE_SIZE, STAMP_SIZES
    from painting_model import Stamp, Stroke

ASSET_DIR = Path(__file__).parent / "assets" / "runtime"
INK = (75, 55, 47)
PAPER = (255, 255, 255)
STUDIO_TOP = (252, 246, 232)
STUDIO_BOTTOM = (246, 236, 214)
CORAL = (244, 111, 97)
LEAF = (89, 184, 106)
SUNSHINE = (255, 194, 52)


class StampArt:
    """Shared-library stamp art scaled once per (stamp, size).

    Sources are resolved semantically through the shared visual catalogue
    (``ControlArt``), never by browsing files. Bounded: 12 stamps × 3 sizes
    plus one picker size fits the 48-entry cache.
    """

    def __init__(self, art: ControlArt | None = None) -> None:
        self._art = art if art is not None else ControlArt(max_entries=48)

    def image(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self._art.image(asset_id, int(size))

    def clear(self) -> None:
        self._art.clear()


class OutlineArt:
    """Colouring-page line art (Activity-private runtime PNGs).

    ``overlay`` reproduces exactly the placement a saved painting got: the
    page is fitted into the PNG's own size first and that picture is then
    fitted into the current canvas, the same transform ``_decode_png`` applies
    to the saved bytes. The outline therefore sits on its baked copy even
    after a resolution change.
    """

    def __init__(self, asset_dir: Path = ASSET_DIR) -> None:
        self._dir = asset_dir
        self._sources: dict[str, pygame.Surface | None] = {}

    def available(self) -> tuple[str, ...]:
        return tuple(page for page in COLOURING_PAGES if self._source(page) is not None)

    def _source(self, page: str) -> pygame.Surface | None:
        if page not in COLOURING_PAGES:
            return None
        if page not in self._sources:
            try:
                surface = pygame.image.load(str(self._dir / f"colouring_{page}.png"))
                if pygame.display.get_surface() is not None:
                    surface = surface.convert_alpha()
            except (pygame.error, FileNotFoundError, OSError):
                surface = None
            self._sources[page] = surface
        return self._sources[page]

    def overlay(
        self,
        page: str,
        canvas_size: tuple[int, int],
        *,
        png_size: tuple[int, int] | None = None,
    ) -> pygame.Surface | None:
        source = self._source(page)
        if source is None:
            return None
        base = png_size or canvas_size
        first = _fit_alpha(source, base)
        return first if base == canvas_size else _fit_alpha(first, canvas_size)

    def preview(self, page: str, size: tuple[int, int]) -> pygame.Surface | None:
        """White card with the outline, for the colouring-page picker."""

        source = self._source(page)
        if source is None:
            return None
        card = pygame.Surface(size)
        card.fill(PAPER)
        card.blit(_fit_alpha(source, size), (0, 0))
        return card


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


class PaintingRenderer:
    """Own Painting presentation, geometry helpers and bounded caches.

    All expensive image/scale work is prepared once in ``_prepare`` and on
    first use of a bounded key. ``on_resize`` drops display-dependent caches
    so no stale scale survives a display size change. Thumbnail decoding is
    bounded by the library bound (48) and invalidated per painting on save.
    """

    THUMBNAIL_LIMIT = 48

    def __init__(
        self,
        metrics,
        theme,
        screen: pygame.Surface,
        *,
        kit: ControlKit | None = None,
        status_labels: dict[str, str] | None = None,  # noqa: ARG002 - legacy keyword, status is word-free
    ) -> None:
        self.metrics = metrics
        self.theme = theme
        self.screen = screen
        self.kit = kit if kit is not None else ControlKit(GreiaTypography(), ControlTheme.for_accent("coral"))
        self.stamps = StampArt()
        self.outlines = OutlineArt()
        self.assets: dict[str, pygame.Surface] = {}
        self._background_surface: pygame.Surface | None = None
        self._scaled_dish: pygame.Surface | None = None
        self._status_icons: dict[str, pygame.Surface] = {}
        self._fx_frames: dict[tuple[str, int], list[pygame.Surface]] = {}
        # LRU over painting ids, hard-bounded by the library bound (48).
        self.thumbnail_cache: OrderedDict[str, pygame.Surface] = OrderedDict()
        self._load_assets()
        self._prepare()

    # -- lifecycle / invalidation ----------------------------------------

    def _load_assets(self) -> None:
        for name in ("tool_gallery", "tool_colouring", "color_well_dish"):
            path = ASSET_DIR / f"{name}.png"
            if not path.exists():
                continue
            try:
                surface = pygame.image.load(str(path))
                if pygame.display.get_surface() is not None:
                    surface = surface.convert_alpha()
                self.assets[name] = surface
            except pygame.error:
                pass

    def _prepare(self) -> None:
        metrics = self.metrics
        dish = self.assets.get("color_well_dish")
        dish_size = metrics.px(46) + metrics.px(6)
        self._scaled_dish = pygame.transform.smoothscale(dish, (dish_size, dish_size)) if dish is not None else None
        w, h = self.screen.get_size()
        background = pygame.Surface((w, h))
        if pygame.display.get_surface() is not None:
            background = background.convert()
        span = max(1, h - 1)
        for row in range(h):
            pygame.draw.line(background, mix(STUDIO_TOP, STUDIO_BOTTOM, row / span), (0, row), (w, row))
        line_y = self.canvas_rect.top - metrics.px(8)
        if line_y > 0:
            pygame.draw.line(background, (236, 224, 200), (0, line_y), (w, line_y), max(1, metrics.px(2)))
        self._background_surface = background
        self._status_icons = {key: self._build_status_icon(key) for key in ("saved", "saving", "error")}
        self._fx_frames.clear()

    def on_resize(self, metrics, screen: pygame.Surface) -> None:
        """Invalidate display-dependent surfaces after a resize."""
        self.metrics = metrics
        self.screen = screen
        self.thumbnail_cache.clear()
        self._prepare()

    @property
    def gallery_icon(self) -> pygame.Surface | None:
        return self.assets.get("tool_gallery")

    @property
    def colouring_icon(self) -> pygame.Surface | None:
        if not self.outlines.available():
            return None
        return self.assets.get("tool_colouring")

    # -- geometry helpers -------------------------------------------------

    @property
    def palette_height(self) -> int:
        return self.metrics.px(82)

    @property
    def canvas_rect(self) -> pygame.Rect:
        return self.metrics.activity_content_rect(top_gap=2, bottom_reserve=self.palette_height)

    def toolbar_rect(self, name: str) -> pygame.Rect:
        slots = {"gallery": (0, "left"), "undo": (1, "left"), "new": (0, "right"), "colouring": (1, "right")}
        index, side = slots[name]
        return self.metrics.activity_toolbar_button(index, side=side)

    def shared_export_button(self) -> pygame.Rect | None:
        """Child-sized share/import slot in the free centre of the safe toolbar."""
        left = self.toolbar_rect("undo")
        right = self.toolbar_rect("colouring")
        size = self.metrics.button_size
        candidate = pygame.Rect((self.metrics.width - size) // 2, left.y, size, size)
        if candidate.left <= left.right + self.metrics.gap or candidate.right >= right.left - self.metrics.gap:
            return None
        return candidate

    def status_rect(self) -> pygame.Rect:
        anchor = self.toolbar_rect("colouring")
        size = self.metrics.px(30)
        rect = pygame.Rect(0, 0, size, size)
        rect.midright = (anchor.left - self.metrics.px(14), anchor.centery)
        return rect

    def tray_rect(self) -> pygame.Rect:
        safe = self.metrics.activity_safe_rect()
        return pygame.Rect(
            safe.left + self.metrics.margin,
            safe.bottom - self.metrics.margin - self.palette_height,
            safe.width - self.metrics.margin * 2,
            self.palette_height,
        )

    def _color_buttons(self) -> list[tuple[pygame.Rect, int]]:
        tray = self.tray_rect()
        left = tray.left + self.metrics.px(10)
        diameter = self.metrics.px(46)
        gap = self.metrics.px(8)
        return [
            (pygame.Rect(left + i * (diameter + gap), tray.centery - diameter // 2, diameter, diameter), i)
            for i in range(len(COLORS))
        ]

    def tool_buttons(self) -> tuple[pygame.Rect, pygame.Rect]:
        """Eraser and stamp tiles at the right end of the tray."""
        tray = self.tray_rect()
        size = self.metrics.px(62)
        gap = self.metrics.px(8)
        right = tray.right - self.metrics.px(10)
        top = tray.centery - size // 2
        stamp = pygame.Rect(right - size, top, size, size)
        eraser = pygame.Rect(stamp.left - gap - size, top, size, size)
        return eraser, stamp

    def _size_buttons(self) -> list[tuple[pygame.Rect, int]]:
        """Brush-size slots, small to large from left to right."""
        eraser, _stamp = self.tool_buttons()
        size = self.metrics.px(56)
        gap = self.metrics.px(6)
        right = eraser.left - self.metrics.px(22)
        top = self.tray_rect().centery - size // 2
        count = len(STAMP_SIZES)
        left = right - count * size - (count - 1) * gap
        return [(pygame.Rect(left + i * (size + gap), top, size, size), i) for i in range(count)]

    def separator_x(self) -> int:
        eraser, _ = self.tool_buttons()
        return eraser.left - self.metrics.px(11)

    def stamp_size(self, size_index: int) -> int:
        return self.metrics.px(STAMP_SIZES[size_index])

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
        """Big previous/next arrows in the (otherwise unused) tray strip."""
        tray = self.tray_rect()
        height = self.metrics.px(66)
        width = self.metrics.px(96)
        y = tray.centery - height // 2
        left = tray.left + self.metrics.px(10)
        right = tray.right - self.metrics.px(10) - width
        return pygame.Rect(left, y, width, height), pygame.Rect(right, y, width, height)

    def gallery_delete_button(self) -> pygame.Rect:
        """Delete tile for the focused card, well away from the page arrows."""
        tray = self.tray_rect()
        size = self.metrics.px(66)
        _previous, following = self.gallery_nav_buttons()
        rect = pygame.Rect(0, 0, size, size)
        rect.midright = (following.left - self.metrics.px(64), tray.centery)
        return rect

    # -- thumbnails / art ---------------------------------------------------

    def thumbnail(self, record, size: tuple[int, int], repository) -> pygame.Surface | None:
        cached = self.thumbnail_cache.get(record.painting_id)
        if cached is not None and cached.get_size() == size:
            self.thumbnail_cache.move_to_end(record.painting_id)
            return cached
        try:
            surface = _decode_png(repository.load_png(record.painting_id), size)
        except (RuntimeError, ValueError, OSError):
            return None
        self.thumbnail_cache[record.painting_id] = surface
        self.thumbnail_cache.move_to_end(record.painting_id)
        while len(self.thumbnail_cache) > self.THUMBNAIL_LIMIT:
            self.thumbnail_cache.popitem(last=False)
        return surface

    def invalidate_thumbnail(self, painting_id: str) -> None:
        self.thumbnail_cache.pop(painting_id, None)

    def stamp_icon(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self.stamps.image(asset_id, size)

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

    def render_mark(self, surface: pygame.Surface, mark: Stroke | Stamp) -> None:
        """Paint one history mark (stroke or stamp) onto ``surface``."""
        if isinstance(mark, Stamp):
            image = self.stamps.image(mark.asset_id, mark.size)
            if image is not None:
                surface.blit(image, image.get_rect(center=mark.center))
            return
        radius = max(1, mark.size // 2)
        if len(mark.points) == 1:
            pygame.draw.circle(surface, mark.color, mark.points[0], radius)
            return
        for start, end in zip(mark.points, mark.points[1:]):
            pygame.draw.line(surface, mark.color, start, end, mark.size)
            pygame.draw.circle(surface, mark.color, start, radius)
        pygame.draw.circle(surface, mark.color, mark.points[-1], radius)

    # -- drawing ----------------------------------------------------------

    def draw_studio_background(self, screen: pygame.Surface) -> None:
        if self._background_surface is not None and self._background_surface.get_size() == screen.get_size():
            screen.blit(self._background_surface, (0, 0))
        else:
            screen.fill(STUDIO_TOP)

    def _panel(self, size: tuple[int, int], fill=(255, 251, 240)) -> pygame.Surface:
        return self.kit.painter.body(BodyShape.PANEL, size, fill, lip=self.metrics.px(4), highlight=False)

    def draw_canvas(self, screen: pygame.Surface, canvas: pygame.Surface, outline: pygame.Surface | None = None) -> None:
        crect = self.canvas_rect
        frame = crect.inflate(self.metrics.px(12), self.metrics.px(12))
        frame.height += self.metrics.px(4)
        screen.blit(self._panel(frame.size), frame.topleft)
        screen.blit(canvas, crect)
        if outline is not None:
            screen.blit(outline, crect)

    def draw_tray(self, screen: pygame.Surface, selected_color: int, tool: str) -> None:
        tray = self.tray_rect()
        screen.blit(self._panel((tray.width, tray.height + self.metrics.px(4))), tray.topleft)
        dish = self._scaled_dish
        for rect, index in self._color_buttons():
            selected = index == selected_color and tool == "brush"
            center = rect.center if not selected else (rect.centerx, rect.centery - self.metrics.px(4))
            if dish is not None:
                screen.blit(dish, dish.get_rect(center=center))
            radius = rect.width // 2 - self.metrics.px(3)
            pygame.draw.circle(screen, COLORS[index], center, radius)
            pygame.draw.circle(screen, INK, center, radius, max(1, self.metrics.px(2)))
            gloss = pygame.Rect(0, 0, radius, max(2, radius // 2))
            gloss.center = (center[0] - radius // 4, center[1] - radius // 2)
            pygame.draw.ellipse(screen, mix(COLORS[index], PAPER, 0.55), gloss)
            if selected:
                ring = rect.width // 2 + self.metrics.px(5)
                pygame.draw.circle(screen, INK, center, ring + max(1, self.metrics.px(2)), max(2, self.metrics.px(3)))
                pygame.draw.circle(screen, SUNSHINE, center, ring, max(2, self.metrics.px(4)))
        x = self.separator_x()
        pygame.draw.line(
            screen, (226, 214, 190),
            (x, tray.top + self.metrics.px(12)), (x, tray.bottom - self.metrics.px(12)),
            max(1, self.metrics.px(2)),
        )

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
        tray = self.tray_rect()
        screen.blit(self._panel((tray.width, tray.height + self.metrics.px(4))), tray.topleft)
        if not records:
            self._draw_empty_gallery(screen)
        inset = self.metrics.px(12)
        for rect, record in self.gallery_cards(records, page):
            selected = focus_index is not None and records[focus_index] is record
            body = self.kit.painter.body(
                BodyShape.TILE, rect.size, SUNSHINE if selected else (255, 251, 240), lip=self.metrics.px(5),
            )
            screen.blit(body, rect.topleft)
            inner = pygame.Rect(rect.left + inset, rect.top + inset, rect.width - 2 * inset, rect.height - 2 * inset - self.metrics.px(5))
            thumb = self.thumbnail(record, inner.size, repository)
            if thumb is not None:
                screen.blit(thumb, inner)
            else:
                pygame.draw.rect(screen, PAPER, inner)
            pygame.draw.rect(screen, INK, inner, width=max(1, self.metrics.px(2)))
        self._draw_page_dots(screen, page, page_count, library_full)

    def _draw_empty_gallery(self, screen: pygame.Surface) -> None:
        """An empty shelf shows a friendly empty frame with a waiting brush stamp."""
        area = self.canvas_rect
        card = pygame.Rect(0, 0, area.width // 3, (area.height * 2) // 3)
        card.center = area.center
        screen.blit(self.kit.painter.body(BodyShape.TILE, card.size, (255, 251, 240), lip=self.metrics.px(5)), card.topleft)
        icon = self.stamps.image("prop.nature.flower", min(card.width, card.height) // 2)
        if icon is not None:
            screen.blit(icon, icon.get_rect(center=card.center))

    def _draw_page_dots(self, screen: pygame.Surface, page: int, page_count: int, library_full: bool) -> None:
        """Language-free pager dots plus the full-shelf pictogram."""
        previous, _following = self.gallery_nav_buttons()
        delete = self.gallery_delete_button()
        left = previous.right + self.metrics.px(16)
        if library_full:
            self._draw_full_badge(screen, left, previous.centery)
            left += self.metrics.px(150) + self.metrics.px(16)
        if page_count <= 1:
            return
        dot = self.metrics.px(9)
        gap = self.metrics.px(12)
        total = page_count * dot * 2 + (page_count - 1) * gap
        span = delete.left - self.metrics.px(16) - left
        x = left + max(0, (span - total) // 2) + dot
        for index in range(page_count):
            current = index == page
            pygame.draw.circle(screen, INK, (x, previous.centery), dot if current else dot - 2)
            pygame.draw.circle(screen, CORAL if current else (236, 224, 200), (x, previous.centery), (dot if current else dot - 2) - max(1, self.metrics.px(2)))
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

    def draw_dim(self, screen: pygame.Surface) -> None:
        shield = self._dim_surface(screen.get_size())
        screen.blit(shield, (0, 0))

    def _dim_surface(self, size: tuple[int, int]) -> pygame.Surface:
        cached = getattr(self, "_dim", None)
        if cached is None or cached.get_size() != size:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            cached.fill((61, 44, 31, 120))
            self._dim = cached
        return cached

    def draw_sheet_panel(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        screen.blit(self._panel(panel.size), panel.topleft)

    def draw_delete_dialog(self, screen: pygame.Surface, panel: pygame.Rect, preview: pygame.Surface | None) -> None:
        """Dim + panel with the painting itself, so the child sees *what* would go."""
        self.draw_dim(screen)
        screen.blit(self._panel(panel.size), panel.topleft)
        face = panel.inflate(-self.metrics.px(28), -self.metrics.px(28))
        thumb_rect = self.delete_preview_rect(panel)
        if preview is not None:
            screen.blit(preview, thumb_rect)
        pygame.draw.rect(screen, INK, thumb_rect, width=max(2, self.metrics.px(3)))
        trash = self.kit.glyph("trash", min(face.height - thumb_rect.height, self.metrics.px(84)))
        if trash is not None:
            screen.blit(trash, trash.get_rect(midtop=(face.centerx, thumb_rect.bottom + self.metrics.px(6))))

    def delete_dialog_rects(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        """Panel, cancel and confirm rects for the delete confirmation."""
        area = self.metrics.activity_safe_rect()
        width = min(area.width - self.metrics.px(40), self.metrics.px(560))
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
        canvas = self.canvas_rect
        width = min(panel.width - self.metrics.px(48), int(height * canvas.width / max(1, canvas.height)))
        height = int(width * canvas.height / max(1, canvas.width))
        rect = pygame.Rect(0, 0, width, height)
        rect.midtop = (panel.centerx, top)
        return rect

    def stamp_sheet_rects(self) -> tuple[pygame.Rect, list[pygame.Rect]]:
        """Panel above the tray (right-aligned) and 6x2 stamp tiles."""
        cols, rows = 6, 2
        tile = self.metrics.px(84)
        gap = self.metrics.px(10)
        pad = self.metrics.px(16)
        width = cols * tile + (cols - 1) * gap + 2 * pad
        height = rows * tile + (rows - 1) * gap + 2 * pad
        tray = self.tray_rect()
        panel = pygame.Rect(0, 0, width, height)
        panel.bottomright = (tray.right, tray.top - self.metrics.px(10))
        safe = self.metrics.activity_safe_rect()
        panel.top = max(panel.top, safe.top + self.metrics.px(4))
        tiles = [
            pygame.Rect(panel.left + pad + col * (tile + gap), panel.top + pad + row * (tile + gap), tile, tile)
            for row in range(rows)
            for col in range(cols)
        ]
        return panel, tiles

    def colouring_sheet_rects(self, count: int) -> tuple[pygame.Rect, list[pygame.Rect]]:
        """Panel over the canvas with one large page card per colouring page."""
        canvas = self.canvas_rect
        pad = self.metrics.px(18)
        gap = self.metrics.px(18)
        card_w = min(self.metrics.px(270), (canvas.width - 2 * pad - (count - 1) * gap) // max(1, count))
        card_h = int(card_w * 0.66)
        width = count * card_w + (count - 1) * gap + 2 * pad
        height = card_h + 2 * pad
        panel = pygame.Rect(0, 0, width, height)
        panel.center = canvas.center
        cards = [pygame.Rect(panel.left + pad + i * (card_w + gap), panel.top + pad, card_w, card_h) for i in range(count)]
        return panel, cards


# -- PNG helpers (shared with app, keeps encode at save boundary only) --

def _fit_rect(source: tuple[int, int], target: tuple[int, int]) -> pygame.Rect:
    """Largest rect with ``source`` aspect centred in ``target`` (contain)."""
    sw, sh = max(1, source[0]), max(1, source[1])
    tw, th = max(1, target[0]), max(1, target[1])
    scale = min(tw / sw, th / sh)
    w, h = max(1, round(sw * scale)), max(1, round(sh * scale))
    return pygame.Rect((tw - w) // 2, (th - h) // 2, w, h)


def _fit_alpha(source: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    rect = _fit_rect(source.get_size(), size)
    result = pygame.Surface(size, pygame.SRCALPHA)
    scaled = source if rect.size == source.get_size() else pygame.transform.smoothscale(source, rect.size)
    result.blit(scaled, rect.topleft)
    return result.convert_alpha() if pygame.display.get_surface() is not None else result


def _encode_png(surface: pygame.Surface) -> bytes:
    image = Image.frombytes("RGBA", surface.get_size(), pygame.image.tostring(surface, "RGBA"))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def _png_size(payload: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(payload)) as image:
        return image.size


def _decode_png(payload: bytes, target_size: tuple[int, int]) -> pygame.Surface:
    """Decode a saved painting and fit it (aspect preserved, both ways) on white."""
    with Image.open(io.BytesIO(payload)) as image:
        converted = image.convert("RGB")
        if converted.size != target_size:
            rect = _fit_rect(converted.size, target_size)
            resized = converted.resize(rect.size, Image.Resampling.BILINEAR)
            background = Image.new("RGB", target_size, PAPER)
            background.paste(resized, rect.topleft)
            converted = background
        surface = pygame.image.fromstring(converted.tobytes(), converted.size, "RGB")
        return surface.convert() if pygame.display.get_surface() is not None else surface


__all__ = ["FxBurst", "OutlineArt", "PaintingRenderer", "StampArt", "_decode_png", "_encode_png", "_png_size"]
