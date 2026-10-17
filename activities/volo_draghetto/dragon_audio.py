"""Sound for Il Volo del Draghetto: tiny synthesized effects + Flash's voice.

Speech uses only owner-approved shared character takes (Flash:
``ready.go``, ``praise.general``, ``encourage.retry``, ``encourage.progress``,
``celebrate.success``) resolved per locale with the platform's English
fallback, plus Flash's owner-approved package line "fly through the rainbow
rings!" (``assets/audio/<locale>/fly_rings.wav``), queued after the first
"ready, go" of a visit. No new lines are generated. Effects are short tones synthesized once, after the first frame (no files).
Everything fails soft without a mixer.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
from typing import Callable, Final
import wave

import pygame

from greia_platform.localization import LocalizationError, activity_resources, shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
SPEAKER: Final = "flash"
SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 5
RATE: Final = 22050
VOICE_CUES: Final = ("ready.go", "praise.general", "encourage.retry", "encourage.progress", "celebrate.success")
# Owner-approved per-Activity lines (``assets/audio/<locale>/<cue>.wav``).
PACKAGE_CUES: Final = ("fly_rings",)
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
MAX_TAKES: Final = 3


def _wav(samples: list[float]) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 30000)) for s in samples))
    return buffer.getvalue()


def _tone(freqs: tuple[float, ...], step: float, volume: float = 0.4, decay: float = 1.0) -> list[float]:
    out: list[float] = []
    n = int(RATE * step)
    for freq in freqs:
        for i in range(n):
            t = i / RATE
            env = max(0.0, 1.0 - t / (step * decay))
            out.append(math.sin(2 * math.pi * freq * t) * env * volume)
    return out


def _sweep(start: float, end: float, seconds: float, volume: float, noise: float = 0.0, seed: int = 7) -> list[float]:
    rng = random.Random(seed)
    out: list[float] = []
    n = int(RATE * seconds)
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = start + (end - start) * t
        phase += 2 * math.pi * freq / RATE
        env = math.sin(math.pi * t)
        out.append((math.sin(phase) * (1 - noise) + (rng.random() * 2 - 1) * noise) * env * volume)
    return out


def effect_recipes() -> dict[str, Callable[[], bytes]]:
    """The effect set as deferred WAV renderers (nothing computed yet)."""

    return {
        "star": lambda: _wav(_tone((1318.5, 1760.0), 0.07, 0.30)),
        "gem": lambda: _wav(_tone((1046.5, 1318.5, 1568.0, 2093.0), 0.06, 0.30)),
        "flap": lambda: _wav(_sweep(420.0, 260.0, 0.14, 0.22, noise=0.45)),
        "ring": lambda: _wav(_tone((784.0, 988.0, 1175.0, 1568.0), 0.09, 0.34)),
        "miss": lambda: _wav(_tone((523.25, 440.0), 0.12, 0.24)),
        "boing": lambda: _wav(_sweep(200.0, 520.0, 0.24, 0.32)),
        "finish": lambda: _wav(_tone((523.25, 659.25, 783.99, 1046.5, 1318.5), 0.12, 0.34)),
        "pop": lambda: _wav(_sweep(700.0, 380.0, 0.09, 0.3)),
    }


def synth_effects() -> dict[str, bytes]:
    """The effect set as WAV bytes (pure function, testable)."""

    return {name: render() for name, render in effect_recipes().items()}


class DragonAudio:
    """Own effect sounds and Flash's speech for one run."""

    def __init__(self, locale: str = "it", *, project_root: Path = PROJECT_ROOT, rng: random.Random | None = None) -> None:
        self.locale = (locale or "it").split("-")[0]
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._speech: dict[str, list[pygame.mixer.Sound]] = {}
        self._available = False
        self.last_speech: str | None = None
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
            for name, render in effect_recipes().items():
                self._sounds.define(name, lambda render=render: pygame.mixer.Sound(io.BytesIO(render())))
            self._load_speech()
            self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    def _load_speech(self) -> None:
        for cue in VOICE_CUES:
            takes: list[pygame.mixer.Sound] = []
            for path in voice_takes(self._project_root, cue, self.locale):
                try:
                    takes.append(pygame.mixer.Sound(str(path)))
                except (pygame.error, OSError):
                    continue
            if takes:
                self._speech[cue] = takes
        try:
            resources = activity_resources(PACKAGE_ROOT, requested_locale=self.locale)
        except LocalizationError:
            return
        for cue in PACKAGE_CUES:
            path = resources.audio_path(cue)
            if path is None:
                continue
            try:
                self._speech[cue] = [pygame.mixer.Sound(str(path))]
            except (pygame.error, OSError):
                continue

    def then(self, cue: str) -> None:
        """Queue one approved cue after the line playing (now when quiet)."""

        self.last_speech = cue
        takes = self._speech.get(cue)
        if not self._available or not takes:
            return
        try:
            channel = pygame.mixer.Channel(SPEECH_CHANNEL)
            if channel.get_busy():
                channel.queue(takes[0])
            else:
                channel.play(takes[0])
        except (pygame.error, RuntimeError):
            return

    def has_speech(self, cue: str) -> bool:
        return cue in self._speech

    def say(self, cue: str) -> None:
        """Speak one approved Flash cue (a random take); silent if missing."""

        self.last_speech = cue
        takes = self._speech.get(cue)
        if not self._available or not takes:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(self._rng.choice(takes))
        except (pygame.error, RuntimeError):
            return

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


def voice_takes(project_root: Path, cue: str, locale: str) -> list[Path]:
    """All approved takes of one Flash cue (locale, else English), max 3."""

    first = shared_character_audio_path(project_root, SPEAKER, cue, locale)
    if first is None:
        return []
    language = first.parent.name
    pattern = f"{SPEAKER}__{language}__{cue}__*.wav"
    return sorted(path for path in first.parent.glob(pattern) if path.is_file())[:MAX_TAKES]


__all__ = ["DragonAudio", "VOICE_CUES", "synth_effects", "voice_takes"]
