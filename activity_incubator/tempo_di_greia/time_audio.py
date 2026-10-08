"""Cached, localized prerecorded audio transport for My Time.

The platform resource catalogue resolves semantic paths. This adapter is
process-local playback only; it neither generates voices nor owns system audio.
"""
from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.localization import LocalizationError, LocalizedResources

if __package__:
    from .time_speech import SPEECH_CUES
else:
    from time_speech import SPEECH_CUES


class LocalTimeSpeechTransport:
    """One voice channel; decode at most one copy of each semantic cue.

    The small selected-locale catalogue is indexed once during composition.
    Actual sound decoding is deferred until after the Activity's first frame
    has been presented and TimeSpeech requests its first utterance.
    """

    def __init__(self, resources: LocalizedResources) -> None:
        self._paths: dict[str, Path] = {}
        self._clips: dict[str, pygame.mixer.Sound] = {}
        self._failed: set[str] = set()
        self._channel: pygame.mixer.Channel | None = None
        if pygame.mixer.get_init() is None:
            return
        try:
            # The Activity has its own process and mixer, not the Shell's.
            self._channel = pygame.mixer.Channel(0)
        except pygame.error:
            return
        for cue in SPEECH_CUES:
            try:
                source = resources.audio_cue(cue, allow_fallback=False).path
            except LocalizationError:
                continue
            if source.is_file():
                self._paths[cue] = source

    def has_clip(self, cue: str) -> bool:
        return (
            self._channel is not None
            and cue in self._paths
            and cue not in self._failed
        )

    def play(self, cue: str) -> bool:
        if not self.has_clip(cue):
            return False
        assert self._channel is not None
        try:
            clip = self._clips.get(cue)
            if clip is None:
                clip = pygame.mixer.Sound(str(self._paths[cue]))
                # Each cue is loaded once, at most |SPEECH_CUES| short clips.
                self._clips[cue] = clip
            self._channel.play(clip)
            return True
        except (pygame.error, OSError):
            # A corrupt/unsupported clip must not leave a fake replay target.
            self._failed.add(cue)
            self._clips.pop(cue, None)
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
