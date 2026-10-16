"""Lifecycle owner for the Writing Activity.

Owns screen/metrics/typography, domain model, renderer, kit controls and
input routing. Delegates rules to the pure model, presentation to the
renderer and every button/tile to the shared control kit (ADR 0037).

Writing is a ``text`` interaction profile Activity (ACTIVITY_INPUT_STANDARDS):
the physical keyboard types, and Space/Enter/arrows keep their text meaning.
Keyboard users move into the toolbar deliberately with Tab (arrows + Enter
there, Tab/Escape or simply typing returns to the page); a controller's
D-pad/stick and south button operate the toolbar, sheets and gallery.
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
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.emoji_palette import EmojiPalette
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.pygame_canvas import PygamePointerSprite, PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import FontRole, GreiaTypography, grapheme_boundaries, grapheme_spans
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .writing_audio import WritingSounds
    from .writing_content import (
        AUTOSAVE_IDLE_SECONDS,
        BODY_TEXT_SIZE,
        CARD_TEXT_SIZE,
        CAST_FRIEND,
        CREATION_PICKER_POLL_SECONDS,
        DEFAULT_TINT,
        FEEDBACK_SECONDS,
        GALLERY_PAGE_SIZE,
        LIBRARY_FULL_SECONDS,
        TINT_IDS,
    )
    from .writing_controls import WritingControls, WritingSheet, WritingSheets
    from .writing_model import DocumentRecord, DocumentRepository, TextBuffer, UndoHistory
    from .writing_renderer import FxBurst, VisualLine, WritingRenderer
else:  # pragma: no cover - runtime/script fallback
    from writing_audio import WritingSounds
    from writing_content import (
        AUTOSAVE_IDLE_SECONDS,
        BODY_TEXT_SIZE,
        CARD_TEXT_SIZE,
        CAST_FRIEND,
        CREATION_PICKER_POLL_SECONDS,
        DEFAULT_TINT,
        FEEDBACK_SECONDS,
        GALLERY_PAGE_SIZE,
        LIBRARY_FULL_SECONDS,
        TINT_IDS,
    )
    from writing_controls import WritingControls, WritingSheet, WritingSheets
    from writing_model import DocumentRecord, DocumentRepository, TextBuffer, UndoHistory
    from writing_renderer import FxBurst, VisualLine, WritingRenderer

_ARROWS = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -3, pygame.K_DOWN: 3}
_NAV_KEYS = {pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN}
_ACTIVATE_KEYS = {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}
_KEYBOARD_EVENTS = {pygame.KEYDOWN, pygame.KEYUP}
# The caret blinks this long after the last edit, then stays on.
CARET_BLINK_SECONDS = 10.0


def _key_text(key: int) -> str:
    """The TEXTINPUT SDL commits after ``key`` (only Space among activators)."""

    return " " if key == pygame.K_SPACE else ""


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(
        region.x <= x < region.right and region.y <= y < region.bottom
        for region in viewport.protected_regions
    )


class WritingApp:
    """Coordinate Writing lifecycle without owning domain or rendering details."""

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas | None,
        metrics: ChildUiMetrics,
        typography: GreiaTypography,
        theme,
        repository: DocumentRepository,
        creations=None,
        *,
        kit: ControlKit | None = None,
        clock=time.monotonic,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.metrics = metrics
        self.typography = typography
        self.theme = theme
        self.repository = repository
        self.creations = creations
        self._clock = clock
        self.shared_request: str | None = None
        self.shared_next_poll = 0.0
        self.shared_state = ""
        self.shared_feedback_until = 0.0
        self._last_shared_digest: dict[str, str] = {}
        self.font_size = self.metrics.px(BODY_TEXT_SIZE)
        self.small_font_size = self.metrics.px(CARD_TEXT_SIZE)
        # Writing is word-free chrome on the Create Collection hue (coral),
        # the same family as Painting.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("coral"))
        self.emoji_palette = EmojiPalette()
        self.emoji_picker_open = False
        self.renderer = WritingRenderer(
            typography, metrics, theme, self.emoji_palette, self.font_size, self.small_font_size, kit=self.kit,
        )
        self.sounds = WritingSounds()
        self.records = self.repository.list_records()
        self.current: DocumentRecord | None = None
        self.tint = DEFAULT_TINT
        self.buffer = TextBuffer()
        self.undo_history = UndoHistory()
        self.mode = "edit"
        self.dirty = False
        self.save_error = False
        self.last_change = 0.0
        self.scroll_line = 0
        # Gallery cursor over *all* saved documents; the visible 3x2 page is
        # derived from it so every page is reachable by arrows or paging.
        self.gallery_focus = 0
        self.library_full_until = 0.0
        self.pending_delete: DocumentRecord | None = None
        self.toolbar_focus = False
        self.running = True
        # Text of the last key a control consumed ("" when none).
        self._swallow_text = ""
        self._pointer = PygamePointerSprite()
        self._pointer_owner: str | None = None
        self._last_typing = clock()
        self._fx: list[FxBurst] = []
        try:
            self.cast: CastFeedback | None = CastFeedback(
                CAST_FRIEND, height=self.metrics.px(150), art=self.kit.art, clock=clock,
            )
        except ValueError:
            self.cast = None
        self.controls = WritingControls(
            self.kit,
            self.renderer,
            lambda: self.editor_rect,
            on_gallery=self._toggle_gallery,
            on_undo=self._undo,
            on_emoji=self._toggle_emoji,
            on_new=self._press_new,
            on_share=self._publish_current_document,
            on_import=self._request_shared_document,
            on_card=self._open_index,
            on_card_delete=self._ask_delete_index,
            on_page=self._gallery_page_step,
            on_delete_focused=self._ask_delete_focused,
        )
        self.sheets = WritingSheets(self.kit, self.renderer)
        self.surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(is_safe=lambda pos: _is_safe_point(self.screen, pos))
        if self.records:
            self._open(self.records[0])
        else:
            # A fresh empty page is only a draft until something is written.
            self._new()
        self._sync_controls()
        pygame.key.start_text_input()

    @property
    def editor_rect(self) -> pygame.Rect:
        return self.metrics.activity_content_rect(top_gap=6)

    @property
    def view_rect(self) -> pygame.Rect:
        """Where text lines show: the page, minus the emoji sheet when open."""
        return self.renderer.text_view_rect(self.editor_rect, self.emoji_picker_open)

    # -- public lifecycle -----------------------------------------------

    def run(self) -> int:
        # Input redraws; the caret blink, banners and save status redraw when
        # their visible state changes; keepalive bounds anything else.
        frames = FrameGovernor(redraw_on_input=True, keepalive_seconds=1.0)
        self.running = True
        ready_published = False
        shown: tuple[object, ...] | None = None
        while self.running and not activity_stop_requested():
            for event in frames.events():
                self.handle_event(event)
            repeat = self._input.poll()
            if repeat is not None:
                self._route_semantic(repeat)
            self._step_frame()
            signature = self._visual_signature()
            frame = frames.frame(
                dirty=signature != shown or self.controls.layer.invalidation.should_draw,
                animating=bool(self._fx) or (self.cast is not None and self.cast.animating),
            )
            if frame is FrameKind.POINTER and ready_published:
                # Writing draws straight to the display: hover moves only
                # Greia's save-under pointer (Acer re-sweep R.3), the page is
                # not re-rendered.
                self._pointer.refresh(self.screen)
            elif frame is not FrameKind.SKIP:
                self._draw()
                shown = signature
                # Legacy optional canvas seam (disabled in production composition).
                if self.canvas is not None:
                    try:
                        self.canvas.present(clear=(252, 246, 232))
                    except Exception:
                        pass
                pygame.display.flip()
                if not ready_published:
                    mark_activity_ready()
                    ready_published = True
            frames.wait(polling=self._input.repeating)
        self._save()
        pygame.key.stop_text_input()
        self.surfaces.close()
        self.typography.clear()
        pygame.quit()
        return 0

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Route one Pygame event; returns False once the Activity should stop."""
        if event.type == pygame.QUIT:
            if self._save():
                self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self.handle_resize(event)
        elif event.type == pygame.KEYDOWN:
            self.running = self.handle_key(event) and self.running
        elif event.type == pygame.TEXTINPUT:
            self._text_input(event.text)
        elif event.type == pygame.MOUSEWHEEL:
            self._wheel(event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_pointer_down(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            if _is_safe_point(self.screen, event.pos):
                self._pointer_layer(event.pos).handle_event(KitPointer(PointerPhase.MOVE, event.pos))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.handle_pointer_up(event.pos)
        elif event.type not in _KEYBOARD_EVENTS:
            translated = self._input.translate(event)
            if isinstance(translated, SemanticInputEvent):
                self._route_semantic(translated)
        return self.running

    # -- keyboard ----------------------------------------------------------

    def handle_key(self, event) -> bool:
        """Route one key press; returns False when the child leaves Writing."""
        self._swallow_text = ""
        key = event.key
        mod = getattr(event, "mod", 0)
        if key == pygame.K_ESCAPE:
            return self._escape()
        sheet = self._top_sheet()
        if sheet is not None:
            self._sheet_key(sheet, key, mod)
            return True
        if self.mode == "gallery":
            if not self._gallery_key(key):
                self._dispatch_key(event)
                self._sync_gallery_focus_from_kit()
            return True
        if key == pygame.K_TAB:
            self._set_toolbar_focus(not self.toolbar_focus)
            return True
        if self.toolbar_focus and (key in _NAV_KEYS or key in _ACTIVATE_KEYS):
            self._dispatch_key(event)
            return True
        self._set_toolbar_focus(False)
        self._edit_key(key, mod)
        return True

    def _edit_key(self, key: int, mod: int) -> None:
        if key == pygame.K_z and mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
            self._undo()
            return
        if key == pygame.K_BACKSPACE:
            self._apply_edit(self.buffer.backspace)
        elif key == pygame.K_DELETE:
            self._apply_edit(self.buffer.delete)
        elif key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            self._apply_edit(lambda: self.buffer.insert("\n"))
        elif key == pygame.K_LEFT:
            self.buffer.move(-1)
        elif key == pygame.K_RIGHT:
            self.buffer.move(1)
        elif key == pygame.K_HOME:
            self.buffer.home()
        elif key == pygame.K_END:
            self.buffer.end()
        elif key == pygame.K_UP:
            self._move_vertical(-1)
        elif key == pygame.K_DOWN:
            self._move_vertical(1)
        else:
            return
        self._last_typing = self._clock()
        self._keep_cursor_visible()

    def _sheet_key(self, sheet: WritingSheet, key: int, mod: int) -> None:
        """Keys while a sheet is up.

        The emoji sheet is non-modal: arrows move over the emoji and Enter
        inserts the focused one once focus is shown, but Space still types a
        space and Backspace/Delete/Ctrl-Z keep editing the page beneath.
        """
        if sheet.modal:
            if key in _NAV_KEYS or key in _ACTIVATE_KEYS:
                self._dispatch_key(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))
            return
        if key in _NAV_KEYS or (key in {pygame.K_RETURN, pygame.K_KP_ENTER} and sheet.layer.focus_visible):
            self._dispatch_key(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))
            return
        if key != pygame.K_SPACE:
            self._edit_key(key, mod)

    def _dispatch_key(self, event) -> None:
        """Hand one key to the kit as semantic navigation/activation."""
        key = pygame.K_RETURN if event.key == pygame.K_KP_ENTER else event.key
        translated = self._input.translate(pygame.event.Event(pygame.KEYDOWN, key=key, mod=getattr(event, "mod", 0)))
        if isinstance(translated, SemanticInputEvent) and translated.edge is InputEdge.PRESSED:
            if self.surfaces.dispatch(translated) is UiEventResult.HANDLED:
                # A key a control consumed must not also type into the page
                # (SDL sends TEXTINPUT right after KEYDOWN for Space).
                self._swallow_text = _key_text(event.key)

    def _gallery_key(self, key: int) -> bool:
        """Gallery keyboard model; True when the key was consumed.

        Left/Right walk *every* saved page (crossing pages), Up/Down move a
        row while it stays inside the grid and otherwise hand focus to the kit
        (toolbar above, page strip below); PageUp/PageDown flip pages.
        """
        if not self.records:
            return False
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
        if key in _ACTIVATE_KEYS:
            self._swallow_text = _key_text(key)
            self._open(self.records[self.gallery_focus])
            return True
        if key == pygame.K_DELETE or key == pygame.K_BACKSPACE:
            self._ask_delete_focused()
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

    def _text_input(self, text: str) -> None:
        # Only the consumed key's own commit is dropped (Space -> " "), and
        # only as the very next text event: a stale flag must never eat a
        # later character (fast synthetic typing, Acer re-sweep R.1).
        swallow, self._swallow_text = self._swallow_text, ""
        if swallow and text == swallow:
            return
        sheet = self._top_sheet()
        if self.mode != "edit" or (sheet is not None and sheet.modal):
            return
        self._set_toolbar_focus(False)
        self._apply_edit(lambda: self.buffer.insert(text))

    def _escape(self) -> bool:
        if self.surfaces.overlays:
            self._close_sheet()
        elif self.toolbar_focus:
            self._set_toolbar_focus(False)
        elif self.mode == "gallery":
            self._toggle_gallery()
        elif self._save():
            self.running = False
            return False
        return True

    def _set_toolbar_focus(self, active: bool) -> None:
        if active == self.toolbar_focus:
            return
        self.toolbar_focus = active
        layer = self.controls.layer
        if active:
            if layer.focused_id is None or not layer.focus(layer.focused_id, visible=True):
                layer.focus("tool.gallery", visible=True)
        else:
            layer.focus_visible = False
            layer.invalidation.invalidate()

    # -- controller / semantic input ---------------------------------------

    def _route_semantic(self, event: SemanticInputEvent) -> None:
        if event.edge is not InputEdge.PRESSED:
            return
        if self.surfaces.overlays:
            self.surfaces.dispatch(event)
            return
        if event.action is SemanticAction.CANCEL:
            if self.mode == "gallery":
                self._toggle_gallery()
            else:
                self._set_toolbar_focus(False)
            return
        if self.mode == "edit":
            if not self.toolbar_focus:
                # The first press only reveals where focus is.
                self._set_toolbar_focus(True)
                return
            self.surfaces.dispatch(event)
            return
        self.surfaces.dispatch(event)
        self._sync_gallery_focus_from_kit()

    def _sync_gallery_focus_from_kit(self) -> None:
        slot = self.controls.focused_card_slot()
        if self.mode == "gallery" and slot is not None:
            index = (self.gallery_focus // GALLERY_PAGE_SIZE) * GALLERY_PAGE_SIZE + slot
            if 0 <= index < len(self.records):
                self.gallery_focus = index

    # -- pointer -----------------------------------------------------------

    def _top_sheet(self) -> WritingSheet | None:
        surfaces = getattr(self, "surfaces", None)
        overlays = surfaces.overlays if surfaces is not None else ()
        top = overlays[-1] if overlays else None
        return top if isinstance(top, WritingSheet) else None

    def _pointer_layer(self, pos: tuple[int, int]):
        sheet = self._top_sheet()
        if sheet is not None and sheet.claims(pos):
            return sheet
        return self.controls.layer

    def handle_pointer_down(self, pos: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, pos):
            return
        sheet = self._top_sheet()
        if sheet is not None and sheet.claims(pos):
            self._pointer_owner = "sheet"
            sheet.handle_event(KitPointer(PointerPhase.DOWN, pos))
            return
        if self.controls.layer.hit(pos) is not None:
            self._pointer_owner = "layer"
            self.controls.layer.handle_event(KitPointer(PointerPhase.DOWN, pos))
            return
        self._pointer_owner = "page"
        if self.mode == "edit" and self.view_rect.collidepoint(pos):
            self._set_toolbar_focus(False)
            self._place_cursor(pos)

    def handle_pointer_up(self, pos: tuple[int, int]) -> None:
        owner = self._pointer_owner
        self._pointer_owner = None
        if not _is_safe_point(self.screen, pos):
            # A lift over protected chrome never activates an Activity control.
            self.controls.layer.handle_event(KitPointer(PointerPhase.CANCEL, (-1, -1)))
            sheet = self._top_sheet()
            if sheet is not None:
                sheet.layer.handle_event(KitPointer(PointerPhase.CANCEL, (-1, -1)))
            return
        if owner is None:
            # A lone release (tools/tests) is a full tap on whatever is there.
            self.handle_pointer_down(pos)
            owner = self._pointer_owner
            self._pointer_owner = None
        sheet = self._top_sheet()
        if owner == "sheet" and sheet is not None:
            sheet.handle_event(KitPointer(PointerPhase.UP, pos))
        elif owner == "layer":
            self.controls.layer.handle_event(KitPointer(PointerPhase.UP, pos))

    def handle_pointer(self, pos: tuple[int, int]) -> bool:
        """Compatibility helper: one complete tap at ``pos``."""
        self.handle_pointer_down(pos)
        self.handle_pointer_up(pos)
        return self.running

    def _wheel(self, direction: int) -> None:
        sheet = self._top_sheet()
        if sheet is not None and sheet.modal:
            return
        if self.mode == "gallery":
            self._gallery_page_step(-1 if direction > 0 else 1)
            return
        lines = self._layout()
        visible = self.renderer.visible_line_count(self.view_rect)
        top = max(0, len(lines) - visible)
        self.scroll_line = max(0, min(top, self.scroll_line - (1 if direction > 0 else -1)))

    def handle_resize(self, event: pygame.event.Event) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.font_size = self.metrics.px(BODY_TEXT_SIZE)
        self.small_font_size = self.metrics.px(CARD_TEXT_SIZE)
        if self.canvas is not None:
            try:
                self.canvas = PygameReferenceCanvas(self.screen)
            except Exception:
                pass
        self._close_sheet()
        self.renderer.on_resize(self.metrics, self.font_size, self.small_font_size)
        self.controls.relayout()
        self._sync_controls()
        self._keep_cursor_visible()

    # -- gallery -------------------------------------------------------------

    def _gallery_move(self, delta: int) -> None:
        count = len(self.records)
        if count:
            self.gallery_focus = max(0, min(count - 1, self.gallery_focus + delta))

    def _gallery_page_step(self, direction: int) -> None:
        """Move one 3x2 page, landing on that page's first document."""
        count = len(self.records)
        if not count:
            return
        pages = self.renderer.gallery_page_count(count)
        page = max(0, min(pages - 1, self.gallery_focus // GALLERY_PAGE_SIZE + direction))
        self.gallery_focus = page * GALLERY_PAGE_SIZE
        self._sync_gallery_targets()
        layer = self.controls.layer
        if self.controls.focused_card_slot() is not None:
            # Keep one highlight: the kit focus follows the page's first card.
            layer.focus(self.controls.card_control_id(0), visible=layer.focus_visible)

    def _focus_gallery_card(self) -> None:
        self._sync_gallery_targets()
        self.controls.layer.focus(
            self.controls.card_control_id(self.gallery_focus % GALLERY_PAGE_SIZE), visible=True,
        )

    def _enter_gallery(self) -> None:
        self._close_sheet()
        self.mode = "gallery"
        self.toolbar_focus = False
        self.gallery_focus = 0
        if self.current is not None:
            for index, record in enumerate(self.records):
                if record.document_id == self.current.document_id:
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
        if self.mode == "edit":
            self._enter_gallery()
        else:
            self.mode = "edit"
            self._sync_controls()

    def _open_index(self, index: int) -> None:
        if 0 <= index < len(self.records):
            self.gallery_focus = index
            self._open(self.records[index])

    def _ask_delete_index(self, index: int) -> None:
        if 0 <= index < len(self.records):
            self.gallery_focus = index
            self._ask_delete(self.records[index])

    def _ask_delete_focused(self) -> None:
        if self.records:
            self._ask_delete(self.records[self.gallery_focus])

    def _ask_delete(self, record: DocumentRecord) -> None:
        """Deliberate delete: the page card itself, back focused first."""
        if self.surfaces.overlays or not self._save():
            return
        self.pending_delete = record
        panel, _cancel, _confirm = self.renderer.delete_dialog_rects()
        preview = self.renderer.card_face(record, self.renderer.delete_preview_rect(panel).size)
        self.surfaces.push_overlay(self.sheets.delete(
            preview, on_cancel=self._close_sheet, on_confirm=self._confirm_delete,
        ))

    def _confirm_delete(self) -> None:
        record = self.pending_delete
        self._close_sheet()
        if record is None:
            return
        try:
            removed = self.repository.delete(record.document_id)
        except (RuntimeError, ValueError, OSError):
            self.save_error = True
            return
        if not removed:
            return
        self.sounds.play("swish")
        self.records = self.repository.list_records()
        self.renderer.invalidate_card(record.document_id)
        if self.current is not None and self.current.document_id == record.document_id:
            self._reset_page(DEFAULT_TINT)
        self.library_full_until = 0.0
        self.gallery_focus = max(0, min(self.gallery_focus, len(self.records) - 1))
        self._sync_controls()
        if self.records:
            self.controls.layer.focus(
                self.controls.card_control_id(self.gallery_focus % GALLERY_PAGE_SIZE),
                visible=self.controls.layer.focus_visible,
            )
        self._burst("fx.dust_puff", self.editor_rect.center)

    # -- sheets ---------------------------------------------------------------

    def _toggle_emoji(self) -> None:
        if self.mode != "edit":
            return
        if self._top_sheet() is not None:
            self._close_sheet()
            return
        self._push_emoji_sheet(None)
        self.sounds.play("tick")

    def _push_emoji_sheet(self, focus_id: str | None) -> None:
        self.surfaces.push_overlay(self.sheets.emoji(
            self.emoji_palette,
            self.editor_rect,
            focus_id=focus_id,
            focus_visible=self.toolbar_focus,
            on_category=self._choose_category,
            on_emoji=self._insert_emoji,
            on_dismiss=self._close_sheet,
        ))
        self.toolbar_focus = False
        self.controls.layer.focus_visible = False
        self.emoji_picker_open = True
        self._keep_cursor_visible()
        self._sync_controls()

    def _choose_category(self, index: int) -> None:
        sheet = self._top_sheet()
        visible = sheet.layer.focus_visible if sheet is not None else False
        self.emoji_palette.select(index)
        while self.surfaces.overlays:
            self.surfaces.pop_overlay()
        category = self.emoji_palette.categories[self.emoji_palette.selected_index]
        self._push_emoji_sheet(f"category.{category.category_id}")
        top = self._top_sheet()
        if top is not None:
            top.layer.focus_visible = visible
        self.sounds.play("tick")

    def _insert_emoji(self, cluster: str) -> None:
        self._apply_edit(lambda: self.buffer.insert(cluster))
        self.sounds.play("pop")

    def _press_new(self) -> None:
        """New page: choose one of six paper colours (dismiss keeps this page)."""
        if self.surfaces.overlays or not self._save():
            return
        blank_draft = self.current is None and not self.buffer.text
        if not blank_draft and self.repository.is_full():
            self._show_full_shelf()
            return
        self.surfaces.push_overlay(self.sheets.paper(
            self.tint if blank_draft else DEFAULT_TINT,
            self.editor_rect,
            focus_visible=self.toolbar_focus or self.controls.layer.focus_visible,
            on_choose=self._choose_paper,
            on_dismiss=self._close_sheet,
        ))
        self.sounds.play("tick")

    def _choose_paper(self, tint: str) -> None:
        self._close_sheet()
        if self.mode == "gallery":
            self.mode = "edit"
        self._new(tint)
        self.sounds.play("pop")

    def _close_sheet(self) -> None:
        self.pending_delete = None
        surfaces = getattr(self, "surfaces", None)
        if surfaces is not None:
            while surfaces.overlays:
                surfaces.pop_overlay()
        was_open = self.emoji_picker_open
        self.emoji_picker_open = False
        if was_open and hasattr(self, "controls"):
            self._sync_controls()

    # -- page lifecycle -------------------------------------------------------

    def _new(self, tint: str | None = None) -> None:
        """Start a fresh page without persisting an empty document.

        A new page is only an in-memory draft: no record is written until the
        child has typed something (see ``_save``). Pressing New on a page that
        is still empty reuses it (only its paper colour changes) instead of
        piling up blank documents.
        """
        tint = tint if tint in TINT_IDS else None
        if self.current is None and not self.buffer.text and not self.dirty:
            self.mode = "edit"
            self._close_sheet()
            self.save_error = False
            if tint is not None:
                self.tint = tint
            self.renderer.invalidate_layout()
            self._sync_controls()
            return
        if self.repository.is_full():
            # Never evict old work: show the full shelf and let the child
            # browse or delete; the current document stays open and untouched.
            self._show_full_shelf()
            return
        self._reset_page(tint or DEFAULT_TINT)
        self.mode = "edit"
        self._sync_controls()

    def _show_full_shelf(self) -> None:
        self.library_full_until = self._clock() + LIBRARY_FULL_SECONDS
        self._enter_gallery()

    def _reset_page(self, tint: str) -> None:
        self.current = None
        self.tint = tint
        self.buffer = TextBuffer()
        self.undo_history.clear()
        self._close_sheet()
        self.dirty = False
        self.save_error = False
        self.scroll_line = 0
        self.renderer.invalidate_layout()

    def _open(self, record: DocumentRecord) -> bool:
        if not self._save():
            return False
        try:
            text = self.repository.load_text(record.document_id)
        except (RuntimeError, UnicodeError, ValueError):
            self.save_error = True
            return False
        self.current = record
        self.tint = record.tint
        self.buffer = TextBuffer(text, len(text))
        self.undo_history.clear()
        self.mode = "edit"
        self._close_sheet()
        self.dirty = False
        self.save_error = False
        self.scroll_line = 0
        self.renderer.invalidate_layout()
        self._keep_cursor_visible()
        self._sync_controls()
        return True

    def _apply_edit(self, action) -> None:
        edit = action()
        if edit is not None:
            self.undo_history.remember(edit)
            self._changed()
            self._keep_cursor_visible()
            controls = getattr(self, "controls", None)
            if controls is not None:
                has_text = bool(self.buffer.text.strip())
                if not controls.undo.enabled or controls.share.enabled != has_text:
                    controls.undo.enabled = True
                    controls.share.enabled = has_text
                    controls.layer.invalidation.invalidate()

    def _undo(self) -> None:
        edit = self.undo_history.pop()
        if edit is None:
            return
        edit.undo(self.buffer)
        self._changed()
        self._keep_cursor_visible()
        self.sounds.play("tick")
        self._sync_controls()

    def _changed(self) -> None:
        self.dirty = True
        self.last_change = self._clock()
        self._last_typing = self.last_change
        self.renderer.invalidate_layout()

    def _step_frame(self) -> None:
        self._autosave()
        now = self._clock()
        if self.shared_request is not None and now >= self.shared_next_poll:
            self._poll_shared_document(now)
        elif self.shared_state and self.shared_state != "pending" and now >= self.shared_feedback_until:
            self.shared_state = ""
            self._sync_controls()
        if self.cast is not None:
            self.cast.update()
        self._fx = [burst for burst in self._fx if not burst.done]

    def _autosave(self) -> None:
        if self.dirty and self._clock() - self.last_change >= AUTOSAVE_IDLE_SECONDS:
            self._save()

    def _save(self) -> bool:
        if not self.dirty:
            return True
        if self.current is None and not self.buffer.text.strip():
            # Typed and then deleted everything on a draft: nothing to keep.
            self.dirty = False
            return True
        tint = getattr(self, "tint", DEFAULT_TINT)
        try:
            if self.current is None:
                updated = self.repository.create_text(self.buffer.text, tint=tint)
            else:
                updated = self.repository.save_text(self.current.document_id, self.buffer.text, tint=tint)
        except (RuntimeError, ValueError):
            self.save_error = True
            return False
        self.current = updated
        self.records = [updated, *[item for item in self.records if item.document_id != updated.document_id]]
        self.dirty = False
        self.save_error = False
        return True

    # -- shared UTF-8 documents ------------------------------------------

    def _publish_current_document(self) -> None:
        """Explicit copy into My Creations, never an automatic autosave export."""
        if self.creations is None or not self.buffer.text.strip():
            return
        if not self._save():
            self.shared_state = "error"
            self.shared_feedback_until = self._now() + FEEDBACK_SECONDS
            return
        if self.current is None:
            return
        payload = self.buffer.text.encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        if self._last_shared_digest.get(self.current.document_id) == digest:
            self.shared_state = "saved"
            self.shared_feedback_until = self._now() + FEEDBACK_SECONDS
            self._celebrate()
            return
        try:
            name = self.repository.private_document_name(self.current.document_id)
            self.creations.publish_private_file(
                name,
                media_type="text/plain",
                role="document",
                title=self.current.preview[:100],
            )
        except (RuntimeError, ValueError, OSError, UnicodeError):
            self.shared_state = "error"
            self.shared_feedback_until = self._now() + FEEDBACK_SECONDS
            return
        self._last_shared_digest[self.current.document_id] = digest
        self.shared_state = "saved"
        self.shared_feedback_until = self._now() + FEEDBACK_SECONDS
        self._celebrate()

    def _now(self) -> float:
        # Tests may build the app without __init__; fall back to wall time.
        return getattr(self, "_clock", time.monotonic)()

    def _celebrate(self) -> None:
        """One feedback grammar: Leo cheers, sparkles, a soft chime."""
        cast = getattr(self, "cast", None)
        if cast is not None:
            cast.correct()
        sounds = getattr(self, "sounds", None)
        if sounds is not None:
            sounds.play("chime")
        renderer = getattr(self, "renderer", None)
        if renderer is not None and hasattr(renderer, "shared_export_button"):
            anchor = renderer.shared_export_button()
            self._burst("fx.sparkle", anchor.center if anchor is not None else self.editor_rect.center)

    def _burst(self, asset_id: str, center: tuple[int, int]) -> None:
        renderer = getattr(self, "renderer", None)
        if renderer is None or not hasattr(renderer, "fx_frames"):
            return
        frames = renderer.fx_frames(asset_id, self.metrics.px(120))
        if frames:
            fx = getattr(self, "_fx", [])
            self._fx = [*fx[-2:], FxBurst(frames, center, clock=getattr(self, "_clock", time.monotonic))]

    def _request_shared_document(self) -> None:
        """Start one nonblocking platform picker for a shared text page."""
        if self.creations is None or self.shared_request is not None:
            return
        try:
            request_id = self.creations.request_selection(
                media_types=("text/plain",),
                roles=("document", "postcard"),
            )
        except (RuntimeError, ValueError, OSError):
            self.shared_state = "error"
            self.shared_feedback_until = self._now() + FEEDBACK_SECONDS
            return
        self.shared_request = request_id
        self.shared_state = "pending"
        self.shared_next_poll = self._now() + CREATION_PICKER_POLL_SECONDS

    def _poll_shared_document(self, now: float) -> None:
        request_id = self.shared_request
        if request_id is None or self.creations is None:
            return
        self.shared_next_poll = now + CREATION_PICKER_POLL_SECONDS
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.shared_request = None
            self.shared_state = "error"
            self.shared_feedback_until = now + FEEDBACK_SECONDS
            return
        if result.state == "pending":
            return
        self.shared_request = None
        if result.state == "cancelled":
            self.shared_state = ""
            return
        token = result.selection_token
        if (
            result.state != "ready"
            or not isinstance(token, str)
            or not token
            or not self._accept_shared_document(token)
        ):
            self.shared_state = "error"
            self.shared_feedback_until = now + FEEDBACK_SECONDS
            return
        self.shared_state = "imported"
        self.shared_feedback_until = now + FEEDBACK_SECONDS
        self._celebrate()

    def _accept_shared_document(self, selection_token: str) -> bool:
        """Import one Shell-confirmed UTF-8 page as an independent private copy."""
        if self.creations is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "text/plain"
                or transfer.record.get("role") not in {"document", "postcard"}
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256") != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected document failed integrity validation")
            text = payload.decode("utf-8", errors="strict")
            record = self.repository.create_text(text)
            loaded = self.repository.load_text(record.document_id)
        except (RuntimeError, ValueError, OSError, UnicodeError):
            return False
        self.current = record
        self.tint = record.tint
        self.records = [record, *[item for item in self.records if item.document_id != record.document_id]]
        self.buffer = TextBuffer(loaded, len(loaded))
        self.undo_history.clear()
        self.mode = "edit"
        self._close_sheet()
        self.dirty = False
        self.save_error = False
        self.scroll_line = 0
        self.renderer.invalidate_layout()
        self._keep_cursor_visible()
        if hasattr(self, "controls"):
            self._sync_controls()
        return True

    # -- layout / cursor helpers (delegate layout to renderer) -----------

    def _layout(self) -> list[VisualLine]:
        return self.renderer.layout(self.buffer.text, self.editor_rect)

    def _cursor_line(self) -> int:
        return self.renderer.cursor_line(self.buffer.cursor, self._layout())

    def _keep_cursor_visible(self) -> None:
        visible = self.renderer.visible_line_count(self.view_rect)
        current = self._cursor_line()
        if current < self.scroll_line:
            self.scroll_line = current
        elif current >= self.scroll_line + visible:
            self.scroll_line = current - visible + 1

    def _move_vertical(self, delta: int) -> None:
        lines = self._layout()
        current_index = self._cursor_line()
        target = lines[max(0, min(len(lines) - 1, current_index + delta))]
        current = lines[current_index]
        current_prefix = self.buffer.text[current.start : self.buffer.cursor]
        column = len(grapheme_spans(current_prefix))
        target_boundaries = grapheme_boundaries(target.text)
        offset = target_boundaries[min(column, len(target_boundaries) - 1)]
        self.buffer.cursor = target.start + offset

    def _place_cursor(self, pos: tuple[int, int]) -> None:
        lines = self._layout()
        line_height = self.renderer.line_height()
        x0, y0 = self.renderer.text_origin(self.editor_rect)
        line_index = self.scroll_line + max(0, (pos[1] - y0) // line_height)
        line = lines[max(0, min(len(lines) - 1, line_index))]
        x = pos[0] - x0
        cursor = line.start
        for span in grapheme_spans(line.text):
            cluster_width = self.typography.measure(span.text, FontRole.BODY, self.font_size).width
            if x < cluster_width / 2:
                break
            x -= cluster_width
            cursor = line.start + span.end
        self.buffer.cursor = min(line.end, cursor)
        self._last_typing = self._clock()
        self._keep_cursor_visible()

    # -- controls sync --------------------------------------------------------

    def _sync_controls(self) -> None:
        controls = getattr(self, "controls", None)
        if controls is None:
            return
        controls.set_mode(self.mode, shared_available=self.creations is not None)
        if self.mode == "gallery":
            self._sync_gallery_targets()
            controls.importer.enabled = self.shared_request is None
        else:
            controls.sync_edit(can_undo=bool(self.undo_history), emoji_open=self.emoji_picker_open)
            controls.share.enabled = bool(self.buffer.text.strip())

    def _sync_gallery_targets(self) -> None:
        if self.mode != "gallery":
            return
        page = self.gallery_focus // GALLERY_PAGE_SIZE
        cards = [rect for rect, _record in self.renderer.gallery_cards(self.editor_rect, self.records, page)]
        self.controls.sync_gallery(
            page=page,
            page_count=self.renderer.gallery_page_count(len(self.records)),
            cards=cards,
            has_focus_card=bool(self.records),
        )

    # -- drawing --------------------------------------------------------

    def _status(self) -> str:
        if self.save_error or self.shared_state == "error":
            return "error"
        return "saving" if self.dirty else "saved"

    def _visual_signature(self) -> tuple[object, ...]:
        """Time-dependent visible state; a change means one redraw is due."""

        return (
            self.mode,
            self._caret_visible(),
            self._status(),
            self.shared_state,
            self._clock() < self.library_full_until,
        )

    def _caret_visible(self) -> bool:
        if self.toolbar_focus:
            return False
        idle = self._clock() - self._last_typing
        if idle >= CARET_BLINK_SECONDS:
            # Like desktop blink timeouts: a steady caret once the child
            # pauses, so an idle page presents nothing (Atom CPU).
            return True
        return idle < 0.8 or int(idle * 1.8) % 2 == 0

    def _draw(self) -> None:
        renderer = self.renderer
        renderer.draw_background(self.screen)
        if self.mode == "gallery":
            renderer.draw_gallery(
                self.screen, self.editor_rect, self.records,
                page=self.gallery_focus // GALLERY_PAGE_SIZE,
                focus_index=self.gallery_focus if self.records else None,
                library_full=self._clock() < self.library_full_until,
            )
        else:
            lines = self._layout()
            renderer.draw_editor(
                self.screen, self.editor_rect, self.view_rect, lines, self.buffer.text, self.buffer.cursor,
                self.scroll_line, tint=self.tint, caret_visible=self._caret_visible(),
            )
            renderer.draw_status(self.screen, self._status())
        self.surfaces.draw(self.screen)
        for burst in self._fx:
            burst.draw(self.screen)
        if self.cast is not None and self.cast.animating:
            editor = self.editor_rect
            self.cast.draw(self.screen, (editor.right - self.metrics.px(90), editor.bottom + self.metrics.px(6)))
        # Activity-local pointer (save-under sprite, so pointer-only frames
        # repair two small rectangles). Trusted Home/Back is platform-owned.
        self._pointer.forget()
        self._pointer.draw(self.screen)


__all__ = ["WritingApp"]
