"""Where a show's voice comes from (one owner for capture lifecycle).

``VoiceSource`` is the single place that opens and closes the microphone or
plays a narration chosen from My Creations while a show is recorded. It
reports a voice level (for the puppets' mouths) and hands back the WAV for
the saved show; it never decides anything about the stage or storage.
"""

from __future__ import annotations

if __package__:
    from .teatrino_audio import ImportedNarrationTrack, MicrophoneRecorder
    from .teatrino_content import MAX_RECORDING_SECONDS
else:
    from teatrino_audio import ImportedNarrationTrack, MicrophoneRecorder
    from teatrino_content import MAX_RECORDING_SECONDS


class VoiceSource:
    """Microphone on / off, or a saved narration (``imported``)."""

    ON = "on"
    OFF = "off"
    IMPORTED = "imported"

    def __init__(self, microphone: MicrophoneRecorder) -> None:
        self.microphone = microphone
        self.imported: ImportedNarrationTrack | None = None
        self.track: ImportedNarrationTrack | None = None  # the one playing now
        self._sound = None
        self._channel = None
        self.capturing = False

    @property
    def state(self) -> str:
        if self.imported is not None:
            return self.IMPORTED
        return self.ON if self.microphone.enabled else self.OFF

    def choose(self, state: str) -> None:
        """Pick microphone on/off (forgets an imported narration)."""
        self.imported = None
        self.microphone.enabled = state == self.ON

    def use_narration(self, track: ImportedNarrationTrack) -> None:
        self.imported = track

    def toggle(self) -> None:
        """Quick toggle: a saved voice goes back to the microphone."""
        if self.imported is not None:
            self.choose(self.ON)
        else:
            self.microphone.toggle()

    @property
    def limit(self) -> float:
        track = self.track if self.capturing else self.imported
        return track.duration_seconds if track is not None else MAX_RECORDING_SECONDS

    def start(self) -> bool:
        """Open the chosen source; False when a narration cannot be played."""
        self.track = self.imported
        self._sound = self._channel = None
        if self.track is not None:
            played = self.track.play()
            if played is None:
                self.track = None
                return False
            self._sound, self._channel = played
        else:
            self.microphone.start_recording()
        self.capturing = True
        return True

    def level(self, elapsed: float) -> float:
        if not self.capturing:
            return 0.0
        if self.track is not None:
            return self.track.level_at(elapsed)
        return float(self.microphone.current_volume)

    def finish(self, elapsed: float) -> bytes | None:
        """Close the source and return the show's WAV (may raise ValueError)."""
        if not self.capturing:
            return None
        self.capturing = False
        track = self.track
        self.track = None
        if track is not None:
            self._stop_channel()
            return track.trimmed(elapsed)
        return self.microphone.stop_recording()

    def abort(self) -> None:
        """Stop capture without keeping anything (Home / quit mid-show)."""
        if not self.capturing:
            self._stop_channel()
            return
        self.capturing = False
        if self.track is not None:
            self.track = None
            self._stop_channel()
            return
        try:
            self.microphone.stop_recording()
        except Exception:
            pass

    def _stop_channel(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except Exception:
                pass
        self._channel = None
        self._sound = None


__all__ = ["VoiceSource"]
