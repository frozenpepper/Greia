"""La Discesa della Biglia — procedural audio.

No microphone, no child recording, no per-cue voice audio yet (this
tranche ships procedural SFX only). All sounds are synthesized in
memory once at startup so the per-frame cost is a small mixer
play call.

The `None` fallback is the right answer for the Simulator: when
SDL audio is not available (`SDL_AUDIODRIVER=dummy` in the
headless test path) every `play(...)` becomes a no-op.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from typing import Final

import pygame


SAMPLE_RATE: Final = 22050


def _synth_wav(samples: list[int], rate: int = SAMPLE_RATE) -> bytes:
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


def _envelope_sin(
    duration: float, freq: float, decay: float, amp: float = 0.25,
    rate: int = SAMPLE_RATE,
) -> list[int]:
    out: list[int] = []
    for i in range(int(rate * duration)):
        t = i / rate
        env = math.exp(-decay * t)
        val = math.sin(2.0 * math.pi * freq * t) * env * amp
        out.append(int(32767.0 * val))
    return out


def _bounce_samples() -> list[int]:
    return _envelope_sin(0.10, freq=420.0, decay=18.0, amp=0.30)


def _place_samples() -> list[int]:
    # Short thunk when a tool is placed
    return _envelope_sin(0.06, freq=260.0, decay=24.0, amp=0.28)


def _miss_samples() -> list[int]:
    # Sad descending pair of notes
    a = _envelope_sin(0.18, freq=320.0, decay=10.0, amp=0.28)
    b = _envelope_sin(0.18, freq=200.0, decay=10.0, amp=0.28)
    return a + b


def _win_samples() -> list[int]:
    # Rising three-note arpeggio
    a = _envelope_sin(0.12, freq=523.0, decay=10.0, amp=0.28)
    b = _envelope_sin(0.12, freq=659.0, decay=10.0, amp=0.28)
    c = _envelope_sin(0.20, freq=784.0, decay=6.0, amp=0.30)
    return a + b + c


class RampAudio:
    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512
                )
            self._init_sounds()
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        self._sounds["bounce"] = pygame.mixer.Sound(
            io.BytesIO(_synth_wav(_bounce_samples()))
        )
        self._sounds["place"] = pygame.mixer.Sound(
            io.BytesIO(_synth_wav(_place_samples()))
        )
        self._sounds["miss"] = pygame.mixer.Sound(
            io.BytesIO(_synth_wav(_miss_samples()))
        )
        self._sounds["win"] = pygame.mixer.Sound(
            io.BytesIO(_synth_wav(_win_samples()))
        )

    def play(self, name: str) -> None:
        if not self._enabled:
            return
        snd = self._sounds.get(name)
        if snd is None:
            return
        try:
            snd.play()
        except Exception:
            pass
