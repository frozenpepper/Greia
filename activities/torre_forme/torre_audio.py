"""Approved speech plus small synthesized effects for La Torre delle Forme.

Speech uses only recorded, owner-approved clips (no generated audio):

* Dani's shared character takes (``ready.go``, ``praise.general``,
  ``encourage.retry``, ``encourage.progress``, ``celebrate.success``)
  through ``shared_character_audio_path``;
* the name of what is being built (``rocket``, ``boat``, ``car``, ``cat``,
  ``fish``, ``turtle``) from the shared vocabulary bank through
  ``shared_vocab_audio_path``.

Both follow the platform speech fallback (selected language -> base ->
English -> silence). Clips are decoded lazily into a tiny LRU (the Acer
floor), never all at start-up. The effects (a wooden pick-up tick, a block
clack, a bright chime, a soft "hm-hm" for a block that does not fit, a turn
click, a sparkle run) are synthesized once in the mixer's own format. Every
call fails soft without a mixer.
"""

from __future__ import annotations

from collections import OrderedDict
import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path, shared_vocab_audio_path
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    bell_sound,
    current_pcm16_mixer_spec,
    mono_pcm16_bytes,
)

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "dani"
SHARED_CUES: Final = ("ready.go", "praise.general", "encourage.retry", "encourage.progress", "celebrate.success")
CLIP_CACHE_LIMIT: Final = 6
EFFECTS: Final = ("pick", "clack", "chime", "hum", "turn", "sparkle")


class TorreAudio:
    """Own Dani's speech, build names and the small sound bank for one visit."""

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
        self._paths: dict[str, Path] = {}
        self._sounds = DeferredSoundBank()
        self._clips: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._available = False
        self.last_speech: str | None = None
        self.last_effect: str | None = None
        for cue in SHARED_CUES:
            try:
                path = shared_character_audio_path(project_root, HOST, cue, self.locale)
            except Exception:
                path = None
            if path is not None:
                self._paths[cue] = path
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
        """Play one approved Dani line (shared character cue)."""

        self.last_speech = cue
        path = self._paths.get(cue)
        return self._speak(cue, path)

    def noun(self, noun_id: str | None) -> bool:
        """Say the name of the build (shared vocabulary clip), if there is one."""

        if not noun_id:
            return False
        key = f"vocab.{noun_id}"
        self.last_speech = key
        if key not in self._paths:
            try:
                path = shared_vocab_audio_path(self._project_root, noun_id, self.locale)
            except Exception:
                path = None
            if path is None:
                return False
            self._paths[key] = path
        return self._speak(key, self._paths[key])

    def stop_speech(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

    def _speak(self, key: str, path: Path | None) -> bool:
        if not self._available or path is None:
            return False
        sound = self._clip(key, path)
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
        self._sounds.define("pick", lambda: bell_sound(rate, channels, (987.8,), 0.14, 2200))
        self._sounds.define("clack", lambda: _wood(rate, channels))
        self._sounds.define("chime", lambda: bell_sound(rate, channels, (784.0, 1174.7), 0.5, 2400))
        self._sounds.define("hum", lambda: _hum(rate, channels))
        self._sounds.define("turn", lambda: bell_sound(rate, channels, (698.5, 880.0), 0.18, 1900))
        self._sounds.define("sparkle", lambda: bell_sound(rate, channels, (1046.5, 1318.5, 1568.0, 2093.0), 1.0, 1900))


def _wood(rate: int, channels: int) -> pygame.mixer.Sound:
    """A short wooden "tock" as a block settles into place."""

    samples: list[float] = []
    duration = 0.12
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.exp(-28.0 * t)
        value = 0.7 * math.sin(2 * math.pi * 300.0 * t) + 0.3 * math.sin(2 * math.pi * 720.0 * t)
        samples.append(int(value * envelope * 9000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _hum(rate: int, channels: int) -> pygame.mixer.Sound:
    """A soft two-note "hm-hm" for a block that does not fit (never a buzzer)."""

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


__all__ = ["CLIP_CACHE_LIMIT", "EFFECTS", "HOST", "SHARED_CUES", "TorreAudio"]
