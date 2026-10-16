"""Approved speech, the child's own voice and small synthesized effects.

* Leo's shared takes (``ready.go``, ``celebrate.success``,
  ``encourage.retry``, ``encourage.progress``, ``praise.general``) from the
  shared character library with the usual locale -> base -> English
  fallback. There are no story-specific lines yet: prompts stay pictorial
  (see the rework report's "voice lines requested").
* The child's recordings (WAV bytes from ``VoiceRecorder``) on their own
  channel, so the slideshow can follow real playback.
* Effects (pop, whoosh, chime, gentle boop, countdown pip, record start/stop,
  page turn, fanfare) are synthesized once, after the first frame.

Every call fails soft without a mixer. All output stops before the
microphone opens so Leo or an effect never ends up inside a recording.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import random
import wave
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, append_mono_pcm16, current_pcm16_mixer_spec

SPEECH_CHANNEL: Final = 0
VOICE_CHANNEL: Final = 1
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST_CUES: Final = ("ready.go", "celebrate.success", "encourage.retry", "encourage.progress", "praise.general")


class StoryAudio:
    """Own Leo's takes, the effect bank and playback of the child's voice."""

    def __init__(
        self,
        *,
        locale: str = "en",
        host: str = "leo",
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.locale = locale.split("-")[0]
        self._host = host
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._host_takes: dict[str, list[pygame.mixer.Sound]] = {}
        self._voice: pygame.mixer.Sound | None = None
        self._available = False
        self.last_cue: str | None = None
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
            self._build_sounds()
            self._load_host()
            self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    # -- Leo ----------------------------------------------------------------

    def host(self, cue: str) -> bool:
        """Play one of the host's approved shared takes (random variant)."""

        self.last_cue = cue
        takes = self._host_takes.get(cue)
        if not self._available or not takes:
            return False
        return self._play_on(SPEECH_CHANNEL, self._rng.choice(takes))

    # -- the child's voice ----------------------------------------------------

    def play_voice(self, wav: bytes) -> bool:
        """Play one recording; returns False when it cannot be played."""

        if not self._available or not wav:
            return False
        try:
            with wave.open(io.BytesIO(wav), "rb") as reader:
                if reader.getnframes() <= 0:
                    return False
            sound = pygame.mixer.Sound(io.BytesIO(wav))
        except (pygame.error, wave.Error, EOFError, OSError):
            return False
        self.stop_speech()
        self._voice = sound  # keep a reference while it plays
        return self._play_on(VOICE_CHANNEL, sound)

    def voice_busy(self) -> bool:
        return self._busy(VOICE_CHANNEL)

    def speech_busy(self) -> bool:
        return self._busy(SPEECH_CHANNEL)

    def stop_voice(self) -> None:
        self._stop(VOICE_CHANNEL)
        self._voice = None

    def stop_speech(self) -> None:
        self._stop(SPEECH_CHANNEL)

    def stop_all(self) -> None:
        """Silence everything (before the microphone opens, and on exit)."""

        if not self._available:
            return
        try:
            pygame.mixer.stop()
        except (pygame.error, RuntimeError):
            pass
        self._voice = None

    # -- effects ------------------------------------------------------------

    def play(self, name: str) -> None:
        if not self._available:
            return
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            for index in range(FIRST_SFX_CHANNEL, LAST_SFX_CHANNEL + 1):
                channel = pygame.mixer.Channel(index)
                if not channel.get_busy():
                    channel.play(sound)
                    return
            pygame.mixer.Channel(FIRST_SFX_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return

    # -- internals ------------------------------------------------------------

    def _play_on(self, index: int, sound: pygame.mixer.Sound) -> bool:
        try:
            pygame.mixer.Channel(index).play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

    def _busy(self, index: int) -> bool:
        if not self._available:
            return False
        try:
            return bool(pygame.mixer.Channel(index).get_busy())
        except (pygame.error, RuntimeError):
            return False

    def _stop(self, index: int) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(index).stop()
        except (pygame.error, RuntimeError):
            return

    def _load_host(self) -> None:
        for cue in HOST_CUES:
            first = shared_character_audio_path(self._project_root, self._host, cue, self.locale)
            if first is None:
                continue
            # Sibling takes of the same family in the same accepted folder.
            prefix = first.name.split("__")
            pattern = "__".join(prefix[:3]) + "__*.wav"
            takes: list[pygame.mixer.Sound] = []
            for path in sorted(first.parent.glob(pattern))[:3]:
                try:
                    takes.append(pygame.mixer.Sound(str(path)))
                except (pygame.error, OSError):
                    continue
            if takes:
                self._host_takes[cue] = takes

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("pop", lambda: _sweep(rate, channels, 0.12, 520.0, 900.0, 7200))
        self._sounds.define("unpop", lambda: _sweep(rate, channels, 0.12, 760.0, 460.0, 5600))
        self._sounds.define("whoosh", lambda: _sweep(rate, channels, 0.24, 900.0, 1500.0, 3600))
        self._sounds.define("chime", lambda: _chord(rate, channels, (659.25, 783.99, 1046.5), 0.5))
        self._sounds.define("boop", lambda: _sweep(rate, channels, 0.22, 420.0, 330.0, 6000))
        self._sounds.define("pip", lambda: _sweep(rate, channels, 0.08, 880.0, 880.0, 6000))
        self._sounds.define("rec_on", lambda: _chord(rate, channels, (880.0, 1318.5), 0.28))
        self._sounds.define("rec_off", lambda: _sweep(rate, channels, 0.16, 990.0, 660.0, 6400))
        self._sounds.define("page", lambda: _sweep(rate, channels, 0.18, 1200.0, 700.0, 2800))
        self._sounds.define("fanfare", lambda: _fanfare(rate, channels))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    buffer = bytearray()
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = start + (end - start) * (t / duration)
        phase += 2.0 * math.pi * frequency / rate
        envelope = math.sin(math.pi * t / duration)
        append_mono_pcm16(buffer, int(math.sin(phase) * envelope * volume), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _chord(rate: int, channels: int, notes: tuple[float, ...], duration: float) -> pygame.mixer.Sound:
    buffer = bytearray()
    stagger = 0.06
    for index in range(int(rate * duration)):
        t = index / rate
        value = 0.0
        for order, frequency in enumerate(notes):
            local = t - order * stagger
            if local >= 0:
                value += math.sin(2.0 * math.pi * frequency * local) * math.exp(-5.0 * local / duration)
        append_mono_pcm16(buffer, int(value * 7000 / max(1, len(notes)) * 1.6), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _fanfare(rate: int, channels: int) -> pygame.mixer.Sound:
    notes = ((0.0, 0.15, 523.25), (0.12, 0.15, 659.25), (0.24, 0.15, 783.99), (0.36, 0.45, 1046.5))
    buffer = bytearray()
    for index in range(int(rate * 0.85)):
        t = index / rate
        value = 0.0
        for start, length, frequency in notes:
            if start <= t < start + length:
                local = t - start
                value += math.sin(2.0 * math.pi * frequency * local) * math.exp(-3.5 * local / length)
        append_mono_pcm16(buffer, int(value * 10000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


__all__ = ["HOST_CUES", "StoryAudio"]
