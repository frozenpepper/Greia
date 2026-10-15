"""Greia persistence and event adapters for Woodland Hide & Seek.

Progress keeps the original key ``nascondino_bosco.progress.v2``. Payload
schema 3 stores the ladder rung, the next season, the lifetime number of
friends found (the old ``stars`` value, never lost) and which friends the
child has ever found. A pre-rework payload (``{"stars": n}``) loads with its
stars kept and starts on the first rung.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .woodland_content import FRIEND_IDS, MAX_LEVEL, SEASON_IDS, STORAGE_KEY
else:
    from woodland_content import FRIEND_IDS, MAX_LEVEL, SEASON_IDS, STORAGE_KEY

SCHEMA_VERSION = 3
MAX_STARS = 1_000_000


@dataclass(frozen=True, slots=True)
class WoodlandProgress:
    level: int = 0
    season: int = 0
    stars: int = 0
    friends: tuple[str, ...] = ()


class ProgressPort(Protocol):
    def load(self) -> WoodlandProgress: ...
    def save(self, progress: WoodlandProgress) -> None: ...


class EventPort(Protocol):
    def friend_found(self, session_id: str, payload: dict[str, Any]) -> None: ...
    def round_completed(self, session_id: str, payload: dict[str, Any]) -> None: ...


def _int(value: object, default: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(low, min(high, value))


def parse_progress(raw: object) -> WoodlandProgress:
    """Bounded parse of any stored payload (current, legacy or corrupt)."""

    if not isinstance(raw, dict):
        return WoodlandProgress()
    stars = _int(raw.get("stars"), 0, 0, MAX_STARS)
    if raw.get("schema_version") != SCHEMA_VERSION:
        return WoodlandProgress(stars=stars)
    friends = raw.get("friends")
    known = tuple(
        friend for friend in FRIEND_IDS if isinstance(friends, list) and friend in friends
    )
    return WoodlandProgress(
        level=_int(raw.get("level"), 0, 0, MAX_LEVEL),
        season=_int(raw.get("season"), 0, 0, len(SEASON_IDS) - 1),
        stars=stars,
        friends=known,
    )


def progress_payload(progress: WoodlandProgress) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "level": max(0, min(MAX_LEVEL, int(progress.level))),
        "season": max(0, min(len(SEASON_IDS) - 1, int(progress.season))),
        "stars": max(0, min(MAX_STARS, int(progress.stars))),
        "friends": [friend for friend in FRIEND_IDS if friend in progress.friends],
    }


class GreiaWoodlandProgress:
    """Map bounded progress onto profile-scoped Greia Storage (fail-soft)."""

    def __init__(self, storage=None) -> None:
        if storage is None:
            try:
                storage = get_storage()
            except Exception:
                storage = None
        self._storage = storage

    def load(self) -> WoodlandProgress:
        if self._storage is None:
            return WoodlandProgress()
        try:
            return parse_progress(self._storage.kv_get(STORAGE_KEY))
        except Exception:
            return WoodlandProgress()

    def save(self, progress: WoodlandProgress) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaWoodlandEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def friend_found(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(
                "woodland.animal_found",
                payload,
                idempotency_key=f"nascondino-bosco:{session_id}:f{payload.get('found', 0)}",
            )
        except Exception:
            return

    def round_completed(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(
                "woodland.round_completed",
                payload,
                idempotency_key=f"nascondino-bosco:{session_id}",
            )
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaWoodlandEvents",
    "GreiaWoodlandProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "WoodlandProgress",
    "parse_progress",
    "progress_payload",
]
