"""Greia persistence and event adapters for Bridge Builders.

Storage keeps the original key (``costruiamo_ponti.progress.v2``) so existing
child saves load. The first release stored ``{"stars": n}`` for three fixed
copy-the-icon bridges that no longer exist; schema 3 keeps that count verbatim
under ``stars`` (child data is never dropped) and adds which set of crossings
comes next plus simple lifetime counters.

A completed crossing keeps the first release's ``bridge.level_completed`` id:
the platform star rule and the Bridge Builder achievement count it.

Events report facts only (Greia decides rewards) and carry per-visit
idempotency keys so a replayed visit is never deduplicated against an old one.
"""

from __future__ import annotations

from typing import Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .ponti_content import CROSSING_SETS
    from .ponti_model import PontiProgress
else:
    from ponti_content import CROSSING_SETS
    from ponti_model import PontiProgress

STORAGE_KEY: Final = "costruiamo_ponti.progress.v2"
SCHEMA_VERSION: Final = 3
_COUNTER_LIMIT: Final = 10_000_000


def _counter(raw: dict, key: str) -> int:
    value = raw.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(_COUNTER_LIMIT, int(value)))


def progress_from_payload(raw: object) -> PontiProgress:
    """Parse schema 3, migrate the first release's stars, else start fresh."""

    if not isinstance(raw, dict):
        return PontiProgress()
    stars = _counter(raw, "stars")
    if raw.get("schema_version") == SCHEMA_VERSION:
        return PontiProgress(
            next_set=_counter(raw, "next_set") % len(CROSSING_SETS),
            crossings_solved=_counter(raw, "crossings_solved"),
            sets_completed=_counter(raw, "sets_completed"),
            legacy_stars=stars,
        )
    return PontiProgress(legacy_stars=stars)


def progress_payload(progress: PontiProgress) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "next_set": max(0, progress.next_set) % len(CROSSING_SETS),
        "crossings_solved": min(_COUNTER_LIMIT, max(0, progress.crossings_solved)),
        "sets_completed": min(_COUNTER_LIMIT, max(0, progress.sets_completed)),
        "stars": min(_COUNTER_LIMIT, max(0, progress.legacy_stars)),
    }


class ProgressPort(Protocol):
    def load(self) -> PontiProgress: ...
    def save(self, progress: PontiProgress) -> None: ...


class EventPort(Protocol):
    def plank_placed(self, visit_id: str, crossing_id: str, length: int, strong: bool) -> None: ...
    def test_started(self, visit_id: str, crossing_id: str, test: int) -> None: ...
    def crossing_completed(self, visit_id: str, crossing_id: str, tests: int) -> None: ...
    def crossing_missed(self, visit_id: str, crossing_id: str, test: int, reason: str) -> None: ...
    def set_completed(self, visit_id: str, set_id: str, crossings: int) -> None: ...


class GreiaPontiProgress:
    """Profile-scoped Greia Storage adapter (never raises into the game loop)."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _resolve(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> PontiProgress:
        try:
            storage = self._resolve()
            raw = storage.kv_get(STORAGE_KEY) if storage is not None else None
        except Exception:
            return PontiProgress()
        return progress_from_payload(raw)

    def save(self, progress: PontiProgress) -> None:
        try:
            storage = self._resolve()
            if storage is not None:
                storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaPontiEvents:
    """Publish the manifest-declared facts, scoped per visit."""

    def __init__(self) -> None:
        self._placed = 0

    def plank_placed(self, visit_id: str, crossing_id: str, length: int, strong: bool) -> None:
        self._placed += 1
        self._emit(
            "bridge.plank_placed",
            {"crossing": crossing_id, "length": length, "stone": strong},
            f"ponti:{visit_id}:{crossing_id}:p{self._placed}",
        )

    def test_started(self, visit_id: str, crossing_id: str, test: int) -> None:
        self._emit("bridge.test_started", {"crossing": crossing_id, "test": test}, f"ponti:{visit_id}:{crossing_id}:t{test}")

    def crossing_completed(self, visit_id: str, crossing_id: str, tests: int) -> None:
        self._emit(
            "bridge.level_completed", {"crossing": crossing_id, "tests": tests}, f"ponti:{visit_id}:{crossing_id}:done"
        )

    def crossing_missed(self, visit_id: str, crossing_id: str, test: int, reason: str) -> None:
        self._emit(
            "bridge.crossing_missed",
            {"crossing": crossing_id, "test": test, "reason": reason},
            f"ponti:{visit_id}:{crossing_id}:m{test}",
        )

    def set_completed(self, visit_id: str, set_id: str, crossings: int) -> None:
        self._emit("bridge.set_completed", {"set": set_id, "crossings": crossings}, f"ponti:{visit_id}:completed")

    @staticmethod
    def _emit(event_id: str, payload: dict, key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaPontiEvents",
    "GreiaPontiProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "progress_from_payload",
    "progress_payload",
]
