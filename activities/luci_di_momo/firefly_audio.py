"""Small, bounded nonverbal audio owner for Luci di Momo.

Luci teaches visual quantity, not spoken language. The Activity therefore avoids
custom mascot voice generation and uses only optional nonverbal feedback tones.
"""

from __future__ import annotations

from array import array
import math
from typing import Final

import pygame


_SAMPLE_RATE: Final = 22_050


class FireflyAudio:
    """Prepare four tiny tones once and fail soft when output is unavailable."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=1, buffer=256)
            self._sounds = {
                "reveal": self._tone(660.0, 0.08, 0.16),
                "correct": self._tone(880.0, 0.11, 0.18),
                "retry": self._tone(440.0, 0.08, 0.10),
                "complete": self._tone(1040.0, 0.18, 0.18),
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
