"""On-demand recording player contracts without an actual SDL mixer."""
from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from greia_platform import creation_audio_pygame as audio
from greia_platform.creation_gallery import GalleryError


class FakeChannel:
    def __init__(self):
        self.busy = True
        self.paused = False
        self.stopped = False

    def pause(self):
        self.paused = True

    def unpause(self):
        self.paused = False

    def stop(self):
        self.stopped = True
        self.busy = False

    def get_busy(self):
        return self.busy


class FakeSound:
    def __init__(self, channel):
        self.channel = channel

    def play(self):
        return self.channel


class FakeMixer:
    def __init__(self):
        self.channel = FakeChannel()
        self.inits = 0
        self.payloads = []

    def get_init(self):
        return self.inits > 0

    def init(self):
        self.inits += 1

    def Sound(self, *, file):
        self.payloads.append(file.read())
        return FakeSound(self.channel)


class RecordingPreviewTests(unittest.TestCase):
    def setUp(self):
        self.mixer = FakeMixer()
        self.pygame = SimpleNamespace(mixer=self.mixer, error=RuntimeError)
        self.module = mock.patch.dict(sys.modules, {"pygame": self.pygame})
        self.module.start()
        self.addCleanup(self.module.stop)
        self.now = 100.0
        self.clock = mock.patch.object(audio.time, "monotonic", side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_play_pause_resume_progress_and_cleanup(self):
        player = audio.PygameRecordingPreview()
        self.assertFalse(player.is_playing())
        player.play(b"RIFF-data")
        self.assertTrue(player.is_playing())
        self.assertEqual(self.mixer.payloads, [b"RIFF-data"])
        self.assertEqual(self.mixer.inits, 1)
        self.now = 103
        self.assertAlmostEqual(player.progress(10), 0.3)
        player.pause()
        self.assertTrue(self.mixer.channel.paused)
        self.now = 140
        self.assertAlmostEqual(player.progress(10), 0.3)
        player.resume()
        self.assertFalse(self.mixer.channel.paused)
        self.now = 142
        self.assertAlmostEqual(player.progress(10), 0.5)
        player.stop()
        self.assertFalse(player.is_playing())
        self.assertEqual(player.progress(10), 0.0)
        self.assertTrue(self.mixer.channel.stopped)

    def test_failed_audio_output_and_oversize_fail_without_playing(self):
        player = audio.PygameRecordingPreview()
        with self.assertRaises(GalleryError):
            player.play(b"x" * (audio.PygameRecordingPreview.MAX_WAV_BYTES + 1))
        self.assertFalse(player.is_playing())
        self.pygame.mixer = SimpleNamespace(get_init=lambda: True, Sound=lambda **_: (_ for _ in ()).throw(RuntimeError("device")))
        with self.assertRaises(GalleryError):
            player.play(b"test")
        self.assertFalse(player.is_playing())


if __name__ == "__main__":
    unittest.main()
