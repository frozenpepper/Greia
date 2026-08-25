"""Platform event publishing and durable sky progress for Stelle Incantate.

The Activity only reports truthful semantic facts; Greia owns Stars, badges
and achievement truth. Durable progress is the bounded set of completed
constellation ids stored through the approved Activity storage API.
"""

from __future__ import annotations

import json
from typing import Any, Final, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .sky_content import CONSTELLATION_ORDER
else:
    from sky_content import CONSTELLATION_ORDER


STORAGE_KEY: Final[str] = "stelle_incantate.progress.v1"
EVENT_CONSTELLATION_COMPLETED: Final[str] = "constellation.completed"
EVENT_FACT_OPENED: Final[str] = "curiosity.fact_opened"


class GreiaSkyEvents:
    """Safe emission of the Activity's declared semantic facts."""

    def constellation_completed(
        self,
        session_id: str,
        constellation_id: str,
        star_count: int,
    ) -> None:
        """Emit ``constellation.completed`` once per figure per session."""

        try:
            emit_activity_event(
                EVENT_CONSTELLATION_COMPLETED,
                idempotency_key=f"{session_id}-{constellation_id}",
                payload={
                    "session_id": session_id,
                    "constellation_id": constellation_id,
                    "star_count": star_count,
                },
            )
        except Exception:
            pass

    def fact_opened(self, session_id: str, constellation_id: str) -> None:
        """Emit ``curiosity.fact_opened`` once per figure per session."""

        try:
            emit_activity_event(
                EVENT_FACT_OPENED,
                idempotency_key=f"{session_id}-{constellation_id}",
                payload={
                    "session_id": session_id,
                    "constellation_id": constellation_id,
                },
            )
        except Exception:
            pass


class GreiaSkyStorage:
    """Bounded durable progress: the set of completed constellation ids."""

    def __init__(self, storage=None, key: str = STORAGE_KEY) -> None:
        self._storage = storage if storage is not None else get_storage()
        self._key = key

    def load_completed(self) -> frozenset[str]:
        try:
            raw = self._storage.kv_get(self._key)
            if not raw:
                return frozenset()
            data = json.loads(raw)
            if not isinstance(data, dict):
                return frozenset()
            ids = data.get("completed_ids")
            if not isinstance(ids, list):
                return frozenset()
            valid = frozenset(CONSTELLATION_ORDER)
            return frozenset(
                constellation_id
                for constellation_id in ids
                if isinstance(constellation_id, str) and constellation_id in valid
            )
        except Exception:
            return frozenset()

    def save_completed(self, completed_ids: Sequence[str]) -> bool:
        unique = sorted(set(completed_ids) & set(CONSTELLATION_ORDER))
        try:
            payload = json.dumps(
                {"completed_ids": unique},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            self._storage.kv_set(self._key, payload)
            return True
        except Exception:
            return False
