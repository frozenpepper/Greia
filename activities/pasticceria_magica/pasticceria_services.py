"""Greia persistence, event and My Creations adapters for Magic Bakery.

Progress lives under the historical key ``pasticceria_magica.state.v3``.
Payload schema 4 stores the ladder rung, finished rounds, orders served, the
"make your own cake" draft and the signature of the last picture shared. A
pre-rework payload (no ``schema_version``: score / stars / recipes_served)
migrates forward: recipes become orders served and the old score and stars
are kept under ``legacy`` so nothing a child earned is dropped.

A shared picture is one flattened 1024x600 PNG written to this Activity's
private storage and published through the trusted Creations broker (never
on autosave; only when the child presses Save).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .pasticceria_content import MAX_LEVEL, PICTURE_NAME, STORAGE_KEY
    from .pasticceria_model import FreeCake
else:
    from pasticceria_content import MAX_LEVEL, PICTURE_NAME, STORAGE_KEY
    from pasticceria_model import FreeCake

SCHEMA_VERSION = 4
MAX_COUNT = 1_000_000
MAX_PICTURE_BYTES = 4 * 1024 * 1024


@dataclass(slots=True)
class BakeryProgress:
    """The child's bakery: ladder rung, history counters and the cake draft."""

    level: int = 0
    rounds: int = 0
    orders_served: int = 0
    free_cake: FreeCake = field(default_factory=FreeCake)
    shared_digest: str = ""
    legacy: dict[str, int] = field(default_factory=dict)


class ProgressPort(Protocol):
    def load(self) -> BakeryProgress: ...
    def save(self, progress: BakeryProgress) -> None: ...


class EventPort(Protocol):
    def order_served(self, event_id: str, session_id: str, payload: dict[str, Any]) -> None: ...
    def round_completed(self, session_id: str, payload: dict[str, Any]) -> None: ...
    def picture_shared(self, digest: str, payload: dict[str, Any]) -> None: ...


class PicturePort(Protocol):
    @property
    def available(self) -> bool: ...
    def publish(self, payload: bytes) -> bool: ...


def _count(value: object, default: int = 0, high: int = MAX_COUNT) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(0, min(high, value))


def parse_progress(raw: object) -> BakeryProgress:
    """Bounded parse of any stored payload (current, legacy or corrupt)."""

    if not isinstance(raw, dict):
        return BakeryProgress()
    if raw.get("schema_version") != SCHEMA_VERSION:
        legacy = {key: _count(raw.get(key)) for key in ("score", "stars") if key in raw}
        return BakeryProgress(orders_served=_count(raw.get("recipes_served")), legacy=legacy)
    legacy_raw = raw.get("legacy")
    legacy = (
        {key: _count(legacy_raw.get(key)) for key in ("score", "stars") if key in legacy_raw}
        if isinstance(legacy_raw, dict)
        else {}
    )
    digest = raw.get("shared_digest")
    return BakeryProgress(
        level=_count(raw.get("level"), 0, MAX_LEVEL),
        rounds=_count(raw.get("rounds")),
        orders_served=_count(raw.get("orders_served")),
        free_cake=FreeCake.from_json(raw.get("free_cake")),
        shared_digest=digest if isinstance(digest, str) and len(digest) == 64 else "",
        legacy=legacy,
    )


def progress_payload(progress: BakeryProgress) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "level": max(0, min(MAX_LEVEL, int(progress.level))),
        "rounds": max(0, min(MAX_COUNT, int(progress.rounds))),
        "orders_served": max(0, min(MAX_COUNT, int(progress.orders_served))),
        "free_cake": progress.free_cake.to_json(),
        "shared_digest": progress.shared_digest,
    }
    if progress.legacy:
        payload["legacy"] = dict(progress.legacy)
    return payload


class GreiaBakeryProgress:
    """Map progress onto profile-scoped Greia Storage (fail-soft)."""

    def __init__(self, storage=None) -> None:
        if storage is None:
            try:
                storage = get_storage()
            except Exception:
                storage = None
        self._storage = storage

    def load(self) -> BakeryProgress:
        if self._storage is None:
            return BakeryProgress()
        try:
            return parse_progress(self._storage.kv_get(STORAGE_KEY))
        except Exception:
            return BakeryProgress()

    def save(self, progress: BakeryProgress) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaBakeryEvents:
    """Publish the milestone, completion and creation facts the manifest declares."""

    def order_served(self, event_id: str, session_id: str, payload: dict[str, Any]) -> None:
        self._emit(event_id, payload, f"pasticceria:{session_id}:o{payload.get('order', 0)}")

    def round_completed(self, session_id: str, payload: dict[str, Any]) -> None:
        self._emit("round.completed", payload, f"pasticceria:{session_id}")

    def picture_shared(self, digest: str, payload: dict[str, Any]) -> None:
        self._emit("creation.completed", payload, f"pasticceria-cake:{digest}")

    @staticmethod
    def _emit(event_id: str, payload: dict[str, Any], key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


class GreiaBakeryPictures:
    """Write the flattened cake picture privately, then publish it to My Creations."""

    def __init__(self, storage=None, creations=None) -> None:
        self._storage = storage
        self._creations = creations

    @property
    def available(self) -> bool:
        return self._storage is not None and self._creations is not None

    def publish(self, payload: bytes) -> bool:
        if not self.available or not isinstance(payload, bytes) or not payload or len(payload) > MAX_PICTURE_BYTES:
            return False
        try:
            self._storage.file_write_atomic(PICTURE_NAME, payload)
            self._creations.publish_private_file(PICTURE_NAME, media_type="image/png", role="composition")
        except Exception:
            return False
        return True


def picture_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "BakeryProgress",
    "EventPort",
    "GreiaBakeryEvents",
    "GreiaBakeryPictures",
    "GreiaBakeryProgress",
    "PicturePort",
    "ProgressPort",
    "SCHEMA_VERSION",
    "parse_progress",
    "picture_digest",
    "progress_payload",
]
