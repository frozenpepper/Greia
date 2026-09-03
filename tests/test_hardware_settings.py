from __future__ import annotations

import json
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

    def test_default_disables_touchpad_tap_and_reports_v2(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            settings = store.read()
        self.assertEqual(settings.schema_version, 2)
        self.assertFalse(settings.touchpad_tap)
        self.assertFalse(settings.disable_while_typing)
        self.assertEqual(settings.resolution, "auto")
        self.assertEqual(settings.keyboard_layout, "us")
        self.assertEqual(settings.mic_gain, 2.0)
        self.assertEqual(store.default_settings(), settings)

    def test_runtime_toml_and_default_safe_agree(self) -> None:
        safe = HardwareDefaults.default_safe()
        self.assertEqual(safe.schema_version, 2)
        self.assertFalse(safe.touchpad_tap)
        self.assertFalse(safe.disable_while_typing)
        loaded = HardwareDefaults.load(
            PROJECT_ROOT / "runtime" / "hardware-settings.toml"
        )
        self.assertEqual(loaded.schema_version, 2)
        self.assertFalse(loaded.touchpad_tap)
        self.assertFalse(loaded.disable_while_typing)
        self.assertEqual(loaded.schema_version, safe.schema_version)
        self.assertEqual(loaded.touchpad_tap, safe.touchpad_tap)
        self.assertEqual(
            loaded.disable_while_typing, safe.disable_while_typing
        )
        toml_text = (
            PROJECT_ROOT / "runtime" / "hardware-settings.toml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("touchpad_tap = true", toml_text)
        self.assertIn("schema_version = 2", toml_text)
        self.assertIn("disable_while_typing", toml_text)

    def test_v1_payload_migrates_without_losing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            store.settings_path.parent.mkdir(parents=True, exist_ok=True)
            store.settings_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "touchpad_tap": True,
                        "touchpad_speed": -0.25,
                        "mouse_speed": 0.75,
                        "natural_scrolling": True,
                        "resolution": "1024x600",
                        "keyboard_layout": "de",
                        "mic_gain": 3.0,
                    }
                ),
                encoding="utf-8",
            )
            migrated = store.read()
        # Stored parent choices survive migration; they are not reset.
        self.assertEqual(migrated.schema_version, 2)
        self.assertTrue(migrated.touchpad_tap)
        self.assertEqual(migrated.touchpad_speed, -0.25)
        self.assertEqual(migrated.mouse_speed, 0.75)
        self.assertTrue(migrated.natural_scrolling)
        self.assertEqual(migrated.resolution, "1024x600")
        self.assertEqual(migrated.keyboard_layout, "de")
        self.assertEqual(migrated.mic_gain, 3.0)
        # New field defaults to False for migrated installs.
        self.assertFalse(migrated.disable_while_typing)

    def test_v1_minimal_payload_migrates_with_new_field_false(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            store.settings_path.parent.mkdir(parents=True, exist_ok=True)
            store.settings_path.write_text(
                json.dumps({"schema_version": 1}),
                encoding="utf-8",
            )
            migrated = store.read()
        self.assertEqual(migrated.schema_version, 2)
        self.assertFalse(migrated.disable_while_typing)
        self.assertEqual(migrated, store.default_settings())

    def test_invalid_v2_data_fails_soft_to_defaults(self) -> None:
        invalid_payloads = [
            {
                "schema_version": 2,
                "touchpad_tap": "yes",
                "touchpad_speed": 0.0,
                "mouse_speed": 0.0,
                "natural_scrolling": False,
                "resolution": "auto",
                "keyboard_layout": "us",
                "mic_gain": 2.0,
                "disable_while_typing": False,
            },
            {
                "schema_version": 2,
                "touchpad_tap": False,
                "touchpad_speed": 99.0,
                "mouse_speed": 0.0,
                "natural_scrolling": False,
                "resolution": "auto",
                "keyboard_layout": "us",
                "mic_gain": 2.0,
                "disable_while_typing": False,
            },
            {
                "schema_version": 2,
                "touchpad_tap": False,
                "touchpad_speed": 0.0,
                "mouse_speed": 0.0,
                "natural_scrolling": False,
                "resolution": "auto",
                "keyboard_layout": "us",
                "mic_gain": 2.0,
                "disable_while_typing": "never",
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    store = self.make_store(root)
                    store.settings_path.parent.mkdir(
                        parents=True, exist_ok=True
                    )
                    store.settings_path.write_text(
                        json.dumps(payload), encoding="utf-8"
                    )
                    reread = store.read()
                self.assertEqual(reread, store.default_settings())
                self.assertEqual(reread.schema_version, 2)
                self.assertFalse(reread.touchpad_tap)
                self.assertFalse(reread.disable_while_typing)

    def test_unknown_schema_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            store.settings_path.parent.mkdir(parents=True, exist_ok=True)
            store.settings_path.write_text(
                json.dumps(
                    {
                        "schema_version": 99,
                        "touchpad_tap": True,
                        "touchpad_speed": 0.5,
                        "mouse_speed": 0.5,
                        "natural_scrolling": True,
                        "resolution": "1024x600",
                        "keyboard_layout": "de",
                        "mic_gain": 3.0,
                        "disable_while_typing": True,
                    }
                ),
                encoding="utf-8",
            )
            reread = store.read()
        self.assertEqual(reread, store.default_settings())

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
            self.assertEqual(defaults.schema_version, 2)
            self.assertFalse(defaults.touchpad_tap)
            self.assertFalse(defaults.disable_while_typing)
            self.assertEqual(defaults.keyboard_layout, "us")
            self.assertEqual(defaults.mic_gain, 2.0)

    def test_parent_update_is_atomic_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            updated = store.update(
                touchpad_tap=True,
                mouse_speed=0.5,
                touchpad_speed=-0.25,
                natural_scrolling=True,
                resolution="1024x600",
                mic_gain=2.5,
                disable_while_typing=True,
                allowed_resolutions=("800x600", "1024x600"),
            )
            reread = store.read()
            raw_text = store.settings_path.read_text(encoding="utf-8")
            leftovers = list(root.glob("*.tmp")) + list(
                root.glob(".*.tmp")
            )
        self.assertEqual(updated, reread)
        self.assertTrue(reread.touchpad_tap)
        self.assertTrue(reread.disable_while_typing)
        self.assertEqual(reread.mouse_speed, 0.5)
        self.assertEqual(reread.mic_gain, 2.5)
        payload = json.loads(raw_text)
        self.assertIn("disable_while_typing", payload)
        self.assertTrue(payload["disable_while_typing"])
        self.assertEqual(leftovers, [])

    def test_disable_while_typing_strict_bool(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            updated = store.update(disable_while_typing=True)
            self.assertTrue(updated.disable_while_typing)
            self.assertTrue(store.read().disable_while_typing)
            with self.assertRaises(HardwareSettingsError):
                store.update(disable_while_typing="yes")  # type: ignore[arg-type]

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

    def test_reset_restores_canonical_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            store.update(
                touchpad_tap=True,
                mouse_speed=0.75,
                mic_gain=3.5,
                disable_while_typing=True,
            )
            reset = store.reset()
            reread = store.read()
        canonical = store.default_settings()
        self.assertEqual(reset, canonical)
        self.assertEqual(reread, canonical)
        self.assertEqual(reset.schema_version, 2)
        self.assertFalse(reset.touchpad_tap)
        self.assertFalse(reset.disable_while_typing)
        self.assertEqual(reset.mic_gain, 2.0)
        # TOML-derived mouse default is 0.5 in the shipped runtime file.
        self.assertEqual(reset.mouse_speed, canonical.mouse_speed)

    def test_no_tap_true_default_authority(self) -> None:
        self.assertFalse(HardwareDefaults.default_safe().touchpad_tap)
        toml_text = (
            PROJECT_ROOT / "runtime" / "hardware-settings.toml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("touchpad_tap = true", toml_text)
        source = (
            PROJECT_ROOT / "src" / "greia_platform" / "hardware.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("touchpad_tap=True", source)
        self.assertNotIn('touchpad_tap", True', source)
