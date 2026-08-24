"""Procedural audio cues for Tre Carte Una Storia."""

from __future__ import annotations

from array import array
import math
from typing import Final

import pygame


_SAMPLE_RATE: Final = 22_050


class StoryAudio:
    """Prepare and play nonverbal interface sounds for story card puzzle and book interactions."""

    def __init__(self) -> None:
        self._clips: dict[str, pygame.mixer.Sound] = {}
        self._channel: pygame.mixer.Channel | None = None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=256)
            pygame.mixer.set_num_channels(8)
            self._channel = pygame.mixer.Channel(0)

            self._clips = {
                "card_swap": self._tone(440.0, 0.05, 0.12),
                "select": self._tone(700.0, 0.04, 0.10),
                "correct": self._chime(),
                "wrong_hint": self._wobble(),
                "save": self._fanfare(),
                "delete": self._tone(280.0, 0.12, 0.15),
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
                    * math.sin(math.pi * (i / count))
                    * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE)
                )
                for i in range(count)
            ),
        )
        return pygame.mixer.Sound(buffer=samples.tobytes())

    @staticmethod
    def _chime() -> pygame.mixer.Sound:
        notes = [523.25, 659.25, 783.99]
        dur = 0.08
        all_samples = array("h")
        for freq in notes:
            count = int(_SAMPLE_RATE * dur)
            for i in range(count):
                env = math.sin(math.pi * (i / count))
                val = int(14000 * env * math.sin(2.0 * math.pi * freq * i / _SAMPLE_RATE))
                all_samples.append(val)
        return pygame.mixer.Sound(buffer=all_samples.tobytes())

    @staticmethod
    def _wobble() -> pygame.mixer.Sound:
        notes = [330.0, 277.0]
        dur = 0.10
        all_samples = array("h")
        for freq in notes:
            count = int(_SAMPLE_RATE * dur)
            for i in range(count):
                env = math.sin(math.pi * (i / count))
                val = int(12000 * env * math.sin(2.0 * math.pi * freq * i / _SAMPLE_RATE))
                all_samples.append(val)
        return pygame.mixer.Sound(buffer=all_samples.tobytes())

    @staticmethod
    def _fanfare() -> pygame.mixer.Sound:
        notes = [440.0, 554.37, 659.25, 880.0]
        dur = 0.07
        all_samples = array("h")
        for freq in notes:
            count = int(_SAMPLE_RATE * dur)
            for i in range(count):
                env = math.sin(math.pi * (i / count))
                val = int(14000 * env * math.sin(2.0 * math.pi * freq * i / _SAMPLE_RATE))
                all_samples.append(val)
        return pygame.mixer.Sound(buffer=all_samples.tobytes())
