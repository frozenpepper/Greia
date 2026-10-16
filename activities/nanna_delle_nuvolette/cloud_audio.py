"""Approved speech plus soft synthesized bedtime sounds for Cloud Bedtime.

Speech uses only recorded, approved clips (no generated audio): Momo's shared
character takes (``praise.general``, ``encourage.retry``,
``celebrate.success``), found through ``shared_character_audio_path``
(locale -> English fallback), played softly. There is no approved recording
of the bedtime wishes, numbers or colours yet, so the game is fully pictorial.

The small effects are synthesized once at start-up in the mixer's own format,
deliberately quiet and slow: a cotton rustle, a sleepy yawn, a music-box note
per cloud falling asleep, a soft "hm-hm" for a declined quilt, a twinkle, and
a slow falling arpeggio of those notes as the end-of-night lullaby. Every call fails
soft without a mixer.
"""

from __future__ import annotations

from collections import OrderedDict
import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HOST: Final = "momo"
MOMO_CUES: Final = ("praise.general", "encourage.retry", "celebrate.success")
SPEECH_VOLUME: Final = 0.7   # Momo whispers a little at bedtime
CLIP_CACHE_LIMIT: Final = 4
EFFECTS: Final = ("pick", "rustle", "yawn", "hush", "twinkle", "sleep_0", "sleep_1", "sleep_2")
# Music-box notes (Hz) for the three clouds falling asleep: C6, E6, G6.
SLEEP_NOTES: Final = (1046.5, 1318.5, 1568.0)
# The end-of-night lullaby reuses those three notes (no extra synthesis):
# a slow, original falling arpeggio, played twice. (seconds, effect name)
LULLABY: Final = (
    (0.0, "sleep_2"), (0.5, "sleep_1"), (1.0, "sleep_0"),
    (1.75, "sleep_2"), (2.25, "sleep_1"), (2.9, "sleep_0"),
)


class CloudAudio:
    """Own the quiet sound bank and Momo's speech for one bedtime visit."""

    def __init__(
        self,
        *,
        locale: str = "en",
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.locale = locale.split("-")[0].split("_")[0] or "en"
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._clips: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._takes: dict[str, list[Path]] = {}
        self._available = False
        self.last_speech: str | None = None
        self.last_effect: str | None = None
        self._find_takes()
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- speech -------------------------------------------------------------

    def momo(self, cue: str) -> bool:
        """Play one of Momo's approved shared takes (random variant), softly."""

        self.last_speech = cue
        takes = self._takes.get(cue)
        if not self._available or not takes:
            return False
        path = self._rng.choice(takes)
        sound = self._clip(f"momo:{path.name}", path)
        if sound is None:
            return False
        try:
            channel = pygame.mixer.Channel(SPEECH_CHANNEL)
            channel.set_volume(SPEECH_VOLUME)
            channel.play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

    def stop_speech(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

    def _clip(self, key: str, path: Path) -> pygame.mixer.Sound | None:
        if key in self._clips:
            self._clips.move_to_end(key)
            return self._clips[key]
        try:
            sound: pygame.mixer.Sound | None = pygame.mixer.Sound(str(path))
        except (pygame.error, OSError):
            sound = None
        self._clips[key] = sound
        while len(self._clips) > CLIP_CACHE_LIMIT:
            self._clips.popitem(last=False)
        return sound

    def _find_takes(self) -> None:
        for cue in MOMO_CUES:
            try:
                first = shared_character_audio_path(self._project_root, HOST, cue, self.locale)
            except Exception:
                first = None
            if first is None:
                continue
            # Sibling takes of the same cue in the same accepted folder.
            pattern = "__".join(first.name.split("__")[:3]) + "__*.wav"
            takes = sorted(first.parent.glob(pattern))[:3]
            if takes:
                self._takes[cue] = takes

    # -- effects ------------------------------------------------------------

    def play(self, name: str) -> None:
        self.last_effect = name
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

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds["pick"] = _bell(rate, channels, 880.0, 0.25, 2600)
        self._sounds["twinkle"] = _bell(rate, channels, 1760.0, 0.4, 1800)
        self._sounds["rustle"] = _rustle(rate, channels)
        self._sounds["yawn"] = _yawn(rate, channels)
        self._sounds["hush"] = _hush(rate, channels)
        for index, note in enumerate(SLEEP_NOTES):
            self._sounds[f"sleep_{index}"] = _bell(rate, channels, note, 0.9, 3200)


def _bell(rate: int, channels: int, frequency: float, duration: float, volume: int) -> pygame.mixer.Sound:
    """A soft music-box/celesta note: quick attack, long gentle decay."""

    buffer = bytearray()
    for index in range(int(rate * duration)):
        t = index / rate
        envelope = min(1.0, t / 0.008) * math.exp(-4.5 * t / duration)
        value = math.sin(2 * math.pi * frequency * t) + 0.3 * math.sin(2 * math.pi * frequency * 2 * t) * math.exp(-8 * t)
        append_mono_pcm16(buffer, int(value * envelope * volume), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _rustle(rate: int, channels: int) -> pygame.mixer.Sound:
    """A soft cotton swish (smoothed noise, slow swell)."""

    noise = random.Random(11)
    buffer = bytearray()
    smooth = 0.0
    duration = 0.5
    for index in range(int(rate * duration)):
        t = index / rate
        swell = math.sin(math.pi * t / duration) ** 2
        smooth += (noise.uniform(-1.0, 1.0) - smooth) * 0.18
        append_mono_pcm16(buffer, int(smooth * swell * 5200), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _yawn(rate: int, channels: int) -> pygame.mixer.Sound:
    """A gentle descending sigh with a soft vowel-like overtone."""

    buffer = bytearray()
    phase = 0.0
    duration = 0.95
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = 300.0 - 110.0 * (t / duration)
        phase += 2 * math.pi * frequency / rate
        envelope = math.sin(math.pi * t / duration) ** 1.5
        value = math.sin(phase) + 0.25 * math.sin(2 * phase)
        append_mono_pcm16(buffer, int(value * envelope * 3600), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


def _hush(rate: int, channels: int) -> pygame.mixer.Sound:
    """A soft two-note "hm-hm" for a declined quilt (never a buzzer)."""

    buffer = bytearray()
    notes = ((0.0, 392.0), (0.22, 349.23))
    duration = 0.55
    for index in range(int(rate * duration)):
        t = index / rate
        value = 0.0
        for start, frequency in notes:
            local = t - start
            if 0.0 <= local < 0.3:
                value += math.sin(2 * math.pi * frequency * local) * math.sin(math.pi * local / 0.3)
        append_mono_pcm16(buffer, int(value * 3000), channels)
    return pygame.mixer.Sound(buffer=bytes(buffer))


__all__ = ["CLIP_CACHE_LIMIT", "CloudAudio", "EFFECTS", "HOST", "LULLABY", "MOMO_CUES"]
