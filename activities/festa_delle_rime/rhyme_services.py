"""Greia persistence and event adapters for Festa delle Rime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .rhyme_model import AttemptSummary, HISTORY_LIMIT
else:
    from rhyme_model import AttemptSummary, HISTORY_LIMIT


STORAGE_KEY = "festa_delle_rime.progress.v1"


@dataclass(frozen=True, slots=True)
class RhymeProgress:
    level: int = 1
    history: tuple[AttemptSummary, ...] = ()


class ProgressPort(Protocol):
    def load(self) -> RhymeProgress: ...
    def save(self, level: int, history: Sequence[AttemptSummary]) -> None: ...


class EventPort(Protocol):
    def match_completed(self, session_id: str, payload: dict[str, int]) -> None: ...
    def festival_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


class GreiaRhymeProgress:
    """Map bounded Activity progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def load(self) -> RhymeProgress:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return RhymeProgress()
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            return RhymeProgress()

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
                retry = item.get("used_retry")
                if (
                    isinstance(first, bool)
                    and isinstance(hints, int)
                    and 0 <= hints <= 32
                    and isinstance(retry, bool)
                ):
                    parsed.append(AttemptSummary(first, hints, retry))
        return RhymeProgress(level, tuple(parsed))

    def save(self, level: int, history: Sequence[AttemptSummary]) -> None:
        bounded = tuple(history[-HISTORY_LIMIT:])
        payload = {
            "schema_version": 1,
            "level": max(1, min(4, int(level))),
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


class GreiaRhymeEvents:
    """Publish milestone and completion facts declared by the manifest."""

    def match_completed(self, session_id: str, payload: dict[str, int]) -> None:
        index = payload.get("challenge_index", 1)
        emit_activity_event(
            "rhyme.match_completed",
            payload,
            idempotency_key=f"festa-delle-rime:{session_id}:m{index}",
        )

    def festival_completed(self, session_id: str, payload: dict[str, int]) -> None:
        emit_activity_event(
            "rhyme.festival_completed",
            payload,
            idempotency_key=f"festa-delle-rime:{session_id}",
        )
