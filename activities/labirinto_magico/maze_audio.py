"""Approved speech plus small synthesized garden sounds for Il Labirinto Magico.

Speech uses only Tito's owner-accepted shared character takes
(``assets/audio/characters/shared/v0.2/tito``) through
``shared_character_audio_path`` (selected language -> English -> silence):
"ready, go" when a maze starts, praise when Tito reaches his tent, the big
cheer at the end of a visit, "keep going" as the first idle nudge and "let's
try again" when the tent or a door is still closed. Sound effects are generated once, after the first frame; every call fails soft without
a mixer.

Tito's owner-approved maze lines (``assets/audio/<locale>/``) are wired too:
"help Tito find the way to his tent!" after the visit's first "ready, go",
"you found a star!" for a star (never over another line), "find all the stars
first!" at a closed tent and "find the key to open the door!" at a locked
door.
"""

from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import (
    LocalizationError,
    activity_resources,
    shared_character_audio_path,
)
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    chime_run_sound,
    current_pcm16_mixer_spec,
    mono_pcm16_bytes,
    sweep_sound,
)

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 5
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
# Owner-approved per-Activity lines (``assets/audio/<locale>/<cue>.wav``).
PACKAGE_CUES: Final[tuple[str, ...]] = (
    "help_tito_tent",
    "found_star",
    "find_all_stars",
    "find_key",
)
SPEAKER: Final = "tito"
# Activity cue -> Tito's shared take family.
SHARED_CUES: Final[dict[str, str]] = {
    "start": "ready.go",
    "solved": "praise.general",
    "complete": "celebrate.success",
    "nudge": "encourage.progress",
    "retry": "encourage.retry",
}


class LabyrinthAudio:
    """Own the speech/sound bank for one Activity run."""

    def __init__(
        self,
        locale: str = "en",
        *,
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.locale = (locale or "en").split("-")[0]
        self._project_root = project_root
        self._rng = rng if rng is not None else random.Random()
        self._sounds = DeferredSoundBank()
        self._speech: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        self.last_speech: str | None = None
        self.last_sound: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._load_speech()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    def has_speech(self, cue: str) -> bool:
        return cue in self._speech

    def say(self, cue: str) -> None:
        """Speak one approved cue now (silent when the take is missing)."""

        self.last_speech = cue
        sound = self._speech.get(cue)
        if not self._available or sound is None:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return

    def speaking(self) -> bool:
        if not self._available:
            return False
        try:
            return bool(pygame.mixer.Channel(SPEECH_CHANNEL).get_busy())
        except (pygame.error, RuntimeError):
            return False

    def say_if_quiet(self, cue: str) -> None:
        """Speak a non-essential line only when no other line is playing."""

        if not self.speaking():
            self.say(cue)

    def then(self, cue: str) -> None:
        """Queue one line after the one playing (now when quiet), never stacked.

        Uses the speech channel's own one-slot queue: no polling, and a newer
        queued line replaces an older one.
        """

        self.last_speech = cue
        sound = self._speech.get(cue)
        if not self._available or sound is None:
            return
        try:
            channel = pygame.mixer.Channel(SPEECH_CHANNEL)
            if channel.get_busy():
                channel.queue(sound)
            else:
                channel.play(sound)
        except (pygame.error, RuntimeError):
            return

    def play(self, name: str) -> None:
        self.last_sound = name
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

    def _load_speech(self) -> None:
        for cue, family in SHARED_CUES.items():
            path = shared_character_audio_path(self._project_root, SPEAKER, family, self.locale)
            if path is None:
                continue
            try:
                self._speech[cue] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue
        try:
            resources = activity_resources(PACKAGE_ROOT, requested_locale=self.locale)
        except LocalizationError:
            return
        for cue in PACKAGE_CUES:
            path = resources.audio_path(cue)
            if path is None:
                continue
            try:
                self._speech[cue] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("step", lambda: sweep_sound(rate, channels, 0.09, 380.0, 300.0, 4200))
        self._sounds.define("bump", lambda: _thud(rate, channels))
        self._sounds.define("star", lambda: chime_run_sound(rate, channels, (1046.5, 1318.5, 1568.0)))
        self._sounds.define("key", lambda: chime_run_sound(rate, channels, (1568.0, 2093.0, 1568.0, 2093.0), step=0.06, volume=7000))
        self._sounds.define("door", lambda: sweep_sound(rate, channels, 0.32, 240.0, 180.0, 6500))
        self._sounds.define("locked", lambda: sweep_sound(rate, channels, 0.22, 420.0, 330.0, 6500))
        self._sounds.define("hint", lambda: chime_run_sound(rate, channels, (1318.5, 1760.0), step=0.09, volume=6000))
        self._sounds.define("tent", lambda: chime_run_sound(rate, channels, (523.25, 659.25, 783.99, 1046.5), step=0.12))
        self._sounds.define("fanfare", lambda: chime_run_sound(rate, channels, (523.25, 659.25, 783.99, 1046.5, 1318.5), step=0.14, volume=10000))


def _thud(rate: int, channels: int) -> pygame.mixer.Sound:
    """Soft leafy bump: low sine plus a little rustle."""

    noise = random.Random(7)
    samples: list[float] = []
    for index in range(int(rate * 0.14)):
        t = index / rate
        envelope = math.exp(-28.0 * t)
        value = 0.75 * math.sin(2.0 * math.pi * 150.0 * t) + 0.25 * noise.uniform(-1.0, 1.0)
        samples.append(int(value * envelope * 7000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


# Back-compat alias for older imports.
MazeAudio = LabyrinthAudio

__all__ = ["LabyrinthAudio", "MazeAudio", "PACKAGE_CUES", "SHARED_CUES"]
