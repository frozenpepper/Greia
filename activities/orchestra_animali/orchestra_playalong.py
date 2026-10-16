"""Play along with a saved recording or song from My Creations.

``PlayAlong`` owns the whole backing-track flow that Orchestra offers on its
stage: ask the trusted picker for an ``audio/wav`` Creation (a Voice Story,
a Teatrino show soundtrack, a song), validate and snapshot it privately
through ``BackingTrackRepository`` before it replaces the active track, play
or pause it on the reserved mixer channel, and report ``concert.performed``
only when a track ends naturally after the child played along.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
from typing import Any

if __package__:
    from .orchestra_audio import BackingTrackPlayer, ImportedBackingTrack
    from .orchestra_backing import (
        SUPPORTED_BACKING_ROLES,
        BackingTrackRecord,
        BackingTrackRepository,
        BackingTrackStoreError,
    )
else:  # pragma: no cover - runtime/script fallback
    from orchestra_audio import BackingTrackPlayer, ImportedBackingTrack
    from orchestra_backing import (
        SUPPORTED_BACKING_ROLES,
        BackingTrackRecord,
        BackingTrackRepository,
        BackingTrackStoreError,
    )

POLL_SECONDS = 0.12
FEEDBACK_SECONDS = 2.0


class PlayAlong:
    """Backing-track import, persistence and playback for one Orchestra run.

    ``import_state`` is ``""`` (idle), ``"pending"`` (picker open),
    ``"imported"`` or ``"error"`` (shown briefly on the import button).
    ``on_concert(live_inputs)`` fires once when a played-along track ends.
    """

    def __init__(
        self,
        *,
        creations: Any | None,
        store: BackingTrackRepository | Any | None,
        player: BackingTrackPlayer | Any | None = None,
        on_concert: Callable[[int], object] | None = None,
    ) -> None:
        self.creations = creations
        self.store = store
        self.player = player if player is not None else BackingTrackPlayer()
        self.on_concert = on_concert
        self.record: BackingTrackRecord | None = None
        self.request_id: str | None = None
        self.next_poll = 0.0
        self.import_state = ""
        self.feedback_until = 0.0
        self.notes_played = 0

    # -- state ----------------------------------------------------------------

    @property
    def can_import(self) -> bool:
        return self.creations is not None and self.store is not None

    @property
    def has_track(self) -> bool:
        return self.player.track is not None

    @property
    def state(self) -> str:
        return self.player.state

    @property
    def playing(self) -> bool:
        return self.player.state == "playing"

    # -- persistence ------------------------------------------------------------

    def load_saved(self) -> bool:
        """Restore the privately saved track (silently ignore a broken one)."""

        if self.store is None:
            return False
        try:
            loaded = self.store.load()
        except BackingTrackStoreError:
            return False
        if loaded is None:
            return False
        record, payload = loaded
        try:
            track = ImportedBackingTrack.from_wav(payload)
        except ValueError:
            return False
        if abs(track.duration_seconds - record.duration_seconds) > 0.05:
            return False
        self.record = record
        self.player.load(track)
        return True

    # -- picker -------------------------------------------------------------------

    def request(self, now: float) -> None:
        if not self.can_import or self.request_id is not None:
            return
        # The trusted picker owns audio preview while visible. Never let an
        # Orchestra backing track compete with Play/Pause/Replay in the picker.
        self.player.stop()
        self.notes_played = 0
        try:
            request_id = self.creations.request_selection(
                media_types=("audio/wav",),
                roles=("narration", "song", "music"),
            )
        except (RuntimeError, ValueError, OSError):
            self._feedback("error", now)
            return
        self.request_id = request_id
        self.import_state = "pending"
        self.next_poll = now + POLL_SECONDS

    def poll(self, now: float) -> bool:
        """Advance the picker request; True when the visible state changed."""

        request_id = self.request_id
        if request_id is None or self.creations is None or now < self.next_poll:
            return False
        self.next_poll = now + POLL_SECONDS
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.request_id = None
            self._feedback("error", now)
            return True
        if result.state == "pending":
            return False
        self.request_id = None
        if result.state == "cancelled":
            self.import_state = ""
            return True
        token = result.selection_token
        if (
            result.state != "ready"
            or not isinstance(token, str)
            or not token
            or not self.accept(token)
        ):
            self._feedback("error", now)
            return True
        self._feedback("imported", now)
        return True

    def accept(self, selection_token: str) -> bool:
        """Validate, persist, then activate the chosen track (in that order)."""

        if self.creations is None or self.store is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            role = transfer.record.get("role")
            if (
                transfer.record.get("media_type") != "audio/wav"
                or role not in SUPPORTED_BACKING_ROLES
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256") != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected backing track failed integrity validation")
            track = ImportedBackingTrack.from_wav(payload)
            title_raw = transfer.record.get("title", "")
            title = title_raw if isinstance(title_raw, str) else ""
            record = self.store.save(
                track.wav_bytes,
                role=role,
                title=title,
                duration_seconds=track.duration_seconds,
            )
        except (BackingTrackStoreError, RuntimeError, ValueError, OSError):
            return False
        self.record = record
        self.player.load(track)
        self.notes_played = 0
        return True

    # -- playback -------------------------------------------------------------------

    def toggle(self, now: float) -> str:
        previous = self.player.state
        state = self.player.toggle()
        if state == "playing" and previous == "ready":
            self.notes_played = 0
        elif state == "error":
            self._feedback("error", now)
        return state

    def note_played(self) -> None:
        if self.playing:
            self.notes_played += 1

    def update(self, now: float) -> bool:
        """Per-frame upkeep; True when something visible changed."""

        changed = self.poll(now)
        if self.import_state and self.import_state != "pending" and now >= self.feedback_until:
            self.import_state = ""
            changed = True
        if self.player.refresh():
            if self.notes_played > 0 and self.on_concert is not None:
                self.on_concert(self.notes_played)
            self.notes_played = 0
            changed = True
        return changed

    def stop(self) -> None:
        self.player.stop()

    def _feedback(self, state: str, now: float) -> None:
        self.import_state = state
        self.feedback_until = now + FEEDBACK_SECONDS


__all__ = ["PlayAlong"]
