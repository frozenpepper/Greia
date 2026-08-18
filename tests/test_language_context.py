from __future__ import annotations

import unittest

from greia_platform.language_context import (
    ActivityContentLanguageSupport,
    ActivityLanguagePolicy,
    ChildLanguageContext,
    resolve_activity_launch_languages,
)
from greia_platform.language_presentation import UiLanguageSelection
from greia_platform.localization import LocalizationError


class ChildLanguageContextTests(unittest.TestCase):
    def test_profile_override_wins_over_device_default(self) -> None:
        inherited = ChildLanguageContext.resolve("it-IT")
        self.assertEqual(inherited.ui_locale.value, "it-IT")

        overridden = ChildLanguageContext.resolve("it-IT", "en-GB")
        self.assertEqual(overridden.device_default.value, "it-IT")
        self.assertEqual(overridden.profile_override.value, "en-GB")
        self.assertEqual(overridden.ui_locale.value, "en-GB")


class ActivityLaunchLanguageTests(unittest.TestCase):
    def test_english_only_activity_on_italian_profile_keeps_italian_catalogue_title(self) -> None:
        child = ChildLanguageContext.resolve("it-IT")
        policy = ActivityLanguagePolicy.localized(
            catalogue_locales=("en", "it"),
            default_catalogue_locale="en",
            ui_locales=("en",),
            default_ui_locale="en",
        )
        launch = resolve_activity_launch_languages(child, policy)
        self.assertEqual(launch.catalogue_locale.value, "it")
        assert launch.ui_locale is not None
        self.assertEqual(launch.ui_locale.selected.value, "en")
        self.assertTrue(launch.activity_ui_differs_from_child)

    def test_multilingual_activity_follows_child_profile(self) -> None:
        policy = ActivityLanguagePolicy.localized(
            catalogue_locales=("en", "it"),
            default_catalogue_locale="en",
            ui_locales=("en", "it"),
            default_ui_locale="en",
        )
        italian = resolve_activity_launch_languages(
            ChildLanguageContext.resolve("it-IT"),
            policy,
        )
        english = resolve_activity_launch_languages(
            ChildLanguageContext.resolve("en-GB"),
            policy,
        )
        assert italian.ui_locale is not None and english.ui_locale is not None
        self.assertEqual(italian.ui_locale.selected.value, "it")
        self.assertEqual(english.ui_locale.selected.value, "en")

    def test_opt_in_prelaunch_ui_choice_can_override_profile_for_one_launch(self) -> None:
        policy = ActivityLanguagePolicy.localized(
            catalogue_locales=("en", "it"),
            default_catalogue_locale="en",
            ui_locales=("en", "it"),
            default_ui_locale="en",
            ui_selection=UiLanguageSelection.PRELAUNCH_CHOOSER,
        )
        launch = resolve_activity_launch_languages(
            ChildLanguageContext.resolve("it-IT"),
            policy,
            ui_choice="en",
        )
        assert launch.ui_locale is not None
        self.assertEqual(launch.ui_locale.selected.value, "en")
        self.assertTrue(launch.activity_ui_differs_from_child)

    def test_non_selectable_activity_rejects_explicit_ui_choice(self) -> None:
        policy = ActivityLanguagePolicy.localized(
            catalogue_locales=("en", "it"),
            default_catalogue_locale="en",
            ui_locales=("en", "it"),
            default_ui_locale="en",
        )
        with self.assertRaises(LocalizationError):
            resolve_activity_launch_languages(
                ChildLanguageContext.resolve("it"),
                policy,
                ui_choice="en",
            )

    def test_language_neutral_ui_can_still_have_selectable_content_language(self) -> None:
        policy = ActivityLanguagePolicy.language_neutral(
            catalogue_locales=("en", "it"),
            default_catalogue_locale="en",
            content=ActivityContentLanguageSupport.selectable(
                ("it", "en"),
                default_locale="it",
            ),
        )
        launch = resolve_activity_launch_languages(
            ChildLanguageContext.resolve("it-IT"),
            policy,
            content_choice="en",
        )
        self.assertIsNone(launch.ui_locale)
        self.assertEqual(launch.catalogue_locale.value, "it")
        assert launch.content_locale is not None
        self.assertEqual(launch.content_locale.value, "en")

    def test_fixed_content_language_cannot_be_overridden(self) -> None:
        policy = ActivityLanguagePolicy.language_neutral(
            catalogue_locales=("it",),
            default_catalogue_locale="it",
            content=ActivityContentLanguageSupport.fixed("en"),
        )
        launch = resolve_activity_launch_languages(
            ChildLanguageContext.resolve("it"),
            policy,
        )
        assert launch.content_locale is not None
        self.assertEqual(launch.content_locale.value, "en")
        with self.assertRaises(LocalizationError):
            resolve_activity_launch_languages(
                ChildLanguageContext.resolve("it"),
                policy,
                content_choice="it",
            )

    def test_prelaunch_chooser_requires_multiple_ui_locales(self) -> None:
        with self.assertRaises(LocalizationError):
            ActivityLanguagePolicy.localized(
                catalogue_locales=("en",),
                default_catalogue_locale="en",
                ui_locales=("en",),
                default_ui_locale="en",
                ui_selection=UiLanguageSelection.PRELAUNCH_CHOOSER,
            )


if __name__ == "__main__":
    unittest.main()
