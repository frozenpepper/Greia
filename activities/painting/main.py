from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import time
import uuid

from PIL import Image
import pygame

from greia_platform.child_text import display_text
from greia_platform.activity_api import (
    activity_stop_requested,
    get_icon_path,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import (
    ChildUiMetrics,
    draw_activity_pointer,
    load_icon,
    mix,
)

AUTOSAVE_IDLE_SECONDS = 1.0
INDEX_KEY = "paintings.index.v1"
MAX_PAINTINGS = 48
MAX_UNDO_STROKES = 24
MAX_STROKE_POINTS = 2048
COLORS = (
    (42, 45, 54),     # Charcoal Night
    (239, 77, 83),    # Coral Red
    (250, 145, 54),   # Bright Orange
    (252, 202, 62),   # Sunshine Yellow
    (77, 180, 96),    # Leaf Green
    (51, 163, 211),   # Sky Blue
    (92, 113, 224),   # Indigo Periwinkle
    (159, 94, 211),   # Lavender Purple
    (239, 104, 170),  # Blossom Pink
    (133, 91, 61),    # Warm Cocoa Brown
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
        self.assets: dict[str, pygame.Surface] = {}
        self._scaled_tool_icons: dict[str, pygame.Surface] = {}
        self._scaled_tool_icons_disabled: dict[str, pygame.Surface] = {}
        self._scaled_brush_icons: dict[int, pygame.Surface] = {}
        self._scaled_dish: pygame.Surface | None = None
        self._scaled_card_frame: pygame.Surface | None = None
        self._background_surface: pygame.Surface | None = None
        self._status_labels: dict[str, pygame.Surface] = {}
        self._load_assets()
        self._precompute_ui_resources()

        # Canvas styling: warm crisp white studio paper
        self.canvas_background = (255, 255, 255)
        self.canvas = self._new_blank_surface()
        self.base_canvas = self.canvas.copy()
        if self.records:
            self._open(self.records[0])
        else:
            self._new()

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
        # Pre-scale tool icons
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

        # Pre-scale color dish
        dish_sz = self.metrics.px(38) + self.metrics.px(6)
        well_dish = self.assets.get("color_well_dish")
        if well_dish is not None:
            self._scaled_dish = pygame.transform.smoothscale(well_dish, (dish_sz, dish_sz))
        else:
            self._scaled_dish = None

        # Pre-scale brush icons
        brush_keys = ["brush_small", "brush_medium", "brush_large"]
        brush_sz = self.metrics.px(34)
        self._scaled_brush_icons = {}
        for idx, key in enumerate(brush_keys):
            b_icon = self.assets.get(key)
            if b_icon is not None:
                self._scaled_brush_icons[idx] = pygame.transform.smoothscale(b_icon, (brush_sz, brush_sz))

        # Pre-scale gallery card frame
        card_frame = self.assets.get("canvas_card_frame")
        area = self.canvas_rect
        gap = self.metrics.px(18)
        card_w = max(1, (area.width - gap * 2) // 3)
        card_h = max(1, (area.height - gap) // 2)
        if card_frame is not None:
            self._scaled_card_frame = pygame.transform.smoothscale(card_frame, (card_w, card_h))
        else:
            self._scaled_card_frame = None

        # Pre-render studio background surface
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

        # Pre-render status labels (child text case policy applied)
        self.status_font = pygame.font.Font(None, self.metrics.px(16))
        self._status_labels = {
            "Salvo": self.status_font.render(display_text("Salvo"), True, (100, 116, 139)),
            "Salva...": self.status_font.render(display_text("Salva..."), True, (100, 116, 139)),
            "Errore": self.status_font.render(display_text("Errore"), True, (100, 116, 139)),
        }

    @property
    def palette_height(self) -> int:
        return self.metrics.px(82)

    @property
    def canvas_rect(self) -> pygame.Rect:
        return self.metrics.activity_content_rect(top_gap=2, bottom_reserve=self.palette_height)

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

        gallery = self.metrics.activity_toolbar_button(0, side="left")
        undo = self.metrics.activity_toolbar_button(1, side="left")
        new = self.metrics.activity_toolbar_button(0, side="right")
        eraser = self.metrics.activity_toolbar_button(1, side="right")

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
        safe = self.metrics.activity_safe_rect()
        left = safe.left + self.metrics.margin + self.metrics.px(10)
        y = safe.bottom - self.metrics.margin - self.palette_height // 2
        diameter = self.metrics.px(38)
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
        # 1. Warm studio tabletop background
        self._draw_studio_background()

        # 2. Toolbar buttons
        self._draw_toolbar()

        # 3. Canvas or Gallery
        if self.mode == "gallery":
            self._draw_gallery()
        else:
            self._draw_canvas()
            self._draw_palette()

        # 4. Activity-local pointer. Trusted Home/Back is platform-owned.
        draw_activity_pointer(self.screen)

    def _draw_studio_background(self) -> None:
        if self._background_surface is not None:
            self.screen.blit(self._background_surface, (0, 0))
            return
        bg_top = (252, 248, 238)
        bg_bottom = (245, 238, 224)
        h = self.screen.get_height()
        w = self.screen.get_width()
        self.screen.fill(bg_top)
        band_h = h // 3
        band_rect = pygame.Rect(0, h - band_h, w, band_h)
        pygame.draw.rect(self.screen, bg_bottom, band_rect)
        line_y = self.canvas_rect.top - self.metrics.px(8)
        if line_y > 0:
            pygame.draw.line(self.screen, (235, 226, 208), (0, line_y), (w, line_y), 2)

    def _draw_toolbar(self) -> None:
        gallery = self.metrics.activity_toolbar_button(0, side="left")
        undo = self.metrics.activity_toolbar_button(1, side="left")
        new = self.metrics.activity_toolbar_button(0, side="right")
        eraser = self.metrics.activity_toolbar_button(1, side="right")

        # Gallery button
        self._draw_tactile_button(
            gallery,
            icon_key="tool_gallery",
            active=self.mode == "gallery",
            base_color=(255, 255, 255),
            active_color=(254, 240, 138),
            fallback_symbol="grid"
        )

        # Undo button (only active in paint mode)
        can_undo = self.mode == "paint" and bool(self.history.items)
        self._draw_tactile_button(
            undo,
            icon_key="tool_undo",
            active=False,
            base_color=(255, 255, 255) if can_undo else (241, 245, 249),
            fallback_symbol="undo",
            disabled=not can_undo
        )

        # New canvas button (golden delight)
        self._draw_tactile_button(
            new,
            icon_key="tool_new",
            active=False,
            base_color=(251, 191, 36),
            fallback_symbol="plus"
        )

        # Eraser button
        self._draw_tactile_button(
            eraser,
            icon_key="tool_eraser",
            active=self.eraser,
            base_color=(255, 255, 255),
            active_color=(254, 226, 226),
            fallback_symbol="eraser"
        )

        # Status Pill Indicator
        pill_w = self.metrics.px(72)
        pill_h = self.metrics.px(28)
        pill_x = eraser.left - pill_w - self.metrics.px(10)
        pill_y = eraser.centery - pill_h // 2
        pill_rect = pygame.Rect(pill_x, pill_y, pill_w, pill_h)
        pygame.draw.rect(self.screen, (255, 255, 255), pill_rect, border_radius=pill_h // 2)
        pygame.draw.rect(self.screen, (226, 232, 240), pill_rect, width=2, border_radius=pill_h // 2)

        status_color = (239, 68, 68) if self.save_error else ((245, 158, 11) if self.dirty else (34, 197, 94))
        pygame.draw.circle(self.screen, status_color, (pill_rect.left + pill_h // 2, pill_rect.centery), self.metrics.px(5))
        # Mini status check or pulse dot
        if not self.dirty and not self.save_error:
            # Green checkmark
            cx = pill_rect.left + pill_h // 2
            cy = pill_rect.centery
            pygame.draw.lines(self.screen, (255, 255, 255), False, [(cx - 3, cy), (cx - 1, cy + 2), (cx + 3, cy - 2)], 2)
        # Status text
        status_label = "Salvo" if not self.dirty else "Salva..."
        if self.save_error:
            status_label = "Errore"
        txt = self._status_labels.get(status_label)
        if txt is None:
            if not hasattr(self, "status_font"):
                self.status_font = pygame.font.Font(None, self.metrics.px(16))
            txt = self.status_font.render(status_label, True, (100, 116, 139))
        self.screen.blit(txt, (pill_rect.left + pill_h + 2, pill_rect.centery - txt.get_height() // 2))

    def _draw_tactile_button(
        self,
        rect: pygame.Rect,
        icon_key: str,
        active: bool = False,
        base_color: tuple[int, int, int] = (255, 255, 255),
        active_color: tuple[int, int, int] = (254, 240, 138),
        fallback_symbol: str = "",
        disabled: bool = False
    ) -> None:
        radius = self.metrics.radius
        shadow_rect = rect.move(0, self.metrics.px(3))
        pygame.draw.rect(self.screen, (203, 213, 225), shadow_rect, border_radius=radius)

        fill = active_color if active else base_color
        if disabled:
            fill = (241, 245, 249)
        pygame.draw.rect(self.screen, fill, rect, border_radius=radius)

        border_col = (234, 88, 12) if active else (226, 232, 240)
        border_w = max(2, self.metrics.px(3)) if active else max(1, self.metrics.px(2))
        pygame.draw.rect(self.screen, border_col, rect, width=border_w, border_radius=radius)

        # Draw pre-scaled icon
        scaled_icon = (
            self._scaled_tool_icons_disabled.get(icon_key)
            if disabled
            else self._scaled_tool_icons.get(icon_key)
        )
        if scaled_icon is not None:
            self.screen.blit(scaled_icon, scaled_icon.get_rect(center=rect.center))
        else:
            # Clean procedural fallback
            col = (148, 163, 184) if disabled else (51, 65, 85)
            if fallback_symbol == "grid":
                for r_idx in range(2):
                    for c_idx in range(2):
                        dot_r = pygame.Rect(rect.centerx - 12 + c_idx * 14, rect.centery - 12 + r_idx * 14, 10, 10)
                        pygame.draw.rect(self.screen, col, dot_r, border_radius=3)
            elif fallback_symbol == "undo":
                pygame.draw.circle(self.screen, col, rect.center, 12, width=3)
            elif fallback_symbol == "plus":
                pygame.draw.line(self.screen, (255, 255, 255), (rect.centerx, rect.centery - 12), (rect.centerx, rect.centery + 12), 4)
                pygame.draw.line(self.screen, (255, 255, 255), (rect.centerx - 12, rect.centery), (rect.centerx + 12, rect.centery), 4)
            elif fallback_symbol == "eraser":
                pygame.draw.rect(self.screen, col, pygame.Rect(rect.centerx - 12, rect.centery - 8, 24, 16), border_radius=4)

    def _draw_canvas(self) -> None:
        crect = self.canvas_rect
        # 1. Tactile drop shadow around the paper canvas
        shadow_rect = crect.inflate(self.metrics.px(8), self.metrics.px(8)).move(0, self.metrics.px(4))
        pygame.draw.rect(self.screen, (214, 204, 188), shadow_rect, border_radius=self.metrics.radius + 4)
        # 2. Outer paper rim / mat
        mat_rect = crect.inflate(self.metrics.px(6), self.metrics.px(6))
        pygame.draw.rect(self.screen, (250, 246, 238), mat_rect, border_radius=self.metrics.radius + 2)
        pygame.draw.rect(self.screen, (226, 218, 202), mat_rect, width=2, border_radius=self.metrics.radius + 2)
        # 3. Canvas surface
        self.screen.blit(self.canvas, crect)
        # 4. Subtle inner border on canvas
        pygame.draw.rect(self.screen, (241, 235, 222), crect, width=1, border_radius=self.metrics.radius)

    def _draw_palette(self) -> None:
        safe = self.metrics.activity_safe_rect()
        panel = pygame.Rect(
            safe.left + self.metrics.margin,
            safe.bottom - self.metrics.margin - self.palette_height,
            safe.width - self.metrics.margin * 2,
            self.palette_height,
        )

        # Tactile tray shadow & body
        tray_shadow = panel.move(0, self.metrics.px(3))
        pygame.draw.rect(self.screen, (214, 204, 188), tray_shadow, border_radius=self.metrics.radius + 4)
        pygame.draw.rect(self.screen, (255, 255, 255), panel, border_radius=self.metrics.radius)
        pygame.draw.rect(self.screen, (226, 218, 202), panel, width=2, border_radius=self.metrics.radius)

        # 1. Color wells (using pre-scaled dish asset)
        scaled_dish = self._scaled_dish
        for rect, index in self._color_buttons():
            if scaled_dish is not None:
                self.screen.blit(scaled_dish, scaled_dish.get_rect(center=rect.center))
            else:
                dish_sz = rect.width + self.metrics.px(6)
                pygame.draw.circle(self.screen, (241, 245, 249), rect.center, dish_sz // 2)
                pygame.draw.circle(self.screen, (203, 213, 225), rect.center, dish_sz // 2, 2)

            col = COLORS[index]
            r = rect.width // 2 - self.metrics.px(2)
            pygame.draw.circle(self.screen, col, rect.center, r)
            # Gloss highlight
            pygame.draw.ellipse(self.screen, (255, 255, 255, 120), (rect.centerx - r // 2, rect.centery - r + 3, r, r // 2))

            # Active selection badge
            if index == self.selected_color and not self.eraser:
                # Radiant golden ring
                glow_r = rect.width // 2 + self.metrics.px(4)
                pygame.draw.circle(self.screen, (251, 191, 36), rect.center, glow_r, max(2, self.metrics.px(3)))
                pygame.draw.circle(self.screen, (255, 255, 255), rect.center, glow_r - 2, 1)

        # 2. Separator line between colors and brush sizes
        first_size_btn = self._size_buttons()[-1][0]
        sep_x = first_size_btn.left - self.metrics.px(14)
        pygame.draw.line(self.screen, (226, 232, 240), (sep_x, panel.top + self.metrics.px(10)), (sep_x, panel.bottom - self.metrics.px(10)), 2)

        # 3. Brush size buttons (using pre-scaled brush icons)
        for rect, index in self._size_buttons():
            is_active = (index == self.selected_size)
            btn_bg = (254, 240, 138) if is_active else (248, 250, 252)
            pygame.draw.rect(self.screen, btn_bg, rect, border_radius=self.metrics.radius)
            b_border = (245, 158, 11) if is_active else (226, 232, 240)
            pygame.draw.rect(self.screen, b_border, rect, width=2, border_radius=self.metrics.radius)

            scaled_b = self._scaled_brush_icons.get(index)
            if scaled_b is not None:
                self.screen.blit(scaled_b, scaled_b.get_rect(center=rect.center))
            else:
                dot_r = max(self.metrics.px(3), self.metrics.px(BRUSH_SIZES[index]) // 2)
                dot_col = (245, 158, 11) if is_active else (51, 65, 85)
                pygame.draw.circle(self.screen, dot_col, rect.center, dot_r)

    def _draw_gallery(self) -> None:
        scaled_frame = self._scaled_card_frame
        for rect, record in self._gallery_cards():
            if scaled_frame is not None and scaled_frame.get_size() == rect.size:
                self.screen.blit(scaled_frame, rect)
            else:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, border_radius=self.metrics.radius)
                pygame.draw.rect(self.screen, (226, 232, 240), rect, width=2, border_radius=self.metrics.radius)

            inner = rect.inflate(-self.metrics.px(24), -self.metrics.px(24))
            thumb = self._thumbnail(record, inner.size)
            if thumb is None:
                self.screen.blit(self.empty_icon, self.empty_icon.get_rect(center=rect.center))
            else:
                self.screen.blit(thumb, inner)
                pygame.draw.rect(self.screen, (226, 232, 240), inner, width=1, border_radius=self.metrics.radius // 2)

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
