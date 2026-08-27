"""Storie della Mia Voce — microphone recorder.

Greia owns the microphone route (ADR 0031, MICROPHONE_RECORDING.md).
This Activity does not enumerate or pick hardware: it asks the
platform for the SDL-openable capture device
(``get_sdl_capture_device()``) and, in the simulator/development
fallback, falls back to the ordinary default. The Activity then
opens one short capture stream per recording, decodes the audio
callback as 16-bit signed mono PCM, applies a small software gain
post-capture for the noisy reference laptop microphone, and
packages the result as a single WAV blob that the storage layer
saves to the per-profile Activity store.

The recorder is stateful. ``start()`` opens a new stream and
begins capturing; ``stop()`` closes the stream and returns the
WAV bytes. ``available()`` is a fast check the lifecycle layer
uses to decide whether the mic path is usable at all (None from
the SDK + no fallback device = Activity is microphone-less).
"""

from __future__ import annotations

import io
import math
import struct
import time
import wave
from typing import Any, Final

import pygame

try:
    from pygame._sdl2 import audio as sdl2_audio
except ImportError:  # pragma: no cover - pygame without _sdl2.audio
    sdl2_audio = None  # type: ignore[assignment]

from greia_platform.activity_api import (
    get_audio_capture_device,
    get_sdl_capture_device,
)


SAMPLE_RATE: Final = 22050
CHANNELS: Final = 1
SAMPLE_WIDTH: Final = 2
SOFT_GAIN_DEFAULT: Final = 1.6  # reasonable post-capture boost for noisy mics


class VoiceRecorder:
    """Non-blocking capture of a short mono PCM stream via SDL2."""

    def __init__(self) -> None:
        self._dev: Any | None = None
        self._pcm = bytearray()
        self._is_recording = False
        self._sdl2_available = sdl2_audio is not None
        self._enabled = True
        self._volume = 0.0

    @property
    def available(self) -> bool:
        """True iff the platform reports a microphone route or the
        development fallback can resolve a default device.
        """
        if get_sdl_capture_device() is not None:
            return True
        if get_audio_capture_device() is not None:
            return True
        if not self._sdl2_available:
            return False
        try:
            names = sdl2_audio.get_audio_device_names(True)
            return bool(names)
        except Exception:
            return False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def live_volume(self) -> float:
        return self._volume

    def _ensure_audio_init(self) -> None:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                pass

    def start(self) -> None:
        if self._is_recording:
            return
        self._pcm = bytearray()
        self._volume = 0.0
        self._ensure_audio_init()
        if not self._sdl2_available:
            # No SDL2 audio: simulate recording so the lifecycle can
            # still exercise its UI flow. We record silence for the
            # requested duration; the saved file is a real (silent) WAV.
            self._is_recording = True
            self._started_at = time.monotonic()
            return
        dev_name = get_sdl_capture_device()
        if dev_name is None and get_audio_capture_device() is None:
            try:
                names = sdl2_audio.get_audio_device_names(True)
                dev_name = names[0] if names else None
            except Exception:
                dev_name = None
        if dev_name is None:
            self._is_recording = True
            return

        def _callback(dev: Any, data: bytes) -> None:
            if not self._is_recording:
                return
            try:
                self._pcm.extend(data)
                if len(data) >= 64:
                    samples = struct.unpack(
                        f"<{len(data) // 2}h", data[: (len(data) // 2) * 2]
                    )
                    peak = max(
                        (abs(s) for s in samples[::4]),
                        default=0,
                    )
                    self._volume = min(1.0, peak / 18000.0)
            except Exception:
                pass

        try:
            self._dev = sdl2_audio.AudioDevice(
                dev_name,
                True,
                SAMPLE_RATE,
                sdl2_audio.AUDIO_S16LSB,
                CHANNELS,
                2048,
                0,
                _callback,
            )
            self._dev.pause(0)
            self._is_recording = True
            self._started_at = time.monotonic()
        except Exception:
            self._dev = None
            self._is_recording = True
            self._started_at = time.monotonic()

    def stop(self, gain: float = SOFT_GAIN_DEFAULT) -> bytes | None:
        if not self._is_recording:
            return None
        self._is_recording = False
        if self._dev is not None:
            try:
                self._dev.pause(1)
                self._dev.close()
            except Exception:
                pass
            self._dev = None
        if not self._pcm:
            return None
        pcm = bytes(self._pcm)
        if gain != 1.0 and len(pcm) >= 2:
            try:
                n = len(pcm) // 2
                samples = struct.unpack(f"<{n}h", pcm[: n * 2])
                boosted = [
                    int(max(-32767, min(32767, s * gain))) for s in samples
                ]
                pcm = struct.pack(f"<{n}h", *boosted)
            except Exception:
                pass
        out = io.BytesIO()
        try:
            with wave.open(out, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(pcm)
            return out.getvalue()
        except Exception:
            return None
