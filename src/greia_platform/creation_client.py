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
class CreationPickerReply:
    """A non-blocking Shell picker result; an Activity never sees library IDs."""

    state: str
    selection_token: str | None = None


@dataclass(frozen=True, slots=True)
class ActivityCreationsClient:
    """Narrow runtime API: publish an own file; receive a picked immutable copy."""

    storage_session: ActivityStorageClient

    def publish_private_file(
        self, filename: str, *, media_type: str, role: str, title: str = ""
    ) -> dict[str, Any]:
        response, _ = self.storage_session.creation_exchange(
            "creations.publish_private",
            filename=filename,
            media_type=media_type,
            role=role,
            title=title,
        )
        return self._record(response)

    def request_selection(
        self, *, media_types: tuple[str, ...], roles: tuple[str, ...] = ()
    ) -> str:
        """Ask the trusted Shell to offer a picker; never enumerate records."""
        if not isinstance(media_types, tuple) or not media_types:
            raise ValueError("explicit non-empty media types required")
        if not isinstance(roles, tuple):
            raise ValueError("semantic roles must be a tuple")
        response, _ = self.storage_session.creation_exchange(
            "creations.request_selection",
            media_types=list(media_types),
            roles=list(roles),
        )
        request_id = response.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise StorageClientError("creation broker did not issue a picker request")
        return request_id

    def poll_selection(self, request_id: str) -> CreationPickerReply:
        """Poll without blocking a Pygame frame for a human choice."""
        response, _ = self.storage_session.creation_exchange(
            "creations.poll_selection", request_id=request_id
        )
        state = response.get("state")
        token = response.get("selection_token")
        if state not in ("pending", "ready", "cancelled"):
            raise StorageClientError("creation broker returned an invalid picker state")
        if state == "ready" and (not isinstance(token, str) or not token):
            raise StorageClientError("ready picker result lacks a selection handle")
        if state != "ready" and token is not None:
            raise StorageClientError("inactive picker unexpectedly carried a handle")
        return CreationPickerReply(state, token if isinstance(token, str) else None)

    def cancel_selection(self, request_id: str) -> bool:
        response, _ = self.storage_session.creation_exchange(
            "creations.cancel_selection", request_id=request_id
        )
        cancelled = response.get("cancelled")
        if not isinstance(cancelled, bool):
            raise StorageClientError("invalid picker cancellation response")
        return cancelled

    def import_selected(self, selection_token: str) -> CreationTransfer:
        response, payload = self.storage_session.creation_exchange(
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
