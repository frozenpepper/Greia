"""Pure domain state for Painting.

No pygame imports. Owns painting records, stroke history and
profile-scoped Greia Storage mapping. Canvas bitmap handling
(PNG encode/decode) lives with the app/renderer because it needs
PIL + pygame surfaces; this module stays focused on invariants
and storage contracts so it can be tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
import uuid

if __package__:
    from .painting_content import INDEX_KEY, MAX_PAINTINGS, MAX_STROKE_POINTS, MAX_UNDO_STROKES
else:  # pragma: no cover - runtime/script fallback
    from painting_content import INDEX_KEY, MAX_PAINTINGS, MAX_STROKE_POINTS, MAX_UNDO_STROKES


@dataclass(frozen=True, slots=True)
class PaintingRecord:
    painting_id: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.painting_id}


class PaintingRepository:
    """Profile-scoped Greia Storage mapping for Painting creations.

    The index key holds ordered painting records; private files hold
    PNG bytes. The repository never evicts old work to satisfy a quota;
    it refuses new creations when the library bound is reached.
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
    """Bounded undo stack for recent strokes.

    When the window fills, the oldest stroke is returned so the
    caller can fold it permanently into the base canvas. Visible
    artwork remains intact while memory growth stays bounded.
    """

    def __init__(self, maximum: int = MAX_UNDO_STROKES) -> None:
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


__all__ = [
    "PaintingRecord",
    "PaintingRepository",
    "Stroke",
    "StrokeHistory",
]
