from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from greia_platform.activity_api import (
    get_audio_capture_device,
    get_audio_processing_mode,
    get_sdl_capture_device,
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


class SdlCaptureDeviceDesignationTests(unittest.TestCase):
    """The SDL device designation is platform-owned route projection."""

    def test_routed_launch_designates_the_sdl_enumerated_device(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "audio.basic",
                "GREIA_AUDIO_CAPTURE_DEVICE": "greia_mic_light",
            },
            clear=False,
        ):
            with patch(
                "pygame._sdl2.audio.get_audio_device_names",
                return_value=["HDA Intel, ALC268 Analog"],
            ) as enumerated:
                self.assertEqual(
                    get_sdl_capture_device(), "HDA Intel, ALC268 Analog"
                )
            self.assertEqual(enumerated.call_count, 1)

    def test_routed_launch_with_no_sdl_capture_devices_returns_none(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "audio.basic",
                "GREIA_AUDIO_CAPTURE_DEVICE": "greia_mic_light",
            },
            clear=False,
        ):
            with patch(
                "pygame._sdl2.audio.get_audio_device_names",
                return_value=[],
            ):
                self.assertIsNone(get_sdl_capture_device())

    def test_development_launch_without_route_falls_back_to_none(self) -> None:
        environment = dict(os.environ)
        environment["GREIA_ACTIVITY_CAPABILITIES"] = "audio.basic"
        environment.pop("GREIA_AUDIO_CAPTURE_DEVICE", None)
        with patch.dict(os.environ, environment, clear=True):
            self.assertIsNone(get_sdl_capture_device())

    def test_activity_without_audio_basic_cannot_read_sdl_designation(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GREIA_ACTIVITY_CAPABILITIES": "storage.basic",
                "GREIA_AUDIO_CAPTURE_DEVICE": "greia_mic_light",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(PermissionError, "audio.basic"):
                get_sdl_capture_device()


if __name__ == "__main__":
    unittest.main()
