"""Move only never-submitted natural cues into an explicit bounded speech lane."""
import copy
import json
from pathlib import Path
from .store import RunStore, write_json
from .inventory import digest, receipt_path, safe_target
from .method_budget import MethodAttemptBudget
from .natural_plan import select_canary
from .automatic_generation import NATURAL_POLICY
from greia_voice_core.registry import CANONICAL_MANIFEST


def prepare_unstarted(source: Path, destination: Path, *, exclude_topics: frozenset[str]):
    """Carry zero-use allowances; never grant another budget to an attempted cue.

    Caller holds the normal generation lock. The parent remains held for method
    review; its durable handoff prevents a second child from spending the same
    never-used allowances. Excluded pedagogical letter-name cues remain explicit.
    """
    parent = RunStore(source)
    try:
        progress=json.loads((source/'progress.json').read_text())
        if progress['status']!='METHOD_REVIEW_REQUIRED' or parent.plan.get('automatic_short_generation_policy')!=NATURAL_POLICY:
            raise ValueError('only a held natural run can hand off unstarted cues')
        handoff=source/'unstarted-handoff.json'
        if handoff.exists():raise ValueError('unstarted cues already handed off; inspect existing child')
        ledger=MethodAttemptBudget(parent).snapshot()
        if parent.plan['registry_manifest_sha256']!=digest(parent.root/CANONICAL_MANIFEST):
            raise ValueError('selected master registry changed')
        selected=[];held=[]
        for row in parent.plan['rows']:
            state=parent.state(row['path']);entry=ledger['entries'][row['path']]
            if state!='READY' or entry['attempts'] or row['natural_topic'] in exclude_topics:
                held.append({'path':row['path'],'state':state,'new_attempts':len(entry['attempts']),'topic':row['natural_topic']})
                continue
            target=safe_target(parent.root,row['path'])
            if digest(target)!=row['original_sha256'] or digest(receipt_path(target))!=row['original_receipt_sha256']:
                raise ValueError('unstarted original changed: '+row['path'])
            selected.append(copy.deepcopy(row))
        if not selected:raise ValueError('no eligible unstarted cues')
        plan=copy.deepcopy(parent.plan);plan['rows']=select_canary(selected)
        plan['natural_run'].update(owner_authorization='Existing2026-10-22 completion authorization; only unused original method allowances; no historical or method budget reset',
            source_run=str(source.resolve()),source_plan_sha256=digest(source/'plan.json'),
            source_reservations_sha256=digest(source/'method-reservations.json'),excluded_topics=sorted(exclude_topics),
            excluded_records=held,canary_count=min(12,len(selected)))
        # Record the intended child before creation: a crash fails closed rather
        # than making the same zero-use allowance available to another child.
        write_json(handoff,{'status':'PREPARING','destination':str(destination.resolve()),'selected':[r['path'] for r in selected],
                            'source_plan_sha256':plan['natural_run']['source_plan_sha256'],'source_reservations_sha256':plan['natural_run']['source_reservations_sha256']})
        child=RunStore.create(destination,plan)
        try:
            write_json(destination/'method-reservations.json',{'entries':{r['path']:ledger['entries'][r['path']] for r in selected}})
            write_json(destination/'carrier-attempt-counts.json',{r['path']:r['historical_attempts'] for r in selected})
            snapshot=json.loads((source/'preinstall-snapshot.json').read_text())
            snapshot['targets']={p:{'audio':digest(safe_target(parent.root,p)),'receipt':digest(receipt_path(safe_target(parent.root,p)))} for p in snapshot['targets']}
            snapshot['plan_sha256']=digest(destination/'plan.json')
            write_json(destination/'preinstall-snapshot.json',snapshot)
            write_json(destination/'progress.json',{'status':'PREPARED','selected':len(selected),'human_review':'PENDING'})
            write_json(handoff,{**json.loads(handoff.read_text()),'status':'PREPARED','child_plan_sha256':digest(destination/'plan.json')})
        finally:child.close()
        return plan
    finally:parent.close()


def validate_handoff(store):
    """Pin both parent proof and child scope again before any provider call."""
    source_name=store.plan['natural_run'].get('source_run')
    if not source_name:return
    source=Path(source_name);meta=store.plan['natural_run']
    handoff=json.loads((source/'unstarted-handoff.json').read_text())
    if (digest(source/'plan.json')!=meta['source_plan_sha256']
            or digest(source/'method-reservations.json')!=meta['source_reservations_sha256']
            or handoff['destination']!=str(store.work)
            or handoff.get('child_plan_sha256')!=digest(store.work/'plan.json')
            or set(handoff['selected'])!={r['path'] for r in store.plan['rows']}):
        raise ValueError('unstarted handoff proof or scope changed')
