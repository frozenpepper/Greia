"""Approved speech plus small synthesized train sounds for Treno Numeri.

Speech uses only recorded, approved clips: Dani's shared reaction library
(``encourage.retry``, ``praise.general``, ``celebrate.success``,
``ready.go``, ``encourage.progress``) and, when they exist, this package's own
cues through ``LocalizedResources`` (for example ``count_1``..``count_10``
once spoken numbers are recorded). Missing cues stay silent; the game remains
fully pictorial. Whistle, chug, chimes and pops are generated once, after the first frame.
"""

from __future__ import annotations

from itertools import accumulate, repeat
import math
from operator import add, mul
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources, shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

SPEECH_CHANNEL: Final[int] = 0
FIRST_SFX_CHANNEL: Final[int] = 2
LAST_SFX_CHANNEL: Final[int] = 5
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
# C major pentatonic climbing two octaves: one gentle step per loaded cargo.
_COUNT_NOTES: Final[tuple[float, ...]] = (
    523.25, 587.33, 659.25, 783.99, 880.00, 1046.5, 1174.7, 1318.5, 1568.0, 1760.0,
)
_SHARED_CUES: Final[dict[str, str]] = {
    "retry": "encourage.retry",
    "praise": "praise.general",
    "celebrate": "celebrate.success",
    "go": "ready.go",
    "progress": "encourage.progress",
}


class TrainAudio:
    """Own the speech/sound bank; every call fails soft without a mixer."""

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
        self.last_sound: str | None = None
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

    def say_number(self, number: int) -> None:
        """Speak a counting word when an approved clip exists (else silent)."""

        cue = f"count_{max(1, min(10, int(number)))}"
        if cue in self._speech:
            self.say(cue)

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
        self.play(f"chime_{max(1, min(10, int(number)))}")

    # -- loading ----------------------------------------------------------

    def _load_speech(self) -> None:
        files: dict[str, Path] = {}
        if self._resources is not None:
            files.update(self._resources.speech_paths())
        for cue, shared in _SHARED_CUES.items():
            path = shared_character_audio_path(self._project_root, "dani", shared, self.locale)
            if path is not None:
                files[cue] = path
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
        self._sounds.define("unload", lambda: _sweep(rate, channels, 0.18, 760.0, 480.0, 7000))
        self._sounds.define("boop", lambda: _sweep(rate, channels, 0.22, 420.0, 330.0, 7000))
        self._sounds.define("creak", lambda: _sweep(rate, channels, 0.32, 210.0, 160.0, 6000))
        self._sounds.define("whistle", lambda: _whistle(rate, channels))
        self._sounds.define("chug", lambda: _chug(rate, channels))
        self._sounds.define("fanfare", lambda: _fanfare(rate, channels))


def _decaying_sine(
    rate: int,
    count: int,
    frequency: float,
    decay: float,
    *,
    start: float = 0.0,
    stop: float | None = None,
    attack: float = 0.0,
    gain: float = 1.0,
) -> list[float]:
    """``gain * sin(2*pi*f*local) * exp(-decay*local) * min(1, local/attack)`` for one partial.

    ``local`` is the time since ``start`` seconds; the list covers sample indices
    ``0..count-1`` and is zero before ``start`` and from ``stop`` on. Instead of a
    ``sin`` and an ``exp`` call per sample (the dominant start-up cost on the
    Atom), the partial is a complex phasor multiplied by one constant per
    sample and accumulated in C by ``itertools.accumulate``: the same curve to
    ~1e-11 (identical 16-bit samples), about three times cheaper.
    """

    first = int(start * rate)
    while first / rate < start:
        first += 1
    while first > 0 and (first - 1) / rate >= start:
        first -= 1
    last = count
    if stop is not None:
        last = min(count, int(stop * rate))
        while last / rate < stop:
            last += 1
        last = min(count, last)
    if first >= last:
        return [0.0] * count
    omega = 2.0 * math.pi * frequency
    offset = first / rate - start
    fade = math.exp(-decay / rate)  # |r| per sample; r = fade * exp(i*omega/rate), z0 = gain * exp((-decay + i*omega) * offset)
    start_amplitude = gain * math.exp(-decay * offset)
    phasors = accumulate(
        repeat(complex(fade * math.cos(omega / rate), fade * math.sin(omega / rate)), last - first - 1),
        mul,
        initial=complex(start_amplitude * math.cos(omega * offset), start_amplitude * math.sin(omega * offset)),
    )
    values = [z.imag for z in phasors]
    if attack > 0.0:
        for index in range(min(len(values), int(attack * rate) + 2)):
            values[index] *= min(1.0, (offset + index / rate) / attack)
    return [0.0] * first + values + [0.0] * (count - last)


def _mix(parts: list[list[float]]) -> list[float]:
    """Sum equally long sample lists."""

    total = parts[0]
    for part in parts[1:]:
        total = list(map(add, total, part))
    return total


def _chime(rate: int, channels: int, duration: float, frequency: float) -> pygame.mixer.Sound:
    count = int(rate * duration)
    decay = 4.5 / duration
    parts = [
        _decaying_sine(rate, count, frequency, decay),
        _decaying_sine(rate, count, 2.0 * frequency, decay, gain=0.35),
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=11000))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    per_sample = 2.0 * math.pi / rate
    phases = accumulate([(start + (end - start) * (t / duration)) * per_sample for t in times])
    envelope = [math.sin(math.pi * t / duration) for t in times]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(map(mul, map(math.sin, phases), envelope), channels, scale=volume))


def _whistle(rate: int, channels: int) -> pygame.mixer.Sound:
    """Two-tone 'toot-toot' (a soft chord, never shrill)."""

    samples: list[float] = []
    duration = 0.62
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = 587.33 if t < 0.26 else 698.46
        local = t if t < 0.26 else t - 0.3
        envelope = 0.0 if 0.26 <= t < 0.3 else min(1.0, local * 30.0) * math.exp(-1.6 * local)
        angle = 2.0 * math.pi * frequency * t
        value = math.sin(angle) + 0.5 * math.sin(1.25 * angle)
        samples.append(int(value * envelope * 7000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _chug(rate: int, channels: int) -> pygame.mixer.Sound:
    noise = random.Random(7)
    samples: list[float] = []
    for index in range(int(rate * 0.08)):
        t = index / rate
        samples.append(int(noise.uniform(-1.0, 1.0) * math.exp(-15.0 * t) * 6000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _fanfare(rate: int, channels: int) -> pygame.mixer.Sound:
    notes = ((0.0, 0.15, 523.25), (0.12, 0.15, 659.25), (0.24, 0.15, 783.99), (0.36, 0.45, 1046.5))
    count = int(rate * 0.81)  # the last note ends at 0.81 s; the old 0.85 s buffer ended in silence
    parts = [_decaying_sine(rate, count, frequency, 3.5 / length, start=start, stop=start + length) for start, length, frequency in notes]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=11000))


__all__ = ["TrainAudio"]
