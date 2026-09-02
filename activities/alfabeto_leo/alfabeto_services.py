"""Services and platform event integration for L'Alfabeto di Leo."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Final

from greia_platform.activity_api import emit_activity_event, get_storage

STORAGE_KEY: Final[str] = "alfabeto_leo.progress.v1"


@dataclass
class AlfabetoStorageState:
    discovered_letters: list[str] = field(default_factory=list)
    rounds_completed: int = 0


class AlfabetoServices:
    """Manages event publishing and persistence for toddler alphabet activity."""

    def emit_event(self, event_id: str, payload: dict | None = None) -> None:
        """Safely report a pedagogical milestone/completion event to Greia."""
        try:
            emit_activity_event(event_id, payload or {})
        except Exception:
            pass

    def load_state(self) -> AlfabetoStorageState:
        try:
            storage = get_storage()
            if storage is None:
                return AlfabetoStorageState()
            raw = storage.kv_get(STORAGE_KEY, {})
            if not isinstance(raw, dict):
                return AlfabetoStorageState()
            letters = raw.get("discovered_letters", [])
            return AlfabetoStorageState(
                discovered_letters=[str(x) for x in letters] if isinstance(letters, list) else [],
                rounds_completed=int(raw.get("rounds_completed", 0)),
            )
        except Exception:
            return AlfabetoStorageState()

    def save_state(self, state: AlfabetoStorageState) -> None:
        try:
            storage = get_storage()
            if storage is None:
                return
            storage.kv_set(STORAGE_KEY, asdict(state))
        except Exception:
            pass
