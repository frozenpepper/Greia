"""Greia persistence and event adapters for My Cute Pet.

The pet lives under the historical key ``cucciolo_mio.state.v3``. Payload
schema 4 stores the adopted species, the picture name, the ladder rung, the
number of finished days and of cares given, and the old accessory choice
(kept so nothing a child picked is lost). A pre-rework payload (no
``schema_version``: species cat/bunny/puppy plus care meters) migrates
forward: its species maps onto the library pets and is pre-selected on the
adopt screen; the meters have no meaning any more and are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .cucciolo_content import LEGACY_SPECIES, MAX_LEVEL, NAMES_BY_ID, SPECIES_BY_ID, STORAGE_KEY
else:
    from cucciolo_content import LEGACY_SPECIES, MAX_LEVEL, NAMES_BY_ID, SPECIES_BY_ID, STORAGE_KEY

SCHEMA_VERSION = 4
MAX_COUNT = 1_000_000
LEGACY_ACCESSORIES = ("bow", "crown", "glasses", "party_hat", "none")


@dataclass(frozen=True, slots=True)
class PetProfile:
    """The child's pet. ``adopted`` once both a species and a name are chosen."""

    species: str | None = None
    name: str | None = None
    level: int = 0
    days: int = 0
    cares: int = 0
    accessory: str | None = None

    @property
    def adopted(self) -> bool:
        return self.species is not None and self.name is not None


class ProgressPort(Protocol):
    def load(self) -> PetProfile: ...
    def save(self, profile: PetProfile) -> None: ...


class EventPort(Protocol):
    def cared(self, event_id: str, session_id: str, payload: dict[str, Any]) -> None: ...
    def day_completed(self, session_id: str, payload: dict[str, Any]) -> None: ...


def _int(value: object, default: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(low, min(high, value))


def _choice(value: object, allowed) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def parse_profile(raw: object) -> PetProfile:
    """Bounded parse of any stored payload (current, legacy or corrupt)."""

    if not isinstance(raw, dict):
        return PetProfile()
    accessory = _choice(raw.get("accessory"), LEGACY_ACCESSORIES)
    if raw.get("schema_version") != SCHEMA_VERSION:
        legacy = raw.get("species")
        species = LEGACY_SPECIES.get(legacy) if isinstance(legacy, str) else None
        return PetProfile(species=species, accessory=accessory)
    return PetProfile(
        species=_choice(raw.get("species"), SPECIES_BY_ID),
        name=_choice(raw.get("name"), NAMES_BY_ID),
        level=_int(raw.get("level"), 0, 0, MAX_LEVEL),
        days=_int(raw.get("days"), 0, 0, MAX_COUNT),
        cares=_int(raw.get("cares"), 0, 0, MAX_COUNT),
        accessory=accessory,
    )


def profile_payload(profile: PetProfile) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "species": profile.species if profile.species in SPECIES_BY_ID else None,
        "name": profile.name if profile.name in NAMES_BY_ID else None,
        "level": max(0, min(MAX_LEVEL, int(profile.level))),
        "days": max(0, min(MAX_COUNT, int(profile.days))),
        "cares": max(0, min(MAX_COUNT, int(profile.cares))),
    }
    if profile.accessory in LEGACY_ACCESSORIES:
        payload["accessory"] = profile.accessory
    return payload


class GreiaPetProgress:
    """Map the pet onto profile-scoped Greia Storage (fail-soft)."""

    def __init__(self, storage=None) -> None:
        if storage is None:
            try:
                storage = get_storage()
            except Exception:
                storage = None
        self._storage = storage

    def load(self) -> PetProfile:
        if self._storage is None:
            return PetProfile()
        try:
            return parse_profile(self._storage.kv_get(STORAGE_KEY))
        except Exception:
            return PetProfile()

    def save(self, profile: PetProfile) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, profile_payload(profile))
        except Exception:
            return


class GreiaPetEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def cared(self, event_id: str, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(
                event_id,
                payload,
                idempotency_key=f"cucciolo-mio:{session_id}:n{payload.get('index', 0)}",
            )
        except Exception:
            return

    def day_completed(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(
                "pet.tucked_in",
                payload,
                idempotency_key=f"cucciolo-mio:{session_id}",
            )
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaPetEvents",
    "GreiaPetProgress",
    "PetProfile",
    "ProgressPort",
    "SCHEMA_VERSION",
    "parse_profile",
    "profile_payload",
]
