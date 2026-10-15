"""Greia persistence and event adapters for Mondo Contrari.

Progress is a tiny profile-scoped record (adaptive level + bounded evidence)
in the Activity's own Greia Storage namespace. The previous toy kept no saved
data, so there is nothing to migrate; malformed records recover to defaults.
Events keep the manifest's two declared ids: one milestone per opposite pair
the child completes and one completion per finished visit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .contrari_model import HISTORY_LIMIT, MAX_LEVEL, MIN_LEVEL, AttemptSummary, OppositeCategory
else:
    from contrari_model import HISTORY_LIMIT, MAX_LEVEL, MIN_LEVEL, AttemptSummary, OppositeCategory

STORAGE_KEY = "mondo_contrari.progress.v1"


@dataclass(frozen=True, slots=True)
class ContrariProgress:
    level: int = MIN_LEVEL
    history: tuple[AttemptSummary, ...] = ()


class ProgressPort(Protocol):
    def load(self) -> ContrariProgress: ...
    def save(self, level: int, history: Sequence[AttemptSummary]) -> None: ...


class EventPort(Protocol):
    def opposite_explored(self, session_id: str, category: OppositeCategory) -> None: ...
    def all_opposites_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


class GreiaContrariProgress:
    """Map bounded Activity progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def load(self) -> ContrariProgress:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return ContrariProgress()
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            return ContrariProgress()
        level = raw.get("level", MIN_LEVEL)
        if not isinstance(level, int) or isinstance(level, bool) or not MIN_LEVEL <= level <= MAX_LEVEL:
            level = MIN_LEVEL
        parsed: list[AttemptSummary] = []
        history = raw.get("history", [])
        if isinstance(history, list):
            for item in history[-HISTORY_LIMIT:]:
                if not isinstance(item, dict):
                    continue
                first = item.get("first_attempt_success")
                hints = item.get("hints_used")
                retry = item.get("used_retry")
                if (
                    isinstance(first, bool)
                    and isinstance(hints, int)
                    and not isinstance(hints, bool)
                    and 0 <= hints <= 32
                    and isinstance(retry, bool)
                ):
                    parsed.append(AttemptSummary(first, hints, retry))
        return ContrariProgress(level, tuple(parsed))

    def save(self, level: int, history: Sequence[AttemptSummary]) -> None:
        bounded = tuple(history[-HISTORY_LIMIT:])
        payload = {
            "schema_version": 1,
            "level": max(MIN_LEVEL, min(MAX_LEVEL, int(level))),
            "history": [
                {
                    "first_attempt_success": item.first_attempt_success,
                    "hints_used": item.hints_used,
                    "used_retry": item.used_retry,
                }
                for item in bounded
            ],
        }
        try:
            self._storage.kv_set(STORAGE_KEY, payload)
        except Exception:
            return


class GreiaContrariEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def opposite_explored(self, session_id: str, category: OppositeCategory) -> None:
        emit_activity_event(
            "mondo_contrari.opposite_explored",
            {"category": category.value},
            idempotency_key=f"contrari:{session_id}:{category.value}",
        )

    def all_opposites_completed(self, session_id: str, payload: dict[str, int]) -> None:
        emit_activity_event(
            "mondo_contrari.all_opposites_completed",
            payload,
            idempotency_key=f"contrari:{session_id}:all",
        )


__all__ = [
    "ContrariProgress",
    "EventPort",
    "GreiaContrariEvents",
    "GreiaContrariProgress",
    "ProgressPort",
    "STORAGE_KEY",
]
