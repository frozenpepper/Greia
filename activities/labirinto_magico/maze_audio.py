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


class LabyrinthAudio:
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

        # 1. Step / Slide whoosh
        step_samples: list[int] = []
        for i in range(int(rate * 0.06)):
            t = i / rate
            env = math.exp(-30.0 * t)
            val = math.sin(2.0 * math.pi * (340.0 - 80.0 * t) * t)
            step_samples.append(int(32767.0 * 0.22 * env * val))
        self._sounds["step"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(step_samples)))

        # 2. Star collection chime
        star_samples: list[int] = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-8.0 * t)
            val = math.sin(2.0 * math.pi * (880.0 + 440.0 * t) * t)
            star_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["star"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(star_samples)))

        # 3. Victory fanfare arpeggio
        win_samples: list[int] = []
        notes = [523.25, 659.25, 783.99, 1046.50]
        for i in range(int(rate * 0.65)):
            t = i / rate
            env = math.exp(-2.5 * t)
            n_idx = min(3, int(t / 0.15))
            val = math.sin(2.0 * math.pi * notes[n_idx] * t)
            win_samples.append(int(32767.0 * 0.35 * env * val))
        self._sounds["win"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))

        # 4. Gentle wall bump feedback
        bump_samples: list[int] = []
        for i in range(int(rate * 0.04)):
            t = i / rate
            env = math.exp(-50.0 * t)
            val = math.sin(2.0 * math.pi * 140.0 * t)
            bump_samples.append(int(32767.0 * 0.15 * env * val))
        self._sounds["bump"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bump_samples)))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


MazeAudio = LabyrinthAudio
