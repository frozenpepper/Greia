"""Greia persistence and event adapters for Stelle Incantate.

The Activity only reports truthful semantic facts; Greia owns Stars, badges
and achievement truth. Durable progress keeps the original key
(``stelle_incantate.progress.v1``) so existing child saves load. The first
release stored a JSON *string* ``{"completed_ids": [...]}``; it migrates
forward to a schema-2 object on first load: completed real constellations stay
revealed, and children who had already lit several figures resume on the 1-10
rung instead of the very first one.
"""

from __future__ import annotations

import json
from typing import Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .sky_content import FIGURES_BY_ID, STORAGE_KEY
    from .sky_model import MAX_COUNTER, MIN_STAGE, FigureSummary, SkyProgress, clamp_stage
else:
    from sky_content import FIGURES_BY_ID, STORAGE_KEY
    from sky_model import MAX_COUNTER, MIN_STAGE, FigureSummary, SkyProgress, clamp_stage

SCHEMA_VERSION: Final[int] = 2
EVENT_CONSTELLATION_COMPLETED: Final[str] = "constellation.completed"
EVENT_FACT_OPENED: Final[str] = "curiosity.fact_opened"
_LEGACY_PROMOTE_AFTER: Final[int] = 4  # figures lit under schema 1


def _counter(raw: dict, key: str, limit: int = MAX_COUNTER) -> int:
    value = raw.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(limit, int(value)))


def _known_ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str) and item in FIGURES_BY_ID}


def progress_from_payload(raw: object) -> SkyProgress:
    """Parse schema 2, migrate schema 1, and fall back safely on anything else."""

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return SkyProgress()
    if not isinstance(raw, dict):
        return SkyProgress()
    if raw.get("schema_version") == SCHEMA_VERSION:
        return SkyProgress(
            stage=clamp_stage(raw.get("stage", MIN_STAGE)),
            clean_streak=_counter(raw, "clean_streak", 3),
            struggle_streak=_counter(raw, "struggle_streak", 3),
            figures_completed=_counter(raw, "figures_completed"),
            nights_completed=_counter(raw, "nights_completed"),
            revealed=_known_ids(raw.get("completed_ids")),
        )
    # Schema 1: {"completed_ids": [...]} with the old six constellation ids.
    legacy = raw.get("completed_ids")
    count = len({item for item in legacy if isinstance(item, str)}) if isinstance(legacy, list) else 0
    return SkyProgress(
        stage=2 if count >= _LEGACY_PROMOTE_AFTER else MIN_STAGE,
        figures_completed=count,
        revealed=_known_ids(legacy),
    )


def progress_payload(progress: SkyProgress) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": clamp_stage(progress.stage),
        "clean_streak": min(3, max(0, progress.clean_streak)),
        "struggle_streak": min(3, max(0, progress.struggle_streak)),
        "figures_completed": min(MAX_COUNTER, max(0, progress.figures_completed)),
        "nights_completed": min(MAX_COUNTER, max(0, progress.nights_completed)),
        # Bounded by the catalogue; the same key the first release used.
        "completed_ids": sorted(progress.revealed & set(FIGURES_BY_ID)),
    }


class ProgressPort(Protocol):
    def load(self) -> SkyProgress: ...
    def save(self, progress: SkyProgress) -> None: ...


class EventPort(Protocol):
    def constellation_completed(self, night_id: str, index: int, summary: FigureSummary) -> None: ...
    def fact_opened(self, night_id: str, figure_id: str) -> None: ...


class GreiaSkyProgress:
    """Profile-scoped Greia Storage adapter (never raises into the game loop)."""

    def __init__(self, storage=None, key: str = STORAGE_KEY) -> None:
        self._storage = storage
        self._key = key

    def _resolve(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> SkyProgress:
        try:
            storage = self._resolve()
            raw = storage.kv_get(self._key) if storage is not None else None
        except Exception:
            return SkyProgress()
        return progress_from_payload(raw)

    def save(self, progress: SkyProgress) -> None:
        try:
            storage = self._resolve()
            if storage is not None:
                storage.kv_set(self._key, progress_payload(progress))
        except Exception:
            return


class GreiaSkyEvents:
    """Publish the manifest-declared completion/milestone facts.

    Keys are scoped per night so a replayed night is never deduplicated
    against the previous one.
    """

    def constellation_completed(self, night_id: str, index: int, summary: FigureSummary) -> None:
        self._emit(
            EVENT_CONSTELLATION_COMPLETED,
            {
                "constellation_id": summary.figure_id,
                "star_count": summary.star_count,
                "stage": summary.stage,
                "first_try": summary.first_try,
            },
            f"sky:{night_id}:figure:{index}",
        )

    def fact_opened(self, night_id: str, figure_id: str) -> None:
        self._emit(EVENT_FACT_OPENED, {"constellation_id": figure_id}, f"sky:{night_id}:fact:{figure_id}")

    @staticmethod
    def _emit(event_id: str, payload: dict, key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


__all__ = [
    "EVENT_CONSTELLATION_COMPLETED",
    "EVENT_FACT_OPENED",
    "EventPort",
    "GreiaSkyEvents",
    "GreiaSkyProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "progress_from_payload",
    "progress_payload",
]
