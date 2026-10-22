"""Saved-only recorded-observation corpus transactions; providers are forbidden."""
import copy
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

import test_voice_saved_recovery as saved_fixture
from greia_voice_core.context_evidence import RecordedTranscriber, observation_identity
from greia_voice_corpus.context_recovery import POLICY
from greia_voice_corpus.carrier_generation import prepare_saved_candidate, CarrierExtractionFailure, generate_candidate
from greia_voice_corpus.inventory import digest, receipt_path
from greia_voice_corpus.runner import CorpusRunner
from greia_voice_corpus.store import RunStore, write_json
from recover_voice_candidates import prepare_plan
from voice_carrier_search import CandidateTranscriptionError


class FixtureObservations(RecordedTranscriber):
    """Populate deterministic synthetic observations; no real ASR or provider."""
    bad_final=False
    def __call__(self,audio,locale):
        identity=observation_identity(audio,locale)
        key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        path=self.cache_root/'asr-cache'/(key+'.json')
        if not path.exists():
            result={'text':'Mauve Lune','segments':[]}
            if audio.name=='context.wav':
                result={'text':'Wrong intro. Trouve Luna.', 'segments':[{'words':[
                    {'word':'Wrong','start':.1,'end':.4}, {'word':' intro.','start':.5,'end':1.2},
                    {'word':' Trouve','start':2.0,'end':2.3},{'word':' Luna.','start':2.4,'end':2.7}]}]}
            if self.bad_final and audio.name.endswith('.validation.wav'):
                result={'text':'Far too many extra words here','segments':[]}
            write_json(path,{'identity':identity,'result':result})
        return super().__call__(audio,locale)


class ContextRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture=saved_fixture.SavedRecoveryTests();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        self.args=self.fixture.selected_source_args();self.args.policy=POLICY
        self.plan=prepare_plan(self.args,self.fixture.root)
        self.store=RunStore.create(self.fixture.base/'context-run',self.plan);self.addCleanup(self.store.close)
        self.row=self.plan['rows'][0];self.engine=self.fixture.engine
        self.raw=self.store.work/'carrier-raw'/(self.row['path']+'.raw.wav');self.raw.parent.mkdir(parents=True)
        shutil.copyfile(self.fixture.raw,self.raw);shutil.copyfile(receipt_path(self.fixture.raw),receipt_path(self.raw))
        self.transcriber=FixtureObservations(self.fixture.base/'cache')
        self.forbid=patch.object(self.engine,'generate',side_effect=AssertionError('provider forbidden'))
        self.provider=self.forbid.start();self.addCleanup(self.forbid.stop)
        self.network=patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden'))
        self.network.start();self.addCleanup(self.network.stop)
        write_json(self.store.work/'carrier-attempt-counts.json',{self.row['path']:3})

    def prepare(self):
        return prepare_saved_candidate(self.engine,self.store,self.row,self.fixture.profile,'required',transcriber=self.transcriber)

    def validate(self,candidate):
        return CorpusRunner(self.store,self.engine,'required')._validate_candidate(self.row,candidate)

    def test_recorded_context_stage_install_resume_restore_no_new_calls_or_budget(self):
        candidate=self.prepare();receipt=self.validate(candidate)
        self.assertEqual(receipt['verification']['selected_evidence'],'contextual')
        self.assertEqual(receipt['verification']['isolated']['transcript'],'Mauve Lune')
        self.assertEqual(receipt['verification']['transcript'],'Trouve Luna.')
        self.assertTrue(Path(receipt['verification']['proof']['contextual_observation']['path']).is_file())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(CorpusRunner(self.store,self.engine,'required').run(),0)
            self.assertEqual(CorpusRunner(self.store,self.engine,'required').run(),0)
        self.assertEqual(self.store.state(self.row['path']),'DONE')
        self.assertEqual(json.loads(receipt_path(self.fixture.target).read_text())['human_review'],'PENDING')
        self.assertEqual(json.loads((self.store.work/'carrier-attempt-counts.json').read_text())[self.row['path']],3)
        self.provider.assert_not_called()
        self.store.restore();self.assertEqual(self.fixture.target.read_bytes(),b'previous accepted speech')

    def test_context_recovery_requires_pinned_selection(self):
        self.args.source_selection=None
        with self.assertRaisesRegex(ValueError,'pinned source'):prepare_plan(self.args,self.fixture.root)

    def test_context_never_invokes_live_or_missing_recognition(self):
        with self.assertRaisesRegex(ValueError,'recorded-only'):
            prepare_saved_candidate(self.engine,self.store,self.row,self.fixture.profile,'required',transcriber=lambda *_:{'text':'Trouve Luna'})
        self.transcriber=RecordedTranscriber(self.fixture.base/'empty-cache')
        with self.assertRaises(CandidateTranscriptionError):self.prepare()
        self.assertEqual(self.fixture.target.read_bytes(),b'previous accepted speech')
        self.provider.assert_not_called()

    def test_recorded_observation_identity_is_checked(self):
        identity=observation_identity(self.raw,'fr')
        key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        dest=self.fixture.base/'cache/asr-cache'/(key+'.json')
        write_json(dest,{'identity':[identity[0],'en',*identity[2:]],'result':{'text':'Trouve Luna'}})
        with self.assertRaisesRegex(ValueError,'identity/result'):
            RecordedTranscriber(self.fixture.base/'cache')(self.raw,'fr')

    def test_missing_fallback_witness_cannot_hide_a_candidate(self):
        candidate=self.prepare();receipt=json.loads(receipt_path(candidate).read_text())
        quality=receipt['verification'];quality.update(contextual=None,disposition='WARN',selected_evidence='none',
                transcript=quality['isolated']['transcript'],score=quality['isolated']['score'],flags=[])
        from greia_voice_core.context_evidence import validate_quality
        with self.assertRaisesRegex(ValueError,'required fallback'):
            validate_quality(quality,source=self.raw,
                extracted=self.store.work/receipt['extracted_pcm']['path'],packaged=candidate,
                decoded=Path(quality['proof']['decoded']),text=self.row['request']['text'],locale='fr',
                policy='locale-number-tokens-v2',root=self.store.work,audio=self.engine.audio,require_pass=False)

    def test_exact_job_request_and_master_controls(self):
        rec=json.loads(receipt_path(self.raw).read_text());rec['reference_sha256']='other master'
        write_json(receipt_path(self.raw),rec)
        with self.assertRaisesRegex(ValueError,'source/master'):self.prepare()
        shutil.copyfile(receipt_path(self.fixture.raw),receipt_path(self.raw))
        rec=json.loads(receipt_path(self.raw).read_text());rec['request']['text']='other target'
        write_json(receipt_path(self.raw),rec)
        with self.assertRaisesRegex(ValueError,'provider request'):self.prepare()

    def test_wrong_completed_provider_job_rejected(self):
        selection=json.loads(self.args.source_selection.read_text())
        job=Path(selection['sources'][0]['job_manifest']);data=json.loads(job.read_text());data['id']='another job'
        write_json(job,data)
        with self.assertRaisesRegex(ValueError,'manifest changed'):self.prepare()

    def test_payload_and_observation_revalidation(self):
        candidate=self.prepare();receipt=json.loads(receipt_path(candidate).read_text())
        witness=receipt['verification']['proof']['contextual_observation'];path=Path(witness['path'])
        record=json.loads(path.read_text());record['result']['text']='Wrong intro. Trouve Luna maintenant.'
        write_json(path,record);witness['sha256']=digest(path);write_json(receipt_path(candidate),receipt)
        with self.assertRaisesRegex(ValueError,'fully covered'):self.validate(candidate)

    def test_incomplete_bounded_candidate_coverage_is_not_approval(self):
        candidate=self.prepare();receipt=json.loads(receipt_path(candidate).read_text())
        receipt['extraction']['candidate_count']+=1;write_json(receipt_path(candidate),receipt)
        with self.assertRaisesRegex(ValueError,'candidate coverage'):self.validate(candidate)

    def test_final_packaged_check_is_independent_of_candidate_verdict(self):
        # Seed exact candidate observations first, but refuse the final payload
        # witness to prove final screening is independently requested.
        original=self.transcriber
        def missing_final(audio,locale):
            if audio.name.endswith('.validation.wav'):raise FileNotFoundError('final exact observation missing')
            return original(audio,locale)
        # Keep the explicit recorded-only type and override just this instance.
        class MissingFinal(FixtureObservations):
            def __call__(self,audio,locale):return missing_final(audio,locale)
        self.transcriber=MissingFinal(self.fixture.base/'cache')
        with self.assertRaisesRegex(FileNotFoundError,'final exact'):self.prepare()
        self.assertFalse(receipt_path(self.store.work/'candidates'/self.row['path']).exists())

    def test_interrupted_audio_receipt_install_recovers_without_generation(self):
        candidate=self.prepare();self.validate(candidate)
        transaction=self.store.prepare(self.row['path'],{self.row['path']:candidate,
             str(receipt_path(Path(self.row['path']))):receipt_path(candidate)})
        import greia_voice_corpus.store as module
        real=module.atomic_bytes
        def interrupt(path,data):
            if path.resolve()==receipt_path(self.fixture.target).resolve():raise OSError('simulated crash')
            return real(path,data)
        with patch.object(module,'atomic_bytes',side_effect=interrupt):
            with self.assertRaises(OSError):self.store.install(transaction)
        self.assertEqual(self.store.state(self.row['path']),'INSTALLING')
        self.store.recover();self.assertEqual(self.store.state(self.row['path']),'DONE')
        self.provider.assert_not_called()
        self.store.restore();self.assertEqual(self.fixture.target.read_bytes(),b'previous accepted speech')

    def test_changed_original_prevents_install(self):
        candidate=self.prepare();self.validate(candidate)
        self.fixture.target.write_bytes(b'concurrent accepted take')
        with redirect_stdout(io.StringIO()):self.assertEqual(CorpusRunner(self.store,self.engine,'required').run(),2)
        self.assertEqual(self.fixture.target.read_bytes(),b'concurrent accepted take')

    def test_missing_candidate_stays_saved_only(self):
        with redirect_stdout(io.StringIO()):self.assertEqual(CorpusRunner(self.store,self.engine,'required').run(),2)
        self.provider.assert_not_called()
        with self.assertRaisesRegex(ValueError,'forbid synthesis'):
            generate_candidate(self.engine,self.store,self.row,self.fixture.profile,'required')
