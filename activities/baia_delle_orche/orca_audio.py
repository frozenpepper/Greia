from __future__ import annotations

import io
import math
import random
import struct
from typing import Protocol
import wave

import pygame


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    """Pack signed 16-bit mono audio samples into a valid in-memory WAV byte stream."""
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


from pathlib import Path

AUDIO_DIR = Path(__file__).parent / "assets" / "audio"


class OrcaAudio(Protocol):
    """Protocol for Activity audio playback."""

    def play(self, name: str) -> None:
        ...

    def play_voice(self, key: str, locale: str = "it") -> None:
        ...

    def stop_voice(self) -> None:
        ...


class PygameOrcaAudio:
    """Synthesizes and caches cute, realistic, non-blocking marine sounds and Tito character voice clips."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._voice_cache: dict[tuple[str, str], pygame.mixer.Sound] = {}
        self._voice_channel: pygame.mixer.Channel | None = None
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            try:
                pygame.mixer.set_num_channels(8)
                self._voice_channel = pygame.mixer.Channel(0)
            except Exception:
                self._voice_channel = None
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        rate = 22050

        # 1. Water Splash
        splash_samples: list[int] = []
        for i in range(int(rate * 0.22)):
            t = i / rate
            env = math.exp(-9.0 * t)
            noise = (random.random() * 2.0 - 1.0) * 0.45
            tone = math.sin(2.0 * math.pi * (260.0 - 80.0 * (t / 0.22)) * t) * 0.55
            splash_samples.append(int(32767.0 * 0.35 * env * (tone + noise)))
        self._sounds["splash"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(splash_samples, rate)))

        # 2. Orca Whistle (Harmonic, joyful cetacean whistle)
        whistle_samples: list[int] = []
        for i in range(int(rate * 0.45)):
            t = i / rate
            env = math.sin(math.pi * (t / 0.45)) ** 0.8
            f = 950.0 + 350.0 * math.sin(2.0 * math.pi * 3.5 * t) + 120.0 * math.sin(2.0 * math.pi * 12.0 * t)
            val = (
                0.7 * math.sin(2.0 * math.pi * f * t)
                + 0.25 * math.sin(2.0 * math.pi * f * 2.0 * t)
                + 0.05 * math.sin(2.0 * math.pi * f * 3.0 * t)
            )
            whistle_samples.append(int(32767.0 * 0.28 * env * val))
        self._sounds["whistle"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(whistle_samples, rate)))

        # 3. Echolocation Clicks
        clicks_samples: list[int] = []
        for i in range(int(rate * 0.28)):
            t = i / rate
            # Rapid clicks at 35Hz repetition
            click_phase = (t * 35.0) % 1.0
            click_env = math.exp(-40.0 * click_phase) if click_phase < 0.15 else 0.0
            high_freq = 2400.0 + random.uniform(-150.0, 150.0)
            val = math.sin(2.0 * math.pi * high_freq * t) * click_env
            clicks_samples.append(int(32767.0 * 0.25 * val))
        self._sounds["clicks"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(clicks_samples, rate)))

        # 4. Fish Nibble / Munch
        nibble_samples: list[int] = []
        for i in range(int(rate * 0.12)):
            t = i / rate
            env = math.exp(-18.0 * t)
            val = math.sin(2.0 * math.pi * 680.0 * t) + 0.35 * (random.random() * 2.0 - 1.0)
            nibble_samples.append(int(32767.0 * 0.32 * env * val))
        self._sounds["nibble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(nibble_samples, rate)))

        # 5. Happy Purr / Chirp
        purr_samples: list[int] = []
        for i in range(int(rate * 0.32)):
            t = i / rate
            env = math.sin(math.pi * (t / 0.32))
            mod = 1.0 + 0.5 * math.sin(2.0 * math.pi * 28.0 * t)
            val = math.sin(2.0 * math.pi * 420.0 * t) * mod
            purr_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["purr"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(purr_samples, rate)))

        # 6. Bubble Pop
        bubble_samples: list[int] = []
        for i in range(int(rate * 0.07)):
            t = i / rate
            env = math.exp(-25.0 * t)
            val = math.sin(2.0 * math.pi * (450.0 + 600.0 * (t / 0.07)) * t)
            bubble_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["bubble"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bubble_samples, rate)))

        # 7. Ball Bounce / Boing
        bounce_samples: list[int] = []
        for i in range(int(rate * 0.15)):
            t = i / rate
            env = math.exp(-12.0 * t)
            f = 320.0 + 180.0 * math.exp(-15.0 * t)
            val = math.sin(2.0 * math.pi * f * t)
            bounce_samples.append(int(32767.0 * 0.32 * env * val))
        self._sounds["bounce"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(bounce_samples, rate)))

        # 8. Marine Chimes for Musical Echolocation (Notes: C5, E5, G5, C6)
        notes = {"bell_0": 523.25, "bell_1": 659.25, "bell_2": 783.99, "bell_3": 1046.50}
        for b_name, freq in notes.items():
            chime_samples: list[int] = []
            for i in range(int(rate * 0.40)):
                t = i / rate
                env = math.exp(-4.5 * t)
                val = 0.65 * math.sin(2.0 * math.pi * freq * t) + 0.35 * math.sin(2.0 * math.pi * (freq * 2.0) * t)
                chime_samples.append(int(32767.0 * 0.30 * env * val))
            self._sounds[b_name] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chime_samples, rate)))

        # 9. Aurora / Night Shimmer Chime
        aurora_samples: list[int] = []
        for i in range(int(rate * 0.55)):
            t = i / rate
            env = math.exp(-2.8 * t)
            val = (
                0.4 * math.sin(2.0 * math.pi * 587.33 * t)
                + 0.35 * math.sin(2.0 * math.pi * 880.0 * t)
                + 0.25 * math.sin(2.0 * math.pi * 1174.66 * t)
            )
            aurora_samples.append(int(32767.0 * 0.26 * env * val))
        self._sounds["aurora"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(aurora_samples, rate)))

    def play(self, name: str) -> None:
        if not self._enabled:
            return
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_voice(self, key: str, locale: str = "it") -> None:
        if not self._enabled:
            return
        loc = "it" if locale.startswith("it") else "en"
        cache_key = (key, loc)
        snd = self._voice_cache.get(cache_key)
        if snd is None:
            p = AUDIO_DIR / loc / f"tito_{key}.wav"
            if p.exists():
                try:
                    snd = pygame.mixer.Sound(str(p))
                    self._voice_cache[cache_key] = snd
                except Exception:
                    pass
        if snd is not None:
            try:
                if self._voice_channel is not None:
                    self._voice_channel.stop()
                    self._voice_channel.play(snd)
                else:
                    snd.play()
            except Exception:
                pass

    def stop_voice(self) -> None:
        if self._enabled and self._voice_channel is not None:
            try:
                self._voice_channel.stop()
            except Exception:
                pass
