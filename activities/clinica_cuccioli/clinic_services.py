"""Greia Storage and event adapters for Little Vet Clinic.

Saves stay under the original key ``clinica_cuccioli.progress.v2``. Older
saves hold only ``{"stars": n}`` (lifetime patients helped); they load
unchanged and start at level 1. New saves add ``level`` and ``days`` in the
same record, so nothing a child earned is ever lost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .clinic_content import MAX_LEVEL, MIN_LEVEL
    from .clinic_model import CareResult
else:
    from clinic_content import MAX_LEVEL, MIN_LEVEL
    from clinic_model import CareResult


STORAGE_KEY = "clinica_cuccioli.progress.v2"
SAVE_VERSION = 3
_MAX_COUNT = 1_000_000


@dataclass(frozen=True, slots=True)
class ClinicProgressState:
    stars: int = 0  # lifetime patients helped
    level: int = MIN_LEVEL
    days: int = 0


class ClinicProgressPort(Protocol):
    """Durable progress seam consumed by the Activity application."""

    def load(self) -> ClinicProgressState: ...

    def save(self, state: ClinicProgressState) -> None: ...


class ClinicEventPort(Protocol):
    """Greia educational/progression event seam consumed by the Activity."""

    def treatment_applied(self, result: CareResult, *, level: int) -> None: ...

    def patient_healed(self, result: CareResult, *, stars: int, level: int) -> None: ...

    def day_completed(self, summary: dict[str, object]) -> None: ...


def _count(value: Any, default: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(0, min(_MAX_COUNT, value))


class GreiaClinicProgress:
    """Profile-scoped durable progress through Greia Storage only."""

    def __init__(self, storage: Any | None = None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def load(self) -> ClinicProgressState:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return ClinicProgressState()
        if not isinstance(raw, dict):
            return ClinicProgressState()
        level = raw.get("level", MIN_LEVEL)
        if isinstance(level, bool) or not isinstance(level, int):
            level = MIN_LEVEL
        return ClinicProgressState(
            stars=_count(raw.get("stars")),
            level=max(MIN_LEVEL, min(MAX_LEVEL, level)),
            days=_count(raw.get("days")),
        )

    def save(self, state: ClinicProgressState) -> None:
        record = {
            "version": SAVE_VERSION,
            "stars": _count(state.stars),
            "level": max(MIN_LEVEL, min(MAX_LEVEL, int(state.level))),
            "days": _count(state.days),
        }
        try:
            self._storage.kv_set(STORAGE_KEY, record)
        except Exception:
            # Progress persistence must not strand a child in a broken
            # interaction when the development storage seam is absent.
            pass


class GreiaClinicEvents:
    """Publish only event IDs declared by ``activity.toml``."""

    def treatment_applied(self, result: CareResult, *, level: int) -> None:
        emit_activity_event(
            "vet.treatment_applied",
            {
                "patient": result.case.species_id,
                "ailment": result.case.ailment_id.value,
                "tool": result.tool.value,
                "step": result.step_index + 1,
                "level": level,
            },
        )

    def patient_healed(self, result: CareResult, *, stars: int, level: int) -> None:
        emit_activity_event(
            "vet.patient_healed",
            {
                "patient": result.case.species_id,
                "ailment": result.case.ailment_id.value,
                "stars": stars,
                "level": level,
            },
        )

    def day_completed(self, summary: dict[str, object]) -> None:
        emit_activity_event("vet.clinic_day_completed", dict(summary))


__all__ = [
    "ClinicEventPort",
    "ClinicProgressPort",
    "ClinicProgressState",
    "GreiaClinicEvents",
    "GreiaClinicProgress",
    "STORAGE_KEY",
]
