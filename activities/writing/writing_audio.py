"""Tiny prepared sound bank for Writing (no speech, no files).

Four short soft cues are synthesized once, after the first frame to match the active
PCM16 mixer: ``tick`` (a control or paper colour was chosen), ``pop`` (an
emoji went onto the page), ``chime`` (a page went to / came from My
Creations) and ``swish`` (a page was deleted). Typing itself stays silent so
long stories never become noisy. Audio is fail-soft: without a mixer the bank
is silent and never raises.
"""

from __future__ import annotations

import io
import math
import wave
from typing import Callable

import pygame

from greia_platform.pygame_audio import DeferredSoundBank, append_mono_pcm16, current_pcm16_mixer_spec


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


def _cue(samples: list[float], rate: int, channels: int) -> pygame.mixer.Sound:
    sound = pygame.mixer.Sound(io.BytesIO(_wav(samples, rate, channels)))
    sound.set_volume(0.5)
    return sound


class WritingSounds:
    """Bounded bank of four prepared cues (all under 0.4 s)."""

    def __init__(self) -> None:
        self._sounds = DeferredSoundBank()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            spec = current_pcm16_mixer_spec()
            if spec is None:
                return
            rate, channels = spec
            for name, recipe in self._recipes(rate).items():
                self._sounds.define(name, lambda recipe=recipe: _cue(recipe(), rate, channels))
        except Exception:  # noqa: BLE001 - audio must never break writing
            self._sounds.clear()

    @staticmethod
    def _recipes(rate: int) -> dict[str, Callable[[], list[float]]]:
        """Name -> sample generator; nothing is computed until a cue is built."""

        def tone(seconds: float, voice) -> Callable[[], list[float]]:
            count = int(rate * seconds)
            return lambda: [voice(i / rate) for i in range(count)]

        return {
            "tick": tone(0.05, lambda t: 7000 * math.sin(2 * math.pi * 880 * t) * math.exp(-60 * t)),
            "pop": tone(
                0.12,
                lambda t: 10000 * math.sin(2 * math.pi * (420 + 900 * t) * t) * math.exp(-28 * t),
            ),
            "chime": tone(
                0.38,
                lambda t: 9000
                * (math.sin(2 * math.pi * (784 if t < 0.12 else 1046.5) * t) * 0.8 + 0.2 * math.sin(2 * math.pi * 2093 * t))
                * math.exp(-7 * t),
            ),
            "swish": tone(
                0.22,
                lambda t: 6000 * math.sin(2 * math.pi * (620 - 1400 * t) * t) * math.sin(math.pi * t / 0.22),
            ),
        }

    def play(self, name: str) -> None:
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass


__all__ = ["WritingSounds"]
