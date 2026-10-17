"""Audio and speech sequencing for L'Alfabeto di Leo.

Only existing recordings are played: this package's letter clips
(``letter_<X>`` — "A as Apple" / "A come Ape" — and ``ask_<X>`` — "Where is the
letter A?", plus the ``trace_letter`` invitation) through ``LocalizedResources.speech_paths`` (selected language →
base → English → silence), and Leo's owner-accepted shared character clips
(``shared_character_audio_path``). Nonverbal chimes are tiny tones built once,
after the first frame. Nothing here generates speech.
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
from greia_platform.pygame_audio import DeferredSoundBank

_SAMPLE_RATE: Final = 22_050
MAX_QUEUE_LEN: Final = 6
# A cue without a playable clip (silent build, missing file) still keeps its
# picture glowing this long, so the pictorial sequence stays readable.
SILENT_CUE_SECONDS: Final = 0.9

# Shared Leo clips (owner-accepted v0.2 character library).
LEO_CUES: Final[dict[str, str]] = {
    "leo.ready": "ready.go",
    "leo.retry": "encourage.retry",
    "leo.praise": "praise.general",
    "leo.progress": "encourage.progress",
    "leo.celebrate": "celebrate.success",
}

# Owner-approved package line spoken when the first tracing step of a round
# starts (``assets/audio/<locale>/trace_letter.wav``).
TRACE_PROMPT_CUE: Final = "trace_letter"
PROMPT_CUES: Final[frozenset[str]] = frozenset({TRACE_PROMPT_CUE})


def letter_cue(char: str) -> str:
    """Spoken letter name with its example word ("A as Apple")."""

    return f"letter_{char.upper()}"


def ask_cue(char: str) -> str:
    """Spoken find question ("Where is the letter A?")."""

    return f"ask_{char.upper()}"


class SpeechPlayer(Protocol):
    def play_speech(self, cue_id: str) -> float | None: ...
    def stop_speech(self) -> None: ...


@dataclass(frozen=True, slots=True)
class SpeechCue:
    """One queued clip; ``tag`` names what glows while it plays."""

    cue_id: str
    tag: str | None = None
    gap: float = 0.25


class SpeechQueue:
    """Bounded, clock-driven speech sequence that never overlaps clips.

    Timing follows each clip's own length (plus a small gap) rather than
    polling the mixer, so glows are deterministic and the sequence still
    advances when audio is unavailable.
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


class AlfabetoAudio:
    """Load approved speech clips and prepare the nonverbal chimes."""

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
        # Approved clips decode after the first frame (or on first use).
        self._speech = DeferredSoundBank()
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._speech_channel: pygame.mixer.Channel | None = None
        self._sfx_channel: pygame.mixer.Channel | None = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=256)
            pygame.mixer.set_num_channels(8)
            self._speech_channel = pygame.mixer.Channel(0)
            self._sfx_channel = pygame.mixer.Channel(1)
            # Synthesized after the first frame (DeferredSoundBank), not at launch.
            sfx = DeferredSoundBank()
            sfx.define("correct", lambda: self._tone(880.0, 0.14, 0.20))
            sfx.define("retry", lambda: self._tone(340.0, 0.08, 0.12))
            sfx.define("stroke", lambda: self._tone(660.0, 0.07, 0.14))
            sfx.define("bloom", lambda: self._tone(1040.0, 0.22, 0.20))
            self._sfx = sfx
            self._load_package_clips()
            self._load_leo_clips()
        except (pygame.error, ValueError, OSError):
            self._speech = {}
            self._sfx = {}

    def has_speech(self, cue_id: str) -> bool:
        return cue_id in self._speech

    def _load_package_clips(self) -> None:
        if self._resources is not None:
            # The shared resolver owns locale selection and English fallback.
            clips = self._resources.speech_paths()
        else:
            folder = self._package_root / "assets" / "audio" / self._locale
            clips = {wav.stem: wav for wav in sorted(folder.glob("*.wav"))} if folder.is_dir() else {}
        for stem, path in clips.items():
            if stem.startswith(("letter_", "ask_")) or stem in PROMPT_CUES:
                self._load(stem, path)

    def _load_leo_clips(self) -> None:
        for cue_id, shared in LEO_CUES.items():
            try:
                path = shared_character_audio_path(self._project_root, "leo", shared, self._locale)
            except Exception:
                path = None
            if path is not None:
                self._load(cue_id, path)

    def _load(self, cue_id: str, path: Path) -> None:
        try:
            self._speech.define(cue_id, lambda path=path: pygame.mixer.Sound(str(path)))
        except (pygame.error, OSError):
            return

    def play_speech(self, cue_id: str) -> float | None:
        """Play one clip; return its length in seconds (None when unavailable)."""

        sound = self._speech.get(cue_id)
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
        sound = self._sfx.get(cue)
        if sound is None or self._sfx_channel is None:
            return
        try:
            self._sfx_channel.play(sound)
        except pygame.error:
            return

    @staticmethod
    def _tone(frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        amplitude = max(0, min(32767, int(32767 * volume)))
        init = pygame.mixer.get_init()
        channels = init[2] if init is not None else 2
        rate = init[0] if init is not None else _SAMPLE_RATE
        samples = array("h")
        count = max(1, int(rate * duration))
        for i in range(count):
            # Short fade in/out avoids clicks on low-cost speakers.
            envelope = min(1.0, i / 220.0, (count - i) / 220.0)
            value = int(amplitude * envelope * math.sin(2.0 * math.pi * frequency * i / rate))
            samples.extend([value] * channels)
        return pygame.mixer.Sound(buffer=samples.tobytes())


__all__ = [
    "AlfabetoAudio",
    "LEO_CUES",
    "PROMPT_CUES",
    "SpeechCue",
    "SpeechQueue",
    "TRACE_PROMPT_CUE",
    "ask_cue",
    "letter_cue",
]
