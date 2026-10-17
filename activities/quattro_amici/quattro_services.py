"""Greia persistence and event adapters for Quattro Amici in Fila.

Progress is tiny and profile-scoped: the current ladder stage, the
Leo-won-matches streak and the last chosen mode. A missing, foreign or
damaged record (or a refused write on a full disk) falls back to defaults
without failing the game. Facts are emitted off the frame thread by one
bounded worker (see ``GreiaQuattroEvents``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import queue
import threading
import time
from typing import Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .quattro_content import FIRST_STAGE, LAST_STAGE, GameMode
    from .quattro_model import Ladder
else:
    from quattro_content import FIRST_STAGE, LAST_STAGE, GameMode
    from quattro_model import Ladder

STORAGE_KEY = "quattro_amici.progress.v1"
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class QuattroProgress:
    ladder: Ladder = Ladder()
    mode: GameMode = GameMode.VS_CPU


class ProgressPort(Protocol):
    def load(self) -> QuattroProgress: ...
    def save(self, progress: QuattroProgress) -> None: ...


class EventPort(Protocol):
    def emit(self, event_id: str, key: str, payload: dict[str, object]) -> None: ...


class GreiaQuattroProgress:
    """Map the adaptive ladder onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage
        self._resolved = storage is not None

    def _store(self):
        if not self._resolved:
            self._resolved = True
            try:
                self._storage = get_storage()
            except Exception:
                self._storage = None
        return self._storage

    def load(self) -> QuattroProgress:
        storage = self._store()
        if storage is None:
            return QuattroProgress()
        try:
            raw = storage.kv_get(STORAGE_KEY)
        except Exception:
            return QuattroProgress()
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            return QuattroProgress()
        stage = raw.get("stage")
        streak = raw.get("loss_streak", 0)
        if not isinstance(stage, int) or not FIRST_STAGE <= stage <= LAST_STAGE:
            stage = FIRST_STAGE
        if not isinstance(streak, int) or not 0 <= streak <= 1:
            streak = 0
        try:
            mode = GameMode(raw.get("mode", GameMode.VS_CPU.value))
        except ValueError:
            mode = GameMode.VS_CPU
        return QuattroProgress(Ladder(stage, streak), mode)

    def save(self, progress: QuattroProgress) -> None:
        storage = self._store()
        if storage is None:
            return
        payload = {
            "schema_version": SCHEMA_VERSION,
            "stage": max(FIRST_STAGE, min(LAST_STAGE, int(progress.ladder.stage))),
            "loss_streak": max(0, min(1, int(progress.ladder.loss_streak))),
            "mode": progress.mode.value,
        }
        try:
            storage.kv_set(STORAGE_KEY, payload)
        except Exception:
            return


class GreiaQuattroEvents:
    """Publish the milestone/completion facts declared by the manifest, off the frame thread.

    An emit is a synchronous broker round trip whose broker side commits
    durable state before replying. On the Acer reference (2026-10-17) that
    held the loop 120-145 ms on every child drop, so the falling disc froze
    for three frames right after the tap. One daemon worker drains a bounded
    FIFO instead: order is kept, the loop never waits, and a stalled broker
    drops (and counts) the newest fact rather than growing the queue.
    """

    _CLOSE = object()

    def __init__(self, queue_depth: int = 16, emitter: Callable[..., object] | None = None) -> None:
        self._emitter = emitter if emitter is not None else emit_activity_event
        self._queue: queue.Queue[object] = queue.Queue(maxsize=max(4, queue_depth))
        self._dropped = 0
        self._idle = threading.Event()
        self._idle.set()
        self._worker = threading.Thread(target=self._drain, name="quattro-event-worker", daemon=True)
        self._worker.start()

    def emit(self, event_id: str, key: str, payload: dict[str, object]) -> None:
        self._idle.clear()
        try:
            self._queue.put_nowait((event_id, key, payload))
        except queue.Full:
            self._dropped += 1
            if self._queue.empty():
                self._idle.set()

    def flush(self, timeout: float = 2.0) -> bool:
        """Wait until every fact submitted so far has been handed to Greia."""

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._queue.empty() and self._idle.is_set():
                return True
            time.sleep(0.005)
        return self._queue.empty() and self._idle.is_set()

    def close(self, timeout: float = 1.0) -> None:
        """Hand over what is queued (bounded by ``timeout``), then stop the worker."""

        try:
            self._queue.put(self._CLOSE, timeout=timeout)
        except queue.Full:
            return
        self._worker.join(timeout=timeout)

    @property
    def dropped_count(self) -> int:
        return self._dropped

    def _drain(self) -> None:
        while True:
            item = self._queue.get()
            if item is self._CLOSE:
                self._idle.set()
                return
            event_id, key, payload = item  # type: ignore[misc]
            try:
                self._emitter(event_id, idempotency_key=key, payload=payload)
            except Exception:
                pass  # facts are fail-soft; play never depends on delivery
            if self._queue.empty():
                self._idle.set()


__all__ = [
    "EventPort",
    "GreiaQuattroEvents",
    "GreiaQuattroProgress",
    "ProgressPort",
    "QuattroProgress",
    "STORAGE_KEY",
]
