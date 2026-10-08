"""Cached, localized prerecorded audio transport for My Time.

The platform resource catalogue resolves semantic paths. This adapter is
process-local playback only; it neither generates voices nor owns system audio.
"""
from __future__ import annotations

import pygame

from greia_platform.localization import LocalizationError, LocalizedResources

if __package__:
    from .time_speech import SPEECH_CUES
else:
    from time_speech import SPEECH_CUES


class LocalTimeSpeechTransport:
    """One voice channel and a bounded set of reviewed package-local clips."""

    def __init__(self, resources: LocalizedResources) -> None:
        self._clips: dict[str, pygame.mixer.Sound] = {}
        self._channel: pygame.mixer.Channel | None = None
        if pygame.mixer.get_init() is None:
            return
        try:
            # This Activity executes in its own process, not the Shell mixer.
            self._channel = pygame.mixer.Channel(0)
        except pygame.error:
            return
        # Semantic instruction speech requires the selected locale;
        # the shared resolver enforces it without constraining whether an
        # author stores clips under locales/, assets/ or a shared media tree.
        for cue in SPEECH_CUES:
            try:
                source = resources.audio_cue(cue, allow_fallback=False).path
            except LocalizationError:
                continue
            if not source.is_file():
                continue
            try:
                self._clips[cue] = pygame.mixer.Sound(str(source))
            except (pygame.error, OSError):
                continue

    def has_clip(self, cue: str) -> bool:
        return self._channel is not None and cue in self._clips

    def play(self, cue: str) -> bool:
        if not self.has_clip(cue):
            return False
        assert self._channel is not None
        try:
            self._channel.play(self._clips[cue])
            return True
        except pygame.error:
            return False

    def busy(self) -> bool:
        if self._channel is None:
            return False
        try:
            return self._channel.get_busy()
        except pygame.error:
            return False

    def stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except pygame.error:
                pass


__all__ = ["LocalTimeSpeechTransport"]
