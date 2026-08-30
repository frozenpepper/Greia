"""Deduped focus-name audio for Encyclopedia.

Tracks the last announced focus cue per page so that repeated
POINTER_MOVE events over the same target do not continuously restart
the same name cue. Once real prerecorded cues are integrated, this
prevents spam.

The helper is intentionally tiny and page-local: each page owns one
instance, no global state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FocusAudioTracker:
    """Remember the last announced focus cue id."""

    _last_cue: str | None = None

    def should_announce(self, cue_id: str | None) -> bool:
        if not cue_id:
            return False
        if cue_id == self._last_cue:
            return False
        return True

    def mark_announced(self, cue_id: str | None) -> None:
        if cue_id:
            self._last_cue = cue_id

    def clear(self) -> None:
        self._last_cue = None

    def announce_once(self, audio: object, cue_id: str | None) -> bool:
        """Announce only if cue_id differs from last, return True if played."""
        if not self.should_announce(cue_id):
            return False
        try:
            ok = bool(audio.play(cue_id))  # type: ignore[union-attr]
        except Exception:
            return False
        if ok:
            self.mark_announced(cue_id)
        return ok
