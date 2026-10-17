"""Approved speech plus small synthesized effects for Woodland Hide & Seek.

Speech uses only recorded, approved clips:

* friend names from the platform's shared vocabulary audio bank
  (``shared_vocab_audio_path``; the package carries no noun clips) with the
  usual locale -> base -> English fallback; a name without a recording stays
  silent and the request remains pictorial;
* Lilli's shared takes (``ready.go``, ``celebrate.success``,
  ``encourage.retry``, ``encourage.progress``, ``praise.general``).

Effects (leaf rustle, found chime, hop pop, "not me" boing, hide whoosh,
fanfare) are synthesized once, after the first frame. Every call fails soft without a
mixer; name clips are decoded at most once each (bounded cache).
"""

from __future__ import annotations

from collections import OrderedDict
from itertools import accumulate, repeat
import math
from operator import add, mul
from pathlib import Path
import random
from typing import Final, Iterable

import pygame

from greia_platform.localization import shared_character_audio_path, shared_vocab_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "lilli"
LILLI_CUES: Final = ("ready.go", "celebrate.success", "encourage.retry", "encourage.progress", "praise.general")
NAME_CACHE_LIMIT: Final = 12
EFFECTS: Final = ("rustle", "found", "pop", "boing", "hide", "fanfare")


class WoodlandAudio:
    """Own the sound bank and speech for one Hide & Seek visit."""

    def __init__(
        self,
        *,
        locale: str = "en",
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.locale = locale.split("-")[0].split("_")[0] or "en"
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._lilli: dict[str, list[pygame.mixer.Sound]] = {}
        self._names: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._name_paths: dict[str, bool] = {}
        self._available = False
        self.last_speech: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._load_lilli()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- speech -------------------------------------------------------------

    def has_name(self, friend_id: str) -> bool:
        """True when an approved recording of the friend's name exists."""

        known = self._name_paths.get(friend_id)
        if known is None:
            known = self._name_path(friend_id) is not None
            self._name_paths[friend_id] = known
        return known

    def prepare_names(self, friend_ids: Iterable[str]) -> None:
        if not self._available:
            return
        for friend_id in friend_ids:
            if friend_id in self._names:
                self._names.move_to_end(friend_id)
                continue
            self._names[friend_id] = self._load_name(friend_id)
            while len(self._names) > NAME_CACHE_LIMIT:
                self._names.popitem(last=False)

    def say_name(self, friend_id: str) -> bool:
        """Speak the friend's name; returns False (silent) without a recording."""

        self.last_speech = f"animal.{friend_id}"
        if not self._available:
            return False
        if friend_id not in self._names:
            self.prepare_names((friend_id,))
        return self._speak(self._names.get(friend_id))

    def lilli(self, cue: str) -> bool:
        """Play one of Lilli's approved shared takes (random variant)."""

        self.last_speech = cue
        takes = self._lilli.get(cue)
        if not self._available or not takes:
            return False
        return self._speak(self._rng.choice(takes))

    def stop_speech(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

    def _speak(self, sound: pygame.mixer.Sound | None) -> bool:
        if sound is None:
            return False
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

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

    def _name_path(self, friend_id: str) -> Path | None:
        try:
            return shared_vocab_audio_path(self._project_root, friend_id, self.locale)
        except Exception:
            return None

    def _load_name(self, friend_id: str) -> pygame.mixer.Sound | None:
        path = self._name_path(friend_id)
        if path is None:
            return None
        try:
            return pygame.mixer.Sound(str(path))
        except (pygame.error, OSError):
            return None

    def _load_lilli(self) -> None:
        for cue in LILLI_CUES:
            try:
                first = shared_character_audio_path(self._project_root, HOST, cue, self.locale)
            except Exception:
                first = None
            if first is None:
                continue
            # Sibling takes of the same family in the same accepted folder.
            pattern = "__".join(first.name.split("__")[:3]) + "__*.wav"
            takes: list[pygame.mixer.Sound] = []
            for path in sorted(first.parent.glob(pattern))[:3]:
                try:
                    takes.append(pygame.mixer.Sound(str(path)))
                except (pygame.error, OSError):
                    continue
            if takes:
                self._lilli[cue] = takes

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("rustle", lambda: _rustle(rate, channels))
        self._sounds.define("found", lambda: _chord(rate, channels, (659.25, 783.99, 1046.5), 0.46))
        self._sounds.define("pop", lambda: _sweep(rate, channels, 0.14, 520.0, 980.0, 7200))
        self._sounds.define("boing", lambda: _boing(rate, channels))
        self._sounds.define("hide", lambda: _sweep(rate, channels, 0.24, 1100.0, 600.0, 3200))
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


def _rustle(rate: int, channels: int) -> pygame.mixer.Sound:
    """Two soft bursts of filtered noise, like leaves being pushed aside."""

    noise = random.Random(7)
    samples: list[float] = []
    duration = 0.32
    smooth = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        burst = math.exp(-((t - 0.07) / 0.045) ** 2) + 0.7 * math.exp(-((t - 0.2) / 0.05) ** 2)
        smooth += (noise.uniform(-1.0, 1.0) - smooth) * 0.35  # gentle low-pass
        samples.append(int(smooth * burst * 9000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _boing(rate: int, channels: int) -> pygame.mixer.Sound:
    """A soft wobbling 'not me' boing (never a buzzer)."""

    samples: list[float] = []
    duration = 0.36
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = 300.0 + 90.0 * math.sin(2.0 * math.pi * 9.0 * t) * math.exp(-4.0 * t)
        phase += 2.0 * math.pi * frequency / rate
        envelope = math.exp(-6.0 * t) * min(1.0, t / 0.01)
        samples.append(int(math.sin(phase) * envelope * 6500))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    per_sample = 2.0 * math.pi / rate
    phases = accumulate([(start + (end - start) * (t / duration)) * per_sample for t in times])
    envelope = [math.sin(math.pi * t / duration) for t in times]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(map(mul, map(math.sin, phases), envelope), channels, scale=volume))


def _chord(rate: int, channels: int, notes: tuple[float, ...], duration: float) -> pygame.mixer.Sound:
    stagger = 0.06
    count = int(rate * duration)
    parts = [
        _decaying_sine(rate, count, frequency, 5.0 / duration, start=order * stagger)
        for order, frequency in enumerate(notes)
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=7000 / max(1, len(notes)) * 1.6))


def _fanfare(rate: int, channels: int) -> pygame.mixer.Sound:
    notes = ((0.0, 0.15, 523.25), (0.12, 0.15, 659.25), (0.24, 0.15, 783.99), (0.36, 0.45, 1046.5))
    count = int(rate * 0.81)  # the last note ends at 0.81 s; the old 0.85 s buffer ended in silence
    parts = [_decaying_sine(rate, count, frequency, 3.5 / length, start=start, stop=start + length) for start, length, frequency in notes]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=10000))


__all__ = ["EFFECTS", "HOST", "LILLI_CUES", "WoodlandAudio"]
