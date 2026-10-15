"""Pedagogical speech audio and procedural feedback for La Casa del Dieci."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources


_SAMPLE_RATE: Final = 22_050


class TenHouseAudio:
    """Prepare pedagogical speech clips, nonverbal feedback tones, and fail soft when unavailable."""

    def __init__(
        self,
        package_root: Path | None = None,
        locale: str = "it",
        resources: LocalizedResources | None = None,
    ) -> None:
        self._resources = resources
        self._locale = locale
        self._package_root = package_root
        self._speech_clips: dict[str, pygame.mixer.Sound] = {}
        self._sfx_clips: dict[str, pygame.mixer.Sound] = {}
        self._speech_channel: pygame.mixer.Channel | None = None
        self._sfx_channel: pygame.mixer.Channel | None = None
        self._rng = random.Random(42)

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=256)
            pygame.mixer.set_num_channels(8)
            self._speech_channel = pygame.mixer.Channel(0)
            self._sfx_channel = pygame.mixer.Channel(1)

            self._sfx_clips = {
                "toggle": self._tone(520.0, 0.05, 0.14),
                "snap": self._tone(640.0, 0.04, 0.14),
                "correct": self._tone(880.0, 0.12, 0.18),
                "retry": self._tone(360.0, 0.09, 0.12),
                "complete": self._tone(1040.0, 0.22, 0.20),
            }
            if self._package_root is not None:
                self._load_speech_clips()
        except (pygame.error, ValueError, OSError):
            self._speech_clips = {}
            self._sfx_clips = {}

    def _load_speech_clips(self) -> None:
        if self._package_root is None:
            return
        audio_root = self._package_root / "assets" / "audio"
        selected = audio_root / self._locale
        english = audio_root / "en"
        # Retain eager short-cue decoding to avoid first-interaction hitches.
        # Filename discovery is Activity-local; LANGUAGE selection is shared.
        names = {
            file.stem
            for directory in (selected, english)
            if directory.is_dir()
            for file in directory.glob("*.wav")
        }
        for name in sorted(names):
            if self._resources is not None:
                path = self._resources.audio_path(
                    name, filename=f"{name}.wav"
                )
            else:
                path = selected / f"{name}.wav"
                if not path.is_file():
                    path = english / f"{name}.wav"
            if path is None or not path.is_file():
                continue
            try:
                self._speech_clips[name] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue

    def play(self, cue: str) -> None:
        sound = self._sfx_clips.get(cue)
        if sound is None or self._sfx_channel is None:
            return
        try:
            self._sfx_channel.play(sound)
        except pygame.error:
            return

    def play_speech(self, cue_id: str) -> None:
        sound = self._speech_clips.get(cue_id)
        if sound is None or self._speech_channel is None:
            return
        try:
            self._speech_channel.play(sound)
        except pygame.error:
            return

    def stop_speech(self) -> None:
        if self._speech_channel is not None:
            try:
                self._speech_channel.stop()
            except pygame.error:
                pass

    def is_speech_busy(self) -> bool:
        if self._speech_channel is None:
            return False
        return self._speech_channel.get_busy()

    def play_feedback(self, correct: bool) -> None:
        """Play positive celebratory or gentle retry feedback with verbal reinforcement."""
        if correct:
            self.play("correct")
            clip_name = self._rng.choice(["correct_1", "correct_2", "correct_3"])
            self.play_speech(clip_name)
        else:
            self.play("retry")
            clip_name = self._rng.choice(["retry_1", "retry_2"])
            self.play_speech(clip_name)

    @staticmethod
    def _tone(frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        count = max(1, int(_SAMPLE_RATE * duration))
        amplitude = max(0, min(32767, int(32767 * volume)))
        samples = array(
            "h",
            (
                int(amplitude * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE))
                for i in range(count)
            ),
        )
        return pygame.mixer.Sound(buffer=samples.tobytes())

