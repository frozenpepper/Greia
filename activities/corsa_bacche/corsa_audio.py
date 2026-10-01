"""Procedural sound effects synthesis and audio playback for Corsa delle Bacche."""

from __future__ import annotations

import io
import math
import random
import struct
import wave
from typing import Final

import pygame

SAMPLE_RATE: Final[int] = 22050


def _synth_wav(samples: list[int], rate: int = SAMPLE_RATE) -> bytes:
    """Pack signed 16-bit mono samples into in-memory WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        clamped = (max(-32767, min(32767, int(s))) for s in samples)
        raw = b"".join(struct.pack("<h", s) for s in clamped)
        w.writeframes(raw)
    return buf.getvalue()


class CorsaAudio:
    """Manages synthesized procedural audio effects with graceful fallback."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled: bool = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SAMPLE_RATE, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        # 1. Pop (Sweet berry eaten)
        pop_samples = []
        duration = 0.12
        n_samples = int(duration * SAMPLE_RATE)
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            freq = 480.0 + (1.0 - t / duration) * 320.0
            env = math.sin(math.pi * (t / duration)) ** 0.8
            val = math.sin(2.0 * math.pi * freq * t) * env * 16000
            pop_samples.append(int(val))
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        # 2. Chimes (Golden berry collected)
        chime_samples = []
        notes = [880.0, 1108.73, 1318.51, 1760.0]
        step = int(0.06 * SAMPLE_RATE)
        total_len = step * len(notes) + int(0.2 * SAMPLE_RATE)
        chime_raw = [0.0] * total_len
        for idx, freq in enumerate(notes):
            start = idx * step
            for i in range(int(0.25 * SAMPLE_RATE)):
                t = i / SAMPLE_RATE
                env = math.exp(-10.0 * t)
                harm = math.sin(2.0 * math.pi * freq * t) + 0.3 * math.sin(4.0 * math.pi * freq * t)
                if start + i < total_len:
                    chime_raw[start + i] += harm * env * 8000
        chime_samples = [int(v) for v in chime_raw]
        self._sounds["chime"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chime_samples)))

        # 3. Star Fanfare (Rainbow Star Berry eaten - 6s powerup activation)
        star_notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
        fanfare_step = int(0.07 * SAMPLE_RATE)
        fanfare_total = fanfare_step * len(star_notes) + int(0.3 * SAMPLE_RATE)
        fanfare_raw = [0.0] * fanfare_total
        for idx, freq in enumerate(star_notes):
            start = idx * fanfare_step
            for i in range(int(0.35 * SAMPLE_RATE)):
                t = i / SAMPLE_RATE
                env = math.exp(-8.0 * t)
                val = (math.sin(2.0 * math.pi * freq * t) + 0.4 * math.sin(4.0 * math.pi * freq * t)) * env * 9000
                if start + i < fanfare_total:
                    fanfare_raw[start + i] += val
        self._sounds["star_fanfare"] = pygame.mixer.Sound(io.BytesIO(_synth_wav([int(v) for v in fanfare_raw])))

        # 4. Dizzy Squeak (Rescuing / tagging a dizzy critter)
        squeak_samples = []
        duration = 0.22
        n_samples = int(duration * SAMPLE_RATE)
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            freq = 700.0 + math.sin(t * 55.0) * 350.0 + (t / duration) * 400.0
            env = math.sin(math.pi * (t / duration))
            val = math.sin(2.0 * math.pi * freq * t) * env * 14000
            squeak_samples.append(int(val))
        self._sounds["dizzy_squeak"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(squeak_samples)))

        # 5. Bounce (Momo gentle wobble / bounce after hazard encounter)
        bounce_samples = []
        duration = 0.28
        n_samples = int(duration * SAMPLE_RATE)
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            freq = 280.0 - (t / duration) * 120.0 + math.sin(t * 30.0) * 40.0
            env = math.exp(-7.0 * t)
            val = math.sin(2.0 * math.pi * freq * t) * env * 15000
            bounce_samples.append(int(val))
        self._sounds["bounce"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bounce_samples)))

        # 6. Apple Munch (Restorative apple at 0 hearts)
        apple_samples = []
        duration = 0.35
        n_samples = int(duration * SAMPLE_RATE)
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Noise-based cheerful crunch
            noise = (random.random() * 2.0 - 1.0)
            crunch = math.sin(2.0 * math.pi * 320.0 * t) * 0.4 + noise * 0.6
            env = (math.sin(math.pi * (t / 0.15)) if t < 0.15 else math.sin(math.pi * ((t - 0.15) / 0.2))) * math.exp(-3.0 * t)
            apple_samples.append(int(crunch * env * 13000))
        self._sounds["apple_munch"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(apple_samples)))

        # 7. Level Clear Fanfare
        clear_notes = [523.25, 659.25, 783.99, 1046.5, 880.0, 1046.5]
        clear_step = int(0.10 * SAMPLE_RATE)
        clear_total = clear_step * len(clear_notes) + int(0.4 * SAMPLE_RATE)
        clear_raw = [0.0] * clear_total
        for idx, freq in enumerate(clear_notes):
            start = idx * clear_step
            note_dur = 0.35 if idx == len(clear_notes) - 1 else 0.20
            for i in range(int(note_dur * SAMPLE_RATE)):
                t = i / SAMPLE_RATE
                env = math.exp(-6.0 * t)
                val = (math.sin(2.0 * math.pi * freq * t) + 0.35 * math.sin(3.0 * math.pi * freq * t)) * env * 9000
                if start + i < clear_total:
                    clear_raw[start + i] += val
        self._sounds["level_clear"] = pygame.mixer.Sound(io.BytesIO(_synth_wav([int(v) for v in clear_raw])))

    def play(self, sound_name: str) -> None:
        """Play a synthesized sound effect if audio is enabled."""
        if not self._enabled:
            return
        sound = self._sounds.get(sound_name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass
