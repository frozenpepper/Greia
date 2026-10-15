"""Greia persistence and event adapters for Tito's Marble Run.

Storage keeps the original key (``la_discesa_della_biglia.progress.v1``) so
existing child saves load. The first release stored ``{"best_times": {level:
seconds}}`` for three free-placement levels that no longer exist; schema 2
keeps those times verbatim under ``best_times`` (child data is never dropped)
and adds which set of boards comes next plus simple lifetime counters.

Events report facts only (Greia decides rewards) and carry per-visit
idempotency keys so a replayed visit is never deduplicated against an old one.
"""

from __future__ import annotations

from typing import Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .ramp_content import BOARD_SETS
    from .ramp_model import RampProgress
else:
    from ramp_content import BOARD_SETS
    from ramp_model import RampProgress

STORAGE_KEY: Final = "la_discesa_della_biglia.progress.v1"
SCHEMA_VERSION: Final = 2
_COUNTER_LIMIT: Final = 10_000_000
_LEGACY_LIMIT: Final = 64  # bounded copy of the first release's best times


def _counter(raw: dict, key: str) -> int:
    value = raw.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(_COUNTER_LIMIT, int(value)))


def _best_times(raw: dict) -> dict[str, float]:
    times = raw.get("best_times", {})
    result: dict[str, float] = {}
    if not isinstance(times, dict):
        return result
    for level_id, value in times.items():
        if len(result) >= _LEGACY_LIMIT:
            break
        if isinstance(level_id, str) and isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            result[level_id] = float(value)
    return result


def progress_from_payload(raw: object) -> RampProgress:
    """Parse schema 2, migrate the first release's best times, else start fresh."""

    if not isinstance(raw, dict):
        return RampProgress()
    legacy = _best_times(raw)
    if raw.get("schema_version") == SCHEMA_VERSION:
        next_set = _counter(raw, "next_set") % len(BOARD_SETS)
        return RampProgress(
            next_set=next_set,
            boards_solved=_counter(raw, "boards_solved"),
            sets_completed=_counter(raw, "sets_completed"),
            legacy_best_times=legacy,
        )
    return RampProgress(legacy_best_times=legacy)


def progress_payload(progress: RampProgress) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "next_set": max(0, progress.next_set) % len(BOARD_SETS),
        "boards_solved": min(_COUNTER_LIMIT, max(0, progress.boards_solved)),
        "sets_completed": min(_COUNTER_LIMIT, max(0, progress.sets_completed)),
        "best_times": dict(progress.legacy_best_times),
    }


class ProgressPort(Protocol):
    def load(self) -> RampProgress: ...
    def save(self, progress: RampProgress) -> None: ...


class EventPort(Protocol):
    def run_started(self, visit_id: str, board_id: str, run: int) -> None: ...
    def basket_hit(self, visit_id: str, board_id: str, runs: int) -> None: ...
    def basket_missed(self, visit_id: str, board_id: str, run: int, outcome: str) -> None: ...
    def set_completed(self, visit_id: str, set_id: str, boards: int) -> None: ...


class GreiaRampProgress:
    """Profile-scoped Greia Storage adapter (never raises into the game loop)."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _resolve(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> RampProgress:
        try:
            storage = self._resolve()
            raw = storage.kv_get(STORAGE_KEY) if storage is not None else None
        except Exception:
            return RampProgress()
        return progress_from_payload(raw)

    def save(self, progress: RampProgress) -> None:
        try:
            storage = self._resolve()
            if storage is not None:
                storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaRampEvents:
    """Publish the manifest-declared facts, scoped per visit."""

    def run_started(self, visit_id: str, board_id: str, run: int) -> None:
        self._emit("ramp.run_started", {"board": board_id, "run": run}, f"biglia:{visit_id}:{board_id}:r{run}")

    def basket_hit(self, visit_id: str, board_id: str, runs: int) -> None:
        self._emit("ramp.basket_hit", {"board": board_id, "runs": runs}, f"biglia:{visit_id}:{board_id}:hit")

    def basket_missed(self, visit_id: str, board_id: str, run: int, outcome: str) -> None:
        self._emit(
            "ramp.basket_missed",
            {"board": board_id, "run": run, "outcome": outcome},
            f"biglia:{visit_id}:{board_id}:m{run}",
        )

    def set_completed(self, visit_id: str, set_id: str, boards: int) -> None:
        self._emit("ramp.set_completed", {"set": set_id, "boards": boards}, f"biglia:{visit_id}:completed")

    @staticmethod
    def _emit(event_id: str, payload: dict, key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaRampEvents",
    "GreiaRampProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "progress_from_payload",
    "progress_payload",
]
