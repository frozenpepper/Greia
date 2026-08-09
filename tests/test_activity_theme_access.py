from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from greia_platform import activity_api


ROOT = Path(__file__).resolve().parents[1]


def _clear_theme_caches() -> None:
    activity_api._root.cache_clear()
    activity_api._theme_store.cache_clear()
    activity_api._default_theme_store.cache_clear()


class ActivityThemeAccessTests(unittest.TestCase):
    def tearDown(self) -> None:
        _clear_theme_caches()

    def test_ordinary_activity_receives_canonical_default_without_manage_permission(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"GREIA_OS_ROOT": str(ROOT)},
            clear=False,
        ):
            os.environ.pop("GREIA_CUSTOMIZATION_DIR", None)
            _clear_theme_caches()
            theme = activity_api.get_theme()

        self.assertEqual(theme.preferences.background, "cream")
        self.assertEqual(theme.preferences.accent, "sunshine")
        self.assertEqual(theme.preferences.text, "cocoa")
        self.assertEqual(theme.background, (247, 235, 203))
        self.assertEqual(theme.accent, (255, 194, 52))
        self.assertEqual(theme.text, (61, 44, 31))
        self.assertIsNone(theme.wallpaper_path)

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
            with mock.patch.dict(
                os.environ,
                {"GREIA_OS_ROOT": str(ROOT)},
                clear=False,
            ):
                os.environ.pop("GREIA_CUSTOMIZATION_DIR", None)
                _clear_theme_caches()
                theme = activity_api.get_theme()
            self.assertEqual(theme.preferences.background, "cream")
            self.assertEqual(theme.preferences.accent, "sunshine")
            self.assertEqual(theme.preferences.text, "cocoa")

    def test_trusted_customization_context_still_receives_resolved_profile_theme(self) -> None:
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
                },
                clear=False,
            ):
                _clear_theme_caches()
                theme = activity_api.get_theme()
            self.assertEqual(theme.preferences.background, "lavender")
            self.assertEqual(theme.preferences.accent, "grape")
            self.assertEqual(theme.preferences.text, "plum")


if __name__ == "__main__":
    unittest.main()
