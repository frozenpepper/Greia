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

from greia_platform.activity_api import activity_stop_requested, get_profile_locale, mark_activity_ready
from greia_platform.activity_ui import ChildUiMetrics, draw_activity_pointer
from greia_platform.pygame_canvas import activity_viewport_for_surface
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from pathlib import Path

if __package__:
    from .painting_content import BRUSH_SIZES, COLORS, CREATION_PICKER_POLL_SECONDS, GALLERY_PAGE_SIZE
    from .painting_model import PaintingRecord, PaintingRepository, Stroke, StrokeHistory
    from .painting_renderer import PaintingRenderer, _decode_png, _encode_png
else:  # pragma: no cover - runtime/script fallback
    from painting_content import BRUSH_SIZES, COLORS, CREATION_PICKER_POLL_SECONDS, GALLERY_PAGE_SIZE
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
        self.shared_import_request: str | None = None
        self.shared_import_state = ""
        self.shared_import_feedback_until = 0.0
        self.shared_import_next_poll = 0.0
        # Renderer never reads global locale or owns translation fallback.
        # The manifest still advertises only IT/EN; ES/FR source is staged.
        context = resolve_activity_locale(
            get_profile_locale(),
            ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it"),
        )
        resources = LocalizedResources(Path(__file__).parent, context) if context else None
        status_labels = (
            {name: resources.text(f"status.{name}") for name in ("saved", "saving", "error")}
            if resources is not None else None
        )
        self.renderer = PaintingRenderer(metrics, theme, screen, status_labels=status_labels)
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
        # Gallery cursor over *all* saved paintings; the visible 3x2 page is
        # derived from it so every drawing is reachable by arrows or paging.
        self.gallery_focus = 0
        self.library_full_until = 0.0

        # Canvas styling: warm crisp white studio paper
        self.canvas_background = (255, 255, 255)
        self.canvas = self._new_blank_surface()
        self.base_canvas = self.canvas.copy()
        if self.records:
            self._open(self.records[0])
        else:
            # A fresh blank page is only a draft until the child draws on it.
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
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
                elif event.type == pygame.MOUSEWHEEL and self.mode == "gallery":
                    self._gallery_page_step(-1 if event.y > 0 else 1)
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
        now = time.monotonic()
        if self.shared_feedback and now >= self.shared_feedback_until:
            self.shared_feedback = ""
        if (
            self.shared_import_request is not None
            and now >= self.shared_import_next_poll
        ):
            self._poll_shared_png()
        elif (
            self.shared_import_state
            and self.shared_import_state != "pending"
            and now >= self.shared_import_feedback_until
        ):
            self.shared_import_state = ""

    # -- input routing ----------------------------------------------------

    def handle_pointer_down(self, pos: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, pos):
            return
        self._mouse_down(pos)

    def handle_key(self, event: pygame.event.Event) -> None:
        """Keyboard/controller-mapped gallery navigation (arrows + Space/Enter)."""
        if self.mode != "gallery" or not self.records:
            return
        key = event.key
        if key == pygame.K_LEFT:
            self._gallery_move(-1)
        elif key == pygame.K_RIGHT:
            self._gallery_move(1)
        elif key == pygame.K_UP:
            self._gallery_move(-3)
        elif key == pygame.K_DOWN:
            self._gallery_move(3)
        elif key == pygame.K_PAGEUP:
            self._gallery_page_step(-1)
        elif key == pygame.K_PAGEDOWN:
            self._gallery_page_step(1)
        elif key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
            self._open(self.records[self.gallery_focus])

    def _gallery_move(self, delta: int) -> None:
        count = len(self.records)
        if count:
            self.gallery_focus = max(0, min(count - 1, self.gallery_focus + delta))

    def _gallery_page_step(self, direction: int) -> None:
        """Move one 3x2 page, landing on that page's first painting."""
        count = len(self.records)
        if not count:
            return
        pages = self.renderer.gallery_page_count(count)
        page = max(0, min(pages - 1, self.gallery_focus // GALLERY_PAGE_SIZE + direction))
        self.gallery_focus = page * GALLERY_PAGE_SIZE

    def _enter_gallery(self) -> None:
        self.mode = "gallery"
        self.gallery_focus = 0
        if self.current is not None:
            for index, record in enumerate(self.records):
                if record.painting_id == self.current.painting_id:
                    self.gallery_focus = index
                    break

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
        # Persist in-flight strokes at the old geometry before it changes: the
        # canvas is re-decoded from storage at the new size below.
        saved = self._save()
        self.screen = pygame.display.get_surface() or self.screen
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        # Rebuild renderer caches for new size
        self.renderer.on_resize(self.metrics, self.screen)
        if not saved:
            return
        if self.current is None:
            # Blank draft: just resize the empty page.
            self.canvas = self._new_blank_surface()
            self.base_canvas = self.canvas.copy()
            self.history.clear()
            self.active_points = []
            self.continuation_only = False
            return
        try:
            # Re-decode current PNG at new size (centered, aspect preserved)
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
            if self.mode == "paint":
                self._enter_gallery()
            else:
                self.mode = "paint"
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
        if shared is not None and shared.collidepoint(pos):
            if self.mode == "paint":
                self._publish_current()
            elif self.mode == "gallery":
                self._request_shared_png()
            return True
        if self.mode == "gallery":
            previous, following = self.renderer.gallery_nav_buttons()
            if previous.collidepoint(pos):
                self._gallery_page_step(-1)
                return True
            if following.collidepoint(pos):
                self._gallery_page_step(1)
                return True
            page = self.gallery_focus // GALLERY_PAGE_SIZE
            for rect, record in self.renderer.gallery_cards(self.records, page):
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
        """Start a fresh page without persisting an empty drawing.

        A blank page is only an in-memory draft: no record or PNG is written
        until the child actually draws (see ``_save``). Pressing New on a page
        that is still blank reuses it instead of piling up empty records.
        """
        if self._canvas_is_blank() and not self.dirty:
            self.mode = "paint"
            self.active_points = []
            self.continuation_only = False
            self.save_error = False
            return
        if self.repository.is_full():
            # Never evict old work: show the full shelf and let the child
            # browse; the current painting stays open and untouched.
            self.library_full_until = time.monotonic() + 4.0
            self._enter_gallery()
            return
        blank = self._new_blank_surface()
        self.current = None
        self.mode = "paint"
        self.canvas = blank
        self.base_canvas = blank.copy()
        self.history.clear()
        self.active_points = []
        self.continuation_only = False
        self.dirty = False
        self.save_error = False

    def _canvas_is_blank(self) -> bool:
        blank = self._new_blank_surface()
        if self.canvas.get_size() != blank.get_size():
            return False
        return pygame.image.tostring(self.canvas, "RGB") == pygame.image.tostring(blank, "RGB")

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
        if not self.dirty:
            return True
        if self.current is None and self._canvas_is_blank():
            # Drew and then erased/undid everything on a draft: nothing to keep.
            self.dirty = False
            return True
        try:
            payload = _encode_png(self.canvas)
            if self.current is None:
                record = self.repository.create(payload)
            else:
                record = self.repository.save_png(self.current.painting_id, payload)
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
        if self.creations is None:
            return
        if not self._save():
            self.shared_feedback = "error"
            self.shared_feedback_until = time.monotonic() + 2.0
            return
        if self.current is None:
            return  # nothing drawn yet: there is nothing to publish
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

    def _request_shared_png(self) -> None:
        """Start one nonblocking platform picker from Painting's own gallery."""
        if (
            self.creations is None
            or self.mode != "gallery"
            or self.shared_import_request is not None
        ):
            return
        if not self._save():
            self.shared_import_state = "error"
            self.shared_import_feedback_until = time.monotonic() + 2.0
            return
        try:
            request_id = self.creations.request_selection(
                media_types=("image/png",)
            )
        except (RuntimeError, ValueError, OSError):
            self.shared_import_state = "error"
            self.shared_import_feedback_until = time.monotonic() + 2.0
            return
        self.shared_import_request = request_id
        self.shared_import_state = "pending"
        self.shared_import_next_poll = time.monotonic()

    def _poll_shared_png(self) -> None:
        request_id = self.shared_import_request
        if request_id is None or self.creations is None:
            return
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.shared_import_request = None
            self.shared_import_next_poll = 0.0
            self.shared_import_state = "error"
            self.shared_import_feedback_until = time.monotonic() + 2.0
            return
        state = getattr(result, "state", None)
        if state == "pending":
            self.shared_import_next_poll = (
                time.monotonic() + CREATION_PICKER_POLL_SECONDS
            )
            return
        self.shared_import_request = None
        self.shared_import_next_poll = 0.0
        if state == "cancelled":
            self.shared_import_state = ""
            return
        token = getattr(result, "selection_token", None)
        if state != "ready" or not isinstance(token, str) or not token:
            self.shared_import_state = "error"
            self.shared_import_feedback_until = time.monotonic() + 2.0
            return
        if self.accept_selected_png(token):
            self.shared_import_state = "imported"
        else:
            self.shared_import_state = "error"
        self.shared_import_feedback_until = time.monotonic() + 2.0

    def accept_selected_png(self, selection_token: str) -> bool:
        """Import one Shell-confirmed PNG as an independent editable painting.

        The source remains an immutable shared artifact and this Activity only
        writes a copy to its own private repository. The UI owns when the
        selected session handle is delivered; this method never lists files or
        presents an Activity-specific chooser.
        """
        if self.creations is None or not self._save():
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            if (
                transfer.record.get("media_type") != "image/png"
                or not isinstance(transfer.payload, bytes)
                or transfer.record.get("sha256") != hashlib.sha256(transfer.payload).hexdigest()
            ):
                raise ValueError("selected picture failed integrity validation")
            # Decode before creating a private record. A corrupted image must
            # never leave a half-initialized project or replace the open canvas.
            canvas = _decode_png(transfer.payload, self.canvas_rect.size)
            record = self.repository.create(transfer.payload)
        except (RuntimeError, ValueError, OSError):
            self.save_error = True
            return False
        self.current = record
        self.records = [
            record,
            *[item for item in self.records if item.painting_id != record.painting_id],
        ]
        self.mode = "paint"
        self.canvas = canvas
        self.base_canvas = canvas.copy()
        self.history.clear()
        self.active_points = []
        self.continuation_only = False
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

    # -- drawing --------------------------------------------------------

    def _draw(self) -> None:
        self.renderer.draw_studio_background(self.screen)
        self.renderer.draw_toolbar(
            self.screen, self.mode, self.history, self.eraser, self.dirty,
            self.save_error,
            shared_available=self.creations is not None,
            shared_feedback=self.shared_feedback,
            shared_import_state=self.shared_import_state,
        )
        if self.mode == "gallery":
            self.renderer.draw_gallery(
                self.screen, self.records, self.repository,
                page=self.gallery_focus // GALLERY_PAGE_SIZE,
                focus_index=self.gallery_focus if self.records else None,
                library_full=time.monotonic() < self.library_full_until,
            )
        else:
            self.renderer.draw_canvas(self.screen, self.canvas)
            self.renderer.draw_palette(self.screen, self.selected_color, self.eraser, self.selected_size)
        draw_activity_pointer(self.screen)


__all__ = ["PaintingApp"]
