"""Audio and speech sequencing for Festa delle Rime.

Only owner-approved recordings are played: the package's word/prompt clips
(through ``LocalizedResources.speech_paths``) and Leo's shared character clips
(``shared_character_audio_path``). Nonverbal feedback chimes are tiny tones
synthesised once at start-up. Nothing here generates speech.
"""

from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Final, Protocol

import pygame

from greia_platform.localization import LocalizedResources, shared_character_audio_path


_SAMPLE_RATE: Final = 22_050
MAX_QUEUE_LEN: Final = 8
# A cue without a playable clip (silent build, missing file) still keeps its
# picture glowing this long, so the pictorial sequence stays readable.
SILENT_CUE_SECONDS: Final = 0.7

# Shared Leo clips (owner-accepted v0.2 character library).
LEO_CUES: Final[dict[str, str]] = {
    "leo.ready": "ready.go",
    "leo.retry": "encourage.retry",
    "leo.celebrate": "celebrate.success",
}


class SpeechPlayer(Protocol):
    def play_speech(self, cue_id: str) -> float | None: ...
    def stop_speech(self) -> None: ...


@dataclass(frozen=True, slots=True)
class SpeechCue:
    """One queued clip; ``tag`` names the picture that glows while it plays."""

    cue_id: str
    tag: str | None = None
    gap: float = 0.25


class SpeechQueue:
    """Bounded, clock-driven speech sequence that never overlaps clips.

    Timing follows each clip's own length (plus a small gap) rather than
    polling the mixer, so the speaking-picture glow is deterministic and the
    sequence still advances when audio is unavailable.
    """

    def __init__(self, audio: SpeechPlayer, *, max_len: int = MAX_QUEUE_LEN) -> None:
        self._audio = audio
        self._queue: deque[SpeechCue] = deque()
        self._max_len = int(max_len)
        self._current: SpeechCue | None = None
        self._remaining = 0.0

    def enqueue(self, cue_id: str, *, tag: str | None = None, gap: float = 0.25) -> None:
        if len(self._queue) < self._max_len:
            self._queue.append(SpeechCue(cue_id, tag, max(0.0, float(gap))))

    def clear(self) -> None:
        self._queue.clear()
        self._current = None
        self._remaining = 0.0
        self._audio.stop_speech()

    @property
    def busy(self) -> bool:
        return self._current is not None or bool(self._queue)

    @property
    def current_tag(self) -> str | None:
        return self._current.tag if self._current is not None else None

    def update(self, dt: float) -> bool:
        """Advance by ``dt`` seconds; return True when the speaking tag changed."""

        before = self.current_tag
        if self._current is not None:
            self._remaining -= max(0.0, dt)
            if self._remaining <= 0.0:
                self._current = None
        if self._current is None and self._queue:
            cue = self._queue.popleft()
            length = self._audio.play_speech(cue.cue_id) or 0.0
            if length <= 0.0 and cue.tag is not None:
                length = SILENT_CUE_SECONDS
            self._current = cue
            self._remaining = length + cue.gap
        return self.current_tag != before


class RhymeAudio:
    """Load approved speech clips and prepare nonverbal feedback chimes."""

    def __init__(
        self,
        package_root: Path,
        locale: str = "it",
        resources: LocalizedResources | None = None,
        *,
        project_root: Path | None = None,
    ) -> None:
        self._resources = resources
        self._locale = locale
        self._package_root = package_root
        self._project_root = project_root if project_root is not None else package_root.resolve().parents[1]
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
            self._load_leo_clips()
        except (pygame.error, ValueError, OSError):
            self._speech_clips = {}
            self._sfx_clips = {}

    def has_speech(self, cue_id: str) -> bool:
        return cue_id in self._speech_clips

    def _load_speech_clips(self) -> None:
        if self._resources is not None:
            # The shared resolver owns locale-specific discovery and English
            # fallback. This Activity still owns decoding and speech channels.
            for stem, path in self._resources.speech_paths().items():
                self._load(stem, path)
            return
        audio_dir = self._package_root / "assets" / "audio" / self._locale
        if audio_dir.is_dir():
            for wav_file in sorted(audio_dir.glob("*.wav")):
                self._load(wav_file.stem, wav_file)

    def _load_leo_clips(self) -> None:
        for cue_id, shared_cue in LEO_CUES.items():
            try:
                path = shared_character_audio_path(self._project_root, "leo", shared_cue, self._locale)
            except Exception:
                path = None
            if path is not None:
                self._load(cue_id, path)

    def _load(self, cue_id: str, path: Path) -> None:
        try:
            self._speech_clips[cue_id] = pygame.mixer.Sound(str(path))
        except (pygame.error, OSError):
            return

    def play_speech(self, cue_id: str) -> float | None:
        """Play one clip; return its length in seconds (None when unavailable)."""

        sound = self._speech_clips.get(cue_id)
        if sound is None or self._speech_channel is None:
            return None
        try:
            self._speech_channel.play(sound)
            return float(sound.get_length())
        except pygame.error:
            return None

    def stop_speech(self) -> None:
        if self._speech_channel is not None:
            try:
                self._speech_channel.stop()
            except pygame.error:
                return

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
        channels = 2
        init = pygame.mixer.get_init()
        if init is not None:
            channels = init[2]
        samples = array("h")
        for i in range(count):
            # Short fade in/out avoids clicks on low-cost speakers.
            envelope = min(1.0, i / 220.0, (count - i) / 220.0)
            value = int(amplitude * envelope * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE))
            samples.extend([value] * channels)
        return pygame.mixer.Sound(buffer=samples.tobytes())
