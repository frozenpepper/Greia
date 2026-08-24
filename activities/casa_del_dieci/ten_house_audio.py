"""Procedural nonverbal audio feedback for La Casa del Dieci."""

from __future__ import annotations

from array import array
import math
from typing import Final

import pygame


_SAMPLE_RATE: Final = 22_050


class TenHouseAudio:
    """Prepare low-resource procedural feedback tones and fail soft when unavailable."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=1, buffer=256)
            self._sounds = {
                "toggle": self._tone(520.0, 0.05, 0.14),
                "correct": self._tone(880.0, 0.12, 0.18),
                "retry": self._tone(360.0, 0.09, 0.12),
                "complete": self._tone(1040.0, 0.22, 0.20),
            }
        except (pygame.error, ValueError):
            self._sounds = {}

    def play(self, cue: str) -> None:
        sound = self._sounds.get(cue)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            return

    @staticmethod
    def _tone(frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        count = max(1, int(_SAMPLE_RATE * duration))
        amplitude = max(0, min(32767, int(32767 * volume)))
        samples = array(
            "h",
            (
                int(amplitude * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE))
                for i in range(count)
            ),
        )
        return pygame.mixer.Sound(buffer=samples.tobytes())
