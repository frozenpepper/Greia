"""Profile-owned, immutable child creations; *trusted-platform* repository.

This is NOT an Activity SDK or a shared filesystem mount. Runtime Activities
must eventually access it only through a session-authorized selection/publish
broker. The repository does not authenticate producer identities by itself;
that responsibility belongs to the supervisor/broker trust boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .creation_capacity import VolumeBudget
from .creation_media import CreationMediaRegistry, CreationMediaError


class CreationLibraryError(RuntimeError):
    """A creation operation failed without exposing a host filesystem path."""


class CreationNotFound(CreationLibraryError):
    """The specified creation is absent from the active profile's library."""


_TOKEN = re.compile(r"^[a-z][a-z0-9._-]{0,95}$")
_ID = re.compile(r"^[0-9a-f]{32}$")
_SCHEMA_VERSION = 1
_PREVIEW_MAX_BYTES = 2 * 1024 * 1024


def _bounded_token(value: str, label: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def _creation_id(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("invalid creation identifier")
    return value


@dataclass(frozen=True, slots=True)
class CreationRecord:
    creation_id: str
    producer_id: str
    media_type: str
    role: str
    title: str
    created_at: str
    content_bytes: int
    sha256: str
    attributes: dict[str, int | float | str]

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "CreationRecord":
        return cls(
            creation_id=row["creation_id"],
            producer_id=row["producer_id"],
            media_type=row["media_type"],
            role=row["role"],
            title=row["title"],
            created_at=row["created_at"],
            content_bytes=row["content_bytes"],
            sha256=row["sha256"],
            attributes=json.loads(row["attributes_json"]),
        )


class CreationLibrary:
    """Transactional metadata and immutable artifacts for *one* child profile.

    Store paths derive exclusively from random internal identifiers plus
    explicitly registered media extensions. Callers must never supply paths.
    Metadata is SQLite in rollback-journal mode for portable consistent backup
    snapshots. Crash-orphan cleanup is a separate bounded maintenance task.
    """

    def __init__(
        self,
        root: Path,
        *,
        media: CreationMediaRegistry | None = None,
        volume_budget: VolumeBudget | None = None,
    ) -> None:
        if root.is_symlink():
            raise CreationLibraryError("creations root cannot be a symlink")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not root.is_dir():
            raise CreationLibraryError("creations root is not a directory")
        self.root = root.resolve(strict=True)
        self.blobs = self.root / "blobs"
        if self.blobs.is_symlink():
            raise CreationLibraryError("creations blob root cannot be a symlink")
        self.blobs.mkdir(mode=0o700, exist_ok=True)
        self._media = media or CreationMediaRegistry()
        self._volume_budget = volume_budget or VolumeBudget()
        self._db_path = self.root / "index.sqlite3"
        if self._db_path.is_symlink():
            raise CreationLibraryError("creations index cannot be a symlink")
        with self._connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, _SCHEMA_VERSION):
                raise CreationLibraryError("creation library schema requires migration")
            db.execute("""
                CREATE TABLE IF NOT EXISTS creations (
                    creation_id TEXT PRIMARY KEY,
                    producer_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    role TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    content_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    attributes_json TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS creations_recent ON creations(created_at DESC, creation_id DESC)")
            if version == 0:
                db.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self._db_path, timeout=3.0, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    def _blob_path(self, creation_id: str, media_type: str) -> Path:
        codec = self._media.codec_for(media_type)
        return self.blobs / f"{_creation_id(creation_id)}.{codec.extension}"

    def _preview_path(self, creation_id: str) -> Path:
        return self.blobs / f"{_creation_id(creation_id)}.preview.png"

    @staticmethod
    def _write_atomic(target: Path, content: bytes) -> None:
        fd, temp_name = tempfile.mkstemp(prefix=".pending-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, target)
        finally:
            if os.path.lexists(temp_name):
                os.unlink(temp_name)

    @staticmethod
    def _read_bounded(path: Path, max_bytes: int) -> bytes:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                    raise CreationLibraryError("stored creation file is invalid")
                data = stream.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise CreationLibraryError("stored creation exceeds media bounds")
                return data
        except OSError as exc:
            raise CreationLibraryError("stored creation file is unavailable") from exc

    def publish(
        self,
        payload: bytes,
        *,
        producer_id: str,
        media_type: str,
        role: str,
        title: str = "",
    ) -> CreationRecord:
        """Create an immutable snapshot; never rewrite a previously published ID."""
        _bounded_token(producer_id, "producer")
        _bounded_token(role, "semantic role")
        if not isinstance(title, str) or len(title) > 100 or "\x00" in title:
            raise ValueError("invalid creation title")
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError("creation payload must be bytes")
        prepared = self._media.codec_for(media_type).prepare(bytes(payload))
        if len(prepared.preview) > _PREVIEW_MAX_BYTES:
            raise CreationMediaError("generated preview exceeds size policy")
        byte_growth = len(prepared.data) + len(prepared.preview)
        artifact_id = uuid.uuid4().hex
        blob = self._blob_path(artifact_id, media_type)
        preview = self._preview_path(artifact_id)
        record = CreationRecord(
            creation_id=artifact_id,
            producer_id=producer_id,
            media_type=media_type,
            role=role,
            title=title,
            created_at=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            content_bytes=len(prepared.data),
            sha256=hashlib.sha256(prepared.data).hexdigest(),
            attributes=prepared.attributes,
        )
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._volume_budget.require_growth(self.root, byte_growth)
                self._write_atomic(blob, prepared.data)
                if prepared.preview:
                    self._write_atomic(preview, prepared.preview)
                db.execute(
                    """INSERT INTO creations (
                        creation_id, producer_id, media_type, role, title, created_at,
                        content_bytes, sha256, attributes_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (record.creation_id, record.producer_id, record.media_type,
                     record.role, record.title, record.created_at,
                     record.content_bytes, record.sha256,
                     json.dumps(record.attributes, separators=(",", ":"))),
                )
                db.execute("COMMIT")
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                for path in (preview, blob):
                    path.unlink(missing_ok=True)
                raise
        return record

    def _get(self, creation_id: str) -> CreationRecord:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM creations WHERE creation_id = ?",
                (_creation_id(creation_id),),
            ).fetchone()
        if row is None:
            raise CreationNotFound("creation does not exist")
        return CreationRecord.from_row(row)

    def list(
        self,
        *,
        media_type: str | None = None,
        limit: int = 24,
        offset: int = 0,
    ) -> tuple[CreationRecord, ...]:
        """Return metadata only; galleries fetch previews on demand by ID."""
        if type(limit) is not int or not 1 <= limit <= 64 or type(offset) is not int or offset < 0:
            raise ValueError("invalid bounded creation page")
        params: tuple[Any, ...]
        if media_type is not None:
            self._media.codec_for(media_type)
            query = "SELECT * FROM creations WHERE media_type = ? ORDER BY created_at DESC, creation_id DESC LIMIT ? OFFSET ?"
            params = (media_type, limit, offset)
        else:
            query = "SELECT * FROM creations ORDER BY created_at DESC, creation_id DESC LIMIT ? OFFSET ?"
            params = (limit, offset)
        with self._connect() as db:
            return tuple(CreationRecord.from_row(row) for row in db.execute(query, params))

    def read(self, creation_id: str) -> bytes:
        record = self._get(creation_id)
        codec = self._media.codec_for(record.media_type)
        payload = self._read_bounded(self._blob_path(record.creation_id, record.media_type), codec.max_source_bytes)
        if len(payload) != record.content_bytes or hashlib.sha256(payload).hexdigest() != record.sha256:
            raise CreationLibraryError("creation failed integrity validation")
        return payload

    def preview(self, creation_id: str) -> tuple[str, bytes]:
        """Return a thumbnail, text snippet or a playable WAV by semantic type.

        Presentation/play/stop is owned by the common child-facing picker UI.
        Do not call this method repeatedly inside rendering/frame loops.
        """
        record = self._get(creation_id)
        codec = self._media.codec_for(record.media_type)
        return codec.preview(
            original=lambda: self.read(record.creation_id),
            thumbnail=lambda: self._read_bounded(
                self._preview_path(record.creation_id), _PREVIEW_MAX_BYTES
            ),
        )

    def delete(self, creation_id: str) -> bool:
        """Delete only this profile's artifact, never an importing snapshot.

        After index removal a power cut may leave an unreferenced blob; bounded
        orphan reconciliation is a future service-maintenance responsibility.
        """
        try:
            record = self._get(creation_id)
        except CreationNotFound:
            return False
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM creations WHERE creation_id = ?", (record.creation_id,))
            db.execute("COMMIT")
        for path in (self._preview_path(record.creation_id), self._blob_path(record.creation_id, record.media_type)):
            path.unlink(missing_ok=True)
        return True
