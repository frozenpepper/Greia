"""Approved speech plus small synthesized garden sounds for Il Labirinto Magico.

Speech uses only Tito's owner-accepted shared character takes
(``assets/audio/characters/shared/v0.2/tito``) through
``shared_character_audio_path`` (selected language -> English -> silence):
"ready, go" when a maze starts, praise when Tito reaches his tent, the big
cheer at the end of a visit, "keep going" as the first idle nudge and "let's
try again" when the tent or a door is still closed. Moments without an
approved line (a star found, the key picked up) stay pictorial + chime.
Sound effects are generated once at start-up; every call fails soft without
a mixer.
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
LAST_SFX_CHANNEL: Final = 5
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPEAKER: Final = "tito"
# Activity cue -> Tito's shared take family.
SHARED_CUES: Final[dict[str, str]] = {
    "start": "ready.go",
    "solved": "praise.general",
    "complete": "celebrate.success",
    "nudge": "encourage.progress",
    "retry": "encourage.retry",
}


class LabyrinthAudio:
    """Own the speech/sound bank for one Activity run."""

    def __init__(
        self,
        locale: str = "en",
        *,
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.locale = (locale or "en").split("-")[0]
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
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

    # -- loading ------------------------------------------------------------

    def _load_speech(self) -> None:
        for cue, family in SHARED_CUES.items():
            path = shared_character_audio_path(self._project_root, SPEAKER, family, self.locale)
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
        self._sounds["step"] = _sweep(rate, channels, 0.09, 380.0, 300.0, 4200)
        self._sounds["bump"] = _thud(rate, channels)
        self._sounds["star"] = _chime(rate, channels, (1046.5, 1318.5, 1568.0))
        self._sounds["key"] = _chime(rate, channels, (1568.0, 2093.0, 1568.0, 2093.0), step=0.06, volume=7000)
        self._sounds["door"] = _sweep(rate, channels, 0.32, 240.0, 180.0, 6500)
        self._sounds["locked"] = _sweep(rate, channels, 0.22, 420.0, 330.0, 6500)
        self._sounds["hint"] = _chime(rate, channels, (1318.5, 1760.0), step=0.09, volume=6000)
        self._sounds["tent"] = _chime(rate, channels, (523.25, 659.25, 783.99, 1046.5), step=0.12)
        self._sounds["fanfare"] = _chime(rate, channels, (523.25, 659.25, 783.99, 1046.5, 1318.5), step=0.14, volume=10000)


def _chime(
    rate: int,
    channels: int,
    notes: tuple[float, ...],
    *,
    step: float = 0.08,
    volume: int = 9000,
) -> pygame.mixer.Sound:
    tail = 0.35
    duration = step * len(notes) + tail
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


def _thud(rate: int, channels: int) -> pygame.mixer.Sound:
    """Soft leafy bump: low sine plus a little rustle."""

    noise = random.Random(7)
    buffer = bytearray()
    for index in range(int(rate * 0.14)):
        t = index / rate
        envelope = math.exp(-28.0 * t)
        value = 0.75 * math.sin(2.0 * math.pi * 150.0 * t) + 0.25 * noise.uniform(-1.0, 1.0)
        append_mono_pcm16(buffer, int(value * envelope * 7000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


# Back-compat alias for older imports.
MazeAudio = LabyrinthAudio

__all__ = ["LabyrinthAudio", "MazeAudio", "SHARED_CUES"]
