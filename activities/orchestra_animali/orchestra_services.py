"""Greia persistence and event adapters for Orchestra Animali.

Progress lives under the original ``STORAGE_KEY`` (schema 2); a legacy
``{"stars": n}`` payload loads with its stars intact and is rewritten in the
new shape on the next save. Events are the manifest-declared facts only.
"""

from __future__ import annotations

from typing import Any, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .orchestra_content import STORAGE_KEY
    from .orchestra_model import ConcertProgress
else:  # pragma: no cover - runtime/script fallback
    from orchestra_content import STORAGE_KEY
    from orchestra_model import ConcertProgress


class ProgressPort(Protocol):
    def load(self) -> ConcertProgress: ...
    def save(self, progress: ConcertProgress) -> None: ...


class EventPort(Protocol):
    def instrument_played(self, session_id: str, instrument: str) -> None: ...
    def echo_matched(self, session_id: str, index: int, level: int) -> None: ...
    def concert_completed(self, session_id: str, payload: dict[str, int]) -> None: ...
    def concert_performed(self, key: str, live_inputs: int) -> None: ...


class GreiaOrchestraProgress:
    """Map bounded Orchestra progress onto profile-scoped Greia Storage."""

    def __init__(self, storage: Any | None = None) -> None:
        self._storage = storage

    @classmethod
    def from_platform(cls) -> "GreiaOrchestraProgress":
        try:
            return cls(get_storage())
        except Exception:
            return cls(None)

    @property
    def storage(self) -> Any | None:
        return self._storage

    def load(self) -> ConcertProgress:
        if self._storage is None:
            return ConcertProgress()
        try:
            raw = self._storage.kv_get(STORAGE_KEY, {})
        except Exception:
            return ConcertProgress()
        return ConcertProgress.from_raw(raw)

    def save(self, progress: ConcertProgress) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, progress.as_dict())
        except Exception:
            return


class GreiaOrchestraEvents:
    """Publish the facts declared in ``activity.toml`` (fail-soft)."""

    def instrument_played(self, session_id: str, instrument: str) -> None:
        self._emit(
            "instrument.played",
            {"instrument": instrument},
            f"orchestra:{session_id}:{instrument}",
        )

    def echo_matched(self, session_id: str, index: int, level: int) -> None:
        self._emit(
            "rhythm.echoed",
            {"echo_index": index + 1, "level": level},
            f"orchestra:{session_id}:echo{index + 1}",
        )

    def concert_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self._emit("band.concert_completed", payload, f"orchestra:{session_id}")

    def concert_performed(self, key: str, live_inputs: int) -> None:
        self._emit("concert.performed", {"live_inputs": live_inputs}, f"orchestra:{key}")

    @staticmethod
    def _emit(event_id: str, payload: dict[str, object], key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


__all__ = ["EventPort", "GreiaOrchestraEvents", "GreiaOrchestraProgress", "ProgressPort"]
