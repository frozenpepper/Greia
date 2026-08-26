"""Greia platform seams for Il Viaggio del Delfino.

Thin, injectable wrappers around Greia storage and the platform event
pipeline so the app layer stays testable with stubs. The Activity reports
factual events only; Greia owns Stars, badges and achievement truth.
"""

from __future__ import annotations

import time
from typing import Any

from greia_platform.activity_api import emit_activity_event, get_storage

STORAGE_KEY = "viaggio_delfino.progress.v1"

#: Durable fields are small non-negative counters; anything else in stored
#: payloads is ignored on load so a corrupt write degrades to defaults.
_MAX_COUNTER = 9_999_999

#: Sentinel for "resolve Greia storage lazily"; an explicit ``None`` means the
#: caller deliberately runs without storage (tests/offline fallback).
_UNSET = object()


class GreiaDelfinoStorage:
    """Bounded durable progress: lifetime pearls and best journey score."""

    def __init__(self, key: str = STORAGE_KEY, storage: Any | None = _UNSET) -> None:
        self._key = key
        self._storage = _safe_storage() if storage is _UNSET else storage

    @property
    def available(self) -> bool:
        return self._storage is not None

    def load_progress(self) -> dict[str, int]:
        raw: Any = None
        if self._storage is not None:
            try:
                raw = self._storage.kv_get(self._key)
            except Exception:
                raw = None
        if not isinstance(raw, dict):
            return {"total_pearls": 0, "best_journey_score": 0}
        return {
            "total_pearls": _bounded_int(raw.get("total_pearls")),
            "best_journey_score": _bounded_int(raw.get("best_journey_score")),
        }

    def save_progress(self, total_pearls: int, best_journey_score: int) -> bool:
        if self._storage is None:
            return False
        try:
            self._storage.kv_set(
                self._key,
                {
                    "total_pearls": max(0, min(_MAX_COUNTER, int(total_pearls))),
                    "best_journey_score": max(0, min(_MAX_COUNTER, int(best_journey_score))),
                    "timestamp": time.time(),
                },
            )
            return True
        except Exception:
            return False


class GreiaDelfinoEvents:
    """Emit exactly the manifest-declared semantic facts."""

    def chapter_completed(self, chapter_number: int) -> None:
        emit_activity_event(
            "dolphin.chapter_completed",
            {"chapter_number": chapter_number},
            idempotency_key=f"dolphin-chapter-{chapter_number}-{time.time_ns()}",
        )

    def fact_opened(self, fact_id: str) -> None:
        emit_activity_event(
            "dolphin.fact_opened",
            {"fact_id": fact_id},
            idempotency_key=f"dolphin-fact-{fact_id}-{time.time_ns()}",
        )

    def journey_score(self, score: int) -> None:
        emit_activity_event(
            "dolphin.journey_score",
            {},
            idempotency_key=f"dolphin-journey-score-{time.time_ns()}",
            score=max(0, int(score)),
        )


def _safe_storage() -> Any:
    try:
        return get_storage()
    except Exception:
        return None


def _bounded_int(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(0, min(_MAX_COUNTER, value))
