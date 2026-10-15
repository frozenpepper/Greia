"""Greia persistence and event adapters for Treno Numeri.

Storage keeps the original key (``treno_numeri.progress.v2``) so existing child
saves load. The first release stored only ``{"stars": n}`` (one star per
station); it migrates forward to schema 2 on first load: the star total becomes
``stations_completed`` and children who already travelled a lot resume on the
second rung instead of the very first one.
"""

from __future__ import annotations

from typing import Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .treno_content import STORAGE_KEY
    from .treno_model import MIN_STAGE, StationSummary, TrainProgress, clamp_stage
else:
    from treno_content import STORAGE_KEY
    from treno_model import MIN_STAGE, StationSummary, TrainProgress, clamp_stage

SCHEMA_VERSION: Final[int] = 2
_COUNTER_LIMIT: Final[int] = 10_000_000
_LEGACY_PROMOTE_AFTER: Final[int] = 10  # stations travelled under schema 1


def _counter(raw: dict, key: str, default: int = 0) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(0, min(_COUNTER_LIMIT, int(value)))


def _streak(raw: dict, key: str) -> int:
    return min(_counter(raw, key), 3)


def progress_from_payload(raw: object) -> TrainProgress:
    """Parse schema 2, migrate schema 1, and fall back safely on anything else."""

    if not isinstance(raw, dict):
        return TrainProgress()
    if raw.get("schema_version") == SCHEMA_VERSION:
        return TrainProgress(
            stage=clamp_stage(raw.get("stage", MIN_STAGE)),
            clean_streak=_streak(raw, "clean_streak"),
            struggle_streak=_streak(raw, "struggle_streak"),
            stations_completed=_counter(raw, "stations_completed"),
            journeys_completed=_counter(raw, "journeys_completed"),
            highest_order=min(10, _counter(raw, "highest_order")),
        )
    # Schema 1: {"stars": n}, one star per finished station.
    stations = _counter(raw, "stars")
    return TrainProgress(
        stage=2 if stations >= _LEGACY_PROMOTE_AFTER else MIN_STAGE,
        stations_completed=stations,
        journeys_completed=stations // 5,
    )


def progress_payload(progress: TrainProgress) -> dict[str, int]:
    stations = min(_COUNTER_LIMIT, max(0, progress.stations_completed))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": clamp_stage(progress.stage),
        "clean_streak": min(3, max(0, progress.clean_streak)),
        "struggle_streak": min(3, max(0, progress.struggle_streak)),
        "stations_completed": stations,
        "journeys_completed": min(_COUNTER_LIMIT, max(0, progress.journeys_completed)),
        "highest_order": min(10, max(0, progress.highest_order)),
        # Kept for any older reader of this key (same meaning as schema 1).
        "stars": stations,
    }


class ProgressPort(Protocol):
    def load(self) -> TrainProgress: ...
    def save(self, progress: TrainProgress) -> None: ...


class EventPort(Protocol):
    def station_completed(self, journey_id: str, index: int, summary: StationSummary) -> None: ...
    def journey_completed(self, journey_id: str, stations: int, stage: int) -> None: ...


class GreiaTrainProgress:
    """Profile-scoped Greia Storage adapter (never raises into the game loop)."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _resolve(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> TrainProgress:
        try:
            storage = self._resolve()
            raw = storage.kv_get(STORAGE_KEY, {}) if storage is not None else {}
        except Exception:
            return TrainProgress()
        return progress_from_payload(raw)

    def save(self, progress: TrainProgress) -> None:
        try:
            storage = self._resolve()
            if storage is not None:
                storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaTrainEvents:
    """Publish the manifest-declared milestone/completion facts.

    Keys are scoped per journey so a replayed journey is never deduplicated
    against the previous one.
    """

    def station_completed(self, journey_id: str, index: int, summary: StationSummary) -> None:
        self._emit(
            "train.station_completed",
            {"order": summary.order, "stage": summary.stage, "first_try": summary.mistakes == 0},
            f"train:{journey_id}:station:{index}",
        )

    def journey_completed(self, journey_id: str, stations: int, stage: int) -> None:
        self._emit(
            "train.journey_completed",
            {"stations": stations, "stage": stage},
            f"train:{journey_id}:completed",
        )

    @staticmethod
    def _emit(event_id: str, payload: dict, key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaTrainEvents",
    "GreiaTrainProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "progress_from_payload",
    "progress_payload",
]
