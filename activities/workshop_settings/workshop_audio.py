"""Approved speech plus tiny synthesized chimes for My Greia.

Speech uses only owner-approved recordings:

* this package's ``activity.title`` clip ("My Greia") as the welcome;
* the shared canonical-cast introductions (``_intros/<lang>/<id>.ogg``) when
  the child picks a cast friend as their avatar for the first time;
* the friend's shared ``celebrate.success`` take as the reaction to a change,
  spaced out so rapid tapping never becomes a stream of voices.

Speech falls back selected language -> English -> silence. Chimes are
generated once, after the first frame; every call fails soft without a mixer.
"""

from __future__ import annotations

import math
from pathlib import Path
import random
import time
from typing import Callable, Final

import pygame

from greia_platform.localization import LocalizedResources, LocaleTag, shared_character_audio_path
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    current_pcm16_mixer_spec,
    mono_pcm16_bytes,
    sweep_sound,
)

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_content import SPEECH_GAP_SECONDS
except ImportError:
    from workshop_content import SPEECH_GAP_SECONDS  # type: ignore[no-redef]

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 3
PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
_MAX_SPEECH_CACHE: Final = 8


class MyGreiaAudio:
    """Own the welcome, reactions and chimes for one My Greia visit."""

    def __init__(
        self,
        resources: LocalizedResources | None = None,
        *,
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._resources = resources
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._clock = clock
        language = "en"
        if resources is not None:
            language = resources.context.selected.language
        self.language = LocaleTag.parse(language).language
        self._sounds = DeferredSoundBank()
        self._speech: dict[Path, pygame.mixer.Sound] = {}
        self._introduced: set[str] = set()
        self._next_speech = 0.0
        self.last_speech: str | None = None
        self._available = False
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- speech -----------------------------------------------------------------

    def welcome(self) -> None:
        path = None
        if self._resources is not None:
            try:
                path = self._resources.audio_path("activity.title")
            except Exception:
                path = None
        self._say("welcome", path)

    def react(self, character: str, *, avatar_changed: bool) -> None:
        """Friend reaction to a change: intro the first time, else a cheer."""

        now = self._clock()
        if avatar_changed and character not in self._introduced:
            self._introduced.add(character)
            if self._say(f"intro.{character}", self._intro_path(character)):
                self._next_speech = now + SPEECH_GAP_SECONDS
                return
        if now < self._next_speech:
            return
        path = shared_character_audio_path(self._project_root, character, "celebrate.success", self.language)
        if self._say(f"celebrate.{character}", path):
            self._next_speech = now + SPEECH_GAP_SECONDS

    def stop_speech(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

    def _intro_path(self, character: str) -> Path | None:
        root = self._project_root / "assets" / "audio" / "characters" / "shared" / "v0.2" / "_intros"
        for language in dict.fromkeys((self.language, "en")):
            candidate = root / language / f"{character}.ogg"
            if candidate.is_file():
                return candidate
        return None

    def _say(self, cue: str, path: Path | None) -> bool:
        self.last_speech = cue if path is not None else None
        if path is None or not self._available:
            return False
        sound = self._speech.get(path)
        if sound is None:
            try:
                sound = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                return False
            if len(self._speech) >= _MAX_SPEECH_CACHE:
                self._speech.pop(next(iter(self._speech)))
            self._speech[path] = sound
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

    # -- effects ------------------------------------------------------------------

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
        self._sounds.define("pick", lambda: _sparkle(rate, channels))
        self._sounds.define("tab", lambda: sweep_sound(rate, channels, 0.12, 520.0, 780.0, 6500))
        self._sounds.define("undo", lambda: sweep_sound(rate, channels, 0.16, 780.0, 470.0, 6500))


def _sparkle(rate: int, channels: int) -> pygame.mixer.Sound:
    """Two quick rising bell notes: a gentle 'ta-da' for a new choice."""

    notes = ((0.0, 0.22, 1046.5), (0.08, 0.30, 1568.0))
    samples: list[float] = []
    for index in range(int(rate * 0.4)):
        t = index / rate
        value = 0.0
        for start, length, frequency in notes:
            if start <= t < start + length:
                local = t - start
                angle = 2.0 * math.pi * frequency * local
                value += (math.sin(angle) + 0.3 * math.sin(2.0 * angle)) * math.exp(-5.0 * local / length)
        samples.append(int(value * 7000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


__all__ = ["MyGreiaAudio"]
