"""Audio manager and procedural SFX for Mondo Contrari."""

from __future__ import annotations

from collections import deque
import math
from pathlib import Path
from typing import Final

import pygame

_SAMPLE_RATE: Final = 22_050
MAX_SPEECH_QUEUE: Final = 3


class ContrariSpeechQueue:
    """FIFO queue preventing audio overlaps and managing speech pacing for toddlers."""

    def __init__(self, audio_manager: ContrariAudio) -> None:
        self._audio = audio_manager
        self._queue: deque[tuple[str, float]] = deque(maxlen=MAX_SPEECH_QUEUE)
        self._cooldown: float = 0.0

    def enqueue(self, cue_id: str, delay_after: float = 0.3) -> None:
        if self._queue and self._queue[-1][0] == cue_id:
            return
        if len(self._queue) < MAX_SPEECH_QUEUE:
            self._queue.append((cue_id, delay_after))

    def clear(self) -> None:
        self._queue.clear()
        self._cooldown = 0.0
        self._audio.stop_speech()

    def update(self, dt: float) -> None:
        if self._cooldown > 0.0:
            self._cooldown -= dt
            return

        if self._audio.is_speech_playing():
            return

        if not self._queue:
            return

        cue_id, delay_after = self._queue.popleft()
        self._audio.play_speech(cue_id)
        self._cooldown = delay_after


class ContrariAudio:
    """Manage playback of localized voice cues and synthesized physical SFX."""

    def __init__(self, package_root: Path, locale: str = "it") -> None:
        self.locale = locale
        self._package_root = package_root
        self._speech_sounds: dict[str, pygame.mixer.Sound] = {}
        self._sfx_sounds: dict[str, pygame.mixer.Sound] = {}
        self._speech_channel: pygame.mixer.Channel | None = None
        self._sfx_channel: pygame.mixer.Channel | None = None
        self._available = False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(8)
            self._speech_channel = pygame.mixer.Channel(0)
            self._sfx_channel = pygame.mixer.Channel(1)
            self._available = True
            self._load_speech_clips()
            self._build_procedural_sfx()
        except (pygame.error, RuntimeError):
            self._available = False

    def _load_speech_clips(self) -> None:
        audio_dir = self._package_root / "locales" / self.locale / "audio"
        if not audio_dir.exists():
            return
        for wav_file in audio_dir.glob("*.wav"):
            try:
                self._speech_sounds[wav_file.stem] = pygame.mixer.Sound(str(wav_file))
            except (pygame.error, RuntimeError):
                pass

    def play_speech(self, cue_id: str) -> None:
        if not self._available or self._speech_channel is None:
            return
        sound = self._speech_sounds.get(cue_id)
        if sound is not None:
            try:
                self._speech_channel.play(sound)
            except (pygame.error, RuntimeError):
                pass

    def stop_speech(self) -> None:
        if self._speech_channel is not None and self._speech_channel.get_busy():
            self._speech_channel.stop()

    def is_speech_playing(self) -> bool:
        return self._speech_channel is not None and self._speech_channel.get_busy()

    def play_sfx(self, sfx_name: str) -> None:
        if not self._available:
            return
        sound = self._sfx_sounds.get(sfx_name)
        if sound is not None:
            try:
                for i in range(2, 8):
                    ch = pygame.mixer.Channel(i)
                    if not ch.get_busy():
                        ch.play(sound)
                        return
                pygame.mixer.Channel(2).play(sound)
            except (pygame.error, RuntimeError):
                pass

    def _build_procedural_sfx(self) -> None:
        # 1. Pop: UI tap sound
        self._sfx_sounds["pop"] = self._synthesize_sweep(_SAMPLE_RATE, 0.10, 420.0, 780.0)
        # 2. Boing: springy jump
        self._sfx_sounds["boing"] = self._synthesize_sweep(_SAMPLE_RATE, 0.26, 210.0, 520.0)
        # 3. Whoosh: swift motion
        self._sfx_sounds["whoosh"] = self._synthesize_sweep(_SAMPLE_RATE, 0.22, 650.0, 220.0)
        # 4. Ding: cheerful bell tone
        self._sfx_sounds["ding"] = self._synthesize_tone(_SAMPLE_RATE, 0.35, 1174.66, harmonics=(1.0, 0.4, 0.15))
        # 5. Creak: playful door opening
        self._sfx_sounds["creak"] = self._synthesize_creak(_SAMPLE_RATE, 0.25)

    @staticmethod
    def _synthesize_tone(
        sample_rate: int,
        duration: float,
        freq: float,
        harmonics: tuple[float, ...] = (1.0,),
    ) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-4.2 * (t / duration))
            val = 0.0
            for h_idx, amp in enumerate(harmonics):
                val += amp * math.sin(2.0 * math.pi * freq * (h_idx + 1) * t)
            sample_val = int(val * env * 12000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_sweep(
        sample_rate: int,
        duration: float,
        start_freq: float,
        end_freq: float,
    ) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            frac = t / duration
            env = math.sin(math.pi * frac)
            freq = start_freq + (end_freq - start_freq) * frac
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 11000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_creak(sample_rate: int, duration: float) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.sin(math.pi * (t / duration))
            freq = 160.0 + 80.0 * math.sin(t * 70.0)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 9000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))
