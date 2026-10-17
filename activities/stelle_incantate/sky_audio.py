"""Approved speech plus small synthesized night-sky sounds for Stelle Incantate.

Speech uses only recorded, approved clips: Leo's shared reaction library
(``ready.go``, ``praise.general``, ``celebrate.success``, ``encourage.retry``,
``encourage.progress``), this package's voiced curiosity facts through
``LocalizedResources``, and — when they are recorded — package counting cues
``count_1`` .. ``count_20``. Missing cues stay silent; the game remains fully
pictorial. Star chimes follow the number itself on a gentle major scale, so
counting up climbs and counting back descends. Effects are generated once, after
the first frame and chimes once per number on first need; every call fails soft
without a mixer.
"""

from __future__ import annotations

from itertools import accumulate, repeat
import math
from operator import add, mul
from pathlib import Path
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources, shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

SPEECH_CHANNEL: Final[int] = 0
FIRST_SFX_CHANNEL: Final[int] = 2
LAST_SFX_CHANNEL: Final[int] = 5
MAX_NUMBER: Final[int] = 20
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_SEMITONES: Final[tuple[int, ...]] = (0, 2, 4, 5, 7, 9, 11)  # major scale
_BASE_HZ: Final[float] = 261.63  # C4: number 1
_SHARED_CUES: Final[dict[str, str]] = {
    "go": "ready.go",
    "praise": "praise.general",
    "celebrate": "celebrate.success",
    "retry": "encourage.retry",
    "progress": "encourage.progress",
}


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


def number_frequency(number: int) -> float:
    """Pitch for a star's number: one major-scale step per number (C4 = 1)."""

    step = max(1, min(MAX_NUMBER, int(number))) - 1
    octave, degree = divmod(step, len(_SEMITONES))
    return _BASE_HZ * 2.0 ** (octave + _SEMITONES[degree] / 12.0)


class SkyAudio:
    """Own the speech/sound bank for the night sky."""

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
        self._voice: dict[str, pygame.mixer.Sound] = {}  # bounded by the fact catalogue
        self._available = False
        self._spec: tuple[int, int] | None = None
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

    # -- speech -----------------------------------------------------------

    def has_speech(self, cue: str) -> bool:
        return cue in self._speech

    def say(self, cue: str) -> None:
        """Speak one approved cue now (silent when it does not exist)."""

        self.last_speech = cue
        sound = self._speech.get(cue)
        if not self._available or sound is None:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return

    def say_number(self, number: int) -> None:
        """Speak a counting word when an approved clip exists (else silent)."""

        cue = f"count_{max(1, min(MAX_NUMBER, int(number)))}"
        if cue in self._speech:
            self.say(cue)

    def play_voice(self, path: Path | str) -> bool:
        """Play one packaged localized voice file on the speech channel."""

        self.last_speech = str(path)
        if not self._available:
            return False
        key = str(path)
        sound = self._voice.get(key)
        if sound is None:
            try:
                sound = pygame.mixer.Sound(key)
            except (pygame.error, OSError):
                return False
            self._voice[key] = sound
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
            return True
        except (pygame.error, RuntimeError):
            return False

    def speaking(self) -> bool:
        if not self._available:
            return False
        try:
            return bool(pygame.mixer.Channel(SPEECH_CHANNEL).get_busy())
        except (pygame.error, RuntimeError):
            return False

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
        number = max(1, min(MAX_NUMBER, int(number)))
        self.prepare_numbers((number,))
        self.play(f"chime_{number}")

    def prepare_numbers(self, numbers) -> None:
        """Synthesize the chimes a figure will use (once each, bounded by 20).

        Done at figure start, during the stars' fade-in, so start-up stays
        cheap on Atom-class hardware and no tap waits for synthesis.
        """

        if self._spec is None:
            return
        rate, channels = self._spec
        for number in numbers:
            number = max(1, min(MAX_NUMBER, int(number)))
            key = f"chime_{number}"
            if key not in self._sounds:
                try:
                    self._sounds.define(key, lambda number=number: _chime(rate, channels, 0.36, number_frequency(number)))
                except (pygame.error, RuntimeError):
                    return

    # -- loading ----------------------------------------------------------

    def _load_speech(self) -> None:
        files: dict[str, Path] = {}
        if self._resources is not None:
            files.update(
                (stem, path) for stem, path in self._resources.speech_paths().items() if stem.startswith("count_")
            )
        for cue, shared in _SHARED_CUES.items():
            path = shared_character_audio_path(self._project_root, "leo", shared, self.locale)
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
        self._spec = spec
        rate, channels = spec
        self._sounds.define("boop", lambda: _sweep(rate, channels, 0.28, 330.0, 262.0, 7000))
        self._sounds.define("twinkle", lambda: _sweep(rate, channels, 0.18, 1320.0, 1760.0, 4000))
        self._sounds.define("card", lambda: _sweep(rate, channels, 0.16, 520.0, 880.0, 8000))
        self._sounds.define("reveal", lambda: _arpeggio(rate, channels, (523.25, 659.25, 783.99, 1046.5, 1318.5), 0.12, 9000))
        self._sounds.define("whoosh", lambda: _sweep(rate, channels, 0.6, 220.0, 880.0, 5000))
        self._sounds.define("fanfare", lambda: _arpeggio(rate, channels, (523.25, 659.25, 783.99, 1046.5), 0.15, 11000))


def _chime(rate: int, channels: int, duration: float, frequency: float) -> pygame.mixer.Sound:
    count = int(rate * duration)
    decay = 4.5 / duration
    parts = [
        _decaying_sine(rate, count, frequency, decay, attack=0.005),
        _decaying_sine(rate, count, 2.0 * frequency, decay, attack=0.005, gain=0.3),
        _decaying_sine(rate, count, 3.0 * frequency, decay, attack=0.005, gain=0.1),
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=9500))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    per_sample = 2.0 * math.pi / rate
    phases = accumulate([(start + (end - start) * (t / duration)) * per_sample for t in times])
    envelope = [math.sin(math.pi * t / duration) for t in times]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(map(mul, map(math.sin, phases), envelope), channels, scale=volume))


def _arpeggio(
    rate: int, channels: int, notes: tuple[float, ...], step: float, volume: int
) -> pygame.mixer.Sound:
    tail = 0.45
    count = int(rate * (step * len(notes) + tail))
    length = step + tail
    parts = [
        _decaying_sine(rate, count, frequency, 4.0 / length, start=position * step, stop=position * step + length)
        for position, frequency in enumerate(notes)
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=volume * 0.8))


__all__ = ["MAX_NUMBER", "SkyAudio", "number_frequency"]
