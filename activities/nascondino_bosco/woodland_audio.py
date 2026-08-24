"""Audio synthesis and playback management for Nascondino nel Bosco."""

from __future__ import annotations

import io
import math
import random
import struct
from typing import Final
import wave

import pygame


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    """Pack integer PCM samples into an in-memory WAV buffer."""
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


class WoodlandAudio:
    """Synthesizes and caches pleasant, child-friendly woodland sound effects."""

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

        # 1. Soft leaf rustle when inspecting a spot
        rustle_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-15.0 * t)
            val = random.uniform(-1.0, 1.0)
            rustle_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["rustle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(rustle_samples)))

        # 2. Joyful pop chime on animal discovery
        pop_samples = []
        for i in range(int(rate * 0.22)):
            t = i / rate
            env = math.exp(-6.0 * t)
            freq = 480.0 + 440.0 * (t / 0.22)
            val = math.sin(2.0 * math.pi * freq * t)
            pop_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        # 3. Victory celebratory fanfare
        win_samples = []
        notes = (523.25, 659.25, 783.99, 1046.50)  # C5 - E5 - G5 - C6 arpeggio
        total_len = 0.55
        for i in range(int(rate * total_len)):
            t = i / rate
            env = math.exp(-2.2 * t)
            note_idx = min(len(notes) - 1, int(t / (total_len / len(notes))))
            freq = notes[note_idx]
            val = math.sin(2.0 * math.pi * freq * t)
            win_samples.append(int(32767.0 * 0.32 * env * val))
        self._sounds["win"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))

    def play(self, name: str) -> None:
        """Play a cached sound effect safely without throwing on audio backend faults."""
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass
