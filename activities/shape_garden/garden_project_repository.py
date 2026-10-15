"""Profile-private persistence for the Shape Garden library.

Layout inside the Activity's Greia Storage namespace:

* ``shape_garden.gardens.v2`` — ordered list of garden ids (newest first);
* ``shape_garden.garden.<id>`` — one schema-2 garden record each;
* ``garden/backgrounds/<sha256>.png`` — imported backdrop pictures, content
  addressed and shared by every garden that uses them;
* ``garden/shared.png`` — the one replace-in-place staging file the trusted
  Creations broker copies when the child shares a picture.

The repository never evicts work to make room: ``create`` refuses when the
library is full and only an explicit, child-confirmed ``delete`` removes a
garden. The v1 single project is migrated once into the first garden and its
key is left untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import uuid

if __package__:
    from .garden_content import (
        BACKGROUND_PREFIX,
        EXPORT_NAME,
        GARDEN_KEY_PREFIX,
        INDEX_KEY,
        LEGACY_STORAGE_KEY,
        MAX_BACKGROUND_BYTES,
        MAX_GARDENS,
    )
    from .garden_project_model import GardenProject, legacy_state
else:  # pragma: no cover - direct script fallback
    from garden_content import (
        BACKGROUND_PREFIX,
        EXPORT_NAME,
        GARDEN_KEY_PREFIX,
        INDEX_KEY,
        LEGACY_STORAGE_KEY,
        MAX_BACKGROUND_BYTES,
        MAX_GARDENS,
    )
    from garden_project_model import GardenProject, legacy_state


class GardenProjectError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GardenRecord:
    garden_id: str


class GardenProjectRepository:
    """Persist a bounded, ordered library of editable gardens."""

    def __init__(self, storage) -> None:
        self.storage = storage
        # v1 garden migrated in memory when the store refused the write.
        self._pending_legacy: tuple[GardenRecord, GardenProject] | None = None

    # -- index -----------------------------------------------------------------

    def list_records(self) -> list[GardenRecord]:
        raw = self.storage.kv_get(INDEX_KEY, None)
        if raw is None:
            if self._pending_legacy is not None:
                return [self._pending_legacy[0]]
            return self._migrate_v1()
        ids = raw.get("gardens") if isinstance(raw, dict) else None
        if not isinstance(ids, list):
            return []
        records: list[GardenRecord] = []
        seen: set[str] = set()
        for garden_id in ids:
            if isinstance(garden_id, str) and _valid_id(garden_id) and garden_id not in seen:
                seen.add(garden_id)
                records.append(GardenRecord(garden_id))
            if len(records) >= MAX_GARDENS:
                break
        return records

    def is_full(self) -> bool:
        return len(self.list_records()) >= MAX_GARDENS

    def _write_index(self, records: list[GardenRecord]) -> None:
        self.storage.kv_set(INDEX_KEY, {"schema": 2, "gardens": [r.garden_id for r in records]})

    def _migrate_v1(self) -> list[GardenRecord]:
        """Turn the v1 project into the first garden (once, non-destructively)."""
        try:
            state = legacy_state(self.storage.kv_get(LEGACY_STORAGE_KEY, None))
        except (RuntimeError, ValueError):
            state = None
        if state is None:
            return []
        record = GardenRecord(uuid.uuid4().hex)
        try:
            self.storage.kv_set(self._key(record.garden_id), GardenProject(state).as_raw())
            self._write_index([record])
        except RuntimeError:
            # Read-only/full store: show the migrated garden this session; the
            # untouched v1 key lets the next start migrate again.
            self._pending_legacy = (record, GardenProject(state))
            return [record]
        return [record]

    # -- gardens ---------------------------------------------------------------

    def load(self, garden_id: str) -> GardenProject:
        _require_id(garden_id)
        pending = self._pending_legacy
        if pending is not None and pending[0].garden_id == garden_id:
            return pending[1]
        raw = self.storage.kv_get(self._key(garden_id), None)
        try:
            return GardenProject.from_raw(raw)
        except ValueError as exc:
            raise GardenProjectError("invalid garden record") from exc

    def create(self, project: GardenProject) -> GardenRecord:
        records = self.list_records()
        if len(records) >= MAX_GARDENS:
            raise GardenProjectError("garden library is full")
        record = GardenRecord(uuid.uuid4().hex)
        try:
            self.storage.kv_set(self._key(record.garden_id), project.as_raw())
            self._write_index([record, *records])
        except RuntimeError as exc:
            try:
                self.storage.kv_delete(self._key(record.garden_id))
            except (RuntimeError, AttributeError):
                pass
            raise GardenProjectError("garden write failed") from exc
        return record

    def save(self, garden_id: str, project: GardenProject) -> GardenRecord:
        """Rewrite one garden and move it to the front of the library."""
        _require_id(garden_id)
        try:
            self.storage.kv_set(self._key(garden_id), project.as_raw())
            records = self.list_records()
            others = [r for r in records if r.garden_id != garden_id]
            record = GardenRecord(garden_id)
            unindexed = self._pending_legacy is not None
            if unindexed or not records or records[0].garden_id != garden_id:
                self._write_index([record, *others][:MAX_GARDENS])
        except RuntimeError as exc:
            raise GardenProjectError("garden write failed") from exc
        self._pending_legacy = None
        return record

    def delete(self, garden_id: str) -> bool:
        """Remove one garden the child explicitly confirmed deleting.

        The index entry goes first so a failed record removal can never leave
        a visible card without data. Pictures it alone used are reclaimed;
        copies already shared to My Creations are independent and untouched.
        """
        _require_id(garden_id)
        records = self.list_records()
        remaining = [r for r in records if r.garden_id != garden_id]
        if len(remaining) == len(records):
            return False
        try:
            self._write_index(remaining)
        except RuntimeError as exc:
            raise GardenProjectError("garden delete failed") from exc
        try:
            self.storage.kv_delete(self._key(garden_id))
        except (RuntimeError, AttributeError):
            pass  # an unlisted record is harmless
        self.reclaim_pictures(remaining)
        return True

    # -- pictures -----------------------------------------------------------------

    @staticmethod
    def picture_name(digest: str) -> str:
        return f"{BACKGROUND_PREFIX}/{digest}.png"

    def store_picture(self, payload: bytes) -> str:
        if not isinstance(payload, bytes) or not payload or len(payload) > MAX_BACKGROUND_BYTES:
            raise GardenProjectError("garden picture exceeds bounds")
        digest = hashlib.sha256(payload).hexdigest()
        try:
            self.storage.file_write_atomic(self.picture_name(digest), payload)
        except RuntimeError as exc:
            raise GardenProjectError("garden picture write failed") from exc
        return digest

    def load_picture(self, digest: str) -> bytes:
        try:
            payload = self.storage.file_read(self.picture_name(digest))
        except RuntimeError as exc:
            raise GardenProjectError("garden picture missing") from exc
        if (
            not isinstance(payload, bytes)
            or not payload
            or len(payload) > MAX_BACKGROUND_BYTES
            or hashlib.sha256(payload).hexdigest() != digest
        ):
            raise GardenProjectError("garden picture failed integrity check")
        return payload

    def reclaim_pictures(self, records: list[GardenRecord] | None = None, *, keep: str | None = None) -> None:
        """Delete pictures no listed garden references (bounded repair work)."""
        records = self.list_records() if records is None else records
        used = {keep} if keep else set()
        for record in records:
            try:
                picture = self.load(record.garden_id).state.picture
            except (GardenProjectError, RuntimeError, ValueError):
                return  # never reclaim while a garden cannot be read
            if picture:
                used.add(picture)
        try:
            names = self.storage.file_list(prefix=BACKGROUND_PREFIX)
        except (RuntimeError, AttributeError):
            return
        for name in names[:32]:
            digest = name.rsplit("/", 1)[-1].removesuffix(".png")
            if digest not in used:
                try:
                    self.storage.file_delete(name)
                except RuntimeError:
                    pass

    # -- sharing ---------------------------------------------------------------------

    def save_export(self, payload: bytes) -> str:
        """Write one replace-in-place PNG source for trusted publication."""
        if not isinstance(payload, bytes) or not payload or len(payload) > MAX_BACKGROUND_BYTES:
            raise GardenProjectError("garden export exceeds bounds")
        try:
            self.storage.file_write_atomic(EXPORT_NAME, payload)
        except RuntimeError as exc:
            raise GardenProjectError("garden export write failed") from exc
        return EXPORT_NAME

    @staticmethod
    def _key(garden_id: str) -> str:
        return f"{GARDEN_KEY_PREFIX}{garden_id}"


def _valid_id(value: str) -> bool:
    return len(value) == 32 and all(ch in "0123456789abcdef" for ch in value)


def _require_id(value: object) -> None:
    if not isinstance(value, str) or not _valid_id(value):
        raise GardenProjectError("invalid garden id")


__all__ = ["GardenProjectError", "GardenProjectRepository", "GardenRecord"]
