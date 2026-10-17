"""Approved speech plus small synthesized care sounds for Little Vet Clinic.

Speech uses only recorded, approved clips: Momo's shared character takes
(``ready.go``, ``praise.general``, ``encourage.retry``,
``encourage.progress``, ``celebrate.success``) and the shared vocabulary
bank for a patient's name where one exists ("cat", "mouse", "dog").
Moments without an approved line ("where does it hurt?", tool names) stay
pictorial and silent. Care sounds are generated once, after the first frame; every call
fails soft without a mixer.
"""

from __future__ import annotations

from itertools import accumulate, repeat
import math
from operator import add, mul
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path, shared_vocab_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

SPEECH_CHANNEL: Final[int] = 0
FIRST_SFX_CHANNEL: Final[int] = 2
LAST_SFX_CHANNEL: Final[int] = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPEAKER: Final = "momo"
MOMO_CUES: Final[tuple[str, ...]] = (
    "ready.go",
    "praise.general",
    "encourage.retry",
    "encourage.progress",
    "celebrate.success",
)
MAX_TAKES: Final = 3


class ClinicAudio:
    """Own the speech/sound bank for one clinic session."""

    def __init__(
        self,
        locale: str = "en",
        *,
        vocab: tuple[str, ...] = (),
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.locale = locale.split("-")[0]
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._speech: dict[str, list[pygame.mixer.Sound]] = {}
        self._available = False
        self.last_speech: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._load_speech(vocab)
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- speech -------------------------------------------------------------

    def has_speech(self, cue: str) -> bool:
        return cue in self._speech

    def say(self, cue: str) -> None:
        """Speak one approved cue now (silent when no clip exists)."""

        self.last_speech = cue
        takes = self._speech.get(cue)
        if not self._available or not takes:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(self._rng.choice(takes))
        except (pygame.error, RuntimeError):
            return

    def speech_busy(self) -> bool:
        if not self._available:
            return False
        try:
            return pygame.mixer.Channel(SPEECH_CHANNEL).get_busy()
        except (pygame.error, RuntimeError):
            return False

    def name(self, noun: str | None) -> None:
        """Say a patient's name from the shared vocabulary bank, if recorded."""

        if noun and not self.speech_busy():
            self.say(f"vocab.{noun}")

    # -- effects ------------------------------------------------------------

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

    # -- loading ------------------------------------------------------------

    def _load_speech(self, vocab: tuple[str, ...]) -> None:
        for cue in MOMO_CUES:
            first = shared_character_audio_path(self._project_root, SPEAKER, cue, self.locale)
            if first is None:
                continue
            # Sibling takes of the same approved cue (``__01``, ``__02`` ...).
            prefix = first.name.rsplit("__", 1)[0]
            paths = sorted(first.parent.glob(f"{prefix}__*.wav"))[:MAX_TAKES] or [first]
            self._speech[cue] = [sound for sound in map(_load, paths) if sound is not None]
        for noun in vocab:
            path = shared_vocab_audio_path(self._project_root, noun, self.locale)
            sound = _load(path) if path is not None else None
            if sound is not None:
                self._speech[f"vocab.{noun}"] = [sound]

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("pop", lambda: _sweep(rate, channels, 0.12, 520.0, 880.0, 7000))
        self._sounds.define("hop", lambda: _sweep(rate, channels, 0.16, 380.0, 640.0, 6000))
        self._sounds.define("whoosh", lambda: _sweep(rate, channels, 0.24, 900.0, 1500.0, 3800))
        self._sounds.define("nope", lambda: _sweep(rate, channels, 0.24, 420.0, 300.0, 6500))
        self._sounds.define("scrub", lambda: _scrub(rate, channels))
        self._sounds.define("fluff", lambda: _sweep(rate, channels, 0.3, 300.0, 520.0, 4200))
        self._sounds.define("drip", lambda: _sweep(rate, channels, 0.14, 1200.0, 700.0, 6000))
        self._sounds.define("stick", lambda: _chime(rate, channels, 0.22, 880.0))
        self._sounds.define("heartbeat", lambda: _heartbeat(rate, channels))
        self._sounds.define("cuddle", lambda: _sweep(rate, channels, 0.38, 520.0, 760.0, 6000))
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


def _load(path: Path) -> pygame.mixer.Sound | None:
    try:
        return pygame.mixer.Sound(str(path))
    except (pygame.error, OSError):
        return None


def _chime(rate: int, channels: int, duration: float, frequency: float) -> pygame.mixer.Sound:
    count = int(rate * duration)
    decay = 4.5 / duration
    parts = [
        _decaying_sine(rate, count, frequency, decay),
        _decaying_sine(rate, count, 2.0 * frequency, decay, gain=0.3),
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=9000))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    per_sample = 2.0 * math.pi / rate
    phases = accumulate([(start + (end - start) * (t / duration)) * per_sample for t in times])
    envelope = [math.sin(math.pi * t / duration) for t in times]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(map(mul, map(math.sin, phases), envelope), channels, scale=volume))


def _scrub(rate: int, channels: int) -> pygame.mixer.Sound:
    """Soft bubbly scrub: a wobbling tone in three little pulses."""

    samples: list[float] = []
    duration = 0.45
    for index in range(int(rate * duration)):
        t = index / rate
        pulse = abs(math.sin(math.pi * t / 0.15))
        frequency = 600.0 + 250.0 * math.sin(t * 60.0)
        samples.append(int(math.sin(2.0 * math.pi * frequency * t) * pulse * 3600))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _heartbeat(rate: int, channels: int) -> pygame.mixer.Sound:
    """"Lub-dub" heard through the stethoscope."""

    samples: list[float] = []
    for index in range(int(rate * 0.6)):
        t = index / rate
        value = 0.0
        for start in (0.0, 0.16):
            local = t - start
            if 0.0 <= local < 0.12:
                value += math.sin(2.0 * math.pi * 70.0 * local) * math.exp(-28.0 * local)
        samples.append(int(value * 14000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _fanfare(rate: int, channels: int) -> pygame.mixer.Sound:
    notes = ((0.0, 0.15, 523.25), (0.12, 0.15, 659.25), (0.24, 0.15, 783.99), (0.36, 0.45, 1046.5))
    count = int(rate * 0.81)  # the last note ends at 0.81 s; the old 0.85 s buffer ended in silence
    parts = [_decaying_sine(rate, count, frequency, 3.5 / length, start=start, stop=start + length) for start, length, frequency in notes]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=10000))


__all__ = ["ClinicAudio", "MOMO_CUES"]
