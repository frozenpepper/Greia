"""Procedural gentle night-sky audio for Stelle Incantate.

All cues are synthesized locally (no audio assets, no voice files). Star
connection notes rise along a pentatonic ladder so counting upward sounds
musical; wrong taps get a soft low wobble, never a harsh error sound.
"""

from __future__ import annotations

import math
from typing import Final

import pygame


MAX_SIMULTANEOUS_CHANNELS: Final[int] = 3
_SAMPLE_RATE: Final[int] = 22050

#: C major pentatonic ladder (C5 D5 E5 G5 A5 C6 D6 E6) for up to 8+ stars.
_LADDER_HZ: Final[tuple[float, ...]] = (
    523.25, 587.33, 659.25, 783.99, 880.00, 1046.50, 1174.66, 1318.51,
)


class SkyAudio:
    """Bounded procedural sound owner for the night-sky Activity."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._available = False
        try:
            if pygame.mixer.get_init() is not None:
                self._build_sounds()
                self._available = True
        except (pygame.error, RuntimeError):
            self._available = False

    def play_note(self, star_index: int) -> None:
        """Play the rising pentatonic note for the n-th connected star."""

        frequency = _LADDER_HZ[min(max(star_index, 0), len(_LADDER_HZ) - 1)]
        self._play(
            "note",
            _tone(_SAMPLE_RATE, 0.34, frequency, harmonics=(1.0, 0.35, 0.12)),
        )

    def play(self, cue: str) -> None:
        """Play one named cue: wrong, complete, fact, victory."""

        sound = self._sounds.get(cue)
        if sound is not None:
            self._play(cue, sound)

    def _play(self, cue: str, sound: pygame.mixer.Sound) -> None:
        if not self._available:
            return
        try:
            for channel in range(MAX_SIMULTANEOUS_CHANNELS):
                if not pygame.mixer.Channel(channel).get_busy():
                    pygame.mixer.Channel(channel).play(sound)
                    return
            pygame.mixer.Channel(0).play(sound)
        except (pygame.error, RuntimeError):
            pass

    def _build_sounds(self) -> None:
        # Wrong tap: soft descending sigh, encouraging rather than punitive.
        self._sounds["wrong"] = _descending(_SAMPLE_RATE, 0.40, 392.0, 294.0)
        # Constellation complete: warm major arpeggio swell.
        self._sounds["complete"] = _arpeggio(
            _SAMPLE_RATE, (523.25, 659.25, 783.99, 1046.50)
        )
        # Fact page: single curious two-note chirp.
        self._sounds["fact"] = _arpeggio(_SAMPLE_RATE, (659.25, 987.77))
        # Whole sky finished: longer celebratory arpeggio.
        self._sounds["victory"] = _arpeggio(
            _SAMPLE_RATE, (523.25, 659.25, 783.99, 1046.50, 1318.51)
        )


def _tone(
    sample_rate: int,
    duration: float,
    freq: float,
    harmonics: tuple[float, ...] = (1.0,),
) -> pygame.mixer.Sound:
    num_samples = int(sample_rate * duration)
    buf = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        env = math.exp(-3.5 * (t / duration))
        value = 0.0
        for h_idx, amp in enumerate(harmonics):
            value += amp * math.sin(2.0 * math.pi * freq * (h_idx + 1) * t)
        sample = int(value * env * 11000)
        sample = max(-32767, min(32767, sample))
        buf.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
    return pygame.mixer.Sound(buffer=bytes(buf))


def _descending(
    sample_rate: int,
    duration: float,
    start_freq: float,
    end_freq: float,
) -> pygame.mixer.Sound:
    num_samples = int(sample_rate * duration)
    buf = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        env = math.sin(math.pi * (t / duration))
        freq = start_freq + (end_freq - start_freq) * (t / duration)
        value = math.sin(2.0 * math.pi * freq * t)
        sample = int(value * env * 9000)
        sample = max(-32767, min(32767, sample))
        buf.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
    return pygame.mixer.Sound(buffer=bytes(buf))


def _arpeggio(sample_rate: int, frequencies: tuple[float, ...]) -> pygame.mixer.Sound:
    note_duration = 0.16
    fade = 0.10
    num_notes = len(frequencies)
    total_samples = int(sample_rate * (note_duration * num_notes + fade))
    buf = bytearray()
    for i in range(total_samples):
        t = i / sample_rate
        value = 0.0
        for n, freq in enumerate(frequencies):
            local = t - n * note_duration
            if 0.0 <= local < note_duration + fade:
                env = math.exp(-4.0 * (local / note_duration))
                value += 0.8 * math.sin(2.0 * math.pi * freq * local) * env
        sample = int(value * 10000)
        sample = max(-32767, min(32767, sample))
        buf.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
    return pygame.mixer.Sound(buffer=bytes(buf))
