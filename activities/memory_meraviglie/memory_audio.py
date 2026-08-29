"""La Memoria delle Meraviglie — audio cues synthesized once at startup.

The Activity ships without packaged audio assets: short sound effects
(flip / match / mismatch / win) are synthesized procedurally when the
audio owner is constructed, then played by name. This keeps the package
small, the per-Activity audio footprint predictable, and avoids
re-decoding the same waveform on every interaction.
"""

from __future__ import annotations

import io
import math
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


class MemoryAudio:
    """Prepared sound bank for memory_meraviglie.

    Sounds are synthesized once at construction time. ``play(name)`` is
    the only public surface Activities or tests should call.
    """

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._init_sounds()
        except Exception:
            # Mixer may be unavailable in headless test runs; the bank
            # is then empty and play() is a no-op.
            pass

    def _init_sounds(self) -> None:
        rate = 22050

        flip_samples: list[int] = []
        for i in range(int(rate * 0.05)):
            t = i / rate
            env = math.exp(-20.0 * t)
            val = math.sin(2.0 * math.pi * 450.0 * t)
            flip_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["flip"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(flip_samples)))

        match_samples: list[int] = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-4.0 * t)
            val = 0.6 * math.sin(2.0 * math.pi * 523.25 * t) + 0.4 * math.sin(2.0 * math.pi * 659.25 * t)
            match_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["match"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(match_samples)))

        mismatch_samples: list[int] = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-12.0 * t)
            val = math.sin(2.0 * math.pi * 180.0 * t)
            mismatch_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["mismatch"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(mismatch_samples)))

        win_samples: list[int] = []
        for i in range(int(rate * 0.45)):
            t = i / rate
            env = math.exp(-2.0 * t)
            freq = 523.25 if t < 0.12 else (659.25 if t < 0.24 else (783.99 if t < 0.36 else 1046.50))
            val = math.sin(2.0 * math.pi * freq * t)
            win_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["win"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is None:
            return
        try:
            snd.play()
        except Exception:
            pass
