"""Platform event publishing and preferences storage for Nanna delle Nuvolette."""

from __future__ import annotations

import json
from typing import Any, Final, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .cloud_content import VALID_BLANKET_IDS
else:
    from cloud_content import VALID_BLANKET_IDS


STORAGE_KEY: Final[str] = "nanna_delle_nuvolette.preferences.v1"
EVENT_REST_COMPLETED: Final[str] = "cloud.rest_completed"

DEFAULT_BLANKET_IDS: Final[tuple[str, str, str]] = ("rose", "amber", "mint")


class GreiaCloudEvents:
    """Safe emission of rest completion event."""

    def rest_completed(self, session_id: str, payload: dict[str, Any]) -> None:
        """Emit cloud.rest_completed when all 3 clouds are asleep."""
        try:
            emit_activity_event(EVENT_REST_COMPLETED, session_id=session_id, payload=payload)
        except Exception:
            pass


class GreiaCloudStorage:
    """Persistence for favorite blankets across nights."""

    def __init__(self, storage=None, key: str = STORAGE_KEY) -> None:
        self._storage = storage if storage is not None else get_storage()
        self._key = key

    def load_preferences(self) -> tuple[str, str, str]:
        try:
            raw = self._storage.kv_get(self._key)
            if not raw:
                return DEFAULT_BLANKET_IDS

            data = json.loads(raw)
            if not isinstance(data, dict):
                return DEFAULT_BLANKET_IDS

            b_ids = data.get("blanket_ids")
            if not isinstance(b_ids, list) or len(b_ids) != 3:
                return DEFAULT_BLANKET_IDS

            sanitized: list[str] = []
            for b in b_ids:
                if isinstance(b, str) and b in VALID_BLANKET_IDS:
                    sanitized.append(b)
                else:
                    return DEFAULT_BLANKET_IDS

            return (sanitized[0], sanitized[1], sanitized[2])
        except Exception:
            return DEFAULT_BLANKET_IDS

    def save_preferences(self, blanket_ids: Sequence[str]) -> bool:
        if len(blanket_ids) != 3:
            return False

        for b in blanket_ids:
            if b not in VALID_BLANKET_IDS:
                return False

        try:
            payload = {"blanket_ids": list(blanket_ids)}
            raw = json.dumps(payload, ensure_ascii=False)
            self._storage.kv_set(self._key, raw)
            return True
        except Exception:
            return False
