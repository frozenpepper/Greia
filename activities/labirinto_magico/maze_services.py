"""Greia persistence and event adapters for Il Labirinto Magico.

Storage keeps the original key (``labirinto_magico.progress.v2``) so existing
child saves load. The first release stored ``{"stars": N}`` (a lifetime star
counter, +5 per finished maze, with the maze size chosen by hand). It migrates
forward to schema 3 on first load: the star count is kept and a child who had
already gathered many stars resumes a little further up the ladder instead of
on the very first tiny maze.
"""

from __future__ import annotations

from typing import Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .maze_model import MIN_LEVEL, LabyrinthProgress, MazeSummary, clamp_level
else:
    from maze_model import MIN_LEVEL, LabyrinthProgress, MazeSummary, clamp_level

STORAGE_KEY: Final = "labirinto_magico.progress.v2"
SCHEMA_VERSION: Final = 3
_COUNTER_LIMIT: Final = 10_000_000
# Legacy lifetime stars -> starting rung (first release: ~8 stars per maze).
_LEGACY_LEVELS: Final[tuple[tuple[int, int], ...]] = ((60, 3), (15, 2))


def _counter(raw: dict, key: str) -> int:
    value = raw.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(_COUNTER_LIMIT, int(value)))


def progress_from_payload(raw: object) -> LabyrinthProgress:
    """Parse schema 3, migrate the first release's ``{"stars": N}``, else start fresh."""

    if not isinstance(raw, dict):
        return LabyrinthProgress()
    if raw.get("schema_version") == SCHEMA_VERSION:
        return LabyrinthProgress(
            level=clamp_level(raw.get("level", MIN_LEVEL)),
            stars=_counter(raw, "stars"),
            mazes_solved=_counter(raw, "mazes_solved"),
            visits_completed=_counter(raw, "visits_completed"),
        )
    if "stars" in raw:
        stars = _counter(raw, "stars")
        level = next((rung for threshold, rung in _LEGACY_LEVELS if stars >= threshold), MIN_LEVEL)
        return LabyrinthProgress(level=level, stars=stars)
    return LabyrinthProgress()


def progress_payload(progress: LabyrinthProgress) -> dict[str, int]:
    return {
        "schema_version": SCHEMA_VERSION,
        "level": clamp_level(progress.level),
        "stars": min(_COUNTER_LIMIT, max(0, progress.stars)),
        "mazes_solved": min(_COUNTER_LIMIT, max(0, progress.mazes_solved)),
        "visits_completed": min(_COUNTER_LIMIT, max(0, progress.visits_completed)),
    }


class ProgressPort(Protocol):
    def load(self) -> LabyrinthProgress: ...
    def save(self, progress: LabyrinthProgress) -> None: ...


class EventPort(Protocol):
    def star_collected(self, visit_id: str, maze: int, star: int, total: int) -> None: ...
    def maze_solved(self, visit_id: str, maze: int, summary: MazeSummary) -> None: ...
    def visit_completed(self, visit_id: str, mazes: int, level: int) -> None: ...


class GreiaLabyrinthProgress:
    """Profile-scoped Greia Storage adapter (never raises into the game loop)."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _resolve(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> LabyrinthProgress:
        try:
            storage = self._resolve()
            raw = storage.kv_get(STORAGE_KEY) if storage is not None else None
        except Exception:
            return LabyrinthProgress()
        return progress_from_payload(raw)

    def save(self, progress: LabyrinthProgress) -> None:
        try:
            storage = self._resolve()
            if storage is not None:
                storage.kv_set(STORAGE_KEY, progress_payload(progress))
        except Exception:
            return


class GreiaLabyrinthEvents:
    """Publish the manifest-declared facts, scoped per visit (never deduplicated
    against a replayed visit)."""

    def star_collected(self, visit_id: str, maze: int, star: int, total: int) -> None:
        self._emit(
            "maze.star_collected",
            {"stars": total},
            f"labirinto:{visit_id}:m{maze}:s{star}",
        )

    def maze_solved(self, visit_id: str, maze: int, summary: MazeSummary) -> None:
        self._emit(
            "maze.solved",
            {"level": summary.level, "stars": summary.stars, "first_try": summary.clean},
            f"labirinto:{visit_id}:m{maze}",
        )

    def visit_completed(self, visit_id: str, mazes: int, level: int) -> None:
        self._emit(
            "maze.completed",
            {"mazes": mazes, "level": level},
            f"labirinto:{visit_id}:completed",
        )

    @staticmethod
    def _emit(event_id: str, payload: dict, key: str) -> None:
        try:
            emit_activity_event(event_id, payload, idempotency_key=key)
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaLabyrinthEvents",
    "GreiaLabyrinthProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "progress_from_payload",
    "progress_payload",
]
