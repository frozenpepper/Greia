"""Sottomarino Giramondo — Prepared Synthesized Sound Bank.

Sound effects for the submarine instruments, ocean acoustics, and encounters.
Synthesized once at construction matching the active PCM16 mixer spec.
Audio is completely fail-soft and non-blocking.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
import wave
from typing import Optional

import pygame

from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec


def _synth_wav(samples: list[int], rate: int = 22050, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = bytearray()
        for s in samples:
            append_mono_pcm16(raw, s, channels)
        w.writeframes(raw)
    return buf.getvalue()


class SubmarineAudio:
    """Prepared sound bank for submarine instruments and encounters."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._init_sounds()
        except Exception:
            pass

    def _init_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        rate = spec[0] if spec else 22050
        channels = spec[1] if spec else 1

        # 1. Sonar Ping (crisp sine pulse with long soft decay)
        duration_s = 0.8
        n_samples = int(rate * duration_s)
        samples = []
        freq = 1200.0
        for i in range(n_samples):
            t = i / rate
            env = math.exp(-4.5 * t)
            val = int(24000.0 * math.sin(2.0 * math.pi * freq * t) * env)
            samples.append(val)
        self._register("sonar", _synth_wav(samples, rate, channels))

        # 2. Bubble Burble (rising bubbly pitch chirps)
        duration_s = 0.4
        n_samples = int(rate * duration_s)
        samples = []
        for i in range(n_samples):
            t = i / rate
            f = 300.0 + 500.0 * (t / duration_s) + 60.0 * math.sin(40.0 * math.pi * t)
            env = math.sin(math.pi * (t / duration_s))
            val = int(20000.0 * math.sin(2.0 * math.pi * f * t) * env)
            samples.append(val)
        self._register("bubbles", _synth_wav(samples, rate, channels))

        # 3. Ship Horn / Whistle (cheerful two-tone acoustic brass whistle)
        duration_s = 1.1
        n_samples = int(rate * duration_s)
        samples = []
        for i in range(n_samples):
            t = i / rate
            if t < 0.42:
                # First whistle note (260 Hz)
                env = math.sin(math.pi * (t / 0.42)) ** 0.5
                f0 = 260.0
                vib = 1.0 + 0.012 * math.sin(2.0 * math.pi * 6.0 * t)
                w = (
                    math.sin(2.0 * math.pi * f0 * vib * t) +
                    0.45 * math.sin(2.0 * math.pi * f0 * 2.0 * vib * t) +
                    0.25 * math.sin(2.0 * math.pi * f0 * 3.0 * vib * t) +
                    0.10 * math.sin(2.0 * math.pi * f0 * 4.0 * vib * t)
                ) / 1.8
                val = int(22000.0 * w * env)
            elif t < 0.48:
                val = 0
            else:
                # Second higher, cheerful whistle note (330 Hz - toot toot!)
                t2 = t - 0.48
                dur2 = duration_s - 0.48
                env = math.sin(math.pi * (t2 / dur2)) ** 0.5
                f0 = 329.6
                vib = 1.0 + 0.012 * math.sin(2.0 * math.pi * 6.0 * t)
                w = (
                    math.sin(2.0 * math.pi * f0 * vib * t) +
                    0.45 * math.sin(2.0 * math.pi * f0 * 2.0 * vib * t) +
                    0.25 * math.sin(2.0 * math.pi * f0 * 3.0 * vib * t) +
                    0.10 * math.sin(2.0 * math.pi * f0 * 4.0 * vib * t)
                ) / 1.8
                val = int(22000.0 * w * env)
            samples.append(val)
        self._register("horn", _synth_wav(samples, rate, channels))

        # 4. Click / Switch (mechanical tactile cockpit toggle)
        duration_s = 0.08
        n_samples = int(rate * duration_s)
        samples = []
        for i in range(n_samples):
            t = i / rate
            noise = (random.random() * 2.0 - 1.0)
            env = math.exp(-50.0 * t)
            val = int(16000.0 * noise * env)
            samples.append(val)
        self._register("click", _synth_wav(samples, rate, channels))

        # 5. Floodlight Hum / Power On
        duration_s = 0.5
        n_samples = int(rate * duration_s)
        samples = []
        for i in range(n_samples):
            t = i / rate
            f = 200.0 + 350.0 * (t / duration_s)
            env = min(1.0, t * 15.0) * (1.0 - t / duration_s)
            val = int(18000.0 * math.sin(2.0 * math.pi * f * t) * env)
            samples.append(val)
        self._register("light", _synth_wav(samples, rate, channels))

        # 6. Gentle Encounter Alert (friendly bell chime)
        duration_s = 0.6
        n_samples = int(rate * duration_s)
        samples = []
        for i in range(n_samples):
            t = i / rate
            env = math.exp(-6.0 * t)
            val = int(22000.0 * (math.sin(2.0 * math.pi * 880.0 * t) + 0.5 * math.sin(2.0 * math.pi * 1760.0 * t)) * env)
            samples.append(val)
        self._register("alert", _synth_wav(samples, rate, channels))

        # 7. Joyful Splash / Giggle (encounter resolution celebration)
        duration_s = 0.8
        n_samples = int(rate * duration_s)
        samples = []
        for i in range(n_samples):
            t = i / rate
            env = min(1.0, t * 8.0) * math.exp(-3.0 * t)
            chord = (
                math.sin(2.0 * math.pi * 523.25 * t) +
                math.sin(2.0 * math.pi * 659.25 * t) +
                math.sin(2.0 * math.pi * 783.99 * t)
            ) / 3.0
            val = int(22000.0 * chord * env)
            samples.append(val)
        self._register("celebrate", _synth_wav(samples, rate, channels))

        # 8. Gentle Engine Telegraph Chug (tactile gear click when moving throttle)
        duration_s = 0.25
        n_samples = int(rate * duration_s)
        samples = []
        for i in range(n_samples):
            t = i / rate
            env = math.sin(math.pi * (t / duration_s))
            f = 110.0 + 30.0 * math.sin(20.0 * math.pi * t)
            val = int(17000.0 * math.sin(2.0 * math.pi * f * t) * env)
            samples.append(val)
        self._register("engine_shift", _synth_wav(samples, rate, channels))

        # Dedicated voice playback channel to prevent speech overlap
        try:
            self._voice_channel = pygame.mixer.Channel(1)
        except Exception:
            self._voice_channel = None

    def _register(self, name: str, wav_bytes: bytes) -> None:
        try:
            self._sounds[name] = pygame.mixer.Sound(file=io.BytesIO(wav_bytes))
        except Exception:
            pass

    def play(self, name: str) -> None:
        """Play a prepared sound effect safely without blocking or raising."""
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def is_voice_busy(self) -> bool:
        """Check if a voice cue is currently speaking."""
        try:
            if self._voice_channel is not None:
                return self._voice_channel.get_busy()
        except Exception:
            pass
        return False

    def play_voice(self, cue_path: Path | str) -> bool:
        """Play a localized voice line on the dedicated voice channel."""
        try:
            p = Path(cue_path)
            if p.is_file():
                snd = pygame.mixer.Sound(str(p))
                if self._voice_channel is not None:
                    self._voice_channel.play(snd)
                else:
                    snd.play()
                return True
        except Exception:
            pass
        return False
