"""Normal automatic short API under bounded corpus budgets and transactions."""
import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'tools'),str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).parent)]
import test_greia_voice_corpus as corpus_fixture
import test_voice_short_routing as short_fixture
from greia_voice_core.engine import VoiceEngine
from greia_voice_core.registry import VoiceRegistry
from greia_voice_core.locking import NullGenerationLock
from greia_voice_core.short_phrases import ShortPhrasePipeline
from greia_voice_corpus.automatic_generation import POLICY,request_for
from greia_voice_corpus.runner import CorpusRunner
from greia_voice_corpus.store import write_json
from greia_voice_corpus.inventory import receipt_path


class AutomaticCorpusTests(unittest.TestCase):
    def setUp(self):
        corpus_fixture.CorpusTests.setUp(self)
        self.row['request']['text']='Find Luna'
        self.plan['automatic_short_generation_policy']=POLICY
        self.store.plan=copy.deepcopy(self.plan)
        write_json(self.store.work/'plan.json',self.plan)
        self.countfile=self.store.work/'carrier-attempt-counts.json'
        write_json(self.countfile,{self.relative:2})
        self.provider=short_fixture.Provider(self.base)
        self.pipeline=ShortPhrasePipeline(transcriber=lambda path,locale:{'text':'Find Luna','segments':[]},
            readiness=lambda:(True,'fixture'),evidence_root=self.base/'automatic-evidence')
        self.engine=VoiceEngine(self.root,VoiceRegistry.load(self.root),[self.provider],
            verifier=short_fixture.NoopVerifier(),generation_lock=NullGenerationLock(),short_phrase_pipeline=self.pipeline)

    def tearDown(self):
        self.engine.close();corpus_fixture.CorpusTests.tearDown(self)

    def run_corpus(self):
        with redirect_stdout(io.StringIO()):
            return CorpusRunner(self.store,self.engine,'required').run(continue_after_carrier_rejection=True)

    def test_one_remaining_take_installs_via_normal_api_and_resumes_without_generation(self):
        self.assertEqual(self.run_corpus(),0)
        self.assertEqual(len(self.provider.calls),1)
        self.assertEqual(json.loads(self.countfile.read_text())[self.relative],3)
        rec=json.loads(receipt_path(self.audio).read_text())
        self.assertEqual(rec['human_review'],'PENDING')
        self.assertEqual(rec['request']['output'],self.relative)
        self.assertEqual(rec['short_phrase']['extraction']['algorithm_version'],'greia-spoken-carrier-extractor-v7')
        self.assertEqual(self.run_corpus(),0);self.assertEqual(len(self.provider.calls),1)
        self.store.restore();self.assertEqual(self.audio.read_bytes(),b'old accepted speech')

    def test_quality_failure_uses_only_one_take_and_keeps_original(self):
        self.pipeline.transcriber=lambda path,locale:{'text':'Wrong words','segments':[]}
        self.assertEqual(self.run_corpus(),0)
        self.assertEqual(len(self.provider.calls),1)
        self.assertEqual(self.store.state(self.relative),'PRESERVED')
        self.assertEqual(self.audio.read_bytes(),b'old accepted speech')
        self.assertTrue((self.store.work/'carrier-evidence'/(self.relative+'.failure.json')).exists())
        result=json.loads((self.store.work/'candidates'/(self.relative+'.result.json')).read_text())
        self.assertTrue(Path(result['evidence_dir']).is_dir())
        self.assertEqual(self.run_corpus(),0);self.assertEqual(len(self.provider.calls),1)

    def test_asr_infrastructure_error_stops_for_recovery_not_acoustic_retry(self):
        def fail(*args):raise OSError('ASR backend broken')
        self.pipeline.transcriber=fail
        self.assertEqual(self.run_corpus(),2)
        self.assertEqual(self.store.state(self.relative),'NEEDS_RECOVERY')
        self.assertEqual(len(self.provider.calls),1)
        self.assertFalse((self.store.work/'carrier-evidence'/(self.relative+'.failure.json')).exists())
        self.assertEqual(self.run_corpus(),2);self.assertEqual(len(self.provider.calls),1)

    def test_exhausted_budget_never_submits(self):
        write_json(self.countfile,{self.relative:3})
        self.assertEqual(self.run_corpus(),2);self.assertFalse(self.provider.calls)
        self.assertEqual(json.loads(self.countfile.read_text())[self.relative],3)

    def test_final_gate_cannot_be_disabled(self):
        with self.assertRaisesRegex(ValueError,'requires final verification'):
            CorpusRunner(self.store,self.engine,'off').run()
        self.assertFalse(self.provider.calls)
        self.assertEqual(json.loads(self.countfile.read_text())[self.relative],2)

    def test_complete_uncertain_candidate_recovers_without_another_submission(self):
        candidate=self.store.work/'candidates'/self.relative
        result=self.engine.generate(request_for(self.row,candidate))
        self.assertTrue(result.evidence_dir.is_dir())
        self.store.set_state(self.relative,'GENERATING')
        write_json(self.countfile,{self.relative:3})
        self.assertEqual(self.run_corpus(),0);self.assertEqual(len(self.provider.calls),1)

    def test_uncertain_job_without_candidate_never_resubmits(self):
        self.store.set_state(self.relative,'GENERATING')
        write_json(self.countfile,{self.relative:3})
        self.assertEqual(self.run_corpus(),2);self.assertFalse(self.provider.calls)
        self.assertEqual(self.store.state(self.relative),'NEEDS_RECOVERY')

    def test_corrupt_final_transcript_is_rejected_despite_reported_pass(self):
        candidate=self.store.work/'candidates'/self.relative
        self.engine.generate(request_for(self.row,candidate))
        rec=json.loads(receipt_path(candidate).read_text());rec['short_phrase']['quality']['transcript']='Find Luna now'
        write_json(receipt_path(candidate),rec)
        with self.assertRaisesRegex(ValueError,'canonical guards'):
            CorpusRunner(self.store,self.engine,'required')._validate_candidate(self.row,candidate)


    def test_incomplete_historical_budget_never_submits(self):
        write_json(self.countfile,{self.relative:1})
        self.assertEqual(self.run_corpus(),2);self.assertFalse(self.provider.calls)
        self.assertEqual(json.loads(self.countfile.read_text())[self.relative],1)


    def test_fresh_plan_preparation_preserves_frozen_scripts_and_reserves_no_take(self):
        from types import SimpleNamespace
        from continue_voice_priority_v7 import prepare
        from greia_voice_corpus.carriers import freeze_row
        source=copy.deepcopy(self.plan);source.pop('automatic_short_generation_policy')
        source['rows'][0]['spoken_carrier']=freeze_row(source['rows'][0],'warn')
        source_file=self.base/'frozen-source.json';write_json(source_file,source)
        priority=self.base/'priority.json';record={'path':self.relative,**self.row['request']}
        write_json(priority,{'records':[record]})
        remaining=self.base/'remaining.json';write_json(remaining,{'remaining':{self.relative:{'cumulative_takes':2}}})
        args=SimpleNamespace(remaining_file=remaining,priority_file=priority,source_plan=source_file,
            history_root=self.base,cache_root=self.base/'cache',work_dir=self.base/'fresh')
        with patch('continue_voice_priority_v7.collect_history',return_value=({self.relative:2},{},{})):
            with redirect_stdout(io.StringIO()):self.assertEqual(prepare(args,self.root),0)
        planned=json.loads((args.work_dir/'plan.json').read_text())
        self.assertNotIn('spoken_carrier',planned['rows'][0])
        self.assertEqual(planned['rows'][0]['previous_carrier_plan'],source['rows'][0]['spoken_carrier'])
        self.assertEqual(json.loads((args.work_dir/'carrier-attempt-counts.json').read_text())[self.relative],2)
        self.assertEqual(json.loads(source_file.read_text()),source)
