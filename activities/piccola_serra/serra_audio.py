"""Approved speech plus small synthesized greenhouse sounds for Piccola Serra.

Speech uses only Tito's owner-accepted shared character takes
(``assets/audio/characters/shared/v0.2/tito``) through
``shared_character_audio_path`` (selected language -> English -> silence):
"ready, go" when a new seed is chosen, praise after a harvest and after the
pictures are in order, the big cheer at the end of a visit, "keep going" as
the first idle nudge and "let's try again" after a care that did not help.
Sound effects are generated once, after
the first frame; every call fails soft without a mixer. No generated speech.

Tito's owner-approved greenhouse lines (``assets/audio/<locale>/``) are wired
too: "pick a seed!" after "ready, go", one line per need as the plant shows it
(thirsty, needs light, too much water, ripe), and "what comes first?" when the
stage pictures appear; a chosen seed's plant name comes from the shared
vocabulary bank (``shared_vocab_audio_path``). Lines are queued, never
stacked.
"""

from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import (
    LocalizationError,
    activity_resources,
    shared_character_audio_path,
    shared_vocab_audio_path,
)
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    current_pcm16_mixer_spec,
    decaying_sine,
    mix_samples,
    mono_pcm16_bytes,
    sweep_sound,
)

if __package__:
    from .serra_content import TITO
else:
    from serra_content import TITO

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 5
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
# Owner-approved per-Activity lines (``assets/audio/<locale>/<cue>.wav``).
PACKAGE_CUES: Final[tuple[str, ...]] = (
    "pick_seed",
    "thirsty",
    "needs_light",
    "too_much_water",
    "ripe_pick",
    "what_comes_first",
)
# Plants with a shared vocabulary-bank name (spoken as ``name.<plant>``).
PLANT_NOUNS: Final[tuple[str, ...]] = ("bean", "sunflower", "strawberry", "carrot")
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

    def speaking(self) -> bool:
        if not self._available:
            return False
        try:
            return bool(pygame.mixer.Channel(SPEECH_CHANNEL).get_busy())
        except (pygame.error, RuntimeError):
            return False

    def say_if_quiet(self, cue: str) -> None:
        """Speak a non-essential line only when no other line is playing."""

        if not self.speaking():
            self.say(cue)

    def then(self, cue: str) -> None:
        """Queue one line after the one playing (now when quiet), never stacked.

        Uses the speech channel's own one-slot queue: no polling, and a newer
        queued line replaces an older one.
        """

        self.last_speech = cue
        sound = self._speech.get(cue)
        if not self._available or sound is None:
            return
        try:
            channel = pygame.mixer.Channel(SPEECH_CHANNEL)
            if channel.get_busy():
                channel.queue(sound)
            else:
                channel.play(sound)
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
        for noun in PLANT_NOUNS:
            path = shared_vocab_audio_path(self._project_root, noun, self.locale)
            if path is None:
                continue
            try:
                self._speech[f"name.{noun}"] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue
        try:
            resources = activity_resources(PACKAGE_ROOT, requested_locale=self.locale)
        except LocalizationError:
            return
        for cue in PACKAGE_CUES:
            path = resources.audio_path(cue)
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
        self._sounds.define("seed", lambda: sweep_sound(rate, channels, 0.14, 520.0, 300.0, 7000))
        self._sounds.define("water", lambda: _trickle(rate, channels))
        self._sounds.define("grow", lambda: _chime(rate, channels, (523.25, 659.25, 783.99), step=0.09, volume=8000))
        self._sounds.define("sun", lambda: _chime(rate, channels, (880.0, 1108.7, 1318.5), step=0.12, volume=6000))
        self._sounds.define("wait", lambda: _ticks(rate, channels))
        self._sounds.define("harvest", lambda: _pop(rate, channels))
        self._sounds.define("basket", lambda: _chime(rate, channels, (783.99, 1046.5, 1318.5, 1568.0), step=0.08))
        self._sounds.define("card", lambda: _chime(rate, channels, (987.77,), step=0.05, volume=7000))
        self._sounds.define("not_yet", lambda: sweep_sound(rate, channels, 0.22, 420.0, 330.0, 5000))
        self._sounds.define("cloth", lambda: _swish(rate, channels))
        self._sounds.define("drip", lambda: _chime(rate, channels, (1318.5, 1046.5), step=0.12, volume=4500))
        self._sounds.define("fanfare", lambda: _chime(rate, channels, (523.25, 659.25, 783.99, 1046.5, 1318.5), step=0.14, volume=10000))


def _chime(rate: int, channels: int, notes: tuple[float, ...], *, step: float = 0.08, volume: int = 9000) -> pygame.mixer.Sound:
    duration = step * len(notes) + 0.35
    count = int(rate * duration)
    parts = []
    for number, frequency in enumerate(notes):
        parts.append(decaying_sine(rate, count, frequency, 7.0, start=number * step))
        parts.append(decaying_sine(rate, count, 2.0 * frequency, 7.0, start=number * step, gain=0.3))
    mixed = [max(-1.6, min(1.6, value)) for value in mix_samples(parts)]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(mixed, channels, scale=volume))


def _pop(rate: int, channels: int) -> pygame.mixer.Sound:
    samples: list[float] = []
    duration = 0.12
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        phase += 2.0 * math.pi * (480.0 + (1.0 - t / duration) * 360.0) / rate
        samples.append(int(math.sin(phase) * math.sin(math.pi * t / duration) ** 0.8 * 9000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _trickle(rate: int, channels: int) -> pygame.mixer.Sound:
    """Soft watering trickle: short bright blips over a gentle noise bed."""

    noise = random.Random(11)
    samples: list[float] = []
    duration = 0.9
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = math.sin(math.pi * t / duration) ** 0.6
        blip = math.sin(2 * math.pi * (900 + 300 * math.sin(t * 31)) * t) * (0.5 + 0.5 * math.sin(t * 57))
        value = 0.35 * blip + 0.25 * noise.uniform(-1.0, 1.0)
        samples.append(int(value * envelope * 5000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _ticks(rate: int, channels: int) -> pygame.mixer.Sound:
    """Tick-tock: time passes."""

    samples: list[float] = []
    duration = 1.0
    for index in range(int(rate * duration)):
        t = index / rate
        local = t % 0.25
        frequency = 1500.0 if int(t / 0.25) % 2 == 0 else 1100.0
        value = math.sin(2 * math.pi * frequency * local) * math.exp(-60.0 * local)
        samples.append(int(value * 6000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _swish(rate: int, channels: int) -> pygame.mixer.Sound:
    noise = random.Random(5)
    samples: list[float] = []
    duration = 0.45
    last = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        last = 0.85 * last + 0.15 * noise.uniform(-1.0, 1.0)
        samples.append(int(last * math.sin(math.pi * t / duration) * 9000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


__all__ = ["EFFECTS", "PACKAGE_CUES", "PLANT_NOUNS", "SHARED_CUES", "SerraAudio"]
