"""Greia persistence and event adapters for The Big Seasons Tree.

Progress lives under ``quattro_stagioni.progress.v1`` (profile-scoped Greia
Storage): the ladder rung, which seasons the child has dressed, the last
season played and the number of finished rounds. The pre-rework Activity
stored nothing, so there is no older payload to migrate; anything unknown or
corrupt loads as a fresh start and is never written back unless the child
plays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .tree_content import MAX_LEVEL, SEASONS, STORAGE_KEY, Season
else:
    from tree_content import MAX_LEVEL, SEASONS, STORAGE_KEY, Season

SCHEMA_VERSION = 1
MAX_ROUNDS = 1_000_000


@dataclass(frozen=True, slots=True)
class SeasonsProgress:
    level: int = 0
    dressed: tuple[Season, ...] = ()
    last: Season | None = None
    rounds: int = 0

    def next_season(self) -> Season:
        """The season the picker focuses: the first not yet dressed, else the next."""

        for season in SEASONS:
            if season not in self.dressed:
                return season
        if self.last is None:
            return SEASONS[0]
        return SEASONS[(SEASONS.index(self.last) + 1) % len(SEASONS)]


class ProgressPort(Protocol):
    def load(self) -> SeasonsProgress: ...
    def save(self, progress: SeasonsProgress) -> None: ...


class EventPort(Protocol):
    def season_dressed(self, session_id: str, payload: dict[str, Any]) -> None: ...
    def all_seasons_dressed(self, session_id: str, payload: dict[str, Any]) -> None: ...


def _int(value: object, default: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(low, min(high, value))


def parse_progress(raw: object) -> SeasonsProgress:
    """Bounded parse of any stored payload (current or corrupt)."""

    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        return SeasonsProgress()
    dressed_raw = raw.get("dressed")
    dressed = tuple(
        season for season in SEASONS if isinstance(dressed_raw, list) and season.value in dressed_raw
    )
    last_raw = raw.get("last")
    last = Season(last_raw) if isinstance(last_raw, str) and last_raw in {s.value for s in SEASONS} else None
    return SeasonsProgress(
        level=_int(raw.get("level"), 0, 0, MAX_LEVEL),
        dressed=dressed,
        last=last,
        rounds=_int(raw.get("rounds"), 0, 0, MAX_ROUNDS),
    )


def progress_payload(progress: SeasonsProgress) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "level": max(0, min(MAX_LEVEL, int(progress.level))),
        "dressed": [season.value for season in SEASONS if season in progress.dressed],
        "last": progress.last.value if progress.last is not None else None,
        "rounds": max(0, min(MAX_ROUNDS, int(progress.rounds))),
    }


class GreiaSeasonsProgress:
    """Map bounded progress onto profile-scoped Greia Storage (fail-soft)."""

    def __init__(self, storage=None) -> None:
        if storage is None:
            try:
                storage = get_storage()
            except Exception:
                storage = None
        self._storage = storage

    def load(self) -> SeasonsProgress:
        if self._storage is None:
            return SeasonsProgress()
        try:
            return parse_progress(self._storage.kv_get(STORAGE_KEY))
        except Exception:
            return SeasonsProgress()

    def save(self, progress: SeasonsProgress) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaSeasonsEvents:
    """Publish the completion and milestone facts declared by the manifest."""

    def season_dressed(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(
                "quattro_stagioni.season_dressed",
                payload,
                idempotency_key=f"quattro-stagioni:{session_id}",
            )
        except Exception:
            return

    def all_seasons_dressed(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(
                "quattro_stagioni.all_seasons_discovered",
                payload,
                idempotency_key=f"quattro-stagioni:{session_id}:all",
            )
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaSeasonsEvents",
    "GreiaSeasonsProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "SeasonsProgress",
    "parse_progress",
    "progress_payload",
]
