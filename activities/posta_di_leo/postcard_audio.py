"""Procedural nonverbal audio feedback for Posta di Leo."""

from __future__ import annotations

from array import array
import math
from typing import Final

import pygame


_SAMPLE_RATE: Final = 22_050


class PostcardAudio:
    """Prepare and play nonverbal interface sounds for postcard interactions."""

    def __init__(self) -> None:
        self._clips: dict[str, pygame.mixer.Sound] = {}
        self._channel: pygame.mixer.Channel | None = None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=256)
            pygame.mixer.set_num_channels(8)
            self._channel = pygame.mixer.Channel(0)

            self._clips = {
                "type": self._tone(640.0, 0.03, 0.10),
                "stamp": self._tone(220.0, 0.08, 0.20),
                "send": self._fanfare(),
                "delete": self._tone(300.0, 0.12, 0.15),
                "select": self._tone(880.0, 0.05, 0.14),
                "full": self._tone(330.0, 0.16, 0.20),
            }
        except (pygame.error, ValueError, OSError):
            self._clips = {}

    def play(self, cue: str) -> None:
        sound = self._clips.get(cue)
        if sound is None or self._channel is None:
            return
        try:
            self._channel.play(sound)
        except pygame.error:
            return

    @staticmethod
    def _tone(frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        count = max(1, int(_SAMPLE_RATE * duration))
        amplitude = max(0, min(32767, int(32767 * volume)))
        samples = array(
            "h",
            (
                int(
                    amplitude
                    * math.sin(math.pi * (i / count))  # Smooth envelope
                    * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE)
                )
                for i in range(count)
            ),
        )
        return pygame.mixer.Sound(buffer=samples.tobytes())

    @staticmethod
    def _fanfare() -> pygame.mixer.Sound:
        notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
        dur = 0.07
        all_samples = array("h")
        for freq in notes:
            count = int(_SAMPLE_RATE * dur)
            for i in range(count):
                env = math.sin(math.pi * (i / count))
                val = int(14000 * env * math.sin(2.0 * math.pi * freq * i / _SAMPLE_RATE))
                all_samples.append(val)
        return pygame.mixer.Sound(buffer=all_samples.tobytes())
