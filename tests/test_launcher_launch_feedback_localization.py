"""Language-neutral test of child-facing launch transition copy."""

from __future__ import annotations

import unittest

from greia_launcher.launch_feedback import launch_feedback


class LaunchFeedbackLocalizationTests(unittest.TestCase):
    def test_four_real_ui_languages_have_launch_and_wait_text(self) -> None:
        expected = {
            "en": ("Starting…", "Starting...", "Please wait…"),
            "it": ("Avvio…", "Avvio...", "Attendi…"),
            "es": ("Iniciando…", "Iniciando...", "Espera…"),
            "fr": ("Démarrage…", "Démarrage...", "Veuillez patienter…"),
        }
        for locale, texts in expected.items():
            with self.subTest(locale=locale):
                feedback = launch_feedback(locale)
                self.assertEqual((feedback.overlay, feedback.badge, feedback.wait), texts)

    def test_region_tags_and_legacy_language_fallback(self) -> None:
        self.assertEqual(launch_feedback("es-MX"), launch_feedback("es"))
        self.assertEqual(launch_feedback("fr_FR"), launch_feedback("fr"))
        self.assertEqual(launch_feedback("de"), launch_feedback("en"))
        self.assertEqual(launch_feedback(None), launch_feedback("en"))

    def test_feedback_does_not_mutate_session_or_device_locale(self) -> None:
        self.assertEqual(launch_feedback("it"), launch_feedback("it"))
        self.assertNotEqual(launch_feedback("fr").wait, launch_feedback("en").wait)


if __name__ == "__main__":
    unittest.main()
