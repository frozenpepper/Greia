from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from greia_platform.customization import ThemeStore
from greia_platform.profile_presentation import (
    GrammaticalGender,
    ProfilePresentation,
    ProfilePresentationError,
    ProfilePresentationStore,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProfilePresentationStoreTests(unittest.TestCase):
    def test_defaults_to_neutral_without_persisted_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = ProfilePresentationStore(Path(temporary))
            preferences = store.read()
            self.assertEqual(preferences.presentation, ProfilePresentation.NEUTRAL)
            self.assertEqual(
                preferences.grammatical_gender,
                GrammaticalGender.NEUTRAL,
            )

    def test_boy_and_girl_map_to_grammatical_agreement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = ProfilePresentationStore(Path(temporary))
            boy = store.set("boy")
            self.assertEqual(boy.grammatical_gender, GrammaticalGender.MASCULINE)
            girl = store.set("girl")
            self.assertEqual(girl.grammatical_gender, GrammaticalGender.FEMININE)
            self.assertEqual(store.read().presentation, ProfilePresentation.GIRL)

    def test_invalid_value_is_rejected_and_corrupt_file_fails_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = ProfilePresentationStore(root)
            with self.assertRaises(ProfilePresentationError):
                store.set("purple")
            store.path.write_text("{broken", encoding="utf-8")
            self.assertEqual(store.read().presentation, ProfilePresentation.NEUTRAL)
            store.path.write_text(
                json.dumps({"schema_version": 99, "presentation": "girl"}),
                encoding="utf-8",
            )
            self.assertEqual(store.read().presentation, ProfilePresentation.NEUTRAL)

    def test_starting_theme_is_seeded_once_and_never_overwrites_custom_theme(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            presentation = ProfilePresentationStore(root)
            theme = ThemeStore.load(
                PROJECT_ROOT / "runtime" / "theme-defaults.toml",
                root,
            )
            girl = presentation.set("girl")
            self.assertTrue(presentation.seed_theme_if_unset(theme, girl))
            self.assertEqual(theme.read_preferences().background, "lavender")
            self.assertEqual(theme.read_preferences().accent, "raspberry")
            self.assertEqual(theme.read_preferences().text, "plum")

            theme.set_colors(background="mint", accent="leaf", text="forest")
            boy = presentation.set("boy")
            self.assertFalse(presentation.seed_theme_if_unset(theme, boy))
            self.assertEqual(theme.read_preferences().background, "mint")
            self.assertEqual(theme.read_preferences().accent, "leaf")
            self.assertEqual(theme.read_preferences().text, "forest")

    def test_neutral_does_not_materialize_redundant_theme_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            presentation = ProfilePresentationStore(root)
            theme = ThemeStore.load(
                PROJECT_ROOT / "runtime" / "theme-defaults.toml",
                root,
            )
            neutral = presentation.set("neutral")
            self.assertFalse(presentation.seed_theme_if_unset(theme, neutral))
            self.assertFalse(theme.preferences_path.exists())


if __name__ == "__main__":
    unittest.main()
