"""Greia persistence and event adapters for La Corsa delle Bacche.

The first release kept nothing between visits (no storage key existed), so
there is no old payload to migrate: a missing or malformed value simply
starts at rung 1. Schema 1 stores the adaptive rung and a few bounded
counters under one profile-scoped key.
"""

from __future__ import annotations

from typing import Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .corsa_model import MAX_LEVEL, MIN_LEVEL, CorsaProgress, GardenSummary
else:
    from corsa_model import MAX_LEVEL, MIN_LEVEL, CorsaProgress, GardenSummary

STORAGE_KEY = "corsa_bacche_progress"
SCHEMA_VERSION = 1
MAX_COUNT = 1_000_000


class ProgressPort(Protocol):
    def load(self) -> CorsaProgress: ...
    def save(self, progress: CorsaProgress) -> None: ...


class EventPort(Protocol):
    def garden_cleared(self, visit_id: str, index: int, summary: GardenSummary) -> None: ...
    def visit_completed(self, visit_id: str, gardens: int, level: int) -> None: ...


def _count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_COUNT else 0


def progress_from_payload(raw: object) -> CorsaProgress:
    """Read schema 1; anything else (missing, junk, a future schema) starts fresh."""

    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        return CorsaProgress()
    level = raw.get("level", MIN_LEVEL)
    if isinstance(level, bool) or not isinstance(level, int) or not MIN_LEVEL <= level <= MAX_LEVEL:
        level = MIN_LEVEL
    return CorsaProgress(
        level=level,
        gardens_cleared=_count(raw.get("gardens_cleared")),
        visits_completed=_count(raw.get("visits_completed")),
        berries=_count(raw.get("berries")),
    )


def progress_payload(progress: CorsaProgress) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "level": max(MIN_LEVEL, min(MAX_LEVEL, int(progress.level))),
        "gardens_cleared": min(MAX_COUNT, max(0, int(progress.gardens_cleared))),
        "visits_completed": min(MAX_COUNT, max(0, int(progress.visits_completed))),
        "berries": min(MAX_COUNT, max(0, int(progress.berries))),
    }


class GreiaCorsaProgress:
    """Map bounded progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _store(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> CorsaProgress:
        try:
            raw = self._store().kv_get(STORAGE_KEY)
        except Exception:
            return CorsaProgress()
        return progress_from_payload(raw)

    def save(self, progress: CorsaProgress) -> None:
        try:
            self._store().kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaCorsaEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def garden_cleared(self, visit_id: str, index: int, summary: GardenSummary) -> None:
        payload = {
            "garden_index": int(index),
            "level": int(summary.level),
            "berries": int(summary.berries),
            "bumps": int(summary.bumps),
            "hints": int(summary.hints),
            "waits": int(summary.waits),
        }
        _emit("berries.garden_cleared", payload, f"corsa-bacche:{visit_id}:g{index}")

    def visit_completed(self, visit_id: str, gardens: int, level: int) -> None:
        payload = {"gardens": int(gardens), "level": int(level)}
        _emit("berries.visit_completed", payload, f"corsa-bacche:{visit_id}")


def _emit(event_id: str, payload: dict[str, int], key: str) -> None:
    """Facts are best effort: a missing runtime channel never stops play."""

    try:
        emit_activity_event(event_id, payload, idempotency_key=key)
    except Exception:
        return


__all__ = [
    "EventPort",
    "GreiaCorsaEvents",
    "GreiaCorsaProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "progress_from_payload",
    "progress_payload",
]
