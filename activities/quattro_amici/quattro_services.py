"""Greia persistence and event adapters for Quattro Amici in Fila.

Progress is tiny and profile-scoped: the current ladder stage, the
Leo-won-matches streak and the last chosen mode. A missing, foreign or
damaged record (or a refused write on a full disk) falls back to defaults
without failing the game.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    """Publish the milestone/completion facts declared by the manifest."""

    def emit(self, event_id: str, key: str, payload: dict[str, object]) -> None:
        try:
            emit_activity_event(event_id, idempotency_key=key, payload=payload)
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaQuattroEvents",
    "GreiaQuattroProgress",
    "ProgressPort",
    "QuattroProgress",
    "STORAGE_KEY",
]
