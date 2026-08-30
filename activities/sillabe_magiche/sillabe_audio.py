from __future__ import annotations

"""Single audio owner for Sillabe Magiche — synth + pedagogical speech.

SoundManager is the only object that touches pygame.mixer. Effects are
synthesized once at construction and cached; pre-recorded syllable/word
clips are loaded lazily and bounded by the process lifetime. No per-frame
decoding or mixer re-init.
"""

import io
import math
from pathlib import Path
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


class SoundManager:
    """Own all Sillabe Magiche audio resources and pedagogical speech routing.

    Effects are synthesized once; pedagogical wav assets are loaded on demand
    and cached. Playback is best-effort and never raises to the caller.
    """

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._audio_dir = Path(__file__).resolve().parent / "assets" / "audio"
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_synth_effects()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_synth_effects(self) -> None:
        # Pop Sound (Bubbly tap)
        pop_samples = [
            int(math.sin(2 * math.pi * (500 + (1000 - i) * 0.8) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.05) * 14000)
            for i in range(1200)
        ]
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop_samples)))

        # Chime (Upward 4 notes)
        chime_samples = []
        for i in range(6000):
            t = i / 22050.0
            f = 523.25 if t < 0.07 else (659.25 if t < 0.14 else (783.99 if t < 0.21 else 1046.50))
            env = max(0.0, 1.0 - t / 0.28)
            chime_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["chime"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chime_samples)))

        # Fanfare (Victory flourish)
        fanfare_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
        for i in range(12000):
            t = i / 22050.0
            idx = min(len(notes) - 1, int(t / 0.08))
            f = notes[idx]
            env = max(0.0, 1.0 - t / 0.54)
            fanfare_samples.append(int(math.sin(2 * math.pi * f * t) * env * 14000))
        self._sounds["fanfare"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples)))

        # Wobble (Spring / oops)
        wobble_samples = [
            int(math.sin(2 * math.pi * (320 + math.sin(i * 0.05) * 45) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.16) * 10000)
            for i in range(3500)
        ]
        self._sounds["wobble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(wobble_samples)))

        # Swoosh (Tile snap)
        swoosh_samples = [
            int(math.sin(2 * math.pi * (200 + i * 0.4) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.12) * 9000)
            for i in range(2600)
        ]
        self._sounds["swoosh"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(swoosh_samples)))

    def _get_sound(self, key: str) -> pygame.mixer.Sound | None:
        if not self._enabled:
            return None
        if key in self._sounds:
            return self._sounds[key]
        if ":" in key:
            loc, name = key.split(":", 1)
            audio_file = self._audio_dir / loc / f"{name}.wav"
            if audio_file.exists():
                try:
                    sound = pygame.mixer.Sound(str(audio_file))
                    self._sounds[key] = sound
                    return sound
                except Exception:
                    pass
        return None

    def play(self, name: str) -> None:
        sound = self._get_sound(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def play_syllable(self, syl: str, locale: str = "it") -> None:
        key = f"{locale}:syl_{syl.lower()}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play("pop")

    def play_prompt(self, syl: str, locale: str = "it") -> None:
        key = f"{locale}:find_{syl.lower()}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play_syllable(syl, locale)

    def play_word(self, word_stem: str, locale: str = "it") -> None:
        key = f"{locale}:word_{word_stem.lower()}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play("chime")

    def play_consonant(self, letter: str, locale: str = "it") -> None:
        key = f"{locale}:letter_{letter.lower()}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play("pop")

    def play_praise(self, locale: str = "it") -> None:
        praises = ["esatto", "fantastico", "super", "magnifico", "ottimo", "ben_fatto"] if locale == "it" else ["great_job", "wonderful", "you_did_it", "fantastic", "super", "well_done"]
        chosen = random.choice(praises)
        key = f"{locale}:{chosen}"
        if self._get_sound(key) is not None:
            self.play(key)
        else:
            self.play("fanfare")


__all__ = ["SoundManager"]
