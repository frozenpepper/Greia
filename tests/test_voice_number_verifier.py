"""The normal (non-carrier) public verifier shares number semantics too."""
import sys,types,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from greia_voice_core.verification import WhisperVerifier
from greia_voice_core.models import VoiceRequest,SpeechKind,VerificationDisposition

class GeneralNumberVerificationTests(unittest.TestCase):
    def verify(self,expected,actual,locale):
        fake=types.SimpleNamespace(transcribe=Mock(return_value={'text':actual}));verifier=WhisperVerifier()
        with patch.dict(sys.modules,{'mlx_whisper':fake}),patch.object(verifier,'probe',return_value=(True,'fixture')),patch('greia_voice_core.verification.cached_asr_model',return_value=Path('/cached/base')),patch('greia_voice_core.verification._release_mlx_transient_memory'):
            result=verifier.verify(VoiceRequest('leo',SpeechKind.CHARACTER_DIALOGUE,locale,expected,short_text_mode='off'),Path('fixture.wav'))
        self.assertIsNone(fake.transcribe.call_args.kwargs['initial_prompt'])
        return result

    def test_spelled_and_digits_match_both_directions_in_every_language(self):
        for language,phrase,number in [('en','Count to twenty-six',26),('it','Conta fino a trentatré',33),('fr','Compte jusqu’à quatre-vingt-onze',91),('es','Cuenta hasta treinta y uno',31)]:
            words=phrase.split();spelling={'en':'twenty-six','it':'trentatré','fr':'quatre-vingt-onze','es':'treinta y uno'}[language];digits=phrase.replace(spelling,str(number))
            for expected,actual in [(phrase,digits),(digits,phrase)]:
                with self.subTest(language=language,expected=expected):
                    result=self.verify(expected,actual,language);self.assertEqual(result.disposition,VerificationDisposition.PASS);self.assertEqual(result.score,1)

    def test_wrong_number_is_not_hidden_by_a_long_matching_sentence(self):
        for locale,expected,actual in [('en','Find the 9999 small stars in this beautiful picture','Find the 9998 small stars in this beautiful picture'),('it','Trova il numero trentatré nel nostro bel disegno','Trova il numero 34 nel nostro bel disegno'),('fr','Trouve le nombre quatre-vingt-onze dans cette belle image','Trouve le nombre 81 dans cette belle image'),('es','Encuentra el número treinta y uno en este bonito dibujo','Encuentra el número 32 en este bonito dibujo')]:
            self.assertEqual(self.verify(expected,actual,locale).disposition,VerificationDisposition.WARN)

    def test_number_marker_cannot_boost_an_unrelated_word(self):
        result=self.verify('Count to ten','Client to 10','en');self.assertEqual(result.disposition,VerificationDisposition.WARN);self.assertLess(result.score,.8)

class NumberReviewPolicyTests(unittest.TestCase):
    def test_saved_evidence_uses_explicit_locale_and_preserves_raw_record(self):
        from greia_voice_core.review_policy import reassess_result
        old={'locale':'fr','status':'WARN','expected_text':'Compte jusqu’à quatre-vingt-onze','flags':['ASR_MISMATCH_OR_ERROR'],'asr':{'status':'WARN','transcript':'Compte jusqu’à 91','score':.1}}
        result=reassess_result(old);self.assertEqual(result['status'],'PASS');self.assertEqual(result['asr']['score'],1);self.assertEqual(result['asr']['unexpected_tokens'],[]);self.assertEqual(old['asr']['score'],.1)
        old['asr']['transcript']='Compte jusqu’à 81';result=reassess_result(old);self.assertEqual(result['status'],'WARN');self.assertIn('TARGET_NUMBER_MISMATCH',result['flags'])
    def test_missing_locale_is_never_guessed(self):
        from greia_voice_core.review_policy import reassess_result
        old={'status':'WARN','expected_text':'Count to ten','flags':[],'asr':{'status':'WARN','transcript':'Count to 10','score':.1}}
        self.assertEqual(reassess_result(old)['asr']['comparison_policy'],'legacy-text-no-locale')
        self.assertEqual(reassess_result(old,locale='en')['status'],'PASS')
