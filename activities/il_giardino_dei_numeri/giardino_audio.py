"""Audio manager and synthesis for Il Giardino dei Numeri."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

MAX_SIMULTANEOUS_CHANNELS: Final[int] = 4
AUDIO_DIR = Path(__file__).resolve().parent / "assets" / "audio"


class GiardinoAudio:
    """Soft, cheerful musical and spoken feedback for toddler counting."""

    def __init__(self, locale: str = "it") -> None:
        self.locale = locale.split("-")[0]
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._spoken_sounds: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        try:
            if pygame.mixer.get_init() is not None:
                self._build_sounds()
                self._load_spoken_assets()
                self._available = True
        except (pygame.error, RuntimeError):
            self._available = False

    def play(self, sound_name: str) -> None:
        if not self._available:
            return
        sound = self._sounds.get(sound_name)
        if sound is not None:
            try:
                for i in range(2, MAX_SIMULTANEOUS_CHANNELS):
                    ch = pygame.mixer.Channel(i)
                    if not ch.get_busy():
                        ch.play(sound)
                        return
                pygame.mixer.Channel(2).play(sound)
            except (pygame.error, RuntimeError):
                pass

    def play_spoken(self, cue_name: str) -> None:
        """Play voice on dedicated voice channel (channel 0)."""
        if not self._available:
            return
        sound = self._spoken_sounds.get(cue_name)
        if sound is not None:
            try:
                pygame.mixer.Channel(0).play(sound)
            except (pygame.error, RuntimeError):
                pass

    def play_intro(self) -> None:
        """Play friendly opening prompt for pre-readers."""
        self.play_spoken("intro")

    def play_count(self, count: int) -> None:
        """Play ascending musical chime and Dani's spoken voice for numbers 1 to 5."""
        clamped = max(1, min(5, count))
        # 1. Play musical chime on SFX channel
        self.play(f"count_{clamped}")
        # 2. Play spoken number on Voice channel
        self.play_spoken(f"count_{clamped}")

    def play_celebration(self) -> None:
        """Play celebration music and Dani's cheer."""
        self.play("celebrate")
        self.play_spoken("well_done")

    def play_basket_full(self) -> None:
        """Play praise when basket is full."""
        self.play("rustle")
        self.play_spoken("basket_full")

    def _load_spoken_assets(self) -> None:
        loc_dir = AUDIO_DIR / self.locale
        if not loc_dir.is_dir():
            loc_dir = AUDIO_DIR / "it"
        if not loc_dir.is_dir():
            return

        for wav_path in loc_dir.glob("*.wav"):
            try:
                self._spoken_sounds[wav_path.stem] = pygame.mixer.Sound(str(wav_path))
            except Exception:
                pass

    def _build_sounds(self) -> None:
        sample_rate = 22050

        # Pentatonic scale for counting 1..5: C5, D5, E5, G5, A5
        pentatonic = {
            "count_1": 523.25,  # C5
            "count_2": 587.33,  # D5
            "count_3": 659.25,  # E5
            "count_4": 783.99,  # G5
            "count_5": 880.00,  # A5
        }
        for name, freq in pentatonic.items():
            self._sounds[name] = self._synthesize_chime(sample_rate, 0.55, freq)

        # Giggle: soft light dual-pip
        self._sounds["giggle"] = self._synthesize_giggle(sample_rate, 0.35)

        # Ripple / gentle water droplet
        self._sounds["ripple"] = self._synthesize_droplet(sample_rate, 0.25, 440.0)

        # Basket rustle / hop
        self._sounds["rustle"] = self._synthesize_rustle(sample_rate, 0.30)

        # Celebration fanfare
        self._sounds["celebrate"] = self._synthesize_fanfare(sample_rate)

    @staticmethod
    def _synthesize_chime(sample_rate: int, duration: float, freq: float) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        harmonics = (1.0, 0.45, 0.20, 0.08)
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-4.5 * (t / duration))
            val = 0.0
            for h_idx, amp in enumerate(harmonics):
                val += amp * math.sin(2.0 * math.pi * freq * (h_idx + 1) * t)
            sample_val = int(val * env * 14000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_giggle(sample_rate: int, duration: float) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.sin(math.pi * (t / duration))
            freq = 600.0 + 150.0 * math.sin(16.0 * math.pi * t)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 10000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_droplet(sample_rate: int, duration: float, start_freq: float) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-8.0 * (t / duration))
            freq = start_freq + 200.0 * (t / duration)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 9000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_rustle(sample_rate: int, duration: float) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.sin(math.pi * (t / duration))
            val = math.sin(2.0 * math.pi * 180.0 * t) * 0.7 + math.sin(2.0 * math.pi * 320.0 * t) * 0.3
            sample_val = int(val * env * 10000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_fanfare(sample_rate: int) -> pygame.mixer.Sound:
        notes = [(0.0, 0.15, 523.25), (0.12, 0.15, 659.25), (0.24, 0.15, 783.99), (0.36, 0.45, 1046.5)]
        total_duration = 0.85
        num_samples = int(sample_rate * total_duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            sample_sum = 0.0
            for start, dur, freq in notes:
                if start <= t < start + dur:
                    local_t = t - start
                    env = math.exp(-3.5 * (local_t / dur))
                    sample_sum += math.sin(2.0 * math.pi * freq * local_t) * env
            sample_val = int(sample_sum * 12000)
            sample_val = max(-32767, min(32767, sample_val))
            buf.extend(int(sample_val).to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))
