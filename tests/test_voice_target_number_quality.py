"""Versioned target comparison never changes historical v6 or numeric identity."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from greia_voice_core.target_quality import TargetQualityChecker


class TargetNumberQualityTests(unittest.TestCase):
    def check(self, target, transcript, locale='en', versioned=True, strict=False):
        extraction = {'extracted_transcript': transcript, 'model_id': 'test-base',
                      'model_revision': 'test-revision'}
        if versioned:
            extraction['comparison_policy'] = 'locale-number-tokens-v1'
        with patch('voice_carrier._read_pcm16', return_value=(22050, 1, [1, 2])), \
             patch('greia_voice_core.target_quality.signal_metrics', return_value=({}, [])):
            return TargetQualityChecker(lambda *args: self.fail('unchanged PCM must use its retained ASR')).check(
                Path('same.wav'), Path('same.wav'), extraction, text=target, locale=locale,
                ignore_accents=not strict, require_word_count=True)

    def test_number_units_match_after_real_whisper_style_digit_conversion(self):
        for target, actual, locale in [('The ten house', 'the 10 house', 'en'),
                                        ('La casa del diez', 'la casa del 10', 'es'),
                                        ('Dix-sept !', '17', 'fr')]:
            with self.subTest(locale=locale):
                result = self.check(target, actual, locale)
                self.assertEqual(result['disposition'], 'PASS')
                self.assertEqual(result['score'], 1.0)
                self.assertEqual(result['flags'], [])

    def test_wrong_number_is_hard_rejection_even_in_an_otherwise_matching_phrase(self):
        result = self.check('Find the twenty one little stars in the lovely picture',
                            'Find the 22 little stars in the lovely picture')
        self.assertIn('TARGET_NUMBER_MISMATCH', result['flags'])
        self.assertEqual(result['disposition'], 'WARN')

    def test_extra_word_cannot_be_excused_by_numeric_equivalence(self):
        result = self.check('The ten house', 'Extra the 10 house')
        self.assertEqual(result['disposition'], 'WARN')
        self.assertIn('TARGET_WORD_COUNT_MISMATCH', result['flags'])

    def test_historical_receipt_retains_old_scoring_and_word_count(self):
        result = self.check('Dix-sept !', '17', 'fr', versioned=False)
        self.assertEqual(result['disposition'], 'WARN')
        self.assertIn('TARGET_WORD_COUNT_MISMATCH', result['flags'])
        self.assertEqual(result['comparison_policy'], 'legacy-text')

    def test_accent_override_still_applies(self):
        self.assertEqual(self.check('dieciséis', '16', 'es')['disposition'], 'PASS')
        self.assertEqual(self.check('dieciseis', '16', 'es', strict=True)['disposition'], 'WARN')


class DisposableIntroTests(unittest.TestCase):
    def test_target_cannot_be_recovered_from_the_declared_intro_itself(self):
        from greia_voice_core.short_policy import ShortPhrasePolicy, PREFIXES
        from greia_voice_core.models import VoiceRequest, SpeechKind
        from greia_voice_core.number_comparison import canonical_number_tokens
        for locale, target in [('en', 'English'), ('it', 'italiano'),
                               ('fr', 'français'), ('es', 'español')]:
            request = VoiceRequest(speaker='leo', kind=SpeechKind.CHARACTER_DIALOGUE,
                                   locale=locale, text=target)
            prefix, composite, _ = ShortPhrasePolicy().composite(request, 'Natural delivery.')
            self.assertNotEqual(prefix, PREFIXES[locale])
            self.assertNotIn(canonical_number_tokens(locale, target)[0],
                             canonical_number_tokens(locale, prefix))
            self.assertTrue(composite.endswith(target))


if __name__ == '__main__':
    unittest.main()
