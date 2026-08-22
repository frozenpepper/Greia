from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.hardware import (
    HardwareDefaults,
    HardwareSettingsError,
    HardwareSettingsStore,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HardwareSettingsTests(unittest.TestCase):
    def make_store(self, root: Path) -> HardwareSettingsStore:
        return HardwareSettingsStore.load(
            PROJECT_ROOT / "runtime" / "hardware-settings.toml",
            root,
        )

    def test_default_disables_touchpad_tap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            settings = self.make_store(Path(temporary)).read()
        self.assertFalse(settings.touchpad_tap)
        self.assertEqual(settings.resolution, "auto")
        self.assertEqual(settings.keyboard_layout, "us")
        self.assertEqual(settings.mic_gain, 2.0)

    def test_keyboard_layout_can_be_updated_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            updated = store.update(keyboard_layout="de")
            self.assertEqual(updated.keyboard_layout, "de")
            self.assertEqual(store.read().keyboard_layout, "de")
            with self.assertRaisesRegex(HardwareSettingsError, "unsupported keyboard layout"):
                store.update(keyboard_layout="not-a-real-layout")

    def test_legacy_defaults_without_keyboard_layout_still_load(self) -> None:
        # Older target payloads predate keyboard_layout; installing over them
        # must not fail on the defaults file.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "hardware-settings.toml"
            legacy.write_text(
                "schema_version = 1\n\n[defaults]\ntouchpad_tap = false\n"
                "touchpad_speed = 0.0\nmouse_speed = 0.0\nnatural_scrolling = false\n"
                "resolution = \"auto\"\n\n[limits]\nminimum_speed = -1.0\nmaximum_speed = 1.0\n",
                encoding="utf-8",
            )
            defaults = HardwareDefaults.load(legacy)
            self.assertEqual(defaults.keyboard_layout, "us")
            self.assertEqual(defaults.mic_gain, 2.0)

    def test_parent_update_is_atomic_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            updated = store.update(
                touchpad_tap=True,
                mouse_speed=0.5,
                touchpad_speed=-0.25,
                natural_scrolling=True,
                resolution="1024x600",
                mic_gain=2.5,
                allowed_resolutions=("800x600", "1024x600"),
            )
            reread = store.read()
        self.assertEqual(updated, reread)
        self.assertTrue(reread.touchpad_tap)
        self.assertEqual(reread.mouse_speed, 0.5)
        self.assertEqual(reread.mic_gain, 2.5)

    def test_mic_gain_update_and_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            updated = store.update(mic_gain=3.0)
            self.assertEqual(updated.mic_gain, 3.0)
            self.assertEqual(store.read().mic_gain, 3.0)

            with self.assertRaisesRegex(HardwareSettingsError, "mic_gain must be between"):
                store.update(mic_gain=0.1)

            with self.assertRaisesRegex(HardwareSettingsError, "mic_gain must be between"):
                store.update(mic_gain=5.0)

    def test_rejects_unsupported_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            with self.assertRaisesRegex(HardwareSettingsError, "not supported"):
                store.update(
                    resolution="1920x1080",
                    allowed_resolutions=("800x600", "1024x600"),
                )

    def test_reset_restores_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            store.update(touchpad_tap=True, mouse_speed=0.75, mic_gain=3.5)
            reset = store.reset()
        self.assertFalse(reset.touchpad_tap)
        self.assertEqual(reset.mouse_speed, 0.0)
        self.assertEqual(reset.mic_gain, 2.0)
