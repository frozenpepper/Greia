from __future__ import annotations

from typing import Any

from greia_platform.activity_api import emit_activity_event, get_storage

STORAGE_KEY = "baia_delle_orche.progress.v1"


class GreiaOrcaProgress:
    """Manages persistent progress for Baia delle Orche through Greia Storage."""

    def __init__(self, key: str = STORAGE_KEY) -> None:
        self._key = key

    def load_progress(self) -> dict[str, Any]:
        storage = get_storage()
        if storage is None:
            return {}
        data = storage.kv_get(self._key)
        return data if isinstance(data, dict) else {}

    def save_progress(self, payload: dict[str, Any]) -> None:
        storage = get_storage()
        if storage is not None:
            storage.kv_set(self._key, payload)


class GreiaOrcaEvents:
    """Emits verified semantic milestones and achievements to the Greia platform."""

    def record_feeding(self, count: int) -> None:
        """Report only food actually eaten, not pellets merely dropped."""
        emit_activity_event("orca.fed", {"count": count})

    def record_fed(self, orca_id: str, food_type: str) -> None:
        emit_activity_event(
            "orca.fed",
            {"orca_id": orca_id, "food_type": food_type},
        )

    def record_cuddled(self, orca_id: str, cuddle_type: str) -> None:
        emit_activity_event(
            "orca.cuddled",
            {"orca_id": orca_id, "cuddle_type": cuddle_type},
        )

    def record_acrobatics(self, orca_id: str, trick_type: str) -> None:
        emit_activity_event(
            "orca.acrobatics_performed",
            {"orca_id": orca_id, "trick_type": trick_type},
        )

    def record_song_completed(self, notes_count: int) -> None:
        emit_activity_event(
            "orca.song_completed",
            {"notes_count": notes_count},
        )

    def record_fact_discovered(self, fact_id: str) -> None:
        emit_activity_event(
            "orca.fact_discovered",
            {"fact_id": fact_id},
        )
