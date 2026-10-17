"""Approved speech plus small synthesized effects for Colline Allegre.

Speech uses only Tito's recorded, owner-approved shared character takes
(``ready.go``, ``praise.general``, ``encourage.retry``,
``encourage.progress``, ``celebrate.success``) through
``shared_character_audio_path`` with the platform fallback (selected
language -> base -> English -> silence), plus two owner-approved package
lines (``slow_down`` when the sign glows after a tumble, ``made_it_picnic``
at each picnic) through ``LocalizedResources.audio_path``. Clips are decoded
lazily into a tiny LRU, never all at start-up. No new speech is generated here.

The effects (a star chime, a flag ding, a soft cartoon "boing" for a
tumble, a mushroom whoosh, a landing thump, a finish fanfare and a sparkle
run for a perfect landing) are synthesized once in the mixer's own format.
There is deliberately no engine drone. Every call fails soft without a mixer.
"""

from __future__ import annotations

from collections import OrderedDict
from itertools import accumulate
import math
from operator import mul
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import (
    LocalizationError,
    activity_resources,
    shared_character_audio_path,
)
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    bell_sound,
    current_pcm16_mixer_spec,
    decaying_sine,
    mono_pcm16_bytes,
)

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 5
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "tito"
SHARED_CUES: Final = ("ready.go", "praise.general", "encourage.retry", "encourage.progress", "celebrate.success")
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
# Owner-approved per-Activity lines (``assets/audio/<locale>/<cue>.wav``).
PACKAGE_CUES: Final = ("slow_down", "made_it_picnic")
CLIP_CACHE_LIMIT: Final = 5
EFFECTS: Final = ("star", "flag", "boing", "whoosh", "thump", "fanfare", "sparkle")


class CollineAudio:
    """Own Tito's speech and the small sound bank for one visit."""

    def __init__(self, *, locale: str = "en", project_root: Path = PROJECT_ROOT, rng: random.Random | None = None) -> None:
        self.locale = locale.split("-")[0].split("_")[0] or "en"
        self._rng = rng if rng is not None else random.Random()
        self._paths: dict[str, Path] = {}
        self._sounds = DeferredSoundBank()
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
            resources = activity_resources(PACKAGE_ROOT, requested_locale=self.locale)
        except LocalizationError:
            resources = None
        for cue in PACKAGE_CUES if resources is not None else ():
            path = resources.audio_path(cue)
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
        self._sounds.define("star", lambda: bell_sound(rate, channels, (1046.5, 1318.5, 1568.0), 0.36, 2300))
        self._sounds.define("flag", lambda: bell_sound(rate, channels, (784.0, 1046.5), 0.32, 2100))
        self._sounds.define("sparkle", lambda: bell_sound(rate, channels, (1046.5, 1318.5, 1568.0, 2093.0), 0.8, 1900))
        self._sounds.define("fanfare", lambda: bell_sound(rate, channels, (523.3, 659.3, 784.0, 1046.5, 1318.5), 1.2, 2600))
        self._sounds.define("boing", lambda: _boing(rate, channels))
        # The whoosh draws its noise from the shared game RNG: build it now so
        # the game's random sequence is exactly what it was before deferral.
        whoosh = _whoosh(rate, channels, self._rng)
        self._sounds.define("whoosh", lambda: whoosh)
        self._sounds.define("thump", lambda: _thump(rate, channels))


def _boing(rate: int, channels: int) -> pygame.mixer.Sound:
    """A gentle cartoon spring (rising wobble), never a failure buzzer."""

    duration = 0.45
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    wobble = 2 * math.pi * 14.0
    per_sample = 2 * math.pi / rate
    phases = accumulate([(180.0 + 360.0 * (t / duration) + math.sin(wobble * t) * 30.0) * per_sample for t in times])
    envelope = [min(1.0, t / 0.01) * (1.0 - t / duration) for t in times]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(map(mul, map(math.sin, phases), envelope), channels, scale=5200))


def _whoosh(rate: int, channels: int, rng: random.Random) -> pygame.mixer.Sound:
    duration = 0.3
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    per_sample = 2 * math.pi / rate
    phases = accumulate([(300.0 + 500.0 * (t / duration)) * per_sample for t in times])
    # One rng.random() per sample, in sample order: the shared game sequence is unchanged.
    noise = [rng.random() for _ in times]
    tone = map(math.sin, phases)
    samples = [
        (tone_value * 0.6 + (draw * 2.0 - 1.0) * 0.25) * math.sin(math.pi * t / duration)
        for tone_value, draw, t in zip(tone, noise, times)
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels, scale=4200))


def _thump(rate: int, channels: int) -> pygame.mixer.Sound:
    count = int(rate * 0.16)
    low = decaying_sine(rate, count, 120.0, 26.0)
    high = decaying_sine(rate, count, 260.0, 26.0)
    samples = [0.8 * a + 0.2 * b for a, b in zip(low, high)]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels, scale=7000))


__all__ = ["CLIP_CACHE_LIMIT", "CollineAudio", "EFFECTS", "HOST", "PACKAGE_CUES", "SHARED_CUES"]
