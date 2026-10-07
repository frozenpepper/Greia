"""Lifecycle owner for the Painting Activity.

Owns screen/canvas/metrics, domain model, renderer and input
routing. Delegates rules to the pure model and presentation to the
renderer. Publishes READY after the first flip in the same loop.
Keeps the experience simple, fast, cute, large canvas, small tools.
"""

from __future__ import annotations

import hashlib
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_ui import ChildUiMetrics, draw_activity_pointer
from greia_platform.pygame_canvas import activity_viewport_for_surface

if __package__:
    from .painting_content import BRUSH_SIZES, COLORS
    from .painting_model import PaintingRecord, PaintingRepository, Stroke, StrokeHistory
    from .painting_renderer import PaintingRenderer, _decode_png, _encode_png
else:  # pragma: no cover - runtime/script fallback
    from painting_content import BRUSH_SIZES, COLORS
    from painting_model import PaintingRecord, PaintingRepository, Stroke, StrokeHistory
    from painting_renderer import PaintingRenderer, _decode_png, _encode_png


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(
        region.x <= x < region.right and region.y <= y < region.bottom
        for region in viewport.protected_regions
    )


class PaintingApp:
    """Coordinate Painting lifecycle without owning domain or rendering details."""

    def __init__(
        self,
        screen: pygame.Surface,
        metrics: ChildUiMetrics,
        theme,
        repository: PaintingRepository,
        creations=None,
    ) -> None:
        self.screen = screen
        self.metrics = metrics
        self.theme = theme
        self.repository = repository
        self.creations = creations
        self._last_shared: tuple[str, str] | None = None
        self.shared_feedback = ""
        self.shared_feedback_until = 0.0
        self.renderer = PaintingRenderer(metrics, theme, screen)
        self.clock = pygame.time.Clock()
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

        # Canvas styling: warm crisp white studio paper
        self.canvas_background = (255, 255, 255)
        self.canvas = self._new_blank_surface()
        self.base_canvas = self.canvas.copy()
        if self.records:
            self._open(self.records[0])
        else:
            self._new()

    # -- geometry proxies (renderer owns metrics-aware rects) ---------------

    @property
    def palette_height(self) -> int:
        return self.renderer.palette_height

    @property
    def canvas_rect(self) -> pygame.Rect:
        return self.renderer.canvas_rect

    # -- lifecycle --------------------------------------------------------

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
                    self.handle_pointer_down(event.pos)
                elif event.type == pygame.MOUSEMOTION and self.drawing:
                    self.handle_pointer_motion(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    running = self.handle_pointer_up(event.pos)
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event)
            self._step_frame()
            self._draw()
            pygame.display.flip()
            if not ready_published:
                mark_activity_ready()
                ready_published = True
            self.clock.tick(30)
        self._save()
        pygame.quit()
        return 0

    def _step_frame(self) -> None:
        self._autosave()
        if self.shared_feedback and time.monotonic() >= self.shared_feedback_until:
            self.shared_feedback = ""

    # -- input routing ----------------------------------------------------

    def handle_pointer_down(self, pos: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, pos):
            return
        self._mouse_down(pos)

    def handle_pointer_motion(self, pos: tuple[int, int]) -> None:
        self._mouse_motion(pos)

    def handle_pointer_up(self, pos: tuple[int, int]) -> bool:
        if not _is_safe_point(self.screen, pos):
            # Allow lift to still finish a stroke even if released in chrome?
            # For painting, ignore chrome lifts to avoid spurious tool taps.
            if self.drawing:
                self._finish_stroke()
                return True
            return True
        return self._mouse_up(pos)

    def handle_resize(self, event: pygame.event.Event) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        # Rebuild renderer caches for new size
        self.renderer.on_resize(self.metrics, self.screen)
        # Recreate canvas surfaces sized to new canvas_rect
        # Keep existing artwork scaled/thumbnail-aware? For now create blank
        # and reload current painting at new size (centered).
        if self.current is not None:
            try:
                # Re-decode current PNG at new size
                surface = _decode_png(self.repository.load_png(self.current.painting_id), self.canvas_rect.size)
                self.canvas = surface
                self.base_canvas = surface.copy()
                self.history.clear()
                self.active_points = []
                self.continuation_only = False
            except Exception:
                pass

    # -- internal mouse handlers (preserve original semantics) ------------

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
        if len(self.active_points) >= 2048:  # MAX_STROKE_POINTS alias, keep literal bound
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
                    if len(self.active_points) >= 2048:
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
        shared = self.renderer.shared_export_button() if self.creations is not None else None
        if shared is not None and shared.collidepoint(pos) and self.mode == "paint":
            self._publish_current()
            return True
        if self.mode == "gallery":
            for rect, record in self.renderer.gallery_cards(self.records):
                if rect.collidepoint(pos):
                    self._open(record)
                    break
            return True
        for rect, index in self.renderer._color_buttons():
            if rect.collidepoint(pos):
                self.selected_color = index
                self.eraser = False
                return True
        for rect, index in self.renderer._size_buttons():
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
            record = self.repository.create(_encode_png(blank))
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
            surface = _decode_png(self.repository.load_png(record.painting_id), self.canvas_rect.size)
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
        # Import here to keep content constants single source
        if __package__:
            from .painting_content import AUTOSAVE_IDLE_SECONDS
        else:
            from painting_content import AUTOSAVE_IDLE_SECONDS
        if self.dirty and time.monotonic() - self.last_change >= AUTOSAVE_IDLE_SECONDS:
            self._save()

    def _save(self) -> bool:
        if not self.dirty or self.current is None:
            return True
        try:
            record = self.repository.save_png(self.current.painting_id, _encode_png(self.canvas))
        except (RuntimeError, ValueError, OSError):
            self.save_error = True
            return False
        self.current = record
        self.records = [record, *[item for item in self.records if item.painting_id != record.painting_id]]
        self.renderer.invalidate_thumbnail(record.painting_id)
        self.dirty = False
        self.save_error = False
        return True

    def _publish_current(self) -> None:
        """Explicit copy into My Creations, never an automatic autosave export."""
        if self.creations is None or self.current is None:
            return
        if not self._save():
            self.shared_feedback = "error"
            self.shared_feedback_until = time.monotonic() + 2.0
            return
        try:
            private_name = self.repository.private_png_name(self.current.painting_id)
            png = self.repository.load_png(self.current.painting_id)
            signature = (self.current.painting_id, hashlib.sha256(png).hexdigest())
            if signature != self._last_shared:
                self.creations.publish_private_file(
                    private_name, media_type="image/png", role="drawing",
                )
                self._last_shared = signature
            self.shared_feedback = "saved"
        except (RuntimeError, ValueError, OSError):
            self.shared_feedback = "error"
        self.shared_feedback_until = time.monotonic() + 2.0

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

    # -- drawing --------------------------------------------------------

    def _draw(self) -> None:
        self.renderer.draw_studio_background(self.screen)
        self.renderer.draw_toolbar(
            self.screen, self.mode, self.history, self.eraser, self.dirty,
            self.save_error,
            shared_available=self.creations is not None,
            shared_feedback=self.shared_feedback,
        )
        if self.mode == "gallery":
            self.renderer.draw_gallery(self.screen, self.records, self.repository)
        else:
            self.renderer.draw_canvas(self.screen, self.canvas)
            self.renderer.draw_palette(self.screen, self.selected_color, self.eraser, self.selected_size)
        draw_activity_pointer(self.screen)


__all__ = ["PaintingApp"]
