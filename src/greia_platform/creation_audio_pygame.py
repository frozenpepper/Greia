"""On-demand audible WAV preview for trusted child selection and gallery."""
from __future__ import annotations
import io
import time
from typing import Any
from .creation_gallery import GalleryError


class PygameRecordingPreview:
    """Own one interruptible channel; no unsolicited playback/background task."""

    MAX_WAV_BYTES = 16 * 1024 * 1024

    def __init__(self) -> None:
        self._sound: Any = None
        self._channel: Any = None
        self._started_at = 0.0

    def play(self, wav_bytes: bytes) -> None:
        import pygame

        self.stop()
        if len(wav_bytes) > self.MAX_WAV_BYTES:
            raise GalleryError("recording exceeds safe preview size")
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._sound = pygame.mixer.Sound(file=io.BytesIO(wav_bytes))
            self._channel = self._sound.play()
            if self._channel is None:
                raise GalleryError("audio output is busy")
            self._started_at = time.monotonic()
        except pygame.error as exc:
            self.stop()
            raise GalleryError("audio output is unavailable") from exc

    def is_playing(self) -> bool:
        try:
            return self._channel is not None and bool(self._channel.get_busy())
        except Exception:  # Device may disappear after unplug or profile exit.
            return False

    def progress(self, duration_seconds: float) -> float:
        """Bounded progress used by the trusted picker; no background timer."""
        if not self.is_playing() or duration_seconds <= 0:
            return 0.0
        return max(0.0, min(1.0, (time.monotonic() - self._started_at) / duration_seconds))

    def stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except Exception:  # Device may disappear during session teardown.
                pass
        self._channel = None
        self._sound = None
