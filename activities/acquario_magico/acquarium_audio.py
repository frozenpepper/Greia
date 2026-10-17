"""Acquario Magico — synthesized sound bank plus Tito's approved voice.

The Activity ships without packaged effect audio. ``AquariumAudio``
synthesizes the five short cues (bubble, nibble, glow, chest,
splash) once, after the first frame, and loads Tito's owner-approved
shared character takes (``celebrate.success``, ``praise.general``)
once through the platform resolver (selected language, then English).
Two owner-approved mission lines ("find the octopus", "feed the hungry
turtle", ``assets/audio/<locale>/``) are spoken when that mission starts,
and a touched creature's name comes from the shared vocabulary bank
(``shared_vocab_audio_path``), never over another line.
Playback is then a name lookup, which means the frame loop never
re-decodes or re-synthesizes audio. No new speech is generated here.

The mixer may be unavailable in headless runs; ``play`` is then
a no-op.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
import wave

import pygame

from greia_platform.localization import (
    LocalizationError,
    activity_resources,
    shared_character_audio_path,
    shared_vocab_audio_path,
)
from greia_platform.pygame_audio import DeferredSoundBank

# Shared character takes this Activity uses (owner-approved v0.2 library).
VOICE_SPEAKER = "tito"
VOICE_CUES = ("celebrate.success", "praise.general")
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
# Owner-approved per-Activity mission lines (cue id = "<kind>_<species>").
MISSION_CUES = ("find_octopus", "feed_turtle")
# Species id -> shared vocabulary-bank noun id (the tag shows the same word).
SPECIES_VOCAB = {
    "clownfish": "fish",
    "turtle": "turtle",
    "octopus": "octopus",
    "dolphin": "dolphin",
    "puffer": "pufferfish",
    "seahorse": "seahorse",
    "jellyfish": "jellyfish",
    "starfish": "starfish",
}


def voice_paths(locale: str, project_root: Path = PROJECT_ROOT) -> dict[str, Path]:
    """Resolve every recorded line this Activity speaks (no decoding).

    Locale -> base -> English -> silence, through the platform resolvers.
    Keys: the mission cue ids and ``name.<species_id>``.
    """

    found: dict[str, Path] = {}
    try:
        resources = activity_resources(PACKAGE_ROOT, requested_locale=locale)
    except LocalizationError:
        resources = None
    if resources is not None:
        for cue in MISSION_CUES:
            path = resources.audio_path(cue)
            if path is not None:
                found[cue] = path
    for species_id, noun in SPECIES_VOCAB.items():
        path = shared_vocab_audio_path(project_root, noun, locale)
        if path is not None:
            found[f"name.{species_id}"] = path
    return found


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = bytearray()
        for s in samples:
            clamped = max(-32768, min(32767, int(s)))
            raw.extend(struct.pack("<h", clamped))
        w.writeframes(raw)
    return buf.getvalue()


class AquariumAudio:
    """Prepared sound bank for acquario_magico.

    Sounds are synthesized once, after the first frame. ``play(name)``
    is the only public surface Activities or tests should call.

    The ``_sounds`` attribute is exposed so contract tests can
    verify the bank's name keys without a real mixer.
    """

    def __init__(self, locale: str | None = None) -> None:
        self._sounds = DeferredSoundBank()
        self._voices: dict[str, pygame.mixer.Sound] = {}
        self._last_voice: pygame.mixer.Sound | None = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._init_sounds()
        except Exception:
            # Mixer may be unavailable in headless test runs; the bank
            # is then empty and play() is a no-op.
            pass
        if locale:
            self._load_voices(locale)

    def _load_voices(self, locale: str) -> None:
        project_root = PROJECT_ROOT
        for cue, path in voice_paths(locale, project_root).items():
            try:
                self._voices[cue] = pygame.mixer.Sound(str(path))
            except Exception:
                continue
        for cue in VOICE_CUES:
            try:
                path = shared_character_audio_path(project_root, VOICE_SPEAKER, cue, locale)
            except Exception:
                path = None
            if path is None:
                continue
            try:
                self._voices[cue] = pygame.mixer.Sound(str(path))
            except Exception:
                continue

    def say(self, cue: str) -> None:
        """Play one approved Tito take (silent when it is unavailable)."""

        voice = self._voices.get(cue)
        if voice is None:
            return
        try:
            voice.play()
            self._last_voice = voice
        except Exception:
            pass

    def speaking(self) -> bool:
        voice = self._last_voice
        if voice is None:
            return False
        try:
            return voice.get_num_channels() > 0
        except Exception:
            return False

    def prompt(self, cue: str) -> None:
        """Speak a mission invitation unless another line is still playing."""

        if not self.speaking():
            self.say(cue)

    def name(self, species_id: str) -> None:
        """Say a touched creature's name, never over another line."""

        if not self.speaking():
            self.say(f"name.{species_id}")

    def _init_sounds(self) -> None:
        rate = 22050

        # 1. Bubble pop
        def render_bubble() -> list[int]:
            bubble_samples: list[int] = []
            for i in range(int(rate * 0.08)):
                t = i / rate
                env = math.exp(-20.0 * t)
                val = math.sin(2.0 * math.pi * (500.0 + 400.0 * (t / 0.08)) * t)
                bubble_samples.append(int(32767.0 * 0.25 * env * val))
            return bubble_samples

        self._sounds.define("bubble", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_bubble()))))

        # 2. Nibble food
        def render_nibble() -> list[int]:
            nibble_samples: list[int] = []
            for i in range(int(rate * 0.10)):
                t = i / rate
                env = math.exp(-15.0 * t)
                val = math.sin(2.0 * math.pi * 750.0 * t) + 0.3 * math.sin(2.0 * math.pi * 1200.0 * t)
                nibble_samples.append(int(32767.0 * 0.22 * env * val))
            return nibble_samples

        self._sounds.define("nibble", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_nibble()))))

        # 3. Glow chime
        def render_glow() -> list[int]:
            glow_samples: list[int] = []
            for i in range(int(rate * 0.35)):
                t = i / rate
                env = math.exp(-3.5 * t)
                val = 0.5 * math.sin(2.0 * math.pi * 523.25 * t) + 0.5 * math.sin(2.0 * math.pi * 783.99 * t)
                glow_samples.append(int(32767.0 * 0.25 * env * val))
            return glow_samples

        self._sounds.define("glow", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_glow()))))

        # 4. Treasure chest chime
        def render_chest() -> list[int]:
            chest_samples: list[int] = []
            for i in range(int(rate * 0.40)):
                t = i / rate
                env = math.exp(-3.0 * t)
                freq = 659.25 if t < 0.1 else (783.99 if t < 0.2 else 1046.50)
                val = math.sin(2.0 * math.pi * freq * t)
                chest_samples.append(int(32767.0 * 0.25 * env * val))
            return chest_samples

        self._sounds.define("chest", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_chest()))))

        # 5. Splash sound
        def render_splash() -> list[int]:
            splash_samples: list[int] = []
            for i in range(int(rate * 0.12)):
                t = i / rate
                env = math.exp(-12.0 * t)
                noise = (random.random() * 2.0 - 1.0) * 0.4
                val = math.sin(2.0 * math.pi * 320.0 * t) * 0.6 + noise
                splash_samples.append(int(32767.0 * 0.22 * env * val))
            return splash_samples

        self._sounds.define("splash", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_splash()))))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is None:
            return
        try:
            snd.play()
        except Exception:
            pass
