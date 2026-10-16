"""Approved speech plus small synthesized effects for My Cute Pet.

Speech uses only recorded, approved clips:

* the pet's picture name from the platform's shared vocabulary audio bank
  (``shared_vocab_audio_path``; ``moon`` is spoken "Luna" in Italian) with
  the usual locale -> base -> English fallback; without a recording the name
  stays pictorial and silent;
* Lilli's shared takes (``ready.go``, ``celebrate.success``,
  ``encourage.retry``, ``encourage.progress``, ``praise.general``).

There are no approved pet-need lines yet ("I'm hungry!"): needs are shown by
body language only. Effects (need chime, "not now" hum, munch, bubbles,
boing, plaster pop, cuddle hearts, yawn, lullaby, room swoosh) are
synthesized once at start-up. Every call fails soft without a mixer.
"""

from __future__ import annotations

from collections import OrderedDict
import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path, shared_vocab_audio_path
from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "lilli"
LILLI_CUES: Final = ("ready.go", "celebrate.success", "encourage.retry", "encourage.progress", "praise.general")
NAME_CACHE_LIMIT: Final = 6
EFFECTS: Final = (
    "chime",
    "nope",
    "pick",
    "munch",
    "bubble",
    "boing",
    "stick",
    "heart",
    "yawn",
    "lullaby",
    "swoosh",
)


class CuccioloAudio:
    """Own the sound bank and speech for one session."""

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
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._lilli: dict[str, list[pygame.mixer.Sound]] = {}
        self._names: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._available = False
        self.last_speech: str | None = None
        self.last_effect: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._load_lilli()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- speech -----------------------------------------------------------------

    def has_name(self, name_id: str) -> bool:
        return self._name_path(name_id) is not None

    def say_name(self, name_id: str) -> bool:
        """Speak the pet's picture name; False (silent) without a recording."""

        self.last_speech = f"name.{name_id}"
        if not self._available:
            return False
        if name_id not in self._names:
            self._names[name_id] = self._load_name(name_id)
            while len(self._names) > NAME_CACHE_LIMIT:
                self._names.popitem(last=False)
        else:
            self._names.move_to_end(name_id)
        return self._speak(self._names.get(name_id))

    def lilli(self, cue: str) -> bool:
        """Play one of Lilli's approved shared takes (random variant)."""

        self.last_speech = cue
        takes = self._lilli.get(cue)
        if not self._available or not takes:
            return False
        return self._speak(self._rng.choice(takes))

    def _speak(self, sound: pygame.mixer.Sound | None) -> bool:
        if sound is None:
            return False
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

    # -- effects ----------------------------------------------------------------

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

    # -- loading ----------------------------------------------------------------

    def _name_path(self, name_id: str) -> Path | None:
        try:
            return shared_vocab_audio_path(self._project_root, name_id, self.locale)
        except Exception:
            return None

    def _load_name(self, name_id: str) -> pygame.mixer.Sound | None:
        path = self._name_path(name_id)
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
        self._sounds["chime"] = _notes(rate, channels, ((0.0, 0.22, 784.0), (0.14, 0.32, 1046.5)), 0.5, 5200)
        self._sounds["nope"] = _notes(rate, channels, ((0.0, 0.16, 392.0), (0.16, 0.24, 330.0)), 0.42, 5600)
        self._sounds["pick"] = _sweep(rate, channels, 0.14, 520.0, 980.0, 7000)
        self._sounds["munch"] = _munch(rate, channels)
        self._sounds["bubble"] = _bubbles(rate, channels)
        self._sounds["boing"] = _boing(rate, channels)
        self._sounds["stick"] = _sweep(rate, channels, 0.09, 900.0, 1500.0, 6500)
        self._sounds["heart"] = _notes(rate, channels, ((0.0, 0.18, 659.25), (0.1, 0.18, 783.99), (0.2, 0.3, 1046.5)), 0.55, 6000)
        self._sounds["yawn"] = _sweep(rate, channels, 0.7, 520.0, 260.0, 4200)
        self._sounds["lullaby"] = _notes(
            rate,
            channels,
            ((0.0, 0.4, 659.25), (0.38, 0.4, 523.25), (0.76, 0.4, 587.33), (1.14, 0.8, 392.0)),
            2.0,
            5200,
        )
        self._sounds["swoosh"] = _swoosh(rate, channels)


def _notes(
    rate: int,
    channels: int,
    notes: tuple[tuple[float, float, float], ...],
    duration: float,
    volume: int,
) -> pygame.mixer.Sound:
    """Soft bell-like notes: (start, length, frequency)."""

    buffer = bytearray()
    for index in range(int(rate * duration)):
        t = index / rate
        value = 0.0
        for start, length, frequency in notes:
            local = t - start
            if 0.0 <= local < length * 2.5:
                attack = min(1.0, local / 0.012)
                value += math.sin(2.0 * math.pi * frequency * local) * attack * math.exp(-3.2 * local / length)
        append_mono_pcm16(buffer, int(value * volume), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


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


def _munch(rate: int, channels: int) -> pygame.mixer.Sound:
    """Two soft crunchy bites (filtered noise bursts)."""

    noise = random.Random(3)
    buffer = bytearray()
    smooth = 0.0
    for index in range(int(rate * 0.34)):
        t = index / rate
        burst = math.exp(-((t - 0.05) / 0.03) ** 2) + 0.8 * math.exp(-((t - 0.2) / 0.03) ** 2)
        smooth += (noise.uniform(-1.0, 1.0) - smooth) * 0.55
        append_mono_pcm16(buffer, int(smooth * burst * 9000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _bubbles(rate: int, channels: int) -> pygame.mixer.Sound:
    """Three little rising bloops."""

    buffer = bytearray()
    phase = 0.0
    duration = 0.42
    for index in range(int(rate * duration)):
        t = index / rate
        local = t % 0.14
        frequency = 500.0 + 1600.0 * local / 0.14
        phase += 2.0 * math.pi * frequency / rate
        envelope = math.sin(math.pi * local / 0.14) * (1.0 - t / duration * 0.5)
        append_mono_pcm16(buffer, int(math.sin(phase) * envelope * 5200), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _boing(rate: int, channels: int) -> pygame.mixer.Sound:
    buffer = bytearray()
    duration = 0.36
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = 330.0 + 120.0 * math.sin(2.0 * math.pi * 7.0 * t) * math.exp(-4.0 * t)
        phase += 2.0 * math.pi * frequency / rate
        envelope = math.exp(-6.0 * t) * min(1.0, t / 0.01)
        append_mono_pcm16(buffer, int(math.sin(phase) * envelope * 6500), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _swoosh(rate: int, channels: int) -> pygame.mixer.Sound:
    noise = random.Random(11)
    buffer = bytearray()
    smooth = 0.0
    duration = 0.36
    for index in range(int(rate * duration)):
        t = index / rate
        smooth += (noise.uniform(-1.0, 1.0) - smooth) * (0.08 + 0.3 * t / duration)
        envelope = math.sin(math.pi * t / duration)
        append_mono_pcm16(buffer, int(smooth * envelope * 9000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


__all__ = ["CuccioloAudio", "EFFECTS", "HOST", "LILLI_CUES"]
