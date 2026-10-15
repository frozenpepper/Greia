"""Pedagogical speech audio and procedural feedback for Specchi Magici."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources

if __package__:
    from .mirror_model import ShapeKind
else:
    from mirror_model import ShapeKind


_SAMPLE_RATE: Final = 22_050


class MirrorAudio:
    """Prepare Lilli speech clips, nonverbal feedback tones, and fail soft when unavailable."""

    def __init__(
        self, package_root: Path | None = None, locale: str = "it",
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
                "place": self._tone(640.0, 0.05, 0.15),
                "correct": self._tone(920.0, 0.12, 0.18),
                "retry": self._tone(320.0, 0.08, 0.12),
                "complete": self._tone(1080.0, 0.22, 0.20),
            }
            if self._package_root is not None:
                self._load_speech_clips()
        except (pygame.error, ValueError, OSError):
            self._speech_clips = {}
            self._sfx_clips = {}

    def _load_speech_clips(self) -> None:
        if self._package_root is None:
            return
        if self._resources is not None:
            files = self._resources.speech_paths()
        else:
            audio_dir = self._package_root / "assets" / "audio" / self._locale
            files = {path.stem: path for path in audio_dir.glob("*.wav")}
        for stem, path in files.items():
            try:
                self._speech_clips[stem] = pygame.mixer.Sound(str(path))
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

    def play_welcome(self) -> None:
        self.play_speech("welcome")

    def play_prompt(self) -> None:
        self.play_speech("prompt_place")

    def play_shape(self, kind: ShapeKind) -> None:
        self.play_speech(f"shape_{kind.value}")

    def play_mosaic_complete(self) -> None:
        self.play("complete")
        self.play_speech("mosaic_complete")

    def play_feedback(self, correct: bool) -> None:
        """Play non-verbal chime/wobble with gender-neutral spoken reinforcement."""
        if correct:
            self.play("place")
            praise = self._rng.choice(["correct_1", "correct_2", "correct_3", "correct_4", "correct_5"])
            self.play_speech(praise)
        else:
            self.play("retry")
            retry = self._rng.choice(["retry_1", "retry_2"])
            self.play_speech(retry)

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

