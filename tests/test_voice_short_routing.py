"""Public engine automatic routing using real cutter and audio packaging."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from greia_voice import build_parser, _request_from_args
from greia_voice_core.engine import VoiceEngine
from greia_voice_core.locking import NullGenerationLock
from greia_voice_core.models import (GeneratedTake, GenerationDisposition, ProviderStatus,
    SpeechKind, VerificationDisposition, VerificationMode, VerificationResult, VoiceProfile, VoiceRequest)
from greia_voice_core.service import request_from_mapping
from greia_voice_core.short_phrases import ShortPhrasePipeline
from greia_voice_core.short_policy import ShortPhrasePolicy, PREFIXES


class Provider:
    provider_id = 'voxstage-voxcpm2'
    sample_rate = 22050
    supports_delivery_prompt = supports_spoken_carrier = True
    def __init__(self, folder): self.folder, self.calls = folder, []
    def supports(self, request, profile): return True
    def probe(self): return ProviderStatus(self.provider_id, True, 'fixture')
    def generate(self, request, profile):
        self.calls.append(request)
        path = self.folder / f'provider-{len(self.calls)}.wav'
        rate = self.sample_rate
        samples = [0] * (rate * 3)
        for start, end in ((.1, 1.45), (2., 2.8)):
            for i in range(round(start*rate), round(end*rate)):
                samples[i] = int(5000 * math.sin(i*.07))
        with wave.open(str(path), 'wb') as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate)
            out.writeframes(struct.pack(f'<{len(samples)}h', *samples))
        return GeneratedTake(self.provider_id, path, rate, {'job_id':f'fixture-{len(self.calls)}'})
    def close(self): pass


class NoopVerifier:
    verifier_id = 'none'
    def verify(self, request, path):
        return VerificationResult(VerificationDisposition.NOT_APPLICABLE, 'none')


class AutomaticShortRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.repo = self.base/'repo'; self.repo.mkdir()
        self.provider = Provider(self.base)
        self.asr_calls = []
        self.target = 'Find Luna'
        self.fail_takes = 0
        def transcribe(path, locale):
            self.asr_calls.append((path, locale))
            words = self.target.split()
            if path.name.endswith('raw.wav'):
                timing = [{'word':'unreliable-intro', 'start':.1, 'end':1.45}]
                timing += [{'word': w, 'start':2+i*.8/len(words), 'end':2+(i+1)*.8/len(words)} for i,w in enumerate(words)]
                return {'text': 'unreliable-intro '+self.target, 'segments':[{'words':timing}]}
            text = 'wrong words' if len(self.provider.calls) <= self.fail_takes else self.target
            retained=text.split()
            return {'text':text,'segments':[{'words':[{'word':w,'start':.3+i*.7/len(retained),'end':.3+(i+1)*.7/len(retained)} for i,w in enumerate(retained)]}]}
        self.pipeline = ShortPhrasePipeline(transcriber=transcribe, readiness=lambda:(True,'fixture'),
                                             evidence_root=self.base/'evidence')
        profiles = {name: VoiceProfile(name,'test.'+name,'cloned_reference','fixture')
                    for name in ('leo','dani','momo','tito','lilli','flash')}
        registry = SimpleNamespace(get=lambda name:profiles[name], registry_version='test', verify_anchor=lambda p:None)
        self.engine = VoiceEngine(self.repo, registry, [self.provider], verifier=NoopVerifier(),
                                  generation_lock=NullGenerationLock(), short_phrase_pipeline=self.pipeline)
    def tearDown(self): self.tmp.cleanup()
    def request(self, **kw):
        return VoiceRequest(**({'speaker':'leo','kind':SpeechKind.CHARACTER_DIALOGUE,'locale':'en',
                                'text':self.target,'output':self.base/'result.wav'} | kw))

    def test_all_locales_and_all_actors_route_without_caller_wrapping(self):
        for speaker in ('leo','dani','momo','tito','lilli','flash'):
            for locale, target in {'en':'Find Luna','it':'Trova Luna','fr':'Trouve Luna','es':'Busca Luna'}.items():
                with self.subTest(speaker=speaker, locale=locale):
                    self.target = target
                    result = self.engine.generate(self.request(speaker=speaker,locale=locale,
                        kind=SpeechKind.DANI_SYSTEM_SPEECH if speaker=='dani' else SpeechKind.CHARACTER_DIALOGUE))
                    self.assertEqual(result.disposition, GenerationDisposition.REVIEW_REQUIRED, result.detail)
                    self.assertEqual(result.verification.disposition, VerificationDisposition.PASS)
                    self.assertEqual(result.attempts, 1)
                    sent = self.provider.calls[-1]
                    self.assertEqual(sent.text, PREFIXES[locale].rstrip('.')+'.\n\n'+target)
                    self.assertEqual(sent.short_text_mode, 'off')
                    self.assertEqual(sent.verification, VerificationMode.OFF)
                    receipt=json.loads(result.receipt_path.read_text())
                    self.assertEqual(receipt['request']['text'],target)
                    self.assertEqual(receipt['human_review'],'PENDING')
                    self.assertIn('short_phrase',receipt)
                    self.assertEqual(receipt['short_phrase']['extraction']['algorithm_version'],
                                     'greia-spoken-carrier-extractor-v7')
                    self.assertTrue(all(p.name != 'raw.wav' for p, _ in self.asr_calls))
                    with wave.open(str(result.output_path)) as wav:
                        self.assertLess(wav.getnframes()/wav.getframerate(),1.5)

    def test_all_actor_locale_routes_package_48khz_provider_audio(self):
        self.provider.sample_rate = 48000
        for speaker in ('leo','dani','momo','tito','lilli','flash'):
            for locale,target in {'en':'Find Luna','it':'Trova Luna','fr':'Trouve Luna','es':'Busca Luna'}.items():
                with self.subTest(speaker=speaker,locale=locale):
                    self.target=target
                    result=self.engine.generate(self.request(speaker=speaker,locale=locale,max_attempts=1))
                    self.assertEqual(result.disposition,GenerationDisposition.REVIEW_REQUIRED,result.detail)
                    receipt=json.loads(result.receipt_path.read_text())
                    self.assertEqual(receipt['short_phrase']['extraction']['sample_rate'],48000)
                    self.assertEqual(receipt['short_phrase']['quality']['disposition'],'PASS')
                    self.assertTrue(result.evidence_dir.is_dir())

    def test_retry_until_pass_up_to_three(self):
        self.fail_takes=2
        result=self.engine.generate(self.request())
        self.assertEqual(result.attempts,3)
        self.assertEqual(result.verification.disposition,VerificationDisposition.PASS)
        self.assertEqual(len(list((self.base/'evidence').rglob('raw.wav'))),3)

    def test_exhaustion_does_not_publish_or_overwrite_previous_output(self):
        self.fail_takes=9
        out=self.base/'result.wav';out.write_bytes(b'previous accepted audio')
        rec=out.with_suffix('.wav.receipt.json');rec.write_bytes(b'previous receipt')
        result=self.engine.generate(self.request(max_attempts=4))
        self.assertEqual(result.disposition,GenerationDisposition.REJECTED)
        self.assertIsNone(result.output_path)
        self.assertEqual(result.attempts,3)
        self.assertEqual(out.read_bytes(),b'previous accepted audio')
        self.assertEqual(rec.read_bytes(),b'previous receipt')

    def test_unavailable_alignment_stops_before_synthesis_even_if_check_off(self):
        self.pipeline.readiness=lambda:(False,'not cached')
        result=self.engine.generate(self.request(verification=VerificationMode.OFF))
        self.assertEqual(result.disposition,GenerationDisposition.UNAVAILABLE)
        self.assertEqual(len(self.provider.calls),0)

    def test_off_skips_quality_but_auto_still_extracts(self):
        result=self.engine.generate(self.request(verification=VerificationMode.OFF))
        self.assertTrue(result.output_path)
        self.assertEqual(result.verification.disposition,VerificationDisposition.NOT_RUN)
        self.assertEqual(len(self.asr_calls),1)  # target-only; no raw-intro ASR
        self.asr_calls.clear()
        result=self.engine.generate(self.request(verification=VerificationMode.OFF, short_text_mode='off'))
        self.assertEqual(len(self.asr_calls),0)
        self.assertNotIn('short_phrase',json.loads(result.receipt_path.read_text()))

    def test_provider_failure_never_allocates_another_take(self):
        with patch.object(self.provider,'generate',side_effect=RuntimeError('worker crashed')) as call:
            result=self.engine.generate(self.request())
        self.assertEqual(call.call_count,1)
        self.assertIsNone(result.output_path)
        state=json.loads(next((self.base/'evidence').rglob('state.json')).read_text())
        self.assertEqual(state['status'],'NEEDS_RECOVERY')

    def test_search_disk_error_never_spends_another_synthesis_take(self):
        with patch('voice_carrier_search._write_pcm', side_effect=OSError('disk full')):
            result = self.engine.generate(self.request())
        self.assertEqual(len(self.provider.calls), 1)
        self.assertIsNone(result.output_path)
        state = json.loads(next((self.base/'evidence').rglob('state.json')).read_text())
        self.assertEqual(state['status'], 'NEEDS_RECOVERY')
        self.assertEqual(len(list((self.base/'evidence').rglob('raw.wav'))), 1)
        self.assertEqual(self.asr_calls, [])

    def test_asr_crash_retains_one_raw_without_a_new_generation(self):
        def broken(*args): raise RuntimeError('ASR worker crashed')
        self.pipeline.transcriber=broken
        result=self.engine.generate(self.request())
        self.assertEqual(len(self.provider.calls),1)
        self.assertIsNone(result.output_path)
        self.assertEqual(len(list((self.base/'evidence').rglob('raw.wav'))),1)

    def test_delivery_trim_stays_in_verified_silence_and_preserves_speech_samples(self):
        from greia_voice_core.short_delivery import prepare_delivery
        rate=22050
        samples=[0]*round(.5*rate)+[6000]*round(.2*rate)
        source=self.base/'extracted.wav';dest=self.base/'delivery.wav'
        with wave.open(str(source),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
            out.writeframes(struct.pack(f'<{len(samples)}h',*samples))
        info=prepare_delivery(source,dest,{'sample_rate':rate,'boundary':{
            'verified_silence_start_seconds':1.,'verified_silence_end_seconds':2.,'cut_sample':round(1.5*rate)}})
        with wave.open(str(dest)) as wav:
            remaining=struct.unpack(f'<{wav.getnframes()}h',wav.readframes(wav.getnframes()))
        self.assertEqual(list(remaining),samples[info['removed_frames']:])
        self.assertGreaterEqual(remaining.index(6000),round(.1*rate))
        self.assertEqual(sum(x==6000 for x in remaining),round(.2*rate))

    def test_policy_thresholds_semantic_exemption_and_explicit_override(self):
        policy=ShortPhrasePolicy()
        self.assertTrue(policy.selected(self.request(text='One two three four'),self.provider))
        self.assertFalse(policy.selected(self.request(text='One two three four five'),self.provider))
        self.assertTrue(policy.selected(self.request(text='One two three four five',short_text_max_words=5),self.provider))
        self.assertFalse(policy.selected(self.request(short_text_max_alnum=2),self.provider))
        self.assertFalse(policy.selected(self.request(kind=SpeechKind.PEDAGOGICAL_SPEECH,speaker='pedagogical',short_text_mode='on'),self.provider))
        self.assertFalse(policy.selected(self.request(short_text_mode='off'),self.provider))
        self.assertTrue(policy.selected(self.request(text='One two three four five',short_text_mode='on'),self.provider))

    def test_cli_and_json_forward_the_same_default_and_overrides(self):
        args=build_parser().parse_args(['generate','--speaker','leo','--kind','character_dialogue','--locale','en','--text','Find Luna','--short-text-max-words','2','--short-text-max-alnum','12','--short-text-mode','off'])
        req=_request_from_args(args)
        self.assertEqual((req.short_text_mode,req.short_text_max_words,req.short_text_max_alnum),('off',2,12))
        normal=request_from_mapping({'speaker':'leo','kind':'character_dialogue','locale':'en','text':'Find Luna'})
        self.assertEqual((normal.short_text_mode,normal.short_text_max_words,normal.max_attempts),('auto',4,3))
        self.assertEqual(request_from_mapping(normal.to_dict()),normal)
        for invalid in ({'short_text_max_words':False},{'short_text_max_alnum':0},{'short_text_mode':'guess'}):
            with self.assertRaises(ValueError):self.request(**invalid)

    def test_extra_word_is_rejected_even_if_similarity_exceeds_threshold(self):
        self.target='Find Luna Luna'
        # The raw target must stay the request; the retained recognizer adds a word.
        from greia_voice_core.target_quality import TargetQualityChecker
        with patch('voice_carrier._read_pcm16',return_value=(22050,1,[1])), patch('greia_voice_core.target_quality.signal_metrics',return_value=({},[])):
            q=TargetQualityChecker(lambda p,l:{}).check(Path('a'),Path('b'),
                {'extracted_transcript':'Find Luna Luna','model_id':'test','model_revision':'test'},
                text='Find Luna',locale='en',require_word_count=True)
        self.assertGreater(q['score'],.8)
        self.assertEqual(q['disposition'],'WARN')
        self.assertIn('TARGET_WORD_COUNT_MISMATCH',q['flags'])

    def test_real_socket_service_routes_a_plain_request(self):
        import socket
        import threading
        import time
        from greia_voice_core.service import serve_loop, send_request
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        thread=threading.Thread(target=serve_loop,args=('127.0.0.1',port,
            lambda request:self.engine.generate(request).to_dict()),daemon=True)
        thread.start()
        try:
            for _ in range(100):
                try:
                    result=send_request('127.0.0.1',port,self.request().to_dict())
                    break
                except ConnectionRefusedError:time.sleep(.01)
            else:self.fail('socket service did not start')
            self.assertTrue(result['ok'])
            self.assertEqual(result['result']['verification']['disposition'],'PASS')
            self.assertEqual(len(self.provider.calls),1)
            self.assertIn('.\n\nFind Luna',self.provider.calls[0].text)
        finally:
            send_request('127.0.0.1',port,{'command':'shutdown'})
            thread.join(timeout=3)
        self.assertFalse(thread.is_alive())

    def test_explicit_corpus_carrier_is_not_wrapped_twice_by_real_engine(self):
        from greia_voice_corpus.carriers import freeze_row
        from greia_voice_corpus.carrier_generation import generate_candidate
        row={'path':'example.wav','state':'READY','request':{
            'speaker':'leo','kind':'character_dialogue','locale':'en','text':self.target,
            'cue_id':'example','delivery_prompt':'Clear, natural delivery.'}}
        row['spoken_carrier']=freeze_row(row,'warn')
        candidate=generate_candidate(self.engine,SimpleNamespace(work=self.base/'corpus'),row,
            self.engine.registry.get('leo'),'required',transcriber=self.pipeline.transcriber)
        self.assertTrue(candidate.is_file())
        self.assertEqual(len(self.provider.calls),1)
        self.assertEqual(self.provider.calls[0].text,row['spoken_carrier']['composite_text'])
        self.assertEqual(self.provider.calls[0].short_text_mode,'off')
        self.assertFalse((self.base/'evidence').exists())
