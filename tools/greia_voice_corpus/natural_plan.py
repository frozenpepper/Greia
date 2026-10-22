"""Freeze the remaining owner-authorized priority scope for the new method."""
import json
import sqlite3
from pathlib import Path
from .inventory import digest, receipt_path, safe_target, preserved_reason
from .store import RunStore, write_json
from .automatic_generation import NATURAL_POLICY
from greia_voice_core.models import VoiceRequest, SpeechKind, VerificationMode
from greia_voice_core.registry import VoiceRegistry, CANONICAL_MANIFEST
from greia_voice_core.natural_carrier import NaturalCarrierPolicy, DELIVERY
from greia_voice_core.number_comparison import COMPARISON_POLICY


def select_canary(rows, maximum=12):
    """Deterministic coverage of actual actor/locale/topic combinations, not easy demos."""
    pending = sorted(rows,key=lambda r:r['path']);selected=[];covered=set()
    def features(row):return {('actor',row['request']['speaker']),('locale',row['request']['locale']),('topic',row['natural_topic'])}
    while pending and len(selected)<maximum:
        row=max(pending,key=lambda r:len(features(r)-covered));pending.remove(row);selected.append(row);covered|=features(row)
    return selected+[r for r in rows if r not in selected]


def prepare_natural(args, root):
    """New-method allowance is explicit; historical counters are never reset."""
    from finish_voice_priority import collect_history
    priority=json.loads(args.priority_file.read_text());records={r['path']:r for r in priority['records']}
    remaining=json.loads(args.remaining_file.read_text())['remaining']
    if not set(remaining)<=set(records):raise ValueError('remaining records exceed frozen priority')
    with sqlite3.connect(args.prior_run/'state.sqlite3') as db:
        done={p for p,s in db.execute('select path,state from cues') if s=='DONE'}
    # Skip only actual completed installations, not stale DONE counters.
    for relative in done:
        candidate=args.prior_run/'candidates'/relative;target=safe_target(root,relative)
        if digest(target)!=digest(candidate) or digest(receipt_path(target))!=digest(receipt_path(candidate)):
            raise ValueError('prior DONE installation differs: '+relative)
    selected=set(remaining)-done
    counts,_,_=collect_history(args.history_root,selected)
    if any(type(counts.get(p)) is not int or counts[p]<0 for p in selected):
        raise ValueError('missing historical provider-call budget')
    registry=VoiceRegistry.load(root)
    for profile in registry.profiles.values():registry.verify_anchor(profile)
    policy=NaturalCarrierPolicy();rows=[]
    for relative in sorted(selected):
        record=records[relative];target=safe_target(root,relative);old=json.loads(receipt_path(target).read_text())
        data={k:record[k] for k in ('speaker','locale','text','cue_id')}
        data.update(kind=SpeechKind.DANI_SYSTEM_SPEECH if data['speaker']=='dani' else SpeechKind.CHARACTER_DIALOGUE,
                    delivery_prompt=DELIVERY[data['locale']],short_text_mode='on',max_attempts=3,verification=VerificationMode.REQUIRED)
        req=VoiceRequest(**data)
        if preserved_reason(relative,old.get('request',{})):raise ValueError('deterministic/protected cue selected: '+relative)
        prefix,text,delivery=policy.composite(req,DELIVERY[req.language])
        if digest(target) is None:raise ValueError('priority original missing: '+relative)
        rows.append({'path':relative,'state':'READY','reason':'owner-authorized natural method, up to3 new takes',
            'original_sha256':digest(target),'original_receipt_sha256':digest(receipt_path(target)),
            'original_kind':old.get('request',{}).get('kind'),'original_speaker':old.get('request',{}).get('speaker'),
            'request':req.to_dict(),'historical_attempts':counts[relative],'natural_topic':policy.topic(req),
            'natural_carrier':{'prefix':prefix,'composite_text':text,'effective_delivery':delivery,
                'composition_policy':policy.composition_policy,'comparison_policy':COMPARISON_POLICY}})
    plan={'root':str(root.resolve()),'rows':select_canary(rows),'registry_manifest_sha256':digest(root/CANONICAL_MANIFEST),
        'automatic_short_generation_policy':NATURAL_POLICY,
        'natural_run':{'owner_authorization':'2026-10-22 complete remaining Greia recordings using new method; new allowance3takes, historical attempts retained',
            'priority_file':str(args.priority_file.resolve()),'priority_sha256':digest(args.priority_file),
            'remaining_file':str(args.remaining_file.resolve()),'remaining_sha256':digest(args.remaining_file),
            'prior_run':str(args.prior_run.resolve()),'prior_completed_excluded':sorted(done),
            'cache_root':str(args.cache_root.resolve()),'maximum_new_attempts':3,'canary_count':min(12,len(rows))}}
    store=RunStore.create(args.work_dir,plan)
    try:
        write_json(store.work/'method-reservations.json',{'entries':{r['path']:{'prior_count':r['historical_attempts'],'attempts':[]} for r in rows}})
        write_json(store.work/'carrier-attempt-counts.json',{r['path']:r['historical_attempts'] for r in rows})
        write_json(store.work/'preinstall-snapshot.json',{'targets':{p:{'audio':digest(safe_target(root,p)),'receipt':digest(receipt_path(safe_target(root,p)))} for p in records},
            'plan_sha256':digest(store.work/'plan.json'),'prior_counts':counts})
        write_json(store.work/'progress.json',{'status':'PREPARED','selected':len(rows),'human_review':'PENDING'})
    finally:store.close()
    return plan
