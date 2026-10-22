import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from greia_voice_core.number_comparison import canonical_number_tokens, same_number_aware_text

# Independent test fixtures (not imported from implementation tables).
SPELLED = {
    "en": ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "twenty-one", "twenty-two", "twenty-three", "twenty-four", "twenty-five"),
    "it": ("zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove", "dieci", "undici", "dodici", "tredici", "quattordici", "quindici", "sedici", "diciassette", "diciotto", "diciannove", "venti", "ventuno", "ventidue", "ventitré", "ventiquattro", "venticinque"),
    "fr": ("zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf", "vingt", "vingt et un", "vingt-deux", "vingt-trois", "vingt-quatre", "vingt-cinq"),
    "es": ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco"),
}

class NumberTokenTests(unittest.TestCase):
    def test_all_26_digit_spelling_vectors_in_four_locales(self):
        self.assertEqual(sum(len(forms) for forms in SPELLED.values()), 104)
        for locale, forms in SPELLED.items():
            for value, spelling in enumerate(forms):
                with self.subTest(locale=locale, value=value):
                    self.assertEqual(canonical_number_tokens(locale, str(value)), (f"<num:{value}>",))
                    self.assertTrue(same_number_aware_text(locale, str(value), spelling))

    def test_requested_actual_space_separated_examples(self):
        self.assertTrue(same_number_aware_text("en", "The ten house", "the 10 house"))
        self.assertTrue(same_number_aware_text("es", "La casa del diez", "la casa del 10"))

    def test_wrong_number_missing_number_and_extra_word_fail(self):
        self.assertFalse(same_number_aware_text("en", "17", "18"))
        self.assertFalse(same_number_aware_text("fr", "dix-sept", "dix-huit"))
        self.assertFalse(same_number_aware_text("es", "veintidós", "veintitrés"))
        self.assertFalse(same_number_aware_text("en", "ten house", "house"))
        self.assertFalse(same_number_aware_text("es", "la casa del diez", "la casa diez"))
        self.assertFalse(same_number_aware_text("en", "the ten house", "the extra ten house"))

    def test_numeric_codes_signs_and_decimal_notation_are_not_cardinal_aliases(self):
        for value in ('01', '0018', '+18', '-18', '−18', '1.8', '1,8', '1/8'):
            with self.subTest(value=value):
                self.assertFalse(same_number_aware_text('en', value, 'eighteen'))
        self.assertFalse(same_number_aware_text('en', '1.8', 'one eight'))
        self.assertFalse(same_number_aware_text('en', '-1', 'one'))

    def test_zero_and_locale_false_friend(self):
        self.assertEqual(canonical_number_tokens("en", "0"), ("<num:0>",))
        self.assertTrue(same_number_aware_text("it", "0", "zero"))
        self.assertFalse(same_number_aware_text("it", "0", "uno"))
        self.assertEqual(canonical_number_tokens("en", "once"), ("once",))
        self.assertEqual(canonical_number_tokens("es", "once"), ("<num:11>",))

    def test_no_fuzzy_substring_or_homophone_matching(self):
        self.assertEqual(canonical_number_tokens("en", "tenth"), ("tenth",))
        self.assertEqual(canonical_number_tokens("en", "listen"), ("listen",))
        self.assertEqual(canonical_number_tokens("es", "diezmo"), ("diezmo",))
        self.assertFalse(same_number_aware_text("en", "two", "too"))

    def test_accent_policy_default_ignores_and_strict_override_preserves(self):
        self.assertTrue(same_number_aware_text("fr", "zéro", "zero"))
        self.assertTrue(same_number_aware_text("es", "dieciséis", "dieciseis"))
        self.assertFalse(same_number_aware_text("fr", "zéro", "zero", ignore_accents=False))
        self.assertFalse(same_number_aware_text("es", "dieciséis", "dieciseis", ignore_accents=False))

    def test_hyphens_are_word_separators_but_compound_numbers_are_one_unit(self):
        self.assertEqual(canonical_number_tokens("fr", "dix-sept"), ("<num:17>",))
        self.assertTrue(same_number_aware_text("fr", "dix-sept", "17"))
        self.assertEqual(canonical_number_tokens("en", "well-known"), ("well", "known"))

    def test_unknown_locale_and_malformed_parameters_rejected(self):
        for locale, text, options, error in [
            ("pt", "10", {}, ValueError), (None, "10", {}, TypeError),
            ("en", None, {}, TypeError), ("en", "10", {"ignore_accents": 1}, TypeError),
        ]:
            with self.subTest(locale=locale, text=text, options=options):
                with self.assertRaises(error):
                    canonical_number_tokens(locale, text, **options)

if __name__ == "__main__":
    unittest.main(verbosity=2)
