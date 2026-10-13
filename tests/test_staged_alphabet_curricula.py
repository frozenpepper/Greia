"""Source-only staged Spanish/French alphabet curriculum, including Ñ."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "activities" / "alfabeto_leo"))

from alfabeto_model import (  # noqa: E402
    LETTERS_CATALOGUE, AlfabetoModel, GameMode, get_letter_catalogue,
)


class StagedAlphabetCurriculumTests(unittest.TestCase):
    def test_existing_en_it_alphabet_and_examples_unchanged(self) -> None:
        expected = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for locale in ("it", "en-GB"):
            with self.subTest(locale=locale):
                letters = get_letter_catalogue(locale)
                self.assertEqual("".join(item.char for item in letters), expected)
                self.assertEqual(letters, tuple(LETTERS_CATALOGUE))
        self.assertEqual(LETTERS_CATALOGUE[0].word_for("it"), "APE")
        self.assertEqual(LETTERS_CATALOGUE[0].word_for("en"), "APPLE")

    def test_spanish_alphabet_has_27_real_learning_letters(self) -> None:
        letters = get_letter_catalogue("es-ES")
        self.assertEqual("".join(item.char for item in letters), "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ")
        self.assertEqual(len(letters), 27)
        self.assertEqual(len({i.char for i in letters}), 27)
        self.assertEqual(letters[14].word_for("es-MX"), "ÑANDÚ")
        for item in letters:
            self.assertTrue(item.word_for("es").startswith(item.char))
            self.assertTrue(item.symbol_for("es"))
        with self.assertRaises(ValueError):
            letters[14].word_for("en")

    def test_french_alphabet_preserves_accents_in_example_words(self) -> None:
        letters = get_letter_catalogue("fr_FR")
        self.assertEqual(len(letters), 26)
        self.assertEqual(letters[21].word_for("fr-FR"), "VÉLO")
        for item in letters:
            self.assertTrue(item.word_for("fr").startswith(item.char))
            self.assertTrue(item.symbol_for("fr"))
        with self.assertRaises(ValueError):
            get_letter_catalogue("zh-CN")

    def test_spanish_navigation_guessing_and_parade_include_enye(self) -> None:
        model = AlfabetoModel(locale="es")
        self.assertTrue(model.select_letter("Ñ"))
        self.assertEqual(model.current_index, 14)
        self.assertEqual(model.active_letter.char, "Ñ")
        self.assertEqual(model.step(1).char, "O")
        self.assertEqual(model.step(-1).char, "Ñ")
        model.switch_mode(GameMode.GUESS)
        self.assertEqual(len(model.guess_choices), 3)
        for item in model.letters:
            model.select_letter(item.char)
        events = model.update(0.02)
        self.assertEqual(events.count("alphabet.parade_completed"), 1)
        self.assertEqual(len(model.discovered_letters), 27)
        self.assertEqual(model.update(0.02), [])
        reloaded = AlfabetoModel(locale="es")
        reloaded.restore_discoveries(model.discovered_letters)
        self.assertEqual(reloaded.update(0.02), [])
        self.assertEqual(len(reloaded.discovered_letters), 27)
        italian = AlfabetoModel(locale="it")
        italian.restore_discoveries({"Ñ", "A", "B"})
        self.assertNotIn("Ñ", italian.discovered_letters)

    def test_activity_stays_two_language_until_voice_approved(self) -> None:
        import tomllib
        manifest = tomllib.loads(
            (ROOT / "activities/alfabeto_leo/activity.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])


if __name__ == "__main__":
    unittest.main()
