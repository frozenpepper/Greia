from __future__ import annotations

import unittest
from unittest import mock

from greia_platform.pygame_audio import append_mono_pcm16, current_pcm16_mixer_spec


class PygameAudioTests(unittest.TestCase):
    def test_current_pcm16_mixer_spec_uses_runtime_frequency_and_channels(self) -> None:
        with mock.patch("pygame.mixer.get_init", return_value=(44100, -16, 2)):
            self.assertEqual(current_pcm16_mixer_spec(), (44100, 2))

    def test_current_pcm16_mixer_spec_rejects_unsupported_or_missing_format(self) -> None:
        for spec in (None, (44100, -8, 2), (0, -16, 2), (44100, -16, 0)):
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


if __name__ == "__main__":
    unittest.main()
