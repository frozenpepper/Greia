import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from greia_voice_core.models import SpeechKind, VoiceRequest
from greia_voice_core.natural_carrier import NaturalCarrierPolicy
from greia_voice_core.number_comparison import (
    SPOKEN_TARGET_COMPARISON_POLICY,
    compare_target_transcript,
    canonical_number_tokens,
)
from greia_voice_core.spoken_target import spoken_target


class SpokenTargetTests(unittest.TestCase):
    def test_owner_approved_letter_spelling_and_number_examples(self):
        cases = {
            ("en", "Y as Yacht"): "why as Yacht",
            ("en", "W as Whale"): "double-u as Whale",
            ("it", "K come Koala"): "cappa come Koala",
            ("fr", "D comme Dauphin"): "dé comme Dauphin",
            ("es", "Ñ de Ñandú"): "eñe de Ñandú",
            ("en", "Count 10 apples"): "Count ten apples",
            ("it", "Conta 22 mele"): "Conta ventidue mele",
        }
        for (locale, source), expected in cases.items():
            with self.subTest(locale=locale, source=source):
                result = spoken_target(locale, source)
                self.assertEqual(result.semantic_text, source)
                self.assertEqual(result.spoken_text, expected)

    def test_digits_that_are_not_standalone_cardinals_fail_closed(self):
        for text in ("Room 101", "1.5", "-3", "2026/10/23", "K2"): 
            with self.subTest(text=text), self.assertRaises(ValueError):
                spoken_target("en", text)

    def test_natural_carrier_preserves_semantic_request_and_speaks_spelling(self):
        request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "it", "K come Koala",
                               cue_id="letter_K", comparison_policy=SPOKEN_TARGET_COMPARISON_POLICY)
        _prefix, composite, _delivery = NaturalCarrierPolicy().composite(request, "")
        self.assertEqual(request.text, "K come Koala")
        self.assertIn("cappa come Koala", composite)
        self.assertNotIn("K come Koala", composite)

    def test_letter_identity_is_hard_guarded_and_owner_glyph_equivalence_is_local(self):
        policy = SPOKEN_TARGET_COMPARISON_POLICY
        self.assertFalse(compare_target_transcript("en", "Y as Yacht", "jay as Yacht", policy=policy)
                         .flags(require_word_count=True) == [])
        self.assertTrue(compare_target_transcript("en", "W as Whale", "double you as Whale", policy=policy)
                        .exact_match)
        self.assertTrue(compare_target_transcript("en", "K as Koala", "ch as Koala", policy=policy)
                        .exact_match)
        self.assertTrue(compare_target_transcript("en", "C as Cat", "kay as Cat", policy=policy)
                        .exact_match)
        wrong = compare_target_transcript("en", "Y as Yacht", "jay as Yacht", policy=policy)
        self.assertIn("TARGET_LETTER_MISMATCH", wrong.flags())
        self.assertNotEqual(canonical_number_tokens("en", "Y as Yacht"),
                            canonical_number_tokens("en", "jay as Yacht"))

    def test_wrong_numbers_and_extra_words_still_fail(self):
        policy = SPOKEN_TARGET_COMPARISON_POLICY
        self.assertIn("TARGET_NUMBER_MISMATCH",
                      compare_target_transcript("en", "Count ten", "Count eleven", policy=policy).flags())
        self.assertIn("TARGET_WORD_COUNT_MISMATCH",
                      compare_target_transcript("en", "Count ten", "Count extra ten", policy=policy).flags())


if __name__ == "__main__":
    unittest.main(verbosity=2)
