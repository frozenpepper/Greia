from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from greia_platform.audio import (
    AudioBackendStatus,
    AudioService,
    AudioSettingsError,
    MicrophoneProcessingMode,
    StaticAudioProcessingBackend,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _backend(*, lightweight: bool = True, advanced: bool = False):
    return StaticAudioProcessingBackend(
        AudioBackendStatus(
            backend_id="test",
            raw_capture_device="raw",
            lightweight_capture_device="light" if lightweight else None,
            advanced_capture_device="advanced" if advanced else None,
        )
    )


class AudioServiceTests(unittest.TestCase):
    def _service(self, state_dir: Path, *, lightweight: bool = True, advanced: bool = False):
        return AudioService.load(
            PROJECT_ROOT / "runtime" / "audio-settings.toml",
            state_dir,
            backend=_backend(lightweight=lightweight, advanced=advanced),
        )

    def test_lightweight_processing_is_default_and_never_auto_promotes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = self._service(Path(temporary), advanced=True)
            route = service.route()
            self.assertEqual(route.mode, MicrophoneProcessingMode.LIGHTWEIGHT)
            self.assertEqual(route.capture_device, "light")
            payload = service.payload()
            self.assertTrue(payload["desired"]["microphone_processing_enabled"])
            self.assertFalse(payload["desired"]["advanced_noise_reduction"])
            self.assertTrue(payload["available"]["advanced"])

    def test_parent_must_explicitly_enable_advanced_processing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = self._service(Path(temporary), advanced=True)
            payload = service.update(advanced_noise_reduction=True)
            self.assertEqual(
                payload["effective"]["microphone_processing_mode"],
                MicrophoneProcessingMode.ADVANCED.value,
            )
            document = json.loads(
                (Path(temporary) / "audio-settings.json").read_text(encoding="utf-8")
            )
            self.assertTrue(document["advanced_noise_reduction"])

    def test_advanced_cannot_be_enabled_when_backend_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = self._service(Path(temporary), advanced=False)
            with self.assertRaisesRegex(AudioSettingsError, "not available"):
                service.update(advanced_noise_reduction=True)
            self.assertEqual(service.route().mode, MicrophoneProcessingMode.LIGHTWEIGHT)

    def test_processing_can_be_disabled_without_changing_backend_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = self._service(Path(temporary), advanced=True)
            service.update(microphone_processing_enabled=False)
            route = service.route()
            self.assertEqual(route.mode, MicrophoneProcessingMode.OFF)
            self.assertEqual(route.capture_device, "raw")
            self.assertTrue(service.payload()["available"]["advanced"])

    def test_missing_lightweight_endpoint_fails_open_to_raw_capture_and_reports_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = self._service(Path(temporary), lightweight=False)
            route = service.route()
            self.assertEqual(route.mode, MicrophoneProcessingMode.OFF)
            self.assertEqual(route.capture_device, "raw")
            self.assertEqual(route.fallback_reason, "lightweight_unavailable")

    def test_activity_environment_contains_only_resolved_platform_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = self._service(Path(temporary), advanced=True)
            service.update(advanced_noise_reduction=True)
            self.assertEqual(
                dict(service.session_environment()),
                {
                    "GREIA_AUDIO_PROCESSING_MODE": "advanced",
                    "GREIA_AUDIO_CAPTURE_DEVICE": "advanced",
                },
            )

    def test_non_boolean_parent_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = self._service(Path(temporary))
            with self.assertRaisesRegex(AudioSettingsError, "must be boolean"):
                service.update(microphone_processing_enabled=1)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
