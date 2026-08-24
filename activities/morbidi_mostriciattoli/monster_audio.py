"""Procedural nonverbal audio feedback for Morbidi Mostriciattoli."""

from __future__ import annotations

import math
from typing import Final

import pygame


MAX_SIMULTANEOUS_CHANNELS: Final[int] = 2


class MonsterAudio:
    """Manage nonverbal monster part selection, surprise roll, and save chimes."""

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

    def _build_sounds(self) -> None:
        sample_rate = 22050
        # 1. Pop: tactile rubber pop
        self._sounds["pop"] = self._synthesize_tone(sample_rate, 0.12, 440.0, harmonics=(1.0, 0.6))
        # 2. Squash: descending squish
        self._sounds["squash"] = self._synthesize_descending(sample_rate, 0.20, 520.0, 260.0)
        # 3. Surprise: cheerful ascending arpeggio chime
        self._sounds["surprise"] = self._synthesize_tone(sample_rate, 0.40, 659.25, harmonics=(1.0, 0.4, 0.2))
        # 4. Save: triumphant camera shutter chime (880Hz + 1318Hz)
        self._sounds["save"] = self._synthesize_tone(sample_rate, 0.50, 880.0, harmonics=(1.0, 0.5, 0.3))
        # 5. Tap: tiny click
        self._sounds["tap"] = self._synthesize_tone(sample_rate, 0.08, 600.0, harmonics=(1.0,))

    @staticmethod
    def _synthesize_tone(
        sample_rate: int,
        duration: float,
        freq: float,
        harmonics: tuple[float, ...] = (1.0,),
    ) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
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
    def _synthesize_descending(
        sample_rate: int,
        duration: float,
        start_freq: float,
        end_freq: float,
    ) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.sin(math.pi * (t / duration))
            freq = start_freq + (end_freq - start_freq) * (t / duration)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 12000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))
