"""Audio playback and channel coordination for Il Bosco dei Numeri di Tito."""

from __future__ import annotations

import math
from pathlib import Path

import pygame

from greia_platform.localization import LocalizedResources

VOICE_CHANNEL_ID = 0
SFX_CHANNEL_ID = 1


class BoscoAudio:
    """Coordinates dedicated voice playback and synthesized SFX."""

    def __init__(self, root: Path, resources: LocalizedResources) -> None:
        self.root = root
        self.resources = resources
        self._voice_channel: pygame.mixer.Channel | None = None
        self._sfx_channel: pygame.mixer.Channel | None = None
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._init_mixer()

    def _init_mixer(self) -> None:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            except Exception:
                return
        pygame.mixer.set_num_channels(8)
        self._voice_channel = pygame.mixer.Channel(VOICE_CHANNEL_ID)
        self._sfx_channel = pygame.mixer.Channel(SFX_CHANNEL_ID)

    def _get_clip(self, name: str) -> pygame.mixer.Sound | None:
        if name in self._sounds:
            return self._sounds[name]

        locale = self.resources.context.selected.language
        path = self.root / "assets" / "audio" / locale / f"{name}.wav"
        if not path.is_file():
            # Fallback to IT
            path = self.root / "assets" / "audio" / "it" / f"{name}.wav"

        if path.is_file():
            try:
                sound = pygame.mixer.Sound(str(path))
                self._sounds[name] = sound
                return sound
            except Exception:
                pass
        return None

    def play_count_number(self, n: int) -> None:
        """Pedagogical counting number (1..10) on voice channel."""
        sound = self._get_clip(f"count_{n}")
        if sound and self._voice_channel:
            self._voice_channel.play(sound)
        self.play_tap()

    def play_intro(self) -> None:
        """Tito welcome on voice channel."""
        sound = self._get_clip("intro")
        if sound and self._voice_channel:
            self._voice_channel.play(sound)

    def play_ask_number(self, n: int) -> None:
        """Tito spoken question: 'Dov'è il numero N?'"""
        sound = self._get_clip(f"ask_{n}")
        if sound and self._voice_channel:
            self._voice_channel.play(sound)

    def play_well_done(self) -> None:
        """Tito congratulations."""
        sound = self._get_clip("well_done")
        if sound and self._voice_channel:
            self._voice_channel.play(sound)
        self.play_chime()

    def play_try_again(self) -> None:
        """Tito encouraging retry."""
        sound = self._get_clip("try_again")
        if sound and self._voice_channel:
            self._voice_channel.play(sound)
        self.play_wobble()

    def play_celebration(self) -> None:
        """Tito final milestone celebration."""
        sound = self._get_clip("celebrate")
        if sound and self._voice_channel:
            self._voice_channel.play(sound)
        self.play_fanfare()

    # Synthesized procedural SFX
    def play_tap(self) -> None:
        self._play_tone(520, duration=0.08, wave="sine", volume=0.55)

    def play_chime(self) -> None:
        self._play_tone(880, duration=0.18, wave="sine", volume=0.65)

    def play_wobble(self) -> None:
        self._play_tone(240, duration=0.22, wave="triangle", volume=0.5)

    def play_fanfare(self) -> None:
        notes = [523, 659, 784, 1046]
        for idx, freq in enumerate(notes):
            self._play_tone(freq, duration=0.12 + idx * 0.05, wave="sine", volume=0.6)

    def _play_tone(self, freq: int, duration: float = 0.1, wave: str = "sine", volume: float = 0.5) -> None:
        if not pygame.mixer.get_init() or not self._sfx_channel:
            return
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        raw_bytes = bytearray()

        for i in range(n_samples):
            t = float(i) / sample_rate
            decay = max(0.0, 1.0 - (float(i) / n_samples) ** 1.5)
            if wave == "sine":
                val = math.sin(2.0 * math.pi * freq * t)
            elif wave == "triangle":
                val = 2.0 * abs(2.0 * (t * freq - math.floor(t * freq + 0.5))) - 1.0
            else:
                val = math.sin(2.0 * math.pi * freq * t)

            sample_int = int(val * decay * volume * 32767)
            raw_bytes.extend(sample_int.to_bytes(2, byteorder="little", signed=True))
            raw_bytes.extend(sample_int.to_bytes(2, byteorder="little", signed=True))

        try:
            sound = pygame.mixer.Sound(buffer=bytes(raw_bytes))
            self._sfx_channel.play(sound)
        except Exception:
            pass
