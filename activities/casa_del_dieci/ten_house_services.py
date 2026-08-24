"""Greia persistence and event adapters for La Casa del Dieci."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .ten_house_model import AttemptSummary, HISTORY_LIMIT
else:
    from ten_house_model import AttemptSummary, HISTORY_LIMIT


STORAGE_KEY = "casa_del_dieci.progress.v1"


@dataclass(frozen=True, slots=True)
class TenHouseProgress:
    level: int = 1
    history: tuple[AttemptSummary, ...] = ()


class ProgressPort(Protocol):
    def load(self) -> TenHouseProgress: ...
    def save(self, level: int, history: Sequence[AttemptSummary]) -> None: ...


class EventPort(Protocol):
    def room_completed(self, session_id: str, payload: dict[str, int]) -> None: ...
    def house_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


class GreiaTenHouseProgress:
    """Map bounded Activity progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def load(self) -> TenHouseProgress:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return TenHouseProgress()
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            return TenHouseProgress()

        level = raw.get("level", 1)
        if not isinstance(level, int) or not 1 <= level <= 5:
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
                if (
                    isinstance(first, bool)
                    and isinstance(hints, int)
                    and 0 <= hints <= 32
                    and isinstance(retry, bool)
                ):
                    parsed.append(AttemptSummary(first, hints, retry))
        return TenHouseProgress(level, tuple(parsed))

    def save(self, level: int, history: Sequence[AttemptSummary]) -> None:
        bounded = tuple(history[-HISTORY_LIMIT:])
        payload = {
            "schema_version": 1,
            "level": max(1, min(5, int(level))),
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


class GreiaTenHouseEvents:
    """Publish milestone and completion facts declared by the manifest."""

    def room_completed(self, session_id: str, payload: dict[str, int]) -> None:
        index = payload.get("challenge_index", 1)
        emit_activity_event(
            "ten_house.room_completed",
            payload,
            idempotency_key=f"casa-del-dieci:{session_id}:c{index}",
        )

    def house_completed(self, session_id: str, payload: dict[str, int]) -> None:
        emit_activity_event(
            "ten_house.house_completed",
            payload,
            idempotency_key=f"casa-del-dieci:{session_id}",
        )
