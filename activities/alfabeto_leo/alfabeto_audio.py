"""Audio manager and synthesis for L'Alfabeto di Leo."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

MAX_SIMULTANEOUS_CHANNELS: Final[int] = 4
AUDIO_DIR = Path(__file__).resolve().parent / "assets" / "audio"


class AlfabetoAudio:
    """Cheerful, gentle musical and spoken audio feedback for letter exploration."""

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

    def play_guess_intro(self) -> None:
        """Play opening prompt when switching to guess mode."""
        self.play_spoken("mode_guess_intro")

    def play_question(self, char: str) -> None:
        """Play spoken question for pre-readers: 'Dov'è la lettera S?'."""
        self.play_spoken(f"ask_{char.upper()}")

    def play_letter(self, char: str) -> None:
        """Play cached marimba feedback and the reviewed spoken letter clip."""
        char_upper = char.upper()
        self.play(f"letter_{char_upper}")
        self.play_spoken(f"letter_{char_upper}")

    def play_wobble(self) -> None:
        """Play gentle wobble sound and gentle retry encouragement."""
        self.play("wobble")
        self.play_spoken("try_again")

    def play_celebration(self) -> None:
        """Play celebratory fanfare and praise."""
        self.play("celebrate")
        self.play_spoken("well_done")

    def _load_spoken_assets(self) -> None:
        loc_dir = AUDIO_DIR / self.locale
        # Never substitute Italian letter names or phonemes for another
        # teaching language. Missing approved speech stays unavailable.
        if not loc_dir.is_dir():
            return

        for wav_path in loc_dir.glob("*.wav"):
            try:
                self._spoken_sounds[wav_path.stem] = pygame.mixer.Sound(str(wav_path))
            except pygame.error:
                pass

    def _build_sounds(self) -> None:
        """Build the bounded procedural set once, outside interaction hot paths."""
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        sample_rate, channel_count = spec

        for index in range(26):
            char = chr(ord("A") + index)
            frequency = 261.63 * (2.0 ** (index / 12.0))
            self._sounds[f"letter_{char}"] = self._synthesize_marimba(
                sample_rate,
                channel_count,
                0.45,
                frequency,
            )

        self._sounds["pop"] = self._synthesize_pop(sample_rate, channel_count, 0.22)
        self._sounds["wobble"] = self._synthesize_wobble(
            sample_rate,
            channel_count,
            0.35,
        )
        self._sounds["celebrate"] = self._synthesize_fanfare(sample_rate, channel_count)

    @staticmethod
    def _synthesize_marimba(
        sample_rate: int,
        channel_count: int,
        duration: float,
        freq: float,
    ) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        harmonics = (1.0, 0.35, 0.12)
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-6.0 * (t / duration))
            val = 0.0
            for h_idx, amp in enumerate(harmonics):
                val += amp * math.sin(2.0 * math.pi * freq * (h_idx + 1) * t)
            sample_val = int(val * env * 14000)
            append_mono_pcm16(buf, sample_val, channel_count)
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_pop(
        sample_rate: int,
        channel_count: int,
        duration: float,
    ) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-12.0 * (t / duration))
            freq = 300.0 + 500.0 * math.sin(math.pi * (t / duration))
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 12000)
            append_mono_pcm16(buf, sample_val, channel_count)
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_wobble(
        sample_rate: int,
        channel_count: int,
        duration: float,
    ) -> pygame.mixer.Sound:
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.sin(math.pi * (t / duration))
            freq = 240.0 + 35.0 * math.sin(24.0 * math.pi * t)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 11000)
            append_mono_pcm16(buf, sample_val, channel_count)
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synthesize_fanfare(
        sample_rate: int,
        channel_count: int,
    ) -> pygame.mixer.Sound:
        notes = [
            (0.0, 0.14, 523.25),
            (0.12, 0.14, 659.25),
            (0.24, 0.14, 783.99),
            (0.36, 0.45, 1046.5),
        ]
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
            append_mono_pcm16(buf, sample_val, channel_count)
        return pygame.mixer.Sound(buffer=bytes(buf))
