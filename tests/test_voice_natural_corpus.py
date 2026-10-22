"""New method, actual retry reservations and existing transaction recovery."""
import copy,io,json,sys,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'tools'),str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).parent)]
import test_greia_voice_corpus as fixture
import test_voice_short_routing as short
from greia_voice_core.models import VoiceRequest,SpeechKind
from greia_voice_core.natural_carrier import NaturalCarrierPolicy,DELIVERY
from greia_voice_core.number_comparison import COMPARISON_POLICY
from greia_voice_core.short_phrases import ShortPhrasePipeline
from greia_voice_core.engine import VoiceEngine
from greia_voice_core.registry import VoiceRegistry
from greia_voice_core.locking import NullGenerationLock
from greia_voice_corpus.store import write_json
from greia_voice_corpus.inventory import receipt_path
from greia_voice_corpus.runner import CorpusRunner
from greia_voice_corpus.method_budget import MethodAttemptBudget
from greia_voice_corpus.automatic_generation import NATURAL_POLICY
from greia_voice_corpus.natural_run import safety_reason
from greia_voice_corpus.natural_plan import select_canary

class NaturalPolicyTests(unittest.TestCase):
 def test_four_locales_topics_preserve_targets_and_remove_imperative_pause(self):
  policy=NaturalCarrierPolicy()
  for locale,text in [('en','Count to ten'),('fr','Trouve Luna'),('it','Conta fino a dieci'),('es','Busca Luna')]:
   req=VoiceRequest('leo',SpeechKind.CHARACTER_DIALOGUE,locale,text)
   prefix,composite,direction=policy.composite(req,'ignored old instruction')
   self.assertTrue(composite.endswith('.\n\n'+text));self.assertEqual(direction,DELIVERY[locale]);self.assertNotIn('two seconds',direction);self.assertNotIn('...',prefix)
  self.assertEqual(policy.composite(VoiceRequest('tito',SpeechKind.CHARACTER_DIALOGUE,'en','Count to ten'),'')[0],"Let's practise counting together.")
  self.assertEqual(policy.composite(VoiceRequest('leo',SpeechKind.CHARACTER_DIALOGUE,'fr','Trouve Luna'),'')[0],'Nous cherchons notre amie.')
 def test_letter_number_and_overlap_are_semantic(self):
  policy=NaturalCarrierPolicy()
  letter=VoiceRequest('leo',SpeechKind.CHARACTER_DIALOGUE,'fr','A comme Abeille',cue_id='alfabeto_leo.letter_A')
  self.assertEqual(policy.topic(letter),'letter')
  req=VoiceRequest('leo',SpeechKind.CHARACTER_DIALOGUE,'en','together')
  self.assertNotIn('together',policy.composite(req,'')[0].casefold())
  self.assertEqual(policy.composite(VoiceRequest('leo',SpeechKind.CHARACTER_DIALOGUE,'it','Ciao',delivery_prompt='Quiet and warm.'),'')[2],'Quiet and warm.')

class NaturalCorpusTests(unittest.TestCase):
 def setUp(self):
  fixture.CorpusTests.setUp(self);self.fail=0
  self.row['request'].update(text='Count to ten',delivery_prompt=DELIVERY['en'])
  self.row['historical_attempts']=3;self.row['natural_topic']='number'
  req=VoiceRequest(**{k:v for k,v in self.row['request'].items() if k!='kind'},kind=SpeechKind.CHARACTER_DIALOGUE)
  policy=NaturalCarrierPolicy();prefix,text,direction=policy.composite(req,'')
  self.row['natural_carrier']={'prefix':prefix,'composite_text':text,'effective_delivery':direction,'composition_policy':policy.composition_policy,'comparison_policy':COMPARISON_POLICY}
  self.plan['automatic_short_generation_policy']=NATURAL_POLICY;self.store.plan=copy.deepcopy(self.plan);write_json(self.store.work/'plan.json',self.plan)
  write_json(self.store.work/'method-reservations.json',{'entries':{self.relative:{'prior_count':3,'attempts':[]}}});write_json(self.store.work/'carrier-attempt-counts.json',{self.relative:3})
  self.budget=MethodAttemptBudget(self.store);self.provider=short.Provider(self.base)
  def transcribe(path,locale):return {'text':'Bad different words' if len(self.provider.calls)<=self.fail else 'Count to 10','segments':[]}
  pipeline=ShortPhrasePipeline(policy=policy,transcriber=transcribe,readiness=lambda:(True,'fixture'),evidence_root=self.base/'evidence',attempt_reservation=self.budget.reserve)
  self.engine=VoiceEngine(self.root,VoiceRegistry.load(self.root),[self.provider],verifier=short.NoopVerifier(),generation_lock=NullGenerationLock(),short_phrase_pipeline=pipeline)
 def tearDown(self):self.engine.close();fixture.CorpusTests.tearDown(self)
 def run_recording(self):
  with redirect_stdout(io.StringIO()):return CorpusRunner(self.store,self.engine,'required').run(continue_after_carrier_rejection=True)
 def test_one_pass_reserves_one_new_take_and_keeps_three_historical(self):
  self.assertEqual(self.run_recording(),0);self.assertEqual(len(self.provider.calls),1)
  self.assertEqual(json.loads((self.store.work/'carrier-attempt-counts.json').read_text())[self.relative],4)
  self.assertEqual(len(self.budget.snapshot()['entries'][self.relative]['attempts']),1)
  rec=json.loads(receipt_path(self.audio).read_text());self.assertEqual(rec['attempts'],1);self.assertEqual(rec['human_review'],'PENDING')
  self.assertEqual(self.run_recording(),0);self.assertEqual(len(self.provider.calls),1)
 def test_two_rejections_then_pass_reserve_three_actual_calls_and_resume(self):
  self.fail=2;self.assertEqual(self.run_recording(),0);self.assertEqual(len(self.provider.calls),3)
  self.assertEqual(json.loads((self.store.work/'carrier-attempt-counts.json').read_text())[self.relative],6)
  self.assertEqual(json.loads(receipt_path(self.audio).read_text())['attempts'],3)
  self.assertEqual(self.run_recording(),0);self.assertEqual(len(self.provider.calls),3)
  self.store.restore();self.assertEqual(self.audio.read_bytes(),b'old accepted speech')
 def test_exhaustion_preserves_original_and_does_not_restart_budget(self):
  self.fail=9;self.assertEqual(self.run_recording(),0);self.assertEqual(len(self.provider.calls),3);self.assertEqual(self.store.state(self.relative),'PRESERVED');self.assertEqual(self.audio.read_bytes(),b'old accepted speech')
  self.assertEqual(self.run_recording(),0);self.assertEqual(len(self.provider.calls),3)
 def test_uncertain_submission_does_not_consume_more_calls(self):
  with patch.object(self.provider,'generate',side_effect=RuntimeError('provider response lost')):
   self.assertEqual(self.run_recording(),2)
  self.assertEqual(len(self.budget.snapshot()['entries'][self.relative]['attempts']),1);self.assertEqual(self.store.state(self.relative),'NEEDS_RECOVERY')
  self.assertEqual(self.run_recording(),2);self.assertFalse(self.provider.calls)
  state=json.loads(next((self.base/'evidence').glob('*/state.json')).read_text());self.assertIn('raw_request',state)
 def test_corrupt_frozen_recipe_blocks_before_submission_or_reservation(self):
  self.store.plan['rows'][0]['natural_carrier']['prefix']='Corrupt';self.assertEqual(self.run_recording(),2);self.assertFalse(self.provider.calls);self.assertFalse(self.budget.snapshot()['entries'][self.relative]['attempts'])
 def test_mirror_crash_window_repairs_without_resetting_ledger(self):
  self.assertEqual(self.run_recording(),0);write_json(self.store.work/'carrier-attempt-counts.json',{self.relative:3});self.budget.reconcile_mirror();self.assertEqual(json.loads((self.store.work/'carrier-attempt-counts.json').read_text())[self.relative],4)
  write_json(self.store.work/'carrier-attempt-counts.json',{self.relative:99})
  with self.assertRaises(ValueError):self.budget.reconcile_mirror()

class NaturalGuardTests(unittest.TestCase):
 def test_poor_method_stops_and_healthy_progress_continues(self):
  terminal=[(str(i),'PRESERVED') for i in range(3)];entries={p:{'attempts':[1,2,3]} for p,s in terminal}
  self.assertIn('consecutive',safety_reason(terminal,entries))
  healthy=[(str(i),'DONE') for i in range(12)];entries={p:{'attempts':[1]} for p,s in healthy};self.assertIsNone(safety_reason(healthy,entries))
  retrying=[(str(i),'DONE') for i in range(5)];entries={p:{'attempts':[1,2,3]} for p,s in retrying};self.assertIn('60percent',safety_reason(retrying,entries))
 def test_canary_is_deterministic_and_covers_languages_actors_topics(self):
  rows=[{'path':str(i),'request':{'locale':loc,'speaker':speaker},'natural_topic':topic} for i,(loc,speaker,topic) in enumerate([('en','leo','letter'),('fr','tito','number'),('it','momo','search'),('es','lilli','general'),('fr','flash','friend')])]
  ordered=select_canary(rows);self.assertEqual(ordered,select_canary(rows));self.assertEqual({r['request']['locale'] for r in ordered[:4]},{'en','fr','it','es'})
