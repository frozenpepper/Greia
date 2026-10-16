"""Approved speech plus small synthesized effects for Colline Allegre.

Speech uses only Tito's recorded, owner-approved shared character takes
(``ready.go``, ``praise.general``, ``encourage.retry``,
``encourage.progress``, ``celebrate.success``) through
``shared_character_audio_path`` with the platform fallback (selected
language -> base -> English -> silence). Clips are decoded lazily into a
tiny LRU, never all at start-up. No new speech is generated here.

The effects (a star chime, a flag ding, a soft cartoon "boing" for a
tumble, a mushroom whoosh, a landing thump, a finish fanfare and a sparkle
run for a perfect landing) are synthesized once in the mixer's own format.
There is deliberately no engine drone. Every call fails soft without a mixer.
"""

from __future__ import annotations

from collections import OrderedDict
import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 5
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "tito"
SHARED_CUES: Final = ("ready.go", "praise.general", "encourage.retry", "encourage.progress", "celebrate.success")
CLIP_CACHE_LIMIT: Final = 5
EFFECTS: Final = ("star", "flag", "boing", "whoosh", "thump", "fanfare", "sparkle")


class CollineAudio:
    """Own Tito's speech and the small sound bank for one visit."""

    def __init__(self, *, locale: str = "en", project_root: Path = PROJECT_ROOT, rng: random.Random | None = None) -> None:
        self.locale = locale.split("-")[0].split("_")[0] or "en"
        self._rng = rng if rng is not None else random.Random()
        self._paths: dict[str, Path] = {}
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._clips: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._available = False
        self.last_speech: str | None = None
        self.last_effect: str | None = None
        for cue in SHARED_CUES:
            try:
                path = shared_character_audio_path(project_root, HOST, cue, self.locale)
            except Exception:
                path = None
            if path is not None:
                self._paths[cue] = path
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    @property
    def cues(self) -> frozenset[str]:
        return frozenset(self._paths)

    # -- speech -------------------------------------------------------------------------

    def say(self, cue: str) -> bool:
        """Play one approved Tito line (shared character cue)."""

        self.last_speech = cue
        path = self._paths.get(cue)
        if not self._available or path is None:
            return False
        sound = self._clip(cue, path)
        if sound is None:
            return False
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

    def speaking(self) -> bool:
        if not self._available:
            return False
        try:
            return bool(pygame.mixer.Channel(SPEECH_CHANNEL).get_busy())
        except (pygame.error, RuntimeError):
            return False

    def _clip(self, key: str, path: Path) -> pygame.mixer.Sound | None:
        if key in self._clips:
            self._clips.move_to_end(key)
            return self._clips[key]
        try:
            sound: pygame.mixer.Sound | None = pygame.mixer.Sound(str(path))
        except (pygame.error, OSError):
            sound = None
        self._clips[key] = sound
        while len(self._clips) > CLIP_CACHE_LIMIT:
            self._clips.popitem(last=False)
        return sound

    # -- effects ------------------------------------------------------------------------

    def play(self, name: str) -> None:
        self.last_effect = name
        if not self._available:
            return
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            for index in range(FIRST_SFX_CHANNEL, LAST_SFX_CHANNEL + 1):
                channel = pygame.mixer.Channel(index)
                if not channel.get_busy():
                    channel.play(sound)
                    return
            pygame.mixer.Channel(FIRST_SFX_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return

    def stop_all(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.stop()
        except (pygame.error, RuntimeError):
            return

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds["star"] = _bell(rate, channels, (1046.5, 1318.5, 1568.0), 0.36, 2300)
        self._sounds["flag"] = _bell(rate, channels, (784.0, 1046.5), 0.32, 2100)
        self._sounds["sparkle"] = _bell(rate, channels, (1046.5, 1318.5, 1568.0, 2093.0), 0.8, 1900)
        self._sounds["fanfare"] = _bell(rate, channels, (523.3, 659.3, 784.0, 1046.5, 1318.5), 1.2, 2600)
        self._sounds["boing"] = _boing(rate, channels)
        self._sounds["whoosh"] = _whoosh(rate, channels, self._rng)
        self._sounds["thump"] = _thump(rate, channels)


def _bell(rate: int, channels: int, notes: tuple[float, ...], duration: float, volume: int) -> pygame.mixer.Sound:
    """Soft celesta notes, one after another (a quick rising run for >1 note)."""

    buffer = bytearray()
    step = duration / (len(notes) + 1)
    for index in range(int(rate * duration)):
        t = index / rate
        value = 0.0
        for order, frequency in enumerate(notes):
            local = t - order * step
            if local < 0:
                continue
            envelope = min(1.0, local / 0.006) * math.exp(-5.0 * local / duration)
            value += math.sin(2 * math.pi * frequency * local) * envelope
        append_mono_pcm16(buffer, int(value * volume), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _boing(rate: int, channels: int) -> pygame.mixer.Sound:
    """A gentle cartoon spring (rising wobble), never a failure buzzer."""

    buffer = bytearray()
    duration = 0.45
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = 180.0 + 360.0 * (t / duration) + math.sin(2 * math.pi * 14.0 * t) * 30.0
        phase += 2 * math.pi * frequency / rate
        envelope = min(1.0, t / 0.01) * (1.0 - t / duration)
        append_mono_pcm16(buffer, int(math.sin(phase) * envelope * 5200), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _whoosh(rate: int, channels: int, rng: random.Random) -> pygame.mixer.Sound:
    buffer = bytearray()
    duration = 0.3
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = 300.0 + 500.0 * (t / duration)
        phase += 2 * math.pi * frequency / rate
        envelope = math.sin(math.pi * t / duration)
        value = math.sin(phase) * 0.6 + (rng.random() * 2.0 - 1.0) * 0.25
        append_mono_pcm16(buffer, int(value * envelope * 4200), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _thump(rate: int, channels: int) -> pygame.mixer.Sound:
    buffer = bytearray()
    duration = 0.16
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.exp(-26.0 * t)
        value = 0.8 * math.sin(2 * math.pi * 120.0 * t) + 0.2 * math.sin(2 * math.pi * 260.0 * t)
        append_mono_pcm16(buffer, int(value * envelope * 7000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


__all__ = ["CLIP_CACHE_LIMIT", "CollineAudio", "EFFECTS", "HOST", "SHARED_CUES"]
