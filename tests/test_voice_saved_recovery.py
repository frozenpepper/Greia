"""Provider-free v7 corpus recovery, promotion and failure controls."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src'), str(ROOT/'tests')]
import test_voice_carrier_generation as fixture
from greia_voice_core.models import VoiceRequest, SpeechKind, VerificationMode
from greia_voice_core.registry import VoiceRegistry, CANONICAL_MANIFEST
from greia_voice_corpus.carriers import freeze_row
from greia_voice_corpus.carrier_generation import prepare_saved_candidate, CarrierExtractionFailure, generate_candidate
from greia_voice_corpus.inventory import digest, receipt_path
from greia_voice_corpus.saved_recovery import POLICY, validate_recovery_receipt
from greia_voice_corpus.runner import CorpusRunner
from greia_voice_corpus.store import RunStore, write_json, atomic_bytes
from recover_voice_candidates import SavedAudioEngine, prepare_plan, install


class SavedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.base=Path(self.temp.name)
        self.root=self.base/'repo';self.root.mkdir()
        atomic_bytes(self.root/CANONICAL_MANIFEST,(ROOT/CANONICAL_MANIFEST).read_bytes())
        for profile in VoiceRegistry.load(ROOT).profiles.values():
            atomic_bytes(self.root/profile.anchor_path.relative_to(ROOT),profile.anchor_path.read_bytes())
        self.profile=VoiceRegistry.load(self.root).get('dani')
        rel='activities/example/assets/audio/fr/hello.wav'
        self.row={'path':rel,'state':'READY','reason':'saved recovery','request':{
            'speaker':'dani','kind':'character_dialogue','locale':'fr','text':'Trouve Luna.',
            'cue_id':'example.hello','delivery_prompt':'Clear and kind.'}}
        self.row['spoken_carrier']=freeze_row(self.row,'warn')
        self.target=self.root/rel
        atomic_bytes(self.target,b'previous accepted speech')
        write_json(receipt_path(self.target),{'original':True})
        self.row.update(original_sha256=digest(self.target),original_receipt_sha256=digest(receipt_path(self.target)))
        self.plan={'root':str(self.root),'rows':[self.row], 'saved_recovery_policy':POLICY,
                   'registry_manifest_sha256':digest(self.root/CANONICAL_MANIFEST)}
        self.store=RunStore.create(self.base/'run',self.plan)
        raw=self.store.work/'carrier-raw'/(rel+'.raw.wav');raw.parent.mkdir(parents=True)
        req=self.row['request'];c=self.row['spoken_carrier']
        request=VoiceRequest(**{**req,'text':c['composite_text'],'delivery_prompt':c['composite_delivery_prompt'],
                                'kind':SpeechKind.CHARACTER_DIALOGUE},output=raw,verification=VerificationMode.OFF,
                             short_text_mode='off')
        fixture.FakeEngine(self.root).generate(request)
        receipt=json.loads(receipt_path(raw).read_text())
        receipt.update(voice_id=self.profile.voice_id, reference_sha256=self.profile.anchor_sha256)
        write_json(receipt_path(raw),receipt)
        self.raw=raw;self.engine=SavedAudioEngine()
        self.transcribe=lambda path,locale:{'text':'Trouve Luna.','segments':[]}

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def prepare(self):
        return prepare_saved_candidate(self.engine,self.store,self.row,self.profile,'required',transcriber=self.transcribe)

    def test_stage_install_resume_restore_without_provider(self):
        with patch.object(self.engine,'generate',side_effect=AssertionError('provider forbidden')) as generate:
            candidate=self.prepare()
            receipt=json.loads(receipt_path(candidate).read_text())
            self.assertEqual(receipt['extraction']['algorithm_version'],'greia-spoken-carrier-extractor-v7')
            self.assertEqual(receipt['extraction']['target_verification_policy'],'warn')
            self.assertEqual(receipt['verification']['comparison_policy'],'locale-number-tokens-v1')
            with redirect_stdout(io.StringIO()):
                self.assertEqual(CorpusRunner(self.store,self.engine,'required').run(),0)
                self.assertEqual(CorpusRunner(self.store,self.engine,'required').run(),0)
            self.assertEqual(self.store.state(self.row['path']),'DONE')
            self.assertEqual(json.loads(receipt_path(self.target).read_text())['human_review'],'PENDING')
            generate.assert_not_called()
        self.store.restore();self.assertEqual(self.target.read_bytes(),b'previous accepted speech')

    def test_missing_candidate_never_calls_provider_or_consumes_budget(self):
        write_json(self.store.work/'carrier-attempt-counts.json',{self.row['path']:3})
        with patch.object(self.engine,'generate',side_effect=AssertionError('provider forbidden')) as generate:
            with redirect_stdout(io.StringIO()):self.assertEqual(CorpusRunner(self.store,self.engine,'required').run(),2)
            generate.assert_not_called()
        self.assertEqual(json.loads((self.store.work/'carrier-attempt-counts.json').read_text())[self.row['path']],3)
        with self.assertRaisesRegex(ValueError,'forbid synthesis'):
            generate_candidate(self.engine,self.store,self.row,self.profile,'required')

    def test_wrong_or_extra_text_never_publishes_candidate(self):
        self.transcribe=lambda path,locale:{'text':'Trouve Luna maintenant.','segments':[]}
        with self.assertRaises(CarrierExtractionFailure):self.prepare()
        self.assertEqual(self.target.read_bytes(),b'previous accepted speech')
        self.assertFalse((self.store.work/'candidates'/self.row['path']).exists())

    def test_master_or_exact_provider_request_mismatch_rejects(self):
        rec=json.loads(receipt_path(self.raw).read_text());rec['request']['text']='Wrong intro and target.'
        write_json(receipt_path(self.raw),rec)
        with self.assertRaisesRegex(ValueError,'provider request differs'):self.prepare()

    def test_recovery_verification_cannot_be_disabled(self):
        with self.assertRaisesRegex(ValueError,'requires final verification'):
            prepare_saved_candidate(self.engine,self.store,self.row,self.profile,'off',transcriber=self.transcribe)

    def test_v7_receipt_needs_explicit_plan_and_recomputed_final_guards(self):
        candidate=self.prepare();receipt=json.loads(receipt_path(candidate).read_text())
        with self.assertRaisesRegex(ValueError,'explicit recovery plan'):validate_recovery_receipt(receipt,False)
        receipt['verification']['transcript']='Trouve Luna maintenant.'
        with self.assertRaisesRegex(ValueError,'canonical quality'):validate_recovery_receipt(receipt,True)

    def test_interrupted_install_recovers_receipt_pair_without_provider(self):
        candidate=self.prepare()
        tid=self.store.prepare(self.row['path'],{self.row['path']:candidate,
              str(receipt_path(Path(self.row['path']))):receipt_path(candidate)})
        real_atomic=__import__('greia_voice_corpus.store',fromlist=['atomic_bytes']).atomic_bytes
        def interrupt(path,data):
            if path.resolve()==receipt_path(self.target).resolve():raise OSError('simulated crash')
            return real_atomic(path,data)
        with patch('greia_voice_corpus.store.atomic_bytes',side_effect=interrupt):
            with self.assertRaises(OSError):self.store.install(tid)
        self.assertEqual(self.store.state(self.row['path']),'INSTALLING')
        self.store.recover();self.assertEqual(self.store.state(self.row['path']),'DONE')
        self.assertEqual(json.loads(receipt_path(self.target).read_text())['human_review'],'PENDING')
        self.store.restore();self.assertEqual(self.target.read_bytes(),b'previous accepted speech')


    def test_source_priority_semantics_and_changed_destination_block_before_staging(self):
        self.store.set_state(self.row['path'],'FAILED','old acoustic rejection')
        source_plan=copy.deepcopy(self.plan);source_plan.pop('saved_recovery_policy')
        write_json(self.store.work/'plan.json',source_plan)
        priority=self.base/'priority.json'
        record={key:self.row['request'][key] for key in ('speaker','locale','text','cue_id')}
        record['path']=self.row['path'];write_json(priority,{'records':[record]})
        args=SimpleNamespace(source_work=self.store.work,history_root=self.base,priority_file=priority)
        self.assertEqual(len(prepare_plan(args,self.root)['rows']),1)
        record['text']='Wrong target';write_json(priority,{'records':[record]})
        with self.assertRaisesRegex(ValueError,'semantic request'):prepare_plan(args,self.root)
        record['text']=self.row['request']['text'];write_json(priority,{'records':[record]})
        atomic_bytes(self.target,b'later owner change')
        with self.assertRaisesRegex(ValueError,'destination changed'):prepare_plan(args,self.root)

    def test_wrong_number_cannot_hide_behind_reported_high_score(self):
        receipt=json.loads(receipt_path(self.prepare()).read_text())
        receipt['target_request']['text']='Trouve 10.'
        receipt['verification'].update(transcript='Trouve 11.',score=.99,flags=[])
        with self.assertRaisesRegex(ValueError,'canonical quality'):validate_recovery_receipt(receipt,True)

    def test_install_rejects_changed_cumulative_budget_manifest(self):
        write_json(self.store.work/'carrier-attempt-counts.json',{self.row['path']:3})
        write_json(self.store.work/'recovery-results.json',[])
        marker={'plan_sha256':digest(self.store.work/'plan.json'),
                'counts_sha256':digest(self.store.work/'carrier-attempt-counts.json'),
                'results_sha256':digest(self.store.work/'recovery-results.json')}
        write_json(self.store.work/'stage-complete.json',marker)
        write_json(self.store.work/'carrier-attempt-counts.json',{self.row['path']:0})
        with self.assertRaisesRegex(ValueError,'manifest/evidence changed'):install(self.store.work)
