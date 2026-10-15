"""Greia persistence and event adapters for Tito's Number Forest.

Progress stays under the original storage key ``bosco_numeri_progress``.
Version 1 saves (from the old tap-to-count game) held only
``total_completed`` and ``current_number``; they load unchanged and are
carried forward in every later save, so no child data is lost. Version 2 adds
the next teaching group, the walks completed and how often each numeral 0–10
has been written (bounded).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Mapping, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

STORAGE_KEY: Final[str] = "bosco_numeri_progress"
SCHEMA_VERSION: Final[int] = 2
MAX_COUNT: Final[int] = 999
MAX_GROUP: Final[int] = 64
MAX_ROUNDS: Final[int] = 1_000_000


def _count(value: object, upper: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return min(upper, value)
    return 0


def _numeral_key(value: object) -> int | None:
    """Numeral keys are stored as JSON strings "0".."10"."""

    if isinstance(value, str) and value.isdigit() and len(value) <= 2:
        number = int(value)
        return number if 0 <= number <= 10 else None
    return None


@dataclass
class BoscoProgress:
    """Bounded, profile-scoped forest progress (all fields JSON-safe)."""

    group: int = 0
    rounds_completed: int = 0
    traced: dict[int, int] = field(default_factory=dict)
    # Carried forward unchanged from version-1 saves (old counting game).
    legacy_total_completed: int = 0
    legacy_current_number: int = 1

    def record_trace(self, value: int) -> bool:
        """Count one written numeral; True the first time it is written."""

        first = self.traced.get(value, 0) == 0
        self.traced[value] = min(MAX_COUNT, self.traced.get(value, 0) + 1)
        return first

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "group": max(0, min(MAX_GROUP, int(self.group))),
            "rounds_completed": max(0, min(MAX_ROUNDS, int(self.rounds_completed))),
            "traced": {str(value): int(count) for value, count in sorted(self.traced.items())},
            "total_completed": max(0, int(self.legacy_total_completed)),
            "current_number": int(self.legacy_current_number),
        }

    @classmethod
    def from_payload(cls, raw: object) -> "BoscoProgress":
        """Parse v1 or v2 payloads defensively; malformed parts are dropped."""

        if not isinstance(raw, Mapping):
            return cls()
        traced: dict[int, int] = {}
        raw_traced = raw.get("traced", {})
        if isinstance(raw_traced, Mapping):
            for key, value in list(raw_traced.items())[:16]:
                number = _numeral_key(key)
                count = _count(value, MAX_COUNT)
                if number is not None and count:
                    traced[number] = count
        current = raw.get("current_number", 1)
        if not (isinstance(current, int) and not isinstance(current, bool) and 1 <= current <= 10):
            current = 1
        return cls(
            group=min(MAX_GROUP, _count(raw.get("group", 0), MAX_GROUP)),
            rounds_completed=_count(raw.get("rounds_completed", 0), MAX_ROUNDS),
            traced=traced,
            legacy_total_completed=_count(raw.get("total_completed", 0), MAX_ROUNDS),
            legacy_current_number=current,
        )


class ProgressPort(Protocol):
    def load(self) -> BoscoProgress: ...
    def save(self, progress: BoscoProgress) -> None: ...


class EventPort(Protocol):
    def numeral_written(self, session_id: str, value: int) -> None: ...
    def walk_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


class GreiaBoscoProgress:
    """Map forest progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _store(self):
        return self._storage if self._storage is not None else get_storage()

    def load(self) -> BoscoProgress:
        try:
            raw = self._store().kv_get(STORAGE_KEY, {})
        except Exception:
            return BoscoProgress()
        return BoscoProgress.from_payload(raw)

    def save(self, progress: BoscoProgress) -> None:
        try:
            self._store().kv_set(STORAGE_KEY, progress.to_payload())
        except Exception:
            return


class GreiaBoscoEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def numeral_written(self, session_id: str, value: int) -> None:
        emit_activity_event(
            "bosco.number_completed",
            {"number": int(value)},
            idempotency_key=f"bosco-numeri:{session_id}:{value}",
        )

    def walk_completed(self, session_id: str, payload: dict[str, int]) -> None:
        emit_activity_event(
            "bosco.challenge_completed",
            payload,
            idempotency_key=f"bosco-numeri:{session_id}",
        )


__all__ = [
    "BoscoProgress",
    "EventPort",
    "GreiaBoscoEvents",
    "GreiaBoscoProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
]
