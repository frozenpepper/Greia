"""Approved speech plus small synthesized effects for The Big Seasons Tree.

Speech uses only recorded, approved clips (no generated audio):

* this package's own Tito lines (``welcome``, the four season lines, the four
  weather lines, ``praise_1..3``), found through ``LocalizedResources``
  (locale -> base -> English fallback);
* Tito's shared character takes (``ready.go``, ``celebrate.success``,
  ``encourage.retry``, ``praise.general``);
* picture names from the platform's shared vocabulary bank where an approved
  recording exists (``flower``, ``frog``, ``sun``); otherwise silence.

Clips are decoded lazily, at most ``CLIP_CACHE_LIMIT`` at a time. Effects
(card pop, place chime, soft "not here" boing, whoosh, fanfare, rustle) are
synthesized once, after the first frame in the mixer's own format. Every call fails soft
without a mixer.
"""

from __future__ import annotations

from collections import OrderedDict
from itertools import accumulate, repeat
import math
from operator import add, mul
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import (
    LocalizedResources,
    shared_character_audio_path,
    shared_vocab_audio_path,
)
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "tito"
TITO_CUES: Final = ("ready.go", "celebrate.success", "encourage.retry", "praise.general")
PRAISE_CLIPS: Final = ("praise_1", "praise_2", "praise_3")
CLIP_CACHE_LIMIT: Final = 6
EFFECTS: Final = ("pop", "place", "boing", "whoosh", "fanfare", "rustle")


class TreeAudio:
    """Own the sound bank and speech for one visit to the seasons tree."""

    def __init__(
        self,
        *,
        resources: LocalizedResources | None = None,
        locale: str = "en",
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.locale = locale.split("-")[0].split("_")[0] or "en"
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._clip_paths: dict[str, Path] = {}
        self._clips: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._tito: dict[str, list[Path]] = {}
        self._available = False
        self.last_speech: str | None = None
        try:
            if resources is not None:
                self._clip_paths = dict(resources.speech_paths())
        except Exception:
            self._clip_paths = {}
        self._find_tito_takes()
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- speech -------------------------------------------------------------

    def has_clip(self, cue: str) -> bool:
        return cue in self._clip_paths

    def say(self, cue: str) -> bool:
        """Play one of this package's approved clips (``winter``, ``snow`` ...)."""

        self.last_speech = cue
        if not self._available or cue not in self._clip_paths:
            return False
        return self._speak(self._clip(f"clip:{cue}", self._clip_paths[cue]))

    def praise(self) -> bool:
        available = [cue for cue in PRAISE_CLIPS if cue in self._clip_paths]
        if available:
            return self.say(self._rng.choice(available))
        return self.tito("praise.general")

    def say_name(self, noun: str) -> bool:
        """Speak a picture name from the shared vocabulary bank; False = silent."""

        self.last_speech = f"vocab.{noun}"
        if not self._available:
            return False
        try:
            path = shared_vocab_audio_path(self._project_root, noun, self.locale)
        except Exception:
            path = None
        if path is None:
            return False
        return self._speak(self._clip(f"vocab:{noun}", path))

    def tito(self, cue: str) -> bool:
        """Play one of Tito's approved shared takes (random variant)."""

        self.last_speech = cue
        takes = self._tito.get(cue)
        if not self._available or not takes:
            return False
        path = self._rng.choice(takes)
        return self._speak(self._clip(f"tito:{path.name}", path))

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

    def _find_tito_takes(self) -> None:
        for cue in TITO_CUES:
            try:
                first = shared_character_audio_path(self._project_root, HOST, cue, self.locale)
            except Exception:
                first = None
            if first is None:
                continue
            # Sibling takes of the same family in the same accepted folder.
            pattern = "__".join(first.name.split("__")[:3]) + "__*.wav"
            takes = sorted(first.parent.glob(pattern))[:3]
            if takes:
                self._tito[cue] = takes

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

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("pop", lambda: _sweep(rate, channels, 0.12, 520.0, 920.0, 6800))
        self._sounds.define("place", lambda: _chord(rate, channels, (659.25, 783.99, 1046.5), 0.46))
        self._sounds.define("boing", lambda: _boing(rate, channels))
        self._sounds.define("whoosh", lambda: _sweep(rate, channels, 0.22, 900.0, 520.0, 2800))
        self._sounds.define("fanfare", lambda: _fanfare(rate, channels))
        self._sounds.define("rustle", lambda: _rustle(rate, channels))


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
    """Two soft bursts of filtered noise, like leaves in the wind."""

    noise = random.Random(7)
    samples: list[float] = []
    smooth = 0.0
    for index in range(int(rate * 0.32)):
        t = index / rate
        burst = math.exp(-((t - 0.07) / 0.045) ** 2) + 0.7 * math.exp(-((t - 0.2) / 0.05) ** 2)
        smooth += (noise.uniform(-1.0, 1.0) - smooth) * 0.35
        samples.append(int(smooth * burst * 9000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _boing(rate: int, channels: int) -> pygame.mixer.Sound:
    """A soft wobbling "not here" boing (never a buzzer)."""

    samples: list[float] = []
    phase = 0.0
    for index in range(int(rate * 0.36)):
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


__all__ = ["CLIP_CACHE_LIMIT", "EFFECTS", "HOST", "PRAISE_CLIPS", "TITO_CUES", "TreeAudio"]
