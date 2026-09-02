"""Audio playback and channel coordination for Il Bosco dei Numeri di Tito."""

from __future__ import annotations

import math
from pathlib import Path

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

VOICE_CHANNEL_ID = 0
SFX_CHANNEL_ID = 1


class BoscoAudio:
    """Coordinates cached voice playback and lightweight procedural SFX."""

    def __init__(self, root: Path, resources: LocalizedResources) -> None:
        self.root = root
        self.resources = resources
        self._voice_channel: pygame.mixer.Channel | None = None
        self._sfx_channel: pygame.mixer.Channel | None = None
        self._voice_clips: dict[str, pygame.mixer.Sound] = {}
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._init_mixer()

    def _init_mixer(self) -> None:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(
                    frequency=44100,
                    size=-16,
                    channels=2,
                    buffer=1024,
                )
            except pygame.error:
                return
        pygame.mixer.set_num_channels(8)
        self._voice_channel = pygame.mixer.Channel(VOICE_CHANNEL_ID)
        self._sfx_channel = pygame.mixer.Channel(SFX_CHANNEL_ID)
        self._build_sfx()

    def _get_clip(self, name: str) -> pygame.mixer.Sound | None:
        cached = self._voice_clips.get(name)
        if cached is not None:
            return cached

        locale = self.resources.context.selected.language
        path = self.root / "assets" / "audio" / locale / f"{name}.wav"
        if not path.is_file():
            path = self.root / "assets" / "audio" / "it" / f"{name}.wav"

        if not path.is_file():
            return None
        try:
            sound = pygame.mixer.Sound(str(path))
        except pygame.error:
            return None
        self._voice_clips[name] = sound
        return sound

    def play_count_number(self, n: int) -> None:
        """Play one reviewed pedagogical counting clip and a cached tap cue."""
        sound = self._get_clip(f"count_{n}")
        if sound is not None and self._voice_channel is not None:
            self._voice_channel.play(sound)
        self.play_tap()

    def play_intro(self) -> None:
        sound = self._get_clip("intro")
        if sound is not None and self._voice_channel is not None:
            self._voice_channel.play(sound)

    def play_ask_number(self, n: int) -> None:
        sound = self._get_clip(f"ask_{n}")
        if sound is not None and self._voice_channel is not None:
            self._voice_channel.play(sound)

    def play_well_done(self) -> None:
        sound = self._get_clip("well_done")
        if sound is not None and self._voice_channel is not None:
            self._voice_channel.play(sound)
        self.play_chime()

    def play_try_again(self) -> None:
        sound = self._get_clip("try_again")
        if sound is not None and self._voice_channel is not None:
            self._voice_channel.play(sound)
        self.play_wobble()

    def play_celebration(self, n: int | None = None) -> None:
        """Repeat final cardinality, then queue Tito praise without overlap."""
        self.play_fanfare()
        if self._voice_channel is None:
            return

        final_num_clip = self._get_clip(f"count_{n}") if n is not None else None
        praise_clip = self._get_clip("celebrate")

        if final_num_clip is not None and praise_clip is not None:
            self._voice_channel.play(final_num_clip)
            self._voice_channel.queue(praise_clip)
        elif final_num_clip is not None:
            self._voice_channel.play(final_num_clip)
        elif praise_clip is not None:
            self._voice_channel.play(praise_clip)

    def play_tap(self) -> None:
        self._play_sfx("tap")

    def play_chime(self) -> None:
        self._play_sfx("chime")

    def play_wobble(self) -> None:
        self._play_sfx("wobble")

    def play_fanfare(self) -> None:
        self._play_sfx("fanfare")

    def _play_sfx(self, name: str) -> None:
        sound = self._sfx.get(name)
        if sound is None or self._sfx_channel is None:
            return
        try:
            self._sfx_channel.play(sound)
        except pygame.error:
            pass

    def _build_sfx(self) -> None:
        """Build bounded procedural clips once, never in the interaction hot path."""
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        sample_rate, channel_count = spec
        try:
            self._sfx = {
                "tap": self._synthesize_tone(
                    sample_rate,
                    channel_count,
                    520.0,
                    0.08,
                    "sine",
                    0.55,
                ),
                "chime": self._synthesize_tone(
                    sample_rate,
                    channel_count,
                    880.0,
                    0.18,
                    "sine",
                    0.65,
                ),
                "wobble": self._synthesize_tone(
                    sample_rate,
                    channel_count,
                    240.0,
                    0.22,
                    "triangle",
                    0.50,
                ),
                "fanfare": self._synthesize_fanfare(sample_rate, channel_count),
            }
        except pygame.error:
            self._sfx.clear()

    @staticmethod
    def _synthesize_tone(
        sample_rate: int,
        channel_count: int,
        frequency: float,
        duration: float,
        wave: str,
        volume: float,
    ) -> pygame.mixer.Sound:
        sample_count = max(1, int(sample_rate * duration))
        raw = bytearray()
        for index in range(sample_count):
            t = index / sample_rate
            decay = max(0.0, 1.0 - (index / sample_count) ** 1.5)
            if wave == "triangle":
                value = (
                    2.0
                    * abs(2.0 * (t * frequency - math.floor(t * frequency + 0.5)))
                    - 1.0
                )
            else:
                value = math.sin(2.0 * math.pi * frequency * t)
            sample = int(max(-1.0, min(1.0, value * decay * volume)) * 32767)
            append_mono_pcm16(raw, sample, channel_count)
        return pygame.mixer.Sound(buffer=bytes(raw))

    @staticmethod
    def _synthesize_fanfare(
        sample_rate: int,
        channel_count: int,
    ) -> pygame.mixer.Sound:
        """Render the four-note reward as one sequenced clip."""
        notes = (
            (0.00, 0.16, 523.25),
            (0.14, 0.16, 659.25),
            (0.28, 0.16, 783.99),
            (0.42, 0.38, 1046.50),
        )
        total_duration = 0.82
        sample_count = max(1, int(sample_rate * total_duration))
        raw = bytearray()
        for index in range(sample_count):
            t = index / sample_rate
            value = 0.0
            for start, duration, frequency in notes:
                if start <= t < start + duration:
                    local_t = t - start
                    envelope = math.exp(-3.5 * (local_t / duration))
                    value += math.sin(2.0 * math.pi * frequency * local_t) * envelope
            sample = int(max(-1.0, min(1.0, value * 0.55)) * 32767)
            append_mono_pcm16(raw, sample, channel_count)
        return pygame.mixer.Sound(buffer=bytes(raw))
