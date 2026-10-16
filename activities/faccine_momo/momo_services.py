"""Greia persistence and event adapters for Momo's Happy Faces.

Progress lives under ``faccine_momo.progress.v1`` (schema 1): the ladder rung
and the feelings the child has recognised so far. The pre-rework Activity
stored nothing, so there is no older payload to migrate; anything unreadable
loads as a fresh start and is never written back over unless a visit ends.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .momo_content import ALL_EMOTIONS, MAX_LEVEL, STORAGE_KEY
else:
    from momo_content import ALL_EMOTIONS, MAX_LEVEL, STORAGE_KEY

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class MomoProgress:
    level: int = 0
    known: tuple[str, ...] = ()


class ProgressPort(Protocol):
    def load(self) -> MomoProgress: ...
    def save(self, progress: MomoProgress) -> None: ...


class MomoEventPort(Protocol):
    def emotion_discovered(self, emotion: str) -> None: ...
    def visit_completed(self, session_id: str, payload: dict[str, Any]) -> None: ...


def parse_progress(raw: object) -> MomoProgress:
    """Bounded parse of any stored payload (current or corrupt)."""

    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        return MomoProgress()
    level = raw.get("level")
    if isinstance(level, bool) or not isinstance(level, int):
        level = 0
    known_raw = raw.get("known")
    names = {emotion.value for emotion in ALL_EMOTIONS}
    known = tuple(
        emotion.value
        for emotion in ALL_EMOTIONS
        if isinstance(known_raw, list) and emotion.value in known_raw and emotion.value in names
    )
    return MomoProgress(level=max(0, min(MAX_LEVEL, level)), known=known)


def progress_payload(progress: MomoProgress) -> dict[str, Any]:
    names = [emotion.value for emotion in ALL_EMOTIONS]
    return {
        "schema_version": SCHEMA_VERSION,
        "level": max(0, min(MAX_LEVEL, int(progress.level))),
        "known": [name for name in names if name in progress.known],
    }


class NullMomoProgress:
    """Standalone-preview store; production composition injects Greia storage."""

    def __init__(self, progress: MomoProgress | None = None) -> None:
        self.saved = progress or MomoProgress()

    def load(self) -> MomoProgress:
        return self.saved

    def save(self, progress: MomoProgress) -> None:
        self.saved = progress


class GreiaMomoProgress:
    """Map bounded progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _store(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> MomoProgress:
        try:
            return parse_progress(self._store().kv_get(STORAGE_KEY))
        except Exception:
            return MomoProgress()

    def save(self, progress: MomoProgress) -> None:
        try:
            self._store().kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class NullMomoEvents:
    """Standalone-preview sink; production composition injects GreiaMomoEvents."""

    def emotion_discovered(self, emotion: str) -> None:
        pass

    def visit_completed(self, session_id: str, payload: dict[str, Any]) -> None:
        pass


class GreiaMomoEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def emotion_discovered(self, emotion: str) -> None:
        emit_activity_event(
            "faccine_momo.emotion_discovered",
            {"emotion": emotion},
            idempotency_key=f"faccine-momo:emotion:{emotion}",
        )

    def visit_completed(self, session_id: str, payload: dict[str, Any]) -> None:
        emit_activity_event(
            "faccine_momo.visit_completed",
            payload,
            idempotency_key=f"faccine-momo:{session_id}",
        )


__all__ = [
    "GreiaMomoEvents",
    "GreiaMomoProgress",
    "MomoEventPort",
    "MomoProgress",
    "NullMomoEvents",
    "NullMomoProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "parse_progress",
    "progress_payload",
]
