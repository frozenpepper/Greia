"""Greia persistence and event adapters for Colline Allegre.

Progress stays under the profile-scoped key the endless-distance version
used (``colline_allegre.progress``). That version stored
``{"best_distance", "total_stars", "timestamp"}``; it is read as schema 1 and
carried forward (the stars and best distance are kept, never dropped) into
schema 2, which adds the rung, a bounded tumble history used for adaptation
and how many courses and sets were finished.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .colline_content import HISTORY_LIMIT, MAX_RUNG, MIN_RUNG
else:
    from colline_content import HISTORY_LIMIT, MAX_RUNG, MIN_RUNG

STORAGE_KEY = "colline_allegre.progress"
SCHEMA_VERSION = 2
MAX_COUNT = 1_000_000
MAX_TUMBLES = 999


@dataclass(frozen=True, slots=True)
class CollineProgress:
    rung: int = MIN_RUNG
    history: tuple[int, ...] = ()  # tumbles per finished set, newest last
    sets: int = 0
    courses: int = 0
    total_stars: int = 0
    best_distance: float = 0.0  # metres, carried over from schema 1


class ProgressPort(Protocol):
    def load(self) -> CollineProgress: ...
    def save(self, progress: CollineProgress) -> None: ...


class EventPort(Protocol):
    def course_finished(self, session_id: str, payload: dict[str, int]) -> None: ...
    def set_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


def _count(value: object, limit: int = MAX_COUNT) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= limit else 0


def _distance(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    number = float(value)
    return number if math.isfinite(number) and 0.0 <= number <= 1e7 else 0.0


def parse_progress(raw: object) -> CollineProgress:
    """Read schema 2, migrate schema 1, recover from anything else."""

    if not isinstance(raw, dict):
        return CollineProgress()
    stars = _count(raw.get("total_stars", 0))
    best = _distance(raw.get("best_distance", 0.0))
    if raw.get("schema_version") != SCHEMA_VERSION:
        return CollineProgress(total_stars=stars, best_distance=best)
    rung = raw.get("rung", MIN_RUNG)
    if not isinstance(rung, int) or isinstance(rung, bool) or not MIN_RUNG <= rung <= MAX_RUNG:
        rung = MIN_RUNG
    history: list[int] = []
    items = raw.get("history", [])
    if isinstance(items, list):
        for item in items[-HISTORY_LIMIT:]:
            if isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= MAX_TUMBLES:
                history.append(item)
    return CollineProgress(rung, tuple(history), _count(raw.get("sets", 0)), _count(raw.get("courses", 0)), stars, best)


def serialize_progress(progress: CollineProgress) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "rung": max(MIN_RUNG, min(MAX_RUNG, int(progress.rung))),
        "history": [max(0, min(MAX_TUMBLES, int(item))) for item in tuple(progress.history)[-HISTORY_LIMIT:]],
        "sets": min(MAX_COUNT, max(0, int(progress.sets))),
        "courses": min(MAX_COUNT, max(0, int(progress.courses))),
        "total_stars": min(MAX_COUNT, max(0, int(progress.total_stars))),
        "best_distance": _distance(progress.best_distance),
    }


class GreiaCollineProgress:
    """Map bounded Activity progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage
        if self._storage is None:
            try:
                self._storage = get_storage()
            except Exception:
                self._storage = None

    def load(self) -> CollineProgress:
        if self._storage is None:
            return CollineProgress()
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return CollineProgress()
        return parse_progress(raw)

    def save(self, progress: CollineProgress) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, serialize_progress(progress))
        except Exception:
            return


class GreiaCollineEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def course_finished(self, session_id: str, payload: dict[str, int]) -> None:
        _emit("colline.course_finished", payload, f"colline:{session_id}:c{payload.get('course', 0)}")

    def set_completed(self, session_id: str, payload: dict[str, int]) -> None:
        _emit("colline.set_completed", payload, f"colline:{session_id}")


def _emit(event_id: str, payload: dict[str, int], key: str) -> None:
    """Facts are best effort: a missing runtime channel never stops play."""

    try:
        emit_activity_event(event_id, payload, idempotency_key=key)
    except Exception:
        return


__all__ = [
    "CollineProgress",
    "EventPort",
    "GreiaCollineEvents",
    "GreiaCollineProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "parse_progress",
    "serialize_progress",
]
