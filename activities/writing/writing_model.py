"""Pure domain state for Writing.

No Pygame imports. Owns document records, text buffer/cursor rules,
undo history and profile-scoped storage mapping. All grapheme
handling is through the shared Greia typography helpers.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
import uuid

from greia_platform.typography import (
    grapheme_boundaries,
    grapheme_spans,
    is_emoji_cluster,
    snap_grapheme_boundary,
    truncate_grapheme_safe,
)

if __package__:
    from .writing_content import (
        DEFAULT_TINT,
        INDEX_KEY,
        MAX_CHARACTERS,
        MAX_DOCUMENTS,
        MAX_UNDO_EDITS,
        MAX_UNDO_PAYLOAD_CHARS,
        PREVIEW_GRAPHEME_LIMIT,
        TINT_IDS,
    )
else:  # pragma: no cover - runtime/script fallback
    from writing_content import (
        DEFAULT_TINT,
        INDEX_KEY,
        MAX_CHARACTERS,
        MAX_DOCUMENTS,
        MAX_UNDO_EDITS,
        MAX_UNDO_PAYLOAD_CHARS,
        PREVIEW_GRAPHEME_LIMIT,
        TINT_IDS,
    )


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """One saved page: id, compact preview and the paper colour it uses.

    Index entries written before paper colours existed are plain
    ``{"id", "preview"}`` and load on the default cream paper. The tint is
    index metadata only; the document body remains plain UTF-8 text.
    """

    document_id: str
    preview: str
    tint: str = DEFAULT_TINT

    def as_dict(self) -> dict[str, str]:
        if self.tint == DEFAULT_TINT:
            return {"id": self.document_id, "preview": self.preview}
        return {"id": self.document_id, "preview": self.preview, "tint": self.tint}


class DocumentRepository:
    """Profile-scoped Greia Storage mapping for Writing documents.

    The index key holds ordered preview records; private files hold
    UTF-8 document bodies. Text storage is ordinary Unicode — never
    renderer glyph IDs or proprietary tokens. The repository never evicts old
    work to satisfy a bound: it refuses a new page when the library is full,
    and only an explicit, child-confirmed ``delete`` removes one.
    """

    def __init__(self, storage) -> None:
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
            tint = item.get("tint", DEFAULT_TINT)
            if tint not in TINT_IDS:
                tint = DEFAULT_TINT
            seen.add(document_id)
            records.append(
                DocumentRecord(
                    document_id,
                    truncate_grapheme_safe(preview, PREVIEW_GRAPHEME_LIMIT),
                    tint,
                ),
            )
            if len(records) >= MAX_DOCUMENTS:
                break
        return records

    def is_full(self) -> bool:
        """True when a new document would be refused by the library bound."""
        return len(self.list_records()) >= MAX_DOCUMENTS

    def create(self) -> DocumentRecord:
        return self.create_text("")

    def create_text(self, text: str, *, tint: str = DEFAULT_TINT) -> DocumentRecord:
        """Atomically create one new private UTF-8 document snapshot."""
        if tint not in TINT_IDS:
            raise ValueError("unknown paper tint")
        records = self.list_records()
        if len(records) >= MAX_DOCUMENTS:
            raise RuntimeError("document library limit reached")
        normalized = clamp_text(text)
        record = DocumentRecord(uuid.uuid4().hex, preview_text(normalized), tint)
        name = self._name(record.document_id)
        self.storage.file_write_atomic(name, normalized.encode("utf-8"))
        try:
            self._write_index([record, *records])
        except RuntimeError:
            try:
                self.storage.file_delete(name)
            except RuntimeError:
                pass
            raise
        return record

    def private_document_name(self, document_id: str) -> str:
        """Return a validated private source name for trusted publication."""
        _require_document_id(document_id)
        return self._name(document_id)

    def load_text(self, document_id: str) -> str:
        _require_document_id(document_id)
        decoded = self.storage.file_read(self._name(document_id)).decode("utf-8")
        return truncate_grapheme_safe(decoded, MAX_CHARACTERS)

    def save_text(self, document_id: str, text: str, *, tint: str | None = None) -> DocumentRecord:
        """Write the body and move the page to the front, keeping its tint."""
        _require_document_id(document_id)
        if tint is not None and tint not in TINT_IDS:
            raise ValueError("unknown paper tint")
        text = clamp_text(text)
        self.storage.file_write_atomic(self._name(document_id), text.encode("utf-8"))
        records = self.list_records()
        if tint is None:
            existing = next((item for item in records if item.document_id == document_id), None)
            tint = existing.tint if existing is not None else DEFAULT_TINT
        updated = DocumentRecord(document_id, preview_text(text), tint)
        others = [item for item in records if item.document_id != document_id]
        self._write_index([updated, *others])
        return updated

    def delete(self, document_id: str) -> bool:
        """Remove one page the child explicitly confirmed deleting.

        The index entry goes first so a failed file removal can never leave a
        visible card pointing at missing text. Copies already shared to My
        Creations are independent artifacts and are not touched.
        """
        _require_document_id(document_id)
        records = self.list_records()
        remaining = [item for item in records if item.document_id != document_id]
        if len(remaining) == len(records):
            return False
        self._write_index(remaining)
        try:
            self.storage.file_delete(self._name(document_id))
        except (RuntimeError, OSError):
            pass  # orphan bytes are harmless; the index no longer lists them
        return True

    def _write_index(self, records: list[DocumentRecord]) -> None:
        self.storage.kv_set(INDEX_KEY, [item.as_dict() for item in records])

    @staticmethod
    def _name(document_id: str) -> str:
        return f"documents/{document_id}.txt"


@dataclass(frozen=True, slots=True)
class TextEdit:
    """One undoable fragment edit (not a full-document snapshot)."""

    start: int
    removed: str
    inserted: str
    cursor_before: int
    cursor_after: int

    @property
    def payload_chars(self) -> int:
        return len(self.removed) + len(self.inserted)

    def undo(self, buffer: TextBuffer) -> None:
        if self.start < 0 or self.start + len(self.inserted) > len(buffer.text):
            raise ValueError("undo edit is outside the current text")
        if buffer.text[self.start : self.start + len(self.inserted)] != self.inserted:
            raise ValueError("undo edit no longer matches current text")
        buffer.text = (
            buffer.text[: self.start] + self.removed + buffer.text[self.start + len(self.inserted) :]
        )
        buffer.cursor = snap_grapheme_boundary(
            buffer.text,
            max(0, min(self.cursor_before, len(buffer.text))),
        )
        buffer.invalidate_graphemes()


@dataclass(slots=True)
class TextBuffer:
    """Grapheme-aware editable text with a single insertion cursor."""

    text: str = ""
    cursor: int = 0
    _boundaries: tuple[int, ...] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.text = clamp_text(self.text)
        self.cursor = snap_grapheme_boundary(
            self.text,
            max(0, min(int(self.cursor), len(self.text))),
        )

    def invalidate_graphemes(self) -> None:
        self._boundaries = None

    def _cursor_boundaries(self) -> tuple[int, ...]:
        if self._boundaries is None:
            self._boundaries = grapheme_boundaries(self.text)
        return self._boundaries

    def insert(self, value: str) -> TextEdit | None:
        if not value:
            return None
        value = truncate_grapheme_safe(value, max(0, MAX_CHARACTERS - len(self.text)))
        if not value:
            return None
        start = self.cursor
        cursor_before = self.cursor
        self.text = self.text[:start] + value + self.text[start:]
        self.cursor = start + len(value)
        self.invalidate_graphemes()
        return TextEdit(start, "", value, cursor_before, self.cursor)

    def backspace(self) -> TextEdit | None:
        if self.cursor == 0:
            return None
        boundaries = self._cursor_boundaries()
        cursor_before = self.cursor
        position = bisect.bisect_left(boundaries, self.cursor)
        start = boundaries[max(0, position - 1)]
        removed = self.text[start : self.cursor]
        self.text = self.text[:start] + self.text[self.cursor :]
        self.cursor = start
        self.invalidate_graphemes()
        return TextEdit(start, removed, "", cursor_before, self.cursor)

    def delete(self) -> TextEdit | None:
        if self.cursor >= len(self.text):
            return None
        boundaries = self._cursor_boundaries()
        cursor_before = self.cursor
        position = bisect.bisect_right(boundaries, self.cursor)
        end = boundaries[min(position, len(boundaries) - 1)]
        removed = self.text[self.cursor : end]
        self.text = self.text[: self.cursor] + self.text[end:]
        self.invalidate_graphemes()
        return TextEdit(self.cursor, removed, "", cursor_before, self.cursor)

    def move(self, delta: int) -> None:
        boundaries = self._cursor_boundaries()
        current = bisect.bisect_left(boundaries, self.cursor)
        target = max(0, min(len(boundaries) - 1, current + int(delta)))
        self.cursor = boundaries[target]

    def home(self) -> None:
        start = self.text.rfind("\n", 0, self.cursor)
        self.cursor = 0 if start < 0 else start + 1

    def end(self) -> None:
        end = self.text.find("\n", self.cursor)
        self.cursor = len(self.text) if end < 0 else end


class UndoHistory:
    """Bounded edit-fragment undo stack."""

    def __init__(
        self,
        maximum: int = MAX_UNDO_EDITS,
        max_payload_chars: int = MAX_UNDO_PAYLOAD_CHARS,
    ) -> None:
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
    return truncate_grapheme_safe(text, MAX_CHARACTERS)


def preview_text(text: str) -> str:
    compact = " ".join(text.replace("\x00", "").split())
    return truncate_grapheme_safe(compact, PREVIEW_GRAPHEME_LIMIT)


def card_badge(preview: str) -> str:
    """Pick the one big identity glyph for a gallery card.

    The first emoji the child used wins ("the dinosaur page"); otherwise the
    first letter or digit, exactly as typed (child text is never re-cased).
    Returns ``""`` for a page without either.
    """
    first_letter = ""
    for span in grapheme_spans(preview):
        if is_emoji_cluster(span.text):
            return span.text
        if not first_letter and span.text[:1].isalnum():
            first_letter = span.text
    return first_letter


def _valid_document_id(value: str) -> bool:
    return len(value) == 32 and all(ch in "0123456789abcdef" for ch in value)


def _require_document_id(value: str) -> None:
    if not isinstance(value, str) or not _valid_document_id(value):
        raise ValueError("invalid document id")


__all__ = [
    "DocumentRecord",
    "DocumentRepository",
    "TextBuffer",
    "TextEdit",
    "UndoHistory",
    "card_badge",
    "clamp_text",
    "preview_text",
]
