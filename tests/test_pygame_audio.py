from __future__ import annotations

import sys
import threading
import unittest
from unittest import mock

from greia_platform import pygame_audio
from greia_platform.first_frame_work import FirstFrameWork
from greia_platform.pygame_audio import (
    DeferredSoundBank,
    SynthesisPacer,
    append_mono_pcm16,
    current_pcm16_mixer_spec,
    mono_pcm16_bytes,
)


class PygameAudioTests(unittest.TestCase):
    def test_current_pcm16_mixer_spec_uses_runtime_frequency_and_channels(self) -> None:
        with mock.patch("pygame.mixer.get_init", return_value=(44100, -16, 2)):
            self.assertEqual(current_pcm16_mixer_spec(), (44100, 2))

    def test_current_pcm16_mixer_spec_rejects_unsupported_or_missing_format(self) -> None:
        for spec in (
            None,
            (44100, -8, 2),
            (44100, 16, 2),
            (0, -16, 2),
            (44100, -16, 0),
        ):
            with self.subTest(spec=spec):
                with mock.patch("pygame.mixer.get_init", return_value=spec):
                    self.assertIsNone(current_pcm16_mixer_spec())

    def test_append_mono_pcm16_duplicates_sample_across_channels(self) -> None:
        raw = bytearray()
        append_mono_pcm16(raw, 0x1234, 2)
        self.assertEqual(raw, bytearray(b"\x34\x12\x34\x12"))

    def test_append_mono_pcm16_clamps_and_validates_channel_count(self) -> None:
        raw = bytearray()
        append_mono_pcm16(raw, 99999, 1)
        self.assertEqual(raw, bytearray(b"\xff\x7f"))
        with self.assertRaises(ValueError):
            append_mono_pcm16(bytearray(), 0, 0)


    def test_append_mono_pcm16_rejects_bad_counts_without_appending(self) -> None:
        for count in (-1, 0, 9):
            raw = bytearray()
            with self.assertRaises(ValueError):
                append_mono_pcm16(raw, 5, count)
            self.assertEqual(raw, bytearray())
        raw = bytearray()
        append_mono_pcm16(raw, -99999.7, 1)
        append_mono_pcm16(raw, -1.9, 3)
        self.assertEqual(raw, bytearray(b"\x00\x80" + b"\xff\xff" * 3))

    def test_mono_pcm16_bytes_matches_per_sample_appends(self) -> None:
        samples = [0.0, 0.5, -0.5, 1.2, -1.3, 0.25]
        for channels in (1, 2, 3):
            expected = bytearray()
            for value in samples:
                append_mono_pcm16(expected, int(value * 30000), channels)
            with self.subTest(channels=channels):
                self.assertEqual(mono_pcm16_bytes(samples, channels, scale=30000), bytes(expected))
        self.assertEqual(mono_pcm16_bytes([1, 2], 1), b"\x01\x00\x02\x00")
        self.assertEqual(mono_pcm16_bytes([], 2), b"")
        with self.assertRaises(ValueError):
            mono_pcm16_bytes([0.0], 0)


class _FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class SynthesisPacerTests(unittest.TestCase):
    def _pacer(self, fake: _FakeTime, **kwargs) -> SynthesisPacer:
        return SynthesisPacer(clock=fake.clock, sleep=fake.sleep, **kwargs)

    def test_rests_after_each_work_slice_and_hurry_skips_rests(self) -> None:
        fake = _FakeTime()
        pacer = self._pacer(fake, work_seconds=0.004, rest_seconds=0.006)
        fake.now += 0.003
        pacer.checkpoint()
        self.assertEqual(fake.sleeps, [])
        fake.now += 0.002
        pacer.checkpoint()
        self.assertEqual(fake.sleeps, [0.006])
        pacer.hurry()
        fake.now += 1.0
        pacer.checkpoint()
        pacer.rest()
        self.assertEqual(fake.sleeps, [0.006])
        pacer.cue_finished()  # the cue boundary clears the hurry and yields
        self.assertEqual(fake.sleeps, [0.006, 0.006])
        with self.assertRaises(ValueError):
            SynthesisPacer(work_seconds=0)
        with self.assertRaises(ValueError):
            SynthesisPacer(switch_interval=0)

    def test_installed_lowers_switch_interval_and_restores_it(self) -> None:
        original = sys.getswitchinterval()
        pacer = SynthesisPacer(switch_interval=original / 4)
        with pacer.installed():
            self.assertAlmostEqual(sys.getswitchinterval(), original / 4)
            self.assertIs(pygame_audio._worker_local.pacer, pacer)
        self.assertAlmostEqual(sys.getswitchinterval(), original)
        self.assertIsNone(pygame_audio._worker_local.pacer)
        with SynthesisPacer(switch_interval=None).installed():
            self.assertAlmostEqual(sys.getswitchinterval(), original)
        # Overlapping workers (two banks): restored only when the last ends.
        first, second = SynthesisPacer(switch_interval=original / 4), SynthesisPacer(switch_interval=original / 4)
        with first.installed():
            with second.installed():
                pass
            self.assertAlmostEqual(sys.getswitchinterval(), original / 4)
        self.assertAlmostEqual(sys.getswitchinterval(), original)

    def test_append_checkpoints_only_on_the_paced_thread(self) -> None:
        fake = _FakeTime()
        pacer = self._pacer(fake, work_seconds=0.001, rest_seconds=0.002, switch_interval=None)
        raw = bytearray()
        for _ in range(pygame_audio.PACE_CHECK_SAMPLES * 4):
            append_mono_pcm16(raw, 1, 1)  # no pacer on this thread: never sleeps
            fake.now += 0.0001
        self.assertEqual(fake.sleeps, [])
        with pacer.installed():
            for _ in range(pygame_audio.PACE_CHECK_SAMPLES * 4):
                append_mono_pcm16(raw, 1, 1)
                fake.now += 0.0001
        self.assertGreaterEqual(len(fake.sleeps), 3)


class _Recorder:
    def __init__(self) -> None:
        self.calls = 0

    def callback(self) -> None:
        self.calls += 1


class FirstFrameWorkTests(unittest.TestCase):
    def test_callbacks_wait_for_release_then_run_immediately(self) -> None:
        work = FirstFrameWork()
        early, late = _Recorder(), _Recorder()
        work.after_first_frame(early.callback)
        self.assertEqual(early.calls, 0)
        work.release()
        self.assertEqual(early.calls, 1)
        work.release()
        self.assertEqual(early.calls, 1)
        work.after_first_frame(late.callback)
        self.assertEqual(late.calls, 1)

    def test_discarded_owners_are_not_kept_alive(self) -> None:
        work = FirstFrameWork()
        recorder = _Recorder()
        work.after_first_frame(recorder.callback)
        del recorder
        work.release()  # nothing to call, nothing raised


class DeferredSoundBankTests(unittest.TestCase):
    def _bank(self) -> DeferredSoundBank:
        return DeferredSoundBank(defer_until_first_frame=False)

    def test_definition_builds_nothing_until_requested(self) -> None:
        bank = self._bank()
        calls: list[str] = []
        bank.define("tick", lambda: calls.append("tick") or "tick-sound")
        bank.define("pop", lambda: calls.append("pop") or "pop-sound")
        self.assertEqual(calls, [])
        self.assertEqual(len(bank), 2)
        self.assertIn("tick", bank)
        self.assertEqual(set(bank), {"tick", "pop"})
        self.assertFalse(bank.built("tick"))
        self.assertEqual(bank.get("tick"), "tick-sound")
        self.assertEqual(bank.get("tick"), "tick-sound")
        self.assertEqual(calls, ["tick"])
        self.assertIsNone(bank.get("missing"))
        self.assertEqual(bank.built_sounds(), ["tick-sound"])

    def test_failing_factory_is_silent_and_not_retried(self) -> None:
        bank = self._bank()
        calls: list[int] = []

        def broken():
            calls.append(1)
            raise RuntimeError("no mixer")

        bank.define("boom", broken)
        self.assertIsNone(bank.get("boom"))
        self.assertIsNone(bank.get("boom"))
        self.assertEqual(len(calls), 1)
        self.assertNotIn("boom", bank)
        with self.assertRaises(KeyError):
            bank["boom"]

    def test_redefinition_replaces_and_clear_forgets(self) -> None:
        bank = self._bank()
        bank.define("cue", lambda: "first")
        self.assertEqual(bank["cue"], "first")
        bank.define("cue", lambda: "second")
        self.assertEqual(bank["cue"], "second")
        bank.clear()
        self.assertEqual(len(bank), 0)
        self.assertIsNone(bank.get("cue"))

    def test_background_warm_builds_every_cue_once_after_release(self) -> None:
        bank = self._bank()
        built: list[str] = []
        lock = threading.Lock()

        def factory(name: str):
            def build():
                with lock:
                    built.append(name)
                return name
            return build

        for name in ("a", "b", "c"):
            bank.define(name, factory(name))
        with mock.patch("pygame.mixer.get_init", return_value=(22050, -16, 1)):
            bank.warm_in_background()
            # A foreground request races the worker but never rebuilds a cue.
            self.assertEqual(bank["b"], "b")
            worker = bank._worker
            self.assertIsNotNone(worker)
            worker.join(timeout=5)
        self.assertEqual(sorted(built), ["a", "b", "c"])
        self.assertTrue(all(bank.built(name) for name in ("a", "b", "c")))

    def test_worker_is_paced_and_hurried_when_a_cue_is_awaited(self) -> None:
        fake_sleeps: list[float] = []
        started = threading.Event()
        release = threading.Event()
        pacers: list[SynthesisPacer] = []

        def make_pacer() -> SynthesisPacer:
            pacer = SynthesisPacer(work_seconds=0.001, rest_seconds=0.001, sleep=fake_sleeps.append)
            pacers.append(pacer)
            return pacer

        def slow():
            started.set()
            release.wait(5)
            return "slow-sound"

        bank = DeferredSoundBank(defer_until_first_frame=False, pacer_factory=make_pacer)
        bank.define("slow", slow)
        bank.define("quick", lambda: "quick-sound")
        with mock.patch("pygame.mixer.get_init", return_value=(22050, -16, 1)):
            bank.warm_in_background()
            self.assertTrue(started.wait(5))
            waiter = threading.Thread(target=lambda: bank.get("slow"))
            waiter.start()
            for _ in range(500):  # until the foreground request is waiting
                if pacers and pacers[0]._hurry:
                    break
                threading.Event().wait(0.002)
            self.assertTrue(pacers[0]._hurry)
            release.set()
            waiter.join(5)
            bank._worker.join(5)
        self.assertTrue(bank.built("slow") and bank.built("quick"))
        self.assertGreaterEqual(len(fake_sleeps), 1, "cue boundaries yield")
        self.assertFalse(pacers[0]._hurry)
        self.assertIsNone(pygame_audio._worker_local.__dict__.get("pacer"))

    def test_bank_registered_for_first_frame_starts_warming_on_release(self) -> None:
        work = FirstFrameWork()
        with mock.patch("greia_platform.pygame_audio.after_first_frame", work.after_first_frame):
            bank = DeferredSoundBank()
        bank.define("only", lambda: "sound")
        self.assertIsNone(bank._worker)
        with mock.patch("pygame.mixer.get_init", return_value=(22050, -16, 1)):
            work.release()
            self.assertIsNotNone(bank._worker)
            bank._worker.join(timeout=5)
        self.assertTrue(bank.built("only"))


if __name__ == "__main__":
    unittest.main()
