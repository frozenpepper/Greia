"""Unstarted allowances move once; attempted cues never get a fresh budget."""
import json
import unittest
import test_voice_natural_corpus as fixture
from greia_voice_corpus.store import write_json, RunStore
from greia_voice_corpus.inventory import digest, receipt_path
from greia_voice_corpus.natural_continuation import prepare_unstarted, validate_handoff

class UnstartedContinuationTests(unittest.TestCase):
    def setUp(self):
        fixture.NaturalCorpusTests.setUp(self)
        self.store.plan['natural_run']={'cache_root':str(self.base/'cache')}
        write_json(self.store.work/'plan.json',self.store.plan)
        write_json(self.store.work/'progress.json',{'status':'METHOD_REVIEW_REQUIRED'})
        write_json(self.store.work/'preinstall-snapshot.json',{'targets':{self.relative:{'audio':digest(self.audio),'receipt':digest(receipt_path(self.audio))}}})
    def tearDown(self):fixture.NaturalCorpusTests.tearDown(self)
    def test_only_unused_allowance_moves_once_with_history_retained(self):
        work=self.base/'child'
        plan=prepare_unstarted(self.store.work,work,exclude_topics=frozenset({'letter'}))
        self.assertEqual(len(plan['rows']),1)
        child=RunStore(work)
        try:
            validate_handoff(child)
            ledger=json.loads((work/'method-reservations.json').read_text())
            self.assertEqual(ledger['entries'][self.relative],{'prior_count':3,'attempts':[]})
            with self.assertRaisesRegex(ValueError,'already handed off'):
                prepare_unstarted(self.store.work,self.base/'duplicate',exclude_topics=frozenset())
            write_json(self.store.work/'method-reservations.json',{'tampered':True})
            with self.assertRaisesRegex(ValueError,'proof or scope changed'):validate_handoff(child)
        finally:child.close()
    def test_attempted_cue_is_not_rebudgeted(self):
        ledger=json.loads((self.store.work/'method-reservations.json').read_text())
        ledger['entries'][self.relative]['attempts']=[{'number':1,'evidence_dir':'existing','request':self.row['request']}]
        write_json(self.store.work/'method-reservations.json',ledger)
        with self.assertRaisesRegex(ValueError,'no eligible'):prepare_unstarted(self.store.work,self.base/'child',exclude_topics=frozenset())
    def test_excluded_letter_lane_stays_unstarted(self):
        self.store.plan['rows'][0]['natural_topic']='letter'
        write_json(self.store.work/'plan.json',self.store.plan)
        with self.assertRaisesRegex(ValueError,'no eligible'):prepare_unstarted(self.store.work,self.base/'child',exclude_topics=frozenset({'letter'}))
