"""Approved speech plus small synthesized wooden-toy sounds for Bridge Builders.

Speech uses only the owner-accepted shared character takes
(``assets/audio/characters/shared/v0.2/<friend>``) through
``shared_character_audio_path`` (selected language -> English -> silence), in
the voice of the friend who is crossing: "ready, go" on the first GO of a
crossing, praise at the picnic, the big cheer at the end of a set, "keep
going" as the first idle nudge and "let's try again" after a stop. Moments
without an approved line (placing a plank, a plank landing or bending) stay
pictorial + sound. Sound effects are generated once at start-up; every call
fails soft without a mixer.
"""

from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 6
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
# Activity cue -> the speaker's shared take family.
SHARED_CUES: Final[dict[str, str]] = {
    "go": "ready.go",
    "arrive": "praise.general",
    "complete": "celebrate.success",
    "nudge": "encourage.progress",
    "retry": "encourage.retry",
}


class BridgeAudio:
    """Own the speech/sound bank for one Activity run (one speaker loaded at a time)."""

    def __init__(self, locale: str = "en", *, project_root: Path = PROJECT_ROOT) -> None:
        self.locale = (locale or "en").split("-")[0]
        self._project_root = project_root
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._speech: dict[str, pygame.mixer.Sound] = {}
        self._speaker: str | None = None
        self._available = False
        self.last_speech: str | None = None
        self.last_sound: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    def use_speaker(self, speaker: str) -> None:
        """Load the takes of the friend who speaks now (drops the previous ones)."""

        if speaker == self._speaker:
            return
        self._speaker = speaker
        self._speech.clear()
        if not self._available:
            return
        for cue, family in SHARED_CUES.items():
            path = shared_character_audio_path(self._project_root, speaker, family, self.locale)
            if path is None:
                continue
            try:
                self._speech[cue] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue

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

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds["pick"] = _knock(rate, channels, 520.0, 0.07, 5200)
        self._sounds["place"] = _knock(rate, channels, 300.0, 0.12, 8000)
        self._sounds["remove"] = _sweep(rate, channels, 0.14, 420.0, 560.0, 4800)
        self._sounds["clack"] = _knock(rate, channels, 860.0, 0.05, 4200)
        self._sounds["go"] = _sweep(rate, channels, 0.22, 220.0, 440.0, 6000)
        self._sounds["creak"] = _sweep(rate, channels, 0.5, 180.0, 140.0, 3200)
        self._sounds["thunk"] = _knock(rate, channels, 200.0, 0.16, 8500)
        self._sounds["sparkle"] = _chime(rate, channels, (1318.5, 1567.98), step=0.07, volume=5200)
        self._sounds["bend"] = _sweep(rate, channels, 0.4, 260.0, 150.0, 6500)
        self._sounds["stop"] = _knock(rate, channels, 180.0, 0.18, 6500)
        self._sounds["arrive"] = _chime(rate, channels, (523.25, 659.25, 783.99, 1046.5), step=0.1)
        self._sounds["hint"] = _chime(rate, channels, (1318.5, 1760.0), step=0.09, volume=6000)
        self._sounds["fanfare"] = _chime(rate, channels, (523.25, 659.25, 783.99, 1046.5, 1318.5), step=0.14, volume=10000)


def _chime(rate: int, channels: int, notes: tuple[float, ...], *, step: float = 0.08, volume: int = 9000) -> pygame.mixer.Sound:
    tail = 0.35
    buffer = bytearray()
    for index in range(int(rate * (step * len(notes) + tail))):
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


def _knock(rate: int, channels: int, frequency: float, duration: float, volume: int) -> pygame.mixer.Sound:
    """Short wooden knock: a fast-decaying tone with a little click of noise."""

    noise = random.Random(int(frequency))
    buffer = bytearray()
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.exp(-38.0 * t)
        value = 0.8 * math.sin(2.0 * math.pi * frequency * t) + 0.2 * noise.uniform(-1.0, 1.0) * math.exp(-120.0 * t)
        append_mono_pcm16(buffer, int(value * envelope * volume), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


__all__ = ["BridgeAudio", "SHARED_CUES"]
