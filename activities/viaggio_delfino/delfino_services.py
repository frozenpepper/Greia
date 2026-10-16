"""Greia platform seams for Il Viaggio del Delfino.

Thin, injectable wrappers around Greia storage and the platform event
pipeline so the app layer stays testable with stubs. The Activity reports
factual events only; Greia owns Stars, badges and achievement truth.

Event emission is a validated synchronous IPC round-trip whose broker side
commits durable state before replying. On low-resource reference hardware
that commit can take hundreds of milliseconds, so emission runs on one
bounded worker thread: ordering is preserved, the frame loop never blocks,
and a stalled broker can never grow the queue without bound.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import queue
import threading
import time
from typing import Any

from greia_platform.activity_api import emit_activity_event, get_storage

STORAGE_KEY = "viaggio_delfino.progress.v1"

#: Durable fields are small non-negative counters; anything else in stored
#: payloads is ignored on load so a corrupt write degrades to defaults.
_MAX_COUNTER = 9_999_999

#: Payload schema written today. Schema 1 (the old single three-chapter
#: journey) stored only ``total_pearls`` and ``best_journey_score``; it is
#: migrated forward on load and never loses those counters.
PROGRESS_VERSION = 2

#: Sentinel for "resolve Greia storage lazily"; an explicit ``None`` means the
#: caller deliberately runs without storage (tests/offline fallback).
_UNSET = object()


@dataclass(frozen=True, slots=True)
class JourneyRecord:
    """What the child achieved on one journey (bounded counters)."""

    completions: int = 0
    best_pearls: int = 0
    best_stars: int = 0

    @property
    def done(self) -> bool:
        return self.completions > 0


@dataclass(frozen=True, slots=True)
class DelfinoProgress:
    """Durable, profile-scoped progress of the Dolphin's Journey."""

    total_pearls: int = 0
    best_journey_score: int = 0
    journeys: Mapping[str, JourneyRecord] = field(default_factory=dict)

    def record(self, journey_id: str) -> JourneyRecord:
        return self.journeys.get(journey_id, JourneyRecord())

    def unlocked(self, order: tuple[str, ...]) -> tuple[str, ...]:
        """Journeys open to the child: the first, plus one after each done one."""

        opened: list[str] = []
        for index, journey_id in enumerate(order):
            if index == 0 or self.record(order[index - 1]).done:
                opened.append(journey_id)
            else:
                break
        return tuple(opened)

    def with_result(self, journey_id: str, pearls: int, stars: int) -> "DelfinoProgress":
        """Return progress updated with one finished journey."""

        old = self.record(journey_id)
        updated = dict(self.journeys)
        updated[journey_id] = JourneyRecord(
            completions=min(_MAX_COUNTER, old.completions + 1),
            best_pearls=max(old.best_pearls, _bounded_int(pearls)),
            best_stars=max(old.best_stars, max(0, min(3, int(stars)))),
        )
        return DelfinoProgress(
            total_pearls=min(_MAX_COUNTER, self.total_pearls + _bounded_int(pearls)),
            best_journey_score=max(self.best_journey_score, _bounded_int(pearls)),
            journeys=updated,
        )


class GreiaDelfinoStorage:
    """Bounded durable progress: pearls, best score and per-journey records."""

    def __init__(
        self,
        key: str = STORAGE_KEY,
        storage: Any | None = _UNSET,
        journey_ids: tuple[str, ...] = (),
    ) -> None:
        self._key = key
        self._storage = _safe_storage() if storage is _UNSET else storage
        self._journey_ids = tuple(journey_ids)

    @property
    def available(self) -> bool:
        return self._storage is not None

    def load(self) -> DelfinoProgress:
        raw: Any = None
        if self._storage is not None:
            try:
                raw = self._storage.kv_get(self._key)
            except Exception:
                raw = None
        if not isinstance(raw, dict):
            return DelfinoProgress()
        total = _bounded_int(raw.get("total_pearls"))
        best = _bounded_int(raw.get("best_journey_score"))
        journeys: dict[str, JourneyRecord] = {}
        stored = raw.get("journeys")
        if isinstance(stored, dict):
            for journey_id, entry in stored.items():
                if not isinstance(entry, dict) or not isinstance(journey_id, str):
                    continue
                if self._journey_ids and journey_id not in self._journey_ids:
                    continue
                journeys[journey_id] = JourneyRecord(
                    completions=_bounded_int(entry.get("completions")),
                    best_pearls=_bounded_int(entry.get("best_pearls")),
                    best_stars=max(0, min(3, _bounded_int(entry.get("best_stars")))),
                )
        elif best > 0 and self._journey_ids:
            # Schema 1: the child had already swum the whole old journey, so
            # the first course counts as done and the next one is open.
            journeys[self._journey_ids[0]] = JourneyRecord(completions=1, best_pearls=0, best_stars=1)
        return DelfinoProgress(total, best, journeys)

    def save(self, progress: DelfinoProgress) -> bool:
        if self._storage is None:
            return False
        try:
            self._storage.kv_set(
                self._key,
                {
                    "version": PROGRESS_VERSION,
                    "total_pearls": max(0, min(_MAX_COUNTER, int(progress.total_pearls))),
                    "best_journey_score": max(0, min(_MAX_COUNTER, int(progress.best_journey_score))),
                    "journeys": {
                        journey_id: {
                            "completions": record.completions,
                            "best_pearls": record.best_pearls,
                            "best_stars": record.best_stars,
                        }
                        for journey_id, record in progress.journeys.items()
                    },
                    "timestamp": time.time(),
                },
            )
            return True
        except Exception:
            return False

    # Compatibility helpers kept for older callers/tools.
    def load_progress(self) -> dict[str, int]:
        progress = self.load()
        return {"total_pearls": progress.total_pearls, "best_journey_score": progress.best_journey_score}


class GreiaDelfinoEvents:
    """Emit exactly the manifest-declared semantic facts, off the frame thread.

    One daemon worker drains a bounded FIFO so celebration moments (star
    pickups, chapter banners) never stall on broker commits. Facts are
    best-effort under a dead broker: an overflow drops the newest item and
    counts it rather than blocking gameplay or growing memory.
    """

    _CLOSE = object()

    def __init__(self, queue_depth: int = 16, emitter: Any = None) -> None:
        self._emitter = emitter if emitter is not None else emit_activity_event
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=max(4, queue_depth))
        self._dropped = 0
        self._idle = threading.Event()
        self._idle.set()
        self._worker = threading.Thread(
            target=self._drain, name="delfino-event-worker", daemon=True
        )
        self._worker.start()

    # ------------------------------------------------------------------ api

    def chapter_completed(self, chapter_number: int) -> None:
        """One journey (course number ``chapter_number``) reached its finish."""

        self._submit(
            "dolphin.chapter_completed",
            {"chapter_number": chapter_number},
            f"dolphin-chapter-{chapter_number}-{time.time_ns()}",
        )

    def fact_opened(self, fact_id: str) -> None:
        self._submit(
            "dolphin.fact_opened",
            {"fact_id": fact_id},
            f"dolphin-fact-{fact_id}-{time.time_ns()}",
        )

    def journey_score(self, score: int) -> None:
        self._submit("dolphin.journey_score", {}, f"dolphin-journey-score-{time.time_ns()}", score)

    def flush(self, timeout: float = 2.0) -> bool:
        """Wait until everything submitted so far has been handed to Greia."""

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._queue.empty() and self._idle.is_set():
                return True
            time.sleep(0.005)
        return self._queue.empty() and self._idle.is_set()

    def close(self) -> None:
        """Stop the worker after draining whatever was already submitted."""

        try:
            self._queue.put(self._CLOSE, timeout=1.0)
        except queue.Full:
            pass
        self._worker.join(timeout=2.0)
        self._idle.set()

    @property
    def dropped_count(self) -> int:
        return self._dropped

    # --------------------------------------------------------------- worker

    def _submit(
        self,
        event_id: str,
        payload: dict[str, object],
        idempotency_key: str,
        score: float | int | None = None,
    ) -> None:
        self._idle.clear()
        try:
            self._queue.put_nowait((event_id, payload, idempotency_key, score))
        except queue.Full:
            self._dropped += 1
            if self._queue.empty():
                self._idle.set()

    def _drain(self) -> None:
        while True:
            item = self._queue.get()
            if item is self._CLOSE:
                return
            event_id, payload, idempotency_key, score = item
            try:
                self._emitter(
                    event_id,
                    payload,
                    idempotency_key=idempotency_key,
                    score=score,
                )
            except Exception:
                pass  # facts are fail-soft; gameplay never depends on delivery
            if self._queue.empty():
                self._idle.set()


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
