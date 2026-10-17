"""Approved speech plus small synthesized chimes for La Casa del Dieci.

Speech uses only recorded, approved clips: this package's cues
(``prompt_compose_1..10``, ``prompt_add``, ``prompt_take_away``,
``prompt_missing_part``, ``correct_1..3``, ``retry_1..2``, ``friends_coming``,
``fireflies_home``, ``count_lights``) through ``LocalizedResources`` and Dani's
shared ``celebrate.success`` take for the end of a visit. Chimes are generated once, after the first frame;
every call fails soft without a mixer.
"""

from __future__ import annotations

from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources, shared_character_audio_path
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    current_pcm16_mixer_spec,
    decaying_sine,
    fanfare_sound,
    mix_samples,
    mono_pcm16_bytes,
    sweep_sound,
)

SPEECH_CHANNEL: Final[int] = 0
FIRST_SFX_CHANNEL: Final[int] = 2
LAST_SFX_CHANNEL: Final[int] = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
# C major pentatonic climbing two octaves: one gentle step per counted room.
_COUNT_NOTES: Final[tuple[float, ...]] = (
    523.25, 587.33, 659.25, 783.99, 880.00, 1046.5, 1174.7, 1318.5, 1568.0, 1760.0,
)
_SHARED: Final[dict[str, str]] = {"complete": "celebrate.success"}
PRAISE_CUES: Final = ("correct_1", "correct_2", "correct_3")
RETRY_CUES: Final = ("retry_1", "retry_2")


class TenHouseAudio:
    """Own the speech/chime sounds for one Ten House visit."""

    def __init__(
        self,
        package_root: Path | None = None,
        locale: str = "it",
        resources: LocalizedResources | None = None,
        *,
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self._package_root = package_root if package_root is not None else Path(__file__).resolve().parent
        self._resources = resources
        self.locale = locale.split("-")[0]
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._speech: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        self.last_speech: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._load_speech()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- speech -------------------------------------------------------------

    def has_speech(self, cue: str) -> bool:
        return cue in self._speech

    def speech_busy(self) -> bool:
        if not self._available:
            return False
        try:
            return pygame.mixer.Channel(SPEECH_CHANNEL).get_busy()
        except (pygame.error, RuntimeError):
            return False

    def say(self, cue: str) -> None:
        """Speak one approved cue now (silent when the clip is missing)."""

        self.last_speech = cue
        sound = self._speech.get(cue)
        if not self._available or sound is None:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return

    def say_if_quiet(self, cue: str) -> None:
        """Speak a non-essential line only when no other line is playing."""

        if not self.speech_busy():
            self.say(cue)

    def praise(self) -> None:
        self.say(self._rng.choice(PRAISE_CUES))

    def encourage(self) -> None:
        self.say(self._rng.choice(RETRY_CUES))

    def stop_speech(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

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

    def chime(self, number: int) -> None:
        self.play(f"chime_{max(1, min(10, int(number)))}")

    # -- loading ------------------------------------------------------------

    def _load_speech(self) -> None:
        if self._resources is not None:
            files = dict(self._resources.speech_paths())
        else:
            folder = self._package_root / "assets" / "audio" / self.locale
            if not folder.is_dir():
                folder = folder.parent / "en"
            files = {path.stem: path for path in sorted(folder.glob("*.wav"))}
        for cue, shared_id in _SHARED.items():
            shared = shared_character_audio_path(self._project_root, "dani", shared_id, self.locale)
            if shared is not None:
                files[cue] = shared
        for stem, path in files.items():
            try:
                self._speech[stem] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        for index, frequency in enumerate(_COUNT_NOTES, start=1):
            self._sounds.define(f"chime_{index}", lambda frequency=frequency: _chime(rate, channels, 0.38, frequency))
        self._sounds.define("pop", lambda: sweep_sound(rate, channels, 0.14, 520.0, 880.0, 8000))
        self._sounds.define("unpop", lambda: sweep_sound(rate, channels, 0.14, 700.0, 420.0, 7000))
        self._sounds.define("whoosh", lambda: sweep_sound(rate, channels, 0.26, 900.0, 1500.0, 4200))
        self._sounds.define("boop", lambda: sweep_sound(rate, channels, 0.22, 420.0, 330.0, 7000))
        self._sounds.define("fanfare", lambda: fanfare_sound(rate, channels, 11000))


def _chime(rate: int, channels: int, duration: float, frequency: float) -> pygame.mixer.Sound:
    count = int(rate * duration)
    decay = 4.5 / duration
    parts = [
        decaying_sine(rate, count, frequency, decay),
        decaying_sine(rate, count, 2.0 * frequency, decay, gain=0.35),
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(mix_samples(parts), channels, scale=10000))


__all__ = ["PRAISE_CUES", "RETRY_CUES", "TenHouseAudio"]
