"""Acquario Magico — synthesized sound bank plus Tito's approved voice.

The Activity ships without packaged effect audio. ``AquariumAudio``
synthesizes the five short cues (bubble, nibble, glow, chest,
splash) once, after the first frame, and loads Tito's owner-approved
shared character takes (``celebrate.success``, ``praise.general``)
once through the platform resolver (selected language, then English).
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

from greia_platform.localization import shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank

# Shared character takes this Activity uses (owner-approved v0.2 library).
VOICE_SPEAKER = "tito"
VOICE_CUES = ("celebrate.success", "praise.general")


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
        project_root = Path(__file__).resolve().parents[2]
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
        except Exception:
            pass

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
