"""Shape Garden sounds: tiny synthesized cues plus Dani's approved clips.

Speech uses only owner-approved recordings: Dani's shared ``ready.go``
(first visit to an empty garden), ``encourage.progress`` (a growing garden,
when the package line below is missing),
``celebrate.success`` (a ghost picture is complete) and ``praise.general``
(a picture was shared); Dani's two owner-approved package lines
(``assets/audio/<locale>/``: "drag a shape into the garden!" after the first
"ready, go", "what a beautiful garden!" for a growing garden); and each
planted shape's name from the shared vocabulary bank (``shape_<kind>``,
``shared_vocab_audio_path``), only when no other line is playing.

Cues are synthesized once for the active PCM16 mixer: one soft ``pop`` per
shape kind (a C-major pentatonic step each, so every shape has its own
voice), ``tick`` (tool), ``snap`` (it fits a ghost slot), ``chime``
(shared / picture complete) and ``swish`` (removed). Audio is fail-soft:
without a mixer everything is silent and nothing raises.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import wave
from typing import Callable, Final

import pygame

from greia_platform.localization import (
    LocalizationError,
    activity_resources,
    shared_character_audio_path,
    shared_vocab_audio_path,
)
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

if __package__:
    from .garden_content import SHAPE_KINDS
else:  # pragma: no cover - direct script fallback
    from garden_content import SHAPE_KINDS

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
SPEECH_CHANNEL: Final = 0
_NOTES: Final = (523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.7, 1318.5)
SPEECH_CUES: Final = ("ready.go", "encourage.progress", "celebrate.success", "praise.general")
PACKAGE_ROOT: Final = Path(__file__).resolve().parent
# Owner-approved per-Activity lines (``assets/audio/<locale>/<cue>.wav``).
PACKAGE_CUES: Final = ("drag_shape", "beautiful_garden")
# The manifest is language-neutral (``*``) but the package ships these four
# locale bundles, so its spoken lines resolve through them.
PACKAGE_LOCALES: Final = ("it", "en", "es", "fr")


def package_line_paths(locale: str) -> dict[str, Path]:
    """Resolve the package lines (locale -> base -> English -> silence)."""

    try:
        resources = activity_resources(PACKAGE_ROOT, requested_locale=locale, supported_locales=PACKAGE_LOCALES)
    except LocalizationError:
        return {}
    found: dict[str, Path] = {}
    for cue in PACKAGE_CUES:
        path = resources.audio_path(cue)
        if path is not None:
            found[cue] = path
    return found


def _wav(samples: list[float], rate: int, channels: int) -> bytes:
    raw = mono_pcm16_bytes(samples, channels)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(raw)
    return buffer.getvalue()


def _cue(samples: list[float], rate: int, channels: int) -> pygame.mixer.Sound:
    sound = pygame.mixer.Sound(io.BytesIO(_wav(samples, rate, channels)))
    sound.set_volume(0.5)
    return sound


class GardenSounds:
    """Bounded bank of short cues and four Dani clips for one session."""

    def __init__(self, locale: str = "en", *, project_root: Path = PROJECT_ROOT) -> None:
        self._sounds = DeferredSoundBank()
        self._speech: dict[str, pygame.mixer.Sound] = {}
        self.last_speech: str | None = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            spec = current_pcm16_mixer_spec()
            if spec is None:
                return
            rate, channels = spec
            pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), 4))
            for name, recipe in self._recipes(rate).items():
                self._sounds.define(name, lambda recipe=recipe: _cue(recipe(), rate, channels))
            for cue in SPEECH_CUES:
                path = shared_character_audio_path(project_root, "dani", cue, locale or "en")
                if path is not None:
                    self._speech[cue] = pygame.mixer.Sound(str(path))
            for cue, path in package_line_paths(locale or "en").items():
                self._speech[cue] = pygame.mixer.Sound(str(path))
            for kind in SHAPE_KINDS:
                path = shared_vocab_audio_path(project_root, f"shape_{kind}", locale or "en")
                if path is not None:
                    self._speech[f"shape.{kind}"] = pygame.mixer.Sound(str(path))
        except Exception:  # noqa: BLE001 - audio must never break the garden
            self._sounds.clear()
            self._speech.clear()

    @staticmethod
    def _recipes(rate: int) -> dict[str, Callable[[], list[float]]]:
        """Name -> sample generator; nothing is computed until a cue is built."""

        def tone(seconds: float, voice) -> Callable[[], list[float]]:
            return lambda: [voice(i / rate) for i in range(int(rate * seconds))]

        recipes = {
            f"pop.{kind}": tone(
                0.16,
                lambda t, f=note: 9000 * math.sin(2 * math.pi * f * t * (1 + 0.15 * math.exp(-30 * t))) * math.exp(-18 * t),
            )
            for kind, note in zip(SHAPE_KINDS, _NOTES)
        }
        recipes["tick"] = tone(0.05, lambda t: 6500 * math.sin(2 * math.pi * 880 * t) * math.exp(-60 * t))
        recipes["snap"] = tone(
            0.22,
            lambda t: 8000 * (math.sin(2 * math.pi * 1046.5 * t) + 0.4 * math.sin(2 * math.pi * 1568 * t)) * math.exp(-14 * t),
        )
        recipes["chime"] = tone(
            0.42,
            lambda t: 8500
            * (math.sin(2 * math.pi * (784 if t < 0.13 else 1046.5) * t) * 0.8 + 0.2 * math.sin(2 * math.pi * 2093 * t))
            * math.exp(-6 * t),
        )
        recipes["swish"] = tone(
            0.22, lambda t: 5500 * math.sin(2 * math.pi * (620 - 1400 * t) * t) * math.sin(math.pi * t / 0.22),
        )
        return recipes

    def play(self, name: str) -> None:
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def pop(self, kind: str) -> None:
        self.play(f"pop.{kind}")

    def name(self, kind: str) -> None:
        """Say a planted shape's name, only when no other line is playing."""

        try:
            if pygame.mixer.get_init() and pygame.mixer.Channel(SPEECH_CHANNEL).get_busy():
                return
        except (pygame.error, RuntimeError):
            return
        self.say(f"shape.{kind}")

    def then(self, cue: str) -> None:
        """Queue one clip after the line playing (now when quiet)."""

        self.last_speech = cue
        sound = self._speech.get(cue)
        if sound is None:
            return
        try:
            channel = pygame.mixer.Channel(SPEECH_CHANNEL)
            if channel.get_busy():
                channel.queue(sound)
            else:
                channel.play(sound)
        except (pygame.error, RuntimeError):
            pass

    def say(self, cue: str) -> bool:
        """Dani speaks one approved clip; False (silent) when it is missing."""
        self.last_speech = cue
        sound = self._speech.get(cue)
        if sound is None:
            return False
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True


__all__ = ["GardenSounds", "PACKAGE_CUES", "SPEECH_CUES", "package_line_paths"]
