"""Explicit Activity-bound reconciliation of registered saved diagnostics.

One result may be admitted only through its registered literal target or an
explicitly registered comparison policy that proves a supported equivalence.
This does not admit arbitrary spoken variants or same-text reuse, and never
changes an original plan, receipt or budget.
"""
import copy
import json
from pathlib import Path
import sqlite3

from .carriers import freeze_row
from .inventory import digest,receipt_path,safe_target
from greia_voice_core.registry import CANONICAL_MANIFEST
from voice_carrier import spoken_words

POLICY='registered-literal-diagnostic-source-v1'
EQUIVALENT_POLICY='registered-equivalent-diagnostic-source-v2'


def reconcile(manifest_path, *, root, source_work, priority_file, comparison_policy="locale-number-tokens-v2"):
    """Return the exact semantic row and proven actual source, without writes."""
    data=json.loads(Path(manifest_path).read_text())
    if data.get('policy') not in {POLICY,EQUIVALENT_POLICY} or data.get('schema_version')!=1:
        raise ValueError('unsupported diagnostic reconciliation policy')
    def pinned(name):
        path=Path(data[name]);
        if digest(path)!=data[name+'_sha256']:raise ValueError('diagnostic '+name+' identity changed')
        return path
    original_plan=pinned('source_plan');priority=pinned('priority_file');remaining=pinned('remaining_file')
    if original_plan.resolve()!=(Path(source_work)/'plan.json').resolve() or priority.resolve()!=Path(priority_file).resolve():
        raise ValueError('diagnostic source/priority route differs')
    plan=json.loads(original_plan.read_text());relative=data['path']
    if Path(plan['root']).resolve()!=Path(root).resolve() or digest(Path(root)/CANONICAL_MANIFEST)!=plan['registry_manifest_sha256']:
        raise ValueError('diagnostic project/registry differs')
    rows=[r for r in plan['rows'] if r['path']==relative]
    if len(rows)!=1:raise ValueError('diagnostic has no unique original target')
    historical=rows[0];row=copy.deepcopy(historical)
    if relative not in json.loads(remaining.read_text())['remaining']:
        raise ValueError('diagnostic target is not remaining')
    scope=[r for r in json.loads(priority.read_text())['records'] if r['path']==relative]
    if len(scope)!=1 or any(scope[0].get(k)!=row['request'].get(k) for k in ('speaker','locale','text','cue_id')):
        raise ValueError('diagnostic target differs from frozen priority')
    with sqlite3.connect(f'file:{Path(source_work)/"state.sqlite3"}?mode=ro',uri=True) as db:
        state=db.execute('select state from cues where path=?',(relative,)).fetchone()
    if not state or state[0] not in {'FAILED','PRESERVED'}:
        raise ValueError('diagnostic original source is not terminal rejected')
    registration=json.loads(pinned('registration').read_text());results=json.loads(pinned('results').read_text())
    index=data['result_index']
    if type(index) is not int or not 0<=index<len(results):raise ValueError('diagnostic result index differs')
    diagnostic=results[index];case=diagnostic['case'];request=diagnostic['result']['request']
    if case not in registration['cases'] or diagnostic['seed'] not in registration['seeds']:
        raise ValueError('diagnostic result was not registered')
    # Spoken lexical equivalence is admitted only through a separately pinned
    # policy; an alias in the source manifest cannot create its own equivalence.
    from greia_voice_core.number_comparison import canonical_number_tokens
    if data['policy']==EQUIVALENT_POLICY:
        if data.get('comparison_policy')!=comparison_policy:
            raise ValueError('diagnostic explicit comparison policy differs')
        equivalent=(canonical_number_tokens(case['locale'],case['spoken'],policy=comparison_policy)==
                    canonical_number_tokens(case['locale'],case['text'],policy=comparison_policy))
    else:
        equivalent=case['spoken']==case['text']
    if not equivalent or case['text']!=row['request']['text']:
        raise ValueError('diagnostic spoken target differs; explicit comparison policy required')
    parts=Path(relative).parts
    if len(parts)<3 or parts[0]!='activities' or not case['cue_id'].startswith(parts[1]+'.'):
        raise ValueError('diagnostic cue belongs to another Activity')
    for key in ('speaker','locale','text'):
        if case[key]!=row['request'][key] or request[key]!=row['request'][key]:
            raise ValueError('diagnostic semantic request differs')
    for key in ('kind','delivery_prompt'):
        if request[key]!=row['request'][key]:raise ValueError('diagnostic semantic delivery differs')
    if request['cue_id']!=case['cue_id']:raise ValueError('diagnostic cue alias differs')
    raw=pinned('raw');rec_path=pinned('raw_receipt');rec=json.loads(rec_path.read_text())
    expected_raw=Path(diagnostic['result']['evidence_dir'])/'attempt-01/raw.wav'
    if raw.resolve()!=expected_raw.resolve() or rec_path.resolve()!=receipt_path(raw).resolve():
        raise ValueError('diagnostic raw does not belong to selected result')
    actual=rec['request'];composite=case['prefix']+'\n\n'+case['spoken']
    if (actual['text']!=composite or actual['cue_id']!=case['cue_id'] or
            rec['generation_parameters']['script_seed']!=diagnostic['seed'] or
            rec['generation_parameters']['delivery_prompt']!=actual['delivery_prompt'] or
            any(actual.get(k)!=request.get(k) for k in ('speaker','locale','kind','delivery_prompt')) or
            actual.get('ignore_accents',True)!=request.get('ignore_accents',True)):
        raise ValueError('diagnostic actual provider request differs')
    # Existing exact job/key/mix/native-packaging proof, unchanged.
    entry={'path':relative,'sha256':digest(raw),'receipt_sha256':digest(rec_path),
           'job_manifest':str(pinned('job_manifest')),'job_manifest_sha256':data['job_manifest_sha256']}
    # The existing helper consumes a carrier-raw layout. Verify this explicit
    # diagnostic through a read-only path adapter, not copied/rewritten receipts.
    from .source_selection import validate_provider_source
    validate_provider_source(entry,raw,rec_path)
    if not data.get('ledgers'):
        raise ValueError('diagnostic generation ledger pins required')
    for ledger in data['ledgers']:
        if digest(Path(ledger['path']))!=ledger['sha256']:raise ValueError('diagnostic generation ledger changed')
    row['request']={k:v for k,v in row['request'].items() if k not in {'output','verification','max_attempts'}}
    row.update(state='READY',reason='explicit registered literal diagnostic saved recovery; no synthesis')
    row.pop('natural_carrier',None)
    carrier=freeze_row(row,'warn')
    if carrier is None:raise ValueError('diagnostic target is not an eligible short cue')
    carrier.update(prefix=case['prefix'],prefix_word_count=len(spoken_words(case['prefix'])),
                   composite_text=composite,composite_delivery_prompt=actual['delivery_prompt'])
    row['spoken_carrier']=carrier
    return row,raw,rec_path,plan


def prepare_plan(args,root):
    """Freeze a new reconciliation plan; retain original semantic and actual aliases."""
    from .context_recovery import CONTEXT_POLICIES
    from .saved_recovery import POLICIES
    if args.policy not in CONTEXT_POLICIES:raise ValueError('diagnostic reconciliation requires saved context policy')
    source=args.source_work.resolve()
    if not source.is_relative_to(args.history_root.resolve()):raise ValueError('diagnostic source lies outside history')
    row,raw,rec,original=reconcile(args.diagnostic_source,root=root,source_work=source,priority_file=args.priority_file,comparison_policy=POLICIES[args.policy])
    target=safe_target(root,row['path'])
    if digest(target)!=row['original_sha256'] or digest(receipt_path(target))!=row['original_receipt_sha256']:
        raise ValueError('diagnostic original destination pair changed')
    return {'root':str(root),'rows':[row],'registry_manifest_sha256':original['registry_manifest_sha256'],
            'saved_recovery_policy':args.policy,'saved_recovery_source':{
                'work':str(source),'plan_sha256':digest(source/'plan.json'),
                'priority_file':str(args.priority_file.resolve()),'priority_sha256':digest(args.priority_file),
                'reconciliation_file':str(args.diagnostic_source.resolve()),
                'reconciliation_sha256':digest(args.diagnostic_source),
                'raw_source':str(raw),'raw_receipt':str(rec)}}


def validate_selected(store,row):
    """Repeat immutable reconciliation before stage and every installation."""
    frozen=store.plan['saved_recovery_source'];manifest=Path(frozen['reconciliation_file'])
    if digest(manifest)!=frozen['reconciliation_sha256']:raise ValueError('diagnostic reconciliation changed')
    from .saved_recovery import POLICIES
    expected,raw,rec,_=reconcile(manifest,root=store.root,source_work=Path(frozen['work']),
                priority_file=Path(frozen['priority_file']),comparison_policy=POLICIES[store.plan['saved_recovery_policy']])
    if expected!=row:raise ValueError('diagnostic reconciled row differs')
    copied=store.work/'carrier-raw'/(row['path']+'.raw.wav')
    if digest(copied)!=digest(raw) or digest(receipt_path(copied))!=digest(rec):
        raise ValueError('diagnostic copied source differs')
