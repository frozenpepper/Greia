"""Trusted session authority for *selected* child creation exchange.

The Activity process never constructs this object. A trusted supervisor binds
its issued ActivityAuthority, validated manifest and own ActivityStorage to the
active profile's CreationLibrary. The child-facing picker will issue a single
opaque grant only *after* its trusted UI records the child's selection.

No method exposed to an Activity can browse the library, delete creations,
issue handles or read another Activity's private namespace.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from .creations import CreationLibrary, CreationRecord

if TYPE_CHECKING:
    from .activities import ActivityManifest
    from .permissions import ActivityAuthority
    from .storage import ActivityStorage


class CreationAccessDenied(PermissionError):
    """An Activity requested a capability or selected item it was not granted."""


@dataclass(frozen=True, slots=True)
class SelectedCreation:
    """A selected version, not an arbitrary library path."""

    record: CreationRecord
    payload: bytes


class CreationSessionAccess:
    """One-session grant store and guarded producer/consumer bridge.

    Selection-grant issuance is a trusted Shell/picker entrypoint, not a broker
    operation. The only child-facing operations are publish_private_file and
    import_selected; both have no profile-id parameter and cannot enumerate.
    """

    MAX_GRANTS = 8
    GRANT_SECONDS = 120.0

    def __init__(
        self,
        *,
        library: CreationLibrary,
        storage: ActivityStorage,
        manifest: ActivityManifest,
        authority: ActivityAuthority,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not session_id or authority.activity_id != manifest.activity_id:
            raise ValueError("creation session identity does not match launch authority")
        if storage.activity_id != manifest.activity_id:
            raise ValueError("creation source storage does not match Activity identity")
        self._library = library
        self._storage = storage
        self._producer_id = manifest.activity_id
        self._can_publish = frozenset(manifest.creations_produces)
        self._can_import = frozenset(manifest.creations_consumes)
        self._session_id = session_id
        self._clock = clock
        self._lock = threading.Lock()
        self._grants: dict[str, tuple[str, float]] = {}
        self._closed = False

    def _require_open(self) -> None:
        if self._closed:
            raise CreationAccessDenied("creation session has ended")

    def publish_private_file(
        self,
        *,
        filename: str,
        media_type: str,
        role: str,
        title: str = "",
    ) -> CreationRecord:
        with self._lock:
            self._require_open()
            if media_type not in self._can_publish:
                raise CreationAccessDenied("Activity cannot publish this media type")
        # The trusted ActivityStorage enforces filename/path isolation and
        # private quota. Caller may publish only its *own* private file bytes.
        payload = self._storage.file_read(filename)
        with self._lock:
            self._require_open()
            return self._library.publish(
                payload,
                producer_id=self._producer_id,
                media_type=media_type,
                role=role,
                title=title,
            )

    @property
    def consumable_media_types(self) -> frozenset[str]:
        """Trusted broker configuration, never a catalogue/read API."""
        return self._can_import

    def grant_child_selection(
        self,
        creation_id: str,
        *,
        only_media_types: frozenset[str] | None = None,
        only_roles: frozenset[str] | None = None,
    ) -> str:
        """TRUSTED PICKER ONLY; apply the active request's narrowed scope."""
        with self._lock:
            self._require_open()
            record = self._library.describe(creation_id)
            if record.media_type not in self._can_import:
                raise CreationAccessDenied("Activity cannot import the selected media type")
            if only_media_types is not None and record.media_type not in only_media_types:
                raise CreationAccessDenied("selection is outside the requested media scope")
            if only_roles is not None and record.role not in only_roles:
                raise CreationAccessDenied("selection is outside the requested semantic role")
            now = self._clock()
            self._grants = {
                token: item
                for token, item in self._grants.items()
                if item[1] > now
            }
            if len(self._grants) >= self.MAX_GRANTS:
                raise CreationAccessDenied("too many pending selections")
            token = secrets.token_urlsafe(32)
            self._grants[token] = (record.creation_id, now + self.GRANT_SECONDS)
            return token

    def import_selected(self, selection_token: str) -> SelectedCreation:
        if not isinstance(selection_token, str) or not selection_token:
            raise CreationAccessDenied("invalid creation selection handle")
        with self._lock:
            self._require_open()
            selection = self._grants.pop(selection_token, None)
            if selection is None or selection[1] <= self._clock():
                raise CreationAccessDenied("selection is absent or has expired")
            record = self._library.describe(selection[0])
            if record.media_type not in self._can_import:
                raise CreationAccessDenied("selection type is not permitted")
            payload = self._library.read(record.creation_id)
            return SelectedCreation(record, payload)

    def close(self) -> None:
        """Invalidate every selection as soon as the Activity session ends."""
        with self._lock:
            self._closed = True
            self._grants.clear()
