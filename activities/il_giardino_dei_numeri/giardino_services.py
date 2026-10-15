"""Greia persistence and event adapters for Il Giardino dei Numeri.

Storage keeps the original key so existing child saves load. Schema 1 (the
pre-rework counters) migrates forward to schema 2 on first load: totals are
kept and the old automatic difficulty maps onto the new adaptive stage.
"""

from __future__ import annotations

from typing import Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .giardino_model import GardenProgress, MAX_STAGE, MIN_STAGE, RoundSummary, clamp_stage
else:
    from giardino_model import GardenProgress, MAX_STAGE, MIN_STAGE, RoundSummary, clamp_stage

STORAGE_KEY: Final[str] = "giardino_dei_numeri.progress.v1"
SCHEMA_VERSION: Final[int] = 2
_COUNTER_LIMIT: Final[int] = 10_000_000


def _counter(raw: dict, key: str, default: int = 0) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(0, min(_COUNTER_LIMIT, int(value)))


def _streak(raw: dict, key: str) -> int:
    return min(_counter(raw, key), 3)


def progress_from_payload(raw: object) -> GardenProgress:
    """Parse schema 2, migrate schema 1, and fall back safely on anything else."""

    if not isinstance(raw, dict):
        return GardenProgress()
    baskets = _counter(raw, "baskets_filled")
    progress = GardenProgress(
        total_counted=_counter(raw, "total_counted"),
        baskets_filled=baskets,
        sessions_completed=_counter(raw, "sessions_completed"),
        highest_count=min(10, _counter(raw, "highest_count")),
    )
    if raw.get("schema_version") == SCHEMA_VERSION:
        progress.stage = clamp_stage(raw.get("stage", MIN_STAGE))
        progress.clean_streak = _streak(raw, "clean_streak")
        progress.struggle_streak = _streak(raw, "struggle_streak")
    else:
        # Schema 1 raised difficulty automatically every two baskets
        # (1-3, 2-4, 3-5 objects). Resume children who reached the 2-4 band at
        # stage 2; nobody is dropped straight into the three-card stage.
        old_difficulty = min(3, 1 + baskets // 2)
        progress.stage = min(MAX_STAGE, 2 if old_difficulty >= 2 else 1)
    return progress


def progress_payload(progress: GardenProgress) -> dict[str, int]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": clamp_stage(progress.stage),
        "clean_streak": min(3, max(0, progress.clean_streak)),
        "struggle_streak": min(3, max(0, progress.struggle_streak)),
        "total_counted": min(_COUNTER_LIMIT, max(0, progress.total_counted)),
        "baskets_filled": min(_COUNTER_LIMIT, max(0, progress.baskets_filled)),
        "sessions_completed": min(_COUNTER_LIMIT, max(0, progress.sessions_completed)),
        "highest_count": min(10, max(0, progress.highest_count)),
    }


class ProgressPort(Protocol):
    def load(self) -> GardenProgress: ...
    def save(self, progress: GardenProgress) -> None: ...


class EventPort(Protocol):
    def set_counted(self, session_id: str, index: int, summary: RoundSummary) -> None: ...
    def basket_filled(self, session_id: str, rounds: int, stage: int) -> None: ...


class GreiaGardenProgress:
    """Profile-scoped Greia Storage adapter (never raises into the game loop)."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _resolve(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> GardenProgress:
        try:
            storage = self._resolve()
            raw = storage.kv_get(STORAGE_KEY, {}) if storage is not None else {}
        except Exception:
            return GardenProgress()
        return progress_from_payload(raw)

    def save(self, progress: GardenProgress) -> None:
        try:
            storage = self._resolve()
            if storage is not None:
                storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaGardenEvents:
    """Publish the manifest-declared milestone/completion facts."""

    def set_counted(self, session_id: str, index: int, summary: RoundSummary) -> None:
        self._emit(
            "garden.set_counted",
            {
                "count": summary.count,
                "stage": summary.stage,
                "first_try": summary.mistakes == 0,
            },
            f"giardino:{session_id}:r{index}",
        )

    def basket_filled(self, session_id: str, rounds: int, stage: int) -> None:
        self._emit("garden.basket_filled", {"rounds": rounds, "stage": stage}, f"giardino:{session_id}")

    @staticmethod
    def _emit(event_id: str, payload: dict, key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaGardenEvents",
    "GreiaGardenProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "progress_from_payload",
    "progress_payload",
]
