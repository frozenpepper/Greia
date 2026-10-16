"""Approved speech plus small synthesized chimes for Il Giardino dei Numeri.

Speech uses only recorded, approved clips: this package's cues (intro, prompt,
count_1..count_5, praise, basket_full) through ``LocalizedResources`` and Dani's
shared reaction library (``encourage.retry``). Missing cues (for example
``count_6``..``count_10`` until they are recorded) stay silent; the game
remains fully pictorial. Chimes are generated once, after the first frame.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources, shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, append_mono_pcm16, current_pcm16_mixer_spec

SPEECH_CHANNEL: Final[int] = 0
FIRST_SFX_CHANNEL: Final[int] = 2
LAST_SFX_CHANNEL: Final[int] = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
# C major pentatonic climbing two octaves: one gentle step per counted object.
_COUNT_NOTES: Final[tuple[float, ...]] = (
    523.25, 587.33, 659.25, 783.99, 880.00, 1046.5, 1174.7, 1318.5, 1568.0, 1760.0,
)
_SHARED_RETRY: Final[str] = "encourage.retry"


class GiardinoAudio:
    """Own the speech/chime sounds; every call fails soft without a mixer."""

    def __init__(
        self,
        locale: str = "it",
        resources: LocalizedResources | None = None,
        *,
        project_root: Path = PROJECT_ROOT,
    ) -> None:
        self._resources = resources
        self.locale = locale.split("-")[0]
        self._project_root = project_root
        self._sounds = DeferredSoundBank()
        self._speech: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        self.last_speech: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._load_speech()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- queries ----------------------------------------------------------

    def has_speech(self, cue: str) -> bool:
        return cue in self._speech

    def speech_busy(self) -> bool:
        if not self._available:
            return False
        try:
            return pygame.mixer.Channel(SPEECH_CHANNEL).get_busy()
        except (pygame.error, RuntimeError):
            return False

    # -- speech -----------------------------------------------------------

    def say(self, cue: str, then: str | None = None) -> None:
        """Speak one cue now, optionally queueing exactly one follow-up cue."""

        self.last_speech = cue
        if not self._available:
            return
        first = self._speech.get(cue)
        follow = self._speech.get(then) if then else None
        try:
            channel = pygame.mixer.Channel(SPEECH_CHANNEL)
            if first is not None:
                channel.play(first)
                if follow is not None:
                    channel.queue(follow)
            elif follow is not None:
                channel.play(follow)
        except (pygame.error, RuntimeError):
            return

    def say_number(self, number: int, then: str | None = None) -> None:
        self.say(f"count_{max(1, min(10, int(number)))}", then)

    def stop_speech(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

    # -- effects ----------------------------------------------------------

    def play(self, name: str) -> None:
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

    def chime(self, number: int) -> None:
        self.play(f"chime_{max(1, min(10, int(number)))}")

    # -- loading ----------------------------------------------------------

    def _load_speech(self) -> None:
        if self._resources is not None:
            files = dict(self._resources.speech_paths())
        else:
            folder = Path(__file__).resolve().parent / "assets" / "audio" / self.locale
            if not folder.is_dir():
                folder = folder.parent / "en"
            files = {path.stem: path for path in sorted(folder.glob("*.wav"))}
        shared = shared_character_audio_path(self._project_root, "dani", _SHARED_RETRY, self.locale)
        if shared is not None:
            files["retry"] = shared
        for stem, path in files.items():
            try:
                self._speech[stem] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        for index, frequency in enumerate(_COUNT_NOTES, start=1):
            self._sounds.define(f"chime_{index}", lambda frequency=frequency: _chime(rate, channels, 0.4, frequency))
        self._sounds.define("pop", lambda: _sweep(rate, channels, 0.16, 520.0, 880.0, 9000))
        self._sounds.define("boop", lambda: _sweep(rate, channels, 0.22, 420.0, 330.0, 7000))
        self._sounds.define("ripple", lambda: _sweep(rate, channels, 0.22, 440.0, 640.0, 6000))
        self._sounds.define("fanfare", lambda: _fanfare(rate, channels))


def _chime(rate: int, channels: int, duration: float, frequency: float) -> pygame.mixer.Sound:
    buffer = bytearray()
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.exp(-4.5 * t / duration)
        angle = 2.0 * math.pi * frequency * t
        value = math.sin(angle) + 0.35 * math.sin(2.0 * angle)
        append_mono_pcm16(buffer, int(value * envelope * 11000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    buffer = bytearray()
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = start + (end - start) * (t / duration)
        phase += 2.0 * math.pi * frequency / rate
        envelope = math.sin(math.pi * t / duration)
        append_mono_pcm16(buffer, int(math.sin(phase) * envelope * volume), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _fanfare(rate: int, channels: int) -> pygame.mixer.Sound:
    notes = ((0.0, 0.15, 523.25), (0.12, 0.15, 659.25), (0.24, 0.15, 783.99), (0.36, 0.45, 1046.5))
    buffer = bytearray()
    for index in range(int(rate * 0.85)):
        t = index / rate
        value = 0.0
        for start, length, frequency in notes:
            if start <= t < start + length:
                local = t - start
                value += math.sin(2.0 * math.pi * frequency * local) * math.exp(-3.5 * local / length)
        append_mono_pcm16(buffer, int(value * 11000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


__all__ = ["GiardinoAudio"]
