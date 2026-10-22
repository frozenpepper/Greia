"""Explicit, disabled-by-default saved-WAV substitution verification.

Context can rescue lexical substitutions only. It cannot overrule isolated
word-count/numeric evidence or substitute a different packaged payload.
"""
from pathlib import Path
import hashlib
import json
import uuid
import wave
from .asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION
from .context_timing import TimedTargetSlice
from .number_comparison import compare_target_transcript, COMPARISON_POLICY
from .review import signal_metrics
from .review_policy import ASR_PASS_THRESHOLD

CONTEXT_VERIFICATION_POLICY = 'saved-wav-context-hard-invariants-v1'


def _read(path):
    with wave.open(str(path), 'rb') as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise ValueError('context verification requires mono PCM16 WAV')
        rate, count = handle.getframerate(), handle.getnframes()
        if rate <= 0 or not 0 < count / rate <= 120:
            raise ValueError('context PCM duration is outside the 120 second bound')
        frames = handle.readframes(count)
        if len(frames) != count * 2:
            raise ValueError('truncated context PCM')
        return rate, frames


def _write(path, rate, frames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(rate)
        handle.writeframes(frames)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ContextualTargetChecker:
    """Own a bounded prefix reconstruction and at most two offline ASR calls.

    Callers explicitly inject this collaborator; normal TargetQualityChecker
    behaviour is unchanged. The caller owns retained external evidence and the
    generation/ASR serialization lock. AudioPipeline and transcriber are reused.
    """

    def __init__(self, audio, transcriber, evidence_root: Path):
        self.audio, self.transcriber = audio, transcriber
        self.evidence_root = Path(evidence_root)

    def check(self, source: Path, extracted: Path, delivered: Path, packaged: Path, *,
              cut_sample: int, text: str, locale: str, ignore_accents: bool = True,
              comparison_policy: str = COMPARISON_POLICY) -> dict:
        """Verify actual packaged WAV; context cannot repair hard isolated flags."""
        if packaged.suffix.lower() != '.wav':
            raise ValueError('saved context verification supports WAV only; OGG remains unchanged')
        rate, raw = _read(source); erate, suffix = _read(extracted)
        if (type(cut_sample) is not int or erate != rate or not 0 < cut_sample < len(raw)//2
                or raw[cut_sample*2:] != suffix):
            raise ValueError('extracted PCM is not the exact fixed source suffix')
        drate, decoded = _read(delivered); prate, packaged_pcm = _read(packaged)
        if drate != 22050 or prate != drate or packaged_pcm != decoded:
            raise ValueError('actual packaged WAV and decoded payload differ')
        work = self.evidence_root / uuid.uuid4().hex
        work.mkdir(parents=True, exist_ok=False)
        expected = self.audio.package(extracted, work/'expected.wav')
        if _read(expected) != (drate, decoded):
            raise ValueError('packaged target does not derive from the fixed suffix')
        try:
            metrics, signal_flags = signal_metrics(delivered)
        except ValueError as exc:
            metrics, signal_flags = {"signal_error":str(exc)}, ["INVALID_SIGNAL"]
        proof = {'source':str(source), 'source_sha256':_sha(source),
                 'extracted':str(extracted), 'extracted_sha256':_sha(extracted),
                 'packaged':str(packaged), 'packaged_sha256':_sha(packaged),
                 'decoded':str(delivered), 'decoded_sha256':_sha(delivered),
                 'cut_sample':cut_sample, 'source_rate':rate,
                 'packaged_suffix_matches':True, 'evidence_dir':str(work)}
        observed = self.transcriber(delivered, locale)
        proof["isolated_observation"] = self._record(delivered, locale, observed, work/"isolated.json")
        if not isinstance(observed, dict) or not isinstance(observed.get('text'), str):
            raise ValueError('malformed isolated transcript')
        isolated = self._compare(text, observed['text'], locale, ignore_accents, comparison_policy)
        isolated['flags'] += signal_flags
        result = {'disposition':'WARN', 'score':isolated['score'], 'transcript':isolated['transcript'],
                  'metrics':metrics, 'flags':list(isolated['flags']), 'isolated':isolated,
                  'contextual':None, 'proof':proof, 'selected_evidence':'none',
                  'verification_strategy':CONTEXT_VERIFICATION_POLICY,
                  'comparison_policy':comparison_policy, 'ignore_accents':ignore_accents,
                  'model_id':DEFAULT_ASR_MODEL, 'model_revision':DEFAULT_ASR_REVISION,
                  'detail':'Saved WAV screening only; human listening remains pending'}
        if isolated['score'] > ASR_PASS_THRESHOLD and not isolated['flags']:
            result.update(disposition='PASS', selected_evidence='isolated')
            return result
        # This independent veto catches the real duplicate-intro false approval.
        # A contextual recognizer may omit speech; it cannot erase contrary
        # isolated count/number evidence even when its own target looks exact.
        if isolated['flags'] or not isolated['transcript'].strip():
            return result
        prefix_source = work/'prefix-source.wav'
        _write(prefix_source, rate, raw[:cut_sample*2])
        prefix = self.audio.package(prefix_source, work/'prefix.wav')
        prefix_rate, prefix_pcm = _read(prefix)
        if prefix_rate != drate:
            raise ValueError('context prefix and payload rates differ')
        context = work/'context.wav'; _write(context, drate, prefix_pcm+decoded)
        if _read(context) != (drate, prefix_pcm+decoded):
            raise ValueError('reconstructed context differs from exact prefix and delivery')
        boundary = len(prefix_pcm)/2/drate
        full = self.transcriber(context, locale)
        proof["contextual_observation"] = self._record(context, locale, full, work/"context.json")
        target = TimedTargetSlice.from_result(full, prefix_seconds=boundary,
                                             duration_seconds=(len(prefix_pcm)+len(decoded))/2/drate)
        contextual = self._compare(text, target.transcript, locale, ignore_accents, comparison_policy)
        if target.straddling:
            contextual['flags'].append('CONTEXT_BOUNDARY_STRADDLES_WORD')
        if not target.words:
            contextual['flags'].append('CONTEXT_TARGET_WORDS_MISSING')
        contextual.update(full_transcript=target.full_transcript, retained_words=list(target.words),
                          straddling=list(target.straddling))
        proof.update(prefix_frames=len(prefix_pcm)//2, prefix_seconds=boundary,
                     context=str(context), context_sha256=_sha(context),
                     payload_pcm_sha256=hashlib.sha256(decoded).hexdigest(),
                     context_payload_identical=True, word_timestamp_coverage_valid=True,
                     intro_wording_agreement_required=False)
        result.update(contextual=contextual, score=contextual['score'], transcript=contextual['transcript'],
                      flags=contextual['flags'])
        if contextual['score'] > ASR_PASS_THRESHOLD and not contextual['flags']:
            result.update(disposition='PASS', selected_evidence='contextual')
        return result

    @staticmethod
    def _record(audio, locale, result, destination):
        """Retain the exact observation before any transcript/timing validation."""
        from .context_evidence import observation_identity
        record = {"identity":observation_identity(audio, locale), "result":result}
        destination.write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n")
        return {"path":str(destination), "sha256":_sha(destination)}

    @staticmethod
    def _compare(expected, actual, locale, ignore_accents, policy):
        comparison = compare_target_transcript(locale, expected, actual,
                                              ignore_accents=ignore_accents, policy=policy)
        return {'score':comparison.score, 'transcript':actual,
                'flags':comparison.flags(require_word_count=True)}


class PackagedCandidateVerifier:
    """Adapt bounded cutter candidates to the same actual-delivery checker."""

    policy_id = CONTEXT_VERIFICATION_POLICY

    def __init__(self, checker):
        self.checker = checker

    def __call__(self, source, candidate, *, cut_sample, locale, target,
                 ignore_accents, comparison_policy):
        work = candidate.with_name(candidate.name+'.delivery-proof')
        work.mkdir(exist_ok=False)
        packaged = self.checker.audio.package(candidate, work/'candidate.wav')
        decoded = work/'decoded.wav'
        self.checker.audio.decode_for_review(packaged, decoded)
        quality = self.checker.check(source, candidate, decoded, packaged, cut_sample=cut_sample,
            text=target, locale=locale, ignore_accents=ignore_accents, comparison_policy=comparison_policy)
        return {'text':quality['transcript'], 'segments':[], 'candidate_quality':quality}
