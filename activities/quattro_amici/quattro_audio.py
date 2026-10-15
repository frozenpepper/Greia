"""Audio management and procedural sound synthesis for Quattro Amici in Fila.

Synthesizes rich tactile wood-on-wood clacks, slot sliding whoosh,
and triumphant melodic chimes in memory at startup matching the active
Pygame mixer specification. Gracefully handles dummy audio drivers.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec
from greia_platform.localization import shared_character_audio_path


class QuattroAudio:
    """Tactile wooden sound effects and character voice reactions."""

    def __init__(self, locale: str = "it") -> None:
        self.locale = locale.split("-")[0]
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._voice_sounds: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        try:
            if pygame.mixer.get_init() is not None:
                self._synthesize_effects()
                self._load_shared_voices()
                self._available = True
        except (pygame.error, RuntimeError):
            self._available = False

    def play(self, sound_name: str) -> None:
        """Play a sound effect on available non-voice channel."""
        if not self._available:
            return
        snd = self._sounds.get(sound_name)
        if snd is not None:
            try:
                # Channels 1-3 for sound effects
                for ch_id in range(1, 4):
                    ch = pygame.mixer.Channel(ch_id)
                    if not ch.get_busy():
                        ch.play(snd)
                        return
                pygame.mixer.Channel(1).play(snd)
            except (pygame.error, RuntimeError):
                pass

    def play_voice(self, voice_key: str) -> None:
        """Play character voice on dedicated channel 0."""
        if not self._available:
            return
        snd = self._voice_sounds.get(voice_key)
        if snd is not None:
            try:
                pygame.mixer.Channel(0).play(snd)
            except (pygame.error, RuntimeError):
                pass

    def play_drop_slide(self) -> None:
        """Slide sound as token falls through slot."""
        self.play("slide")

    def play_drop_clack(self) -> None:
        """Wood-on-wood clack as token hits bottom."""
        self.play("clack")

    def play_win(self, winner_is_flash: bool) -> None:
        """Play celebratory chime and matching character victory sound."""
        self.play("win_chime")
        self.play("cheer")
        if winner_is_flash:
            self.play_voice("flash_celebrate")
        else:
            self.play_voice("leo_celebrate")

    def play_hover(self) -> None:
        """Subtle click when moving selector."""
        self.play("hover")

    def play_click(self) -> None:
        """Button click."""
        self.play("click")

    def _synthesize_effects(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        sample_rate, channels = spec

        self._sounds["slide"] = self._synth_whoosh(sample_rate, channels, duration=0.22)
        self._sounds["clack"] = self._synth_clack(sample_rate, channels)
        self._sounds["win_chime"] = self._synth_arpeggio(sample_rate, channels)
        self._sounds["cheer"] = self._synth_cheer_fanfare(sample_rate, channels)
        self._sounds["hover"] = self._synth_wood_tap(sample_rate, channels, freq=380.0)
        self._sounds["click"] = self._synth_wood_tap(sample_rate, channels, freq=520.0)

    def _load_shared_voices(self) -> None:
        """Fetch owner-approved shared character speech through Greia locale."""
        project_root = Path(__file__).resolve().parents[2]
        for speaker in ("flash", "leo"):
            path = shared_character_audio_path(
                project_root, speaker, "celebrate.success", self.locale
            )
            if path is None:
                continue
            try:
                self._voice_sounds[f"{speaker}_celebrate"] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                pass

    @staticmethod
    def _synth_whoosh(sample_rate: int, channels: int, duration: float) -> pygame.mixer.Sound:
        """Smooth air and wooden slide whoosh."""
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.sin(math.pi * (t / duration)) ** 1.5
            freq = 420.0 - 180.0 * (t / duration)
            val = (
                math.sin(2.0 * math.pi * freq * t) * 0.6
                + math.sin(2.0 * math.pi * (freq * 1.5) * t) * 0.4
            )
            sample_val = int(val * env * 8500)
            append_mono_pcm16(buf, sample_val, channels)
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synth_clack(sample_rate: int, channels: int) -> pygame.mixer.Sound:
        """Deep tactile wood-on-wood impact with tiny spring bounce."""
        duration = 0.12
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            # Sharp attack, fast exponential decay
            env = math.exp(-32.0 * t)
            # Wood resonant modes: primary ~220Hz, secondary ~540Hz
            val = (
                math.sin(2.0 * math.pi * 220.0 * t) * 0.7
                + math.sin(2.0 * math.pi * 540.0 * t) * 0.3
            )
            # Subtle bounce echo at 45ms
            if t > 0.045:
                t2 = t - 0.045
                env2 = math.exp(-40.0 * t2) * 0.35
                val += math.sin(2.0 * math.pi * 280.0 * t2) * env2
            sample_val = int(val * env * 16000)
            append_mono_pcm16(buf, sample_val, channels)
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synth_wood_tap(sample_rate: int, channels: int, freq: float) -> pygame.mixer.Sound:
        """Short soft wooden tap for navigation clicks."""
        duration = 0.05
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-45.0 * t)
            val = math.sin(2.0 * math.pi * freq * t)
            sample_val = int(val * env * 10000)
            append_mono_pcm16(buf, sample_val, channels)
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synth_arpeggio(sample_rate: int, channels: int) -> pygame.mixer.Sound:
        """Magical rising pentatonic chime (C5 - E5 - G5 - C6)."""
        notes = [
            (0.00, 0.12, 523.25),
            (0.08, 0.12, 659.25),
            (0.16, 0.14, 783.99),
            (0.24, 0.35, 1046.50),
        ]
        total_duration = 0.65
        num_samples = int(sample_rate * total_duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            s_val = 0.0
            for start, dur, freq in notes:
                if start <= t < start + dur:
                    lt = t - start
                    env = math.exp(-6.0 * (lt / dur))
                    s_val += (
                        math.sin(2.0 * math.pi * freq * lt) * 0.7
                        + math.sin(2.0 * math.pi * (freq * 2.0) * lt) * 0.3
                    ) * env
            sample_val = int(s_val * 12000)
            append_mono_pcm16(buf, sample_val, channels)
        return pygame.mixer.Sound(buffer=bytes(buf))

    @staticmethod
    def _synth_cheer_fanfare(sample_rate: int, channels: int) -> pygame.mixer.Sound:
        """Warm brassy celebratory fanfare chord."""
        duration = 0.8
        num_samples = int(sample_rate * duration)
        buf = bytearray()
        chords = [(523.25, 0.4), (659.25, 0.3), (783.99, 0.3)]
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-3.0 * t)
            s_val = sum(math.sin(2.0 * math.pi * freq * t) * amp for freq, amp in chords)
            sample_val = int(s_val * env * 11000)
            append_mono_pcm16(buf, sample_val, channels)
        return pygame.mixer.Sound(buffer=bytes(buf))
