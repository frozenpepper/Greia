"""Lifecycle owner for the Painting Activity.

Owns screen/canvas/metrics, domain model, renderer, kit controls and input
routing. Delegates rules to the pure model, presentation to the renderer and
every button/swatch/tile to the shared control kit (ADR 0037), so the studio
works with mouse, touch, keyboard (arrows + Space/Enter) and controller
(D-pad focus, left-stick Greia virtual pointer, south button to paint/press).
Publishes READY after the first flip in the same loop.
"""

from __future__ import annotations

import hashlib
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_controls import (
    ControlKit,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback
from greia_platform.activity_ui import ChildUiMetrics, draw_activity_pointer
from greia_platform.pygame_canvas import activity_viewport_for_surface
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator

if __package__:
    from .painting_audio import PaintingSounds
    from .painting_content import (
        AUTOSAVE_IDLE_SECONDS,
        BRUSH_SIZES,
        COLORS,
        CREATION_PICKER_POLL_SECONDS,
        FEEDBACK_SECONDS,
        GALLERY_PAGE_SIZE,
        LIBRARY_FULL_SECONDS,
        MAX_STROKE_POINTS,
        STAMP_IDS,
    )
    from .painting_controls import PaintingControls, PaintingSheet, PaintingSheets
    from .painting_input import ControllerPointer
    from .painting_model import PaintingRecord, PaintingRepository, Stamp, Stroke, StrokeHistory
    from .painting_renderer import FxBurst, PaintingRenderer, _decode_png, _encode_png, _png_size
else:  # pragma: no cover - runtime/script fallback
    from painting_audio import PaintingSounds
    from painting_content import (
        AUTOSAVE_IDLE_SECONDS,
        BRUSH_SIZES,
        COLORS,
        CREATION_PICKER_POLL_SECONDS,
        FEEDBACK_SECONDS,
        GALLERY_PAGE_SIZE,
        LIBRARY_FULL_SECONDS,
        MAX_STROKE_POINTS,
        STAMP_IDS,
    )
    from painting_controls import PaintingControls, PaintingSheet, PaintingSheets
    from painting_input import ControllerPointer
    from painting_model import PaintingRecord, PaintingRepository, Stamp, Stroke, StrokeHistory
    from painting_renderer import FxBurst, PaintingRenderer, _decode_png, _encode_png, _png_size

_ARROWS = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -3, pygame.K_DOWN: 3}


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
        *,
        kit: ControlKit | None = None,
        clock=time.monotonic,
    ) -> None:
        self.screen = screen
        self.metrics = metrics
        self.theme = theme
        self.repository = repository
        self.creations = creations
        self._clock = clock
        self._last_shared: tuple[str, str] | None = None
        self.shared_feedback = ""
        self.shared_feedback_until = 0.0
        self.shared_import_request: str | None = None
        self.shared_import_state = ""
        self.shared_import_feedback_until = 0.0
        self.shared_import_next_poll = 0.0
        # Painting is word-free: tools are pictures, save state is an icon.
        # The shared kit takes the Create Collection hue (coral) as its accent.
        self.kit = kit if kit is not None else ControlKit(GreiaTypography(), ControlTheme.for_accent("coral"))
        self.renderer = PaintingRenderer(metrics, theme, screen, kit=self.kit)
        self.sounds = PaintingSounds()
        self.clock = pygame.time.Clock()
        self.records = self.repository.list_records()
        self.current: PaintingRecord | None = None
        self.page: str | None = None  # colouring page of the open painting/draft
        self.outline: pygame.Surface | None = None
        self.mode = "paint"
        self.selected_color = 1
        self.selected_size = 1
        self.tool = "brush"  # brush | eraser | stamp
        self.stamp_index = 0
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
        self.pending_delete: PaintingRecord | None = None
        self._fx: list[FxBurst] = []
        self._pointer_pressed = False
        self._stamp_tap = False
        # Controller: left stick drives a Greia virtual pointer (pointer profile).
        self.controller_pointer = ControllerPointer(
            lambda: self.screen.get_size(), lambda: self.canvas_rect.center,
        )
        self._last_frame = clock()
        self.running = True

        try:
            self.cast: CastFeedback | None = CastFeedback(
                "lilli", height=self.metrics.px(150), art=self.kit.art, clock=clock,
            )
        except ValueError:
            self.cast = None
        self.canvas_background = (255, 255, 255)
        self.canvas = self._new_blank_surface()
        self.base_canvas = self.canvas.copy()
        self.controls = PaintingControls(
            self.kit,
            self.renderer,
            gallery_icon=self.renderer.gallery_icon,
            colouring_icon=self.renderer.colouring_icon,
            on_gallery=self._toggle_gallery,
            on_undo=self._undo,
            on_new=self._press_new,
            on_share=self._publish_current,
            on_import=self._request_shared_png,
            on_colouring=self._open_colouring_sheet,
            on_color=self._choose_color,
            on_size=self._choose_size,
            on_eraser=self._toggle_eraser,
            on_stamp=self._open_stamp_sheet,
            on_card=self._open_index,
            on_card_delete=self._ask_delete_index,
            on_page=self._gallery_page_step,
            on_delete_focused=self._ask_delete_focused,
        )
        self.sheets = PaintingSheets(self.kit, self.renderer)
        self.surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(is_safe=lambda pos: _is_safe_point(self.screen, pos))
        if self.records:
            self._open(self.records[0])
        else:
            # A fresh blank page is only a draft until the child draws on it.
            self._new()
        self._sync_controls()
        self.controls.layer.focus(f"color.{self.selected_color}", visible=False)

    # -- compatibility / geometry proxies ---------------------------------

    @property
    def eraser(self) -> bool:
        return self.tool == "eraser"

    @eraser.setter
    def eraser(self, value: bool) -> None:
        self.tool = "eraser" if value else "brush"

    @property
    def palette_height(self) -> int:
        return self.renderer.palette_height

    @property
    def canvas_rect(self) -> pygame.Rect:
        return self.renderer.canvas_rect

    @property
    def stamp_id(self) -> str:
        return STAMP_IDS[self.stamp_index]

    # -- lifecycle --------------------------------------------------------

    def run(self) -> int:
        self.running = True
        ready_published = False
        while self.running and not activity_stop_requested():
            for event in pygame.event.get():
                self.handle_event(event)
            repeat = self._input.poll()
            if repeat is not None and not self.controller_pointer.active:
                self._dispatch_to_kit(repeat)
            self._step_frame()
            self._draw()
            pygame.display.flip()
            if not ready_published:
                mark_activity_ready()
                ready_published = True
            self.clock.tick(30)
        self._save()
        self.surfaces.close()
        pygame.quit()
        return 0

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route one Pygame event (pointer, keyboard, controller, window)."""
        if event.type == pygame.QUIT:
            if self._save():
                self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.handle_resize(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._escape()
            return
        if event.type == pygame.KEYDOWN and self.handle_key(event):
            return
        if event.type == pygame.MOUSEWHEEL:
            if self.mode == "gallery" and not self.surfaces.overlays:
                self._gallery_page_step(-1 if event.y > 0 else 1)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.controller_pointer.deactivate()
            self.handle_pointer_down(event.pos)
            return
        if event.type == pygame.MOUSEMOTION:
            self.controller_pointer.deactivate()
            self.handle_pointer_motion(event.pos)
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.handle_pointer_up(event.pos)
            return
        if self.controller_pointer.handle(event, on_down=self.handle_pointer_down, on_up=self.handle_pointer_up):
            if self.controller_pointer.active:
                self.controls.layer.focus_visible = False
            return
        translated = self._input.translate(event)
        if translated is not None and not isinstance(translated, KitPointer):
            self.controller_pointer.deactivate()
            self._dispatch_to_kit(translated)

    def _escape(self) -> None:
        if self.surfaces.overlays:
            self._close_sheet()
        elif self.mode == "gallery":
            self._toggle_gallery()
        elif self._save():
            self.running = False

    def _step_frame(self) -> None:
        now = self._clock()
        elapsed = min(0.1, max(0.0, now - self._last_frame))
        self._last_frame = now
        moved = self.controller_pointer.step(elapsed)
        if moved is not None:
            self.handle_pointer_motion(moved)
        self._autosave()
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
        if self.cast is not None:
            self.cast.update()
        self._fx = [burst for burst in self._fx if not burst.done]

    # -- input routing ----------------------------------------------------

    def handle_pointer_down(self, pos: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, pos):
            return
        if (
            not self.surfaces.overlays
            and self.mode == "paint"
            and self.canvas_rect.collidepoint(pos)
            and self.controls.layer.hit(pos) is None
        ):
            self._mouse_down(pos)
            return
        self._pointer_pressed = True
        self.surfaces.dispatch(KitPointer(PointerPhase.DOWN, pos))

    def _dispatch_to_kit(self, event) -> None:
        """Dispatch to the control kit, then re-pin gallery selection to its ring."""
        self.surfaces.dispatch(event)
        self._sync_gallery_focus_from_kit()

    def _sync_gallery_focus_from_kit(self) -> None:
        """Make the selected painting the one the focus ring is on.

        The kit moves its ring spatially (Down from New, Tab, stick, page strip
        hand-back) without telling the app, so ``gallery_focus`` -- the single
        painting that open and delete act on -- must follow it, otherwise the
        highlighted/ringed card and the acted-on painting could disagree.
        """
        slot = self.controls.focused_card_slot()
        if (
            self.mode != "gallery" or slot is None or self.surfaces.overlays
            or not self.controls.layer.focus_visible
        ):
            # A hidden ring (pointer/touch) never overrides the tapped card,
            # which pointer callbacks select by explicit index.
            return
        index = (self.gallery_focus // GALLERY_PAGE_SIZE) * GALLERY_PAGE_SIZE + slot
        if 0 <= index < len(self.records) and index != self.gallery_focus:
            self.gallery_focus = index

    def handle_key(self, event: pygame.event.Event) -> bool:
        """Gallery keyboard model; True when the key was consumed.

        Left/Right walk *every* saved painting (crossing pages), Up/Down move
        a row while it stays inside the grid and otherwise hand focus to the
        kit (toolbar above, page strip below); PageUp/PageDown flip pages.
        """
        if self.mode != "gallery" or not self.records or self.surfaces.overlays:
            return False
        key = event.key
        if key == pygame.K_PAGEUP:
            self._gallery_page_step(-1)
            return True
        if key == pygame.K_PAGEDOWN:
            self._gallery_page_step(1)
            return True
        layer = self.controls.layer
        on_card = self.controls.focused_card_slot() is not None or not layer.focus_visible
        if not on_card:
            return False
        if key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
            self._sync_gallery_focus_from_kit()
            self._open(self.records[self.gallery_focus])
            return True
        delta = _ARROWS.get(key)
        if delta is None:
            return False
        if abs(delta) == 3:
            slot = self.gallery_focus % GALLERY_PAGE_SIZE
            target = self.gallery_focus + delta
            same_page = target // GALLERY_PAGE_SIZE == self.gallery_focus // GALLERY_PAGE_SIZE
            if not (0 <= target < len(self.records)) or not same_page or (slot < 3) == (delta < 0):
                # Leaving the grid: the kit moves focus spatially from this card.
                layer.focus(self.controls.card_control_id(slot), visible=True)
                return False
        self._gallery_move(delta)
        self._focus_gallery_card()
        return True

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
        on_card = self.controls.focused_card_slot() is not None
        self.gallery_focus = page * GALLERY_PAGE_SIZE
        self._sync_gallery_targets()
        if on_card:
            # Keep the ring on the painting that is now selected.
            self.controls.layer.focus(
                self.controls.card_control_id(0), visible=self.controls.layer.focus_visible,
            )

    def _focus_gallery_card(self) -> None:
        self._sync_gallery_targets()
        self.controls.layer.focus(
            self.controls.card_control_id(self.gallery_focus % GALLERY_PAGE_SIZE), visible=True,
        )

    def _enter_gallery(self) -> None:
        self.mode = "gallery"
        self.gallery_focus = 0
        if self.current is not None:
            for index, record in enumerate(self.records):
                if record.painting_id == self.current.painting_id:
                    self.gallery_focus = index
                    break
        self._sync_controls()
        if self.records:
            self.controls.layer.focus(
                self.controls.card_control_id(self.gallery_focus % GALLERY_PAGE_SIZE),
                visible=self.controls.layer.focus_visible,
            )

    def _toggle_gallery(self) -> None:
        if not self._save():
            return
        self.sounds.play("tick")
        if self.mode == "paint":
            self._enter_gallery()
        else:
            self.mode = "paint"
            self._sync_controls()

    def handle_pointer_motion(self, pos: tuple[int, int]) -> None:
        if self.drawing:
            self._mouse_motion(pos)
            return
        if _is_safe_point(self.screen, pos):
            self.surfaces.dispatch(KitPointer(PointerPhase.MOVE, pos))

    def handle_pointer_up(self, pos: tuple[int, int]) -> bool:
        if not _is_safe_point(self.screen, pos):
            # A lift over the protected chrome still finishes a stroke but
            # never activates an Activity control.
            if self.drawing:
                self._finish_stroke()
            self._pointer_pressed = False
            self.surfaces.dispatch(KitPointer(PointerPhase.CANCEL, (-1, -1)))
            return True
        return self._mouse_up(pos)

    def handle_resize(self, event: pygame.event.Event) -> None:
        # Persist in-flight strokes at the old geometry before it changes: the
        # canvas is re-decoded from storage at the new size below.
        saved = self._save()
        self.screen = pygame.display.get_surface() or self.screen
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.renderer.on_resize(self.metrics, self.screen)
        self.controls.relayout()
        self.controller_pointer.reset()
        if self.surfaces.overlays:
            self._close_sheet()
        if not saved:
            return
        if self.current is None:
            # Blank draft: just resize the empty page.
            self.canvas = self._new_blank_surface()
            self.base_canvas = self.canvas.copy()
            self.history.clear()
            self.active_points = []
            self.continuation_only = False
            self._apply_outline(None)
            return
        try:
            payload = self.repository.load_png(self.current.painting_id)
            surface = _decode_png(payload, self.canvas_rect.size)
            self.canvas = surface
            self.base_canvas = surface.copy()
            self.history.clear()
            self.active_points = []
            self.continuation_only = False
            self._apply_outline(_png_size(payload))
        except Exception:
            pass
        self._sync_controls()

    # -- internal pointer handlers -----------------------------------------

    def _mouse_down(self, pos: tuple[int, int]) -> None:
        if self.mode != "paint" or not self.canvas_rect.collidepoint(pos):
            return
        point = self._local(pos)
        if self.tool == "stamp":
            self._place_stamp(point)
            self._stamp_tap = True
            return
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
        self._extend_stroke(previous, point)

    def _extend_stroke(self, previous: tuple[int, int], point: tuple[int, int]) -> None:
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
                    self._extend_stroke(self.active_points[-1], point)
            self._finish_stroke()
            return True
        if self._stamp_tap:
            self._stamp_tap = False
            return True
        if not self._pointer_pressed:
            # A lone release (tools/tests) is a full tap on whatever is there.
            self.surfaces.dispatch(KitPointer(PointerPhase.DOWN, pos))
        self._pointer_pressed = False
        self.surfaces.dispatch(KitPointer(PointerPhase.UP, pos))
        return True

    def _commit_active_stroke(self) -> None:
        if not self.active_points or self.continuation_only:
            self.active_points = []
            self.continuation_only = False
            return
        stroke = Stroke(self._brush_color(), self._brush_size(), tuple(self.active_points))
        self._remember(stroke)
        self.active_points = []
        self.continuation_only = False

    def _remember(self, mark: Stroke | Stamp) -> None:
        dropped = self.history.add(mark)
        if dropped is not None:
            self.renderer.render_mark(self.base_canvas, dropped)
        self.dirty = True
        self.last_change = self._clock()
        self.controls.undo.enabled = True

    def _finish_stroke(self) -> None:
        self.drawing = False
        self._commit_active_stroke()

    def _place_stamp(self, point: tuple[int, int]) -> None:
        stamp = Stamp(self.stamp_id, point, self.renderer.stamp_size(self.selected_size))
        self.renderer.render_mark(self.canvas, stamp)
        self._remember(stamp)
        self.sounds.play("pop")

    def _undo(self) -> None:
        if self.history.undo() is None:
            return
        self.canvas = self.base_canvas.copy()
        for mark in self.history.items:
            self.renderer.render_mark(self.canvas, mark)
        self.dirty = True
        self.last_change = self._clock()
        self.sounds.play("tick")
        self._sync_controls()

    # -- tool callbacks ------------------------------------------------------

    def _choose_color(self, index: int) -> None:
        self.selected_color = index
        self.tool = "brush"
        self.sounds.play("tick")
        self._sync_controls()

    def _choose_size(self, index: int) -> None:
        self.selected_size = index
        self.sounds.play("tick")
        self._sync_controls()

    def _toggle_eraser(self) -> None:
        self.tool = "brush" if self.tool == "eraser" else "eraser"
        self.sounds.play("tick")
        self._sync_controls()

    def _choose_stamp(self, index: int) -> None:
        self.stamp_index = index
        self.tool = "stamp"
        self._close_sheet()
        self.sounds.play("pop")
        self._sync_controls()

    def _press_new(self) -> None:
        if self._save():
            self._new()
            self.sounds.play("tick")

    # -- sheets (stamp picker, colouring pages, delete confirmation) --------

    def _open_stamp_sheet(self) -> None:
        if self.mode != "paint" or self.surfaces.overlays:
            return
        self._push_sheet(self.sheets.stamps(
            self.stamp_index if self.tool == "stamp" else None,
            focus_visible=self.controls.layer.focus_visible,
            on_choose=self._choose_stamp,
            on_dismiss=self._close_sheet,
        ))
        self.sounds.play("tick")

    def _open_colouring_sheet(self) -> None:
        pages = self.renderer.outlines.available()
        if self.mode != "paint" or self.surfaces.overlays or not pages:
            return
        self._push_sheet(self.sheets.pages(
            pages,
            focus_visible=self.controls.layer.focus_visible,
            on_choose=self._start_colouring,
            on_dismiss=self._close_sheet,
        ))
        self.sounds.play("tick")

    def _start_colouring(self, page: str) -> None:
        self._close_sheet()
        if not self._save():
            return
        if self.repository.is_full():
            self._show_full_shelf()
            return
        self._reset_canvas(None)
        self.mode = "paint"
        self.page = page
        self._apply_outline(None)
        self.tool = "brush"
        self.sounds.play("pop")
        self._sync_controls()

    def _ask_delete_index(self, index: int) -> None:
        if 0 <= index < len(self.records):
            self.gallery_focus = index
            self._ask_delete(self.records[index])

    def _ask_delete_focused(self) -> None:
        self._sync_gallery_focus_from_kit()
        if self.records:
            self._ask_delete(self.records[self.gallery_focus])

    def _ask_delete(self, record: PaintingRecord) -> None:
        """Deliberate delete: a preview of the painting, cancel focused first."""
        if self.surfaces.overlays or not self._save():
            return
        self.pending_delete = record

        def load_preview(size: tuple[int, int]) -> pygame.Surface | None:
            try:
                return _decode_png(self.repository.load_png(record.painting_id), size)
            except (RuntimeError, ValueError, OSError):
                return None

        self._push_sheet(self.sheets.delete(
            load_preview, on_cancel=self._close_sheet, on_confirm=self._confirm_delete,
        ))

    def _confirm_delete(self) -> None:
        record = self.pending_delete
        self._close_sheet()
        if record is None:
            return
        try:
            removed = self.repository.delete(record.painting_id)
        except (RuntimeError, ValueError, OSError):
            self.save_error = True
            return
        if not removed:
            return
        self.sounds.play("swish")
        self.records = self.repository.list_records()
        self.renderer.thumbnail_cache.clear()
        if self.current is not None and self.current.painting_id == record.painting_id:
            self._reset_canvas(None)
        self.library_full_until = 0.0
        self.gallery_focus = max(0, min(self.gallery_focus, len(self.records) - 1))
        self._sync_controls()
        if self.records:
            self.controls.layer.focus(
                self.controls.card_control_id(self.gallery_focus % GALLERY_PAGE_SIZE),
                visible=self.controls.layer.focus_visible,
            )
        self._burst("fx.dust_puff", self.renderer.canvas_rect.center)

    def _push_sheet(self, sheet: PaintingSheet) -> None:
        if self.drawing:
            self._finish_stroke()
        self.surfaces.push_overlay(sheet)

    def _close_sheet(self) -> None:
        self.pending_delete = None
        while self.surfaces.overlays:
            self.surfaces.pop_overlay()

    # -- painting lifecycle ------------------------------------------------

    def _new(self) -> None:
        """Start a fresh page without persisting an empty drawing.

        A blank page is only an in-memory draft: no record or PNG is written
        until the child actually draws (see ``_save``). Pressing New on a page
        that is still blank reuses it instead of piling up empty records.
        """
        if self._canvas_is_blank() and not self.dirty and self.current is None:
            self.mode = "paint"
            self.active_points = []
            self.continuation_only = False
            self.save_error = False
            if self.page is not None:
                self.page = None
                self._apply_outline(None)
        elif self.repository.is_full():
            # Never evict old work: show the full shelf and let the child
            # browse or delete; the current painting stays open and untouched.
            self._show_full_shelf()
            return
        else:
            self._reset_canvas(None)
            self.mode = "paint"
        if hasattr(self, "controls"):
            self._sync_controls()

    def _show_full_shelf(self) -> None:
        self.library_full_until = self._clock() + LIBRARY_FULL_SECONDS
        self._enter_gallery()

    def _reset_canvas(self, record: PaintingRecord | None) -> None:
        blank = self._new_blank_surface()
        self.current = record
        self.page = None
        self.outline = None
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

    def _open_index(self, index: int) -> None:
        if 0 <= index < len(self.records):
            self.gallery_focus = index
            self._open(self.records[index])

    def _open(self, record: PaintingRecord) -> bool:
        if not self._save():
            return False
        try:
            payload = self.repository.load_png(record.painting_id)
            surface = _decode_png(payload, self.canvas_rect.size)
        except (RuntimeError, ValueError, OSError):
            self.save_error = True
            return False
        self.current = record
        self.page = record.page
        self.mode = "paint"
        self.canvas = surface
        self.base_canvas = surface.copy()
        self.history.clear()
        self.active_points = []
        self.continuation_only = False
        self.dirty = False
        self.save_error = False
        self._apply_outline(_png_size(payload))
        if hasattr(self, "controls"):
            self._sync_controls()
        return True

    def _apply_outline(self, png_size: tuple[int, int] | None) -> None:
        """Build the one colouring overlay for the open painting (or none)."""
        if self.page is None:
            self.outline = None
            return
        self.outline = self.renderer.outlines.overlay(self.page, self.canvas_rect.size, png_size=png_size)

    def _new_blank_surface(self) -> pygame.Surface:
        surface = pygame.Surface(self.canvas_rect.size)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        surface.fill(self.canvas_background)
        return surface

    def _autosave(self) -> None:
        if self.dirty and self._clock() - self.last_change >= AUTOSAVE_IDLE_SECONDS:
            self._save()

    def _flattened(self) -> pygame.Surface:
        if self.outline is None:
            return self.canvas
        flat = self.canvas.copy()
        flat.blit(self.outline, (0, 0))
        return flat

    def _save(self) -> bool:
        if not self.dirty:
            return True
        if self.current is None and self._canvas_is_blank():
            # Drew and then erased/undid everything on a draft: nothing to keep.
            self.dirty = False
            return True
        try:
            payload = _encode_png(self._flattened())
            if self.current is None:
                record = self.repository.create(payload, page=self.page)
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

    # -- My Creations ------------------------------------------------------

    def _publish_current(self) -> None:
        """Explicit copy into My Creations, never an automatic autosave export."""
        if self.creations is None:
            return
        if not self._save():
            self.shared_feedback = "error"
            self.shared_feedback_until = time.monotonic() + FEEDBACK_SECONDS
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
            self._celebrate()
        except (RuntimeError, ValueError, OSError):
            self.shared_feedback = "error"
        self.shared_feedback_until = time.monotonic() + FEEDBACK_SECONDS

    def _celebrate(self) -> None:
        """One feedback grammar: Lilli cheers, sparkles, a soft chime."""
        cast = getattr(self, "cast", None)
        if cast is not None:
            cast.correct()
        sounds = getattr(self, "sounds", None)
        if sounds is not None:
            sounds.play("chime")
        renderer = getattr(self, "renderer", None)
        if renderer is not None and hasattr(renderer, "shared_export_button"):
            anchor = renderer.shared_export_button()
            self._burst("fx.sparkle", anchor.center if anchor is not None else renderer.canvas_rect.center)

    def _burst(self, asset_id: str, center: tuple[int, int]) -> None:
        renderer = getattr(self, "renderer", None)
        if renderer is None or not hasattr(renderer, "fx_frames"):
            return
        frames = renderer.fx_frames(asset_id, self.metrics.px(120))
        if frames:
            fx = getattr(self, "_fx", [])
            self._fx = [*fx[-2:], FxBurst(frames, center, clock=self._clock)]

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
            self.shared_import_feedback_until = time.monotonic() + FEEDBACK_SECONDS
            return
        try:
            request_id = self.creations.request_selection(
                media_types=("image/png",)
            )
        except (RuntimeError, ValueError, OSError):
            self.shared_import_state = "error"
            self.shared_import_feedback_until = time.monotonic() + FEEDBACK_SECONDS
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
            self.shared_import_feedback_until = time.monotonic() + FEEDBACK_SECONDS
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
            self.shared_import_feedback_until = time.monotonic() + FEEDBACK_SECONDS
            return
        if self.accept_selected_png(token):
            self.shared_import_state = "imported"
            self._celebrate()
        else:
            self.shared_import_state = "error"
        self.shared_import_feedback_until = time.monotonic() + FEEDBACK_SECONDS

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
        self.page = None
        self.outline = None
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
        if hasattr(self, "controls"):
            self._sync_controls()
        return True

    # -- brush helpers -------------------------------------------------------

    def _brush_color(self) -> tuple[int, int, int]:
        return self.canvas_background if self.tool == "eraser" else COLORS[self.selected_color]

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

    def _local(self, pos: tuple[int, int]) -> tuple[int, int]:
        return pos[0] - self.canvas_rect.left, pos[1] - self.canvas_rect.top

    # -- controls sync --------------------------------------------------------

    def _sync_controls(self) -> None:
        controls = self.controls
        controls.set_mode(
            self.mode,
            shared_available=self.creations is not None,
            colouring_available=bool(self.renderer.outlines.available()),
        )
        if self.mode == "gallery":
            self._sync_gallery_targets()
            controls.importer.enabled = self.shared_import_state != "pending"
        else:
            controls.sync_paint(
                color_index=self.selected_color,
                size_index=self.selected_size,
                tool=self.tool,
                can_undo=bool(self.history.items),
                stamp_icon=self.renderer.stamp_icon(self.stamp_id, self.metrics.px(46)),
            )

    def _sync_gallery_targets(self) -> None:
        if self.mode != "gallery":
            return
        page = self.gallery_focus // GALLERY_PAGE_SIZE
        cards = [rect for rect, _record in self.renderer.gallery_cards(self.records, page)]
        self.controls.sync_gallery(
            page=page,
            page_count=self.renderer.gallery_page_count(len(self.records)),
            cards=cards,
            has_focus_card=bool(self.records),
        )

    # -- drawing --------------------------------------------------------

    def _status(self) -> str:
        if self.save_error:
            return "error"
        return "saving" if self.dirty else "saved"

    def _draw(self) -> None:
        renderer = self.renderer
        renderer.draw_studio_background(self.screen)
        if self.mode == "gallery":
            renderer.draw_gallery(
                self.screen, self.records, self.repository,
                page=self.gallery_focus // GALLERY_PAGE_SIZE,
                focus_index=self.gallery_focus if self.records else None,
                library_full=self._clock() < self.library_full_until,
            )
        else:
            renderer.draw_canvas(self.screen, self.canvas, self.outline)
            renderer.draw_tray(self.screen, self.selected_color, self.tool)
            renderer.draw_status(self.screen, self._status())
        self.surfaces.draw(self.screen)
        for burst in self._fx:
            burst.draw(self.screen)
        if self.cast is not None and self.cast.animating:
            crect = self.canvas_rect
            self.cast.draw(self.screen, (crect.right - self.metrics.px(80), crect.bottom + self.metrics.px(12)))
        virtual = self.controller_pointer.position
        if self.controller_pointer.active and virtual is not None:
            draw_activity_pointer(self.screen, virtual)
        else:
            draw_activity_pointer(self.screen)


__all__ = ["PaintingApp"]
