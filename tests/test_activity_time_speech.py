"""Provider-free semantic speech acceptance for the My Time incubator."""
from __future__ import annotations

import unittest

from activity_incubator.tempo_di_greia.time_model import TimeMode
from activity_incubator.tempo_di_greia.time_speech import SPEECH_CUES, TimeSpeech


class FakeSpeechTransport:
    def __init__(self, cues: tuple[str, ...] = SPEECH_CUES) -> None:
        self.cues = set(cues)
        self.played: list[str] = []
        self.stop_count = 0
        self.speaking = False

    def has_clip(self, cue: str) -> bool:
        return cue in self.cues

    def play(self, cue: str) -> bool:
        if not self.has_clip(cue):
            return False
        if self.speaking:
            raise AssertionError("overlapping voice playback")
        self.played.append(cue)
        self.speaking = True
        return True

    def busy(self) -> bool:
        return self.speaking

    def stop(self) -> None:
        self.stop_count += 1
        self.speaking = False

    def finish(self) -> None:
        self.speaking = False


class TimeSpeechTests(unittest.TestCase):
    def test_welcome_then_instruction_without_overlap(self) -> None:
        audio = FakeSpeechTransport()
        speech = TimeSpeech(audio)
        speech.start(TimeMode.CLOCK, False)
        self.assertEqual(audio.played, ["presenter.welcome"])
        speech.start(TimeMode.CLOCK, False)  # no duplicate launch
        speech.update()  # current clip is playing
        self.assertEqual(len(audio.played), 1)
        audio.finish()
        speech.update()
        self.assertEqual(audio.played[-1], "instruction.clock")
        speech.update()
        self.assertEqual(len(audio.played), 2)

    def test_mode_change_cancels_obsolete_instruction_and_repeat_replaces(self) -> None:
        audio = FakeSpeechTransport()
        speech = TimeSpeech(audio)
        speech.start(TimeMode.CLOCK, False)
        speech.on_context(TimeMode.TIMER, False)
        self.assertEqual(audio.played[-1], "instruction.timer")
        self.assertEqual(audio.stop_count, 1)
        speech.on_context(TimeMode.TIMER, False)  # same tab is not a repeated prompt
        self.assertEqual(audio.played.count("instruction.timer"), 1)
        self.assertTrue(speech.can_repeat)
        self.assertTrue(speech.replay())
        self.assertEqual(audio.played.count("instruction.timer"), 2)
        speech.timer_finished()
        self.assertEqual(audio.played[-1], "feedback.timer_finished")
        speech.update()  # canceled welcome must never resurface
        self.assertNotIn("instruction.clock", audio.played)
        speech.close()
        self.assertFalse(audio.speaking)

    def test_practice_is_once_only_and_leaving_uses_optional_real_time(self) -> None:
        audio = FakeSpeechTransport()
        speech = TimeSpeech(audio)
        speech.start(TimeMode.CLOCK, False)
        speech.on_context(TimeMode.CLOCK, True)
        self.assertEqual(audio.played[-1], "instruction.practice")
        speech.on_context(TimeMode.CLOCK, False)
        self.assertEqual(audio.played[-1], "instruction.real_time")
        count = len(audio.played)
        speech.on_context(TimeMode.CLOCK, True)
        self.assertEqual(len(audio.played), count)  # introduced already
        self.assertTrue(speech.replay())
        self.assertEqual(audio.played[-1], "instruction.practice")

    def test_missing_recordings_never_create_fake_speech_or_replay(self) -> None:
        audio = FakeSpeechTransport(())
        speech = TimeSpeech(audio)
        speech.start(TimeMode.CLOCK, False)
        speech.on_context(TimeMode.TIMER, False)
        speech.update()
        self.assertFalse(speech.can_repeat)
        self.assertFalse(speech.replay())
        speech.timer_finished()
        self.assertEqual(audio.played, [])

    def test_startup_context_changes_do_not_speak_before_first_frame(self) -> None:
        audio = FakeSpeechTransport()
        speech = TimeSpeech(audio)
        speech.on_context(TimeMode.TIMER, False)
        self.assertEqual(audio.played, [])
        speech.start(TimeMode.TIMER, False)
        self.assertEqual(audio.played, ["presenter.welcome"])
        audio.finish()
        speech.update()
        self.assertEqual(audio.played[-1], "instruction.timer")

    def test_no_welcome_still_plays_instruction_and_cancels_on_close(self) -> None:
        audio = FakeSpeechTransport(("instruction.stopwatch",))
        speech = TimeSpeech(audio)
        speech.start(TimeMode.STOPWATCH, False)
        self.assertEqual(audio.played, ["instruction.stopwatch"])
        speech.close()
        self.assertFalse(audio.speaking)


if __name__ == "__main__":
    unittest.main()
