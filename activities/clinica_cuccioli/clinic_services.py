from __future__ import annotations

from typing import Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

from clinic_model import TreatmentResult


STORAGE_KEY = "clinica_cuccioli.progress.v2"


class ClinicProgressPort(Protocol):
    """Durable progress seam consumed by the Activity application."""

    def load_stars(self) -> int: ...

    def save_stars(self, stars: int) -> None: ...


class ClinicEventPort(Protocol):
    """Greia educational/progression event seam consumed by the Activity."""

    def treatment_applied(self, result: TreatmentResult) -> None: ...

    def patient_healed(self, result: TreatmentResult) -> None: ...


class GreiaClinicProgress:
    """Profile-scoped durable star persistence through Greia Storage only."""

    def __init__(self) -> None:
        self._storage = get_storage()

    def load_stars(self) -> int:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return 0
        if not isinstance(raw, dict):
            return 0
        stars = raw.get("stars", 0)
        return stars if isinstance(stars, int) and stars >= 0 else 0

    def save_stars(self, stars: int) -> None:
        if stars < 0:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, {"stars": stars})
        except Exception:
            # Progress persistence is important but must not strand a child in a
            # broken interaction state when the development storage seam is absent.
            pass


class GreiaClinicEvents:
    """Publish only event IDs declared by ``activity.toml``.

    Keeping these IDs in one adapter prevents renderer/gameplay refactors from
    silently drifting away from the manifest's progression contract.
    """

    def treatment_applied(self, result: TreatmentResult) -> None:
        emit_activity_event(
            "vet.treatment_applied",
            {
                "patient": result.patient_id,
                "tool": result.tool_id,
                "stars": result.total_stars,
            },
        )

    def patient_healed(self, result: TreatmentResult) -> None:
        emit_activity_event(
            "vet.patient_healed",
            {
                "patient": result.patient_id,
                "stars": result.total_stars,
                "session_complete": result.session_complete,
            },
        )
