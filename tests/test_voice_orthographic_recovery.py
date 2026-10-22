"""Explicit English Oskar/Oscar recovery; historical policies stay unchanged."""
import json
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io
import test_voice_saved_recovery as fixture
from greia_voice_core.number_comparison import (
    COMPARISON_POLICY, ORTHOGRAPHIC_COMPARISON_POLICY, compare_target_transcript)
from greia_voice_corpus.saved_recovery import ORTHOGRAPHIC_POLICY, validate_recovery_receipt
from greia_voice_corpus.inventory import receipt_path
from greia_voice_corpus.store import write_json
from greia_voice_corpus.runner import CorpusRunner
from greia_voice_corpus.carrier_generation import CarrierExtractionFailure


class OrthographicRecoveryTests(unittest.TestCase):
    def setUp(self):
        fixture.SavedRecoveryTests.setUp(self)
        self.row['request'].update(locale='en', text='Find Oskar')
        carrier=self.row['spoken_carrier']
        carrier.update(prefix="Let's look for our friend.", prefix_word_count=5,
                       target='Find Oskar', target_word_count=2,
                       composite_text="Let's look for our friend.\n\nFind Oskar")
        self.plan['saved_recovery_policy']=ORTHOGRAPHIC_POLICY
        self.store.plan=self.plan
        rec=json.loads(receipt_path(self.raw).read_text())
        rec['request'].update(locale='en',text=carrier['composite_text'])
        write_json(receipt_path(self.raw),rec)
        self.transcribe=lambda path,locale:{'text':'Find Oscar.','segments':[]}

    def tearDown(self):
        fixture.SavedRecoveryTests.tearDown(self)

    def prepare(self):
        return fixture.SavedRecoveryTests.prepare(self)

    # The shared fixture owns the original bytes and no-synthesis engine.
    def test_explicit_name_recovery_transaction(self):
        with patch.object(self.engine,'generate',side_effect=AssertionError('provider forbidden')) as provider:
            candidate=self.prepare()
            receipt=json.loads(receipt_path(candidate).read_text())
            self.assertEqual(receipt['verification']['score'],1)
            self.assertEqual(receipt['verification']['transcript'],'Find Oscar.')
            self.assertEqual(receipt['target_request']['text'],'Find Oskar')
            self.assertEqual(receipt['verification']['comparison_policy'],ORTHOGRAPHIC_COMPARISON_POLICY)
            with self.assertRaises(ValueError):validate_recovery_receipt(receipt,True)
            validate_recovery_receipt(receipt,True,ORTHOGRAPHIC_POLICY)
            with redirect_stdout(io.StringIO()):self.assertEqual(CorpusRunner(self.store,self.engine,'required').run(),0)
            self.assertEqual(self.store.state(self.row['path']),'DONE')
            provider.assert_not_called()
        self.store.restore()
        self.assertEqual(self.target.read_bytes(),b'previous accepted speech')

    def test_variants_and_negative_controls(self):
        for locale in ('en','it','fr','es'):
            match=compare_target_transcript(locale,'Find Oskar','Find Oscar',policy=ORTHOGRAPHIC_COMPARISON_POLICY)
            self.assertEqual(match.exact_match,locale=='en')
        self.assertFalse(compare_target_transcript('en','Find Oskar','Find Oscar',policy=COMPARISON_POLICY).exact_match)
        for wrong in ('Find Omar','Find Luna','Find Oscar now','Find Oscar 2','Find Oskars'):
            comparison=compare_target_transcript('en','Find Oskar',wrong,policy=ORTHOGRAPHIC_COMPARISON_POLICY)
            self.assertFalse(comparison.exact_match,wrong)
        for locale,pair in {'en':('Count to ten','Count to 11'),'it':('Conta fino a dieci','Conta fino a 11'),
                            'fr':('Compte dix','Compte 11'),'es':('Cuenta diez','Cuenta 11')}.items():
            self.assertFalse(compare_target_transcript(locale,*pair,policy=ORTHOGRAPHIC_COMPARISON_POLICY).numbers_match)

    def test_number_homophones_are_position_bounded_and_opt_in(self):
        from greia_voice_core.number_comparison import ENGLISH_SPOKEN_COMPARISON_POLICY as spoken
        for expected, actual in [('Find two the same', 'Find to the same'),('Count to ten','Count 2 10'),
                                  ('You won','You one'),('Four birds','For birds'),('Eight apples','Ate apples'),('W as Whale','Double U as whale'),('W as Whale','Double you as whale')]:
            c=compare_target_transcript('en',expected,actual,policy=spoken)
            self.assertTrue(c.exact_match,(expected,actual));self.assertEqual(c.flags(),[])
        for actual in ('Find three the same','Find 4 the same','Find to the same now','Find 2 now'):
            c=compare_target_transcript('en','Find two the same',actual,policy=spoken)
            self.assertTrue(c.score<=.8 or c.flags(),actual)
        self.assertFalse(compare_target_transcript('en','Find two the same','Find to the same').numbers_match)
        self.assertFalse(compare_target_transcript('it','due','to',policy=spoken).numbers_match)
        self.assertLessEqual(compare_target_transcript('en','W as whale','Double you as well',policy=spoken).score,.8)
        self.assertFalse(compare_target_transcript('en','Y as yacht','Double you as yacht',policy=spoken).exact_match)
        for expected,actual in [('one','eight'),('two','four'),('ten','eleven'),('21','22'),('002','2'),('2.5','2.6')]:
            self.assertFalse(compare_target_transcript('en',expected,actual,policy=spoken).numbers_match)

    def test_added_word_cannot_be_recovered(self):
        self.transcribe=lambda path,locale:{'text':'Find Oscar now','segments':[]}
        with self.assertRaises(CarrierExtractionFailure):self.prepare()
        self.assertEqual(self.target.read_bytes(),b'previous accepted speech')

