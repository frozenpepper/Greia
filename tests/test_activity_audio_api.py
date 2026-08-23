from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from greia_platform.activity_api import (
    get_audio_capture_device,
    get_audio_processing_mode,
)


class ActivityAudioApiTests(unittest.TestCase):
    def test_audio_basic_activity_receives_platform_selected_route(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "audio.basic",
                "GREIA_AUDIO_CAPTURE_DEVICE": "greia_mic_light",
                "GREIA_AUDIO_PROCESSING_MODE": "lightweight",
            },
            clear=False,
        ):
            self.assertEqual(get_audio_capture_device(), "greia_mic_light")
            self.assertEqual(get_audio_processing_mode(), "lightweight")

    def test_activity_without_audio_basic_cannot_read_microphone_route(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "storage.basic",
                "GREIA_AUDIO_CAPTURE_DEVICE": "greia_mic_light",
                "GREIA_AUDIO_PROCESSING_MODE": "lightweight",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(PermissionError, "audio.basic"):
                get_audio_capture_device()
            with self.assertRaisesRegex(PermissionError, "audio.basic"):
                get_audio_processing_mode()

    def test_development_fallback_uses_default_capture_and_off_mode(self) -> None:
        environment = dict(os.environ)
        environment["GREIA_ACTIVITY_CAPABILITIES"] = "audio.basic"
        environment.pop("GREIA_AUDIO_CAPTURE_DEVICE", None)
        environment.pop("GREIA_AUDIO_PROCESSING_MODE", None)
        with patch.dict(os.environ, environment, clear=True):
            self.assertIsNone(get_audio_capture_device())
            self.assertEqual(get_audio_processing_mode(), "off")

    def test_invalid_processing_mode_fails_descriptively_to_off(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "audio.basic",
                "GREIA_AUDIO_PROCESSING_MODE": "mystery-dsp",
            },
            clear=False,
        ):
            self.assertEqual(get_audio_processing_mode(), "off")


if __name__ == "__main__":
    unittest.main()
