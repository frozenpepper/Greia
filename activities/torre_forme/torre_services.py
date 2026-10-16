"""Greia persistence and event adapters for La Torre delle Forme.

Progress lives under the same profile-scoped key the earlier falling-block
version used (``torre_forme_save``). That version stored only
``{"stars": n}``; it is read as schema 1 and carried forward (the stars are
kept, never dropped) into schema 2, which adds the rung, the bounded attempt
history used for adaptation and the number of finished builds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .torre_model import HISTORY_LIMIT, MAX_LEVEL, AttemptSummary
else:
    from torre_model import HISTORY_LIMIT, MAX_LEVEL, AttemptSummary


STORAGE_KEY = "torre_forme_save"
SCHEMA_VERSION = 2
MAX_COUNT = 1_000_000


@dataclass(frozen=True, slots=True)
class TorreProgress:
    level: int = 1
    history: tuple[AttemptSummary, ...] = ()
    builds: int = 0
    stars: int = 0  # carried over from the schema-1 falling-block game


class ProgressPort(Protocol):
    def load(self) -> TorreProgress: ...
    def save(self, progress: TorreProgress) -> None: ...


class EventPort(Protocol):
    def build_completed(self, session_id: str, payload: dict[str, int]) -> None: ...
    def set_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


def _count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_COUNT else 0


def parse_progress(raw: object) -> TorreProgress:
    """Read schema 2, migrate schema 1 (``{"stars": n}``), recover from junk."""

    if not isinstance(raw, dict):
        return TorreProgress()
    stars = _count(raw.get("stars", 0))
    if raw.get("schema_version") != SCHEMA_VERSION:
        return TorreProgress(stars=stars)
    level = raw.get("level", 1)
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= MAX_LEVEL:
        level = 1
    parsed: list[AttemptSummary] = []
    history = raw.get("history", [])
    if isinstance(history, list):
        for item in history[-HISTORY_LIMIT:]:
            if not isinstance(item, dict):
                continue
            first = item.get("first_attempt_success")
            hints = item.get("hints_used")
            retry = item.get("used_retry")
            if isinstance(first, bool) and isinstance(hints, int) and 0 <= hints <= 32 and isinstance(retry, bool):
                parsed.append(AttemptSummary(first, hints, retry))
    return TorreProgress(level, tuple(parsed), _count(raw.get("builds", 0)), stars)


def serialize_progress(progress: TorreProgress) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "level": max(1, min(MAX_LEVEL, int(progress.level))),
        "history": [
            {
                "first_attempt_success": item.first_attempt_success,
                "hints_used": item.hints_used,
                "used_retry": item.used_retry,
            }
            for item in tuple(progress.history)[-HISTORY_LIMIT:]
        ],
        "builds": min(MAX_COUNT, max(0, int(progress.builds))),
        "stars": min(MAX_COUNT, max(0, int(progress.stars))),
    }


class GreiaTorreProgress:
    """Map bounded Activity progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def load(self) -> TorreProgress:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return TorreProgress()
        return parse_progress(raw)

    def save(self, progress: TorreProgress) -> None:
        try:
            self._storage.kv_set(STORAGE_KEY, serialize_progress(progress))
        except Exception:
            return


class GreiaTorreEvents:
    """Publish milestone and completion facts declared by the manifest."""

    def build_completed(self, session_id: str, payload: dict[str, int]) -> None:
        index = payload.get("build_index", 1)
        _emit("tower.build_completed", payload, f"torre-forme:{session_id}:b{index}")

    def set_completed(self, session_id: str, payload: dict[str, int]) -> None:
        _emit("tower.set_completed", payload, f"torre-forme:{session_id}")


def _emit(event_id: str, payload: dict[str, int], key: str) -> None:
    """Facts are best effort: a missing runtime channel never stops play."""

    try:
        emit_activity_event(event_id, payload, idempotency_key=key)
    except Exception:
        return


__all__ = [
    "EventPort",
    "GreiaTorreEvents",
    "GreiaTorreProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "TorreProgress",
    "parse_progress",
    "serialize_progress",
]
