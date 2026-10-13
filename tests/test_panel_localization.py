"""Locale-safe Parent overlay text without a display or cloud provider."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from greia_launcher.panel_localization import (
    LOCALES, _MESSAGES, audit_panel_messages, panel_message,
    panel_constant, panel_audio_preset, audit_panel_constants, _FORM_TRANSLATIONS,
)
from greia_launcher.parent_panel import ParentSettingsOverlay
from greia_platform.system_language import SUPPORTED_SYSTEM_LANGUAGES


class ParentPanelTextTests(unittest.TestCase):
    def test_all_semantic_keys_and_variables_have_four_language_parity(self) -> None:
        self.assertEqual(LOCALES, ("en", "it", "es", "fr"))
        self.assertEqual(audit_panel_messages(), [])
        self.assertGreaterEqual(len(_MESSAGES), 20)
        for key in _MESSAGES:
            for locale in LOCALES:
                self.assertTrue(panel_message(
                    key, locale, **(
                        {"name": "Italiano"} if key == "language.changed"
                        else {"detail": "read-only"} if key == "language.failed"
                        else {}
                    ),
                ))

    def test_named_parent_form_constants_cover_all_four_languages(self) -> None:
        from greia_launcher import panel_strings
        self.assertEqual(audit_panel_constants(), [])
        self.assertGreaterEqual(len(_FORM_TRANSLATIONS), 48)
        for name in _FORM_TRANSLATIONS:
            english = getattr(panel_strings, name)
            self.assertEqual(panel_constant(name, "en", **(
                {"count": "7"} if "{count}" in english else {}
            )), english.format(**({"count": "7"} if "{count}" in english else {})))
            for locale in LOCALES:
                translated = panel_constant(name, locale, **(
                    {"count": "7"} if "{count}" in english else {}
                ))
                self.assertIsInstance(translated, str)
                self.assertTrue(translated.strip())

    def test_parent_account_deletion_and_security_warnings_do_not_fall_back(self) -> None:
        from greia_launcher import panel_strings
        for name in (
            "ACCOUNTS_INTRO", "ACCOUNTS_CONFIRM_REMOVE_TITLE",
            "ACCOUNTS_CONFIRM_REMOVE_BODY", "ACCOUNTS_CONFIRM_REMOVE_YES",
            "SECURITY_INTRO", "SECURITY_MISMATCH", "SECURITY_CURRENT_WRONG",
        ):
            for locale in ("it", "es", "fr"):
                with self.subTest(name=name, locale=locale):
                    self.assertNotEqual(panel_constant(name, locale), getattr(panel_strings, name))

    def test_parent_audio_presets_follow_display_locale_not_gain(self) -> None:
        from greia_launcher import panel_strings
        for gain in (1.0, 1.5, 2.0, 3.0, 4.0):
            self.assertEqual(panel_audio_preset(gain, "en"), panel_strings.AUDIO_PRESET_NAMES[gain])
            self.assertTrue(panel_audio_preset(gain, "it"))
            self.assertTrue(panel_audio_preset(gain, "es"))
            self.assertTrue(panel_audio_preset(gain, "fr"))
        self.assertEqual(panel_audio_preset(4.0, "fr"), "Maximum")
        self.assertEqual(panel_constant("AUDIO_LEVEL_LABEL", "es"), "Nivel")

    def test_form_dynamic_variables_are_explicit_not_translated(self) -> None:
        self.assertIn("7", panel_constant("ACCOUNTS_LIMIT_REACHED", "fr", count="7"))
        with self.assertRaises(ValueError):
            panel_constant("ACCOUNTS_LIMIT_REACHED", "fr")
        with self.assertRaises(ValueError):
            panel_constant("STATUS_SAVED", "it", count="7")
        with self.assertRaises(KeyError):
            panel_constant("UNOWNED_TEXT", "it")

    def test_english_and_italian_settings_have_distinct_copy(self) -> None:
        self.assertEqual(panel_message("parent.title", "en"), "Parent Settings")
        self.assertEqual(panel_message("parent.title", "it"), "Impostazioni genitori")
        self.assertEqual(panel_message("tab.language", "it"), "Lingua")
        self.assertEqual(panel_message("auth.unlock", "es"), "Desbloquear")
        self.assertEqual(panel_message("auth.unlock", "fr"), "Déverrouiller")
        self.assertEqual(panel_message("language.option.it", "fr"), "Italien")
        self.assertEqual(panel_message("tab.wifi", "it"), "Wi-Fi")

    def test_unsupported_and_malformed_locale_fallback_only_in_ui_copy(self) -> None:
        self.assertEqual(panel_message("tab.audio", "zh-CN"), "Audio & Mic")
        self.assertEqual(panel_message("tab.audio", "invalid_/locale"), "Audio & Mic")
        self.assertEqual(panel_message("tab.audio", "it-IT"), "Audio e microfono")

    def test_only_semantic_keys_and_exact_placeholders_are_accepted(self) -> None:
        with self.assertRaises(KeyError):
            panel_message("child.name", "en")
        with self.assertRaises(ValueError):
            panel_message("language.changed", "it")
        with self.assertRaises(ValueError):
            panel_message("auth.cancel", "en", name="untrusted")

    def test_dynamic_values_are_kept_verbatim_and_not_interpreted(self) -> None:
        name = "A{B} & casa"
        self.assertIn(name, panel_message("language.changed", "es", name=name))
        self.assertIn("error: /readonly", panel_message(
            "language.failed", "fr", detail="error: /readonly"
        ))

    def test_all_visible_parent_tabs_use_semantic_copy(self) -> None:
        from greia_launcher import panel_strings
        self.assertEqual(
            {f"tab.{tab}" for _label, tab in panel_strings.TABS},
            {key for key in _MESSAGES if key.startswith("tab.")},
        )


class _FakeLanguage:
    def __init__(self, locale: str = "en") -> None:
        self.locale = locale

    def read(self) -> SimpleNamespace:
        return SimpleNamespace(locale=self.locale)

    def set(self, locale: str) -> SimpleNamespace:
        if locale not in {item.locale for item in SUPPORTED_SYSTEM_LANGUAGES}:
            raise ValueError("unsupported")
        self.locale = locale
        return self.read()


class ParentPanelLocaleStateTests(unittest.TestCase):
    def _overlay(self, initial: str = "en") -> ParentSettingsOverlay:
        panel = ParentSettingsOverlay.__new__(ParentSettingsOverlay)
        panel.language_service = _FakeLanguage(initial)
        panel._language_index = 0
        panel._device_locale = "en"
        panel._language_message = ""
        panel._language_message_is_error = False
        return panel

    def test_device_locale_reloads_without_profile_locale_guess(self) -> None:
        panel = self._overlay("it")
        panel._sync_language_selection()
        self.assertEqual(panel._device_locale, "it")
        self.assertEqual(panel._language_index, 1)
        self.assertEqual(panel._ui_message("auth.prompt"), "Inserisci la password genitore")

    def test_after_parent_change_cache_identity_and_confirmation_follow_locale(self) -> None:
        panel = self._overlay()
        panel._sync_language_selection()
        before = panel._composite_key("underlay", (1024, 600))
        panel._apply_language(1)
        after = panel._composite_key("underlay", (1024, 600))
        self.assertNotEqual(before, after)
        self.assertEqual(panel._device_locale, "it")
        self.assertEqual(panel._language_index, 1)
        self.assertEqual(panel._language_message, "Lingua impostata: Italiano.")
        self.assertFalse(panel._language_message_is_error)

    def test_failed_language_change_does_not_change_selected_locale(self) -> None:
        panel = self._overlay("it")
        panel._sync_language_selection()
        panel._apply_language(999)
        self.assertEqual(panel._device_locale, "it")
        self.assertTrue(panel._language_message_is_error)
        self.assertTrue(panel._language_message.startswith("Impossibile cambiare lingua:"))

    def test_staged_french_and_spanish_are_not_advertised(self) -> None:
        self.assertEqual(tuple(x.locale for x in SUPPORTED_SYSTEM_LANGUAGES), ("en", "it"))
        panel = self._overlay("fr")
        panel._sync_language_selection()
        # A test/prototype can preview staged strings without extending the
        # product registry or introducing new Parent API mutations.
        self.assertEqual(panel._ui_message("language.title"), "Langue de Greia")
        self.assertEqual(panel._language_index, 0)


if __name__ == "__main__":
    unittest.main()
