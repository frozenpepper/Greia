"""Approved speech plus small synthesized effects for Woodland Hide & Seek.

Speech uses only recorded, approved clips:

* friend names from the platform's shared vocabulary audio bank
  (``shared_vocab_audio_path``; the package carries no noun clips) with the
  usual locale -> base -> English fallback; a name without a recording stays
  silent and the request remains pictorial;
* Lilli's shared takes (``ready.go``, ``celebrate.success``,
  ``encourage.retry``, ``encourage.progress``, ``praise.general``);
* Lilli's owner-approved package lines (``assets/audio/<locale>/``):
  "where is the...?" before the wanted friend's name, and the place phrase
  ("behind the bush", "under the leaves", "in the pond", ...) queued after a
  found friend's name.

Effects (leaf rustle, found chime, hop pop, "not me" boing, hide whoosh,
fanfare) are synthesized once, after the first frame. Every call fails soft without a
mixer; name clips are decoded at most once each (bounded cache).
"""

from __future__ import annotations

from collections import OrderedDict
import math
from pathlib import Path
import random
from typing import Final, Iterable

import pygame

from greia_platform.localization import (
    LocalizationError,
    activity_resources,
    shared_character_audio_path,
    shared_vocab_audio_path,
)
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    chord_sound,
    current_pcm16_mixer_spec,
    fanfare_sound,
    mono_pcm16_bytes,
    sweep_sound,
)

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
# Hiding-place prop kind -> owner-approved place phrase (package cue id).
PLACE_CUES: Final[dict[str, str]] = {
    "bush": "place_bush",
    "bush_autumn": "place_bush",
    "bush_snow": "place_bush",
    "rock": "place_rock",
    "log": "place_log",
    "mushroom": "place_mushroom",
    "pumpkin": "place_pumpkin",
    "leaves": "place_leaves",
    "snow": "place_snow",
    "pond": "place_pond",
}
WHERE_IS_CUE: Final = "where_is"
PACKAGE_CUES: Final[tuple[str, ...]] = (*dict.fromkeys(PLACE_CUES.values()), WHERE_IS_CUE)
HOST: Final = "lilli"
LILLI_CUES: Final = ("ready.go", "celebrate.success", "encourage.retry", "encourage.progress", "praise.general")
NAME_CACHE_LIMIT: Final = 12
EFFECTS: Final = ("rustle", "found", "pop", "boing", "hide", "fanfare")


class WoodlandAudio:
    """Own the sound bank and speech for one Hide & Seek visit."""

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
        self._sounds = DeferredSoundBank()
        self._lilli: dict[str, list[pygame.mixer.Sound]] = {}
        self._names: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._name_paths: dict[str, bool] = {}
        self._lines: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        self.last_speech: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._load_lilli()
                self._load_lines()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- speech -------------------------------------------------------------

    def has_name(self, friend_id: str) -> bool:
        """True when an approved recording of the friend's name exists."""

        known = self._name_paths.get(friend_id)
        if known is None:
            known = self._name_path(friend_id) is not None
            self._name_paths[friend_id] = known
        return known

    def prepare_names(self, friend_ids: Iterable[str]) -> None:
        if not self._available:
            return
        for friend_id in friend_ids:
            if friend_id in self._names:
                self._names.move_to_end(friend_id)
                continue
            self._names[friend_id] = self._load_name(friend_id)
            while len(self._names) > NAME_CACHE_LIMIT:
                self._names.popitem(last=False)

    def say_name(self, friend_id: str) -> bool:
        """Speak the friend's name; returns False (silent) without a recording."""

        self.last_speech = f"animal.{friend_id}"
        if not self._available:
            return False
        if friend_id not in self._names:
            self.prepare_names((friend_id,))
        return self._speak(self._names.get(friend_id))

    def ask_where(self, friend_id: str) -> bool:
        """"Where is the...?" then the friend's name (just the name without it)."""

        if not self._available:
            self.last_speech = f"animal.{friend_id}"
            return False
        where = self._lines.get(WHERE_IS_CUE)
        if where is None or not self._speak(where):
            return self.say_name(friend_id)
        if friend_id not in self._names:
            self.prepare_names((friend_id,))
        self.last_speech = f"animal.{friend_id}"
        return self._queue(self._names.get(friend_id))

    def say_place(self, prop_kind: str) -> bool:
        """Queue the found friend's place phrase after the line playing."""

        cue = PLACE_CUES.get(prop_kind)
        if cue is None:
            return False
        self.last_speech = cue
        return self._available and self._queue(self._lines.get(cue))

    def lilli(self, cue: str) -> bool:
        """Play one of Lilli's approved shared takes (random variant)."""

        self.last_speech = cue
        takes = self._lilli.get(cue)
        if not self._available or not takes:
            return False
        return self._speak(self._rng.choice(takes))

    def stop_speech(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).stop()
        except (pygame.error, RuntimeError):
            return

    def _queue(self, sound: pygame.mixer.Sound | None) -> bool:
        if sound is None:
            return False
        try:
            channel = pygame.mixer.Channel(SPEECH_CHANNEL)
            if channel.get_busy():
                channel.queue(sound)
            else:
                channel.play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

    def _load_lines(self) -> None:
        try:
            resources = activity_resources(PACKAGE_ROOT, requested_locale=self.locale)
        except LocalizationError:
            return
        for cue in PACKAGE_CUES:
            path = resources.audio_path(cue)
            if path is None:
                continue
            try:
                self._lines[cue] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue

    def _speak(self, sound: pygame.mixer.Sound | None) -> bool:
        if sound is None:
            return False
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

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

    # -- loading ------------------------------------------------------------

    def _name_path(self, friend_id: str) -> Path | None:
        try:
            return shared_vocab_audio_path(self._project_root, friend_id, self.locale)
        except Exception:
            return None

    def _load_name(self, friend_id: str) -> pygame.mixer.Sound | None:
        path = self._name_path(friend_id)
        if path is None:
            return None
        try:
            return pygame.mixer.Sound(str(path))
        except (pygame.error, OSError):
            return None

    def _load_lilli(self) -> None:
        for cue in LILLI_CUES:
            try:
                first = shared_character_audio_path(self._project_root, HOST, cue, self.locale)
            except Exception:
                first = None
            if first is None:
                continue
            # Sibling takes of the same family in the same accepted folder.
            pattern = "__".join(first.name.split("__")[:3]) + "__*.wav"
            takes: list[pygame.mixer.Sound] = []
            for path in sorted(first.parent.glob(pattern))[:3]:
                try:
                    takes.append(pygame.mixer.Sound(str(path)))
                except (pygame.error, OSError):
                    continue
            if takes:
                self._lilli[cue] = takes

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("rustle", lambda: _rustle(rate, channels))
        self._sounds.define("found", lambda: chord_sound(rate, channels, (659.25, 783.99, 1046.5), 0.46))
        self._sounds.define("pop", lambda: sweep_sound(rate, channels, 0.14, 520.0, 980.0, 7200))
        self._sounds.define("boing", lambda: _boing(rate, channels))
        self._sounds.define("hide", lambda: sweep_sound(rate, channels, 0.24, 1100.0, 600.0, 3200))
        self._sounds.define("fanfare", lambda: fanfare_sound(rate, channels))


def _rustle(rate: int, channels: int) -> pygame.mixer.Sound:
    """Two soft bursts of filtered noise, like leaves being pushed aside."""

    noise = random.Random(7)
    samples: list[float] = []
    duration = 0.32
    smooth = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        burst = math.exp(-((t - 0.07) / 0.045) ** 2) + 0.7 * math.exp(-((t - 0.2) / 0.05) ** 2)
        smooth += (noise.uniform(-1.0, 1.0) - smooth) * 0.35  # gentle low-pass
        samples.append(int(smooth * burst * 9000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


def _boing(rate: int, channels: int) -> pygame.mixer.Sound:
    """A soft wobbling 'not me' boing (never a buzzer)."""

    samples: list[float] = []
    duration = 0.36
    phase = 0.0
    for index in range(int(rate * duration)):
        t = index / rate
        frequency = 300.0 + 90.0 * math.sin(2.0 * math.pi * 9.0 * t) * math.exp(-4.0 * t)
        phase += 2.0 * math.pi * frequency / rate
        envelope = math.exp(-6.0 * t) * min(1.0, t / 0.01)
        samples.append(int(math.sin(phase) * envelope * 6500))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


__all__ = ["EFFECTS", "HOST", "LILLI_CUES", "PACKAGE_CUES", "PLACE_CUES", "WoodlandAudio"]
