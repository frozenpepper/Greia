"""Audio owners for Teatrino delle Fiabe.

Owns synthesized sound bank and microphone capture lifecycle in one place.
"""

from __future__ import annotations

import io
import json
import math
import random
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

import pygame

try:
    from pygame._sdl2 import audio as sdl2_audio
except ImportError:
    sdl2_audio = None

from greia_platform.activity_api import get_audio_capture_device, get_sdl_capture_device
from greia_platform.creation_media import CreationMediaError, WavCodec


class MicrophoneRecorder:
    """Non-blocking low-latency microphone capture with live voice waveform."""

    def __init__(self) -> None:
        self.enabled = True
        self.is_recording = False
        self.sample_rate = 22050
        self.recorded_pcm = bytearray()
        self.current_volume = 0.0
        self._dev = None

    def _ensure_audio_init(self) -> None:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                pass

    @property
    def has_hardware(self) -> bool:
        try:
            self._ensure_audio_init()
            if get_sdl_capture_device() is not None:
                return True
            if get_audio_capture_device() is None and sdl2_audio is not None:
                names = sdl2_audio.get_audio_device_names(True)
                return bool(names)
        except Exception:
            return False
        return False

    def toggle(self) -> bool:
        try:
            self.enabled = not self.enabled
            return self.enabled
        except Exception:
            self.enabled = False
            return False

    def _get_system_gain(self) -> float:
        try:
            settings_file = Path("/var/lib/greia-system-settings/settings.json")
            if settings_file.is_file():
                data = json.loads(settings_file.read_text(encoding="utf-8"))
                return max(0.5, min(4.0, float(data.get("mic_gain", 2.0))))
        except Exception:
            pass
        return 2.0

    def start_recording(self) -> None:
        self.recorded_pcm.clear()
        self.current_volume = 0.0
        try:
            self._ensure_audio_init()
        except Exception:
            pass

        if not self.enabled or sdl2_audio is None:
            self.is_recording = True
            return

        gain = self._get_system_gain()

        def _audio_callback(dev, data: bytes):
            if not self.is_recording:
                return
            try:
                self.recorded_pcm.extend(data)
                if len(data) >= 128:
                    num_samples = len(data) // 2
                    samples = struct.unpack(f"<{num_samples}h", data[: num_samples * 2])
                    peak = max(abs(s) for s in samples[::8]) * gain
                    self.current_volume = min(1.0, peak / 18000.0)
            except Exception:
                pass

        try:
            dev_name = get_sdl_capture_device()
            if dev_name is None and get_audio_capture_device() is None:
                names = sdl2_audio.get_audio_device_names(True)
                dev_name = names[0] if names else None
            self._dev = sdl2_audio.AudioDevice(
                dev_name,
                True,
                self.sample_rate,
                sdl2_audio.AUDIO_S16LSB,
                1,
                2048,
                0,
                _audio_callback,
            )
            self._dev.pause(0)
            self.is_recording = True
        except Exception:
            self._dev = None
            self.is_recording = True

    def stop_recording(self) -> bytes | None:
        if not self.is_recording:
            return None
        self.is_recording = False
        if self._dev is not None:
            try:
                self._dev.pause(1)
                self._dev.close()
            except Exception:
                pass
            self._dev = None

        if not self.recorded_pcm:
            return None

        gain = self._get_system_gain()
        raw_pcm = bytes(self.recorded_pcm)

        if len(raw_pcm) >= 2 and gain != 1.0:
            try:
                num_samples = len(raw_pcm) // 2
                samples = struct.unpack(f"<{num_samples}h", raw_pcm[: num_samples * 2])
                boosted = [
                    int(max(-32767, min(32767, s * gain)))
                    for s in samples
                ]
                raw_pcm = struct.pack(f"<{num_samples}h", *boosted)
            except Exception:
                pass

        out_io = io.BytesIO()
        try:
            with wave.open(out_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(raw_pcm)
            return out_io.getvalue()
        except Exception:
            return None


@dataclass(frozen=True, slots=True)
class ImportedNarrationTrack:
    """Canonical bounded narration selected through My Creations."""

    wav_bytes: bytes
    duration_seconds: float

    @classmethod
    def from_wav(
        cls,
        payload: bytes,
        *,
        max_duration_seconds: float,
    ) -> "ImportedNarrationTrack":
        if max_duration_seconds <= 0:
            raise ValueError("narration duration bound must be positive")
        try:
            prepared = WavCodec().prepare(payload)
        except CreationMediaError as exc:
            raise ValueError("invalid narration WAV") from exc
        duration = float(prepared.attributes.get("duration_seconds", 0.0))
        if duration <= 0.0 or duration > max_duration_seconds:
            raise ValueError("narration is too long for a Theatre recording")
        return cls(prepared.data, duration)

    def trimmed(self, seconds: float) -> bytes:
        """Return a canonical prefix when a child stops puppeteering early."""
        if seconds <= 0:
            raise ValueError("trim duration must be positive")
        if seconds >= self.duration_seconds - 0.01:
            return self.wav_bytes
        try:
            with wave.open(io.BytesIO(self.wav_bytes), "rb") as source:
                channels = source.getnchannels()
                width = source.getsampwidth()
                rate = source.getframerate()
                frames = source.getnframes()
                keep = min(frames, max(1, int(round(seconds * rate))))
                pcm = source.readframes(keep)
            output = io.BytesIO()
            with wave.open(output, "wb") as target:
                target.setnchannels(channels)
                target.setsampwidth(width)
                target.setframerate(rate)
                target.writeframes(pcm)
            return output.getvalue()
        except (EOFError, OSError, ValueError, wave.Error) as exc:
            raise ValueError("narration WAV could not be trimmed") from exc

    def play(self) -> tuple[pygame.mixer.Sound, pygame.mixer.Channel] | None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound = pygame.mixer.Sound(io.BytesIO(self.wav_bytes))
            channel = sound.play()
            if channel is None:
                return None
            return sound, channel
        except Exception:
            return None


class SoundManager:
    """Procedural audio effects for theater cues and magic sound buttons."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._build_all_effects()
        except Exception:
            self._enabled = False

    def _build_sound(self, generator_func, duration: float = 0.3) -> pygame.mixer.Sound:
        sample_rate = 22050
        total_samples = int(sample_rate * duration)
        raw = bytearray()
        for i in range(total_samples):
            t = i / float(sample_rate)
            val = generator_func(t, duration)
            sample = int(max(-1.0, min(1.0, val)) * 30000.0)
            raw.extend(struct.pack("<hh", sample, sample))
        return pygame.mixer.Sound(buffer=bytes(raw))

    def _build_all_effects(self) -> None:
        self._sounds["pop"] = self._build_sound(
            lambda t, d: math.sin(2 * math.pi * (300 + 700 * (t / d)) * t) * (1.0 - t / d),
            0.12,
        )
        self._sounds["trumpet"] = self._build_sound(
            lambda t, d: (
                (0.6 * math.sin(2 * math.pi * (523.25 if t < 0.15 else 659.25 if t < 0.3 else 783.99) * t)
                 + 0.3 * math.sin(4 * math.pi * (523.25 if t < 0.15 else 659.25 if t < 0.3 else 783.99) * t))
                * min(1.0, t * 20.0) * (1.0 - t / d)
            ),
            0.55,
        )
        self._sounds["magic"] = self._build_sound(
            lambda t, d: (
                math.sin(2 * math.pi * (800 + 1200 * math.sin(t * 30)) * t)
                * (0.5 + 0.5 * math.sin(t * 80))
                * (1.0 - t / d)
            ),
            0.5,
        )
        self._sounds["applause"] = self._build_sound(
            lambda t, d: (
                (random.random() * 2.0 - 1.0)
                * (0.3 + 0.7 * (math.sin(t * 40) ** 2))
                * (1.0 - (t / d) ** 0.5)
            ),
            0.8,
        )
        self._sounds["giggle"] = self._build_sound(
            lambda t, d: (
                math.sin(2 * math.pi * (600 + 250 * math.sin(t * 35)) * t)
                * min(1.0, t * 15.0)
                * (1.0 - t / d)
            ),
            0.4,
        )
        self._sounds["mystery"] = self._build_sound(
            lambda t, d: (
                (0.7 * math.sin(2 * math.pi * (220 + 80 * math.cos(t * 8)) * t)
                 + 0.3 * math.sin(2 * math.pi * (330 + 120 * math.sin(t * 12)) * t))
                * (1.0 - t / d)
            ),
            0.6,
        )
        self._sounds["boing"] = self._build_sound(
            lambda t, d: (
                math.sin(2 * math.pi * (160 + 600 * math.exp(-t * 8)) * t)
                * (1.0 - t / d)
            ),
            0.35,
        )

    def play(self, sound_name: str) -> None:
        if not self._enabled:
            return
        snd = self._sounds.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass


__all__ = ["ImportedNarrationTrack", "MicrophoneRecorder", "SoundManager"]
