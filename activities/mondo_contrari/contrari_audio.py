"""Approved speech plus small synthesized effects for Mondo Contrari.

Speech uses only recorded, approved clips: this package's Flash cues
(``welcome``, the ten concept words ``up`` .. ``slow``, ``praise_1..3`` and
``now_the_opposite`` before a pair's second word)
through ``LocalizedResources`` (selected language -> base -> English ->
silence), and Flash's shared character takes for "let's try again"
(``encourage.retry``) and the end of a visit (``celebrate.success``).
Effects are generated once, after the first frame; every call fails soft without a mixer.
"""

from __future__ import annotations

from collections import deque
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
MAX_PENDING: Final[int] = 3
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
PRAISE_CUES: Final = ("praise_1", "praise_2", "praise_3")
_SHARED: Final[dict[str, str]] = {
    "retry": "encourage.retry",
    "complete": "celebrate.success",
}


class ContrariAudio:
    """Own the speech and effect sounds for one Opposites visit."""

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
        self._speech: dict[str, pygame.mixer.Sound] = {}
        self._sounds = DeferredSoundBank()
        self._pending: deque[str] = deque(maxlen=MAX_PENDING)
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

    def length(self, cue: str) -> float:
        """Seconds of one approved cue (0 when missing or without a mixer)."""

        sound = self._speech.get(cue)
        if sound is None:
            return 0.0
        try:
            return float(sound.get_length())
        except (pygame.error, RuntimeError):
            return 0.0

    def speech_busy(self) -> bool:
        if not self._available:
            return False
        try:
            return pygame.mixer.Channel(SPEECH_CHANNEL).get_busy()
        except (pygame.error, RuntimeError):
            return False

    def say(self, cue: str) -> None:
        """Speak one approved cue now (interrupts; silent when missing)."""

        self._pending.clear()
        self._play_speech(cue)

    def queue(self, cue: str) -> None:
        """Speak after the current line finishes (bounded; call ``update``)."""

        if not self.speech_busy():
            self._play_speech(cue)
            return
        if not self._pending or self._pending[-1] != cue:
            self._pending.append(cue)

    def update(self) -> None:
        if self._pending and not self.speech_busy():
            self._play_speech(self._pending.popleft())

    def praise(self) -> None:
        self.say(self._rng.choice(PRAISE_CUES))

    def encourage(self) -> None:
        self.say("retry")

    def celebrate(self) -> None:
        self.say("complete")

    def stop_speech(self) -> None:
        self._pending.clear()
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

    def _play_speech(self, cue: str) -> None:
        self.last_speech = cue
        sound = self._speech.get(cue)
        if not self._available or sound is None:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
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

    # -- loading ------------------------------------------------------------

    def _load_speech(self) -> None:
        if self._resources is not None:
            files = dict(self._resources.speech_paths())
        else:
            folder = self._package_root / "locales" / self.locale / "audio"
            if not folder.is_dir():
                folder = self._package_root / "locales" / "en" / "audio"
            files = {path.stem: path for path in sorted(folder.glob("*.wav"))}
        for cue, shared_id in _SHARED.items():
            shared = shared_character_audio_path(self._project_root, "flash", shared_id, self.locale)
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
        self._sounds.define("pop", lambda: sweep_sound(rate, channels, 0.12, 520.0, 880.0, 8000))
        self._sounds.define("rise", lambda: sweep_sound(rate, channels, 0.5, 420.0, 1180.0, 6500))
        self._sounds.define("fall", lambda: sweep_sound(rate, channels, 0.5, 900.0, 300.0, 6500))
        self._sounds.define("boing", lambda: sweep_sound(rate, channels, 0.26, 210.0, 520.0, 9000))
        self._sounds.define("whoosh", lambda: sweep_sound(rate, channels, 0.24, 650.0, 1500.0, 4200))
        self._sounds.define("ding", lambda: _chime(rate, channels, 0.4, 1174.7))
        self._sounds.define("boop", lambda: sweep_sound(rate, channels, 0.22, 420.0, 330.0, 7000))
        self._sounds.define("fanfare", lambda: fanfare_sound(rate, channels))


def _chime(rate: int, channels: int, duration: float, frequency: float) -> pygame.mixer.Sound:
    count = int(rate * duration)
    decay = 4.5 / duration
    parts = [
        decaying_sine(rate, count, frequency, decay),
        decaying_sine(rate, count, 2.0 * frequency, decay, gain=0.35),
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(mix_samples(parts), channels, scale=9000))


__all__ = ["ContrariAudio", "PRAISE_CUES"]
