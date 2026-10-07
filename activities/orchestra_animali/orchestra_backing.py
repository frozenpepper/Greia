"""Durable private backing-track ownership for Orchestra Animali.

The shared Creation is only an import source. Once the child chooses it,
Orchestra owns a content-addressed private WAV snapshot plus a tiny metadata
pointer. The star/progression state remains a separate storage concern.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


BACKING_KEY = "orchestra_animali.backing.v1"
BACKING_PREFIX = "orchestra/backing"
MAX_BACKING_BYTES = 16 * 1024 * 1024
SUPPORTED_BACKING_ROLES = frozenset({"narration", "song", "music"})


class BackingTrackStoreError(RuntimeError):
    """The persisted backing-track pointer/blob is unavailable or inconsistent."""


@dataclass(frozen=True, slots=True)
class BackingTrackRecord:
    sha256: str
    role: str
    title: str
    duration_seconds: float

    def __post_init__(self) -> None:
        if (
            len(self.sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.sha256)
        ):
            raise ValueError("invalid backing-track digest")
        if self.role not in SUPPORTED_BACKING_ROLES:
            raise ValueError("unsupported backing-track semantic role")
        if not isinstance(self.title, str) or len(self.title) > 100:
            raise ValueError("invalid backing-track title")
        if not 0.0 < float(self.duration_seconds) <= 90.0:
            raise ValueError("invalid backing-track duration")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "sha256": self.sha256,
            "role": self.role,
            "title": self.title,
            "duration_seconds": round(float(self.duration_seconds), 3),
        }

    @classmethod
    def from_raw(cls, raw: object) -> "BackingTrackRecord":
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ValueError("unsupported backing-track record")
        digest = raw.get("sha256")
        role = raw.get("role")
        title = raw.get("title", "")
        duration = raw.get("duration_seconds")
        if (
            not isinstance(digest, str)
            or not isinstance(role, str)
            or not isinstance(title, str)
            or not isinstance(duration, (int, float))
            or isinstance(duration, bool)
        ):
            raise ValueError("invalid backing-track record")
        return cls(digest, role, title, float(duration))


class BackingTrackRepository:
    """One authoritative private backing-track snapshot per profile/Activity."""

    def __init__(self, storage) -> None:
        self.storage = storage

    @staticmethod
    def _name(digest: str) -> str:
        return f"{BACKING_PREFIX}/{digest}.wav"

    def _record(self, *, strict: bool) -> BackingTrackRecord | None:
        try:
            raw = self.storage.kv_get(BACKING_KEY, None)
        except Exception as exc:
            if strict:
                raise BackingTrackStoreError(
                    "backing-track metadata could not be read"
                ) from exc
            return None
        if raw is None:
            return None
        try:
            return BackingTrackRecord.from_raw(raw)
        except ValueError as exc:
            if strict:
                raise BackingTrackStoreError(
                    "backing-track metadata is invalid"
                ) from exc
            return None

    def load(self) -> tuple[BackingTrackRecord, bytes] | None:
        record = self._record(strict=False)
        if record is None:
            return None
        try:
            payload = self.storage.file_read(self._name(record.sha256))
        except Exception:
            return None
        if (
            not isinstance(payload, bytes)
            or not payload
            or len(payload) > MAX_BACKING_BYTES
            or hashlib.sha256(payload).hexdigest() != record.sha256
        ):
            return None
        return record, payload

    def save(
        self,
        payload: bytes,
        *,
        role: str,
        title: str,
        duration_seconds: float,
    ) -> BackingTrackRecord:
        if (
            not isinstance(payload, bytes)
            or not payload
            or len(payload) > MAX_BACKING_BYTES
        ):
            raise BackingTrackStoreError("backing-track payload exceeds bounds")
        previous = self._record(strict=True)
        digest = hashlib.sha256(payload).hexdigest()
        record = BackingTrackRecord(
            digest,
            role,
            title[:100],
            float(duration_seconds),
        )
        name = self._name(digest)
        previous_digest = previous.sha256 if previous is not None else None
        try:
            self.storage.file_write_atomic(name, payload)
            self.storage.kv_set(BACKING_KEY, record.as_dict())
        except Exception as exc:
            if previous_digest != digest:
                try:
                    self.storage.file_delete(name)
                except Exception:
                    pass
            raise BackingTrackStoreError(
                "backing track could not be committed"
            ) from exc

        if previous_digest is not None and previous_digest != digest:
            try:
                self.storage.file_delete(self._name(previous_digest))
            except Exception:
                pass
        self._cleanup(keep=digest)
        return record

    def clear(self) -> bool:
        previous = self._record(strict=True)
        if previous is None:
            return True
        try:
            deleted = self.storage.kv_delete(BACKING_KEY)
        except Exception:
            return False
        if not deleted:
            return False
        try:
            self.storage.file_delete(self._name(previous.sha256))
        except Exception:
            pass
        self._cleanup(keep=None)
        return True

    def _cleanup(self, *, keep: str | None) -> None:
        keep_name = self._name(keep) if keep is not None else None
        try:
            names = self.storage.file_list(prefix=BACKING_PREFIX)
        except Exception:
            return
        for name in names[:8]:
            if name != keep_name:
                try:
                    self.storage.file_delete(name)
                except Exception:
                    pass


__all__ = [
    "BACKING_KEY",
    "BACKING_PREFIX",
    "BackingTrackRecord",
    "BackingTrackRepository",
    "BackingTrackStoreError",
    "MAX_BACKING_BYTES",
    "SUPPORTED_BACKING_ROLES",
]
