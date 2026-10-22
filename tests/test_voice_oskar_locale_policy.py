"""Explicit exact proper-name spelling only; historical/default policies unchanged."""
import unittest
from greia_voice_core.number_comparison import (compare_target_transcript,COMPARISON_POLICY,
    OSKAR_LOCALE_COMPARISON_POLICY,ENGLISH_SPOKEN_COMPARISON_POLICY)

class OskarLocalePolicyTests(unittest.TestCase):
    def test_explicit_name_equivalence_in_four_locales_only(self):
        for locale in ('en','it','fr','es'):
            for target,actual in [('Oskar','Oscar'),('Oscar','Oskar')]:
                with self.subTest(locale=locale,target=target):
                    self.assertEqual(compare_target_transcript(locale,target,actual,policy=OSKAR_LOCALE_COMPARISON_POLICY).score,1)
                    self.assertFalse(compare_target_transcript(locale,target,actual,policy=COMPARISON_POLICY).exact_match)
    def test_names_extra_words_and_different_numbers_remain_wrong(self):
        for locale in ('en','it','fr','es'):
            for actual in ('Luna','Oskar maintenant','Oskar 11'):
                comp=compare_target_transcript(locale,'Oskar 10',actual,policy=OSKAR_LOCALE_COMPARISON_POLICY)
                self.assertFalse(comp.exact_match)
                self.assertTrue(comp.flags() or comp.score<=.8)
    def test_no_new_homophones_or_letter_names_in_name_policy(self):
        for target,actual in [('two','to'),('W as Whale','double you as whale')]:
            self.assertFalse(compare_target_transcript('en',target,actual,policy=OSKAR_LOCALE_COMPARISON_POLICY).exact_match)
            self.assertTrue(compare_target_transcript('en',target,actual,policy=ENGLISH_SPOKEN_COMPARISON_POLICY).exact_match)
