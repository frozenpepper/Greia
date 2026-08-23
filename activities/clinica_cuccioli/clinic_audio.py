from __future__ import annotations

import io
import math
import struct
from typing import Protocol
import wave

import pygame


class ClinicAudioPort(Protocol):
    """Playback seam consumed by ClinicActivity and replaceable in tests."""

    def play(self, name: str) -> None: ...


class PygameClinicAudio:
    """Own the clinic's small prebuilt procedural sound-effect bank.

    All synthesis happens once during construction. The frame/input path performs
    only a dictionary lookup and ``Sound.play()``. Failure is deliberately soft:
    visual gameplay remains complete when an audio device is unavailable.
    """

    SAMPLE_RATE = 22050

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=self.SAMPLE_RATE,
                    size=-16,
                    channels=1,
                    buffer=512,
                )
            self._build_sound_bank()
        except (pygame.error, OSError, ValueError):
            self._sounds.clear()

    def play(self, name: str) -> None:
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def _build_sound_bank(self) -> None:
        rate = self.SAMPLE_RATE
        self._sounds = {
            "stethoscope": self._sound(
                self._samples(0.15, lambda t: 0.35 * math.exp(-12.0 * t) * math.sin(2.0 * math.pi * 90.0 * t))
            ),
            "bath": self._sound(
                self._samples(
                    0.20,
                    lambda t: 0.25
                    * math.exp(-6.0 * t)
                    * math.sin(2.0 * math.pi * (400.0 + 300.0 * math.sin(t * 40.0)) * t),
                )
            ),
            "bandaid": self._sound(
                self._samples(0.22, lambda t: 0.25 * math.exp(-5.0 * t) * math.sin(2.0 * math.pi * 880.0 * t))
            ),
            "food": self._sound(
                self._samples(
                    0.18,
                    lambda t: 0.28
                    * math.exp(-10.0 * t)
                    * ((2.0 / math.pi) * math.asin(math.sin(2.0 * math.pi * 260.0 * t))),
                )
            ),
            "cuddle": self._sound(
                self._samples(
                    0.25,
                    lambda t: 0.30
                    * math.exp(-4.0 * t)
                    * math.sin(2.0 * math.pi * (587.0 + 200.0 * (t / 0.25)) * t),
                )
            ),
            "win": self._sound(
                self._samples(
                    0.50,
                    lambda t: 0.30
                    * math.exp(-1.8 * t)
                    * math.sin(2.0 * math.pi * self._win_frequency(t) * t),
                )
            ),
        }

    def _samples(self, duration: float, fn) -> list[int]:
        return [
            int(32767.0 * fn(index / self.SAMPLE_RATE))
            for index in range(int(self.SAMPLE_RATE * duration))
        ]

    def _sound(self, samples: list[int]) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(io.BytesIO(_synth_wav(samples, self.SAMPLE_RATE)))

    @staticmethod
    def _win_frequency(t: float) -> float:
        if t < 0.12:
            return 523.0
        if t < 0.24:
            return 659.0
        if t < 0.36:
            return 784.0
        return 1046.0


def _synth_wav(samples: list[int], rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        raw = bytearray()
        for sample in samples:
            clamped = max(-32768, min(32767, int(sample)))
            raw.extend(struct.pack("<h", clamped))
        wav_file.writeframes(raw)
    return buffer.getvalue()
