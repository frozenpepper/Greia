"""Activity-side typed creation transfer over the existing storage session.

There is deliberately no API for listing, deleting, choosing or reading an
arbitrary library ID. A platform-owned child picker issues selection handles;
Activities can import only a handle the child selected for this session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .storage_client import ActivityStorageClient, StorageClientError


@dataclass(frozen=True, slots=True)
class CreationTransfer:
    """A read-selected artifact snapshot; import it into a private project."""

    record: dict[str, Any]
    payload: bytes


@dataclass(frozen=True, slots=True)
class ActivityCreationsClient:
    """Narrow runtime API: publish an own file; receive a picked immutable copy."""

    storage_session: ActivityStorageClient

    def publish_private_file(
        self, filename: str, *, media_type: str, role: str, title: str = ""
    ) -> dict[str, Any]:
        response, _ = self.storage_session._request(
            "creations.publish_private",
            filename=filename,
            media_type=media_type,
            role=role,
            title=title,
        )
        return self._record(response)

    def import_selected(self, selection_token: str) -> CreationTransfer:
        response, payload = self.storage_session._request(
            "creations.import_selected", selection_token=selection_token
        )
        return CreationTransfer(self._record(response), payload)

    @staticmethod
    def _record(response: dict[str, object]) -> dict[str, Any]:
        raw = response.get("record")
        if not isinstance(raw, dict):
            raise StorageClientError("creation broker returned no artifact descriptor")
        required = ("creation_id", "producer_id", "media_type", "role", "created_at", "sha256")
        if not all(isinstance(raw.get(key), str) for key in required):
            raise StorageClientError("creation broker returned an invalid artifact descriptor")
        if not isinstance(raw.get("content_bytes"), int):
            raise StorageClientError("creation broker returned an invalid artifact size")
        return raw
