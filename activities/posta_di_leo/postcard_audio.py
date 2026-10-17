"""Sound for Leo's Post: tiny prepared cues + the friends' approved voices.

Cues are synthesized once, after the first frame to match the active PCM16 mixer:
``tick`` (a choice), ``pop`` (a sticker lands), ``flip`` (the card turns),
``whoosh`` (the postcard flies), ``drop`` (it lands in the mailbox), ``chime``
(shared to My Creations) and ``swish`` (a card was deleted).

Friend reactions use only owner-approved shared character clips
(``shared_character_audio_path``: selected language -> English -> silence);
Leo's three owner-approved package lines (``assets/audio/<locale>/``: "who
is it for?", "pick a picture!", "off it goes!") play on the same voice
channel, never over a friend's reaction. No speech is generated here. Audio is fail-soft: without a mixer the bank is
silent and never raises.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import wave
from typing import Callable

import pygame

from greia_platform.localization import (
    LocalizationError,
    activity_resources,
    shared_character_audio_path,
)
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

if __package__:
    from .postcard_content import FRIEND_REACTION_CUE, FRIEND_REACTION_VARIANTS
else:
    from postcard_content import FRIEND_REACTION_CUE, FRIEND_REACTION_VARIANTS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parent
# Leo's owner-approved per-Activity lines (``assets/audio/<locale>/<cue>.wav``).
LEO_LINES = ("who_is_it_for", "pick_picture", "off_it_goes")
MAX_VOICES = 6


def _wav(samples: list[float], rate: int, channels: int) -> bytes:
    raw = mono_pcm16_bytes(samples, channels)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(raw)
    return buffer.getvalue()


def _cue(samples: list[float], rate: int, channels: int) -> pygame.mixer.Sound:
    sound = pygame.mixer.Sound(io.BytesIO(_wav(samples, rate, channels)))
    sound.set_volume(0.55)
    return sound


def reaction_clip_path(friend_id: str, locale: str, *, project_root: Path = PROJECT_ROOT) -> Path | None:
    """The friend's approved "Wonderful!"-style clip for ``locale`` (or None)."""

    try:
        first = shared_character_audio_path(project_root, friend_id, FRIEND_REACTION_CUE, locale)
    except Exception:
        return None
    if first is None:
        return None
    # The shared resolver returns take 01; prefer the takes that fit receiving
    # a postcard ("Wonderful!", "Hooray!") when they exist in the same folder.
    for variant in FRIEND_REACTION_VARIANTS:
        candidate = first.with_name(first.name.replace("__01.wav", f"__{variant:02d}.wav"))
        if candidate.is_file():
            return candidate
    return first


class PostcardAudio:
    """Bounded bank of prepared cues plus at most six cached friend voices."""

    def __init__(self, *, locale: str = "en", project_root: Path = PROJECT_ROOT) -> None:
        self._sounds = DeferredSoundBank()
        self._voices: dict[str, pygame.mixer.Sound | None] = {}
        self._lines: dict[str, pygame.mixer.Sound | None] = {}
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

        return {
            "tick": tone(0.05, lambda t: 7000 * math.sin(2 * math.pi * 880 * t) * math.exp(-60 * t)),
            "pop": tone(0.12, lambda t: 11000 * math.sin(2 * math.pi * (340 + 900 * t) * t) * math.exp(-28 * t)),
            "flip": tone(0.14, lambda t: 5000 * math.sin(2 * math.pi * (300 + 1600 * t) * t) * math.sin(math.pi * t / 0.14)),
            "whoosh": tone(
                0.42,
                lambda t: 5200 * math.sin(2 * math.pi * (260 + 900 * t) * t) * math.sin(math.pi * t / 0.42),
            ),
            "drop": tone(0.2, lambda t: 9000 * math.sin(2 * math.pi * (520 - 600 * t) * t) * math.exp(-14 * t)),
            "chime": tone(
                0.38,
                lambda t: 9000
                * (math.sin(2 * math.pi * (784 if t < 0.12 else 1046.5) * t) * 0.8 + 0.2 * math.sin(2 * math.pi * 2093 * t))
                * math.exp(-7 * t),
            ),
            "swish": tone(0.22, lambda t: 6000 * math.sin(2 * math.pi * (620 - 1400 * t) * t) * math.sin(math.pi * t / 0.22)),
        }

    def play(self, name: str) -> None:
        self.played.append(name)
        del self.played[:-16]
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def friend_reacts(self, friend_id: str) -> bool:
        """Play the friend's approved reaction clip; False when silent."""

        self.played.append(f"voice.{friend_id}")
        del self.played[:-16]
        if self._voice_channel is None:
            return False
        sound = self._voice(friend_id)
        if sound is None:
            return False
        try:
            self._voice_channel.play(sound)
        except pygame.error:
            return False
        return True

    def leo_says(self, cue: str) -> bool:
        """Play one of Leo's package lines unless a voice is still playing."""

        self.played.append(f"line.{cue}")
        del self.played[:-16]
        if self._voice_channel is None or cue not in LEO_LINES:
            return False
        try:
            if self._voice_channel.get_busy():
                return False
        except pygame.error:
            return False
        if cue not in self._lines:
            sound: pygame.mixer.Sound | None = None
            try:
                path = activity_resources(PACKAGE_ROOT, requested_locale=self._locale).audio_path(cue)
                sound = pygame.mixer.Sound(str(path)) if path is not None else None
            except (LocalizationError, pygame.error, OSError):
                sound = None
            self._lines[cue] = sound  # bounded: three package lines at most
        sound = self._lines[cue]
        if sound is None:
            return False
        try:
            self._voice_channel.play(sound)
        except pygame.error:
            return False
        return True

    def _voice(self, friend_id: str) -> pygame.mixer.Sound | None:
        if friend_id in self._voices:
            return self._voices[friend_id]
        sound: pygame.mixer.Sound | None = None
        path = reaction_clip_path(friend_id, self._locale, project_root=self._root)
        if path is not None:
            try:
                sound = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                sound = None
        if len(self._voices) >= MAX_VOICES:
            self._voices.pop(next(iter(self._voices)))
        self._voices[friend_id] = sound
        return sound

    def stop(self) -> None:
        try:
            if self._voice_channel is not None:
                self._voice_channel.stop()
        except pygame.error:
            pass


__all__ = ["PostcardAudio", "reaction_clip_path"]
