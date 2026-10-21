"""Owner-selected screening thresholds, shared by live and saved-evidence reviews."""
from copy import deepcopy
import math

POLICY_VERSION = 'greia-audio-screen-v3'
ASR_PASS_THRESHOLD = 0.8
MAX_TRAILING_SILENCE = 1.5
MAX_INTERNAL_PAUSE = 1.5


def reassess_result(record: dict, *, expected_text: str | None = None, ignore_accents: bool | None = None) -> dict:
    """Apply current thresholds without rewriting raw evidence or human decisions.

    Decode/metadata failures and unrelated warning classes remain actionable.
    ASR policy exclusions are never relabeled as transcript verification.
    """
    result = deepcopy(record)
    result['policy_version'] = POLICY_VERSION
    if result.get('status') == 'FAIL':
        return result
    flags = [flag for flag in result.get('flags', []) if flag not in
             {'LONG_TRAILING_SILENCE', 'LONG_INTERNAL_PAUSE'}]
    metrics = result.get('metrics', {})
    if metrics.get('trailing_silence_seconds', 0) >= MAX_TRAILING_SILENCE:
        flags.append('LONG_TRAILING_SILENCE')
    if metrics.get('longest_internal_pause_seconds', 0) >= MAX_INTERNAL_PAUSE:
        flags.append('LONG_INTERNAL_PAUSE')
    asr = result.get('asr', {})
    expected_text = expected_text if expected_text is not None else result.get('expected_text')
    ignore_accents = ignore_accents if ignore_accents is not None else result.get('ignore_accents', True)
    result['ignore_accents'] = ignore_accents
    if expected_text is not None:
        result['expected_text'] = expected_text
    if (asr.get('status') in {'PASS', 'WARN'} and isinstance(asr.get('transcript'), str)
            and isinstance(expected_text, str)):
        from .verification import transcript_similarity
        asr['score'] = transcript_similarity(expected_text, asr['transcript'], ignore_accents=ignore_accents)
        asr['ignore_accents'] = ignore_accents
        # Tokens derived under an earlier accent policy must not survive reassessment.
        from .verification import normalize_transcript
        asr['unexpected_tokens'] = sorted(set(normalize_transcript(asr['transcript'], ignore_accents=ignore_accents).split())
                                         - set(normalize_transcript(expected_text, ignore_accents=ignore_accents).split()))
    if asr.get('status') in {'PASS', 'WARN'}:
        score = asr.get('score')
        if isinstance(score, (float, int)) and not isinstance(score, bool) and math.isfinite(score):
            flags = [flag for flag in flags if flag != 'ASR_MISMATCH_OR_ERROR']
            asr['status'] = asr['disposition'] = 'PASS' if score > ASR_PASS_THRESHOLD else 'WARN'
            asr['screening_threshold'] = ASR_PASS_THRESHOLD
            asr['threshold_comparison'] = '>'
            if asr['status'] == 'WARN':
                flags.append('ASR_MISMATCH_OR_ERROR')
            asr['detail'] = 'Transcript screened using current threshold; human listening remains separate'
        else:
            asr['status'] = 'ERROR'
    result['flags'] = list(dict.fromkeys(flags))
    result['status'] = ('BLOCKED' if asr.get('status') in {'ERROR', 'UNAVAILABLE'}
                        else 'WARN' if flags else 'PASS')
    result['pass_basis'] = ('transcript_and_signal' if asr.get('status') == 'PASS'
                            else 'signal_only_asr_excluded_or_unavailable')
    return result
