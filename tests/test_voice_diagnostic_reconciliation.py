"""Registered literal diagnostic provenance; no synthesis or recognizer calls."""
import copy,json,shutil
from pathlib import Path
from types import SimpleNamespace
import unittest
from contextlib import redirect_stdout
import io
from unittest.mock import patch
import test_voice_saved_recovery as fixture
from test_voice_context_recovery import FixtureObservations
from greia_voice_corpus.diagnostic_reconciliation import POLICY as SOURCE_POLICY
from greia_voice_corpus.context_recovery import POLICY
from greia_voice_corpus.store import RunStore,write_json
from greia_voice_corpus.inventory import digest,receipt_path
from greia_voice_corpus.carrier_generation import prepare_saved_candidate
from greia_voice_corpus.runner import CorpusRunner
from recover_voice_candidates import prepare_plan


class DiagnosticReconciliationTests(unittest.TestCase):
    def setUp(self):
        f=self.f=fixture.SavedRecoveryTests();f.setUp();self.addCleanup(f.tearDown)
        args=f.selected_source_args();args.policy=POLICY;args.source_selection=None
        parent=json.loads((f.store.work/'plan.json').read_text());parent['rows'][0]['request']['cue_id']='greia.requested.hello.fr'
        write_json(f.store.work/'plan.json',parent)
        scope=json.loads(args.priority_file.read_text());scope['records'][0]['cue_id']='greia.requested.hello.fr';write_json(args.priority_file,scope)
        case={'id':'fixture-fr','speaker':'dani','locale':'fr','text':'Trouve Luna.',
              'cue_id':'example.hello','spoken':'Trouve Luna.','prefix':'Cette phrase est en français.'}
        self.case=case
        raw=f.base/'diagnostic/evidence/take/attempt-01/raw.wav';raw.parent.mkdir(parents=True);shutil.copyfile(f.raw,raw)
        rec=json.loads(receipt_path(f.raw).read_text());rec['request'].update(text=case['prefix']+'\n\n'+case['spoken'],delivery_prompt=f.row['request']['delivery_prompt'])
        rec['generation_parameters']['delivery_prompt']=f.row['request']['delivery_prompt']
        rec['generation_parameters']['script_seed']=42;write_json(receipt_path(raw),rec)
        job=f.base/'provider-job.json';j=json.loads(job.read_text());j['plan']['recordings'][0]['text']=rec['request']['text'];write_json(job,j)
        semantic={**f.row['request'],'cue_id':case['cue_id']}
        self.registration=f.base/'registration.json';self.results=f.base/'results.json'
        write_json(self.registration,{'cases':[case],'seeds':[42]})
        write_json(self.results,[{'case':case,'seed':42,'result':{'request':semantic,'evidence_dir':str(raw.parent.parent)}}])
        ledger=f.base/'ledger.json';write_json(ledger,{'takes':3})
        self.raw=raw;self.manifest=f.base/'diagnostic-source.json';self.args=args;args.diagnostic_source=self.manifest
        self.data={'schema_version':1,'policy':SOURCE_POLICY,'path':f.row['path'],'result_index':0,
                   'ledgers':[{'path':str(ledger),'sha256':digest(ledger)}]}
        for name,path in [('source_plan',f.store.work/'plan.json'),('priority_file',args.priority_file),
                 ('remaining_file',f.base/'remaining.json'),('registration',self.registration),('results',self.results),
                 ('raw',raw),('raw_receipt',receipt_path(raw)),('job_manifest',job)]:
            self.data[name]=str(path);self.data[name+'_sha256']=digest(path)
        self.save()

    def save(self):write_json(self.manifest,self.data)
    def build(self):return prepare_plan(self.args,self.f.root)
    def revise_case(self,key,value):
        reg=json.loads(self.registration.read_text());reg['cases'][0][key]=value;write_json(self.registration,reg)
        results=json.loads(self.results.read_text());results[0]['case'][key]=value;write_json(self.results,results)
        self.data['registration_sha256']=digest(self.registration);self.data['results_sha256']=digest(self.results);self.save()

    def test_aliases_preserved_and_stage_install_restore_provider_forbidden(self):
        plan=self.build();row=plan['rows'][0]
        self.assertEqual(row['request']['cue_id'],'greia.requested.hello.fr')
        self.assertEqual(json.loads(receipt_path(self.raw).read_text())['request']['cue_id'],'example.hello')
        self.assertEqual(row['spoken_carrier']['composite_text'],self.case['prefix']+'\n\nTrouve Luna.')
        store=RunStore.create(self.f.base/'diagnostic-recovery',plan);self.addCleanup(store.close)
        dst=store.work/'carrier-raw'/(row['path']+'.raw.wav');dst.parent.mkdir(parents=True)
        shutil.copyfile(self.raw,dst);shutil.copyfile(receipt_path(self.raw),receipt_path(dst))
        with patch.object(self.f.engine,'generate',side_effect=AssertionError('provider forbidden')):
            candidate=prepare_saved_candidate(self.f.engine,store,row,self.f.profile,'required',
                         transcriber=FixtureObservations(self.f.base/'cache'))
            CorpusRunner(store,self.f.engine,'required')._validate_candidate(row,candidate)
            with redirect_stdout(io.StringIO()):self.assertEqual(CorpusRunner(store,self.f.engine,'required').run(),0)
            self.assertEqual(store.state(row['path']),'DONE')
            self.assertEqual(json.loads(receipt_path(self.f.target).read_text())['human_review'],'PENDING')
            store.restore();self.assertEqual(self.f.target.read_bytes(),b'previous accepted speech')

    def test_other_activity_same_words_is_not_a_valid_mapping(self):
        self.revise_case('cue_id','different_activity.hello')
        with self.assertRaisesRegex(ValueError,'another Activity'):self.build()

    def test_spoken_variant_requires_its_own_comparison_policy(self):
        self.revise_case('spoken','A different spoken representation')
        with self.assertRaisesRegex(ValueError,'comparison policy'):self.build()

    def test_changed_original_is_not_reconciled_away(self):
        self.f.target.write_bytes(b'another approved take')
        with self.assertRaisesRegex(ValueError,'destination pair'):self.build()

    def test_changed_budget_or_missing_pin_rejects(self):
        Path(self.data['ledgers'][0]['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'ledger changed'):self.build()
        self.data['ledgers']=[];self.save()
        with self.assertRaisesRegex(ValueError,'ledger pins'):self.build()

    def test_wrong_diagnostic_result_or_raw_receipt_rejects(self):
        self.data['result_index']=1;self.save()
        with self.assertRaisesRegex(ValueError,'result index'):self.build()
        self.data['result_index']=0;self.save()
        rec=json.loads(receipt_path(self.raw).read_text());rec['request']['text']='another actual script'
        write_json(receipt_path(self.raw),rec);self.data['raw_receipt_sha256']=digest(receipt_path(self.raw));self.save()
        with self.assertRaisesRegex(ValueError,'actual provider request'):self.build()
