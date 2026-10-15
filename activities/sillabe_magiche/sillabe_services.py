"""Greia persistence and event adapters for Leo's Syllable Train.

Saves stay under the original key. Schema 1 (the old free-play modes) stored
only ``score`` / ``stars`` / ``words_completed``; those counters are carried
forward unchanged into schema 2, which adds the train stage and a bounded
attempt history. Malformed data never raises and never erases counters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .sillabe_content import STORAGE_KEY
    from .sillabe_model import HISTORY_LIMIT, MAX_LEVEL, MIN_LEVEL, AttemptSummary
else:
    from sillabe_content import STORAGE_KEY
    from sillabe_model import HISTORY_LIMIT, MAX_LEVEL, MIN_LEVEL, AttemptSummary


SCHEMA_VERSION = 2
_COUNTERS = ("score", "stars", "words_completed")
_COUNTER_LIMIT = 10_000_000


@dataclass(frozen=True, slots=True)
class TrainProgress:
    level: int = 1
    history: tuple[AttemptSummary, ...] = ()
    score: int = 0
    stars: int = 0
    words_completed: int = 0


class ProgressPort(Protocol):
    def load(self) -> TrainProgress: ...
    def save(self, level: int, history: Sequence[AttemptSummary], *, words: int, stars: int) -> None: ...


class EventPort(Protocol):
    def word_completed(self, session_id: str, payload: dict[str, int]) -> None: ...
    def train_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


def _counter(raw: dict, key: str) -> int:
    value = raw.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, min(_COUNTER_LIMIT, value))


class GreiaTrainProgress:
    """Map bounded train progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()
        self._loaded = TrainProgress()

    def load(self) -> TrainProgress:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            raw = None
        if not isinstance(raw, dict):
            self._loaded = TrainProgress()
            return self._loaded
        counters = {key: _counter(raw, key) for key in _COUNTERS}
        level = raw.get("level", MIN_LEVEL) if raw.get("schema_version") == SCHEMA_VERSION else MIN_LEVEL
        if isinstance(level, bool) or not isinstance(level, int) or not MIN_LEVEL <= level <= MAX_LEVEL:
            level = MIN_LEVEL
        parsed: list[AttemptSummary] = []
        history = raw.get("history", []) if raw.get("schema_version") == SCHEMA_VERSION else []
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
        self._loaded = TrainProgress(level, tuple(parsed), **counters)
        return self._loaded

    def save(self, level: int, history: Sequence[AttemptSummary], *, words: int, stars: int) -> None:
        """Persist the stage + history and add this round's counters to the totals."""

        base = self._loaded
        updated = TrainProgress(
            max(MIN_LEVEL, min(MAX_LEVEL, int(level))),
            tuple(history[-HISTORY_LIMIT:]),
            score=min(_COUNTER_LIMIT, base.score + 10 * max(0, words)),
            stars=min(_COUNTER_LIMIT, base.stars + max(0, stars)),
            words_completed=min(_COUNTER_LIMIT, base.words_completed + max(0, words)),
        )
        payload = {
            "schema_version": SCHEMA_VERSION,
            "level": updated.level,
            "history": [
                {
                    "first_attempt_success": item.first_attempt_success,
                    "hints_used": item.hints_used,
                    "used_retry": item.used_retry,
                }
                for item in updated.history
            ],
            "score": updated.score,
            "stars": updated.stars,
            "words_completed": updated.words_completed,
        }
        try:
            self._storage.kv_set(STORAGE_KEY, payload)
        except Exception:
            return
        self._loaded = updated


class GreiaTrainEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def word_completed(self, session_id: str, payload: dict[str, int]) -> None:
        index = payload.get("word_index", 1)
        try:
            emit_activity_event(
                "syllable.word_completed",
                payload,
                idempotency_key=f"sillabe-magiche:{session_id}:w{index}",
            )
        except Exception:
            return

    def train_completed(self, session_id: str, payload: dict[str, int]) -> None:
        try:
            emit_activity_event(
                "syllable.train_completed",
                payload,
                idempotency_key=f"sillabe-magiche:{session_id}",
            )
        except Exception:
            return


__all__ = ["EventPort", "GreiaTrainEvents", "GreiaTrainProgress", "ProgressPort", "SCHEMA_VERSION", "TrainProgress"]
