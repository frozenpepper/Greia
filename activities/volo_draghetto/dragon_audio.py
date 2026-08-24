"""Sound effects synthesis and audio management for Il Volo del Draghetto."""

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
        raw = b"".join(struct.pack("<h", max(-32767, min(32767, s))) for s in samples)
        w.writeframes(raw)
    return buf.getvalue()


class DragonAudio:
    """Manages synthesized sound effects with fail-soft fallback."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        # 1. Star collect chime (sparkling major third)
        star_samples = []
        for i in range(4500):
            t = i / 22050.0
            f = 987.77 if t < 0.07 else (1318.51 if t < 0.14 else 1760.0)
            env = max(0.0, 1.0 - t / 0.20)
            star_samples.append(int(math.sin(2 * math.pi * f * t) * env * 14000))
        self._sounds["star"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(star_samples)))

        # 2. Whoosh / Turbo Dash
        whoosh_samples = []
        for i in range(8000):
            t = i / 22050.0
            f = 320.0 + math.sin(t * 16.0) * 140.0 + (1.0 - t / 0.36) * 450.0
            env = math.sin(math.pi * (t / 0.36))
            noise = (random.random() * 2.0 - 1.0) * 0.18
            whoosh_samples.append(int((math.sin(2 * math.pi * f * t) * 0.8 + noise) * env * 15000))
        self._sounds["whoosh"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(whoosh_samples)))

        # 3. Boing (Cloud bounce)
        boing_samples = []
        for i in range(5500):
            t = i / 22050.0
            f = 220.0 + (t / 0.25) * 360.0
            env = max(0.0, 1.0 - t / 0.25)
            boing_samples.append(int(math.sin(2 * math.pi * f * t) * env * 13000))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing_samples)))

        # 4. Pop (Accessory switch)
        pop_samples = []
        for i in range(2500):
            t = i / 22050.0
            f = 600.0 - (t / 0.11) * 300.0
            env = max(0.0, 1.0 - t / 0.11)
            pop_samples.append(int(math.sin(2 * math.pi * f * t) * env * 15000))
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        # 5. Victory Fanfare
        vic_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50]
        for note_idx, note_f in enumerate(notes):
            for i in range(3500):
                t = i / 22050.0
                env = max(0.0, 1.0 - t / 0.15)
                sample = int((math.sin(2 * math.pi * note_f * t) + 0.3 * math.sin(4 * math.pi * note_f * t)) * env * 12000)
                vic_samples.append(sample)
        self._sounds["victory"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(vic_samples)))

    def play(self, name: str) -> None:
        if self._enabled and name in self._sounds:
            try:
                self._sounds[name].play()
            except Exception:
                pass
