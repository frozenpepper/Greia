"""Sound synthesis and voice-cue playback for Il Viaggio del Delfino.

Synthesized effects are prepared once as small mixer Sounds (the audio
equivalent of pre-rendered sprites). Character voice cues are Activity-owned
reviewed OGG files resolved through ``LocalizedResources.audio_cue()`` so text
and audio always share one semantic key per locale. Voice playback owns one
dedicated channel and is fail-soft: missing hardware or assets never break
gameplay.
"""

from __future__ import annotations

import io
import math
import random
import struct
import wave
from typing import Protocol

import pygame

from greia_platform.localization import LocalizedResources

try:
    from delfino_content import audio_key
except ImportError:  # repository/package import context
    from .delfino_content import audio_key


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        raw = bytearray()
        for sample in samples:
            raw.extend(struct.pack("<h", max(-32767, min(32767, int(sample)))))
        handle.writeframes(bytes(raw))
    return buf.getvalue()


class DelfinoAudio(Protocol):  # pragma: no cover - typing seam only
    def play(self, name: str) -> None: ...


class PygameDelfinoAudio:
    """Prepares synthesized effects plus localized Tito voice playback."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._voice_cache: dict[str, pygame.mixer.Sound] = {}
        self._voice_channel: pygame.mixer.Channel | None = None
        self.enabled = False
        self.resources: LocalizedResources | None = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            try:
                pygame.mixer.set_num_channels(8)
                self._voice_channel = pygame.mixer.Channel(0)
            except Exception:
                self._voice_channel = None
            self._init_sounds()
            self.enabled = True
        except Exception:
            self.enabled = False

    # ------------------------------------------------------------------ sfx

    def _init_sounds(self) -> None:
        rate = 22050

        # Pearl chime: two ascending sparkles.
        chime: list[int] = []
        for i in range(int(rate * 0.22)):
            t = i / rate
            freq = 1318.5 if t < 0.08 else 1760.0
            env = max(0.0, 1.0 - t / 0.20)
            chime.append(
                int((math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t)) * env * 13000)
            )
        self._sounds["pearl"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chime, rate)))

        # Starfish fanfare: quick major arpeggio.
        fanfare: list[int] = []
        for note in (1046.5, 1318.5, 1568.0):
            for i in range(int(rate * 0.09)):
                t = i / rate
                env = max(0.0, 1.0 - t / 0.09)
                fanfare.append(int(math.sin(2 * math.pi * note * t) * env * 12000))
        self._sounds["star"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare, rate)))

        # Splash: noise burst with falling body.
        splash: list[int] = []
        for i in range(int(rate * 0.30)):
            t = i / rate
            env = math.exp(-8.5 * t)
            noise = (random.random() * 2.0 - 1.0) * 0.55
            tone = math.sin(2 * math.pi * (300.0 - 160.0 * (t / 0.30)) * t) * 0.45
            splash.append(int(32767.0 * 0.32 * env * (tone + noise)))
        self._sounds["splash"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(splash, rate)))

        # Jelly bounce: friendly boing.
        boing: list[int] = []
        for i in range(int(rate * 0.20)):
            t = i / rate
            env = math.exp(-11.0 * t)
            freq = 320.0 + 190.0 * math.exp(-14.0 * t)
            boing.append(int(math.sin(2 * math.pi * freq * t) * env * 13500))
        self._sounds["boing"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(boing, rate)))

        # Tail-boost whoosh.
        whoosh: list[int] = []
        for i in range(int(rate * 0.28)):
            t = i / rate
            env = math.sin(math.pi * (t / 0.28))
            freq = 280.0 + math.sin(t * 18.0) * 120.0 + (1.0 - t / 0.28) * 380.0
            noise = (random.random() * 2.0 - 1.0) * 0.2
            whoosh.append(int((math.sin(2 * math.pi * freq * t) * 0.75 + noise) * env * 14000))
        self._sounds["whoosh"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(whoosh, rate)))

        # Chapter/finish celebration.
        victory: list[int] = []
        for note in (523.25, 659.25, 783.99, 1046.5):
            for i in range(int(rate * 0.13)):
                t = i / rate
                env = max(0.0, 1.0 - t / 0.13)
                victory.append(
                    int(
                        (
                            math.sin(2 * math.pi * note * t)
                            + 0.3 * math.sin(4 * math.pi * note * t)
                        )
                        * env
                        * 11500
                    )
                )
        self._sounds["victory"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(victory, rate)))

        # Fact-button pop.
        pop: list[int] = []
        for i in range(int(rate * 0.09)):
            t = i / rate
            env = max(0.0, 1.0 - t / 0.09)
            pop.append(int(math.sin(2 * math.pi * (640.0 - 2600.0 * t) * t) * env * 14000))
        self._sounds["pop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(pop, rate)))

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self._sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    # ---------------------------------------------------------------- voice

    def bind_resources(self, resources: LocalizedResources) -> None:
        """Attach the launch locale resolver used for voice cue lookup."""

        self.resources = resources

    def preload_voice(self, fact_ids: list[str]) -> None:
        """Decode every localized cue once up front.

        On the low-resource reference hardware a cold OGG decode inside the
        frame loop causes a very visible hitch at exactly the celebration
        moment (star pickup), so all cues are prepared eagerly at startup.
        Fail-soft: a missing cue is simply skipped and ``play_voice`` will
        report 0.0 for it later.
        """

        if not self.enabled or self.resources is None:
            return
        for fact_id in fact_ids:
            if fact_id in self._voice_cache:
                continue
            try:
                cue = self.resources.audio_cue(audio_key(fact_id))
                self._voice_cache[fact_id] = pygame.mixer.Sound(str(cue.path))
            except Exception:
                continue

    def play_voice(self, fact_id: str) -> float:
        """Play the reviewed Tito cue for a fact; return its duration in seconds.

        Returns 0.0 when audio or the cue is unavailable so the app can fall
        back to a bounded caption-only window instead of leaking state.
        """

        if not self.enabled or self.resources is None:
            return 0.0
        sound = self._voice_cache.get(fact_id)
        if sound is None:
            try:
                cue = self.resources.audio_cue(audio_key(fact_id))
                sound = pygame.mixer.Sound(str(cue.path))
            except Exception:
                return 0.0
            self._voice_cache[fact_id] = sound
        try:
            if self._voice_channel is not None:
                self._voice_channel.stop()
                self._voice_channel.play(sound)
            else:
                sound.play()
        except Exception:
            return 0.0
        return float(sound.get_length())

    def stop_voice(self) -> None:
        if self.enabled and self._voice_channel is not None:
            try:
                self._voice_channel.stop()
            except Exception:
                pass

    def shutdown(self) -> None:
        self.stop_voice()
