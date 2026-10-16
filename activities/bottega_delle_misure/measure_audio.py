"""Approved speech plus small synthesized workshop sounds for La Bottega delle Misure.

Speech uses only this package's recorded, owner-approved clips through the
platform ``LocalizedResources`` fallback policy (selected language → base →
English → silence): the comparison prompts, the measuring prompt and the
short praise / try-again lines. Jobs without a recorded prompt (the balance)
stay pictorial. Wooden clacks, counting chimes, the balance creak and the
fanfare are generated once, after the first frame; every call fails soft without a mixer.
"""

from __future__ import annotations

import math
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.pygame_audio import DeferredSoundBank, append_mono_pcm16, current_pcm16_mixer_spec

SPEECH_CHANNEL: Final[int] = 0
FIRST_SFX_CHANNEL: Final[int] = 2
LAST_SFX_CHANNEL: Final[int] = 5
PRAISE_CUES: Final[tuple[str, ...]] = ("correct_1", "correct_2", "correct_3")
RETRY_CUES: Final[tuple[str, ...]] = ("retry_1", "retry_2")
PROMPT_CUES: Final[tuple[str, ...]] = (
    "prompt_compare_longer",
    "prompt_compare_shorter",
    "prompt_compare_taller",
    "prompt_compare_shorter_h",
    "prompt_measure",
)
# Only the clips this game speaks are decoded (older recorded cues stay unused).
USED_CUES: Final[frozenset[str]] = frozenset((*PRAISE_CUES, *RETRY_CUES, *PROMPT_CUES))
# C major pentatonic climbing: one gentle step per laid / counted block.
_COUNT_NOTES: Final[tuple[float, ...]] = (523.25, 587.33, 659.25, 783.99, 880.00, 1046.5, 1174.7, 1318.5, 1568.0)


class MeasureAudio:
    """Own the speech/sound bank for one Activity run."""

    def __init__(self, resources: LocalizedResources | None = None, *, rng: random.Random | None = None) -> None:
        self._resources = resources
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._speech: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        self._praise = 0
        self.last_speech: str | None = None
        self.last_sound: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._load_speech()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    def has_speech(self, cue: str) -> bool:
        return cue in self._speech

    # -- speech -----------------------------------------------------------

    def say(self, cue: str | None) -> None:
        """Speak one recorded cue now (silent when it is not recorded)."""

        if cue is None:
            return
        self.last_speech = cue
        if not self._available:
            return
        sound = self._speech.get(cue)
        if sound is None:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return

    def praise(self) -> None:
        self.say(PRAISE_CUES[self._praise % len(PRAISE_CUES)])
        self._praise += 1

    def encourage(self) -> None:
        self.say(self._rng.choice(RETRY_CUES))

    # -- effects ----------------------------------------------------------

    def play(self, name: str) -> None:
        self.last_sound = name
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
        self.play(f"chime_{max(1, min(len(_COUNT_NOTES), int(number)))}")

    # -- loading ----------------------------------------------------------

    def _load_speech(self) -> None:
        if self._resources is None:
            return
        for stem, path in self._resources.speech_paths().items():
            if stem not in USED_CUES:
                continue
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
            self._sounds.define(f"chime_{index}", lambda frequency=frequency: _chime(rate, channels, 0.38, frequency))
        self._sounds.define("clack", lambda: _knock(rate, channels, 0.07, 9000, 11))
        self._sounds.define("take", lambda: _sweep(rate, channels, 0.16, 640.0, 420.0, 6500))
        self._sounds.define("pop", lambda: _sweep(rate, channels, 0.16, 520.0, 880.0, 8000))
        self._sounds.define("boop", lambda: _sweep(rate, channels, 0.22, 420.0, 330.0, 7000))
        self._sounds.define("creak", lambda: _sweep(rate, channels, 0.34, 220.0, 160.0, 6000))
        self._sounds.define("whoosh", lambda: _whoosh(rate, channels))
        self._sounds.define("fanfare", lambda: _fanfare(rate, channels))


def _chime(rate: int, channels: int, duration: float, frequency: float) -> pygame.mixer.Sound:
    buffer = bytearray()
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.exp(-4.5 * t / duration)
        angle = 2.0 * math.pi * frequency * t
        value = math.sin(angle) + 0.35 * math.sin(2.0 * angle)
        append_mono_pcm16(buffer, int(value * envelope * 10000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _knock(rate: int, channels: int, duration: float, volume: int, seed: int) -> pygame.mixer.Sound:
    """A short hollow wooden block 'clack' (resonant body + a little noise)."""

    noise = random.Random(seed)
    buffer = bytearray()
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.exp(-60.0 * t)
        value = 0.7 * math.sin(2.0 * math.pi * 900.0 * t) + 0.3 * noise.uniform(-1.0, 1.0)
        append_mono_pcm16(buffer, int(value * envelope * volume), channels)
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


def _whoosh(rate: int, channels: int) -> pygame.mixer.Sound:
    noise = random.Random(5)
    buffer = bytearray()
    duration = 0.36
    smooth = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        smooth = 0.82 * smooth + 0.18 * noise.uniform(-1.0, 1.0)  # soft low-passed air
        envelope = math.sin(math.pi * t / duration)
        append_mono_pcm16(buffer, int(smooth * envelope * 14000), channels)
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
        append_mono_pcm16(buffer, int(value * 10000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


__all__ = ["MeasureAudio", "PRAISE_CUES", "PROMPT_CUES", "RETRY_CUES", "USED_CUES"]
