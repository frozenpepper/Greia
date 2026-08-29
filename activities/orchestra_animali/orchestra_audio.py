"""Orchestra Animali — synthesized instrument and piano-note audio.

The Activity ships without packaged audio assets. ``SoundManager``
synthesizes the piano octave + the five solo instruments once at
construction time so playback never re-decodes or re-synthesizes
during play. The mixer may be unavailable in headless runs; the
manager then becomes a no-op.
"""

from __future__ import annotations

import io
import math
import random
import struct
import wave

import pygame

if __package__:
    from .orchestra_content import NOTE_FREQS
else:
    from orchestra_content import NOTE_FREQS


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = b"".join(struct.pack("<h", max(-32767, min(32767, int(s)))) for s in samples)
        w.writeframes(raw)
    return buf.getvalue()


class SoundManager:
    """Prepared instrument and piano-octave sound bank."""

    def __init__(self) -> None:
        self._notes: list[pygame.mixer.Sound] = []
        self._inst_sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        # Piano 8 notes (rich acoustic timbre)
        for freq in NOTE_FREQS:
            samples: list[int] = []
            for i in range(8800):
                t = i / 22050.0
                env = math.exp(-t * 4.0)
                val = int(
                    (
                        math.sin(2 * math.pi * freq * t) * 0.68
                        + math.sin(4 * math.pi * freq * t) * 0.24
                        + math.sin(6 * math.pi * freq * t) * 0.08
                    )
                    * env
                    * 15000
                )
                samples.append(val)
            self._notes.append(pygame.mixer.Sound(io.BytesIO(_synth_wav(samples))))

        # Grand Piano Chord Arpeggio
        pn_samples: list[int] = []
        chord = [261.63, 329.63, 392.00, 523.25]
        for i in range(10000):
            t = i / 22050.0
            env = math.exp(-t * 3.2)
            v = 0.0
            for idx, f in enumerate(chord):
                sub_t = max(0.0, t - idx * 0.04)
                sub_env = math.exp(-sub_t * 3.5) if t >= idx * 0.04 else 0.0
                v += (
                    math.sin(2 * math.pi * f * sub_t) * 0.7
                    + math.sin(4 * math.pi * f * sub_t) * 0.3
                ) * sub_env
            pn_samples.append(int(v * 0.28 * 16000))
        self._inst_sounds["piano"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pn_samples)))

        # Drums (bass drum thump + snare crack)
        bd_samples: list[int] = []
        for i in range(5500):
            t = i / 22050.0
            freq = max(45.0, 160.0 - t * 480.0)
            env_bass = math.exp(-t * 12.0)
            snare_noise = (
                random.uniform(-1, 1) * math.exp(-max(0.0, t - 0.03) * 16.0)
                if t >= 0.03
                else 0.0
            )
            val = int(
                (math.sin(2 * math.pi * freq * t) * env_bass * 0.7 + snare_noise * 0.3)
                * 18000
            )
            bd_samples.append(val)
        self._inst_sounds["drums"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bd_samples)))

        # Trumpet Fanfare
        tr_samples: list[int] = []
        notes = [523.25, 659.25, 783.99]
        for i in range(9000):
            t = i / 22050.0
            n_idx = min(len(notes) - 1, int(t / 0.08))
            f = notes[n_idx]
            env = max(0.0, 1.0 - t / 0.38)
            val = int(
                (
                    math.sin(2 * math.pi * f * t) * 0.55
                    + math.sin(4 * math.pi * f * t) * 0.30
                    + math.sin(6 * math.pi * f * t) * 0.15
                )
                * env
                * 15000
            )
            tr_samples.append(val)
        self._inst_sounds["trumpet"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(tr_samples)))

        # Guitar Pluck / Arpeggio
        gt_samples: list[int] = []
        g_chord = [329.63, 440.00, 554.37, 659.25]
        for i in range(10000):
            t = i / 22050.0
            v = 0.0
            for idx, f in enumerate(g_chord):
                sub_t = max(0.0, t - idx * 0.05)
                sub_env = math.exp(-sub_t * 4.0) if t >= idx * 0.05 else 0.0
                v += math.sin(2 * math.pi * f * sub_t) * sub_env
            gt_samples.append(int(v * 0.28 * 16000))
        self._inst_sounds["guitar"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(gt_samples)))

        # Maracas Shaker
        mr_samples: list[int] = []
        for i in range(4000):
            t = i / 22050.0
            p1 = math.exp(-t * 28.0)
            p2 = math.exp(-max(0.0, t - 0.07) * 24.0) if t >= 0.07 else 0.0
            env = max(p1, p2)
            val = int(random.uniform(-1, 1) * env * 14000)
            mr_samples.append(val)
        self._inst_sounds["maracas"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(mr_samples)))

    def play_note(self, index: int) -> None:
        if self._enabled and 0 <= index < len(self._notes):
            try:
                self._notes[index].play()
            except Exception:
                pass

    def play_inst(self, name: str) -> None:
        if self._enabled and name in self._inst_sounds:
            try:
                self._inst_sounds[name].play()
            except Exception:
                pass
