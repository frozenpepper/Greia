from __future__ import annotations

"""Procedural audio bank for La Torre delle Forme.

Provides wooden block clicks, snaps, xylophone arpeggios, rainbow sparkles,
and celebration fanfares without external audio asset dependencies.
"""

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


class TorreAudio:
    """Prebuilt procedural sound-effect bank for wooden blocks and tower gameplay."""

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

        # 1. Block Clack (wooden thud on placement / landing)
        clack_samples: list[int] = []
        for i in range(int(rate * 0.09)):
            t = i / rate
            env = math.exp(-22.0 * t)
            # Wood resonance: combination of 260Hz and 640Hz with short noise burst
            val = 0.7 * math.sin(2.0 * math.pi * 280.0 * t) + 0.3 * math.sin(2.0 * math.pi * 680.0 * t)
            clack_samples.append(int(32767.0 * 0.40 * env * val))
        self._sounds["clack"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(clack_samples, rate)))

        # 2. Rotate Click (crisp wood twist)
        rotate_samples: list[int] = []
        for i in range(int(rate * 0.05)):
            t = i / rate
            env = math.exp(-35.0 * t)
            freq = 700.0 + 400.0 * (1.0 - t / 0.05)
            val = math.sin(2.0 * math.pi * freq * t)
            rotate_samples.append(int(32767.0 * 0.28 * env * val))
        self._sounds["rotate"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(rotate_samples, rate)))

        # 3. Snap (cheerful xylophone ding for snap placement in Mode 1)
        snap_samples: list[int] = []
        for i in range(int(rate * 0.18)):
            t = i / rate
            env = math.exp(-8.0 * t)
            val = math.sin(2.0 * math.pi * 880.0 * t) + 0.2 * math.sin(2.0 * math.pi * 1760.0 * t)
            snap_samples.append(int(32767.0 * 0.35 * env * val))
        self._sounds["snap"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(snap_samples, rate)))

        # 4. Line Clear (ascending bright xylophone arpeggio: C5 - E5 - G5 - C6)
        line_samples: list[int] = []
        duration = 0.38
        notes = [523.25, 659.25, 783.99, 1046.50]
        step_len = duration / len(notes)
        for i in range(int(rate * duration)):
            t = i / rate
            note_idx = min(len(notes) - 1, int(t / step_len))
            note_t = t - (note_idx * step_len)
            note_env = math.exp(-7.0 * note_t)
            freq = notes[note_idx]
            val = math.sin(2.0 * math.pi * freq * t) + 0.25 * math.sin(2.0 * math.pi * freq * 2 * t)
            line_samples.append(int(32767.0 * 0.35 * note_env * val))
        self._sounds["line_clear"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(line_samples, rate)))

        # 5. Rainbow Sparkle Chime (twinkling star effect)
        sparkle_samples: list[int] = []
        for i in range(int(rate * 0.42)):
            t = i / rate
            env = math.exp(-4.5 * t)
            # Bell with FM modulation for sparkle
            mod = 80.0 * math.sin(2.0 * math.pi * 28.0 * t)
            freq = 1318.5 + mod
            val = math.sin(2.0 * math.pi * freq * t) + 0.3 * math.sin(2.0 * math.pi * (freq * 1.5) * t)
            sparkle_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["rainbow"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(sparkle_samples, rate)))

        # 6. Celebration Fanfare (joyful brassy party celebration)
        fanfare_samples: list[int] = []
        f_dur = 0.65
        f_notes = [523.25, 659.25, 783.99, 1046.50, 1046.50]
        f_step = f_dur / 5.0
        for i in range(int(rate * f_dur)):
            t = i / rate
            idx = min(len(f_notes) - 1, int(t / f_step))
            st = t - (idx * f_step)
            env = math.exp(-3.5 * st)
            freq = f_notes[idx]
            val = 0.6 * math.sin(2.0 * math.pi * freq * t) + 0.3 * math.sin(2.0 * math.pi * freq * 2 * t)
            fanfare_samples.append(int(32767.0 * 0.38 * env * val))
        self._sounds["fanfare"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples, rate)))

    def play(self, cue: str) -> None:
        snd = self._sounds.get(cue)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass
