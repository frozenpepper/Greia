"""Baia delle Orche — synthesized sea sounds plus Tito's approved voice.

The splash/whistle/purr/bell cues are tiny tones synthesized once, after the first frame.
Speech is never generated here: Tito's six orca facts are the Activity's
owner-approved recordings (``assets/audio/<lang>/tito_fact_*.wav``, resolved by
``LocalizedResources.audio_path``), and his short praise lines are the shared
character takes resolved through ``shared_character_audio_path`` (selected
language, then English, then silence).
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
from typing import Protocol
import wave

import pygame

from greia_platform.localization import LocalizedResources, shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    """Pack signed 16-bit mono audio samples into a valid in-memory WAV byte stream."""
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


PACKAGE_ROOT = Path(__file__).resolve().parent
AUDIO_DIR = PACKAGE_ROOT / "assets" / "audio"
# Shared character takes this Activity uses (owner-approved v0.2 library).
VOICE_SPEAKER = "tito"
VOICE_CUES = ("celebrate.success", "praise.general")


class OrcaAudio(Protocol):
    """Protocol for Activity audio playback."""

    def play(self, name: str) -> None:
        ...

    def play_voice(self, key: str, locale: str = "it") -> None:
        ...

    def stop_voice(self) -> None:
        ...

    def say(self, cue: str) -> None:
        ...


class PygameOrcaAudio:
    """Synthesizes and caches cute, realistic, non-blocking marine sounds and Tito character voice clips."""

    def __init__(
        self,
        resources: LocalizedResources | None = None,
        *,
        project_root: Path | None = None,
    ) -> None:
        self._resources = resources
        self._project_root = project_root if project_root is not None else PACKAGE_ROOT.parents[1]
        self._sounds = DeferredSoundBank()
        self._voice_cache: dict[tuple[str, str], pygame.mixer.Sound] = {}
        self._shared_voices: dict[str, pygame.mixer.Sound | None] = {}
        self._voice_channel: pygame.mixer.Channel | None = None
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            try:
                pygame.mixer.set_num_channels(8)
                # Channel 0 is reserved for speech so effects never cut Tito off.
                pygame.mixer.set_reserved(1)
                self._voice_channel = pygame.mixer.Channel(0)
            except Exception:
                self._voice_channel = None
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        rate = 22050

        # 1. Water Splash
        def render_splash() -> list[int]:
            splash_samples: list[int] = []
            for i in range(int(rate * 0.22)):
                t = i / rate
                env = math.exp(-9.0 * t)
                noise = (random.random() * 2.0 - 1.0) * 0.45
                tone = math.sin(2.0 * math.pi * (260.0 - 80.0 * (t / 0.22)) * t) * 0.55
                splash_samples.append(int(32767.0 * 0.35 * env * (tone + noise)))
            return splash_samples

        self._sounds.define("splash", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_splash(), rate))))

        # 2. Orca Whistle (Harmonic, joyful cetacean whistle)
        def render_whistle() -> list[int]:
            whistle_samples: list[int] = []
            for i in range(int(rate * 0.45)):
                t = i / rate
                env = math.sin(math.pi * (t / 0.45)) ** 0.8
                f = 950.0 + 350.0 * math.sin(2.0 * math.pi * 3.5 * t) + 120.0 * math.sin(2.0 * math.pi * 12.0 * t)
                val = (
                    0.7 * math.sin(2.0 * math.pi * f * t)
                    + 0.25 * math.sin(2.0 * math.pi * f * 2.0 * t)
                    + 0.05 * math.sin(2.0 * math.pi * f * 3.0 * t)
                )
                whistle_samples.append(int(32767.0 * 0.28 * env * val))
            return whistle_samples

        self._sounds.define("whistle", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_whistle(), rate))))

        # 3. Echolocation Clicks
        def render_clicks() -> list[int]:
            clicks_samples: list[int] = []
            for i in range(int(rate * 0.28)):
                t = i / rate
                # Rapid clicks at 35Hz repetition
                click_phase = (t * 35.0) % 1.0
                click_env = math.exp(-40.0 * click_phase) if click_phase < 0.15 else 0.0
                high_freq = 2400.0 + random.uniform(-150.0, 150.0)
                val = math.sin(2.0 * math.pi * high_freq * t) * click_env
                clicks_samples.append(int(32767.0 * 0.25 * val))
            return clicks_samples

        self._sounds.define("clicks", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_clicks(), rate))))

        # 4. Fish Nibble / Munch
        def render_nibble() -> list[int]:
            nibble_samples: list[int] = []
            for i in range(int(rate * 0.12)):
                t = i / rate
                env = math.exp(-18.0 * t)
                val = math.sin(2.0 * math.pi * 680.0 * t) + 0.35 * (random.random() * 2.0 - 1.0)
                nibble_samples.append(int(32767.0 * 0.32 * env * val))
            return nibble_samples

        self._sounds.define("nibble", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_nibble(), rate))))

        # 5. Happy Purr / Chirp
        def render_purr() -> list[int]:
            purr_samples: list[int] = []
            for i in range(int(rate * 0.32)):
                t = i / rate
                env = math.sin(math.pi * (t / 0.32))
                mod = 1.0 + 0.5 * math.sin(2.0 * math.pi * 28.0 * t)
                val = math.sin(2.0 * math.pi * 420.0 * t) * mod
                purr_samples.append(int(32767.0 * 0.25 * env * val))
            return purr_samples

        self._sounds.define("purr", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_purr(), rate))))

        # 6. Bubble Pop
        def render_bubble() -> list[int]:
            bubble_samples: list[int] = []
            for i in range(int(rate * 0.07)):
                t = i / rate
                env = math.exp(-25.0 * t)
                val = math.sin(2.0 * math.pi * (450.0 + 600.0 * (t / 0.07)) * t)
                bubble_samples.append(int(32767.0 * 0.30 * env * val))
            return bubble_samples

        self._sounds.define("bubble", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_bubble(), rate))))

        # 7. Ball Bounce / Boing
        def render_bounce() -> list[int]:
            bounce_samples: list[int] = []
            for i in range(int(rate * 0.15)):
                t = i / rate
                env = math.exp(-12.0 * t)
                f = 320.0 + 180.0 * math.exp(-15.0 * t)
                val = math.sin(2.0 * math.pi * f * t)
                bounce_samples.append(int(32767.0 * 0.32 * env * val))
            return bounce_samples

        self._sounds.define("bounce", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_bounce(), rate))))

        # 8. Marine Chimes for Musical Echolocation (Notes: C5, E5, G5, C6)
        notes = {"bell_0": 523.25, "bell_1": 659.25, "bell_2": 783.99, "bell_3": 1046.50}

        def render_bell(freq: float) -> list[int]:
            chime_samples: list[int] = []
            for i in range(int(rate * 0.40)):
                t = i / rate
                env = math.exp(-4.5 * t)
                val = 0.65 * math.sin(2.0 * math.pi * freq * t) + 0.35 * math.sin(2.0 * math.pi * (freq * 2.0) * t)
                chime_samples.append(int(32767.0 * 0.30 * env * val))
            return chime_samples

        for b_name, freq in notes.items():
            self._sounds.define(
                b_name,
                lambda freq=freq: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_bell(freq), rate))),
            )

        # 9. Aurora / Night Shimmer Chime
        def render_aurora() -> list[int]:
            aurora_samples: list[int] = []
            for i in range(int(rate * 0.55)):
                t = i / rate
                env = math.exp(-2.8 * t)
                val = (
                    0.4 * math.sin(2.0 * math.pi * 587.33 * t)
                    + 0.35 * math.sin(2.0 * math.pi * 880.0 * t)
                    + 0.25 * math.sin(2.0 * math.pi * 1174.66 * t)
                )
                aurora_samples.append(int(32767.0 * 0.26 * env * val))
            return aurora_samples

        self._sounds.define("aurora", lambda: pygame.mixer.Sound(io.BytesIO(_synth_wav(render_aurora(), rate))))

    def play(self, name: str) -> None:
        if not self._enabled:
            return
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_voice(self, key: str, locale: str = "it") -> None:
        if not self._enabled:
            return
        if self._resources is not None:
            loc = self._resources.context.selected.language
            path = self._resources.audio_path(
                f"tito.{key}", filename=f"tito_{key}.wav"
            )
        else:
            # Older unit-test callers may still construct the audio class on
            # its own. The shipped Activity supplies shared resources.
            loc = locale.split("-", 1)[0]
            path = AUDIO_DIR / loc / f"tito_{key}.wav"
            if not path.is_file():
                path = AUDIO_DIR / "en" / f"tito_{key}.wav"
        cache_key = (key, loc)
        snd = self._voice_cache.get(cache_key)
        if snd is None and path is not None and path.is_file():
            try:
                snd = pygame.mixer.Sound(str(path))
                self._voice_cache[cache_key] = snd
            except (pygame.error, OSError):
                pass
        if snd is not None:
            try:
                if self._voice_channel is not None:
                    self._voice_channel.stop()
                    self._voice_channel.play(snd)
                else:
                    snd.play()
            except Exception:
                pass

    def stop_voice(self) -> None:
        if self._enabled and self._voice_channel is not None:
            try:
                self._voice_channel.stop()
            except Exception:
                pass

    def say(self, cue: str) -> None:
        """Play one approved shared Tito take (silent when unavailable)."""

        if not self._enabled or cue not in VOICE_CUES:
            return
        if cue not in self._shared_voices:
            sound: pygame.mixer.Sound | None = None
            locale = self._resources.context.selected.value if self._resources is not None else "en"
            try:
                path = shared_character_audio_path(self._project_root, VOICE_SPEAKER, cue, locale)
                if path is not None:
                    sound = pygame.mixer.Sound(str(path))
            except Exception:
                sound = None
            self._shared_voices[cue] = sound
        sound = self._shared_voices[cue]
        if sound is None:
            return
        try:
            if self._voice_channel is not None:
                self._voice_channel.stop()
                self._voice_channel.play(sound)
            else:
                sound.play()
        except Exception:
            pass
