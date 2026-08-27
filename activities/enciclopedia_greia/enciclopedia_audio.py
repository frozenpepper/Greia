"""Fail-soft prerecorded voice playback for the encyclopedia.

The child device never synthesizes narration. This owner resolves semantic
localized cues to packaged OGG/WAV assets when they exist and otherwise remains
silent until the independently produced recordings are integrated.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pygame

from greia_platform.localization import LocalizedResources


class EncyclopediaAudio:
    MAX_CACHED_SOUNDS = 32

    def __init__(self, resources: LocalizedResources) -> None:
        self._resources = resources
        self._cache: OrderedDict[Path, pygame.mixer.Sound] = OrderedDict()
        self._channel: pygame.mixer.Channel | None = None

    def play(self, cue_id: str) -> bool:
        try:
            cue = self._resources.audio_cue(cue_id)
        except Exception:
            return False
        sound = self._sound(cue.path)
        if sound is None:
            return False
        channel = self._voice_channel()
        if channel is None:
            return False
        try:
            channel.play(sound)
        except pygame.error:
            return False
        return True

    def stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except pygame.error:
                pass

    def close(self) -> None:
        self.stop()
        self._cache.clear()
        self._channel = None

    def _voice_channel(self) -> pygame.mixer.Channel | None:
        if self._channel is not None:
            return self._channel
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            self._channel = pygame.mixer.Channel(3)
        except pygame.error:
            return None
        return self._channel

    def _sound(self, path: Path) -> pygame.mixer.Sound | None:
        cached = self._cache.get(path)
        if cached is not None:
            self._cache.move_to_end(path)
            return cached
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            sound = pygame.mixer.Sound(str(path))
        except (OSError, pygame.error):
            return None
        self._cache[path] = sound
        self._cache.move_to_end(path)
        while len(self._cache) > self.MAX_CACHED_SOUNDS:
            self._cache.popitem(last=False)
        return sound
