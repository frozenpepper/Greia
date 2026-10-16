"""Greia persistence and event adapters for Cloud Bedtime.

Progress lives under ``nanna_delle_nuvolette.progress.v1`` (profile-scoped
Greia Storage): the ladder rung and the number of finished nights. The
pre-rework Activity saved favourite blanket colours under
``nanna_delle_nuvolette.preferences.v1``; that key is history the child
created, so it is never rewritten or deleted. A child who already finished a
night with the old game (the old key exists) simply starts the new ladder at
its first rung, like everyone else. Anything unknown or corrupt loads as a
fresh start and is only written back after the child finishes a night.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .cloud_content import MAX_LEVEL, STORAGE_KEY
else:
    from cloud_content import MAX_LEVEL, STORAGE_KEY

SCHEMA_VERSION: Final = 1
MAX_NIGHTS: Final = 1_000_000
EVENT_REST_COMPLETED: Final = "cloud.rest_completed"


@dataclass(frozen=True, slots=True)
class BedtimeProgress:
    level: int = 0
    nights: int = 0


class ProgressPort(Protocol):
    def load(self) -> BedtimeProgress: ...
    def save(self, progress: BedtimeProgress) -> None: ...


class EventPort(Protocol):
    def rest_completed(self, session_id: str, payload: dict[str, Any]) -> None: ...


def _int(value: object, default: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(low, min(high, value))


def parse_progress(raw: object) -> BedtimeProgress:
    """Bounded parse of any stored payload (current or corrupt)."""

    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        return BedtimeProgress()
    return BedtimeProgress(
        level=_int(raw.get("level"), 0, 0, MAX_LEVEL),
        nights=_int(raw.get("nights"), 0, 0, MAX_NIGHTS),
    )


def progress_payload(progress: BedtimeProgress) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "level": max(0, min(MAX_LEVEL, int(progress.level))),
        "nights": max(0, min(MAX_NIGHTS, int(progress.nights))),
    }


class GreiaBedtimeProgress:
    """Map bounded progress onto profile-scoped Greia Storage (fail-soft)."""

    def __init__(self, storage=None) -> None:
        if storage is None:
            try:
                storage = get_storage()
            except Exception:
                storage = None
        self._storage = storage

    def load(self) -> BedtimeProgress:
        if self._storage is None:
            return BedtimeProgress()
        try:
            return parse_progress(self._storage.kv_get(STORAGE_KEY))
        except Exception:
            return BedtimeProgress()

    def save(self, progress: BedtimeProgress) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaCloudEvents:
    """Publish the completion fact declared by the manifest."""

    def rest_completed(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(EVENT_REST_COMPLETED, payload, idempotency_key=f"cloud-rest:{session_id}")
        except Exception:
            return


__all__ = [
    "BedtimeProgress",
    "EVENT_REST_COMPLETED",
    "EventPort",
    "GreiaBedtimeProgress",
    "GreiaCloudEvents",
    "ProgressPort",
    "SCHEMA_VERSION",
    "parse_progress",
    "progress_payload",
]
