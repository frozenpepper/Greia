import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from greia_voice_core.number_comparison import (canonical_number_tokens, same_number_aware_text,
    compare_target_transcript, LEGACY_COMPARISON_POLICY)

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

    def test_larger_cardinals_and_literal_number_identity(self):
        cases = {
            'en': {26:'twenty-six',31:'thirty-one',48:'forty-eight',71:'seventy-one',80:'eighty',99:'ninety-nine',100:'one hundred'},
            'it': {26:'ventisei',28:'ventotto',31:'trentuno',33:'trentatré',48:'quarantotto',71:'settantuno',80:'ottanta',99:'novantanove',100:'cento'},
            'fr': {26:'vingt-six',31:'trente et un',48:'quarante-huit',70:'soixante-dix',71:'soixante et onze',80:'quatre-vingts',81:'quatre-vingt-un',91:'quatre-vingt-onze',99:'quatre-vingt-dix-neuf',100:'cent'},
            'es': {26:'veintiséis',31:'treinta y uno',48:'cuarenta y ocho',71:'setenta y uno',80:'ochenta',99:'noventa y nueve',100:'cien'},
        }
        for locale, forms in cases.items():
            for value, spelling in forms.items():
                with self.subTest(locale=locale, value=value):
                    self.assertTrue(same_number_aware_text(locale,str(value),spelling))
                    self.assertTrue(same_number_aware_text(locale,spelling,str(value)))
                    self.assertEqual(compare_target_transcript(locale,spelling,str(value)).score,1)
                    self.assertFalse(compare_target_transcript(locale,spelling,str(value+1)).numbers_match)
        for left,right in [('9999','9998'),('01','1'),('-18','18'),('1.8','1.9'),('1,8','18')]:
            self.assertFalse(compare_target_transcript('en',left,right).numbers_match)

    def test_internal_numeric_labels_do_not_inflate_wrong_word_score(self):
        observed=compare_target_transcript('en','Count to ten','Client to 10')
        self.assertTrue(observed.numbers_match)
        self.assertTrue(observed.word_count_matches)
        self.assertLess(observed.score,.8)
        historical=compare_target_transcript('en','Count to ten','Client to 10',policy=LEGACY_COMPARISON_POLICY)
        self.assertGreater(historical.score,.8)

    def test_v1_remains_frozen_and_unknown_versions_fail(self):
        self.assertNotEqual(canonical_number_tokens('en','twenty six',policy=LEGACY_COMPARISON_POLICY),
                            canonical_number_tokens('en','26',policy=LEGACY_COMPARISON_POLICY))
        with self.assertRaises(ValueError):canonical_number_tokens('en','ten',policy='invented')

    def test_larger_cardinal_accents_and_non_number_controls(self):
        for locale,accented,plain in [('it','trentatré','trentatre'),('es','veintiséis','veintiseis')]:
            self.assertTrue(same_number_aware_text(locale,accented,plain))
            self.assertFalse(same_number_aware_text(locale,accented,plain,ignore_accents=False))
        for locale,left,right in [('en','twenty six','twenty seven'),('fr','quatre-vingt-un','quatre-vingt-onze'),('es','treinta y uno','treinta uno'),('it','cento','centro')]:
            self.assertFalse(same_number_aware_text(locale,left,right))

if __name__ == "__main__":
    unittest.main(verbosity=2)
