"""Teatrino's side of My Creations (P4 pictures, P5 narration, poster share).

The trusted Shell owns the picker; the theatre only asks for a selection,
polls without blocking a frame, and imports exactly the handle the child
chose, verifying media type, role and digest before anything on stage
changes. Publishing is deliberate (the share button) and deduplicated.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib

import pygame

from greia_platform.pygame_png import PygamePngError, decode_png_surface

if __package__:
    from .teatrino_audio import ImportedNarrationTrack
    from .teatrino_content import (
        MAX_RECORDING_SECONDS,
        POSTER_FILE,
        POSTER_ROLE,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
else:
    from teatrino_audio import ImportedNarrationTrack
    from teatrino_content import (
        MAX_RECORDING_SECONDS,
        POSTER_FILE,
        POSTER_ROLE,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )

PICKER_POLL_SECONDS = 0.12


class CreationsBridge:
    """Nonblocking picker requests and verified imports for the theatre.

    One request at a time: a picture request never competes with a
    narration request. Results are delivered through the callbacks; a
    cancelled picker changes nothing.
    """

    def __init__(
        self,
        creations,
        *,
        clock: Callable[[], float],
        on_backdrop: Callable[[bytes, pygame.Surface], object],
        on_narration: Callable[[ImportedNarrationTrack], object],
        on_error: Callable[[], object],
    ) -> None:
        self.creations = creations
        self._clock = clock
        self._on_backdrop = on_backdrop
        self._on_narration = on_narration
        self._on_error = on_error
        self.backdrop_request: str | None = None
        self.narration_request: str | None = None
        self.backdrop_state = ""
        self.narration_state = ""
        self._next_poll = 0.0
        self._last_shared_digest: str | None = None

    @property
    def available(self) -> bool:
        return self.creations is not None

    @property
    def busy(self) -> bool:
        return self.backdrop_request is not None or self.narration_request is not None

    # -- requests ------------------------------------------------------------

    def request_backdrop(self) -> bool:
        if self.creations is None or self.busy:
            return False
        try:
            self.backdrop_request = self.creations.request_selection(media_types=("image/png",))
        except (RuntimeError, ValueError, OSError):
            self.backdrop_state = "error"
            self._on_error()
            return False
        self.backdrop_state = "pending"
        self._next_poll = self._clock() + PICKER_POLL_SECONDS
        return True

    def request_narration(self) -> bool:
        if self.creations is None or self.busy:
            return False
        try:
            self.narration_request = self.creations.request_selection(
                media_types=("audio/wav",), roles=("narration",)
            )
        except (RuntimeError, ValueError, OSError):
            self.narration_state = "error"
            self._on_error()
            return False
        self.narration_state = "pending"
        self._next_poll = self._clock() + PICKER_POLL_SECONDS
        return True

    # -- polling ---------------------------------------------------------------

    def poll(self, now: float) -> None:
        if not self.busy or self.creations is None or now < self._next_poll:
            return
        self._next_poll = now + PICKER_POLL_SECONDS
        if self.backdrop_request is not None:
            self._poll_one("backdrop", self.backdrop_request, self.accept_backdrop)
        elif self.narration_request is not None:
            self._poll_one("narration", self.narration_request, self.accept_narration)

    def _poll_one(self, kind: str, request_id: str, accept: Callable[[str], bool]) -> None:
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self._settle(kind, "error")
            self._on_error()
            return
        if result.state == "pending":
            return
        if result.state == "cancelled":
            self._settle(kind, "")
            return
        token = result.selection_token
        if result.state != "ready" or not isinstance(token, str) or not token or not accept(token):
            self._settle(kind, "error")
            self._on_error()
            return
        self._settle(kind, "imported")

    def _settle(self, kind: str, state: str) -> None:
        if kind == "backdrop":
            self.backdrop_request = None
            self.backdrop_state = state
        else:
            self.narration_request = None
            self.narration_state = state

    # -- verified imports ---------------------------------------------------------

    def accept_backdrop(self, selection_token: str) -> bool:
        if self.creations is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "image/png"
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256") != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected backdrop failed integrity validation")
            surface = decode_png_surface(payload, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
        except (PygamePngError, RuntimeError, ValueError, OSError):
            return False
        self._on_backdrop(payload, surface)
        return True

    def accept_narration(self, selection_token: str) -> bool:
        if self.creations is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "audio/wav"
                or transfer.record.get("role") != "narration"
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256") != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected narration failed integrity validation")
            track = ImportedNarrationTrack.from_wav(payload, max_duration_seconds=MAX_RECORDING_SECONDS)
        except (RuntimeError, ValueError, OSError):
            return False
        self._on_narration(track)
        return True

    # -- publish -------------------------------------------------------------------

    def publish_poster(self, payload: bytes, write_private: Callable[[str, bytes], bool]) -> bool:
        """Publish one poster PNG as a ``picture`` creation (once per content)."""

        if self.creations is None:
            return False
        digest = hashlib.sha256(payload).hexdigest()
        if digest == self._last_shared_digest:
            return True
        if not write_private(POSTER_FILE, payload):
            return False
        try:
            self.creations.publish_private_file(POSTER_FILE, media_type="image/png", role=POSTER_ROLE)
        except (RuntimeError, ValueError, OSError):
            return False
        self._last_shared_digest = digest
        return True


__all__ = ["CreationsBridge", "PICKER_POLL_SECONDS"]
