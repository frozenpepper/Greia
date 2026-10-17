"""Approved speech plus small synthesized greenhouse sounds for Piccola Serra.

Speech uses only Tito's owner-accepted shared character takes
(``assets/audio/characters/shared/v0.2/tito``) through
``shared_character_audio_path`` (selected language -> English -> silence):
"ready, go" when a new seed is chosen, praise after a harvest and after the
pictures are in order, the big cheer at the end of a visit, "keep going" as
the first idle nudge and "let's try again" after a care that did not help.
Moments without an approved line ("the plant is thirsty", "what comes
first?") stay pictorial + sound. Sound effects are generated once, after
the first frame; every call fails soft without a mixer. No generated speech.
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

if __package__:
    from .serra_content import TITO
else:
    from serra_content import TITO

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 5
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SHARED_CUES: Final[dict[str, str]] = {
    "start": "ready.go",
    "praise": "praise.general",
    "complete": "celebrate.success",
    "nudge": "encourage.progress",
    "retry": "encourage.retry",
}
EFFECTS: Final = (
    "seed", "water", "grow", "sun", "wait", "harvest", "basket", "card", "not_yet", "cloth", "drip", "fanfare",
)


class SerraAudio:
    """Own the speech/sound bank for one Activity run."""

    def __init__(self, locale: str = "en", *, project_root: Path = PROJECT_ROOT) -> None:
        self.locale = (locale or "en").split("-")[0].split("_")[0] or "en"
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

    # -- loading -------------------------------------------------------------

    def _load_speech(self) -> None:
        for cue, family in SHARED_CUES.items():
            try:
                path = shared_character_audio_path(self._project_root, TITO, family, self.locale)
            except Exception:
                path = None
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
        self._sounds.define("seed", lambda: _sweep(rate, channels, 0.14, 520.0, 300.0, 7000))
        self._sounds.define("water", lambda: _trickle(rate, channels))
        self._sounds.define("grow", lambda: _chime(rate, channels, (523.25, 659.25, 783.99), step=0.09, volume=8000))
        self._sounds.define("sun", lambda: _chime(rate, channels, (880.0, 1108.7, 1318.5), step=0.12, volume=6000))
        self._sounds.define("wait", lambda: _ticks(rate, channels))
        self._sounds.define("harvest", lambda: _pop(rate, channels))
        self._sounds.define("basket", lambda: _chime(rate, channels, (783.99, 1046.5, 1318.5, 1568.0), step=0.08))
        self._sounds.define("card", lambda: _chime(rate, channels, (987.77,), step=0.05, volume=7000))
        self._sounds.define("not_yet", lambda: _sweep(rate, channels, 0.22, 420.0, 330.0, 5000))
        self._sounds.define("cloth", lambda: _swish(rate, channels))
        self._sounds.define("drip", lambda: _chime(rate, channels, (1318.5, 1046.5), step=0.12, volume=4500))
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


def _chime(rate: int, channels: int, notes: tuple[float, ...], *, step: float = 0.08, volume: int = 9000) -> pygame.mixer.Sound:
    duration = step * len(notes) + 0.35
    count = int(rate * duration)
    parts = []
    for number, frequency in enumerate(notes):
        parts.append(_decaying_sine(rate, count, frequency, 7.0, start=number * step))
        parts.append(_decaying_sine(rate, count, 2.0 * frequency, 7.0, start=number * step, gain=0.3))
    mixed = [max(-1.6, min(1.6, value)) for value in _mix(parts)]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(mixed, channels, scale=volume))


def _pop(rate: int, channels: int) -> pygame.mixer.Sound:
    samples: list[float] = []
    duration = 0.12
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        phase += 2.0 * math.pi * (480.0 + (1.0 - t / duration) * 360.0) / rate
        samples.append(int(math.sin(phase) * math.sin(math.pi * t / duration) ** 0.8 * 9000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    per_sample = 2.0 * math.pi / rate
    phases = accumulate([(start + (end - start) * (t / duration)) * per_sample for t in times])
    envelope = [math.sin(math.pi * t / duration) for t in times]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(map(mul, map(math.sin, phases), envelope), channels, scale=volume))


def _trickle(rate: int, channels: int) -> pygame.mixer.Sound:
    """Soft watering trickle: short bright blips over a gentle noise bed."""

    noise = random.Random(11)
    samples: list[float] = []
    duration = 0.9
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.sin(math.pi * t / duration) ** 0.6
        blip = math.sin(2 * math.pi * (900 + 300 * math.sin(t * 31)) * t) * (0.5 + 0.5 * math.sin(t * 57))
        value = 0.35 * blip + 0.25 * noise.uniform(-1.0, 1.0)
        samples.append(int(value * envelope * 5000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _ticks(rate: int, channels: int) -> pygame.mixer.Sound:
    """Tick-tock: time passes."""

    samples: list[float] = []
    duration = 1.0
    for index in range(int(rate * duration)):
        t = index / rate
        local = t % 0.25
        frequency = 1500.0 if int(t / 0.25) % 2 == 0 else 1100.0
        value = math.sin(2 * math.pi * frequency * local) * math.exp(-60.0 * local)
        samples.append(int(value * 6000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _swish(rate: int, channels: int) -> pygame.mixer.Sound:
    noise = random.Random(5)
    samples: list[float] = []
    duration = 0.45
    last = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        last = 0.85 * last + 0.15 * noise.uniform(-1.0, 1.0)
        samples.append(int(last * math.sin(math.pi * t / duration) * 9000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


__all__ = ["EFFECTS", "SHARED_CUES", "SerraAudio"]
