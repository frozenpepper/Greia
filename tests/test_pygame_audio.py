from __future__ import annotations

import threading
import unittest
from unittest import mock

from greia_platform.first_frame_work import FirstFrameWork
from greia_platform.pygame_audio import DeferredSoundBank, append_mono_pcm16, current_pcm16_mixer_spec


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
