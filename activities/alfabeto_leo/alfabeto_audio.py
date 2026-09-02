"""Procedural audio synthesis for L'Alfabeto di Leo."""

from __future__ import annotations

import math
from typing import Final

import pygame

MAX_SIMULTANEOUS_CHANNELS: Final[int] = 4


class AlfabetoAudio:
    """Cheerful, gentle musical audio feedback for letter exploration."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        try:
            if pygame.mixer.get_init() is not None:
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError):
            self._available = False

    def play(self, sound_name: str) -> None:
        if not self._available:
            return
        sound = self._sounds.get(sound_name)
        if sound is not None:
            try:
                for i in range(MAX_SIMULTANEOUS_CHANNELS):
                    ch = pygame.mixer.Channel(i)
                    if not ch.get_busy():
                        ch.play(sound)
                        return
                pygame.mixer.Channel(0).play(sound)
            except (pygame.error, RuntimeError):
                pass

    def play_letter(self, char: str) -> None:
        """Play distinct musical chime based on the letter position."""
        idx = max(0, min(25, ord(char.upper()) - ord("A")))
        # Base frequency scale from C4 (261.63 Hz) up to C6 (1046.5 Hz)
        freq = 261.63 * (2.0 ** (idx / 12.0))
        sample_rate = 22050
        sound = self._synthesize_marimba(sample_rate, 0.45, freq)
        try:
            pygame.mixer.Channel(0).play(sound)
        except Exception:
            pass

    def _build_sounds(self) -> None:
        sample_rate = 22050

        # Flip / Pop: bubble pop sound
        self._sounds["pop"] = self._synthesize_pop(sample_rate, 0.22)

        # Wobble / Try again: soft woodblock boing
        self._sounds["wobble"] = self._synthesize_wobble(sample_rate, 0.35)

        # Sparkle: gentle high chime
        self._sounds["sparkle"] = self._synthesize_marimba(sample_rate, 0.5, 987.77)

        # Fanfare: joyful completion chord
        self._sounds["celebrate"] = self._synthesize_fanfare(sample_rate)

    @staticmethod
    def _synthesize_marimba(sample_rate: int, duration: float, freq: float) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        harmonics = (1.0, 0.4, 0.15)
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-6.0 * (t / duration))
            val = 0.0
            for h_idx, amp in enumerate(harmonics):
                val += amp * math.sin(2.0 * math.pi * freq * (h_idx + 1) * t)
            sample_val = int(val * env * 14000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_pop(sample_rate: int, duration: float) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-12.0 * (t / duration))
            freq = 300.0 + 400.0 * (1.0 - t / duration)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 11000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_wobble(sample_rate: int, duration: float) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-4.5 * (t / duration))
            freq = 240.0 + 35.0 * math.sin(18.0 * math.pi * t)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 11000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_fanfare(sample_rate: int) -> pygame.mixer.Sound:
        # F4 - A4 - C5 - F5 triumphant warm chords
        notes = [(0.0, 0.18, 349.23), (0.14, 0.18, 440.00), (0.28, 0.18, 523.25), (0.42, 0.50, 698.46)]
        total_duration = 0.95
        num_samples = int(sample_rate * total_duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            sample_sum = 0.0
            for start, dur, freq in notes:
                if start <= t < start + dur:
                    local_t = t - start
                    env = math.exp(-3.5 * (local_t / dur))
                    sample_sum += math.sin(2.0 * math.pi * freq * local_t) * env
            sample_val = int(sample_sum * 12000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))
