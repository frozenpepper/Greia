"""Shared Activity synthesis primitives stay byte-identical to the per-Activity copies they replaced.

The golden digests below were taken from the ``_decaying_sine`` / ``_mix`` /
``_sweep`` / ``_bell`` / ``_chord`` / ``_chime`` / ``_fanfare`` helpers that
were copied into ~21 Activities (commit fdb7cc21) just before they moved into
``greia_platform.pygame_audio``; a change to any digest changes how every
Activity cue sounds and must be deliberate.
"""

from __future__ import annotations

import hashlib
import math
import unittest
from unittest import mock

from greia_platform import pygame_audio
from greia_platform.pygame_audio import (
    bell_sound,
    chime_run_sound,
    chord_sound,
    decaying_sine,
    fanfare_sound,
    mix_samples,
    mono_pcm16_bytes,
    sweep_samples,
    sweep_sound,
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


class _CapturedSound:
    """Stands in for ``pygame.mixer.Sound(buffer=...)`` and keeps the PCM."""

    last: bytes = b""

    def __init__(self, *, buffer: bytes) -> None:
        type(self).last = bytes(buffer)


def _sound_digest(factory, *args, **kwargs) -> str:
    with mock.patch.object(pygame_audio.pygame.mixer, "Sound", _CapturedSound):
        factory(*args, **kwargs)
    return _digest(_CapturedSound.last)


class DecayingSineTests(unittest.TestCase):
    CASES = {
        "a": ((22050, 11025, 880.0, 9.0), {}, "59cb19aea5487ceb"),
        "b": ((22050, 22050, 523.25, 7.0), {"start": 0.3, "gain": 0.3}, "1e0b9370955e1a7c"),
        "c": ((22050, 18000, 659.25, 3.5 / 0.15), {"start": 0.12, "stop": 0.27}, "cd1b88cf8d3eb59a"),
        "d": ((44100, 20000, 1046.5, 12.0), {"start": 0.0213, "attack": 0.012, "stop": 0.3, "gain": 0.5}, "2e42c600cfa5a1f5"),
        "e": ((22050, 1000, 440.0, 5.0), {"start": 5.0}, "fc19b19971194257"),
        "f": ((22050, 3000, 440.0, 5.0), {"start": 0.05, "stop": 0.01}, "ff6698a6e831ffcf"),
        "g": ((48000, 24000, 2093.0, 2.0), {"attack": 0.006, "start": 0.1}, "1407f20bb05f5e5f"),
    }

    def test_matches_the_activity_copies_byte_for_byte(self) -> None:
        for name, (args, kwargs, golden) in self.CASES.items():
            with self.subTest(case=name):
                self.assertEqual(_digest(mono_pcm16_bytes(decaying_sine(*args, **kwargs), 2, scale=10000)), golden)

    def test_matches_the_closed_form_curve_in_16_bit_samples(self) -> None:
        rate, count, frequency, decay, start, gain = 22050, 6000, 660.0, 8.0, 0.05, 0.7
        direct = [
            0.0 if index / rate < start else
            gain * math.sin(2.0 * math.pi * frequency * (index / rate - start)) * math.exp(-decay * (index / rate - start))
            for index in range(count)
        ]
        shared = decaying_sine(rate, count, frequency, decay, start=start, gain=gain)
        self.assertEqual(len(shared), count)
        self.assertEqual(mono_pcm16_bytes(shared, 1, scale=10000), mono_pcm16_bytes(direct, 1, scale=10000))

    def test_window_outside_the_buffer_is_silence_of_the_requested_length(self) -> None:
        self.assertEqual(decaying_sine(22050, 1000, 440.0, 5.0, start=5.0), [0.0] * 1000)
        self.assertEqual(decaying_sine(22050, 100, 440.0, 5.0, start=0.1, stop=0.05), [0.0] * 100)


class MixAndSweepTests(unittest.TestCase):
    def test_mix_samples_sums_parts_and_passes_a_single_part_through(self) -> None:
        parts = [
            decaying_sine(22050, 5000, 440.0, 3.0),
            decaying_sine(22050, 5000, 660.0, 3.0, start=0.05),
            decaying_sine(22050, 5000, 880.0, 3.0, gain=0.3),
        ]
        self.assertEqual(_digest(mono_pcm16_bytes(mix_samples(parts), 2, scale=9000)), "eb4394967287f6df")
        self.assertEqual(_digest(mono_pcm16_bytes(mix_samples(parts[:1]), 1, scale=9000)), "daaccfeccd03b36c")
        self.assertEqual(mix_samples([[1.0, 2.0], [0.5, -2.0]]), [1.5, 0.0])

    def test_sweep_matches_the_activity_copies_byte_for_byte(self) -> None:
        goldens = {
            (22050, 0.14, 520.0, 880.0): "8384b333fca7d0ff",
            (22050, 0.5, 900.0, 300.0): "2a11519b5b368e0f",
            (44100, 0.09, 380.0, 300.0): "eb6f6c38c807b699",
            (22050, 0.26, 900.0, 1500.0): "709916c3853f41ad",
        }
        for (rate, duration, start, end), golden in goldens.items():
            with self.subTest(rate=rate, duration=duration):
                self.assertEqual(_sound_digest(sweep_sound, rate, 2, duration, start, end, 7200), golden)
                self.assertEqual(_digest(mono_pcm16_bytes(sweep_samples(rate, duration, start, end), 2, scale=7200)), golden)

    def test_sweep_fades_in_and_out(self) -> None:
        samples = sweep_samples(22050, 0.1, 400.0, 800.0)
        self.assertEqual(len(samples), 2205)
        self.assertEqual(samples[0], 0.0)
        self.assertLess(abs(samples[-1]), 0.01)
        self.assertLessEqual(max(map(abs, samples)), 1.0)


class CueRecipeTests(unittest.TestCase):
    def test_recipes_match_the_activity_copies_byte_for_byte(self) -> None:
        cases = {
            "bell": (bell_sound, (22050, 2, (1046.5, 1318.5, 1568.0), 0.36, 2300), {}, "afcfab44a9bb7b7f"),
            "bell_single": (bell_sound, (22050, 1, (784.0,), 0.32, 2100), {}, "4016aff39504104a"),
            "chord": (chord_sound, (22050, 2, (659.25, 783.99, 1046.5), 0.42), {}, "ac9731d856a262f1"),
            "chime_run": (chime_run_sound, (22050, 2, (783.99, 1046.5, 1318.5, 1568.0)), {"step": 0.08}, "1d4185a4ea7564e9"),
            "chime_run_custom": (chime_run_sound, (44100, 1, (523.25, 659.25)), {"step": 0.12, "volume": 6000}, "81f0b6a4f533aeb4"),
            "fanfare_default": (fanfare_sound, (22050, 2), {}, "7e96d6da0f51f3bd"),
            "fanfare_louder": (fanfare_sound, (22050, 2, 11000), {}, "7ffff1cbc15a0b4d"),
        }
        for name, (factory, args, kwargs, golden) in cases.items():
            with self.subTest(recipe=name):
                self.assertEqual(_sound_digest(factory, *args, **kwargs), golden)


if __name__ == "__main__":
    unittest.main()
