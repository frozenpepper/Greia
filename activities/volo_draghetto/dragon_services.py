"""Greia persistence and event adapters for Il Volo del Draghetto.

Progress lives under the same profile-scoped key the endless prototype used
(``volo_draghetto.progress.v2``). The old payload ``{"score", "stars",
"timestamp"}`` migrates forward to schema 3: the lifetime star count and old
score are kept, so no child data is lost. Schema 3 stores the best completion
stars per course (unlocking the next course and a look), the chosen look and
a small per-course assist flag (wider rings after a hard flight).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

try:
    from dragon_courses import COURSE_IDS, COURSES, LOOK_IDS
except ImportError:  # pragma: no cover - package import path
    from .dragon_courses import COURSE_IDS, COURSES, LOOK_IDS

STORAGE_KEY = "volo_draghetto.progress.v2"
SCHEMA_VERSION = 3
MAX_COUNTER = 10_000_000


@dataclass(slots=True)
class FlightProgress:
    """Bounded per-profile progress for the course ladder."""

    best: dict[str, int] = field(default_factory=dict)
    assist: dict[str, bool] = field(default_factory=dict)
    look: str = "none"
    lifetime_stars: int = 0
    legacy_score: int = 0

    def is_unlocked(self, index: int) -> bool:
        if index <= 0:
            return True
        if index >= len(COURSES):
            return False
        return self.best.get(COURSES[index - 1].course_id, 0) >= 1

    def look_unlocked(self, look_id: str) -> bool:
        if look_id == "none":
            return True
        return any(
            course.look_reward == look_id and self.best.get(course.course_id, 0) >= 1 for course in COURSES
        )

    def first_open_course(self) -> int:
        """The first unlocked course not finished yet (else the last one)."""

        for index, course in enumerate(COURSES):
            if self.is_unlocked(index) and self.best.get(course.course_id, 0) == 0:
                return index
        return len(COURSES) - 1

    @property
    def star_sum(self) -> int:
        return sum(self.best.values())

    def record(self, course_id: str, earned: int, stars: int, misses: int) -> bool:
        """Store one finished flight; returns True when a new look unlocked."""

        before = {look for look in LOOK_IDS if self.look_unlocked(look)}
        earned = max(1, min(3, int(earned)))
        self.best[course_id] = max(self.best.get(course_id, 0), earned)
        self.assist[course_id] = misses >= 2
        self.lifetime_stars = min(MAX_COUNTER, self.lifetime_stars + max(0, int(stars)))
        after = {look for look in LOOK_IDS if self.look_unlocked(look)}
        return bool(after - before)

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "best": {cid: int(v) for cid, v in self.best.items() if cid in COURSE_IDS},
            "assist": {cid: bool(v) for cid, v in self.assist.items() if cid in COURSE_IDS},
            "look": self.look if self.look in LOOK_IDS else "none",
            "lifetime_stars": int(self.lifetime_stars),
            "legacy_score": int(self.legacy_score),
        }


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(MAX_COUNTER, int(value)))


def parse_progress(raw: object) -> FlightProgress:
    """Parse schema 3, migrate the v2 endless-flight payload, else defaults."""

    if not isinstance(raw, Mapping):
        return FlightProgress()
    if raw.get("schema_version") != SCHEMA_VERSION:
        # Endless-flight prototype: {"score", "stars", "timestamp"}.
        return FlightProgress(lifetime_stars=_count(raw.get("stars")), legacy_score=_count(raw.get("score")))
    best: dict[str, int] = {}
    raw_best = raw.get("best")
    if isinstance(raw_best, Mapping):
        for cid, value in raw_best.items():
            if cid in COURSE_IDS and isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 3:
                best[cid] = value
    assist: dict[str, bool] = {}
    raw_assist = raw.get("assist")
    if isinstance(raw_assist, Mapping):
        for cid, value in raw_assist.items():
            if cid in COURSE_IDS and isinstance(value, bool):
                assist[cid] = value
    look = raw.get("look")
    progress = FlightProgress(
        best=best,
        assist=assist,
        look=look if isinstance(look, str) and look in LOOK_IDS else "none",
        lifetime_stars=_count(raw.get("lifetime_stars")),
        legacy_score=_count(raw.get("legacy_score")),
    )
    if not progress.look_unlocked(progress.look):
        progress.look = "none"
    return progress


class ProgressPort(Protocol):
    def load(self) -> FlightProgress: ...
    def save(self, progress: FlightProgress) -> None: ...


class EventPort(Protocol):
    def ring_passed(self, session_id: str, course_id: str, checkpoint: int) -> None: ...
    def course_completed(self, session_id: str, course_id: str, payload: dict[str, int]) -> None: ...


class GreiaFlightProgress:
    """Map flight progress onto profile-scoped Greia Storage (fail-soft)."""

    def __init__(self, storage=None) -> None:
        if storage is None:
            try:
                storage = get_storage()
            except Exception:
                storage = None
        self._storage = storage

    def load(self) -> FlightProgress:
        if self._storage is None:
            return FlightProgress()
        try:
            raw = self._storage.kv_get(STORAGE_KEY, None)
        except Exception:
            return FlightProgress()
        return parse_progress(raw)

    def save(self, progress: FlightProgress) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, progress.to_payload())
        except Exception:
            return


class GreiaFlightEvents:
    """Publish the milestone/completion facts declared by the manifest."""

    def ring_passed(self, session_id: str, course_id: str, checkpoint: int) -> None:
        try:
            emit_activity_event(
                "flight.ring_passed",
                {"course": course_id, "ring": checkpoint + 1},
                idempotency_key=f"volo-draghetto:{session_id}:r{checkpoint}",
            )
        except Exception:
            return

    def course_completed(self, session_id: str, course_id: str, payload: dict[str, int]) -> None:
        try:
            emit_activity_event(
                "flight.course_completed",
                {"course": course_id, **payload},
                idempotency_key=f"volo-draghetto:{session_id}",
            )
        except Exception:
            return


__all__ = [
    "EventPort",
    "FlightProgress",
    "GreiaFlightEvents",
    "GreiaFlightProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "parse_progress",
]
