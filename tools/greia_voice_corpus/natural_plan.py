"""Freeze the remaining owner-authorized priority scope for the new method."""
import json
import sqlite3
import subprocess
from pathlib import Path
from .inventory import digest, receipt_path, safe_target, preserved_reason
from .store import RunStore, write_json
from .automatic_generation import NATURAL_POLICY, NATURAL_PARAKEET_FULL_POLICY
from greia_voice_core.models import VoiceRequest, SpeechKind, VerificationMode
from greia_voice_core.registry import VoiceRegistry, CANONICAL_MANIFEST
from greia_voice_core.natural_carrier import NaturalCarrierPolicy, DELIVERY
from greia_voice_core.number_comparison import COMPARISON_POLICY, PARAKEET_COMPARISON_POLICY
from greia_voice_core.asr_policy import DEFAULT_PARAKEET_MODEL, DEFAULT_PARAKEET_REVISION


def select_canary(rows, maximum=12):
    """Deterministic coverage of actual actor/locale/topic combinations, not easy demos."""
    pending = sorted(rows,key=lambda r:r['path']);selected=[];covered=set()
    def features(row):return {('actor',row['request']['speaker']),('locale',row['request']['locale']),('topic',row['natural_topic'])}
    while pending and len(selected)<maximum:
        row=max(pending,key=lambda r:len(features(r)-covered));pending.remove(row);selected.append(row);covered|=features(row)
    return selected+[r for r in rows if r not in selected]


def select_remaining_scope(remaining, prior_done, *, full_parakeet=False):
    """Keep a separately authorized full replacement equal to its frozen audit."""
    scope=set(remaining)
    return scope if full_parakeet else scope-set(prior_done)


def prepare_natural(args, root, *, policy_id=NATURAL_POLICY):
    """New-method allowance is explicit; historical counters are never reset."""
    from finish_voice_priority import collect_history
    priority=json.loads(args.priority_file.read_text());records={r['path']:r for r in priority['records']}
    remaining=json.loads(args.remaining_file.read_text())['remaining']
    if len(records)!=len(priority['records']) or len(remaining)!=len(set(remaining)):
        raise ValueError('duplicate priority or remaining path')
    if not set(remaining)<=set(records):raise ValueError('remaining records exceed frozen priority')
    if policy_id not in {NATURAL_POLICY, NATURAL_PARAKEET_FULL_POLICY}:
        raise ValueError('unsupported natural generation policy')
    full_parakeet = policy_id == NATURAL_PARAKEET_FULL_POLICY
    comparison_policy = PARAKEET_COMPARISON_POLICY if full_parakeet else COMPARISON_POLICY
    scope_audit_path = args.remaining_file.parent / 'audit.json'
    scope_audit = json.loads(scope_audit_path.read_text()) if scope_audit_path.is_file() else None
    if full_parakeet:
        remaining_doc=json.loads(args.remaining_file.read_text())
        if (scope_audit is None or set(scope_audit.get('remaining',[])) != set(remaining)
                or scope_audit.get('remaining_categories') != {
                    'unstarted_letters':44,'unstarted_ordinary':193,'exhausted':0}
                or scope_audit.get('all_requested_complete') is not False
                or set(remaining) != set(remaining_doc.get('unstarted_letters',[]))
                    | set(remaining_doc.get('unstarted_ordinary',[]))):
            raise ValueError('full Parakeet plan scope differs from the current 237-row v5 audit')
    with sqlite3.connect(args.prior_run/'state.sqlite3') as db:
        done={p for p,s in db.execute('select path,state from cues') if s=='DONE'}
    # Skip only actual completed installations, not stale DONE counters.
    for relative in done:
        candidate=args.prior_run/'candidates'/relative;target=safe_target(root,relative)
        if digest(target)!=digest(candidate) or digest(receipt_path(target))!=digest(receipt_path(candidate)):
            raise ValueError('prior DONE installation differs: '+relative)
    # The new full-scope owner order names the exact current remaining rows.
    # Historical DONE rows from earlier runs do not remove rows from this new
    # allowance; the old candidates and receipts stay in their original runs.
    # Legacy natural-v1 behavior continues to skip only this prior run's DONEs.
    selected=select_remaining_scope(remaining,done,full_parakeet=full_parakeet)
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
                    delivery_prompt=DELIVERY[data['locale']],short_text_mode='on',max_attempts=3,verification=VerificationMode.REQUIRED,
                    comparison_policy=comparison_policy)
        req=VoiceRequest(**data)
        if preserved_reason(relative,old.get('request',{})):raise ValueError('deterministic/protected cue selected: '+relative)
        prefix,text,delivery=policy.composite(req,DELIVERY[req.language])
        if digest(target) is None:raise ValueError('priority original missing: '+relative)
        rows.append({'path':relative,'state':'READY','reason':'owner-authorized natural method, up to3 new takes',
            'original_sha256':digest(target),'original_receipt_sha256':digest(receipt_path(target)),
            'original_kind':old.get('request',{}).get('kind'),'original_speaker':old.get('request',{}).get('speaker'),
            'request':req.to_dict(),'historical_attempts':counts[relative],'natural_topic':policy.topic(req),
            'natural_carrier':{'prefix':prefix,'composite_text':text,'effective_delivery':delivery,
                'composition_policy':policy.composition_policy,'comparison_policy':comparison_policy}})
    plan={'root':str(root.resolve()),'rows':select_canary(rows),'registry_manifest_sha256':digest(root/CANONICAL_MANIFEST),
        'automatic_short_generation_policy':policy_id,
        'natural_run':{'owner_authorization':'2026-10-22 complete remaining Greia recordings using new method; new allowance3takes, historical attempts retained',
            'priority_file':str(args.priority_file.resolve()),'priority_sha256':digest(args.priority_file),
            'remaining_file':str(args.remaining_file.resolve()),'remaining_sha256':digest(args.remaining_file),
            'prior_run':str(args.prior_run.resolve()),
            'prior_completed_excluded':sorted(done-selected),
            'cache_root':None if full_parakeet else str(args.cache_root.resolve()),
            'maximum_new_attempts':3,'canary_count':min(12,len(rows))}}
    if full_parakeet:
        if len(remaining) != 237 or len(rows) != 237:
            raise ValueError('full Parakeet plan requires all exact 237 current remaining records')
        producer_files = [
            'tools/greia_voice_corpus/automatic_generation.py',
            'tools/greia_voice_corpus/natural_plan.py',
            'tools/greia_voice_corpus/natural_run.py',
            'tools/greia_voice_corpus/runner.py',
            'tools/greia_voice_core/natural_carrier.py',
            'tools/greia_voice_core/short_phrases.py',
            'tools/greia_voice_core/verification.py',
            'tools/greia_voice_core/number_comparison.py',
            'tools/record_natural_voice_priority.py',
            'tools/greia_voice.py',
        ]
        dirty=subprocess.run(['git','diff','--quiet','HEAD','--',*producer_files],cwd=root).returncode
        if dirty:
            raise ValueError('full Parakeet producer sources must be committed before scope freeze')
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        master_identities={name:{'voice_id':profile.voice_id,'anchor_sha256':profile.anchor_sha256}
                           for name,profile in sorted(registry.profiles.items())}
        diagnostic_root=args.remaining_file.parent.parent
        diagnostic_run=diagnostic_root/'parakeet-v3-pipeline-10-v1'
        diagnostic_ledger=diagnostic_root/'diagnostic-generation-ledger-v1.json'
        diagnostic_files={
            'registration':diagnostic_run/'registered-scope.json',
            'results':diagnostic_run/'results.json',
            'progress':diagnostic_run/'progress.json',
            'separate_generation_ledger':diagnostic_ledger,
        }
        diagnostic_hashes={key:digest(path) for key,path in diagnostic_files.items()}
        if any(value is None for value in diagnostic_hashes.values()):
            raise ValueError('separate ten-request Parakeet diagnostic evidence is incomplete')
        plan['natural_run'].update({
            'owner_authorization':'2026-10-23 explicit order: regenerate all exact 237 rows from natural-completion-audit-v5; separate fresh allowance of up to3 calls per row; retain all historical totals',
            'execution_profile':'natural-parakeet-v3-full237-v1',
            'comparison_policy':PARAKEET_COMPARISON_POLICY,
            'recognizer_model':DEFAULT_PARAKEET_MODEL,
            'recognizer_revision':DEFAULT_PARAKEET_REVISION,
            'producer_commit':revision,
            'producer_source_hashes':{path:digest(root/path) for path in producer_files},
            'scope_audit_file':str(scope_audit_path.resolve()),
            'scope_audit_sha256':digest(scope_audit_path),
            'master_identities':master_identities,
            'separate_diagnostic_evidence':{
                'files':{key:str(path.resolve()) for key,path in diagnostic_files.items()},
                'sha256':diagnostic_hashes,
                'not_corpus_output':True,
            },
            'aggregate_yield_guard':'disabled only for this explicitly authorized full237 scope; all per-record quality and infrastructure gates remain enabled',
            'preserved_historical_run_policies':[NATURAL_POLICY],
        })
    store=RunStore.create(args.work_dir,plan)
    try:
        write_json(store.work/'method-reservations.json',{'entries':{r['path']:{'prior_count':r['historical_attempts'],'attempts':[]} for r in rows}})
        write_json(store.work/'carrier-attempt-counts.json',{r['path']:r['historical_attempts'] for r in rows})
        write_json(store.work/'preinstall-snapshot.json',{'targets':{p:{'audio':digest(safe_target(root,p)),'receipt':digest(receipt_path(safe_target(root,p)))} for p in records},
            'plan_sha256':digest(store.work/'plan.json'),'prior_counts':counts})
        write_json(store.work/'progress.json',{'status':'PREPARED','selected':len(rows),'human_review':'PENDING'})
    finally:store.close()
    return plan
