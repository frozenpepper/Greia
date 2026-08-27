"""La Discesa della Biglia — durable progress + event reporting.

This module is the Activity's narrow seam to the platform. It
owns the per-profile progress shape (per-level best times) and
the named helper that the lifecycle layer uses to emit semantic
events through the platform's ActivityEventClient.

The Activity never writes global Greia reward files, never
increments Greia Star balances, and never grants badges. It
reports facts; Greia decides rewards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from greia_platform.activity_api import emit_activity_event, get_storage

from ramp_content import ProgressState, empty_progress


STORAGE_KEY = "la_discesa_della_biglia.progress.v1"


@dataclass(frozen=True, slots=True)
class RampStorage:
    """Per-profile progress wrapper around the platform Activity storage."""

    _progress: ProgressState

    @classmethod
    def load(cls) -> "RampStorage":
        storage = get_storage()
        if storage is None:
            return cls(empty_progress())
        try:
            raw = storage.kv_get(STORAGE_KEY, {})
        except Exception:
            return cls(empty_progress())
        if not isinstance(raw, dict):
            return cls(empty_progress())
        best_times_raw = raw.get("best_times", {})
        best_times: dict[str, float] = {}
        if isinstance(best_times_raw, dict):
            for level_id, value in best_times_raw.items():
                if not isinstance(level_id, str) or not isinstance(value, (int, float)):
                    continue
                v = float(value)
                if v > 0:
                    best_times[level_id] = v
        return cls(ProgressState(best_times=best_times))

    def best_time(self, level_id: str) -> float | None:
        return self._progress.best_times.get(level_id)

    def record_completion(self, level_id: str, elapsed: float) -> tuple[bool, float | None]:
        """Record a level completion. Returns (improved, new_best).

        The improved flag is True iff this run was faster than any
        previously recorded run. The full state is also persisted.
        """
        existing = self._progress.best_times.get(level_id)
        improved = existing is None or elapsed < existing
        if not improved:
            return False, existing
        new_state = ProgressState(
            best_times={**self._progress.best_times, level_id: elapsed}
        )
        storage = get_storage()
        if storage is not None:
            try:
                storage.kv_set(
                    STORAGE_KEY,
                    {"best_times": dict(new_state.best_times)},
                )
            except Exception:
                pass
        return True, elapsed

    def reset(self) -> None:
        storage = get_storage()
        if storage is None:
            return
        try:
            storage.kv_set(STORAGE_KEY, {"best_times": {}})
        except Exception:
            pass


class RampEvents:
    """Named wrapper around the platform's event client.

    Each method maps to a declared event id in `activity.toml`. The
    manifest is the contract; this class is a typed convenience.
    """

    @staticmethod
    def run_started(level_id: str) -> None:
        _emit("ramp.run_started", {"level": level_id})

    @staticmethod
    def tool_placed(tool_kind: str) -> None:
        _emit("ramp.tool_placed", {"tool": tool_kind})

    @staticmethod
    def basket_hit(level_id: str, elapsed: float) -> None:
        _emit(
            "ramp.basket_hit",
            {"level": level_id, "elapsed": round(elapsed, 2)},
        )

    @staticmethod
    def basket_missed(level_id: str, elapsed: float) -> None:
        _emit(
            "ramp.basket_missed",
            {"level": level_id, "elapsed": round(elapsed, 2)},
        )

    @staticmethod
    def level_completed(level_id: str, elapsed: float, improved: bool) -> None:
        _emit(
            "ramp.level_completed",
            {
                "level": level_id,
                "elapsed": round(elapsed, 2),
                "improved": improved,
            },
        )

    @staticmethod
    def personal_best(level_id: str, elapsed: float) -> None:
        # `score` event: numeric `score` + correct score_order in
        # the manifest. The ActivityHistory service uses these to
        # record the personal best; the Greia progression policy
        # decides whether the run earns a Star.
        _emit(
            "ramp.personal_best",
            {
                "level": level_id,
                "score": round(elapsed, 2),
            },
        )


def _emit(event_id: str, payload: dict[str, Any]) -> None:
    # The ActivityEventClient is the platform's IPC; it can be
    # unavailable in the simulator. We try/except so a missing
    # broker is a no-op for the simulator gate, not an error.
    try:
        emit_activity_event(event_id, payload=payload)
    except Exception:
        pass
