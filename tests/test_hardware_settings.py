from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.hardware import HardwareSettingsError, HardwareSettingsStore


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

    def test_parent_update_is_atomic_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            updated = store.update(
                touchpad_tap=True,
                mouse_speed=0.5,
                touchpad_speed=-0.25,
                natural_scrolling=True,
                resolution="1024x600",
                allowed_resolutions=("800x600", "1024x600"),
            )
            reread = store.read()
        self.assertEqual(updated, reread)
        self.assertTrue(reread.touchpad_tap)
        self.assertEqual(reread.mouse_speed, 0.5)

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
            store.update(touchpad_tap=True, mouse_speed=0.75)
            reset = store.reset()
        self.assertFalse(reset.touchpad_tap)
        self.assertEqual(reset.mouse_speed, 0.0)
