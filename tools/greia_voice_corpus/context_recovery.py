"""Explicit saved-only WAV adapter; exact source selection and receipt replay."""
from pathlib import Path
import json

from greia_voice_core.context_evidence import RecordedTranscriber, validate_quality
from greia_voice_core.contextual_target import ContextualTargetChecker, PackagedCandidateVerifier
from .inventory import digest, receipt_path

POLICY = 'target-only-v7-saved-wav-context-v1'


def selected_source(store, row):
    """Reconcile original plan, remaining scope, copied raw and completed job."""
    from .source_selection import load_selection, validate_selected_source
    frozen = store.plan['saved_recovery_source']
    source = Path(frozen['work'])
    if digest(source/'plan.json') != frozen['plan_sha256']:
        raise ValueError('context source plan changed')
    selection_path = Path(frozen['selection_file'])
    if digest(selection_path) != frozen['selection_sha256']:
        raise ValueError('context selected sources changed')
    entries = load_selection(selection_path,source,Path(frozen['priority_file']))
    entry = entries[row['path']]
    original = [r for r in json.loads((source/'plan.json').read_text())['rows'] if r['path']==row['path']]
    if (len(original)!=1 or original[0]['request'] != row['request'] or
            original[0]['spoken_carrier'] != row['spoken_carrier']):
        raise ValueError('context semantic/carrier request differs from original')
    validate_selected_source(entry,source,original[0])
    raw = store.work/'carrier-raw'/(row['path']+'.raw.wav')
    if digest(raw)!=entry['sha256'] or digest(receipt_path(raw))!=entry['receipt_sha256']:
        raise ValueError('context copied raw/receipt differs from selected source')
    if Path(row['path']).suffix.lower()!='.wav':
        raise ValueError('context recovery supports WAV only')


def checker_for(engine, store, row, transcriber):
    """Require an explicitly read-only observation cache, never live recognition."""
    if not isinstance(transcriber, RecordedTranscriber):
        raise ValueError('context saved recovery requires recorded-only ASR')
    selected_source(store,row)
    return ContextualTargetChecker(engine.audio,transcriber,
                                  store.work/'context-verification'/row['path'])


def validate_candidate(store,row,candidate,receipt,audio):
    """Recheck every measured candidate and the actual final packaged delivery."""
    from voice_carrier_search import CONTEXT_ALGORITHM_VERSION, MAX_CANDIDATES
    selected_source(store,row)
    extraction = receipt['extraction']
    if extraction['algorithm_version']!=CONTEXT_ALGORITHM_VERSION:
        raise ValueError('context extraction version differs')
    evidence = Path(extraction['search_evidence_json'])
    if not evidence.resolve().is_relative_to(store.work.resolve()) or digest(evidence)!=receipt['search_evidence_sha256']:
        raise ValueError('context bounded-search evidence changed')
    report = json.loads(evidence.read_text())
    items = extraction['candidate_results']
    if (not 0<len(items)<=MAX_CANDIDATES or len(items)!=extraction['candidate_count'] or
            report['candidate_results']!=items or len(report['qualifying_quiet_runs'])!=len(items) or
            report['qualifying_quiet_run_count']!=len(items) or
            len({item['cut_sample'] for item in items})!=len(items)):
        raise ValueError('context incomplete or ambiguous candidate coverage')
    raw = store.work/receipt['raw_audio']['path']
    policy = extraction['comparison_policy']; passing=[]
    for item in items:
        quality = item['candidate_quality'];proof = quality['proof']
        if quality.get('ignore_accents')!=extraction.get('ignore_accents',True):
            raise ValueError('context candidate accent policy differs')
        if proof['cut_sample']!=item['cut_sample'] or digest(Path(item['candidate_path']))!=item['candidate_sha256']:
            raise ValueError('context candidate boundary/hash differs')
        passed = validate_quality(quality,source=raw,extracted=Path(item['candidate_path']),
            packaged=Path(proof['packaged']),decoded=Path(proof['decoded']),text=row['request']['text'],
            locale=row['request']['locale'],policy=policy,root=store.work,audio=audio,require_pass=False)
        from greia_voice_core.number_comparison import compare_target_transcript
        comp = compare_target_transcript(row['request']['locale'],row['request']['text'],quality['transcript'],
                                        ignore_accents=extraction.get('ignore_accents',True),policy=policy)
        # Required extraction retains exactness; warn retains the existing .8 gate.
        passed = passed and (comp.exact_match if row['spoken_carrier']['target_verification']=='required'
                             else comp.score>.8 and not comp.flags(require_word_count=True))
        if passed:passing.append(item['candidate_id'])
        if item['target_verification_qualifies']!=passed:
            raise ValueError('context candidate qualification differs')
    if passing!=[extraction['candidate_id']]:
        raise ValueError('context candidate selection is not unique')
    chosen = next(item for item in items if item['candidate_id']==extraction['candidate_id'])
    if (chosen['cut_sample']!=extraction['boundary']['cut_sample'] or
            chosen['candidate_sha256']!=extraction['output_sha256'] or
            extraction['output_sha256']!=receipt['extracted_pcm']['sha256']):
        raise ValueError('context selected suffix/boundary differs from extraction')
    if receipt['extraction']['delivery']['removed_frames']!=0:
        raise ValueError('context saved recovery cannot move the measured boundary')
    quality = receipt['verification'];proof = quality['proof']
    if quality.get('ignore_accents')!=extraction.get('ignore_accents',True):
        raise ValueError('context final accent policy differs')
    if proof['cut_sample']!=extraction['boundary']['cut_sample']:
        raise ValueError('context final boundary differs')
    validate_quality(quality,source=raw,extracted=store.work/receipt['extracted_pcm']['path'],
        packaged=candidate,decoded=Path(proof['decoded']),text=row['request']['text'],
        locale=row['request']['locale'],policy=policy,root=store.work,audio=audio)
