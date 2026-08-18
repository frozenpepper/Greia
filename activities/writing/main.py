from __future__ import annotations

from dataclasses import dataclass
import time
import uuid

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
    draw_icon_button,
    draw_plus_symbol,
    draw_undo_symbol,
    load_icon,
    mix,
)

AUTOSAVE_IDLE_SECONDS = 1.2
MAX_DOCUMENTS = 120
MAX_CHARACTERS = 120_000
MAX_UNDO_EDITS = 128
MAX_UNDO_PAYLOAD_CHARS = 65_536
INDEX_KEY = "documents.index.v1"


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    document_id: str
    preview: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.document_id, "preview": self.preview}


class DocumentRepository:
    def __init__(self, storage):
        self.storage = storage

    def list_records(self) -> list[DocumentRecord]:
        raw = self.storage.kv_get(INDEX_KEY, [])
        if not isinstance(raw, list):
            return []
        records: list[DocumentRecord] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            document_id = item.get("id")
            preview = item.get("preview", "")
            if (
                not isinstance(document_id, str)
                or not _valid_document_id(document_id)
                or document_id in seen
                or not isinstance(preview, str)
            ):
                continue
            seen.add(document_id)
            records.append(DocumentRecord(document_id, preview[:80]))
            if len(records) >= MAX_DOCUMENTS:
                break
        return records

    def create(self) -> DocumentRecord:
        records = self.list_records()
        if len(records) >= MAX_DOCUMENTS:
            raise RuntimeError("document library limit reached")
        record = DocumentRecord(uuid.uuid4().hex, "")
        name = self._name(record.document_id)
        self.storage.file_write_atomic(name, b"")
        try:
            self._write_index([record, *records])
        except RuntimeError:
            try:
                self.storage.file_delete(name)
            except RuntimeError:
                pass
            raise
        return record

    def load_text(self, document_id: str) -> str:
        _require_document_id(document_id)
        return self.storage.file_read(self._name(document_id)).decode("utf-8")[:MAX_CHARACTERS]

    def save_text(self, document_id: str, text: str) -> DocumentRecord:
        _require_document_id(document_id)
        text = clamp_text(text)
        self.storage.file_write_atomic(self._name(document_id), text.encode("utf-8"))
        updated = DocumentRecord(document_id, preview_text(text))
        others = [item for item in self.list_records() if item.document_id != document_id]
        self._write_index([updated, *others])
        return updated

    def _write_index(self, records: list[DocumentRecord]) -> None:
        self.storage.kv_set(INDEX_KEY, [item.as_dict() for item in records])

    @staticmethod
    def _name(document_id: str) -> str:
        return f"documents/{document_id}.txt"


@dataclass(frozen=True, slots=True)
class TextEdit:
    start: int
    removed: str
    inserted: str
    cursor_before: int
    cursor_after: int

    @property
    def payload_chars(self) -> int:
        return len(self.removed) + len(self.inserted)

    def undo(self, buffer: "TextBuffer") -> None:
        if self.start < 0 or self.start + len(self.inserted) > len(buffer.text):
            raise ValueError("undo edit is outside the current text")
        if buffer.text[self.start : self.start + len(self.inserted)] != self.inserted:
            raise ValueError("undo edit no longer matches current text")
        buffer.text = (
            buffer.text[: self.start]
            + self.removed
            + buffer.text[self.start + len(self.inserted) :]
        )
        buffer.cursor = max(0, min(self.cursor_before, len(buffer.text)))


@dataclass(slots=True)
class TextBuffer:
    text: str = ""
    cursor: int = 0

    def __post_init__(self) -> None:
        self.text = clamp_text(self.text)
        self.cursor = max(0, min(int(self.cursor), len(self.text)))

    def insert(self, value: str) -> TextEdit | None:
        if not value:
            return None
        value = value[: max(0, MAX_CHARACTERS - len(self.text))]
        if not value:
            return None
        start = self.cursor
        cursor_before = self.cursor
        self.text = self.text[:start] + value + self.text[start:]
        self.cursor = start + len(value)
        return TextEdit(start, "", value, cursor_before, self.cursor)

    def backspace(self) -> TextEdit | None:
        if self.cursor == 0:
            return None
        cursor_before = self.cursor
        start = self.cursor - 1
        removed = self.text[start : self.cursor]
        self.text = self.text[:start] + self.text[self.cursor :]
        self.cursor = start
        return TextEdit(start, removed, "", cursor_before, self.cursor)

    def delete(self) -> TextEdit | None:
        if self.cursor >= len(self.text):
            return None
        cursor_before = self.cursor
        start = self.cursor
        removed = self.text[start : start + 1]
        self.text = self.text[:start] + self.text[start + 1 :]
        return TextEdit(start, removed, "", cursor_before, self.cursor)

    def move(self, delta: int) -> None:
        self.cursor = max(0, min(len(self.text), self.cursor + int(delta)))

    def home(self) -> None:
        start = self.text.rfind("\n", 0, self.cursor)
        self.cursor = 0 if start < 0 else start + 1

    def end(self) -> None:
        end = self.text.find("\n", self.cursor)
        self.cursor = len(self.text) if end < 0 else end


class UndoHistory:
    def __init__(
        self,
        maximum: int = MAX_UNDO_EDITS,
        max_payload_chars: int = MAX_UNDO_PAYLOAD_CHARS,
    ):
        if maximum < 1:
            raise ValueError("undo history must retain at least one edit")
        if max_payload_chars < 1:
            raise ValueError("undo payload bound must be positive")
        self.maximum = int(maximum)
        self.max_payload_chars = int(max_payload_chars)
        self._items: list[TextEdit] = []
        self._payload_chars = 0

    @property
    def payload_chars(self) -> int:
        return self._payload_chars

    def remember(self, edit: TextEdit) -> None:
        payload = edit.payload_chars
        if payload > self.max_payload_chars:
            self.clear()
            return
        self._items.append(edit)
        self._payload_chars += payload
        while len(self._items) > self.maximum or self._payload_chars > self.max_payload_chars:
            removed = self._items.pop(0)
            self._payload_chars -= removed.payload_chars

    def pop(self) -> TextEdit | None:
        if not self._items:
            return None
        edit = self._items.pop()
        self._payload_chars -= edit.payload_chars
        return edit

    def clear(self) -> None:
        self._items.clear()
        self._payload_chars = 0

    def __bool__(self) -> bool:
        return bool(self._items)


def clamp_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("document text must be a string")
    return text[:MAX_CHARACTERS]


def preview_text(text: str) -> str:
    return " ".join(text.replace("\x00", "").split())[:80]


def _valid_document_id(value: str) -> bool:
    return len(value) == 32 and all(ch in "0123456789abcdef" for ch in value)


def _require_document_id(value: str) -> None:
    if not isinstance(value, str) or not _valid_document_id(value):
        raise ValueError("invalid document id")


@dataclass(frozen=True, slots=True)
class VisualLine:
    start: int
    end: int
    text: str


class WritingApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.key.start_text_input()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.theme = get_theme()
        self.font = pygame.font.Font(None, self.metrics.px(42))
        self.small_font = pygame.font.Font(None, self.metrics.px(27))
        self.repository = DocumentRepository(get_storage())
        icon_size = self.metrics.px(42)
        self.book_icon = load_icon(get_icon_path("book", 64), icon_size)
        self.empty_icon = load_icon(get_icon_path("yellow_star", 64), self.metrics.px(46))
        self.records = self.repository.list_records()
        self.current: DocumentRecord | None = None
        self.buffer = TextBuffer()
        self.undo_history = UndoHistory()
        self.mode = "edit"
        self.dirty = False
        self.save_error = False
        self.last_change = 0.0
        self.scroll_line = 0
        self._layout_text: str | None = None
        self._lines: list[VisualLine] = []
        if self.records:
            self._open(self.records[0])
        else:
            self._new()

    @property
    def editor_rect(self) -> pygame.Rect:
        return self.metrics.activity_content_rect(top_gap=6)

    def run(self) -> int:
        running = True
        ready_published = False
        while running and not activity_stop_requested():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self._save():
                        running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._key(event)
                elif event.type == pygame.TEXTINPUT and self.mode == "edit":
                    self._apply_edit(lambda: self.buffer.insert(event.text))
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    running = self._click(event.pos)
            self._autosave()
            self._draw()
            pygame.display.flip()
            if not ready_published:
                mark_activity_ready()
                ready_published = True
            self.clock.tick(30)
        self._save()
        pygame.key.stop_text_input()
        pygame.quit()
        return 0

    def _key(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_ESCAPE:
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

    def _click(self, pos: tuple[int, int]) -> bool:
        gallery = self.metrics.activity_toolbar_button(0, side="left")
        undo = self.metrics.activity_toolbar_button(1, side="left")
        new = self.metrics.activity_toolbar_button(0, side="right")
        if gallery.collidepoint(pos):
            if not self._save():
                return True
            self.mode = "gallery" if self.mode == "edit" else "edit"
            return True
        if undo.collidepoint(pos) and self.mode == "edit":
            self._undo()
            return True
        if new.collidepoint(pos):
            if self._save():
                self._new()
            return True
        if self.mode == "gallery":
            for rect, record in self._gallery_cards():
                if rect.collidepoint(pos):
                    self._open(record)
                    break
        elif self.editor_rect.collidepoint(pos):
            self._place_cursor(pos)
        return True

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
        self.dirty = False
        self.save_error = False
        self.scroll_line = 0
        self._layout_text = None

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
        self.dirty = False
        self.save_error = False
        self.scroll_line = 0
        self._layout_text = None
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
        self._layout_text = None

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

    def _layout(self) -> list[VisualLine]:
        if self._layout_text == self.buffer.text:
            return self._lines
        width = max(40, self.editor_rect.width - self.metrics.px(52))
        text = self.buffer.text
        widths: dict[str, int] = {}
        lines: list[VisualLine] = []
        line_start = 0
        line_width = 0
        last_space: int | None = None
        index = 0
        while index < len(text):
            ch = text[index]
            if ch == "\n":
                lines.append(VisualLine(line_start, index, text[line_start:index]))
                index += 1
                line_start = index
                line_width = 0
                last_space = None
                continue
            char_width = widths.setdefault(ch, max(1, self.font.size(ch)[0]))
            if ch.isspace():
                last_space = index
            if line_width + char_width > width and index > line_start:
                wrap = last_space + 1 if last_space is not None and last_space >= line_start else index
                lines.append(VisualLine(line_start, wrap, text[line_start:wrap].rstrip("\n")))
                line_start = wrap
                index = wrap
                line_width = 0
                last_space = None
                continue
            line_width += char_width
            index += 1
        lines.append(VisualLine(line_start, len(text), text[line_start:]))
        self._layout_text = text
        self._lines = lines
        return lines

    def _cursor_line(self) -> int:
        lines = self._layout()
        for index in range(len(lines) - 1, -1, -1):
            line = lines[index]
            if line.start <= self.buffer.cursor <= line.end:
                return index
        return max(0, len(lines) - 1)

    def _keep_cursor_visible(self) -> None:
        visible = max(1, (self.editor_rect.height - self.metrics.px(34)) // self.font.get_linesize())
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
        column = max(0, self.buffer.cursor - current.start)
        self.buffer.cursor = min(target.end, target.start + column)

    def _place_cursor(self, pos: tuple[int, int]) -> None:
        lines = self._layout()
        line_height = self.font.get_linesize()
        x0 = self.editor_rect.left + self.metrics.px(26)
        y0 = self.editor_rect.top + self.metrics.px(18)
        line_index = self.scroll_line + max(0, (pos[1] - y0) // line_height)
        line = lines[max(0, min(len(lines) - 1, line_index))]
        x = pos[0] - x0
        cursor = line.start
        for offset, ch in enumerate(line.text):
            char_width = self.font.size(ch)[0]
            if x < char_width / 2:
                break
            x -= char_width
            cursor = line.start + offset + 1
        self.buffer.cursor = min(line.end, cursor)
        self._keep_cursor_visible()

    def _gallery_cards(self) -> list[tuple[pygame.Rect, DocumentRecord]]:
        area = self.editor_rect
        gap = self.metrics.px(18)
        card_w = (area.width - gap * 2) // 3
        card_h = (area.height - gap) // 2
        cards = []
        for index, record in enumerate(self.records[:6]):
            row, col = divmod(index, 3)
            cards.append((pygame.Rect(area.left + col * (card_w + gap), area.top + row * (card_h + gap), card_w, card_h), record))
        return cards

    def _draw(self) -> None:
        self.screen.fill(self.theme.background)
        gallery = self.metrics.activity_toolbar_button(0, side="left")
        undo = self.metrics.activity_toolbar_button(1, side="left")
        new = self.metrics.activity_toolbar_button(0, side="right")
        draw_icon_button(self.screen, gallery, fill=self.theme.panel, icon=self.book_icon, selected=self.mode == "gallery", outline=self.theme.accent)
        undo_fill = self.theme.panel if self.mode == "edit" and self.undo_history else mix(self.theme.panel, self.theme.background, 0.35)
        draw_icon_button(self.screen, undo, fill=undo_fill)
        draw_undo_symbol(self.screen, undo, self.theme.text)
        draw_icon_button(self.screen, new, fill=self.theme.accent)
        draw_plus_symbol(self.screen, new, self.theme.accent_text)
        status = (210, 76, 76) if self.save_error else ((246, 178, 55) if self.dirty else (87, 174, 104))
        pygame.draw.circle(self.screen, status, (new.left - self.metrics.px(18), new.centery), self.metrics.px(6))
        if self.mode == "gallery":
            self._draw_gallery()
        else:
            self._draw_editor()

    def _draw_editor(self) -> None:
        rect = self.editor_rect
        pygame.draw.rect(self.screen, mix(self.theme.panel, (255, 255, 255), 0.58), rect, border_radius=self.metrics.radius)
        lines = self._layout()
        cursor_line = self._cursor_line()
        line_height = self.font.get_linesize()
        x = rect.left + self.metrics.px(26)
        y = rect.top + self.metrics.px(18)
        visible = max(1, (rect.height - self.metrics.px(34)) // line_height)
        visible_lines = lines[self.scroll_line : self.scroll_line + visible]
        for offset, line in enumerate(visible_lines):
            if line.text:
                self.screen.blit(self.font.render(line.text, True, self.theme.text), (x, y))
            if self.scroll_line + offset == cursor_line:
                cursor_x = x + self.font.size(self.buffer.text[line.start : self.buffer.cursor])[0]
                pygame.draw.line(self.screen, self.theme.accent, (cursor_x, y + 4), (cursor_x, y + line_height - 5), max(2, self.metrics.px(3)))
            y += line_height

    def _draw_gallery(self) -> None:
        for rect, record in self._gallery_cards():
            pygame.draw.rect(self.screen, self.theme.panel, rect, border_radius=self.metrics.radius)
            if not record.preview:
                self.screen.blit(self.empty_icon, self.empty_icon.get_rect(center=rect.center))
                continue
            words = record.preview.split()
            line = ""
            y = rect.top + self.metrics.px(22)
            max_width = rect.width - self.metrics.px(30)
            for word in words:
                candidate = f"{line} {word}".strip()
                if line and self.small_font.size(candidate)[0] > max_width:
                    self.screen.blit(self.small_font.render(line, True, self.theme.text), (rect.left + self.metrics.px(16), y))
                    y += self.small_font.get_linesize()
                    line = word
                    if y > rect.bottom - self.small_font.get_linesize() * 2:
                        break
                else:
                    line = candidate
            if line and y < rect.bottom - self.small_font.get_linesize():
                self.screen.blit(self.small_font.render(line, True, self.theme.text), (rect.left + self.metrics.px(16), y))


def main() -> int:
    return WritingApp().run()


if __name__ == "__main__":
    raise SystemExit(main())
