"""Services and platform event integration for Il Giardino dei Numeri."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

from greia_platform.activity_api import emit_activity_event, get_storage

STORAGE_KEY: Final[str] = "giardino_dei_numeri.progress.v1"


@dataclass
class GiardinoStorageState:
    total_counted: int = 0
    baskets_filled: int = 0
    highest_count: int = 3


class GiardinoServices:
    """Manages event publishing and persistence for toddler counting."""

    def emit_event(self, event_id: str, payload: dict | None = None) -> None:
        """Safely report a pedagogical milestone/completion event to Greia."""
        try:
            emit_activity_event(event_id, payload or {})
        except Exception:
            pass

    def load_state(self) -> GiardinoStorageState:
        try:
            storage = get_storage()
            if storage is None:
                return GiardinoStorageState()
            raw = storage.kv_get(STORAGE_KEY, {})
            if not isinstance(raw, dict):
                return GiardinoStorageState()
            return GiardinoStorageState(
                total_counted=int(raw.get("total_counted", 0)),
                baskets_filled=int(raw.get("baskets_filled", 0)),
                highest_count=int(raw.get("highest_count", 3)),
            )
        except Exception:
            return GiardinoStorageState()

    def save_state(self, state: GiardinoStorageState) -> None:
        try:
            storage = get_storage()
            if storage is None:
                return
            storage.kv_set(STORAGE_KEY, asdict(state))
        except Exception:
            pass
