"""Treno Numeri — prepared audio bank (synthesized once).

Sounds are synthesized procedurally at construction time so the Activity
ships without large audio assets. Playback is a single ``play(name)`` call.
"""

from __future__ import annotations

import io
import math
import random
import struct
import wave

import pygame


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = bytearray()
        for s in samples:
            clamped = max(-32768, min(32767, int(s)))
            raw.extend(struct.pack("<h", clamped))
        w.writeframes(raw)
    return buf.getvalue()


class TrainAudio:
    """Bounded prepared sound bank for Treno Numeri.

    Sounds are synthesized once when the owner is constructed, then
    played by name. Mixer unavailability in headless tests is tolerated.
    """

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._init_sounds()
        except Exception:
            pass

    def _init_sounds(self) -> None:
        rate = 22050
        # Whistle
        whistle_samples: list[int] = []
        for i in range(int(rate * 0.45)):
            t = i / rate
            env = min(1.0, t * 12.0) * math.exp(-1.5 * t)
            freq = 600.0 if t < 0.15 else 760.0
            val = math.sin(2.0 * math.pi * freq * t) + 0.5 * math.sin(
                2.0 * math.pi * (freq * 1.25) * t
            )
            whistle_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["whistle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(whistle_samples)))

        # Steam chug
        chug_samples: list[int] = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-15.0 * t)
            val = random.uniform(-1.0, 1.0)
            chug_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["chug"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chug_samples)))

        # Musical notes 1..10
        scale = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25, 783.99, 880.00]
        for idx, freq in enumerate(scale):
            samples: list[int] = []
            for i in range(int(rate * 0.22)):
                t = i / rate
                env = math.exp(-5.5 * t)
                val = math.sin(2.0 * math.pi * freq * t)
                samples.append(int(32767.0 * 0.28 * env * val))
            self._sounds[f"load_{idx}"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(samples)))

        # Win Fanfare
        win_samples: list[int] = []
        for i in range(int(rate * 0.60)):
            t = i / rate
            env = math.exp(-2.2 * t)
            note_idx = min(3, int(t / 0.15))
            freq = [523.25, 659.25, 783.99, 1046.50][note_idx]
            val = math.sin(2.0 * math.pi * freq * t)
            win_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["win"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


__all__ = ["TrainAudio"]
