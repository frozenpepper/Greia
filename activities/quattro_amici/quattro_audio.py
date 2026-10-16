"""Sounds and character voices for Quattro Amici in Fila.

* Tiny wooden effects (slide, clack, taps, a gentle "boop", counting chimes
  and a short fanfare) are synthesised once at startup for the active mixer.
* Speech uses ONLY the owner-approved shared character takes of Flash and
  Leo, resolved through ``shared_character_audio_path`` (selected language,
  then English, then silence). A cue's sibling takes (``__01``, ``__02``…)
  are loaded lazily on first use and kept in a small bounded table.

Every method is a silent no-op when the mixer is unavailable.
"""

from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

VOICE_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 1
LAST_SFX_CHANNEL: Final = 3
MAX_TAKES: Final = 3
SPEAKERS: Final = ("flash", "leo")
# Ascending notes for counting the discs of a winning row (C major pentatonic).
_COUNT_NOTES: Final = (523.25, 587.33, 659.25, 783.99, 880.0)


class QuattroAudio:
    """Wooden effects and Flash/Leo reactions for one Activity session."""

    def __init__(self, locale: str = "it", *, project_root: Path | None = None, rng: random.Random | None = None) -> None:
        self.locale = locale.split("-")[0]
        self._project_root = project_root or Path(__file__).resolve().parents[2]
        self._rng = rng or random.Random()
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._voices: dict[tuple[str, str], list[pygame.mixer.Sound]] = {}
        self._available = False
        try:
            if pygame.mixer.get_init() is not None:
                self._synthesize_effects()
                self._available = True
        except (pygame.error, RuntimeError):
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    # -- effects -------------------------------------------------------------------

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

    def play_hover(self) -> None:
        self.play("hover")

    def play_click(self) -> None:
        self.play("click")

    def play_drop_slide(self) -> None:
        self.play("slide")

    def play_drop_clack(self) -> None:
        self.play("clack")

    def chime(self, step: int) -> None:
        """One counting note (1-based) for a disc of the winning row."""

        self.play(f"chime_{max(1, min(len(_COUNT_NOTES), int(step)))}")

    # -- voice ---------------------------------------------------------------------

    def say(self, speaker: str, cue: str, take: int | None = None) -> None:
        """Play one approved take of ``cue`` by ``speaker`` (random when ``take`` is None)."""

        if not self._available or speaker not in SPEAKERS:
            return
        takes = self._takes(speaker, cue)
        if not takes:
            return
        index = self._rng.randrange(len(takes)) if take is None else max(0, min(len(takes) - 1, take - 1))
        try:
            pygame.mixer.Channel(VOICE_CHANNEL).play(takes[index])
        except (pygame.error, RuntimeError):
            return

    def _takes(self, speaker: str, cue: str) -> list[pygame.mixer.Sound]:
        key = (speaker, cue)
        cached = self._voices.get(key)
        if cached is not None:
            return cached
        sounds: list[pygame.mixer.Sound] = []
        first = shared_character_audio_path(self._project_root, speaker, cue, self.locale)
        if first is not None:
            # Sibling takes of the same approved cue (``__01``, ``__02`` ...).
            prefix = first.name.rsplit("__", 1)[0]
            for path in sorted(first.parent.glob(f"{prefix}__*.wav"))[:MAX_TAKES] or [first]:
                try:
                    sounds.append(pygame.mixer.Sound(str(path)))
                except (pygame.error, OSError):
                    continue
        self._voices[key] = sounds
        return sounds

    # -- synthesis -------------------------------------------------------------------

    def _synthesize_effects(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds["slide"] = _sweep(rate, channels, 0.2, 420.0, 240.0, 7000)
        self._sounds["clack"] = _clack(rate, channels)
        self._sounds["hover"] = _tap(rate, channels, 380.0)
        self._sounds["click"] = _tap(rate, channels, 520.0)
        self._sounds["boop"] = _sweep(rate, channels, 0.22, 420.0, 300.0, 7000)
        self._sounds["pop"] = _sweep(rate, channels, 0.14, 520.0, 880.0, 7500)
        for index, frequency in enumerate(_COUNT_NOTES, start=1):
            self._sounds[f"chime_{index}"] = _chime(rate, channels, frequency)
        self._sounds["fanfare"] = _fanfare(rate, channels)


def _sound(raw: bytearray) -> pygame.mixer.Sound:
    return pygame.mixer.Sound(buffer=bytes(raw))


def _sweep(rate: int, channels: int, seconds: float, start: float, end: float, amplitude: int) -> pygame.mixer.Sound:
    raw = bytearray()
    count = int(rate * seconds)
    phase = 0.0
    for i in range(count):
        t = i / count
        phase += 2.0 * math.pi * (start + (end - start) * t) / rate
        envelope = math.sin(math.pi * t) ** 1.2
        append_mono_pcm16(raw, int(math.sin(phase) * envelope * amplitude), channels)
    return _sound(raw)


def _clack(rate: int, channels: int) -> pygame.mixer.Sound:
    """Wood-on-wood impact with a tiny bounce."""

    raw = bytearray()
    for i in range(int(rate * 0.12)):
        t = i / rate
        value = (math.sin(2 * math.pi * 220.0 * t) * 0.7 + math.sin(2 * math.pi * 540.0 * t) * 0.3) * math.exp(-32.0 * t)
        if t > 0.045:
            t2 = t - 0.045
            value += math.sin(2 * math.pi * 280.0 * t2) * math.exp(-40.0 * t2) * 0.35
        append_mono_pcm16(raw, int(value * 15000), channels)
    return _sound(raw)


def _tap(rate: int, channels: int, frequency: float) -> pygame.mixer.Sound:
    raw = bytearray()
    for i in range(int(rate * 0.05)):
        t = i / rate
        append_mono_pcm16(raw, int(math.sin(2 * math.pi * frequency * t) * math.exp(-45.0 * t) * 9000), channels)
    return _sound(raw)


def _chime(rate: int, channels: int, frequency: float) -> pygame.mixer.Sound:
    raw = bytearray()
    count = int(rate * 0.3)
    for i in range(count):
        t = i / rate
        value = math.sin(2 * math.pi * frequency * t) * 0.75 + math.sin(4 * math.pi * frequency * t) * 0.25
        append_mono_pcm16(raw, int(value * math.exp(-9.0 * t) * 10000), channels)
    return _sound(raw)


def _fanfare(rate: int, channels: int) -> pygame.mixer.Sound:
    """Warm rising C-E-G-C chime."""

    notes = ((0.0, 523.25), (0.09, 659.25), (0.18, 783.99), (0.27, 1046.5))
    raw = bytearray()
    for i in range(int(rate * 0.7)):
        t = i / rate
        value = 0.0
        for start, frequency in notes:
            if t >= start:
                local = t - start
                value += math.sin(2 * math.pi * frequency * local) * math.exp(-5.0 * local) * 0.4
        append_mono_pcm16(raw, int(value * 11000), channels)
    return _sound(raw)


__all__ = ["QuattroAudio", "SPEAKERS"]
