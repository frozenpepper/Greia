"""Momo's approved speech clips and small procedural cues for Luci di Momo.

Speech uses only the package's existing recordings (resolved through the
shared ``LocalizedResources.speech_paths`` with English fallback):
``welcome`` ("look closely at how many fireflies glow ..."),
``prompt_choose`` ("how many fireflies did you see?"), ``count_1..5``
("three fireflies!"), ``correct_1..5`` (praise), ``retry_1..2`` ("almost! look
again ...") and ``garden_complete``. Sound effects are short synthesized tones
generated once at start-up (a bounded set); nothing is decoded per frame.
Everything fails soft to silence when the mixer is unavailable.
"""

from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources


_SAMPLE_RATE: Final = 22_050
SPOKEN_COUNTS: Final = 5
_CHIME_BASE: Final = 523.25  # C5; counting chimes climb a major scale
_SCALE: Final = (0, 2, 4, 5, 7, 9, 11, 12, 14, 16)


class FireflyAudio:
    """Own Momo's speech/SFX channels and a bounded clip cache."""

    def __init__(
        self, package_root: Path | None = None, locale: str = "it",
        resources: LocalizedResources | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._resources = resources
        self._locale = locale
        self._package_root = package_root
        self._speech_clips: dict[str, pygame.mixer.Sound] = {}
        self._sfx_clips: dict[str, pygame.mixer.Sound] = {}
        self._chimes: list[pygame.mixer.Sound] = []
        self._speech_channel: pygame.mixer.Channel | None = None
        self._sfx_channel: pygame.mixer.Channel | None = None
        self._chime_channel: pygame.mixer.Channel | None = None
        self._rng = rng if rng is not None else random.Random()

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=256)
            pygame.mixer.set_num_channels(8)
            self._speech_channel = pygame.mixer.Channel(0)
            self._sfx_channel = pygame.mixer.Channel(1)
            self._chime_channel = pygame.mixer.Channel(2)

            self._sfx_clips = {
                "reveal": self._tone(660.0, 0.10, 0.14),
                "correct": self._tone(880.0, 0.12, 0.16),
                "retry": self._tone(392.0, 0.10, 0.10),
                "complete": self._tone(1046.5, 0.22, 0.16),
                "light": self._tone(1318.5, 0.09, 0.12),
            }
            self._chimes = [
                self._tone(_CHIME_BASE * 2 ** (step / 12), 0.09, 0.12) for step in _SCALE
            ]
            if self._package_root is not None:
                self._load_speech_clips()
        except (pygame.error, ValueError, OSError):
            self._speech_clips = {}
            self._sfx_clips = {}
            self._chimes = []

    def _load_speech_clips(self) -> None:
        if self._package_root is None:
            return
        if self._resources is not None:
            # The shared resolver owns locale-specific discovery and English
            # fallback. This Activity still owns decoding and speech channels.
            for stem, path in self._resources.speech_paths().items():
                try:
                    self._speech_clips[stem] = pygame.mixer.Sound(str(path))
                except (pygame.error, OSError):
                    continue
            return
        audio_dir = self._package_root / "assets" / "audio" / self._locale
        if not audio_dir.exists():
            return
        for wav_file in audio_dir.glob("*.wav"):
            try:
                self._speech_clips[wav_file.stem] = pygame.mixer.Sound(str(wav_file))
            except (pygame.error, OSError):
                continue

    # -- primitives -----------------------------------------------------------

    def play(self, cue: str) -> None:
        sound = self._sfx_clips.get(cue)
        if sound is None or self._sfx_channel is None:
            return
        try:
            self._sfx_channel.play(sound)
        except pygame.error:
            return

    def chime(self, number: int) -> None:
        """A rising counting tick (1 is lowest); silent beyond the prepared set."""

        if not self._chimes or self._chime_channel is None:
            return
        index = max(1, min(len(self._chimes), int(number))) - 1
        try:
            self._chime_channel.play(self._chimes[index])
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

    def speech_seconds(self, cue_id: str) -> float:
        """Length of an approved clip (0.0 when it is not available)."""

        sound = self._speech_clips.get(cue_id)
        if sound is None:
            return 0.0
        try:
            return float(sound.get_length())
        except pygame.error:
            return 0.0

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

    # -- semantic cues ----------------------------------------------------------

    def play_welcome(self) -> None:
        self.play_speech("welcome")

    def play_prompt_choose(self) -> None:
        self.play_speech("prompt_choose")

    def play_count(self, quantity: int) -> bool:
        """Say "N fireflies" when an approved clip exists (1..5); True if spoken."""

        cue = f"count_{quantity}"
        if quantity > SPOKEN_COUNTS or cue not in self._speech_clips:
            return False
        self.play_speech(cue)
        return True

    def play_garden_complete(self) -> None:
        self.play("complete")
        self.play_speech("garden_complete")

    def praise(self) -> None:
        self.play_speech(self._rng.choice(["correct_1", "correct_2", "correct_3", "correct_4", "correct_5"]))

    def encourage(self) -> None:
        self.play_speech(self._rng.choice(["retry_1", "retry_2"]))

    def play_feedback(self, correct: bool) -> None:
        """Non-verbal chime plus spoken reinforcement (kept for callers/tests)."""

        if correct:
            self.play("correct")
            self.praise()
        else:
            self.play("retry")
            self.encourage()

    @staticmethod
    def _tone(frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        count = max(1, int(_SAMPLE_RATE * duration))
        amplitude = max(0, min(32767, int(32767 * volume)))
        fade = max(1, count // 5)
        samples = array(
            "h",
            (
                int(
                    amplitude
                    * min(1.0, (count - i) / fade, (i + 1) / 32)
                    * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE)
                )
                for i in range(count)
            ),
        )
        channels = 1
        init = pygame.mixer.get_init()
        if init is not None:
            channels = init[2]
        if channels > 1:
            samples = array("h", (value for value in samples for _ in range(channels)))
        return pygame.mixer.Sound(buffer=samples.tobytes())
