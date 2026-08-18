from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from greia_platform import activity_api
from greia_platform.customization import ThemeStore
from greia_platform.theme_snapshot import encode_theme_snapshot
from greia_platform.ui_preferences import InterfaceSize, UiPreferencesStore


ROOT = Path(__file__).resolve().parents[1]


def _clear_theme_caches() -> None:
    activity_api._root.cache_clear()
    activity_api._theme_store.cache_clear()
    activity_api._ui_preferences_store.cache_clear()
    activity_api._default_theme_store.cache_clear()


class ActivityThemeAccessTests(unittest.TestCase):
    def tearDown(self) -> None:
        _clear_theme_caches()

    def test_ordinary_activity_receives_canonical_default_without_launch_snapshot(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"GREIA_OS_ROOT": str(ROOT)},
            clear=False,
        ):
            os.environ.pop("GREIA_CUSTOMIZATION_DIR", None)
            os.environ.pop("GREIA_THEME_SNAPSHOT", None)
            os.environ.pop("GREIA_INTERFACE_SIZE", None)
            _clear_theme_caches()
            theme = activity_api.get_theme()
            preferences = activity_api.get_ui_preferences()

        self.assertEqual(theme.preferences.background, "cream")
        self.assertEqual(theme.preferences.accent, "sunshine")
        self.assertEqual(theme.preferences.text, "cocoa")
        self.assertEqual(theme.background, (247, 235, 203))
        self.assertEqual(theme.accent, (255, 194, 52))
        self.assertEqual(theme.text, (61, 44, 31))
        self.assertIsNone(theme.wallpaper_path)
        self.assertEqual(preferences.interface_size, InterfaceSize.NORMAL)

    def test_unprivileged_activity_does_not_read_profile_customization_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            (state / "theme.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "background": "lavender",
                        "accent": "grape",
                        "text": "plum",
                        "wallpaper_enabled": False,
                    }
                ),
                encoding="utf-8",
            )
            UiPreferencesStore(state).set_interface_size("large")
            with mock.patch.dict(
                os.environ,
                {"GREIA_OS_ROOT": str(ROOT)},
                clear=False,
            ):
                os.environ.pop("GREIA_CUSTOMIZATION_DIR", None)
                os.environ.pop("GREIA_THEME_SNAPSHOT", None)
                os.environ.pop("GREIA_INTERFACE_SIZE", None)
                _clear_theme_caches()
                theme = activity_api.get_theme()
                preferences = activity_api.get_ui_preferences()
            self.assertEqual(theme.preferences.background, "cream")
            self.assertEqual(theme.preferences.accent, "sunshine")
            self.assertEqual(theme.preferences.text, "cocoa")
            self.assertEqual(preferences.interface_size, InterfaceSize.NORMAL)

    def test_ordinary_activity_consumes_only_resolved_launch_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            store = ThemeStore.load(ROOT / "runtime" / "theme-defaults.toml", state)
            store.set_colors(background="lavender", accent="grape", text="plum")
            UiPreferencesStore(state).set_interface_size("large")
            snapshot = encode_theme_snapshot(store.resolve())
            with mock.patch.dict(
                os.environ,
                {
                    "GREIA_OS_ROOT": str(ROOT),
                    "GREIA_THEME_SNAPSHOT": snapshot,
                    "GREIA_INTERFACE_SIZE": "large",
                },
                clear=False,
            ):
                os.environ.pop("GREIA_CUSTOMIZATION_DIR", None)
                _clear_theme_caches()
                theme = activity_api.get_theme()
                preferences = activity_api.get_ui_preferences()
            self.assertEqual(theme.preferences.background, "lavender")
            self.assertEqual(theme.preferences.accent, "grape")
            self.assertEqual(theme.preferences.text, "plum")
            self.assertIsNone(theme.wallpaper_path)
            self.assertEqual(preferences.interface_size, InterfaceSize.LARGE)

    def test_trusted_customization_context_still_receives_profile_store_and_can_set_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            (state / "theme.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "background": "lavender",
                        "accent": "grape",
                        "text": "plum",
                        "wallpaper_enabled": False,
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {
                    "GREIA_OS_ROOT": str(ROOT),
                    "GREIA_CUSTOMIZATION_DIR": str(state),
                    "GREIA_ACTIVITY_CAPABILITIES": "customization.manage",
                },
                clear=False,
            ):
                _clear_theme_caches()
                theme = activity_api.get_theme()
                updated = activity_api.set_interface_size("compact")
                preferences = activity_api.get_ui_preferences()
            self.assertEqual(theme.preferences.background, "lavender")
            self.assertEqual(theme.preferences.accent, "grape")
            self.assertEqual(theme.preferences.text, "plum")
            self.assertEqual(updated.interface_size, InterfaceSize.COMPACT)
            self.assertEqual(preferences.interface_size, InterfaceSize.COMPACT)


if __name__ == "__main__":
    unittest.main()
