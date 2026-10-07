"""Lifecycle owner for the Writing Activity.

Owns screen/canvas/metrics/typography, domain model, renderer and input
routing. Delegates rules to the pure model and presentation to the
renderer. Publishes READY after the first flip in the same loop.
"""

from __future__ import annotations

import bisect
import hashlib
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.emoji_palette import EmojiPalette
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import FontRole, GreiaTypography, grapheme_boundaries, grapheme_spans

if __package__:
    from .writing_content import AUTOSAVE_IDLE_SECONDS
    from .writing_model import DocumentRecord, DocumentRepository, TextBuffer, UndoHistory
    from .writing_renderer import VisualLine, WritingRenderer
else:  # pragma: no cover - runtime/script fallback
    from writing_content import AUTOSAVE_IDLE_SECONDS
    from writing_model import DocumentRecord, DocumentRepository, TextBuffer, UndoHistory
    from writing_renderer import VisualLine, WritingRenderer


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
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.metrics = metrics
        self.typography = typography
        self.theme = theme
        self.repository = repository
        self.creations = creations
        self.shared_request: str | None = None
        self.shared_next_poll = 0.0
        self.shared_state = ""
        self.shared_feedback_until = 0.0
        self._last_shared_digest: dict[str, str] = {}
        self.font_size = self.metrics.px(42)
        self.small_font_size = self.metrics.px(27)
        self.emoji_palette = EmojiPalette()
        self.emoji_picker_open = False
        self.renderer = WritingRenderer(
            typography, metrics, theme, self.emoji_palette, self.font_size, self.small_font_size
        )
        self.records = self.repository.list_records()
        self.current: DocumentRecord | None = None
        self.buffer = TextBuffer()
        self.undo_history = UndoHistory()
        self.mode = "edit"
        self.dirty = False
        self.save_error = False
        self.last_change = 0.0
        self.scroll_line = 0
        if self.records:
            self._open(self.records[0])
        else:
            self._new()
        pygame.key.start_text_input()

    @property
    def editor_rect(self) -> pygame.Rect:
        return self.metrics.activity_content_rect(top_gap=6)

    # -- public lifecycle -----------------------------------------------

    def run(self) -> int:
        clock = pygame.time.Clock()
        running = True
        ready_published = False
        while running and not activity_stop_requested():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self._save():
                        running = False
                elif event.type == pygame.KEYDOWN:
                    running = self.handle_key(event)
                elif event.type == pygame.TEXTINPUT and self.mode == "edit":
                    self._apply_edit(lambda: self.buffer.insert(event.text))
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    running = self.handle_pointer(event.pos)
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event)
            self._step_frame()
            self._draw()
            # Present via reference canvas when available; keep direct flip for R7.3 compat.
            if self.canvas is not None:
                try:
                    self.canvas.present(clear=self.theme.background)
                except Exception:
                    pass
            pygame.display.flip()
            if not ready_published:
                mark_activity_ready()
                ready_published = True
            clock.tick(30)
        self._save()
        pygame.key.stop_text_input()
        self.typography.clear()
        pygame.quit()
        return 0

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Compatibility dispatcher for external callers; returns dirty flag."""
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            self.handle_key(event)
            return True
        if event.type == pygame.TEXTINPUT and self.mode == "edit":
            self._apply_edit(lambda: self.buffer.insert(event.text))
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.handle_pointer(event.pos)
            return True
        if event.type == pygame.VIDEORESIZE:
            self.handle_resize(event)
            return True
        return False

    def handle_key(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_ESCAPE:
            if self.emoji_picker_open:
                self.emoji_picker_open = False
                return True
            return not self._save()
        if self.mode == "gallery":
            if event.key in {pygame.K_RETURN, pygame.K_SPACE} and self.records:
                self._open(self.records[0])
            return True
        if event.key == pygame.K_z and event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
            self._undo()
            return True
        if event.key == pygame.K_BACKSPACE:
            self._apply_edit(self.buffer.backspace)
        elif event.key == pygame.K_DELETE:
            self._apply_edit(self.buffer.delete)
        elif event.key == pygame.K_RETURN:
            self._apply_edit(lambda: self.buffer.insert("\n"))
        elif event.key == pygame.K_LEFT:
            self.buffer.move(-1)
        elif event.key == pygame.K_RIGHT:
            self.buffer.move(1)
        elif event.key == pygame.K_HOME:
            self.buffer.home()
        elif event.key == pygame.K_END:
            self.buffer.end()
        elif event.key == pygame.K_UP:
            self._move_vertical(-1)
        elif event.key == pygame.K_DOWN:
            self._move_vertical(1)
        self._keep_cursor_visible()
        return True

    def handle_pointer(self, pos: tuple[int, int]) -> bool:
        if not _is_safe_point(self.screen, pos):
            return True
        gallery = self.metrics.activity_toolbar_button(0, side="left")
        undo = self.metrics.activity_toolbar_button(1, side="left")
        emoji = self.metrics.activity_toolbar_button(2, side="left")
        new = self.metrics.activity_toolbar_button(0, side="right")
        shared = self.metrics.activity_toolbar_button(1, side="right")
        if (
            self.creations is not None
            and shared.collidepoint(pos)
        ):
            if self.mode == "edit":
                self._publish_current_document()
            else:
                self._request_shared_document()
            return True
        if gallery.collidepoint(pos):
            if not self._save():
                return True
            self.mode = "gallery" if self.mode == "edit" else "edit"
            self.emoji_picker_open = False
            return True
        if undo.collidepoint(pos) and self.mode == "edit":
            self._undo()
            return True
        if emoji.collidepoint(pos) and self.mode == "edit":
            self.emoji_picker_open = not self.emoji_picker_open
            return True
        if new.collidepoint(pos):
            if self._save():
                self._new()
            return True
        if self.mode == "gallery":
            for rect, record in self.renderer.gallery_cards(self.editor_rect, self.records):
                if rect.collidepoint(pos):
                    self._open(record)
                    break
        elif self.emoji_picker_open:
            self._click_emoji_picker(pos)
        elif self.editor_rect.collidepoint(pos):
            self._place_cursor(pos)
        return True

    def handle_resize(self, event: pygame.event.Event) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.font_size = self.metrics.px(42)
        self.small_font_size = self.metrics.px(27)
        if self.canvas is not None:
            try:
                self.canvas = PygameReferenceCanvas(self.screen)
            except Exception:
                pass
        self.renderer.on_resize(self.metrics, self.font_size, self.small_font_size)

    # -- internal helpers -----------------------------------------------

    def _new(self) -> None:
        try:
            record = self.repository.create()
        except RuntimeError:
            self.save_error = True
            return
        self.current = record
        self.buffer = TextBuffer()
        self.undo_history.clear()
        self.records = [record, *[item for item in self.records if item.document_id != record.document_id]]
        self.mode = "edit"
        self.emoji_picker_open = False
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
        self.buffer = TextBuffer(text, len(text))
        self.undo_history.clear()
        self.mode = "edit"
        self.emoji_picker_open = False
        self.dirty = False
        self.save_error = False
        self.scroll_line = 0
        self.renderer.invalidate_layout()
        self._keep_cursor_visible()
        return True

    def _apply_edit(self, action) -> None:
        edit = action()
        if edit is not None:
            self.undo_history.remember(edit)
            self._changed()
            self._keep_cursor_visible()

    def _undo(self) -> None:
        edit = self.undo_history.pop()
        if edit is None:
            return
        edit.undo(self.buffer)
        self._changed()
        self._keep_cursor_visible()

    def _changed(self) -> None:
        self.dirty = True
        self.last_change = time.monotonic()
        self.renderer.invalidate_layout()

    def _step_frame(self) -> None:
        self._autosave()
        now = time.monotonic()
        if self.shared_request is not None and now >= self.shared_next_poll:
            self._poll_shared_document(now)
        elif (
            self.shared_state
            and self.shared_state != "pending"
            and now >= self.shared_feedback_until
        ):
            self.shared_state = ""

    def _autosave(self) -> None:
        if self.dirty and time.monotonic() - self.last_change >= AUTOSAVE_IDLE_SECONDS:
            self._save()

    def _save(self) -> bool:
        if not self.dirty or self.current is None:
            return True
        try:
            updated = self.repository.save_text(self.current.document_id, self.buffer.text)
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
        if (
            self.creations is None
            or self.current is None
            or not self.buffer.text.strip()
        ):
            return
        if not self._save():
            self.shared_state = "error"
            self.shared_feedback_until = time.monotonic() + 2.0
            return
        payload = self.buffer.text.encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        if self._last_shared_digest.get(self.current.document_id) == digest:
            self.shared_state = "saved"
            self.shared_feedback_until = time.monotonic() + 2.0
            return
        try:
            name = self.repository.private_document_name(
                self.current.document_id
            )
            self.creations.publish_private_file(
                name,
                media_type="text/plain",
                role="document",
                title=self.current.preview[:100],
            )
        except (RuntimeError, ValueError, OSError, UnicodeError):
            self.shared_state = "error"
            self.shared_feedback_until = time.monotonic() + 2.0
            return
        self._last_shared_digest[self.current.document_id] = digest
        self.shared_state = "saved"
        self.shared_feedback_until = time.monotonic() + 2.0

    def _request_shared_document(self) -> None:
        if self.creations is None or self.shared_request is not None:
            return
        try:
            request_id = self.creations.request_selection(
                media_types=("text/plain",),
                roles=("document", "postcard"),
            )
        except (RuntimeError, ValueError, OSError):
            self.shared_state = "error"
            self.shared_feedback_until = time.monotonic() + 2.0
            return
        self.shared_request = request_id
        self.shared_state = "pending"
        self.shared_next_poll = time.monotonic() + 0.12

    def _poll_shared_document(self, now: float) -> None:
        request_id = self.shared_request
        if request_id is None or self.creations is None:
            return
        self.shared_next_poll = now + 0.12
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.shared_request = None
            self.shared_state = "error"
            self.shared_feedback_until = now + 2.0
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
            self.shared_feedback_until = now + 2.0
            return
        self.shared_state = "imported"
        self.shared_feedback_until = now + 2.0

    def _accept_shared_document(self, selection_token: str) -> bool:
        if self.creations is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "text/plain"
                or transfer.record.get("role") not in {"document", "postcard"}
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256")
                != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected document failed integrity validation")
            text = payload.decode("utf-8", errors="strict")
            record = self.repository.create_text(text)
            loaded = self.repository.load_text(record.document_id)
        except (RuntimeError, ValueError, OSError, UnicodeError):
            return False
        self.current = record
        self.records = [
            record,
            *[
                item
                for item in self.records
                if item.document_id != record.document_id
            ],
        ]
        self.buffer = TextBuffer(loaded, len(loaded))
        self.undo_history.clear()
        self.mode = "edit"
        self.emoji_picker_open = False
        self.dirty = False
        self.save_error = False
        self.scroll_line = 0
        self.renderer.invalidate_layout()
        self._keep_cursor_visible()
        return True

    # -- layout / cursor helpers (delegate layout to renderer) -----------

    def _layout(self) -> list[VisualLine]:
        return self.renderer.layout(self.buffer.text, self.editor_rect)

    def _cursor_line(self) -> int:
        lines = self._layout()
        return self.renderer.cursor_line(self.buffer.cursor, lines)

    def _keep_cursor_visible(self) -> None:
        line_height = self.typography.line_height(FontRole.BODY, self.font_size)
        visible = max(1, (self.editor_rect.height - self.metrics.px(34)) // line_height)
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
        line_height = self.typography.line_height(FontRole.BODY, self.font_size)
        x0 = self.editor_rect.left + self.metrics.px(26)
        y0 = self.editor_rect.top + self.metrics.px(18)
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
        self._keep_cursor_visible()

    def _click_emoji_picker(self, pos: tuple[int, int]) -> None:
        categories, items = self.renderer.emoji_picker_layout(self.editor_rect)
        for idx, rect in enumerate(categories):
            if rect.collidepoint(pos):
                self.emoji_palette.select(idx)
                return
        for rect, cluster in items:
            if rect.collidepoint(pos):
                self._apply_edit(lambda cluster=cluster: self.buffer.insert(cluster))
                return

    # -- drawing --------------------------------------------------------

    def _draw(self) -> None:
        self.screen.fill(self.theme.background)
        gallery, undo, emoji, new, shared = self.renderer.draw_toolbar(
            self.screen,
            self.undo_history,
            self.emoji_picker_open,
            self.mode,
            shared_available=self.creations is not None,
            shared_state=self.shared_state,
        )
        # Status dot.
        status = (210, 76, 76) if self.save_error else ((246, 178, 55) if self.dirty else (87, 174, 104))
        pygame.draw.circle(
            self.screen,
            status,
            (new.left - self.metrics.px(18), new.centery),
            self.metrics.px(6),
        )
        if self.mode == "gallery":
            self.renderer.draw_gallery(self.screen, self.editor_rect, self.records)
        else:
            lines = self._layout()
            self.renderer.draw_editor(
                self.screen, self.editor_rect, lines, self.buffer.text, self.buffer.cursor, self.scroll_line
            )
            if self.emoji_picker_open:
                self.renderer.draw_emoji_picker(self.screen, self.editor_rect)
        # Activity-local pointer. Trusted Home/Back is platform-owned.
        from greia_platform.activity_ui import draw_activity_pointer

        draw_activity_pointer(self.screen)


__all__ = ["WritingApp"]
