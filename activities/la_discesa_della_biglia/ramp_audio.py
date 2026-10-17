"""Approved speech plus small synthesized wooden-toy sounds for Tito's Marble Run.

Speech uses only Tito's owner-accepted shared character takes
(``assets/audio/characters/shared/v0.2/tito``) through
``shared_character_audio_path`` (selected language -> English -> silence):
"ready, go" on the first GO of a board, praise when the marble lands in the
basket, the big cheer at the end of a set, "keep going" as the first idle
nudge and "let's try again" after a miss. Moments without an approved line
(placing or turning a piece, the marble stopping) stay pictorial + sound.
Sound effects are generated once, after the first frame; every call fails soft without a
mixer.
"""

from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    chime_run_sound,
    current_pcm16_mixer_spec,
    mono_pcm16_bytes,
    sweep_sound,
)

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 6
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPEAKER: Final = "tito"
# Activity cue -> Tito's shared take family.
SHARED_CUES: Final[dict[str, str]] = {
    "go": "ready.go",
    "basket": "praise.general",
    "complete": "celebrate.success",
    "nudge": "encourage.progress",
    "retry": "encourage.retry",
}


class RampAudio:
    """Own the speech/sound bank for one Activity run."""

    def __init__(self, locale: str = "en", *, project_root: Path = PROJECT_ROOT) -> None:
        self.locale = (locale or "en").split("-")[0]
        self._project_root = project_root
        self._sounds = DeferredSoundBank()
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
        self._sounds.define("pick", lambda: _knock(rate, channels, 520.0, 0.07, 5200))
        self._sounds.define("place", lambda: _knock(rate, channels, 300.0, 0.12, 8000))
        self._sounds.define("turn", lambda: _knock(rate, channels, 680.0, 0.06, 5200))
        self._sounds.define("remove", lambda: sweep_sound(rate, channels, 0.14, 420.0, 560.0, 4800))
        self._sounds.define("go", lambda: sweep_sound(rate, channels, 0.22, 220.0, 440.0, 6000))
        self._sounds.define("clack", lambda: _knock(rate, channels, 860.0, 0.05, 4200))
        self._sounds.define("bonk", lambda: sweep_sound(rate, channels, 0.16, 300.0, 520.0, 7000))
        self._sounds.define("basket", lambda: chime_run_sound(rate, channels, (523.25, 659.25, 783.99, 1046.5), step=0.1))
        self._sounds.define("lost", lambda: sweep_sound(rate, channels, 0.42, 520.0, 220.0, 6000))
        self._sounds.define("stopped", lambda: _knock(rate, channels, 180.0, 0.18, 6500))
        self._sounds.define("hint", lambda: chime_run_sound(rate, channels, (1318.5, 1760.0), step=0.09, volume=6000))
        self._sounds.define("fanfare", lambda: chime_run_sound(rate, channels, (523.25, 659.25, 783.99, 1046.5, 1318.5), step=0.14, volume=10000))


def _knock(rate: int, channels: int, frequency: float, duration: float, volume: int) -> pygame.mixer.Sound:
    """Short wooden knock: a fast-decaying tone with a little click of noise."""

    noise = random.Random(int(frequency))
    samples: list[float] = []
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.exp(-38.0 * t)
        value = 0.8 * math.sin(2.0 * math.pi * frequency * t) + 0.2 * noise.uniform(-1.0, 1.0) * math.exp(-120.0 * t)
        samples.append(int(value * envelope * volume))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


__all__ = ["RampAudio", "SHARED_CUES"]
