"""Audio and speech sequencing for Leo's Syllable Train.

Only owner-approved recordings are spoken: this package's syllable / vowel /
word / instruction clips (resolved through ``LocalizedResources.audio_path``,
which owns the selected-language → English fallback) and Leo's shared
character clips (``shared_character_audio_path``). Nonverbal sounds — the clap
drum, the train whistle and feedback chimes — are tiny tones synthesised once
at start-up. Nothing here generates speech.

Clips are decoded lazily on first use into a bounded LRU cache (a round touches
about a dozen clips), so start-up never decodes the whole syllabary.
"""

from __future__ import annotations

from array import array
from collections import OrderedDict, deque
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Final, Protocol

import pygame

from greia_platform.localization import LocalizedResources, shared_character_audio_path


_SAMPLE_RATE: Final = 22_050
MAX_QUEUE_LEN: Final = 10
MAX_CLIPS: Final = 40
SFX_PREFIX: Final = "sfx:"
# A cue without a playable clip (silent build, missing file) still keeps its
# picture glowing this long, so the pictorial sequence stays readable.
SILENT_CUE_SECONDS: Final = 0.6
SFX_SECONDS: Final = {"drum": 0.32, "whistle": 0.55}

# Shared Leo clips (owner-accepted v0.2 character library).
LEO_CUES: Final[dict[str, str]] = {
    "leo.ready": "ready.go",
    "leo.retry": "encourage.retry",
    "leo.praise": "praise.general",
    "leo.progress": "encourage.progress",
    "leo.celebrate": "celebrate.success",
}


def recorded_clip_checker(package_root: Path, locale: str):
    """Strict per-language check: offer a syllable only if *this* language recorded it.

    Speech playback may fall back to English (owner policy), but lesson
    *content* must never be built from another language's recordings.
    """

    folder = package_root / "assets" / "audio" / locale.replace("_", "-").split("-", 1)[0].lower()

    def exists(cue: str) -> bool:
        return (folder / f"{cue}.wav").is_file()

    return exists


class SpeechPlayer(Protocol):
    def play_speech(self, cue_id: str) -> float | None: ...
    def stop_speech(self) -> None: ...


@dataclass(frozen=True, slots=True)
class SpeechCue:
    """One queued clip; ``tag`` names the thing that glows while it plays."""

    cue_id: str
    tag: str | None = None
    gap: float = 0.25


class SpeechQueue:
    """Bounded, clock-driven speech sequence that never overlaps clips.

    Timing follows each clip's own length (plus a small gap) rather than
    polling the mixer, so glows are deterministic and the sequence still
    advances when audio is unavailable. ``sfx:<name>`` cues play a nonverbal
    sound in sequence (the drum beats of a demonstration).
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

    def pause(self, seconds: float) -> None:
        """Queue a silent beat (lets speech wait for an animation to land)."""

        if len(self._queue) < self._max_len:
            self._queue.append(SpeechCue("", None, max(0.0, float(seconds))))

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
        """Advance by ``dt`` seconds; return True when the glowing tag changed."""

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


class SillabeAudio:
    """Resolve approved clips lazily and own the synthesised nonverbal sounds."""

    def __init__(
        self,
        package_root: Path,
        locale: str = "it",
        resources: LocalizedResources | None = None,
        *,
        project_root: Path | None = None,
        max_clips: int = MAX_CLIPS,
    ) -> None:
        self._resources = resources
        self._locale = locale
        self._package_root = package_root
        self._project_root = project_root if project_root is not None else package_root.resolve().parents[1]
        self._clips: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._max_clips = int(max_clips)
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._speech_channel: pygame.mixer.Channel | None = None
        self._sfx_channel: pygame.mixer.Channel | None = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=256)
            pygame.mixer.set_num_channels(8)
            self._speech_channel = pygame.mixer.Channel(0)
            self._sfx_channel = pygame.mixer.Channel(1)
            self._sfx = {
                "drum": self._drum(),
                "whistle": self._whistle(),
                "correct": self._tone(880.0, 0.14, 0.20),
                "retry": self._tone(340.0, 0.08, 0.12),
                "complete": self._tone(1040.0, 0.25, 0.22),
            }
        except (pygame.error, ValueError, OSError):
            self._sfx = {}
            self._speech_channel = None

    # -- lookup ---------------------------------------------------------------------
    def clip_path(self, cue_id: str) -> Path | None:
        """Approved file for one package or Leo cue (None when not recorded)."""

        if cue_id in LEO_CUES:
            try:
                return shared_character_audio_path(self._project_root, "leo", LEO_CUES[cue_id], self._locale)
            except Exception:
                return None
        if not cue_id or "/" in cue_id or "\\" in cue_id or cue_id.startswith("."):
            return None
        if self._resources is not None:
            try:
                return self._resources.audio_path(cue_id, filename=f"{cue_id}.wav")
            except Exception:
                return None
        for language in (self._locale, "en"):
            path = self._package_root / "assets" / "audio" / language / f"{cue_id}.wav"
            if path.is_file():
                return path
        return None

    def has_clip(self, cue_id: str) -> bool:
        path = self.clip_path(cue_id)
        return path is not None and path.is_file()

    def _sound(self, cue_id: str) -> pygame.mixer.Sound | None:
        if cue_id in self._clips:
            self._clips.move_to_end(cue_id)
            return self._clips[cue_id]
        sound = None
        path = self.clip_path(cue_id)
        if path is not None and self._speech_channel is not None:
            try:
                sound = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                sound = None
        self._clips[cue_id] = sound
        while len(self._clips) > self._max_clips:
            self._clips.popitem(last=False)
        return sound

    # -- playback -------------------------------------------------------------------
    def play_speech(self, cue_id: str) -> float | None:
        """Play one clip (or ``sfx:`` sound); return its length in seconds."""

        if not cue_id:
            return None
        if cue_id.startswith(SFX_PREFIX):
            name = cue_id[len(SFX_PREFIX):]
            self.play_sfx(name)
            return SFX_SECONDS.get(name, 0.3)
        sound = self._sound(cue_id)
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

    def clear(self) -> None:
        self._clips.clear()

    # -- synthesis (once) ------------------------------------------------------------
    @staticmethod
    def _channels() -> int:
        init = pygame.mixer.get_init()
        return init[2] if init is not None else 2

    @classmethod
    def _render(cls, values: list[float], volume: float) -> pygame.mixer.Sound:
        channels = cls._channels()
        amplitude = max(0, min(32767, int(32767 * volume)))
        samples = array("h")
        for value in values:
            samples.extend([int(amplitude * max(-1.0, min(1.0, value)))] * channels)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    @classmethod
    def _tone(cls, frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        count = max(1, int(_SAMPLE_RATE * duration))
        values = [
            # Short fade in/out avoids clicks on low-cost speakers.
            min(1.0, i / 220.0, (count - i) / 220.0) * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE)
            for i in range(count)
        ]
        return cls._render(values, volume)

    @classmethod
    def _drum(cls) -> pygame.mixer.Sound:
        """A soft tom thump: falling pitch with a quick exponential decay."""

        count = int(_SAMPLE_RATE * 0.22)
        values = []
        phase = 0.0
        for i in range(count):
            t = i / _SAMPLE_RATE
            frequency = 70.0 + 120.0 * math.exp(-t * 28.0)
            phase += 2.0 * math.pi * frequency / _SAMPLE_RATE
            values.append(min(1.0, i / 40.0) * math.exp(-t * 16.0) * math.sin(phase))
        return cls._render(values, 0.55)

    @classmethod
    def _whistle(cls) -> pygame.mixer.Sound:
        """Two-note toy-train toot."""

        count = int(_SAMPLE_RATE * 0.5)
        values = []
        for i in range(count):
            t = i / _SAMPLE_RATE
            frequency = 660.0 if t < 0.22 else 830.0
            envelope = min(1.0, i / 300.0, (count - i) / 600.0)
            wave = math.sin(2 * math.pi * frequency * t) + 0.35 * math.sin(2 * math.pi * frequency * 1.5 * t)
            values.append(envelope * wave * 0.7)
        return cls._render(values, 0.22)


__all__ = ["LEO_CUES", "SFX_PREFIX", "SillabeAudio", "SpeechCue", "SpeechQueue", "recorded_clip_checker"]
