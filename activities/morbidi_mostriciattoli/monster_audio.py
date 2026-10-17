"""Sound for Fluffy Monsters: tiny prepared cues + Momo's approved voice.

Cues are synthesized once, after the first frame (``DeferredSoundBank``), to
match the active PCM16 mixer:
``tick`` (a drawer opens), ``boing`` (a part pops on), ``squish`` (a new body
or colour), ``giggle`` (the friend is tickled), ``rattle`` (surprise dice),
``chime`` (saved / shared), ``swish`` (a friend was deleted) and ``syllable.N``
(a bright two-note chirp per name syllable — not speech).

Momo, the host, speaks only owner-approved clips: shared character takes
(``shared_character_audio_path``: selected language -> English -> silence)
and two package lines (``assets/audio/<locale>/``: "a new friend!" queued
after the save cheer, "surprise!" for the dice when Momo is quiet); no speech
is generated here. Audio is fail-soft: without a mixer the bank is
silent and never raises.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Callable, Final
import wave

import pygame

from greia_platform.localization import (
    LocalizationError,
    activity_resources,
    shared_character_audio_path,
)
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

if __package__:
    from .monster_content import SYLLABLES
else:
    from monster_content import SYLLABLES

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
HOST: Final = "momo"
# cue -> preferred take (1-based) among the approved shared clips
HOST_LINES: Final[dict[str, tuple[str, int]]] = {
    "hello": ("ready.go", 3),  # "Here we go!" / "Si parte!"
    "saved": ("celebrate.success", 3),  # "Wonderful!" / "Che meraviglia!"
    "shared": ("praise.general", 2),  # "Great work!" / "Ottimo lavoro!"
    "nudge": ("encourage.progress", 1),  # "Keep going!" / "Continua così!"
}
# Owner-approved per-Activity lines (``assets/audio/<locale>/<cue>.wav``).
PACKAGE_LINES: Final[tuple[str, ...]] = ("new_friend", "surprise")
PACKAGE_ROOT: Final = Path(__file__).resolve().parent
MAX_VOICES: Final = 4


def _wav(samples: list[float], rate: int, channels: int) -> bytes:
    raw = mono_pcm16_bytes([int(max(-32000, min(32000, value))) for value in samples], channels)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(raw)
    return buffer.getvalue()


def _cue(samples: list[float], rate: int, channels: int) -> pygame.mixer.Sound:
    sound = pygame.mixer.Sound(io.BytesIO(_wav(samples, rate, channels)))
    sound.set_volume(0.5)
    return sound


def host_clip_path(line: str, locale: str, *, project_root: Path = PROJECT_ROOT) -> Path | None:
    """Momo's approved clip for ``line`` in ``locale`` (English fallback) or None."""

    if line in PACKAGE_LINES:
        try:
            return activity_resources(PACKAGE_ROOT, requested_locale=locale).audio_path(line)
        except LocalizationError:
            return None
    cue, take = HOST_LINES[line]
    try:
        first = shared_character_audio_path(project_root, HOST, cue, locale)
    except Exception:
        return None
    if first is None:
        return None
    preferred = first.with_name(first.name.replace("__01.wav", f"__{take:02d}.wav"))
    return preferred if preferred.is_file() else first


class MonsterAudio:
    """Bounded bank of prepared cues plus at most four cached host lines."""

    def __init__(self, *, locale: str = "en", project_root: Path = PROJECT_ROOT) -> None:
        self._sounds = DeferredSoundBank()
        self._voices: dict[str, pygame.mixer.Sound | None] = {}
        self._voice_channel: pygame.mixer.Channel | None = None
        self._locale = locale
        self._root = project_root
        self.played: list[str] = []
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            spec = current_pcm16_mixer_spec()
            if spec is None:
                return
            rate, channels = spec
            for name, recipe in self._recipes(rate).items():
                self._sounds.define(name, lambda recipe=recipe: _cue(recipe(), rate, channels))
            pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
            self._voice_channel = pygame.mixer.Channel(7)
        except Exception:  # noqa: BLE001 - audio must never break the Activity
            self._sounds.clear()
            self._voice_channel = None

    @staticmethod
    def _recipes(rate: int) -> dict[str, Callable[[], list[float]]]:
        """Name -> sample generator; nothing is computed until a cue is built."""

        def tone(seconds: float, voice) -> Callable[[], list[float]]:
            return lambda: [voice(i / rate) for i in range(int(rate * seconds))]

        def chirp(f1: float, f2: float):
            def voice(t: float) -> float:
                freq = f1 if t < 0.07 else f2
                return 8000 * math.sin(2 * math.pi * freq * t) * math.exp(-9 * (t % 0.07 if t < 0.07 else t - 0.07)) * min(1.0, t * 300)
            return voice

        cues = {
            "tick": tone(0.05, lambda t: 7000 * math.sin(2 * math.pi * 880 * t) * math.exp(-60 * t)),
            "boing": tone(
                0.26,
                lambda t: 10000 * math.sin(2 * math.pi * (220 + 260 * math.sin(math.pi * t / 0.26) * (1 + 0.3 * math.sin(2 * math.pi * 18 * t))) * t) * math.exp(-9 * t),
            ),
            "squish": tone(0.22, lambda t: 9000 * math.sin(2 * math.pi * (480 - 900 * t) * t) * math.sin(math.pi * t / 0.22)),
            "giggle": tone(
                0.48,
                lambda t: 7500 * math.sin(2 * math.pi * (620 + 140 * math.sin(2 * math.pi * 11 * t) + 260 * t) * t)
                * (0.55 + 0.45 * math.sin(2 * math.pi * 9 * t)) * math.exp(-3.5 * t),
            ),
            "rattle": tone(
                0.36,
                lambda t: 6000 * math.sin(2 * math.pi * (900 + 400 * ((int(t * 28) % 2))) * t) * (1 if int(t * 28) % 3 else 0.2) * math.exp(-4 * t),
            ),
            "chime": tone(
                0.42,
                lambda t: 9000
                * (math.sin(2 * math.pi * (784 if t < 0.13 else 1046.5) * t) * 0.8 + 0.2 * math.sin(2 * math.pi * 2093 * t))
                * math.exp(-6.5 * t),
            ),
            "swish": tone(0.22, lambda t: 6000 * math.sin(2 * math.pi * (620 - 1400 * t) * t) * math.sin(math.pi * t / 0.22)),
        }
        base = (523.3, 587.3, 659.3, 698.5, 784.0, 880.0, 987.8, 1046.5)
        for index, _ in enumerate(SYLLABLES):
            f = base[index % len(base)]
            cues[f"syllable.{index}"] = tone(0.2, chirp(f, f * 1.25))
        return cues

    def play(self, name: str) -> None:
        self.played.append(name)
        del self.played[:-24]
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def host_says(self, line: str) -> bool:
        """Play one of Momo's approved lines; False when silent."""

        self.played.append(f"voice.{line}")
        del self.played[:-24]
        if self._voice_channel is None:
            return False
        sound = self._voice(line)
        if sound is None:
            return False
        try:
            self._voice_channel.play(sound)
        except pygame.error:
            return False
        return True

    def host_then(self, line: str) -> bool:
        """Queue one of Momo's lines after the one playing (now when quiet)."""

        self.played.append(f"voice.{line}")
        del self.played[:-24]
        if self._voice_channel is None:
            return False
        sound = self._voice(line)
        if sound is None:
            return False
        try:
            if self._voice_channel.get_busy():
                self._voice_channel.queue(sound)
            else:
                self._voice_channel.play(sound)
        except pygame.error:
            return False
        return True

    def host_says_if_quiet(self, line: str) -> bool:
        """Momo's line only when no other line is playing (mashing stays calm)."""

        try:
            if self._voice_channel is not None and self._voice_channel.get_busy():
                return False
        except pygame.error:
            return False
        return self.host_says(line)

    def _voice(self, line: str) -> pygame.mixer.Sound | None:
        if line in self._voices:
            return self._voices[line]
        sound: pygame.mixer.Sound | None = None
        path = host_clip_path(line, self._locale, project_root=self._root)
        if path is not None:
            try:
                sound = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                sound = None
        if len(self._voices) >= MAX_VOICES:
            self._voices.pop(next(iter(self._voices)))
        self._voices[line] = sound
        return sound

    def stop(self) -> None:
        try:
            if self._voice_channel is not None:
                self._voice_channel.stop()
        except pygame.error:
            pass


__all__ = ["HOST", "HOST_LINES", "MonsterAudio", "PACKAGE_LINES", "host_clip_path"]
