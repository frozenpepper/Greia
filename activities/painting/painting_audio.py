"""Tiny prepared sound bank for Painting (no speech, no files).

Four short soft cues are synthesized once at construction to match the
active PCM16 mixer: ``tick`` (tool/colour chosen), ``pop`` (stamp placed),
``chime`` (a picture went to / came from My Creations) and ``swish``
(a painting was deleted). Audio is fail-soft: without a mixer the bank is
silent and never raises.
"""

from __future__ import annotations

import io
import math
import wave

import pygame

from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec


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


class PaintingSounds:
    """Bounded bank of four prepared cues (all under 0.4 s)."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            spec = current_pcm16_mixer_spec()
            if spec is None:
                return
            rate, channels = spec
            for name, samples in self._recipes(rate).items():
                self._sounds[name] = pygame.mixer.Sound(io.BytesIO(_wav(samples, rate, channels)))
                self._sounds[name].set_volume(0.55)
        except Exception:  # noqa: BLE001 - audio must never break painting
            self._sounds.clear()

    @staticmethod
    def _recipes(rate: int) -> dict[str, list[float]]:
        def tone(seconds: float, voice) -> list[float]:
            count = int(rate * seconds)
            return [voice(i / rate) for i in range(count)]

        return {
            "tick": tone(0.05, lambda t: 7000 * math.sin(2 * math.pi * 880 * t) * math.exp(-60 * t)),
            "pop": tone(
                0.12,
                lambda t: 11000 * math.sin(2 * math.pi * (340 + 900 * t) * t) * math.exp(-28 * t),
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


__all__ = ["PaintingSounds"]
