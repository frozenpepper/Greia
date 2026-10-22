"""Read-only recorded Base observations and physical saved-WAV receipt checks."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile

from .asr_policy import DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION
from .context_timing import TimedTargetSlice
from .number_comparison import compare_target_transcript
from .review import signal_metrics

SETTINGS = 'temperature=0;previous_text=false;prompt=null;word_timestamps=true'


def observation_identity(audio, locale):
    """The existing exact CachedTranscriber identity; no alternative ASR settings."""
    return [hashlib.sha256(Path(audio).read_bytes()).hexdigest(), locale,
            DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION, SETTINGS]


class RecordedTranscriber:
    """Read exact pinned observations only; missing evidence never invokes ASR."""
    def __init__(self, cache_root):
        self.cache_root = Path(cache_root)

    def __call__(self, audio, locale):
        identity = observation_identity(audio, locale)
        key = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        path = self.cache_root/'asr-cache'/(key+'.json')
        record = json.loads(path.read_text())
        if record.get('identity') != identity or not isinstance(record.get('result'), dict):
            raise ValueError('recorded ASR identity/result differs')
        return record['result']


def validate_quality(quality, *, source, extracted, packaged, decoded, text,
                     locale, policy, root, audio, require_pass=True):
    """Recompute actual PCM, observation, timing and quality without new ASR.

    Used by the explicit saved-only installer. All witness paths stay inside its
    run; original provider/master/request identity belongs to source selection.
    """
    from .contextual_target import CONTEXT_VERIFICATION_POLICY, _read, _write
    root = Path(root).resolve()
    proof = quality['proof']
    if (quality.get('verification_strategy') != CONTEXT_VERIFICATION_POLICY or
            quality.get('model_id') != DEFAULT_ASR_MODEL or
            quality.get('model_revision') != DEFAULT_ASR_REVISION or
            quality.get('comparison_policy') != policy):
        raise ValueError('context quality policy/model differs')
    def checked(path, digest):
        path = Path(path)
        if not path.resolve().is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('context evidence path/hash differs')
        return path
    for name, path in [('source',source),('extracted',extracted),('packaged',packaged),('decoded',decoded)]:
        if Path(proof[name]).resolve() != Path(path).resolve():
            raise ValueError('context evidence points to another payload')
        checked(path, proof[name+'_sha256'])
    rate, raw = _read(source); erate, suffix = _read(extracted)
    if proof['source_rate']!=rate or proof.get('packaged_suffix_matches') is not True:
        raise ValueError('context source-rate/suffix metadata differs')
    cut = proof['cut_sample']
    if type(cut) is not int or not 0 < cut < len(raw)//2 or rate != erate or raw[cut*2:] != suffix:
        raise ValueError('context source/suffix identity differs')
    drate, payload = _read(decoded)
    if Path(packaged).suffix.lower() != '.wav' or drate != 22050 or _read(packaged) != (drate,payload):
        raise ValueError('context supports exact packaged WAV only')
    with tempfile.TemporaryDirectory(prefix='context-receipt-') as temp:
        temp = Path(temp)
        expected = audio.package(extracted,temp/'target.wav')
        if _read(expected) != (drate,payload):
            raise ValueError('context actual delivery differs from suffix')
        metrics, signal_flags = signal_metrics(decoded)
        def observation(name, path):
            ref = proof[name+'_observation']; record = json.loads(checked(ref['path'],ref['sha256']).read_text())
            if record['identity'] != observation_identity(path,locale):
                raise ValueError('context observation identity differs')
            return record['result']
        isolated = observation('isolated',decoded)
        accents = quality.get('ignore_accents', True)
        def compare(actual):
            return compare_target_transcript(locale,text,actual,ignore_accents=accents,policy=policy)
        first = compare(isolated['text'])
        iso_flags = first.flags(require_word_count=True)+signal_flags
        if (quality['isolated']['transcript'] != isolated['text'] or
                quality['isolated']['score'] != first.score or quality['isolated']['flags'] != iso_flags):
            raise ValueError('isolated context evidence differs')
        passed = first.score > .8 and not iso_flags
        selected = 'isolated' if passed else 'none'
        transcript, score, flags = isolated['text'], first.score, iso_flags
        if (quality.get('contextual') is None and not passed and not iso_flags
                and isolated['text'].strip()):
            raise ValueError('context required fallback observation is missing')
        if quality.get('contextual') is not None:
            if passed or iso_flags or not isolated['text'].strip():
                raise ValueError('context overrode hard isolated evidence')
            if (proof.get('context_payload_identical') is not True or
                    proof.get('word_timestamp_coverage_valid') is not True or
                    proof.get('intro_wording_agreement_required') is not False):
                raise ValueError('context recognition strategy metadata differs')
            context = checked(proof['context'],proof['context_sha256'])
            _write(temp/'prefix-source.wav',rate,raw[:cut*2])
            prefix = audio.package(temp/'prefix-source.wav',temp/'prefix.wav')
            prefix_rate, prefix_pcm = _read(prefix)
            if (prefix_rate != drate or _read(context) != (drate,prefix_pcm+payload) or
                    proof['prefix_frames'] != len(prefix_pcm)//2 or
                    proof['prefix_seconds'] != len(prefix_pcm)/2/drate):
                raise ValueError('context prefix/frame/payload differs')
            if proof['payload_pcm_sha256'] != hashlib.sha256(payload).hexdigest():
                raise ValueError('context payload PCM hash differs')
            full = observation('contextual',context)
            target = TimedTargetSlice.from_result(full,prefix_seconds=proof['prefix_seconds'],
                                                  duration_seconds=(len(prefix_pcm)+len(payload))/2/drate)
            comp = compare(target.transcript)
            transcript, score, flags = target.transcript, comp.score, comp.flags(require_word_count=True)
            if target.straddling:flags.append('CONTEXT_BOUNDARY_STRADDLES_WORD')
            if not target.words:flags.append('CONTEXT_TARGET_WORDS_MISSING')
            contextual = quality['contextual']
            if (contextual['full_transcript'] != target.full_transcript or
                    contextual['retained_words'] != list(target.words) or
                    contextual['straddling'] != list(target.straddling) or
                    contextual['transcript'] != transcript or contextual['flags'] != flags or
                    contextual['score'] != score):
                raise ValueError('context full-word evidence differs')
            passed = score > .8 and not flags
            selected = 'contextual' if passed else 'none'
        if (quality['transcript'] != transcript or quality['score'] != score or
                quality['flags'] != flags or quality['metrics'] != metrics or
                quality['selected_evidence'] != selected or
                quality['disposition'] != ('PASS' if passed else 'WARN')):
            raise ValueError('context verdict differs from recorded evidence')
        if require_pass and not passed:
            raise ValueError('context final quality did not pass')
        return passed
