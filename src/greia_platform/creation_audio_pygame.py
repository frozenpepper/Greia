"""On-demand audible WAV preview for trusted child selection and gallery."""
from __future__ import annotations
import io
from typing import Any
from .creation_gallery import GalleryError


class PygameRecordingPreview:
    """Own one interruptible channel; no unsolicited playback/background task."""

    MAX_WAV_BYTES = 16 * 1024 * 1024

    def __init__(self) -> None:
        self._sound: Any = None
        self._channel: Any = None

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
        except pygame.error as exc:
            self.stop()
            raise GalleryError("audio output is unavailable") from exc

    def stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except Exception:  # Device may disappear during session teardown.
                pass
        self._channel = None
        self._sound = None
