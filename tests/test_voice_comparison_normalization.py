"""Versioned orthographic normalization for current Parakeet verification."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from greia_voice_core.number_comparison import (
    COMPARISON_POLICY,
    PARAKEET_COMPARISON_POLICY,
    canonical_number_tokens,
    compare_target_transcript,
)


class ParakeetComparisonNormalizationTests(unittest.TestCase):
    def test_owner_approved_ch_c_k_equivalence_is_lexical_and_bidirectional(self):
        examples = (
            ("en", "Oskar", "Oscar"),
            ("it", "Casa", "Kasa"),
            ("fr", "chaud", "kaud"),
            ("es", "chico", "kiko"),
            ("en", "Kite", "Cite"),
            ("fr", "C comme Chat", "K comme Kat"),
        )
        for locale, left, right in examples:
            with self.subTest(locale=locale, left=left, right=right):
                self.assertEqual(
                    compare_target_transcript(
                        locale, left, right, policy=PARAKEET_COMPARISON_POLICY
                    ).expected_tokens,
                    compare_target_transcript(
                        locale, left, right, policy=PARAKEET_COMPARISON_POLICY
                    ).actual_tokens,
                )
                self.assertEqual(
                    compare_target_transcript(
                        locale, right, left, policy=PARAKEET_COMPARISON_POLICY
                    ).score,
                    1.0,
                )

    def test_hyphen_space_punctuation_case_and_accent_were_already_equivalent(self):
        expected = "Raconte-moi cette image!"
        observed = "Raconte moi cette image"
        self.assertEqual(
            compare_target_transcript("fr", expected, observed,
                                      policy=COMPARISON_POLICY).expected_tokens,
            compare_target_transcript("fr", expected, observed,
                                      policy=COMPARISON_POLICY).actual_tokens,
        )
        self.assertEqual(
            compare_target_transcript("fr", expected, observed,
                                      policy=PARAKEET_COMPARISON_POLICY).score,
            1.0,
        )

    def test_historical_v2_and_registered_previous_policies_keep_their_meaning(self):
        self.assertFalse(compare_target_transcript(
            "it", "Trova Oskar", "Trova Oscar", policy=COMPARISON_POLICY
        ).exact_match)
        self.assertEqual(
            canonical_number_tokens("fr", "dix-sept", policy=COMPARISON_POLICY),
            ("<num:17>",),
        )
        self.assertEqual(
            canonical_number_tokens("fr", "dix-sept", policy=PARAKEET_COMPARISON_POLICY),
            ("<num:17>",),
        )

    def test_numeric_parse_happens_before_spelling_normalization(self):
        equivalent_number = compare_target_transcript(
            "it", "cinque Casa", "5 Kasa", policy=PARAKEET_COMPARISON_POLICY
        )
        self.assertTrue(equivalent_number.exact_match)
        changed_spelling_number = compare_target_transcript(
            "it", "cinque Casa", "kinque Kasa", policy=PARAKEET_COMPARISON_POLICY
        )
        self.assertFalse(changed_spelling_number.numbers_match)
        self.assertIn("TARGET_NUMBER_MISMATCH", changed_spelling_number.flags())

    def test_wrong_numbers_extra_words_and_other_letters_remain_distinct(self):
        wrong_number = compare_target_transcript(
            "it", "Trova Oskar 10", "Trova Oscar 11",
            policy=PARAKEET_COMPARISON_POLICY,
        )
        self.assertFalse(wrong_number.numbers_match)
        self.assertIn("TARGET_NUMBER_MISMATCH", wrong_number.flags())
        extra_word = compare_target_transcript(
            "it", "Trova Oskar", "Trova Oscar adesso",
            policy=PARAKEET_COMPARISON_POLICY,
        )
        self.assertFalse(extra_word.word_count_matches)
        self.assertIn("TARGET_WORD_COUNT_MISMATCH", extra_word.flags())
        different_word = compare_target_transcript(
            "en", "Cat", "Bat", policy=PARAKEET_COMPARISON_POLICY
        )
        self.assertNotEqual(different_word.expected_tokens, different_word.actual_tokens)

    def test_normalization_does_not_mutate_the_authored_or_recognized_strings(self):
        expected = "Raconte-moi cette image!"
        observed = "Raconte moi cette image"
        before = expected, observed
        comparison = compare_target_transcript(
            "fr", expected, observed, policy=PARAKEET_COMPARISON_POLICY
        )
        self.assertTrue(comparison.exact_match)
        self.assertEqual((expected, observed), before)


if __name__ == "__main__":
    unittest.main()
