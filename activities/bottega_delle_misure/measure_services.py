"""Greia persistence and event adapters for La Bottega delle Misure.

Storage keeps the original key (``bottega_delle_misure.progress.v1``) so
existing child saves load. Schema 1 stored ``{"level": 1..5, "history": [...]}``
from the first release, whose levels were compare / order / numbered-blocks /
the same numbered-blocks again / mixed. It migrates forward to schema 2 on
first load: level 1 stays on direct comparison, 2 (ordering lengths) resumes
on balance + close comparisons, 3 and the duplicated 4 resume on measuring
with blocks (reading numbered blocks never practised laying units), and 5
resumes on measure-and-compare.
"""

from __future__ import annotations

from typing import Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .measure_content import STORAGE_KEY
    from .measure_model import JobSummary, MIN_STAGE, WorkshopProgress, clamp_stage
else:
    from measure_content import STORAGE_KEY
    from measure_model import JobSummary, MIN_STAGE, WorkshopProgress, clamp_stage

SCHEMA_VERSION: Final[int] = 2
_COUNTER_LIMIT: Final[int] = 10_000_000
_LEGACY_STAGE: Final[dict[int, int]] = {1: 1, 2: 2, 3: 3, 4: 3, 5: 4}


def _counter(raw: dict, key: str) -> int:
    value = raw.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(_COUNTER_LIMIT, int(value)))


def _streak(raw: dict, key: str) -> int:
    return min(_counter(raw, key), 3)


def progress_from_payload(raw: object) -> WorkshopProgress:
    """Parse schema 2, migrate schema 1, and fall back safely on anything else."""

    if not isinstance(raw, dict):
        return WorkshopProgress()
    version = raw.get("schema_version")
    if version == SCHEMA_VERSION:
        return WorkshopProgress(
            stage=clamp_stage(raw.get("stage", MIN_STAGE)),
            clean_streak=_streak(raw, "clean_streak"),
            struggle_streak=_streak(raw, "struggle_streak"),
            jobs_completed=_counter(raw, "jobs_completed"),
            deliveries_completed=_counter(raw, "deliveries_completed"),
        )
    if version == 1:
        level = raw.get("level", MIN_STAGE)
        if isinstance(level, bool) or not isinstance(level, int):
            level = MIN_STAGE
        history = raw.get("history")
        jobs = len(history) if isinstance(history, list) else 0
        return WorkshopProgress(stage=_LEGACY_STAGE.get(level, MIN_STAGE), jobs_completed=min(jobs, 8))
    return WorkshopProgress()


def progress_payload(progress: WorkshopProgress) -> dict[str, int]:
    stage = clamp_stage(progress.stage)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "clean_streak": min(3, max(0, progress.clean_streak)),
        "struggle_streak": min(3, max(0, progress.struggle_streak)),
        "jobs_completed": min(_COUNTER_LIMIT, max(0, progress.jobs_completed)),
        "deliveries_completed": min(_COUNTER_LIMIT, max(0, progress.deliveries_completed)),
        # Same meaning as schema 1's level for any older reader of this key.
        "level": stage,
    }


class ProgressPort(Protocol):
    def load(self) -> WorkshopProgress: ...
    def save(self, progress: WorkshopProgress) -> None: ...


class EventPort(Protocol):
    def parcel_completed(self, delivery_id: str, index: int, summary: JobSummary) -> None: ...
    def delivery_completed(self, delivery_id: str, jobs: int, stage: int) -> None: ...


class GreiaMeasureProgress:
    """Profile-scoped Greia Storage adapter (never raises into the game loop)."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _resolve(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> WorkshopProgress:
        try:
            storage = self._resolve()
            raw = storage.kv_get(STORAGE_KEY) if storage is not None else None
        except Exception:
            return WorkshopProgress()
        return progress_from_payload(raw)

    def save(self, progress: WorkshopProgress) -> None:
        try:
            storage = self._resolve()
            if storage is not None:
                storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaMeasureEvents:
    """Publish the manifest-declared milestone/completion facts.

    Keys are scoped per delivery so a replayed delivery is never deduplicated
    against the previous one.
    """

    def parcel_completed(self, delivery_id: str, index: int, summary: JobSummary) -> None:
        self._emit(
            "measure.parcel_completed",
            {"job": summary.kind.value, "stage": summary.stage, "first_try": summary.mistakes == 0},
            f"bottega-misure:{delivery_id}:p{index}",
        )

    def delivery_completed(self, delivery_id: str, jobs: int, stage: int) -> None:
        self._emit(
            "measure.delivery_completed",
            {"jobs": jobs, "stage": stage},
            f"bottega-misure:{delivery_id}",
        )

    @staticmethod
    def _emit(event_id: str, payload: dict, key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaMeasureEvents",
    "GreiaMeasureProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "progress_from_payload",
    "progress_payload",
]
