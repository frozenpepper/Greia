"""Sound effects synthesis and audio management for Colline Allegre."""

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


class CollineAudio:
    """Manages synthesized sound effects with fail-soft fallback."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        self._engine_channel: pygame.mixer.Channel | None = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        rate = 22050

        # 1. Star chime (sparkling major triad arpeggio)
        star_samples: list[int] = []
        for i in range(5000):
            t = i / float(rate)
            f = 1046.50 if t < 0.07 else (1318.51 if t < 0.14 else 1567.98)
            env = max(0.0, 1.0 - t / 0.22)
            sample = math.sin(2.0 * math.pi * f * t) + 0.3 * math.sin(4.0 * math.pi * f * t)
            star_samples.append(int(sample * env * 14000))
        self._sounds["star"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(star_samples, rate)))

        # 2. Comical Spring BOING! (cartoon boxing glove pitch bend up with wobble)
        boing_samples: list[int] = []
        for i in range(12000):
            t = i / float(rate)
            dur = 12000.0 / rate
            base_f = 150.0 + (t / dur) * 480.0
            wobble = math.sin(2.0 * math.pi * 18.0 * t) * 35.0
            f = base_f + wobble
            env = max(0.0, 1.0 - t / dur)
            # Rich comical harmonic timbre
            val = math.sin(2.0 * math.pi * f * t) * 0.7 + math.sin(4.0 * math.pi * f * t) * 0.3
            boing_samples.append(int(val * env * 18000))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing_samples, rate)))

        # 3. Jump whoosh (air rush)
        whoosh_samples: list[int] = []
        for i in range(7000):
            t = i / float(rate)
            dur = 7000.0 / rate
            f = 260.0 + (1.0 - t / dur) * 350.0
            noise = (random.random() * 2.0 - 1.0) * 0.35
            env = math.sin(math.pi * (t / dur))
            val = (math.sin(2.0 * math.pi * f * t) * 0.65 + noise) * env
            whoosh_samples.append(int(val * 13000))
        self._sounds["whoosh"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(whoosh_samples, rate)))

        # 4. Tire squeak on sharp brake
        squeak_samples: list[int] = []
        for i in range(4500):
            t = i / float(rate)
            dur = 4500.0 / rate
            f = 1200.0 - (t / dur) * 500.0 + math.sin(t * 80.0) * 60.0
            env = max(0.0, 1.0 - t / dur)
            noise = (random.random() * 2.0 - 1.0) * 0.15
            squeak_samples.append(int((math.sin(2.0 * math.pi * f * t) + noise) * env * 10000))
        self._sounds["squeak"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(squeak_samples, rate)))

        # 5. Celebration fanfare (joyful triumphant brass chords)
        fanfare_samples: list[int] = []
        notes = [523.25, 659.25, 783.99, 1046.50]
        for note in notes:
            for i in range(3200):
                t = i / float(rate)
                env = max(0.0, 1.0 - t / 0.14)
                sample = (
                    math.sin(2.0 * math.pi * note * t)
                    + 0.4 * math.sin(4.0 * math.pi * note * t)
                    + 0.15 * math.sin(6.0 * math.pi * note * t)
                )
                fanfare_samples.append(int(sample * env * 12500))
        self._sounds["fanfare"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples, rate)))

        # 6. Perfect landing chime
        landing_samples: list[int] = []
        for i in range(5000):
            t = i / float(rate)
            f = 783.99 if t < 0.1 else 1046.50
            env = max(0.0, 1.0 - t / 0.22)
            landing_samples.append(int(math.sin(2.0 * math.pi * f * t) * env * 15000))
        self._sounds["perfect_landing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(landing_samples, rate)))

    def play(self, name: str) -> None:
        if self._enabled and name in self._sounds:
            try:
                self._sounds[name].play()
            except Exception:
                pass

    def stop_all(self) -> None:
        if self._enabled:
            try:
                pygame.mixer.stop()
            except Exception:
                pass
