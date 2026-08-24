"""Audio and speech playback manager for Officina dei Suoni."""

from __future__ import annotations

from array import array
from collections import deque
import math
from pathlib import Path
from typing import Final

import pygame


_SAMPLE_RATE: Final = 22_050
MAX_QUEUE_LEN: Final = 4


class SpeechQueue:
    """Bounded FIFO speech queue for pedagogical audio sequencing."""

    def __init__(self, audio_manager: SoundWorkshopAudio) -> None:
        self._audio = audio_manager
        self._queue: deque[tuple[str, float]] = deque(maxlen=MAX_QUEUE_LEN)
        self._wait_timer = 0.0
        self._current_playing = False

    def enqueue(self, cue_id: str, delay_after: float = 0.0) -> None:
        if len(self._queue) < MAX_QUEUE_LEN:
            self._queue.append((cue_id, delay_after))

    def clear(self) -> None:
        self._queue.clear()
        self._wait_timer = 0.0
        self._audio.stop_speech()
        self._current_playing = False

    def update(self, dt: float) -> None:
        if self._wait_timer > 0.0:
            self._wait_timer -= dt
            return

        if self._audio.is_speech_busy():
            return

        self._current_playing = False

        if not self._queue:
            return

        cue_id, delay_after = self._queue.popleft()
        self._audio.play_speech(cue_id)
        self._current_playing = True
        self._wait_timer = delay_after


class SoundWorkshopAudio:
    """Load package pedagogical speech clips and prepare nonverbal feedback chimes."""

    def __init__(self, package_root: Path, locale: str = "it") -> None:
        self._locale = locale
        self._package_root = package_root
        self._speech_clips: dict[str, pygame.mixer.Sound] = {}
        self._sfx_clips: dict[str, pygame.mixer.Sound] = {}
        self._speech_channel: pygame.mixer.Channel | None = None
        self._sfx_channel: pygame.mixer.Channel | None = None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=256)
            pygame.mixer.set_num_channels(8)
            self._speech_channel = pygame.mixer.Channel(0)
            self._sfx_channel = pygame.mixer.Channel(1)

            self._sfx_clips = {
                "correct": self._tone(880.0, 0.14, 0.20),
                "retry": self._tone(340.0, 0.08, 0.12),
                "complete": self._tone(1040.0, 0.25, 0.22),
            }
            self._load_speech_clips()
        except (pygame.error, ValueError, OSError):
            self._speech_clips = {}
            self._sfx_clips = {}

    def _load_speech_clips(self) -> None:
        audio_dir = self._package_root / "assets" / "audio" / self._locale
        if not audio_dir.exists():
            return
        for wav_file in audio_dir.glob("*.wav"):
            try:
                sound = pygame.mixer.Sound(str(wav_file))
                self._speech_clips[wav_file.stem] = sound
            except (pygame.error, OSError):
                continue

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
                return

    def is_speech_busy(self) -> bool:
        if self._speech_channel is None:
            return False
        try:
            return self._speech_channel.get_busy()
        except pygame.error:
            return False

    def play_sfx(self, cue: str) -> None:
        sound = self._sfx_clips.get(cue)
        if sound is None or self._sfx_channel is None:
            return
        try:
            self._sfx_channel.play(sound)
        except pygame.error:
            return

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
