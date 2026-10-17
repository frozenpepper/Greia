"""Approved speech plus small synthesized effects for Magic Bakery.

Speech uses only recorded, approved clips, with the usual
locale -> base language -> English -> silence fallback:

* the cast's shared takes (``celebrate.success``, ``praise.general``,
  ``encourage.retry``, ``encourage.progress``, ``ready.go``) for the
  customer at the counter and for Momo the baker;
* topping names from the shared vocabulary bank (``shared_vocab_audio_path``)
  and spoken numbers from the shared numbers bank when the platform offers
  one (``shared_number_audio_path``, P7 F6). Neither bank has these words
  yet, so orders and counting stay pictorial and silent today and become
  spoken as soon as approved clips land - no Activity change needed.

Effects (topping pop, take-off, "not that one" hum, serve bell, happy jingle,
gentle "hmm", shop door chime, rising counting tones, swoosh) are synthesized
once, after the first frame. Every call fails soft without a mixer.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from itertools import accumulate, repeat
import math
from operator import add, mul
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform import localization
from greia_platform.localization import shared_character_audio_path, shared_vocab_audio_path
from greia_platform.pygame_audio import DeferredSoundBank, current_pcm16_mixer_spec, mono_pcm16_bytes

SPEECH_CHANNEL: Final = 0
FIRST_SFX_CHANNEL: Final = 2
LAST_SFX_CHANNEL: Final = 4
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
CAST_CUES: Final = ("ready.go", "celebrate.success", "praise.general", "encourage.retry", "encourage.progress")
CAST_CACHE_LIMIT: Final = 2  # the customer at the counter and the next one (or Momo)
WORD_CACHE_LIMIT: Final = 12
SPEECH_QUEUE_LIMIT: Final = 6
COUNT_TONES: Final = 12
EFFECTS: Final = ("pop", "unpop", "nope", "bell", "yum", "hmm", "door", "swoosh", "save")
# C major from C5 upward: one step per counted topping.
_SCALE: Final = (523.25, 587.33, 659.25, 698.46, 783.99, 880.0, 987.77, 1046.5, 1174.66, 1318.51, 1396.91, 1567.98)


class BakeryAudio:
    """Own the sound bank, the cast takes and the spoken-word queue for one session."""

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
        self._cast: OrderedDict[str, dict[str, list[pygame.mixer.Sound]]] = OrderedDict()
        self._words: OrderedDict[str, pygame.mixer.Sound | None] = OrderedDict()
        self._queue: deque[pygame.mixer.Sound] = deque(maxlen=SPEECH_QUEUE_LIMIT)
        self._available = False
        self.last_speech: str | None = None
        self.last_effect: str | None = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), LAST_SFX_CHANNEL + 1))
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError, OSError):
            self._available = False

    # -- cast ---------------------------------------------------------------------

    def cast(self, character: str, cue: str) -> bool:
        """Play one approved shared take of ``character`` (random variant)."""

        self.last_speech = f"{character}:{cue}"
        if not self._available:
            return False
        takes = self._takes(character).get(cue)
        if not takes:
            return False
        self._queue.clear()
        return self._speak(self._rng.choice(takes))

    def prepare_cast(self, character: str) -> None:
        """Load a character's takes ahead of its entrance (bounded cache)."""

        if self._available:
            self._takes(character)

    # -- words --------------------------------------------------------------------

    def has_number(self, value: int) -> bool:
        return self._number_path(value) is not None

    def say_number(self, value: int) -> bool:
        """Count aloud with the shared numbers bank; False (silent) without it."""

        self.last_speech = f"number.{int(value)}"
        sound = self._word(f"number.{int(value)}", lambda: self._number_path(value))
        if sound is None:
            return False
        self._queue.clear()
        return self._speak(sound)

    def say_order(self, items: tuple[tuple[int, str], ...]) -> bool:
        """Queue "<number> <topping>" for each order line that has recordings."""

        self.last_speech = "order"
        queued = False
        self._queue.clear()
        for amount, topping_id in items:
            for key, resolve in (
                (f"number.{amount}", lambda a=amount: self._number_path(a)),
                (f"noun.{topping_id}", lambda t=topping_id: self._noun_path(t)),
            ):
                sound = self._word(key, resolve)
                if sound is not None:
                    self._queue.append(sound)
                    queued = True
        if queued:
            self.update()
        return queued

    def say_topping(self, topping_id: str) -> bool:
        sound = self._word(f"noun.{topping_id}", lambda: self._noun_path(topping_id))
        if sound is None:
            return False
        self._queue.clear()
        return self._speak(sound)

    def update(self) -> None:
        """Feed the next queued word once the speech channel is free."""

        if not self._available or not self._queue:
            return
        try:
            if not pygame.mixer.Channel(SPEECH_CHANNEL).get_busy():
                self._speak(self._queue.popleft())
        except (pygame.error, RuntimeError):
            self._queue.clear()

    # -- effects ------------------------------------------------------------------

    def play(self, name: str) -> None:
        self.last_effect = name
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

    def count_tone(self, value: int) -> None:
        """Rising tone for the n-th counted topping (heard even without words)."""

        self.play(f"count{max(1, min(COUNT_TONES, int(value)))}")

    # -- loading ------------------------------------------------------------------

    def _speak(self, sound: pygame.mixer.Sound | None) -> bool:
        if sound is None:
            return False
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return False
        return True

    def _takes(self, character: str) -> dict[str, list[pygame.mixer.Sound]]:
        cached = self._cast.get(character)
        if cached is not None:
            self._cast.move_to_end(character)
            return cached
        takes: dict[str, list[pygame.mixer.Sound]] = {}
        for cue in CAST_CUES:
            try:
                first = shared_character_audio_path(self._project_root, character, cue, self.locale)
            except Exception:
                first = None
            if first is None:
                continue
            # Sibling takes of the same family in the same accepted folder.
            pattern = "__".join(first.name.split("__")[:3]) + "__*.wav"
            sounds: list[pygame.mixer.Sound] = []
            for path in sorted(first.parent.glob(pattern))[:3]:
                try:
                    sounds.append(pygame.mixer.Sound(str(path)))
                except (pygame.error, OSError):
                    continue
            if sounds:
                takes[cue] = sounds
        self._cast[character] = takes
        while len(self._cast) > CAST_CACHE_LIMIT:
            self._cast.popitem(last=False)
        return takes

    def _word(self, key: str, resolve) -> pygame.mixer.Sound | None:
        if not self._available:
            return None
        if key in self._words:
            self._words.move_to_end(key)
            return self._words[key]
        sound = None
        path = resolve()
        if path is not None:
            try:
                sound = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                sound = None
        self._words[key] = sound
        while len(self._words) > WORD_CACHE_LIMIT:
            self._words.popitem(last=False)
        return sound

    def _noun_path(self, topping_id: str) -> Path | None:
        try:
            return shared_vocab_audio_path(self._project_root, topping_id, self.locale)
        except Exception:
            return None

    def _number_path(self, value: int) -> Path | None:
        # The shared numbers bank (P7 F6) is pending owner voice approval; use
        # it as soon as the platform publishes its resolver.
        resolver = getattr(localization, "shared_number_audio_path", None)
        if not callable(resolver):
            return None
        try:
            path = resolver(self._project_root, int(value), self.locale)
        except Exception:
            return None
        return path if isinstance(path, Path) else None

    def _build_sounds(self) -> None:
        spec = current_pcm16_mixer_spec()
        if spec is None:
            return
        rate, channels = spec
        self._sounds.define("pop", lambda: _sweep(rate, channels, 0.09, 600.0, 1200.0, 6500))
        self._sounds.define("unpop", lambda: _sweep(rate, channels, 0.11, 900.0, 420.0, 5200))
        self._sounds.define("nope", lambda: _notes(rate, channels, ((0.0, 0.14, 392.0), (0.14, 0.2, 330.0)), 0.4, 5200))
        self._sounds.define("bell", lambda: _bell(rate, channels))
        self._sounds.define("yum", lambda: _notes(
            rate, channels, ((0.0, 0.16, 659.25), (0.12, 0.16, 783.99), (0.24, 0.3, 1046.5)), 0.7, 6200
        ))
        self._sounds.define("hmm", lambda: _sweep(rate, channels, 0.32, 440.0, 360.0, 4200))
        self._sounds.define("door", lambda: _notes(rate, channels, ((0.0, 0.3, 1318.51), (0.16, 0.4, 1046.5)), 0.8, 4800))
        self._sounds.define("swoosh", lambda: _swoosh(rate, channels))
        self._sounds.define("save", lambda: _notes(
            rate, channels, ((0.0, 0.14, 783.99), (0.1, 0.14, 987.77), (0.2, 0.3, 1174.66)), 0.6, 5600
        ))
        for index, frequency in enumerate(_SCALE[:COUNT_TONES], start=1):
            self._sounds.define(f"count{index}", lambda frequency=frequency: _notes(rate, channels, ((0.0, 0.16, frequency),), 0.32, 5600))


def _decaying_sine(
    rate: int,
    count: int,
    frequency: float,
    decay: float,
    *,
    start: float = 0.0,
    stop: float | None = None,
    attack: float = 0.0,
    gain: float = 1.0,
) -> list[float]:
    """``gain * sin(2*pi*f*local) * exp(-decay*local) * min(1, local/attack)`` for one partial.

    ``local`` is the time since ``start`` seconds; the list covers sample indices
    ``0..count-1`` and is zero before ``start`` and from ``stop`` on. Instead of a
    ``sin`` and an ``exp`` call per sample (the dominant start-up cost on the
    Atom), the partial is a complex phasor multiplied by one constant per
    sample and accumulated in C by ``itertools.accumulate``: the same curve to
    ~1e-11 (identical 16-bit samples), about three times cheaper.
    """

    first = int(start * rate)
    while first / rate < start:
        first += 1
    while first > 0 and (first - 1) / rate >= start:
        first -= 1
    last = count
    if stop is not None:
        last = min(count, int(stop * rate))
        while last / rate < stop:
            last += 1
        last = min(count, last)
    if first >= last:
        return [0.0] * count
    omega = 2.0 * math.pi * frequency
    offset = first / rate - start
    fade = math.exp(-decay / rate)  # |r| per sample; r = fade * exp(i*omega/rate), z0 = gain * exp((-decay + i*omega) * offset)
    start_amplitude = gain * math.exp(-decay * offset)
    phasors = accumulate(
        repeat(complex(fade * math.cos(omega / rate), fade * math.sin(omega / rate)), last - first - 1),
        mul,
        initial=complex(start_amplitude * math.cos(omega * offset), start_amplitude * math.sin(omega * offset)),
    )
    values = [z.imag for z in phasors]
    if attack > 0.0:
        for index in range(min(len(values), int(attack * rate) + 2)):
            values[index] *= min(1.0, (offset + index / rate) / attack)
    return [0.0] * first + values + [0.0] * (count - last)


def _mix(parts: list[list[float]]) -> list[float]:
    """Sum equally long sample lists."""

    total = parts[0]
    for part in parts[1:]:
        total = list(map(add, total, part))
    return total


def _notes(
    rate: int,
    channels: int,
    notes: tuple[tuple[float, float, float], ...],
    duration: float,
    volume: int,
) -> pygame.mixer.Sound:
    """Soft bell-like notes: (start, length, frequency)."""

    count = int(rate * duration)
    parts = [
        _decaying_sine(rate, count, frequency, 3.2 / length, start=start, stop=start + length * 2.5, attack=0.012)
        for start, length, frequency in notes
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=volume))


def _sweep(rate: int, channels: int, duration: float, start: float, end: float, volume: int) -> pygame.mixer.Sound:
    count = int(rate * duration)
    times = [index / rate for index in range(count)]
    per_sample = 2.0 * math.pi / rate
    phases = accumulate([(start + (end - start) * (t / duration)) * per_sample for t in times])
    envelope = [math.sin(math.pi * t / duration) for t in times]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(map(mul, map(math.sin, phases), envelope), channels, scale=volume))


def _bell(rate: int, channels: int) -> pygame.mixer.Sound:
    """Counter service bell: a bright struck tone with an inharmonic partial."""

    count = int(rate * 0.7)
    parts = [
        _decaying_sine(rate, count, 1568.0, 5.5, attack=0.004, gain=0.7),
        _decaying_sine(rate, count, 1568.0 * 2.76, 5.5, attack=0.004, gain=0.3),
    ]
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(_mix(parts), channels, scale=6500))


def _swoosh(rate: int, channels: int) -> pygame.mixer.Sound:
    noise = random.Random(11)
    samples: list[float] = []
    smooth = 0.0
    duration = 0.36
    for index in range(int(rate * duration)):
        t = index / rate
        smooth += (noise.uniform(-1.0, 1.0) - smooth) * (0.08 + 0.3 * t / duration)
        envelope = math.sin(math.pi * t / duration)
        samples.append(int(smooth * envelope * 8000))
    return pygame.mixer.Sound(buffer=mono_pcm16_bytes(samples, channels))


__all__ = ["BakeryAudio", "CAST_CUES", "COUNT_TONES", "EFFECTS"]
