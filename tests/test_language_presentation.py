from __future__ import annotations

import unittest

from greia_platform.language_presentation import (
    UiLanguageSelection,
    activity_language_badge,
    language_flag,
    supports_language_flag,
)
from greia_platform.localization import LocalizationError


class LanguageFlagTests(unittest.TestCase):
    def test_canonical_language_flags_use_selected_greia_convention(self) -> None:
        self.assertEqual(language_flag("en").asset_id, "flag.gb")
        self.assertEqual(language_flag("en-US").asset_id, "flag.gb")
        self.assertEqual(language_flag("es-MX").asset_id, "flag.es")
        self.assertEqual(language_flag("it-IT").asset_id, "flag.it")
        self.assertEqual(language_flag("pt-BR").asset_id, "flag.pt")

    def test_unknown_language_requires_explicit_platform_mapping(self) -> None:
        self.assertFalse(supports_language_flag("eo"))
        with self.assertRaises(LocalizationError):
            language_flag("eo")

    def test_dynamic_badge_tracks_actual_launch_language(self) -> None:
        fallback = activity_language_badge(
            profile_locale="it-IT",
            launch_locale="en",
        )
        self.assertEqual(fallback.flag.asset_id, "flag.gb")
        self.assertTrue(fallback.differs_from_profile)
        self.assertFalse(fallback.selectable)

        following = activity_language_badge(
            profile_locale="it-IT",
            launch_locale="it",
            selectable=True,
        )
        self.assertEqual(following.flag.asset_id, "flag.it")
        self.assertFalse(following.differs_from_profile)
        self.assertTrue(following.selectable)

    def test_language_initials_are_not_the_child_presentation_contract(self) -> None:
        # The renderer receives a semantic flag asset ID, never a two-letter
        # text badge as the primary child-facing language marker.
        flag = language_flag("en")
        self.assertTrue(flag.asset_id.startswith("flag."))
        self.assertNotEqual(flag.asset_id, "EN")
        self.assertEqual(UiLanguageSelection.PRELAUNCH_CHOOSER.value, "prelaunch_chooser")


if __name__ == "__main__":
    unittest.main()
