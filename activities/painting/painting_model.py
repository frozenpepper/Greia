"""Pure domain state for Painting.

No pygame imports. Owns painting records, the mark history (strokes and
stamps) and profile-scoped Greia Storage mapping. Canvas bitmap handling
(PNG encode/decode) lives with the app/renderer because it needs
PIL + pygame surfaces; this module stays focused on invariants
and storage contracts so it can be tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
import uuid

if __package__:
    from .painting_content import COLOURING_PAGES, INDEX_KEY, MAX_PAINTINGS, MAX_STROKE_POINTS, MAX_UNDO_STROKES
else:  # pragma: no cover - runtime/script fallback
    from painting_content import COLOURING_PAGES, INDEX_KEY, MAX_PAINTINGS, MAX_STROKE_POINTS, MAX_UNDO_STROKES


@dataclass(frozen=True, slots=True)
class PaintingRecord:
    """One saved painting; ``page`` names the colouring page it started from.

    Index entries written before colouring pages existed are plain
    ``{"id": ...}`` and load as free paintings (``page`` is ``None``).
    """

    painting_id: str
    page: str | None = None

    def as_dict(self) -> dict[str, str]:
        if self.page is None:
            return {"id": self.painting_id}
        return {"id": self.painting_id, "page": self.page}


class PaintingRepository:
    """Profile-scoped Greia Storage mapping for Painting creations.

    The index key holds ordered painting records; private files hold
    PNG bytes. The repository never evicts old work to satisfy a quota;
    it refuses new creations when the library bound is reached, and only
    an explicit, child-confirmed ``delete`` removes a painting.
    """

    def __init__(self, storage) -> None:
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
            page = item.get("page")
            if page not in COLOURING_PAGES:
                # Unknown/removed page ids degrade to a free painting; the
                # saved PNG already contains the flattened outline.
                page = None
            seen.add(painting_id)
            records.append(PaintingRecord(painting_id, page))
            if len(records) >= MAX_PAINTINGS:
                break
        return records

    def is_full(self) -> bool:
        """True when a new painting would be refused by the library bound."""
        return len(self.list_records()) >= MAX_PAINTINGS

    def create(self, initial_png: bytes, *, page: str | None = None) -> PaintingRecord:
        if page is not None and page not in COLOURING_PAGES:
            raise ValueError("unknown colouring page")
        records = self.list_records()
        if len(records) >= MAX_PAINTINGS:
            raise RuntimeError("painting library limit reached")
        record = PaintingRecord(uuid.uuid4().hex, page)
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

    def private_png_name(self, painting_id: str) -> str:
        """Bounded private source for the platform's trusted publish broker."""
        _require_id(painting_id)
        return self._name(painting_id)

    def save_png(self, painting_id: str, payload: bytes) -> PaintingRecord:
        _require_id(painting_id)
        self.storage.file_write_atomic(self._name(painting_id), bytes(payload))
        records = self.list_records()
        existing = next((item for item in records if item.painting_id == painting_id), None)
        record = existing if existing is not None else PaintingRecord(painting_id)
        others = [item for item in records if item.painting_id != painting_id]
        self._write_index([record, *others])
        return record

    def delete(self, painting_id: str) -> bool:
        """Remove one painting the child explicitly confirmed deleting.

        The index entry goes first so a failed file removal can never leave
        a visible card pointing at missing bytes. Copies already shared to
        My Creations are independent artifacts and are not touched.
        """
        _require_id(painting_id)
        records = self.list_records()
        remaining = [item for item in records if item.painting_id != painting_id]
        if len(remaining) == len(records):
            return False
        self._write_index(remaining)
        try:
            self.storage.file_delete(self._name(painting_id))
        except (RuntimeError, OSError):
            pass  # orphan bytes are harmless; the index no longer lists them
        return True

    def _write_index(self, records: list[PaintingRecord]) -> None:
        self.storage.kv_set(INDEX_KEY, [item.as_dict() for item in records])

    @staticmethod
    def _name(painting_id: str) -> str:
        return f"paintings/{painting_id}.png"


@dataclass(frozen=True, slots=True)
class Stroke:
    """One freehand line (brush or eraser) in canvas pixels."""

    color: tuple[int, int, int]
    size: int
    points: tuple[tuple[int, int], ...]

    def validate(self) -> None:
        if self.size <= 0 or not self.points:
            raise ValueError("stroke must have positive size and at least one point")
        if len(self.points) > MAX_STROKE_POINTS:
            raise ValueError("stroke exceeds point bound")


@dataclass(frozen=True, slots=True)
class Stamp:
    """One placed shared-library stamp, centred at ``center`` (canvas pixels)."""

    asset_id: str
    center: tuple[int, int]
    size: int

    def validate(self) -> None:
        if self.size <= 0 or not self.asset_id:
            raise ValueError("stamp must have an asset and a positive size")


Mark = Stroke | Stamp


class StrokeHistory:
    """Bounded undo stack for recent marks (strokes and stamps).

    When the window fills, the oldest mark is returned so the
    caller can fold it permanently into the base canvas. Visible
    artwork remains intact while memory growth stays bounded.
    """

    def __init__(self, maximum: int = MAX_UNDO_STROKES) -> None:
        if maximum < 1:
            raise ValueError("undo history must retain at least one stroke")
        self.maximum = int(maximum)
        self._items: list[Mark] = []

    @property
    def items(self) -> tuple[Mark, ...]:
        return tuple(self._items)

    def add(self, mark: Mark) -> Mark | None:
        mark.validate()
        self._items.append(mark)
        if len(self._items) <= self.maximum:
            return None
        return self._items.pop(0)

    def undo(self) -> Mark | None:
        return self._items.pop() if self._items else None

    def clear(self) -> None:
        self._items.clear()


def _valid_id(value: str) -> bool:
    return len(value) == 32 and all(ch in "0123456789abcdef" for ch in value)


def _require_id(value: str) -> None:
    if not isinstance(value, str) or not _valid_id(value):
        raise ValueError("invalid painting id")


__all__ = [
    "Mark",
    "PaintingRecord",
    "PaintingRepository",
    "Stamp",
    "Stroke",
    "StrokeHistory",
]
