"""Approved speech plus small synthesized effects for Wonder Match.

Speech uses only recorded, approved clips:

* picture names from the platform's shared vocabulary audio bank
  (``shared_vocab_audio_path``; the package carries no noun clips) with the
  usual locale -> base -> English fallback; a name without a recording stays
  silent;
* Lilli's shared takes (``ready.go``, ``celebrate.success``,
  ``encourage.retry``, ``encourage.progress``) from the shared character
  library.

Effects (flip, match chime, gentle miss, sticker pop, whoosh, fanfare) are
synthesized once, after the first frame. Every call fails soft without a mixer, and
speech for the current album is loaded once when a board starts.
"""

from __future__ import annotations

from collections import OrderedDict
import math
from pathlib import Path
import random
from typing import Final, Iterable

import pygame

from greia_platform.localization import (
    LocalizedResources,
    shared_character_audio_path,
    shared_vocab_audio_path,
)
from greia_platform.pygame_audio import DeferredSoundBank, append_mono_pcm16, current_pcm16_mixer_spec

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "lilli"
LILLI_CUES: Final = ("ready.go", "celebrate.success", "encourage.retry", "encourage.progress", "praise.general")
NAME_CACHE_LIMIT: Final = 12


class MemoryAudio:
    """Own the sound bank and speech for one Wonder Match visit."""

    def __init__(
        self,
        resources: LocalizedResources | None = None,
        *,
        locale: str = "en",
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self._resources = resources
        self.locale = locale.split("-")[0]
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._lilli: dict[str, list[pygame.mixer.Sound]] = {}
        self._names: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
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

    def prepare_names(self, subject_ids: Iterable[str]) -> None:
        """Decode the picture-name clips of the coming board once (bounded)."""

        if not self._available:
            return
        for subject_id in subject_ids:
            if subject_id in self._names:
                self._names.move_to_end(subject_id)
                continue
            self._names[subject_id] = self._load_name(subject_id)
            while len(self._names) > NAME_CACHE_LIMIT:
                self._names.popitem(last=False)

    def has_name(self, subject_id: str) -> bool:
        return self._names.get(subject_id) is not None

    def say_name(self, subject_id: str) -> bool:
        """Speak the picture's name; returns False (silent) without a recording."""

        self.last_speech = f"item.{subject_id}"
        if not self._available:
            return False
        if subject_id not in self._names:
            self.prepare_names((subject_id,))
        return self._speak(self._names.get(subject_id))

    def lilli(self, cue: str) -> bool:
        """Play one of Lilli's approved shared takes (random variant)."""

        self.last_speech = cue
        takes = self._lilli.get(cue)
        if not self._available or not takes:
            return False
        return self._speak(self._rng.choice(takes))

    def speech_busy(self) -> bool:
        if not self._available:
            return False
        try:
            return pygame.mixer.Channel(SPEECH_CHANNEL).get_busy()
        except (pygame.error, RuntimeError):
            return False

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

    def _load_name(self, subject_id: str) -> pygame.mixer.Sound | None:
        try:
            path = shared_vocab_audio_path(self._project_root, subject_id, self.locale)
        except Exception:
            return None
        if path is None:
            return None
        try:
            return pygame.mixer.Sound(str(path))
        except (pygame.error, OSError):
            return None

    def _load_lilli(self) -> None:
        for cue in LILLI_CUES:
            first = shared_character_audio_path(self._project_root, HOST, cue, self.locale)
            if first is None:
                continue
            # Sibling takes of the same family in the same accepted folder.
            prefix = first.name.split("__")
            pattern = "__".join(prefix[:3]) + "__*.wav"
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
        self._sounds.define("flip", lambda: _sweep(rate, channels, 0.09, 700.0, 1100.0, 5200))
        self._sounds.define("unflip", lambda: _sweep(rate, channels, 0.08, 900.0, 600.0, 3600))
        self._sounds.define("match", lambda: _chord(rate, channels, (659.25, 783.99, 1046.5), 0.42))
        self._sounds.define("miss", lambda: _sweep(rate, channels, 0.2, 420.0, 330.0, 6000))
        self._sounds.define("pop", lambda: _sweep(rate, channels, 0.14, 520.0, 880.0, 7600))
        self._sounds.define("whoosh", lambda: _sweep(rate, channels, 0.26, 900.0, 1500.0, 3800))
        self._sounds.define("peek", lambda: _chord(rate, channels, (880.0, 1318.5), 0.5))
        self._sounds.define("fanfare", lambda: _fanfare(rate, channels))


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


def _chord(rate: int, channels: int, notes: tuple[float, ...], duration: float) -> pygame.mixer.Sound:
    buffer = bytearray()
    stagger = 0.06
    for index in range(int(rate * duration)):
        t = index / rate
        value = 0.0
        for order, frequency in enumerate(notes):
            local = t - order * stagger
            if local >= 0:
                value += math.sin(2.0 * math.pi * frequency * local) * math.exp(-5.0 * local / duration)
        append_mono_pcm16(buffer, int(value * 7000 / max(1, len(notes)) * 1.6), channels)
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


__all__ = ["HOST", "LILLI_CUES", "MemoryAudio"]
