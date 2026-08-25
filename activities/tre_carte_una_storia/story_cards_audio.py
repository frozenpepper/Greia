from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
from typing import Final

import pygame


_SAMPLE_RATE: Final = 22_050


class StoryAudio:
    """Prepare and play Lilli voice prompts, story narrations, and procedural feedback."""

    def __init__(self, package_root: Path | None = None, locale: str = "it") -> None:
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
                "card_swap": self._tone(440.0, 0.05, 0.12),
                "select": self._tone(700.0, 0.04, 0.10),
                "correct": self._chime(),
                "wrong_hint": self._wobble(),
                "save": self._fanfare(),
                "delete": self._tone(280.0, 0.12, 0.15),
                "full": self._tone(330.0, 0.16, 0.20),
            }
            if self._package_root is not None:
                self._load_speech_clips()
        except (pygame.error, ValueError, OSError):
            self._speech_clips = {}
            self._sfx_clips = {}

    def _load_speech_clips(self) -> None:
        if self._package_root is None:
            return
        audio_dir = self._package_root / "assets" / "audio" / self._locale
        if not audio_dir.exists():
            return
        for wav_file in audio_dir.glob("*.wav"):
            try:
                sound = pygame.mixer.Sound(str(wav_file))
                self._speech_clips[wav_file.stem] = sound
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

    def play_slot(self, slot_idx: int) -> None:
        cue = f"slot_{slot_idx + 1}"
        self.play_speech(cue)

    def play_story_sentence(self, seed_id: str, card_index: int) -> None:
        cue = f"story_{seed_id}_c{card_index + 1}"
        self.play_speech(cue)

    def play_caption_intro(self) -> None:
        self.play_speech("caption_intro")

    def play_feedback(self, correct: bool) -> None:
        """Play celebratory chime or gentle wobble alongside spoken praise."""
        if correct:
            self.play("correct")
            praise = self._rng.choice(["correct_1", "correct_2", "correct_3"])
            self.play_speech(praise)
        else:
            self.play("wrong_hint")
            self.play_speech("retry_1")

    @staticmethod
    def _tone(frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        count = max(1, int(_SAMPLE_RATE * duration))
        amplitude = max(0, min(32767, int(32767 * volume)))
        samples = array(
            "h",
            (
                int(
                    amplitude
                    * math.sin(math.pi * (i / count))
                    * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE)
                )
                for i in range(count)
            ),
        )
        return pygame.mixer.Sound(buffer=samples.tobytes())

    @staticmethod
    def _chime() -> pygame.mixer.Sound:
        notes = [523.25, 659.25, 783.99]
        dur = 0.08
        all_samples = array("h")
        for freq in notes:
            count = int(_SAMPLE_RATE * dur)
            for i in range(count):
                env = math.sin(math.pi * (i / count))
                val = int(14000 * env * math.sin(2.0 * math.pi * freq * i / _SAMPLE_RATE))
                all_samples.append(val)
        return pygame.mixer.Sound(buffer=all_samples.tobytes())

    @staticmethod
    def _wobble() -> pygame.mixer.Sound:
        notes = [330.0, 277.0]
        dur = 0.10
        all_samples = array("h")
        for freq in notes:
            count = int(_SAMPLE_RATE * dur)
            for i in range(count):
                env = math.sin(math.pi * (i / count))
                val = int(12000 * env * math.sin(2.0 * math.pi * freq * i / _SAMPLE_RATE))
                all_samples.append(val)
        return pygame.mixer.Sound(buffer=all_samples.tobytes())

    @staticmethod
    def _fanfare() -> pygame.mixer.Sound:
        notes = [440.0, 554.37, 659.25, 880.0]
        dur = 0.07
        all_samples = array("h")
        for freq in notes:
            count = int(_SAMPLE_RATE * dur)
            for i in range(count):
                env = math.sin(math.pi * (i / count))
                val = int(14000 * env * math.sin(2.0 * math.pi * freq * i / _SAMPLE_RATE))
                all_samples.append(val)
        return pygame.mixer.Sound(buffer=all_samples.tobytes())
