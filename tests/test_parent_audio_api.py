from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_parent.update_api import UpdateParentApiApplication
from greia_platform.audio import (
    AudioBackendStatus,
    StaticAudioProcessingBackend,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ParentAudioApiTests(unittest.TestCase):
    def _app(self, root: Path, *, advanced: bool = False) -> UpdateParentApiApplication:
        return UpdateParentApiApplication(
            PROJECT_ROOT,
            root / "parent",
            profiles_dir=root / "profiles",
            hardware_settings_dir=root / "hardware",
            hardware_status_path=root / "hardware-status.json",
            active_profile_status_path=root / "active-profile.json",
            audio_backend=StaticAudioProcessingBackend(
                AudioBackendStatus(
                    backend_id="test",
                    raw_capture_device="raw",
                    lightweight_capture_device="light",
                    advanced_capture_device="advanced" if advanced else None,
                )
            ),
        )

    def test_top_level_parent_api_advertises_audio_resource_and_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary))
            payload = app.index_payload()
            self.assertTrue(payload["capabilities"]["settings.audio"])
            paths = {resource["path"] for resource in payload["resources"]}
            self.assertIn("/api/v1/settings/audio", paths)
            self.assertIn("/api/v1/settings/audio/reset", paths)

    def test_parent_audio_defaults_to_lightweight_and_advanced_off(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary), advanced=True)
            payload = app.audio_payload()
            self.assertTrue(payload["desired"]["microphone_processing_enabled"])
            self.assertFalse(payload["desired"]["advanced_noise_reduction"])
            self.assertEqual(
                payload["effective"]["microphone_processing_mode"], "lightweight"
            )

    def test_parent_can_disable_processing_and_explicitly_enable_advanced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary), advanced=True)
            disabled = app.update_audio(microphone_processing_enabled=False)
            self.assertEqual(
                disabled["effective"]["microphone_processing_mode"], "off"
            )
            advanced = app.update_audio(
                microphone_processing_enabled=True,
                advanced_noise_reduction=True,
            )
            self.assertEqual(
                advanced["effective"]["microphone_processing_mode"], "advanced"
            )
            reset = app.reset_audio()
            self.assertEqual(
                reset["effective"]["microphone_processing_mode"], "lightweight"
            )
            self.assertFalse(reset["desired"]["advanced_noise_reduction"])


if __name__ == "__main__":
    unittest.main()
