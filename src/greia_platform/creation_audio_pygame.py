"""On-demand audible WAV previews for the trusted child picker/viewer."""
from __future__ import annotations

import io
import time
from typing import Any

from .creation_gallery import GalleryError


class PygameRecordingPreview:
    """One interruptible channel with real pause, resume, replay and progress."""

    MAX_WAV_BYTES = 16 * 1024 * 1024

    def __init__(self) -> None:
        self._sound: Any = None
        self._channel: Any = None
        self._started_at = 0.0
        self._paused_at: float | None = None

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

    def pause(self) -> None:
        if self._channel is None or self._paused_at is not None:
            return
        try:
            self._channel.pause()
        except Exception as exc:
            self.stop()
            raise GalleryError("audio output is unavailable") from exc
        self._paused_at = time.monotonic()

    def resume(self) -> None:
        if self._channel is None or self._paused_at is None:
            return
        try:
            self._channel.unpause()
        except Exception as exc:
            self.stop()
            raise GalleryError("audio output is unavailable") from exc
        self._started_at += time.monotonic() - self._paused_at
        self._paused_at = None

    def is_playing(self) -> bool:
        if self._channel is None:
            return False
        if self._paused_at is not None:
            return True
        try:
            return bool(self._channel.get_busy())
        except Exception:  # A device may disappear during Activity/profile exit.
            return False

    def progress(self, duration_seconds: float) -> float:
        if self._channel is None or duration_seconds <= 0:
            return 0.0
        now = self._paused_at if self._paused_at is not None else time.monotonic()
        return max(0.0, min(1.0, (now - self._started_at) / duration_seconds))

    def stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except Exception:  # Device removal must not block cleanup.
                pass
        self._channel = None
        self._sound = None
        self._paused_at = None
        self._started_at = 0.0
