from __future__ import annotations

from dataclasses import dataclass
import io
import time
import uuid

from PIL import Image
import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_icon_path,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import (
    ChildUiMetrics,
    draw_eraser_symbol,
    draw_grid_symbol,
    draw_icon_button,
    draw_plus_symbol,
    draw_undo_symbol,
    load_icon,
    mix,
)

AUTOSAVE_IDLE_SECONDS = 1.0
INDEX_KEY = "paintings.index.v1"
MAX_PAINTINGS = 48
MAX_UNDO_STROKES = 24
MAX_STROKE_POINTS = 2048
COLORS = (
    (42, 45, 54),
    (239, 77, 83),
    (250, 145, 54),
    (252, 202, 62),
    (77, 180, 96),
    (51, 163, 211),
    (92, 113, 224),
    (159, 94, 211),
    (239, 104, 170),
    (133, 91, 61),
)
BRUSH_SIZES = (8, 18, 34)


@dataclass(frozen=True, slots=True)
class PaintingRecord:
    painting_id: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.painting_id}


class PaintingRepository:
    def __init__(self, storage):
        self.storage = storage

    def list_records(self) -> list[PaintingRecord]:
        raw = self.storage.kv_get(INDEX_KEY, [])
        if not isinstance(raw, list):
            return []
        records: list[PaintingRecord] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            painting_id = item.get("id")
            if (
                not isinstance(painting_id, str)
                or not _valid_id(painting_id)
                or painting_id in seen
            ):
                continue
            seen.add(painting_id)
            records.append(PaintingRecord(painting_id))
            if len(records) >= MAX_PAINTINGS:
                break
        return records

    def create(self, initial_png: bytes) -> PaintingRecord:
        records = self.list_records()
        if len(records) >= MAX_PAINTINGS:
            raise RuntimeError("painting library limit reached")
        record = PaintingRecord(uuid.uuid4().hex)
        name = self._name(record.painting_id)
        self.storage.file_write_atomic(name, bytes(initial_png))
        try:
            self._write_index([record, *records])
        except RuntimeError:
            try:
                self.storage.file_delete(name)
            except RuntimeError:
                pass
            raise
        return record

    def load_png(self, painting_id: str) -> bytes:
        _require_id(painting_id)
        return self.storage.file_read(self._name(painting_id))

    def save_png(self, painting_id: str, payload: bytes) -> PaintingRecord:
        _require_id(painting_id)
        self.storage.file_write_atomic(self._name(painting_id), bytes(payload))
        record = PaintingRecord(painting_id)
        others = [item for item in self.list_records() if item.painting_id != painting_id]
        self._write_index([record, *others])
        return record

    def _write_index(self, records: list[PaintingRecord]) -> None:
        self.storage.kv_set(INDEX_KEY, [item.as_dict() for item in records])

    @staticmethod
    def _name(painting_id: str) -> str:
        return f"paintings/{painting_id}.png"


@dataclass(frozen=True, slots=True)
class Stroke:
    color: tuple[int, int, int]
    size: int
    points: tuple[tuple[int, int], ...]


class StrokeHistory:
    def __init__(self, maximum: int = MAX_UNDO_STROKES):
        if maximum < 1:
            raise ValueError("undo history must retain at least one stroke")
        self.maximum = int(maximum)
        self._items: list[Stroke] = []

    @property
    def items(self) -> tuple[Stroke, ...]:
        return tuple(self._items)

    def add(self, stroke: Stroke) -> Stroke | None:
        if stroke.size <= 0 or not stroke.points:
            raise ValueError("stroke must have positive size and at least one point")
        if len(stroke.points) > MAX_STROKE_POINTS:
            raise ValueError("stroke exceeds point bound")
        self._items.append(stroke)
        if len(self._items) <= self.maximum:
            return None
        return self._items.pop(0)

    def undo(self) -> Stroke | None:
        return self._items.pop() if self._items else None

    def clear(self) -> None:
        self._items.clear()


def _valid_id(value: str) -> bool:
    return len(value) == 32 and all(ch in "0123456789abcdef" for ch in value)


def _require_id(value: str) -> None:
    if not isinstance(value, str) or not _valid_id(value):
        raise ValueError("invalid painting id")


class PaintingApp:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.theme = get_theme()
        self.repository = PaintingRepository(get_storage())
        icon_size = self.metrics.px(42)
        self.close_icon = load_icon(get_icon_path("close_button", 64), icon_size)
        self.empty_icon = load_icon(get_icon_path("rainbow", 64), self.metrics.px(52))
        self.records = self.repository.list_records()
        self.current: PaintingRecord | None = None
        self.mode = "paint"
        self.selected_color = 1
        self.selected_size = 1
        self.eraser = False
        self.history = StrokeHistory()
        self.active_points: list[tuple[int, int]] = []
        self.drawing = False
        self.continuation_only = False
        self.dirty = False
        self.save_error = False
        self.last_change = 0.0
        self.thumbnail_cache: dict[str, pygame.Surface] = {}
        self.canvas_background = mix(self.theme.panel, (255, 255, 255), 0.72)
        self.canvas = self._new_blank_surface()
        self.base_canvas = self.canvas.copy()
        if self.records:
            self._open(self.records[0])
        else:
            self._new()

    @property
    def palette_height(self) -> int:
        return self.metrics.px(82)

    @property
    def canvas_rect(self) -> pygame.Rect:
        top = self.metrics.margin + self.metrics.toolbar_height + self.metrics.px(2)
        bottom = self.metrics.margin + self.palette_height
        return pygame.Rect(
            self.metrics.margin,
            top,
            self.screen.get_width() - self.metrics.margin * 2,
            self.screen.get_height() - top - bottom,
        )

    def run(self) -> int:
        running = True
        ready_published = False
        while running and not activity_stop_requested():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self._save():
                        running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self._save():
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._mouse_down(event.pos)
                elif event.type == pygame.MOUSEMOTION and self.drawing:
                    self._mouse_motion(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    running = self._mouse_up(event.pos)
            self._autosave()
            self._draw()
            pygame.display.flip()
            if not ready_published:
                mark_activity_ready()
                ready_published = True
            self.clock.tick(30)
        self._save()
        pygame.quit()
        return 0

    def _mouse_down(self, pos: tuple[int, int]) -> None:
        if self.mode != "paint" or not self.canvas_rect.collidepoint(pos):
            return
        point = self._local(pos)
        self.drawing = True
        self.continuation_only = False
        self.active_points = [point]
        self._draw_dot(self.canvas, point)

    def _mouse_motion(self, pos: tuple[int, int]) -> None:
        if not self.canvas_rect.collidepoint(pos):
            return
        point = self._local(pos)
        if not self.active_points:
            self.active_points = [point]
            self.continuation_only = False
            self._draw_dot(self.canvas, point)
            return
        previous = self.active_points[-1]
        if (point[0] - previous[0]) ** 2 + (point[1] - previous[1]) ** 2 < self.metrics.px(3) ** 2:
            return
        if len(self.active_points) >= MAX_STROKE_POINTS:
            self._commit_active_stroke()
            self.active_points = [previous]
            self.continuation_only = True
        self.active_points.append(point)
        self.continuation_only = False
        self._draw_segment(self.canvas, previous, point)

    def _mouse_up(self, pos: tuple[int, int]) -> bool:
        if self.drawing:
            if self.canvas_rect.collidepoint(pos):
                point = self._local(pos)
                if point != self.active_points[-1]:
                    previous = self.active_points[-1]
                    if len(self.active_points) >= MAX_STROKE_POINTS:
                        self._commit_active_stroke()
                        self.active_points = [previous]
                        self.continuation_only = True
                    self.active_points.append(point)
                    self.continuation_only = False
                    self._draw_segment(self.canvas, previous, point)
            self._finish_stroke()
            return True

        close = self.metrics.toolbar_button(0, side="left")
        gallery = self.metrics.toolbar_button(1, side="left")
        undo = self.metrics.toolbar_button(2, side="left")
        new = self.metrics.toolbar_button(0, side="right")
        eraser = self.metrics.toolbar_button(1, side="right")

        if close.collidepoint(pos):
            return not self._save()
        if gallery.collidepoint(pos):
            if not self._save():
                return True
            self.mode = "gallery" if self.mode == "paint" else "paint"
            return True
        if new.collidepoint(pos):
            if self._save():
                self._new()
            return True
        if undo.collidepoint(pos) and self.mode == "paint":
            self._undo()
            return True
        if eraser.collidepoint(pos) and self.mode == "paint":
            self.eraser = not self.eraser
            return True
        if self.mode == "gallery":
            for rect, record in self._gallery_cards():
                if rect.collidepoint(pos):
                    self._open(record)
                    break
            return True
        for rect, index in self._color_buttons():
            if rect.collidepoint(pos):
                self.selected_color = index
                self.eraser = False
                return True
        for rect, index in self._size_buttons():
            if rect.collidepoint(pos):
                self.selected_size = index
                return True
        return True

    def _commit_active_stroke(self) -> None:
        if not self.active_points or self.continuation_only:
            self.active_points = []
            self.continuation_only = False
            return
        stroke = Stroke(self._brush_color(), self._brush_size(), tuple(self.active_points))
        dropped = self.history.add(stroke)
        if dropped is not None:
            self._render_stroke(self.base_canvas, dropped)
        self.active_points = []
        self.continuation_only = False
        self.dirty = True
        self.last_change = time.monotonic()

    def _finish_stroke(self) -> None:
        self.drawing = False
        self._commit_active_stroke()

    def _undo(self) -> None:
        if self.history.undo() is None:
            return
        self.canvas = self.base_canvas.copy()
        for stroke in self.history.items:
            self._render_stroke(self.canvas, stroke)
        self.dirty = True
        self.last_change = time.monotonic()

    def _new(self) -> None:
        blank = self._new_blank_surface()
        try:
            record = self.repository.create(self._encode_png(blank))
        except (RuntimeError, ValueError, OSError):
            self.save_error = True
            return
        self.current = record
        self.records = [record, *[item for item in self.records if item.painting_id != record.painting_id]]
        self.mode = "paint"
        self.canvas = blank
        self.base_canvas = blank.copy()
        self.history.clear()
        self.active_points = []
        self.continuation_only = False
        self.dirty = False
        self.save_error = False

    def _open(self, record: PaintingRecord) -> bool:
        if not self._save():
            return False
        try:
            surface = self._decode_png(self.repository.load_png(record.painting_id), self.canvas_rect.size)
        except (RuntimeError, ValueError, OSError):
            self.save_error = True
            return False
        self.current = record
        self.mode = "paint"
        self.canvas = surface
        self.base_canvas = surface.copy()
        self.history.clear()
        self.active_points = []
        self.continuation_only = False
        self.dirty = False
        self.save_error = False
        return True

    def _new_blank_surface(self) -> pygame.Surface:
        surface = pygame.Surface(self.canvas_rect.size).convert()
        surface.fill(self.canvas_background)
        return surface

    def _autosave(self) -> None:
        if self.dirty and time.monotonic() - self.last_change >= AUTOSAVE_IDLE_SECONDS:
            self._save()

    def _save(self) -> bool:
        if not self.dirty or self.current is None:
            return True
        try:
            record = self.repository.save_png(self.current.painting_id, self._encode_png(self.canvas))
        except (RuntimeError, ValueError, OSError):
            self.save_error = True
            return False
        self.current = record
        self.records = [record, *[item for item in self.records if item.painting_id != record.painting_id]]
        self.thumbnail_cache.pop(record.painting_id, None)
        self.dirty = False
        self.save_error = False
        return True

    def _brush_color(self) -> tuple[int, int, int]:
        return self.canvas_background if self.eraser else COLORS[self.selected_color]

    def _brush_size(self) -> int:
        return self.metrics.px(BRUSH_SIZES[self.selected_size])

    def _draw_dot(self, surface: pygame.Surface, point: tuple[int, int]) -> None:
        pygame.draw.circle(surface, self._brush_color(), point, max(1, self._brush_size() // 2))

    def _draw_segment(self, surface: pygame.Surface, start: tuple[int, int], end: tuple[int, int]) -> None:
        color = self._brush_color()
        size = self._brush_size()
        radius = max(1, size // 2)
        pygame.draw.line(surface, color, start, end, size)
        pygame.draw.circle(surface, color, start, radius)
        pygame.draw.circle(surface, color, end, radius)

    @staticmethod
    def _render_stroke(surface: pygame.Surface, stroke: Stroke) -> None:
        radius = max(1, stroke.size // 2)
        if len(stroke.points) == 1:
            pygame.draw.circle(surface, stroke.color, stroke.points[0], radius)
            return
        for start, end in zip(stroke.points, stroke.points[1:]):
            pygame.draw.line(surface, stroke.color, start, end, stroke.size)
            pygame.draw.circle(surface, stroke.color, start, radius)
        pygame.draw.circle(surface, stroke.color, stroke.points[-1], radius)

    def _local(self, pos: tuple[int, int]) -> tuple[int, int]:
        return pos[0] - self.canvas_rect.left, pos[1] - self.canvas_rect.top

    def _color_buttons(self) -> list[tuple[pygame.Rect, int]]:
        left = self.metrics.margin + self.metrics.px(10)
        y = self.screen.get_height() - self.metrics.margin - self.palette_height // 2
        diameter = self.metrics.px(38)
        gap = self.metrics.px(8)
        return [
            (pygame.Rect(left + i * (diameter + gap), y - diameter // 2, diameter, diameter), i)
            for i in range(len(COLORS))
        ]

    def _size_buttons(self) -> list[tuple[pygame.Rect, int]]:
        size = self.metrics.px(48)
        gap = self.metrics.px(6)
        right = self.screen.get_width() - self.metrics.margin
        y = self.screen.get_height() - self.metrics.margin - self.palette_height // 2
        result = []
        for order, brush_index in enumerate(reversed(range(len(BRUSH_SIZES)))):
            result.append((pygame.Rect(right - (order + 1) * size - order * gap, y - size // 2, size, size), brush_index))
        return result

    def _gallery_cards(self) -> list[tuple[pygame.Rect, PaintingRecord]]:
        area = self.canvas_rect
        gap = self.metrics.px(18)
        card_w = (area.width - gap * 2) // 3
        card_h = (area.height - gap) // 2
        cards = []
        for index, record in enumerate(self.records[:6]):
            row, col = divmod(index, 3)
            cards.append((pygame.Rect(area.left + col * (card_w + gap), area.top + row * (card_h + gap), card_w, card_h), record))
        return cards

    def _thumbnail(self, record: PaintingRecord, size: tuple[int, int]) -> pygame.Surface | None:
        cached = self.thumbnail_cache.get(record.painting_id)
        if cached is not None and cached.get_size() == size:
            return cached
        try:
            surface = self._decode_png(self.repository.load_png(record.painting_id), size)
        except (RuntimeError, ValueError, OSError):
            return None
        self.thumbnail_cache[record.painting_id] = surface
        return surface

    def _draw(self) -> None:
        self.screen.fill(self.theme.background)
        close = self.metrics.toolbar_button(0, side="left")
        gallery = self.metrics.toolbar_button(1, side="left")
        undo = self.metrics.toolbar_button(2, side="left")
        new = self.metrics.toolbar_button(0, side="right")
        eraser = self.metrics.toolbar_button(1, side="right")
        draw_icon_button(self.screen, close, fill=self.theme.panel, icon=self.close_icon)
        draw_icon_button(self.screen, gallery, fill=self.theme.panel, selected=self.mode == "gallery", outline=self.theme.accent)
        draw_grid_symbol(self.screen, gallery, self.theme.text)
        draw_icon_button(self.screen, undo, fill=self.theme.panel)
        draw_undo_symbol(self.screen, undo, self.theme.text)
        draw_icon_button(self.screen, new, fill=self.theme.accent)
        draw_plus_symbol(self.screen, new, self.theme.accent_text)
        draw_icon_button(self.screen, eraser, fill=self.theme.panel, selected=self.eraser, outline=self.theme.accent)
        draw_eraser_symbol(self.screen, eraser, self.theme.text)
        status = (210, 76, 76) if self.save_error else ((246, 178, 55) if self.dirty else (87, 174, 104))
        pygame.draw.circle(self.screen, status, (eraser.left - self.metrics.px(18), eraser.centery), self.metrics.px(6))
        if self.mode == "gallery":
            self._draw_gallery()
        else:
            self._draw_canvas()
            self._draw_palette()

    def _draw_canvas(self) -> None:
        pygame.draw.rect(self.screen, mix(self.theme.text, self.theme.background, 0.82), self.canvas_rect.inflate(self.metrics.px(4), self.metrics.px(4)), border_radius=self.metrics.radius)
        self.screen.blit(self.canvas, self.canvas_rect)

    def _draw_palette(self) -> None:
        panel = pygame.Rect(
            self.metrics.margin,
            self.screen.get_height() - self.metrics.margin - self.palette_height,
            self.screen.get_width() - self.metrics.margin * 2,
            self.palette_height,
        )
        pygame.draw.rect(self.screen, self.theme.panel, panel, border_radius=self.metrics.radius)
        for rect, index in self._color_buttons():
            pygame.draw.circle(self.screen, COLORS[index], rect.center, rect.width // 2)
            if index == self.selected_color and not self.eraser:
                pygame.draw.circle(self.screen, self.theme.text, rect.center, rect.width // 2, max(3, self.metrics.px(4)))
        for rect, index in self._size_buttons():
            if index == self.selected_size:
                pygame.draw.circle(self.screen, self.theme.accent, rect.center, rect.width // 2)
            dot = self.theme.accent_text if index == self.selected_size else self.theme.text
            pygame.draw.circle(self.screen, dot, rect.center, max(self.metrics.px(3), self.metrics.px(BRUSH_SIZES[index]) // 2))

    def _draw_gallery(self) -> None:
        for rect, record in self._gallery_cards():
            pygame.draw.rect(self.screen, self.theme.panel, rect, border_radius=self.metrics.radius)
            inner = rect.inflate(-self.metrics.px(18), -self.metrics.px(18))
            thumb = self._thumbnail(record, inner.size)
            if thumb is None:
                self.screen.blit(self.empty_icon, self.empty_icon.get_rect(center=rect.center))
            else:
                self.screen.blit(thumb, inner)

    @staticmethod
    def _encode_png(surface: pygame.Surface) -> bytes:
        image = Image.frombytes("RGBA", surface.get_size(), pygame.image.tostring(surface, "RGBA"))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=False)
        return buffer.getvalue()

    @staticmethod
    def _decode_png(payload: bytes, target_size: tuple[int, int]) -> pygame.Surface:
        with Image.open(io.BytesIO(payload)) as image:
            converted = image.convert("RGB")
            if converted.size != target_size:
                converted.thumbnail(target_size, Image.Resampling.BILINEAR)
                background = Image.new("RGB", target_size, (255, 255, 255))
                background.paste(converted, ((target_size[0] - converted.width) // 2, (target_size[1] - converted.height) // 2))
                converted = background
            return pygame.image.fromstring(converted.tobytes(), converted.size, "RGB").convert()


def main() -> int:
    return PaintingApp().run()


if __name__ == "__main__":
    raise SystemExit(main())
