"""Provider-free proofs for the disabled saved-WAV candidate seam.

Synthetic PCM/timestamps prove plumbing and fail-closed behavior, not ASR yield.
"""
import copy
import math
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from greia_voice_core.context_timing import TimedTargetSlice
from greia_voice_core.contextual_target import ContextualTargetChecker, PackagedCandidateVerifier
from greia_voice_core.target_quality import TargetQualityChecker
from greia_voice_core.audio import AudioPipeline
from voice_carrier import ExtractionRejected
from voice_carrier_search import extract, CONTEXT_ALGORITHM_VERSION, CandidateTranscriptionError
from test_voice_carrier_search import _wav, _two_gap_wav


def pcm(path, seconds=1, rate=22050):
    frames = struct.pack('<'+'h'*round(seconds*rate), *[
        int(8000*math.sin(i*.13)) for i in range(round(seconds*rate))])
    write(path, rate, frames)
    return frames


def write(path, rate, frames):
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(frames)


def timed(text='Wrong intro. Basket full.'):
    return {'text':text, 'segments':[{'words':[
        {'word':'Wrong', 'start':.1, 'end':.3},
        {'word':' intro.', 'start':.4, 'end':.7},
        {'word':' Basket', 'start':1.1, 'end':1.4},
        {'word':' full.', 'start':1.5, 'end':1.8}]}]}


class CopyAudio:
    """PCM already canonical; integration below also exercises real FFmpeg."""
    def package(self, source, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
        return output

    def decode_for_review(self, source, output):
        shutil.copyfile(source, output)


class TimingTests(unittest.TestCase):
    def test_complete_target_uses_all_words_after_fixed_boundary(self):
        result = TimedTargetSlice.from_result(timed(), prefix_seconds=1, duration_seconds=2)
        self.assertEqual(result.transcript, 'Basket full.')
        self.assertFalse(result.straddling)

    def test_bad_or_incomplete_timings_rejected(self):
        cases=[]
        for value in [float('nan'), float('inf'), True, -1, 2.5]:
            item=timed(); item['segments'][0]['words'][0]['start']=value; cases.append(item)
        item=timed(); item['text'] += ' omitted'; cases.append(item)
        item=timed(); item['segments'][0]['words'][2]['start']=.5; cases.append(item)
        item=timed(); item['segments'][0]['words'][2]['end']=1.1; cases.append(item)
        cases += [{'text':'Basket', 'segments':[]}, {'text':'Basket'}, {'text':'Basket','segments':[{}]}]
        for item in cases:
            with self.subTest(item=item), self.assertRaises(ValueError):
                TimedTargetSlice.from_result(item, prefix_seconds=1, duration_seconds=2)

    def test_recognizer_real_scalar_timestamps_are_valid(self):
        # Actual mlx-whisper arithmetic uses numpy.float64, not type(float).
        import numpy as np
        item=timed()
        for word in item['segments'][0]['words']:
            word['start']=np.float64(word['start']);word['end']=np.float64(word['end'])
        result=TimedTargetSlice.from_result(item,prefix_seconds=1,duration_seconds=2)
        self.assertEqual(result.transcript,'Basket full.')

    def test_straddling_word_is_retained_as_conflict(self):
        item=timed(); item['segments'][0]['words'][2]['start']=.9
        result=TimedTargetSlice.from_result(item, prefix_seconds=1,duration_seconds=2)
        self.assertEqual(len(result.straddling),1)
        self.assertEqual(result.transcript,'full.')

    def test_invalid_boundary(self):
        for boundary in [0,2,float('nan'),True]:
            with self.subTest(boundary=boundary),self.assertRaises(ValueError):
                TimedTargetSlice.from_result(timed(),prefix_seconds=boundary,duration_seconds=2)


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'source.wav'; self.suffix=self.root/'suffix.wav'
        self.package=self.root/'actual.wav'; self.decoded=self.root/'decoded.wav'
        target=pcm(self.suffix); write(self.source,22050,target+target)
        shutil.copyfile(self.suffix,self.package); shutil.copyfile(self.package,self.decoded)
        # Any accidental network/provider operation is fatal to these tests.
        self.network=patch('urllib.request.urlopen',side_effect=AssertionError('provider forbidden'))
        self.network.start(); self.addCleanup(self.network.stop)

    def check(self, isolated, context=None, **options):
        calls=[]
        def transcribe(path,locale):
            calls.append(path)
            return {'text':isolated} if len(calls)==1 else (context or timed())
        checker=ContextualTargetChecker(CopyAudio(),transcribe,self.root/'evidence')
        result=checker.check(self.source,self.suffix,self.decoded,self.package,
                             cut_sample=22050,text='Basket full!',locale='en',**options)
        return result,calls

    def test_isolated_pass_skips_context(self):
        result,calls=self.check('Basket full.')
        self.assertEqual(result['selected_evidence'],'isolated'); self.assertEqual(len(calls),1)

    def test_substitution_rescued_without_intro_correctness(self):
        result,calls=self.check('Racket fall')
        self.assertEqual(result['disposition'],'PASS'); self.assertEqual(len(calls),2)
        self.assertEqual(result['isolated']['transcript'],'Racket fall')
        self.assertEqual(result['selected_evidence'],'contextual')
        proof=result['proof']; self.assertEqual(proof['prefix_frames'],22050)
        self.assertTrue(proof['context_payload_identical'])
        self.assertFalse(proof['intro_wording_agreement_required'])

    def test_captured_false_approval_is_independently_vetoed(self):
        calls=[]
        def asr(path,locale):
            calls.append(path)
            return {'text':'Vamos a hablar con calma, Zestes, el IG un álbum.'}
        checker=ContextualTargetChecker(CopyAudio(),asr,self.root/'evidence')
        result=checker.check(self.source,self.suffix,self.decoded,self.package,
                    cut_sample=22050,text='¡Elige un álbum!',locale='es')
        self.assertEqual(result['disposition'],'WARN')
        self.assertIn('TARGET_WORD_COUNT_MISMATCH',result['flags'])
        self.assertEqual(len(calls),1)

    def test_number_equivalence_and_conflict_in_each_locale(self):
        for locale,word in [('en','ten'),('it','dieci'),('fr','dix'),('es','diez')]:
            for expected,passes in [('10',True),('11',False)]:
                calls=[]
                def asr(path,locale):
                    calls.append(path);return {'text':word}
                checker=ContextualTargetChecker(CopyAudio(),asr,self.root/'evidence')
                result=checker.check(self.source,self.suffix,self.decoded,self.package,
                        cut_sample=22050,text=expected,locale=locale)
                self.assertEqual(result['disposition']=='PASS',passes)
                self.assertEqual(len(calls),1)

    def test_signal_flags_never_rescued(self):
        with patch('greia_voice_core.contextual_target.signal_metrics',return_value=({},['LOW_LEVEL'])):
            result,calls=self.check('Racket fall')
            self.assertEqual(result['disposition'],'WARN');self.assertEqual(len(calls),1)
        with patch('greia_voice_core.contextual_target.signal_metrics',side_effect=ValueError('silent')):
            result,calls=self.check('Basket full')
            self.assertIn('INVALID_SIGNAL',result['flags']);self.assertEqual(len(calls),1)

    def test_final_quality_uses_same_fixed_delivery_checker(self):
        checker=ContextualTargetChecker(CopyAudio(),lambda *_:{'text':'Basket full'},self.root/'evidence')
        quality=TargetQualityChecker(context_checker=checker).check(self.suffix,self.decoded,
            {'boundary':{'cut_sample':22050}},source=self.source,packaged=self.package,
            text='Basket full',locale='en')
        self.assertEqual(quality['disposition'],'PASS')
        self.assertTrue(quality['proof']['packaged_suffix_matches'])

    def test_extra_missing_number_empty_isolated_veto_never_calls_context(self):
        for text in ['Intro Basket full','Basket','Basket 4','', 'Vamos a hablar con calma Zestes el IG un album']:
            with self.subTest(text=text):
                result,calls=self.check(text)
                self.assertEqual(result['disposition'],'WARN'); self.assertEqual(len(calls),1)
                self.assertIsNone(result['contextual'])

    def test_context_cannot_drop_extra_or_change_number(self):
        for text, words in [ ('Wrong intro. Basket full now.',[
                {'word':' now.','start':1.85,'end':1.95}]),
                ('Wrong intro. Basket 4.',[]) ]:
            context=timed();context['text']=text
            if words: context['segments'][0]['words'] += words
            else: context['segments'][0]['words'][-1]['word']=' 4.'
            result,_=self.check('Racket fall',context)
            self.assertEqual(result['disposition'],'WARN')

    def test_straddling_word_fails(self):
        context=timed();context['segments'][0]['words'][2]['start']=.9
        result,_=self.check('Racket fall',context)
        self.assertIn('CONTEXT_BOUNDARY_STRADDLES_WORD',result['flags'])
        self.assertEqual(result['disposition'],'WARN')

    def test_partial_clock_is_infrastructure_error(self):
        with self.assertRaises(ValueError): self.check('Racket fall',{'text':'Basket full','segments':[]})

    def test_tampered_package_rejected_before_asr(self):
        pcm(self.package,seconds=.5)
        with self.assertRaisesRegex(ValueError,'payload differ'): self.check('Basket full')

    def test_both_tampered_package_and_decode_rejected(self):
        pcm(self.package,seconds=.5);shutil.copyfile(self.package,self.decoded)
        with self.assertRaisesRegex(ValueError,'fixed suffix'): self.check('Basket full')

    def test_source_suffix_mismatch_rejected(self):
        pcm(self.suffix,seconds=.5)
        with self.assertRaisesRegex(ValueError,'exact fixed source suffix'): self.check('Basket full')

    def test_ogg_never_admitted(self):
        self.package=self.package.with_suffix('.ogg')
        with self.assertRaisesRegex(ValueError,'WAV only'): self.check('Basket full')

    def test_quality_checker_requires_explicit_source_and_package(self):
        checker=TargetQualityChecker(context_checker=object())
        with self.assertRaisesRegex(ValueError,'exact source'):
            checker.check(self.suffix,self.decoded,{},text='Basket full',locale='en')

    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg not installed')
    def test_actual_native_48k_packaging_and_candidate_adapter(self):
        target=pcm(self.suffix,rate=48000);write(self.source,48000,target+target)
        checker=ContextualTargetChecker(AudioPipeline(),lambda *_:{'text':'Basket full'},self.root/'evidence')
        result=PackagedCandidateVerifier(checker)(self.source,self.suffix,cut_sample=48000,
                    locale='en',target='Basket full',ignore_accents=True,
                    comparison_policy='locale-number-tokens-v2')
        self.assertEqual(result['candidate_quality']['disposition'],'PASS')
        self.assertEqual(result['candidate_quality']['proof']['source_rate'],48000)


class CandidateSeamTests(unittest.TestCase):
    def run_case(self,root,*,two=False,flags=None,malformed=False):
        source=root/'raw.wav'; (_two_gap_wav if two else _wav)(source)
        class Verifier:
            policy_id='saved-wav-context-hard-invariants-v1'
            def __call__(self,*args,**kwargs):
                if malformed:return {'text':'ten house'}
                quality={'verification_strategy':self.policy_id,'disposition':'PASS',
                         'flags':flags or [],'transcript':'ten house'}
                return {'text':'ten house','candidate_quality':quality}
        return extract(source,root/'out.wav',locale='en',prefix='Find a number',target='10 house',
                    remove_first_words=3,candidate_verifier=Verifier(),
                    transcriber=lambda *_:self.fail('default recognizer must not run'))

    def test_explicit_version_and_truthful_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_case(Path(temp))
            self.assertEqual(result['algorithm_version'],CONTEXT_ALGORITHM_VERSION)
            self.assertIn('prefix-heard',result['raw_intro_asr'])
            self.assertIn('selected_candidate_quality',result)

    def test_multiple_matches_keep_ambiguity_rejection(self):
        with tempfile.TemporaryDirectory() as temp,self.assertRaisesRegex(ExtractionRejected,'multiple'):
            self.run_case(Path(temp),two=True)

    def test_quality_flags_cannot_be_bypassed_by_exact_text(self):
        with tempfile.TemporaryDirectory() as temp,self.assertRaisesRegex(ExtractionRejected,'no candidate'):
            self.run_case(Path(temp),flags=['TARGET_NUMBER_MISMATCH'])

    def test_missing_proof_is_fatal_not_acoustic_retry(self):
        with tempfile.TemporaryDirectory() as temp,self.assertRaises(CandidateTranscriptionError):
            self.run_case(Path(temp),malformed=True)
