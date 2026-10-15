"""Audio owners for Teatrino delle Fiabe.

* ``MicrophoneRecorder`` - bounded, non-blocking microphone capture for one
  show (with a live voice level that makes the held puppet's mouth move);
* ``ImportedNarrationTrack`` - a narration WAV chosen from My Creations,
  validated, trimmed on an early stop, with a coarse loudness envelope so
  puppets lip-sync to it too;
* ``SoundManager`` - the theatre's short synthesized cues (sound stickers,
  curtain, countdown pips), prepared once;
* ``HostVoice`` - the host friend's owner-approved shared character takes
  (selected language, then English, else silence). No speech is generated.
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path
import random
import struct
import wave
from dataclasses import dataclass, field

import pygame

try:
    from pygame._sdl2 import audio as sdl2_audio
except ImportError:
    sdl2_audio = None

from greia_platform.activity_api import get_audio_capture_device, get_sdl_capture_device
from greia_platform.creation_media import CreationMediaError, WavCodec
from greia_platform.localization import shared_character_audio_path

ENVELOPE_HZ = 15
VOICE_THRESHOLD = 0.12


class MicrophoneRecorder:
    """Non-blocking low-latency microphone capture with a live voice level."""

    def __init__(self) -> None:
        self.enabled = True
        self.is_recording = False
        self.sample_rate = 22050
        self.recorded_pcm = bytearray()
        self.current_volume = 0.0
        self._dev = None
        # 45 s of mono PCM16 at 22.05 kHz plus slack; capture never grows past it.
        self._max_bytes = int(self.sample_rate * 2 * 47)

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
        self.enabled = not self.enabled
        return self.enabled

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
                room = self._max_bytes - len(self.recorded_pcm)
                if room > 0:
                    self.recorded_pcm.extend(data[:room])
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
        self.current_volume = 0.0
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
        self.recorded_pcm.clear()

        if len(raw_pcm) >= 2 and gain != 1.0:
            try:
                num_samples = len(raw_pcm) // 2
                samples = struct.unpack(f"<{num_samples}h", raw_pcm[: num_samples * 2])
                boosted = [int(max(-32767, min(32767, s * gain))) for s in samples]
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
    envelope: tuple[float, ...] = field(default=(), compare=False)

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
        return cls(prepared.data, duration, _loudness_envelope(prepared.data))

    def level_at(self, seconds: float) -> float:
        """Coarse loudness (0..1) at ``seconds`` for puppet lip-sync."""
        if not self.envelope or seconds < 0:
            return 0.0
        index = int(seconds * ENVELOPE_HZ)
        return self.envelope[index] if index < len(self.envelope) else 0.0

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


def _loudness_envelope(wav_bytes: bytes) -> tuple[float, ...]:
    """Peak level per 1/ENVELOPE_HZ window (bounded: <= 45 s * 15 values)."""

    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as source:
            channels = source.getnchannels()
            width = source.getsampwidth()
            rate = source.getframerate()
            pcm = source.readframes(source.getnframes())
    except (EOFError, OSError, wave.Error):
        return ()
    frame_bytes = channels * width
    window = max(1, rate // ENVELOPE_HZ)
    stride = 16
    levels: list[float] = []
    total = len(pcm) // frame_bytes
    for start in range(0, total, window):
        peak = 0
        for frame in range(start, min(total, start + window), stride):
            offset = frame * frame_bytes
            if width == 2:
                value = abs(int.from_bytes(pcm[offset : offset + 2], "little", signed=True))
            else:  # 8-bit unsigned
                value = abs(pcm[offset] - 128) * 256
            peak = max(peak, value)
        levels.append(min(1.0, peak / 16000.0))
        if len(levels) >= 45 * ENVELOPE_HZ + 2:
            break
    return tuple(levels)


def _wav(samples: list[float], rate: int) -> bytes:
    raw = bytearray()
    for value in samples:
        raw.extend(struct.pack("<h", int(max(-1.0, min(1.0, value)) * 26000)))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(raw))
    return buffer.getvalue()


class SoundManager:
    """Short synthesized theatre cues, prepared once (silent without a mixer).

    Cues are rendered as small mono WAVs at 16 kHz and handed to the mixer,
    which converts them to its own format, so the bank works whatever rate
    or channel count the Shell opened the mixer with.
    """

    RATE = 16000

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            for name, (voice, seconds) in self._recipes().items():
                count = int(self.RATE * seconds)
                samples = [voice(i / self.RATE, seconds) for i in range(count)]
                self._sounds[name] = pygame.mixer.Sound(io.BytesIO(_wav(samples, self.RATE)))
                self._sounds[name].set_volume(0.6)
        except Exception:
            self._sounds.clear()

    @staticmethod
    def _recipes() -> dict:
        def fade(t: float, d: float) -> float:
            return max(0.0, 1.0 - t / d)

        rng = random.Random(7)
        noise = [rng.random() * 2.0 - 1.0 for _ in range(4096)]

        def hiss(t: float) -> float:
            return noise[int(t * 16000) % len(noise)]

        def trumpet_note(t: float) -> float:
            return 523.25 if t < 0.15 else 659.25 if t < 0.3 else 783.99

        return {
            "pop": (lambda t, d: math.sin(2 * math.pi * (300 + 700 * (t / d)) * t) * fade(t, d), 0.12),
            "trumpet": (
                lambda t, d: (
                    0.6 * math.sin(2 * math.pi * trumpet_note(t) * t)
                    + 0.3 * math.sin(4 * math.pi * trumpet_note(t) * t)
                ) * min(1.0, t * 20.0) * fade(t, d),
                0.55,
            ),
            "magic": (
                lambda t, d: math.sin(2 * math.pi * (800 + 1200 * math.sin(t * 30)) * t)
                * (0.5 + 0.5 * math.sin(t * 80)) * fade(t, d) * 0.7,
                0.5,
            ),
            "applause": (
                lambda t, d: hiss(t) * (0.3 + 0.7 * (math.sin(t * 40) ** 2)) * (1.0 - (t / d) ** 0.5) * 0.6,
                0.8,
            ),
            "giggle": (
                lambda t, d: math.sin(2 * math.pi * (600 + 250 * math.sin(t * 35)) * t) * min(1.0, t * 15.0) * fade(t, d),
                0.4,
            ),
            "mystery": (
                lambda t, d: (
                    0.7 * math.sin(2 * math.pi * (220 + 80 * math.cos(t * 8)) * t)
                    + 0.3 * math.sin(2 * math.pi * (330 + 120 * math.sin(t * 12)) * t)
                ) * fade(t, d),
                0.6,
            ),
            "boing": (lambda t, d: math.sin(2 * math.pi * (160 + 600 * math.exp(-t * 8)) * t) * fade(t, d), 0.35),
            # Curtain glide: a soft filtered whoosh.
            "curtain": (lambda t, d: hiss(t) * math.sin(math.pi * t / d) * 0.35, 0.5),
            # Countdown lamps: two low pips and one bright "go" pip.
            "pip": (lambda t, d: math.sin(2 * math.pi * 660 * t) * math.exp(-t * 18), 0.16),
            "go": (lambda t, d: math.sin(2 * math.pi * 990 * t) * math.exp(-t * 9), 0.3),
            # A puppet goes back into the box.
            "poof": (lambda t, d: hiss(t) * math.exp(-t * 14) * 0.6 + math.sin(2 * math.pi * (500 - 600 * t) * t) * fade(t, d) * 0.3, 0.25),
            # The stage is full: a gentle "no more room" wobble.
            "full": (lambda t, d: math.sin(2 * math.pi * (300 + 40 * math.sin(t * 50)) * t) * fade(t, d) * 0.7, 0.3),
        }

    def play(self, sound_name: str) -> None:
        sound = self._sounds.get(sound_name)
        if sound is None:
            return
        try:
            sound.play()
        except Exception:
            pass

    def stop_all(self) -> None:
        for sound in self._sounds.values():
            try:
                sound.stop()
            except Exception:
                pass


class HostVoice:
    """The host friend's approved shared takes, loaded once (or silence)."""

    def __init__(self, speaker: str, cues: tuple[str, ...], locale: str, *, project_root: Path | None = None) -> None:
        self._voices: dict[str, pygame.mixer.Sound] = {}
        self._channel: pygame.mixer.Channel | None = None
        root = project_root if project_root is not None else Path(__file__).resolve().parents[2]
        for cue in cues:
            try:
                path = shared_character_audio_path(root, speaker, cue, locale)
                if path is not None:
                    self._voices[cue] = pygame.mixer.Sound(str(path))
            except Exception:
                continue

    def say(self, cue: str) -> float:
        """Play one take; returns its length in seconds (0 when silent)."""
        voice = self._voices.get(cue)
        if voice is None:
            return 0.0
        try:
            self.stop()
            self._channel = voice.play()
            return float(voice.get_length())
        except Exception:
            return 0.0

    def stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except Exception:
                pass
            self._channel = None

    @property
    def cues(self) -> tuple[str, ...]:
        return tuple(self._voices)


__all__ = ["HostVoice", "ImportedNarrationTrack", "MicrophoneRecorder", "SoundManager", "VOICE_THRESHOLD"]
