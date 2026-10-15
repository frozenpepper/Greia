"""Shape Garden sounds: tiny synthesized cues plus Dani's approved clips.

Speech uses only owner-approved recordings: Dani's shared ``ready.go``
(first visit to an empty garden), ``encourage.progress`` (a growing garden),
``celebrate.success`` (a ghost picture is complete) and ``praise.general``
(a picture was shared). Shape names have no approved recording yet, so
naming stays pictorial and silent.

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
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

if __package__:
    from .garden_content import SHAPE_KINDS
else:  # pragma: no cover - direct script fallback
    from garden_content import SHAPE_KINDS

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
SPEECH_CHANNEL: Final = 0
_NOTES: Final = (523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.7, 1318.5)
SPEECH_CUES: Final = ("ready.go", "encourage.progress", "celebrate.success", "praise.general")


def _wav(samples: list[float], rate: int, channels: int) -> bytes:
    raw = bytearray()
    for value in samples:
        append_mono_pcm16(raw, int(value), channels)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(raw))
    return buffer.getvalue()


class GardenSounds:
    """Bounded bank of short cues and four Dani clips for one session."""

    def __init__(self, locale: str = "en", *, project_root: Path = PROJECT_ROOT) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
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
            for name, samples in self._recipes(rate).items():
                sound = pygame.mixer.Sound(io.BytesIO(_wav(samples, rate, channels)))
                sound.set_volume(0.5)
                self._sounds[name] = sound
            for cue in SPEECH_CUES:
                path = shared_character_audio_path(project_root, "dani", cue, locale or "en")
                if path is not None:
                    self._speech[cue] = pygame.mixer.Sound(str(path))
        except Exception:  # noqa: BLE001 - audio must never break the garden
            self._sounds.clear()
            self._speech.clear()

    @staticmethod
    def _recipes(rate: int) -> dict[str, list[float]]:
        def tone(seconds: float, voice) -> list[float]:
            return [voice(i / rate) for i in range(int(rate * seconds))]

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

    def say(self, cue: str) -> None:
        """Dani speaks one approved shared clip (silent when it is missing)."""
        self.last_speech = cue
        sound = self._speech.get(cue)
        if sound is None:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            pass


__all__ = ["GardenSounds", "SPEECH_CUES"]
