"""Approved speech plus small synthesized wooden-toy sounds for Tito's Marble Run.

Speech uses only Tito's owner-accepted shared character takes
(``assets/audio/characters/shared/v0.2/tito``) through
``shared_character_audio_path`` (selected language -> English -> silence):
"ready, go" on the first GO of a board, praise when the marble lands in the
basket, the big cheer at the end of a set, "keep going" as the first idle
nudge and "let's try again" after a miss. Moments without an approved line
(placing or turning a piece, the marble stopping) stay pictorial + sound.
Sound effects are generated once, after the first frame; every call fails soft without a
mixer.
"""

from __future__ import annotations

from itertools import accumulate, repeat
import math
from operator import add, mul
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 6
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPEAKER: Final = "tito"
# Activity cue -> Tito's shared take family.
SHARED_CUES: Final[dict[str, str]] = {
    "go": "ready.go",
    "basket": "praise.general",
    "complete": "celebrate.success",
    "nudge": "encourage.progress",
    "retry": "encourage.retry",
}


class RampAudio:
    """Own the speech/sound bank for one Activity run."""

    def __init__(self, locale: str = "en", *, project_root: Path = PROJECT_ROOT) -> None:
        self.locale = (locale or "en").split("-")[0]
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

    def has_speech(self, cue: str) -> bool:
        return cue in self._speech

    def say(self, cue: str) -> None:
        """Speak one approved cue now (silent when the take is missing)."""

        self.last_speech = cue
        sound = self._speech.get(cue)
        if not self._available or sound is None:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return

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

    # -- loading ------------------------------------------------------------

    def _load_speech(self) -> None:
        for cue, family in SHARED_CUES.items():
            path = shared_character_audio_path(self._project_root, SPEAKER, family, self.locale)
            if path is None:
                continue
            try:
                self._speech[cue] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("pick", lambda: _knock(rate, channels, 520.0, 0.07, 5200))
        self._sounds.define("place", lambda: _knock(rate, channels, 300.0, 0.12, 8000))
        self._sounds.define("turn", lambda: _knock(rate, channels, 680.0, 0.06, 5200))
        self._sounds.define("remove", lambda: _sweep(rate, channels, 0.14, 420.0, 560.0, 4800))
        self._sounds.define("go", lambda: _sweep(rate, channels, 0.22, 220.0, 440.0, 6000))
        self._sounds.define("clack", lambda: _knock(rate, channels, 860.0, 0.05, 4200))
        self._sounds.define("bonk", lambda: _sweep(rate, channels, 0.16, 300.0, 520.0, 7000))
        self._sounds.define("basket", lambda: _chime(rate, channels, (523.25, 659.25, 783.99, 1046.5), step=0.1))
        self._sounds.define("lost", lambda: _sweep(rate, channels, 0.42, 520.0, 220.0, 6000))
        self._sounds.define("stopped", lambda: _knock(rate, channels, 180.0, 0.18, 6500))
        self._sounds.define("hint", lambda: _chime(rate, channels, (1318.5, 1760.0), step=0.09, volume=6000))
        self._sounds.define("fanfare", lambda: _chime(rate, channels, (523.25, 659.25, 783.99, 1046.5, 1318.5), step=0.14, volume=10000))


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


def _chime(
    rate: int,
    channels: int,
    notes: tuple[float, ...],
    *,
    step: float = 0.08,
    volume: int = 9000,
) -> pygame.mixer.Sound:
    tail = 0.35
    duration = step * len(notes) + tail
    count = int(rate * duration)
    parts = []
    for number, frequency in enumerate(notes):
        parts.append(_decaying_sine(rate, count, frequency, 7.0, start=number * step))
        parts.append(_decaying_sine(rate, count, 2.0 * frequency, 7.0, start=number * step, gain=0.3))
    mixed = [max(-1.6, min(1.6, value)) for value in _mix(parts)]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(mixed, channels, scale=volume))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    per_sample = 2.0 * math.pi / rate
    phases = accumulate([(start + (end - start) * (t / duration)) * per_sample for t in times])
    envelope = [math.sin(math.pi * t / duration) for t in times]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(map(mul, map(math.sin, phases), envelope), channels, scale=volume))


def _knock(rate: int, channels: int, frequency: float, duration: float, volume: int) -> pygame.mixer.Sound:
    """Short wooden knock: a fast-decaying tone with a little click of noise."""

    noise = random.Random(int(frequency))
    samples: list[float] = []
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.exp(-38.0 * t)
        value = 0.8 * math.sin(2.0 * math.pi * frequency * t) + 0.2 * noise.uniform(-1.0, 1.0) * math.exp(-120.0 * t)
        samples.append(int(value * envelope * volume))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


__all__ = ["RampAudio", "SHARED_CUES"]
