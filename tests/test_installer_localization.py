from __future__ import annotations

import unittest
from pathlib import Path

from greia_installer.i18n import InstallerTranslator, LocalizedFont, _ITALIAN
from greia_installer.i18n_es_fr import FRENCH, SPANISH
from greia_platform.system_language import SUPPORTED_SYSTEM_LANGUAGES


ROOT = Path(__file__).resolve().parents[1]


class _FakeFont:
    def __init__(self) -> None:
        self.last_text = ""

    def render(self, text: str, *args: object, **kwargs: object) -> str:
        self.last_text = text
        return text

    def get_height(self) -> int:
        return 42


class InstallerLocalizationTests(unittest.TestCase):
    def test_italian_translates_core_installer_copy(self) -> None:
        translator = InstallerTranslator("it")
        self.assertEqual(translator.text("Start"), "Inizia")
        self.assertEqual(translator.text("Continue"), "Continua")
        self.assertEqual(translator.text("Back"), "Indietro")
        self.assertEqual(
            translator.text("Choose the internal disk"),
            "Scegli il disco interno",
        )
        self.assertEqual(
            translator.text("Everything currently on this disk will be erased."),
            "Tutto ciò che si trova su questo disco verrà cancellato.",
        )
        self.assertEqual(
            translator.text("Greia is installed and ready."),
            "Greia è installato e pronto.",
        )

    def test_dynamic_copy_preserves_machine_or_probe_data(self) -> None:
        translator = InstallerTranslator("it")
        self.assertEqual(
            translator.text("Press the key that types “/”"),
            "Premi il tasto che scrive “/”",
        )
        self.assertEqual(
            translator.text("Connecting to Casa…"),
            "Connessione a Casa…",
        )
        self.assertEqual(
            translator.text("Connected to Casa"),
            "Connesso a Casa",
        )
        self.assertEqual(translator.text("3 of 6 pressed"), "3 di 6 premuti")
        self.assertEqual(
            translator.text("After 2 more keys I'll show a list to confirm."),
            "Dopo altri 2 tasti mostrerò un elenco da confermare.",
        )
        # An SSID-bearing status line is intentionally not semantically parsed.
        self.assertEqual(translator.text("Wi-Fi: Casa"), "Wi-Fi: Casa")

    def test_released_four_language_translations_are_selectable(self) -> None:
        self.assertTrue({"en", "it", "es", "fr"}.issubset(
            {item.locale for item in SUPPORTED_SYSTEM_LANGUAGES}
        ))
        self.assertEqual(InstallerTranslator("es").text("Continue"), "Continuar")
        self.assertEqual(InstallerTranslator("fr").text("Continue"), "Continuer")
        self.assertEqual(InstallerTranslator("es-ES").text("Start"), "Empezar")
        self.assertEqual(InstallerTranslator("fr-FR").text("Start"), "Commencer")
        for locale in ("en", "zz", "xx-NOPE"):
            with self.subTest(locale=locale):
                self.assertEqual(InstallerTranslator(locale).text("Continue"), "Continue")

    def test_installer_catalogue_key_parity_and_destructive_warning(self) -> None:
        self.assertEqual(set(SPANISH), set(_ITALIAN))
        self.assertEqual(set(FRENCH), set(_ITALIAN))
        for locale in ("es", "fr"):
            with self.subTest(locale=locale):
                translator = InstallerTranslator(locale)
                for source in ("Hold to erase and install", "Everything currently on this disk will be erased.",
                               "installation payload is damaged; the disk was not changed",
                               "selected disk identity changed; installation stopped"):
                    self.assertNotEqual(translator.text(source), source)

    def test_spanish_and_french_preserve_dynamic_data(self) -> None:
        for locale, expected_key, expected_battery in (
            ("es", "Pulsa la tecla que escribe “/”", "batería al 30%"),
            ("fr", "Appuyez sur la touche qui écrit « / »", "batterie à 30 %"),
        ):
            with self.subTest(locale=locale):
                translator = InstallerTranslator(locale)
                self.assertEqual(translator.text("Press the key that types “/”"), expected_key)
                self.assertIn("Casa", translator.text("Connecting to Casa…"))
                self.assertIn("Casa", translator.text("Connected to Casa"))
                self.assertEqual(translator.text("Wi-Fi: Casa"), "Wi-Fi: Casa")
                self.assertIn(expected_battery, translator.text(
                    "Connect the power adapter before installing (battery is 30%)."
                ))
                self.assertEqual(translator.text("Disk: /dev/sda"), "Disk: /dev/sda")

    def test_font_proxy_translates_without_changing_font_metrics_api(self) -> None:
        base = _FakeFont()
        localized = LocalizedFont(base, InstallerTranslator("it"))
        self.assertEqual(localized.render("Installing", True, (0, 0, 0)), "Installazione in corso")
        self.assertEqual(base.last_text, "Installazione in corso")
        self.assertEqual(localized.get_height(), 42)

    def test_language_first_screen_uses_greia_pointer_and_localized_typography(self) -> None:
        source = (ROOT / "src/greia_installer/entrypoint.py").read_text(encoding="utf-8")
        self.assertIn("LocalizedTypography", source)
        self.assertIn("pygame.mouse.set_visible(False)", source)
        self.assertIn("_load_pointer", source)
        self.assertIn("_draw_pointer", source)
        self.assertIn("yellow_star.png", source)
        self.assertIn("pygame.mouse.get_pos()", source)
        self.assertIn("hovered = cell.collidepoint(pointer_position)", source)
        # Step 8A.5 split: the language-first selection reaches the install
        # through the transaction settings snapshot, not a direct request.
        self.assertIn("def _snapshot_locale", source)
        self.assertIn("return self.locale", source)


if __name__ == "__main__":
    unittest.main()
