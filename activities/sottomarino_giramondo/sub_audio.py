"""Sottomarino Giramondo — Prepared Synthesized Sound Bank.

Sound effects for the submarine instruments, ocean acoustics, and encounters.
Synthesized once, after the first frame matching the active PCM16 mixer spec.
Audio is completely fail-soft and non-blocking.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import random
import struct
import wave
from collections import OrderedDict
from dataclasses import dataclass
import enum
from typing import Callable, Optional

import pygame

from greia_platform.pygame_audio import DeferredSoundBank, append_mono_pcm16, current_pcm16_mixer_spec


def _synth_wav(samples: list[int], rate: int = 22050, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = bytearray()
        for s in samples:
            append_mono_pcm16(raw, s, channels)
        w.writeframes(raw)
    return buf.getvalue()


class SubmarineAudio:
    """Prepared sound bank for submarine instruments and encounters."""

    def __init__(self) -> None:
        self._sounds = DeferredSoundBank()
        self._voice_sounds: OrderedDict[str, pygame.mixer.Sound] = OrderedDict()
        self._voice_channel = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._init_sounds()
        except Exception:
            pass

    def _init_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        rate = spec[0] if spec else 22050
        channels = spec[1] if spec else 1

        # 1. Sonar Ping (crisp sine pulse with long soft decay)
        def render_sonar() -> list[int]:
            duration_s = 0.8
            n_samples = int(rate * duration_s)
            samples = []
            freq = 1200.0
            for i in range(n_samples):
                t = i / rate
                env = math.exp(-4.5 * t)
                val = int(24000.0 * math.sin(2.0 * math.pi * freq * t) * env)
                samples.append(val)
            return samples

        self._register("sonar", render_sonar, rate, channels)

        # 2. Bubble Burble (rising bubbly pitch chirps)
        def render_bubbles() -> list[int]:
            duration_s = 0.4
            n_samples = int(rate * duration_s)
            samples = []
            for i in range(n_samples):
                t = i / rate
                f = 300.0 + 500.0 * (t / duration_s) + 60.0 * math.sin(40.0 * math.pi * t)
                env = math.sin(math.pi * (t / duration_s))
                val = int(20000.0 * math.sin(2.0 * math.pi * f * t) * env)
                samples.append(val)
            return samples

        self._register("bubbles", render_bubbles, rate, channels)

        # 3. Ship Horn / Whistle (cheerful two-tone acoustic brass whistle)
        def render_horn() -> list[int]:
            duration_s = 1.1
            n_samples = int(rate * duration_s)
            samples = []
            for i in range(n_samples):
                t = i / rate
                if t < 0.42:
                    # First whistle note (260 Hz)
                    env = math.sin(math.pi * (t / 0.42)) ** 0.5
                    f0 = 260.0
                    vib = 1.0 + 0.012 * math.sin(2.0 * math.pi * 6.0 * t)
                    w = (
                        math.sin(2.0 * math.pi * f0 * vib * t) +
                        0.45 * math.sin(2.0 * math.pi * f0 * 2.0 * vib * t) +
                        0.25 * math.sin(2.0 * math.pi * f0 * 3.0 * vib * t) +
                        0.10 * math.sin(2.0 * math.pi * f0 * 4.0 * vib * t)
                    ) / 1.8
                    val = int(22000.0 * w * env)
                elif t < 0.48:
                    val = 0
                else:
                    # Second higher, cheerful whistle note (330 Hz - toot toot!)
                    t2 = t - 0.48
                    dur2 = duration_s - 0.48
                    env = math.sin(math.pi * (t2 / dur2)) ** 0.5
                    f0 = 329.6
                    vib = 1.0 + 0.012 * math.sin(2.0 * math.pi * 6.0 * t)
                    w = (
                        math.sin(2.0 * math.pi * f0 * vib * t) +
                        0.45 * math.sin(2.0 * math.pi * f0 * 2.0 * vib * t) +
                        0.25 * math.sin(2.0 * math.pi * f0 * 3.0 * vib * t) +
                        0.10 * math.sin(2.0 * math.pi * f0 * 4.0 * vib * t)
                    ) / 1.8
                    val = int(22000.0 * w * env)
                samples.append(val)
            return samples

        self._register("horn", render_horn, rate, channels)

        # 4. Click / Switch (mechanical tactile cockpit toggle)
        def render_click() -> list[int]:
            duration_s = 0.08
            n_samples = int(rate * duration_s)
            samples = []
            for i in range(n_samples):
                t = i / rate
                noise = (random.random() * 2.0 - 1.0)
                env = math.exp(-50.0 * t)
                val = int(16000.0 * noise * env)
                samples.append(val)
            return samples

        self._register("click", render_click, rate, channels)

        # 5. Floodlight Hum / Power On
        def render_light() -> list[int]:
            duration_s = 0.5
            n_samples = int(rate * duration_s)
            samples = []
            for i in range(n_samples):
                t = i / rate
                f = 200.0 + 350.0 * (t / duration_s)
                env = min(1.0, t * 15.0) * (1.0 - t / duration_s)
                val = int(18000.0 * math.sin(2.0 * math.pi * f * t) * env)
                samples.append(val)
            return samples

        self._register("light", render_light, rate, channels)

        # 6. Gentle Encounter Alert (friendly bell chime)
        def render_alert() -> list[int]:
            duration_s = 0.6
            n_samples = int(rate * duration_s)
            samples = []
            for i in range(n_samples):
                t = i / rate
                env = math.exp(-6.0 * t)
                val = int(22000.0 * (math.sin(2.0 * math.pi * 880.0 * t) + 0.5 * math.sin(2.0 * math.pi * 1760.0 * t)) * env)
                samples.append(val)
            return samples

        self._register("alert", render_alert, rate, channels)

        # 7. Joyful Splash / Giggle (encounter resolution celebration)
        def render_celebrate() -> list[int]:
            duration_s = 0.8
            n_samples = int(rate * duration_s)
            samples = []
            for i in range(n_samples):
                t = i / rate
                env = min(1.0, t * 8.0) * math.exp(-3.0 * t)
                chord = (
                    math.sin(2.0 * math.pi * 523.25 * t) +
                    math.sin(2.0 * math.pi * 659.25 * t) +
                    math.sin(2.0 * math.pi * 783.99 * t)
                ) / 3.0
                val = int(22000.0 * chord * env)
                samples.append(val)
            return samples

        self._register("celebrate", render_celebrate, rate, channels)

        # 8. Gentle Engine Telegraph Chug (tactile gear click when moving throttle)
        def render_engine_shift() -> list[int]:
            duration_s = 0.25
            n_samples = int(rate * duration_s)
            samples = []
            for i in range(n_samples):
                t = i / rate
                env = math.sin(math.pi * (t / duration_s))
                f = 110.0 + 30.0 * math.sin(20.0 * math.pi * t)
                val = int(17000.0 * math.sin(2.0 * math.pi * f * t) * env)
                samples.append(val)
            return samples

        self._register("engine_shift", render_engine_shift, rate, channels)

        # Dedicated voice playback channel to prevent speech overlap
        try:
            # Reserve the voice channel so effects never occupy it (otherwise
            # a celebration chime would delay the captain's next line).
            pygame.mixer.set_reserved(2)
            self._voice_channel = pygame.mixer.Channel(1)
        except Exception:
            self._voice_channel = None

    def _register(self, name: str, render: Callable[[], list[int]], rate: int, channels: int) -> None:
        """Define one cue; its samples are rendered after the first frame."""

        self._sounds.define(
            name, lambda: pygame.mixer.Sound(file=io.BytesIO(_synth_wav(render(), rate, channels)))
        )

    def play(self, name: str) -> None:
        """Play a prepared sound effect safely without blocking or raising."""
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def is_voice_busy(self) -> bool:
        """Check if a voice cue is currently speaking."""
        try:
            if self._voice_channel is not None:
                return self._voice_channel.get_busy()
        except Exception:
            pass
        return False

    _MAX_VOICE_SOUNDS = 12

    def play_voice(self, cue_path: Path | str) -> bool:
        """Play a localized voice line on the dedicated voice channel.

        Decoded clips are kept in a small LRU so a repeated line (orders,
        instrument names) is not decoded from disk every time.
        """
        try:
            p = Path(cue_path)
            key = str(p)
            snd = self._voice_sounds.get(key)
            if snd is None:
                if not p.is_file():
                    return False
                snd = pygame.mixer.Sound(key)
                self._voice_sounds[key] = snd
                while len(self._voice_sounds) > self._MAX_VOICE_SOUNDS:
                    self._voice_sounds.popitem(last=False)
            else:
                self._voice_sounds.move_to_end(key)
            if self._voice_channel is not None:
                self._voice_channel.play(snd)
            else:
                snd.play()
            return True
        except Exception:
            pass
        return False

    def stop_voice(self) -> None:
        try:
            if self._voice_channel is not None:
                self._voice_channel.stop()
        except Exception:
            pass


class SpeechPriority(enum.IntEnum):
    """Lower value = spoken first. Facts never delay an order."""

    URGENT = 0   # orders, visitors at the glass, praise
    NORMAL = 1   # instrument names, creature names
    LOW = 2      # sea facts


@dataclass
class _QueuedCue:
    key: str
    priority: SpeechPriority
    queued_at: float


class SpeechQueue:
    """Bounded, prioritised queue of voice cues spoken one after another.

    * at most ``capacity`` cues wait; a new cue evicts the least important;
    * a cue already waiting is not queued twice, and the same cue is not
      repeated within ``repeat_gap`` seconds (button mashing stays calm);
    * non-urgent cues that waited longer than ``stale_after`` are dropped,
      so a creature's name is never heard long after it swam by.
    """

    def __init__(
        self,
        *,
        capacity: int = 3,
        repeat_gap: float = 4.0,
        stale_after: float = 6.0,
        pause: float = 0.4,
    ) -> None:
        self.capacity = int(capacity)
        self.repeat_gap = float(repeat_gap)
        self.stale_after = float(stale_after)
        self.pause = float(pause)
        self._items: list[_QueuedCue] = []
        self._last_spoken: dict[str, float] = {}
        self._cooldown = 0.0
        self._now = 0.0

    @property
    def pending(self) -> tuple[str, ...]:
        return tuple(item.key for item in self._items)

    def push(self, key: str, priority: SpeechPriority = SpeechPriority.NORMAL, *, force: bool = False) -> bool:
        if not key:
            return False
        if any(item.key == key for item in self._items):
            return False
        if not force and self._now - self._last_spoken.get(key, -1e9) < self.repeat_gap:
            return False
        if priority is SpeechPriority.URGENT:
            # An order or visitor makes queued facts irrelevant.
            self._items = [item for item in self._items if item.priority is not SpeechPriority.LOW]
        self._items.append(_QueuedCue(key, priority, self._now))
        self._items.sort(key=lambda item: (item.priority, item.queued_at))
        while len(self._items) > self.capacity:
            self._items.pop()  # the least important / newest of the lowest tier
        return any(item.key == key for item in self._items)

    def drop(self, priority: SpeechPriority) -> None:
        self._items = [item for item in self._items if item.priority is not priority]

    def clear(self) -> None:
        self._items.clear()

    def update(self, dt: float, busy: bool, speak: Callable[[str], bool]) -> Optional[str]:
        """Advance time; speak the next cue when the voice channel is free."""

        self._now += max(0.0, dt)
        if self._cooldown > 0:
            self._cooldown -= dt
            return None
        if busy:
            return None
        while self._items:
            item = self._items.pop(0)
            if item.priority is not SpeechPriority.URGENT and self._now - item.queued_at > self.stale_after:
                continue
            if speak(item.key):
                self._last_spoken[item.key] = self._now
                if len(self._last_spoken) > 64:
                    oldest = min(self._last_spoken, key=self._last_spoken.get)
                    del self._last_spoken[oldest]
                self._cooldown = self.pause
                return item.key
        return None
