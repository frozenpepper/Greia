"""Approved speech plus small synthesized effects for Specchi Magici.

Speech uses only recorded, owner-approved clips (no generated audio):

* this package's Lilli lines (``assets/audio/<locale>/*.wav``: ``welcome``,
  ``prompt_place``, ``correct_1..5``, ``retry_1..2``, ``mosaic_complete``,
  ``shape_circle|square|triangle|semicircle``), found through the
  localization resolver (selected language -> base -> English -> silence);
* Lilli's shared character takes (``celebrate.success``, ``ready.go``)
  through ``shared_character_audio_path``.

Clips are decoded lazily into a tiny LRU (the Acer floor), never all at
start-up. The effects (a tile click, a bright chime, a soft "hm-hm" for a
tile that does not belong, a sparkle run along the mirror) are synthesized
once in the mixer's own format. Every call fails soft without a mixer.
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

from greia_platform.localization import LocalizedResources, shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

if __package__:
    from .mirror_model import ShapeKind
else:
    from mirror_model import ShapeKind

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "lilli"
SHARED_CUES: Final = ("celebrate.success", "ready.go")
PACKAGE_CUES: Final = (
    "welcome", "prompt_place", "correct_1", "correct_2", "correct_3", "correct_4", "correct_5",
    "retry_1", "retry_2", "mosaic_complete",
    "shape_circle", "shape_square", "shape_triangle", "shape_semicircle",
)
# Spoken shape names exist for these four tiles only (rhombus/heart stay silent).
SPOKEN_SHAPES: Final = frozenset({ShapeKind.CIRCLE, ShapeKind.SQUARE, ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE})
CLIP_CACHE_LIMIT: Final = 6
EFFECTS: Final = ("pick", "place", "chime", "hum", "sparkle")


class MirrorAudio:
    """Own Lilli's speech and the small sound bank for one visit."""

    def __init__(
        self,
        *,
        locale: str = "en",
        resources: LocalizedResources | None = None,
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.locale = locale.split("-")[0].split("_")[0] or "en"
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._paths: dict[str, Path] = {}
        self._sounds = DeferredSoundBank()
        self._clips: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._available = False
        self.last_speech: str | None = None
        self.last_effect: str | None = None
        self._find_paths(resources)
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    @property
    def cues(self) -> frozenset[str]:
        """Speech cues that resolved to an approved recording."""

        return frozenset(self._paths)

    # -- speech -------------------------------------------------------------

    def say(self, cue: str) -> bool:
        """Play one approved line (package cue or shared ``lilli`` cue)."""

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

    def praise(self) -> bool:
        return self.say(f"correct_{self._rng.randint(1, 5)}")

    def shape_name(self, kind: ShapeKind) -> bool:
        if kind not in SPOKEN_SHAPES:
            return False
        return self.say(f"shape_{kind.value}")

    def stop_speech(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

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

    def _find_paths(self, resources: LocalizedResources | None) -> None:
        if resources is not None:
            try:
                found = resources.speech_paths()
            except Exception:
                found = {}
            for cue in PACKAGE_CUES:
                if cue in found:
                    self._paths[cue] = Path(found[cue])
        for cue in SHARED_CUES:
            try:
                path = shared_character_audio_path(self._project_root, HOST, cue, self.locale)
            except Exception:
                path = None
            if path is not None:
                self._paths[cue] = path

    # -- effects ------------------------------------------------------------

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

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("pick", lambda: _bell(rate, channels, (987.8,), 0.16, 2400))
        self._sounds.define("place", lambda: _bell(rate, channels, (659.3,), 0.22, 3000))
        self._sounds.define("chime", lambda: _bell(rate, channels, (784.0, 1174.7), 0.5, 2600))
        self._sounds.define("hum", lambda: _hum(rate, channels))
        self._sounds.define("sparkle", lambda: _bell(rate, channels, (1318.5, 1568.0, 2093.0), 0.9, 1900))


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


def _bell(rate: int, channels: int, notes: tuple[float, ...], duration: float, volume: int) -> pygame.mixer.Sound:
    """Soft celesta notes, one after another (a quick rising run for >1 note)."""

    count = int(rate * duration)
    step = duration / (len(notes) + 1)
    parts = [
        _decaying_sine(rate, count, frequency, 5.0 / duration, start=order * step, attack=0.006)
        for order, frequency in enumerate(notes)
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=volume))


def _hum(rate: int, channels: int) -> pygame.mixer.Sound:
    """A soft two-note "hm-hm" for a tile that does not belong (never a buzzer)."""

    samples: list[float] = []
    notes = ((0.0, 440.0), (0.2, 392.0))
    duration = 0.5
    for index in range(int(rate * duration)):
        t = index / rate
        value = 0.0
        for start, frequency in notes:
            local = t - start
            if 0.0 <= local < 0.28:
                value += math.sin(2 * math.pi * frequency * local) * math.sin(math.pi * local / 0.28)
        samples.append(int(value * 2800))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


__all__ = ["CLIP_CACHE_LIMIT", "EFFECTS", "HOST", "MirrorAudio", "PACKAGE_CUES", "SHARED_CUES", "SPOKEN_SHAPES"]
