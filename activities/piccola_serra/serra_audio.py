"""Approved speech plus small synthesized greenhouse sounds for Piccola Serra.

Speech uses only Tito's owner-accepted shared character takes
(``assets/audio/characters/shared/v0.2/tito``) through
``shared_character_audio_path`` (selected language -> English -> silence):
"ready, go" when a new seed is chosen, praise after a harvest and after the
pictures are in order, the big cheer at the end of a visit, "keep going" as
the first idle nudge and "let's try again" after a care that did not help.
Moments without an approved line ("the plant is thirsty", "what comes
first?") stay pictorial + sound. Sound effects are generated once at
start-up; every call fails soft without a mixer. No generated speech.
"""

from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

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
        self._sounds: dict[str, pygame.mixer.Sound] = {}
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
        self._sounds["seed"] = _sweep(rate, channels, 0.14, 520.0, 300.0, 7000)
        self._sounds["water"] = _trickle(rate, channels)
        self._sounds["grow"] = _chime(rate, channels, (523.25, 659.25, 783.99), step=0.09, volume=8000)
        self._sounds["sun"] = _chime(rate, channels, (880.0, 1108.7, 1318.5), step=0.12, volume=6000)
        self._sounds["wait"] = _ticks(rate, channels)
        self._sounds["harvest"] = _pop(rate, channels)
        self._sounds["basket"] = _chime(rate, channels, (783.99, 1046.5, 1318.5, 1568.0), step=0.08)
        self._sounds["card"] = _chime(rate, channels, (987.77,), step=0.05, volume=7000)
        self._sounds["not_yet"] = _sweep(rate, channels, 0.22, 420.0, 330.0, 5000)
        self._sounds["cloth"] = _swish(rate, channels)
        self._sounds["drip"] = _chime(rate, channels, (1318.5, 1046.5), step=0.12, volume=4500)
        self._sounds["fanfare"] = _chime(rate, channels, (523.25, 659.25, 783.99, 1046.5, 1318.5), step=0.14, volume=10000)


def _chime(rate: int, channels: int, notes: tuple[float, ...], *, step: float = 0.08, volume: int = 9000) -> pygame.mixer.Sound:
    duration = step * len(notes) + 0.35
    buffer = bytearray()
    for index in range(int(rate * duration)):
        t = index / rate
        value = 0.0
        for number, frequency in enumerate(notes):
            start = number * step
            if t >= start:
                local = t - start
                angle = 2.0 * math.pi * frequency * local
                value += (math.sin(angle) + 0.3 * math.sin(2 * angle)) * math.exp(-7.0 * local)
        append_mono_pcm16(buffer, int(max(-1.6, min(1.6, value)) * volume), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _pop(rate: int, channels: int) -> pygame.mixer.Sound:
    buffer = bytearray()
    duration = 0.12
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        phase += 2.0 * math.pi * (480.0 + (1.0 - t / duration) * 360.0) / rate
        append_mono_pcm16(buffer, int(math.sin(phase) * math.sin(math.pi * t / duration) ** 0.8 * 9000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    buffer = bytearray()
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        phase += 2.0 * math.pi * (start + (end - start) * (t / duration)) / rate
        append_mono_pcm16(buffer, int(math.sin(phase) * math.sin(math.pi * t / duration) * volume), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _trickle(rate: int, channels: int) -> pygame.mixer.Sound:
    """Soft watering trickle: short bright blips over a gentle noise bed."""

    noise = random.Random(11)
    buffer = bytearray()
    duration = 0.9
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.sin(math.pi * t / duration) ** 0.6
        blip = math.sin(2 * math.pi * (900 + 300 * math.sin(t * 31)) * t) * (0.5 + 0.5 * math.sin(t * 57))
        value = 0.35 * blip + 0.25 * noise.uniform(-1.0, 1.0)
        append_mono_pcm16(buffer, int(value * envelope * 5000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _ticks(rate: int, channels: int) -> pygame.mixer.Sound:
    """Tick-tock: time passes."""

    buffer = bytearray()
    duration = 1.0
    for index in range(int(rate * duration)):
        t = index / rate
        local = t % 0.25
        frequency = 1500.0 if int(t / 0.25) % 2 == 0 else 1100.0
        value = math.sin(2 * math.pi * frequency * local) * math.exp(-60.0 * local)
        append_mono_pcm16(buffer, int(value * 6000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _swish(rate: int, channels: int) -> pygame.mixer.Sound:
    noise = random.Random(5)
    buffer = bytearray()
    duration = 0.45
    last = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        last = 0.85 * last + 0.15 * noise.uniform(-1.0, 1.0)
        append_mono_pcm16(buffer, int(last * math.sin(math.pi * t / duration) * 9000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


__all__ = ["EFFECTS", "SHARED_CUES", "SerraAudio"]
