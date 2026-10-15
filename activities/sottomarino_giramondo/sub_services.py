"""Sottomarino Giramondo — profile-scoped progress through Greia Storage."""

from __future__ import annotations

from greia_platform.activity_api import get_storage

try:
    from sub_model import SubmarineLog
except ImportError:
    from .sub_model import SubmarineLog

STORAGE_KEY = "submarine.log"


class SubmarineProgressStore:
    """Load/save the captain's log (stars, species met); never raises."""

    def __init__(self, key: str = STORAGE_KEY) -> None:
        self._key = key

    def load(self) -> SubmarineLog:
        storage = get_storage()
        if storage is None:
            return SubmarineLog()
        try:
            return SubmarineLog.from_payload(storage.kv_get(self._key))
        except Exception:
            return SubmarineLog()

    def save(self, log: SubmarineLog) -> bool:
        storage = get_storage()
        if storage is None:
            return False
        try:
            storage.kv_set(self._key, log.export())
            return True
        except Exception:
            # Storage may refuse writes (e.g. low disk); play must go on.
            return False
