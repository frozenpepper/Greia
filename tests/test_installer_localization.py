from __future__ import annotations

import unittest
from pathlib import Path

from greia_installer.i18n import InstallerTranslator, LocalizedFont


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

    def test_other_selectable_locales_fall_back_honestly_to_english_copy(self) -> None:
        for locale in ("en", "es", "de", "fr", "zh-CN", "ar", "hi", "bn", "sw"):
            with self.subTest(locale=locale):
                self.assertEqual(InstallerTranslator(locale).text("Continue"), "Continue")

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
