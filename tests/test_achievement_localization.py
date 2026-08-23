from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_launcher.achievement_localization import (
    achievement_ui_strings,
    missing_supported_locales,
    resolve_achievement_locale,
)


class AchievementLocalizationTests(unittest.TestCase):
    def test_simulator_explicit_italian_wins_over_empty_system_store(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = {
                "GREIA_PROFILE_LOCALE": "it",
                "GREIA_DEVICE_LOCALE": "it",
                "GREIA_SYSTEM_SETTINGS_DIR": str(root / "system-settings"),
                "GREIA_INSTALL_RECORD": str(root / "missing-install-record.json"),
            }
            with patch.dict(os.environ, environment, clear=False):
                self.assertEqual(resolve_achievement_locale(), "it")

    def test_profile_locale_has_priority_over_device_locale(self) -> None:
        with patch.dict(
            os.environ,
            {"GREIA_PROFILE_LOCALE": "it", "GREIA_DEVICE_LOCALE": "en"},
            clear=False,
        ):
            self.assertEqual(resolve_achievement_locale(), "it")

    def test_all_supported_system_languages_have_badge_library_chrome(self) -> None:
        self.assertEqual(missing_supported_locales(), ())

    def test_italian_library_chrome_is_not_english(self) -> None:
        copy = achievement_ui_strings("it")
        self.assertEqual(copy.library_title, "I MIEI DISTINTIVI")
        self.assertEqual(copy.new_label, "NUOVO")
        self.assertEqual(copy.new_badge, "NUOVO DISTINTIVO!")
        self.assertNotIn("MY BADGES", copy.library_title)

    def test_non_italian_language_is_not_forced_to_english(self) -> None:
        spanish = achievement_ui_strings("es")
        self.assertEqual(spanish.library_title, "MIS INSIGNIAS")
        self.assertEqual(spanish.new_label, "NUEVO")
        self.assertNotEqual(spanish.library_title, achievement_ui_strings("en").library_title)

    def test_unknown_locale_fails_soft_to_english(self) -> None:
        self.assertEqual(
            achievement_ui_strings("xx-invalid"),
            achievement_ui_strings("en"),
        )


if __name__ == "__main__":
    unittest.main()
