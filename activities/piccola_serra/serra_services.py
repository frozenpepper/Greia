"""Greia persistence and event adapters for Piccola Serra.

Schema 1 (the first release) stored ``{"harvest_count": n, "timestamp": t}``
under the same key and was never read back. It migrates forward: the
harvest count is kept and the ladder starts at rung 1. Schema 2 stores the
adaptive rung and a few bounded counters; anything else starts fresh.
"""

from __future__ import annotations

from typing import Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .serra_content import MAX_LEVEL, MIN_LEVEL, PLANTS_BY_ID, STORAGE_KEY
    from .serra_model import PlantSummary, SerraProgress
else:
    from serra_content import MAX_LEVEL, MIN_LEVEL, PLANTS_BY_ID, STORAGE_KEY
    from serra_model import PlantSummary, SerraProgress

SCHEMA_VERSION = 2
MAX_COUNT = 1_000_000


class ProgressPort(Protocol):
    def load(self) -> SerraProgress: ...
    def save(self, progress: SerraProgress) -> None: ...


class EventPort(Protocol):
    def seed_planted(self, visit_id: str, index: int, plant_id: str) -> None: ...
    def plant_finished(self, visit_id: str, index: int, summary: PlantSummary) -> None: ...
    def visit_completed(self, visit_id: str, plants: int, level: int) -> None: ...


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, min(MAX_COUNT, value))


def progress_from_payload(raw: object) -> SerraProgress:
    """Read schema 2, migrate schema 1, otherwise start fresh (never raises)."""

    if not isinstance(raw, dict):
        return SerraProgress()
    version = raw.get("schema_version")
    if version is None and "harvest_count" in raw:
        return SerraProgress(harvests=_count(raw.get("harvest_count")))
    if version != SCHEMA_VERSION:
        return SerraProgress()
    level = raw.get("level", MIN_LEVEL)
    if isinstance(level, bool) or not isinstance(level, int) or not MIN_LEVEL <= level <= MAX_LEVEL:
        level = MIN_LEVEL
    plants_raw = raw.get("plants")
    plants: dict[str, int] = {}
    if isinstance(plants_raw, dict):
        for plant_id in PLANTS_BY_ID:
            count = _count(plants_raw.get(plant_id))
            if count:
                plants[plant_id] = count
    return SerraProgress(
        level=level,
        harvests=_count(raw.get("harvests")),
        visits=_count(raw.get("visits")),
        plants=plants,
    )


def progress_payload(progress: SerraProgress) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "level": max(MIN_LEVEL, min(MAX_LEVEL, int(progress.level))),
        "harvests": _count(int(progress.harvests)),
        "visits": _count(int(progress.visits)),
        "plants": {plant_id: _count(int(count)) for plant_id, count in progress.plants.items() if plant_id in PLANTS_BY_ID},
    }


class GreiaSerraProgress:
    """Map bounded progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _store(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> SerraProgress:
        try:
            raw = self._store().kv_get(STORAGE_KEY)
        except Exception:
            return SerraProgress()
        return progress_from_payload(raw)

    def save(self, progress: SerraProgress) -> None:
        try:
            self._store().kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaSerraEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def seed_planted(self, visit_id: str, index: int, plant_id: str) -> None:
        _emit("greenhouse.seed_planted", {"plant": plant_id, "index": int(index)}, f"piccola-serra:{visit_id}:p{index}:seed")

    def plant_finished(self, visit_id: str, index: int, summary: PlantSummary) -> None:
        payload = {
            "plant": summary.plant_id,
            "level": int(summary.level),
            "care_misses": int(summary.care_misses),
            "order_misses": int(summary.order_misses),
            "cards": int(summary.cards),
        }
        _emit("greenhouse.plant_grown", payload, f"piccola-serra:{visit_id}:p{index}")

    def visit_completed(self, visit_id: str, plants: int, level: int) -> None:
        _emit("greenhouse.harvest_completed", {"plants": int(plants), "level": int(level)}, f"piccola-serra:{visit_id}")


def _emit(event_id: str, payload: dict, key: str) -> None:
    """Facts are best effort: a missing runtime channel never stops play."""

    try:
        emit_activity_event(event_id, payload, idempotency_key=key)
    except Exception:
        return


__all__ = [
    "EventPort",
    "GreiaSerraEvents",
    "GreiaSerraProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "progress_from_payload",
    "progress_payload",
]
