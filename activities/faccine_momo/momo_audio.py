"""Voice playback and small procedural sound effects for Momo's Happy Faces.

Speech uses only the package's approved Momo recordings, selected by Greia's
localization (selected language -> base -> English -> silence). ``say``
interrupts the previous line so feedback is never delayed behind a queue.
Sound effects are tiny tones synthesised once, after the first frame (no files).
"""

from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.pygame_audio import DeferredSoundBank

_SAMPLE_RATE: Final = 22_050
PRAISE_CUES: Final[tuple[str, ...]] = ("praise_1", "praise_2", "praise_3")


class MomoAudio:
    """Load package speech clips and generate procedural expressive SFX."""

    def __init__(
        self,
        package_root: Path,
        locale: str = "it",
        resources: LocalizedResources | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._resources = resources
        self.locale = locale
        self._package_root = package_root
        self._rng = rng if rng is not None else random.Random()
        self._speech_sounds: dict[str, pygame.mixer.Sound] = {}
        self._sfx_sounds = DeferredSoundBank()
        self._speech_channel: pygame.mixer.Channel | None = None
        self._available = False
        self.spoken: list[str] = []  # bounded log of requested cues (tests/tools)

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(8)
            self._speech_channel = pygame.mixer.Channel(0)
            self._available = True
            self._load_speech_clips()
            self._build_procedural_sfx()
        except (pygame.error, RuntimeError):
            self._available = False

    @property
    def cues(self) -> frozenset[str]:
        return frozenset(self._speech_sounds)

    def _load_speech_clips(self) -> None:
        if self._resources is not None:
            # Locale and EN compatibility selection belongs to Greia, not
            # the Activity's mixer or procedural sound effects.
            files = self._resources.speech_paths()
        else:
            audio_dir = self._package_root / "locales" / self.locale / "audio"
            files = {p.stem: p for p in audio_dir.glob("*.wav")}
        for stem, path in files.items():
            try:
                self._speech_sounds[stem] = pygame.mixer.Sound(str(path))
            except (pygame.error, RuntimeError, OSError):
                pass

    # -- speech --------------------------------------------------------------

    def say(self, cue_id: str) -> None:
        """Play one approved line now (interrupting the previous one)."""

        self.spoken.append(cue_id)
        del self.spoken[:-16]
        if not self._available or self._speech_channel is None:
            return
        sound = self._speech_sounds.get(cue_id)
        if sound is None:
            return
        try:
            self._speech_channel.stop()
            self._speech_channel.play(sound)
        except (pygame.error, RuntimeError):
            pass

    def praise(self) -> str:
        cue = self._rng.choice(PRAISE_CUES)
        self.say(cue)
        return cue

    def stop_speech(self) -> None:
        if self._speech_channel is not None:
            try:
                self._speech_channel.stop()
            except (pygame.error, RuntimeError):
                pass

    def is_speech_playing(self) -> bool:
        try:
            return self._speech_channel is not None and bool(self._speech_channel.get_busy())
        except (pygame.error, RuntimeError):
            return False

    # -- effects ---------------------------------------------------------------

    def play_sfx(self, sfx_name: str | None) -> None:
        if not self._available or sfx_name is None:
            return
        sound = self._sfx_sounds.get(sfx_name)
        if sound is None:
            return
        try:
            for index in range(2, 8):
                channel = pygame.mixer.Channel(index)
                if not channel.get_busy():
                    channel.play(sound)
                    return
            pygame.mixer.Channel(2).play(sound)
        except (pygame.error, RuntimeError):
            pass

    def _build_procedural_sfx(self) -> None:
        self._sfx_sounds.define("pop", lambda: self._sweep(0.10, 450.0, 800.0))
        self._sfx_sounds.define("giggle", lambda: self._giggle())
        self._sfx_sounds.define("heart", lambda: self._tone(0.45, 587.33, harmonics=(1.0, 0.5, 0.2)))
        self._sfx_sounds.define("boing", lambda: self._sweep(0.25, 200.0, 520.0))
        self._sfx_sounds.define("wobble", lambda: self._wobble(0.35, 280.0))
        self._sfx_sounds.define("chime", lambda: self._tone(0.6, 880.0, harmonics=(1.0, 0.35, 0.15)))
        self._sfx_sounds.define("whoosh", lambda: self._sweep(0.35, 700.0, 260.0, level=7000))
        self._sfx_sounds.define("splat", lambda: self._sweep(0.18, 320.0, 120.0))
        self._sfx_sounds.define("crash", lambda: self._rumble(0.45, 140.0, level=9000))
        self._sfx_sounds.define("rumble", lambda: self._rumble(0.9, 70.0, level=10000))

    @staticmethod
    def _pack(samples) -> pygame.mixer.Sound:
        buf = bytearray()
        for value in samples:
            sample = max(-32767, min(32767, int(value)))
            buf.extend(sample.to_bytes(2, byteorder="little", signed=True))
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _tone(self, duration: float, freq: float, harmonics: tuple[float, ...] = (1.0,)) -> pygame.mixer.Sound:
        count = int(_SAMPLE_RATE * duration)

        def sample(i: int) -> float:
            t = i / _SAMPLE_RATE
            env = math.exp(-4.0 * (t / duration))
            return sum(amp * math.sin(2.0 * math.pi * freq * (k + 1) * t) for k, amp in enumerate(harmonics)) * env * 12000

        return self._pack(sample(i) for i in range(count))

    def _sweep(self, duration: float, start: float, end: float, *, level: int = 11000) -> pygame.mixer.Sound:
        count = int(_SAMPLE_RATE * duration)

        def sample(i: int) -> float:
            t = i / _SAMPLE_RATE
            frac = t / duration
            freq = start + (end - start) * frac
            return math.sin(2.0 * math.pi * freq * t) * math.sin(math.pi * frac) * level

        return self._pack(sample(i) for i in range(count))

    def _giggle(self) -> pygame.mixer.Sound:
        duration = 0.35
        count = int(_SAMPLE_RATE * duration)

        def sample(i: int) -> float:
            t = i / _SAMPLE_RATE
            env = math.sin(math.pi * (t / duration)) * abs(math.sin(t * math.pi * 9.0))
            freq = 600.0 + 300.0 * math.sin(t * 30.0)
            return math.sin(2.0 * math.pi * freq * t) * env * 10000

        return self._pack(sample(i) for i in range(count))

    def _wobble(self, duration: float, base: float) -> pygame.mixer.Sound:
        count = int(_SAMPLE_RATE * duration)

        def sample(i: int) -> float:
            t = i / _SAMPLE_RATE
            env = math.exp(-3.5 * (t / duration))
            freq = base + 40.0 * math.sin(t * 40.0)
            return math.sin(2.0 * math.pi * freq * t) * env * 9000

        return self._pack(sample(i) for i in range(count))

    def _rumble(self, duration: float, base: float, *, level: int) -> pygame.mixer.Sound:
        """Low soft rumble (thunder far away, blocks tumbling) - never harsh."""

        count = int(_SAMPLE_RATE * duration)
        noise = random.Random(7)
        state = 0.0

        def sample(i: int) -> float:
            nonlocal state
            t = i / _SAMPLE_RATE
            state = state * 0.97 + noise.uniform(-1.0, 1.0) * 0.03
            env = math.sin(math.pi * min(1.0, t / duration)) * math.exp(-1.2 * t / duration)
            tone = math.sin(2.0 * math.pi * base * t) * 0.5
            return (state * 6.0 + tone) * env * level

        return self._pack(sample(i) for i in range(count))


__all__ = ["MomoAudio", "PRAISE_CUES"]
