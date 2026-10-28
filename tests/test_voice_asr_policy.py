"""Base-default and comparison-only accent-policy regressions; no live ASR."""
import importlib.util
import math
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from greia_voice_core.asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION, cached_asr_model
from greia_voice_core.models import VoiceRequest, SpeechKind, VerificationDisposition
from greia_voice_core.verification import WhisperVerifier, transcript_similarity
from greia_voice_core.review_policy import reassess_result
from greia_voice_core.service import request_from_mapping
from voice_carrier import extract, ExtractionRejected, validate_transcript_and_boundary

HAS_HUGGINGFACE_HUB = importlib.util.find_spec("huggingface_hub") is not None


def result(*words):
    """Small timestamp fixture usable under both package and discovery runners."""
    return {"text": " ".join(word for word, _, _ in words),
            "segments": [{"words": [{"word": word, "start": start, "end": end}
                                     for word, start, end in words]}]}



class AsrPolicyTests(unittest.TestCase):
    @unittest.skipUnless(
        HAS_HUGGINGFACE_HUB,
        "optional huggingface_hub voice-provider dependency is not installed",
    )
    def test_base_is_default_and_pinned_cache_resolution_is_offline(self):
        self.assertEqual(WhisperVerifier().model_id, 'mlx-community/whisper-base-mlx')
        with patch('huggingface_hub.snapshot_download', return_value='/cached/base') as load:
            self.assertEqual(cached_asr_model(), Path('/cached/base'))
        load.assert_called_once_with(DEFAULT_ASR_MODEL, local_files_only=True, allow_patterns=["config.json", "weights.npz", "weights.safetensors"], revision=DEFAULT_ASR_REVISION)

    def test_accents_ignored_both_directions_and_unicode_forms(self):
        for a,b in [('trovò','trovo'),('trovo','trovò'),('été','ete'),('está','esta'),('trovó','trovò'),('e\u0301té','ete')]:
            with self.subTest(a=a,b=b):
                self.assertEqual(transcript_similarity(a,b),1)
                self.assertLess(transcript_similarity(a,b,ignore_accents=False),1)
        self.assertLess(transcript_similarity('trovo','banana'),.5)

    def test_request_and_transport_keep_script_and_allow_strict_override(self):
        payload={'speaker':'leo','kind':'character_dialogue','locale':'it','text':'Lui trovò.'}
        self.assertTrue(request_from_mapping(payload).ignore_accents)
        strict=request_from_mapping({**payload,'ignore_accents':False})
        self.assertFalse(strict.ignore_accents)
        self.assertEqual(strict.to_dict()['text'],'Lui trovò.')
        with self.assertRaisesRegex(ValueError,'boolean'):
            request_from_mapping({**payload,'ignore_accents':'false'})

    def test_live_verifier_uses_request_policy_without_changing_model_input(self):
        fake=types.SimpleNamespace(transcribe=Mock(return_value={'text':'Lui trovo.'}))
        verifier=WhisperVerifier()
        with patch.dict(sys.modules,{'mlx_whisper':fake}), patch.object(verifier,'probe',return_value=(True,'cached')), patch('greia_voice_core.verification.cached_asr_model',return_value=Path('/cached/base')), patch('greia_voice_core.verification._release_mlx_transient_memory'):
            normal=verifier.verify(VoiceRequest('leo',SpeechKind.CHARACTER_DIALOGUE,'it','Lui trovò.'),Path('audio.wav'))
            strict=verifier.verify(VoiceRequest('leo',SpeechKind.CHARACTER_DIALOGUE,'it','Lui trovò.',ignore_accents=False),Path('audio.wav'))
        self.assertEqual(normal.disposition,VerificationDisposition.PASS)
        self.assertEqual(strict.disposition,VerificationDisposition.WARN)
        self.assertEqual(fake.transcribe.call_args.kwargs['path_or_hf_repo'],'/cached/base')

    def test_target_location_ignores_accents_but_strict_can_reject(self):
        raw=result(('garble',.1,.3),('trovo',.6,.9))
        self.assertTrue(validate_transcript_and_boundary(raw,'Intro','trovò',1)[2])
        with self.assertRaisesRegex(ExtractionRejected,'no matching final target'):
            validate_transcript_and_boundary(raw,'Intro','trovò',1,ignore_accents=False)

    def test_extraction_verification_uses_same_accent_policy(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source.wav';dst=Path(t)/'target.wav'
            samples=[0]*10000
            for lo,hi in [(1000,3000),(6000,8500)]:
                for i in range(lo,hi):samples[i]=int(5000*math.sin(i*.1))
            with wave.open(str(src),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(10000);f.writeframes(struct.pack('<10000h',*samples))
            def transcribe(path,locale):
                return result(('garble',.1,.3),('trovo',.6,.85)) if path==src else result(('trovo',.1,.35))
            receipt=extract(src,dst,locale='it',prefix='Intro',target='trovò',remove_first_words=1,transcriber=transcribe)
            self.assertTrue(receipt['ignore_accents'])
            self.assertTrue(receipt['extracted_target_exact_match'])
            self.assertEqual(receipt['target'],'trovò')
            self.assertEqual(receipt['extracted_transcript'],'trovo')
            self.assertEqual(receipt['model_id'],DEFAULT_ASR_MODEL)

    def test_saved_carrier_accent_warning_can_be_cleared_without_mutating_receipt(self):
        from greia_voice_corpus.review import CorpusReview
        row={'request':{'text':'trovò'},'spoken_carrier':{'mode':'spoken-short-v1'}}
        receipt={'extraction':{'target_verification_warning':True,'extracted_transcript':'trovo','unremoved_raw_aligned_tokens':['trovo']}}
        normal={'status':'WARN','flags':['CARRIER_TARGET_TRANSCRIPT_MISMATCH'],'ignore_accents':True,'asr':{'status':'PASS','score':1}}
        updated=CorpusReview._apply_carrier_review_flags(normal,row,receipt)
        self.assertEqual(updated['status'],'PASS')
        self.assertTrue(receipt['extraction']['target_verification_warning'])
        strict={'status':'WARN','flags':['CARRIER_TARGET_TRANSCRIPT_MISMATCH'],'ignore_accents':False,'asr':{'status':'PASS','score':1}}
        self.assertEqual(CorpusReview._apply_carrier_review_flags(strict,row,receipt)['status'],'WARN')

    def test_saved_evidence_rescores_without_relabeling_old_model(self):
        old={'status':'WARN','flags':['ASR_MISMATCH_OR_ERROR'],'asr':{'status':'WARN','transcript':'trovo','score':.1,'verifier_id':'mlx-whisper-tiny'}}
        normal=reassess_result(old,expected_text='trovò')
        strict=reassess_result(old,expected_text='trovò',ignore_accents=False)
        self.assertEqual(normal['status'],'PASS')
        self.assertEqual(strict['status'],'WARN')
        self.assertEqual(normal['asr']['verifier_id'],'mlx-whisper-tiny')
        self.assertEqual(old['asr']['score'],.1)

if __name__=='__main__':unittest.main()
