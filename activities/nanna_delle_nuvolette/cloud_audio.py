"""Procedural, gentle bedtime audio synthesis for Nanna delle Nuvolette."""

from __future__ import annotations

import math
from typing import Final

import pygame


MAX_SIMULTANEOUS_CHANNELS: Final[int] = 2


class CloudAudio:
    """Manage soft nonverbal bedtime chimes, yawns, and rustles."""

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
                # Find available channel
                for i in range(MAX_SIMULTANEOUS_CHANNELS):
                    ch = pygame.mixer.Channel(i)
                    if not ch.get_busy():
                        ch.play(sound)
                        return
                # If all busy, play on channel 0
                pygame.mixer.Channel(0).play(sound)
            except (pygame.error, RuntimeError):
                pass

    def _build_sounds(self) -> None:
        sample_rate = 22050
        # 1. Chime: soft celesta pentatonic tone (F5, C6)
        self._sounds["chime"] = self._synthesize_tone(sample_rate, 0.45, 698.46, harmonics=(1.0, 0.4, 0.15))
        # 2. Yawn: soft descending sigh (330Hz down to 220Hz)
        self._sounds["yawn"] = self._synthesize_descending(sample_rate, 0.70, 330.0, 220.0)
        # 3. Rustle / Tuck: soft cotton pat (180Hz warm pulse)
        self._sounds["rustle"] = self._synthesize_tone(sample_rate, 0.22, 180.0, harmonics=(1.0, 0.2))
        # 4. Star snap: tiny sparkle chime (1046Hz)
        self._sounds["star"] = self._synthesize_tone(sample_rate, 0.30, 1046.5, harmonics=(1.0, 0.5, 0.2))

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
            env = math.exp(-4.0 * (t / duration))
            val = 0.0
            for h_idx, amp in enumerate(harmonics):
                val += amp * math.sin(2.0 * math.pi * freq * (h_idx + 1) * t)
            sample_val = int(val * env * 12000)
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
            env = math.sin(math.pi * (t / duration))  # Bell envelope
            freq = start_freq + (end_freq - start_freq) * (t / duration)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 10000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))
