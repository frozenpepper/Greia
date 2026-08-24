"""Greia persistence and event adapters for Luci di Momo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .firefly_model import AttemptSummary, HISTORY_LIMIT
else:
    from firefly_model import AttemptSummary, HISTORY_LIMIT


STORAGE_KEY = "luci_di_momo.progress.v1"


@dataclass(frozen=True, slots=True)
class FireflyProgress:
    level: int = 1
    history: tuple[AttemptSummary, ...] = ()


class ProgressPort(Protocol):
    def load(self) -> FireflyProgress: ...
    def save(self, level: int, history: Sequence[AttemptSummary]) -> None: ...


class EventPort(Protocol):
    def garden_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


class GreiaFireflyProgress:
    """Map bounded Activity progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def load(self) -> FireflyProgress:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return FireflyProgress()
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            return FireflyProgress()

        level = raw.get("level", 1)
        if not isinstance(level, int) or not 1 <= level <= 4:
            level = 1

        parsed: list[AttemptSummary] = []
        history = raw.get("history", [])
        if isinstance(history, list):
            for item in history[-HISTORY_LIMIT:]:
                if not isinstance(item, dict):
                    continue
                first = item.get("first_attempt_success")
                hints = item.get("hints_used")
                replay = item.get("used_replay")
                if (
                    isinstance(first, bool)
                    and isinstance(hints, int)
                    and 0 <= hints <= 32
                    and isinstance(replay, bool)
                ):
                    parsed.append(AttemptSummary(first, hints, replay))
        return FireflyProgress(level, tuple(parsed))

    def save(self, level: int, history: Sequence[AttemptSummary]) -> None:
        bounded = tuple(history[-HISTORY_LIMIT:])
        payload = {
            "schema_version": 1,
            "level": max(1, min(4, int(level))),
            "history": [
                {
                    "first_attempt_success": item.first_attempt_success,
                    "hints_used": item.hints_used,
                    "used_replay": item.used_replay,
                }
                for item in bounded
            ],
        }
        try:
            self._storage.kv_set(STORAGE_KEY, payload)
        except Exception:
            return


class GreiaFireflyEvents:
    """Publish only the one completion fact declared by the manifest."""

    def garden_completed(self, session_id: str, payload: dict[str, int]) -> None:
        emit_activity_event(
            "firefly.garden_completed",
            payload,
            idempotency_key=f"luci-di-momo:{session_id}",
        )
