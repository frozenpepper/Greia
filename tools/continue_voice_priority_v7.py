#!/usr/bin/env python3
"""Prepare/run a frozen priority's final remaining take via normal short VoiceEngine.

No source discovery or budget reset. Prepare a new external plan, then run it.
Three-take exhausted rows are excluded; uncertainty stops for exact job recovery.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src'),str(ROOT)]
from greia_voice import build_engine
from greia_voice_core.registry import CANONICAL_MANIFEST,VoiceRegistry
from greia_voice_core.short_phrases import ShortPhrasePipeline
from greia_voice_core.short_policy import COMPOSITION_POLICY
from greia_voice_core.direction import character_delivery
from greia_voice_core.verification import WhisperVerifier
from greia_voice_core.locking import InterprocessGenerationLock,NullGenerationLock
from greia_voice_core.paths import voice_home
from greia_voice_corpus.automatic_generation import POLICY
from greia_voice_corpus.inventory import digest,receipt_path,safe_target
from greia_voice_corpus.store import RunStore,write_json
from greia_voice_corpus.runner import CorpusRunner
from finish_voice_priority import collect_history,CachedTranscriber


def read(path):return json.loads(path.read_text())


def prepare(args,root=ROOT):
    """Freeze exact current originals and exactly-two-prior-take request rows."""
    remaining=read(args.remaining_file)['remaining']
    priority=read(args.priority_file);selected={r['path']:r for r in priority['records']}
    if len(selected)!=len(priority['records']) or not set(remaining)<=set(selected):
        raise ValueError('remaining IDs are duplicated or outside the owner-frozen priority')
    source=read(args.source_plan)
    if Path(source['root']).resolve()!=root.resolve() or source['registry_manifest_sha256']!=digest(root/CANONICAL_MANIFEST):
        raise ValueError('source project or selected registry differs')
    counts,_,_=collect_history(args.history_root,set(remaining))
    if any(counts.get(p)!=remaining[p]['cumulative_takes'] for p in remaining):
        raise ValueError('history budgets differ from the reconciled remaining list')
    if any(type(c) is not int or c not in (2,3) for c in counts.values()):
        raise ValueError('unsupported/incomplete cumulative budgets')
    original={r['path']:r for r in source['rows']};rows=[];exhausted=[]
    for relative in sorted(remaining):
        if counts[relative]==3:
            exhausted.append(relative);continue
        row=copy.deepcopy(original[relative]);record=selected[relative]
        if any(row['request'].get(k)!=record[k] for k in ('speaker','locale','text','cue_id')):
            raise ValueError('source target differs from frozen priority: '+relative)
        target=safe_target(root,relative)
        if digest(target)!=row['original_sha256'] or digest(receipt_path(target))!=row['original_receipt_sha256']:
            raise ValueError('original destination changed: '+relative)
        if not row.get('spoken_carrier'):
            raise ValueError('source lacks a frozen short-cue policy')
        row['previous_carrier_plan']=row.pop('spoken_carrier')
        row['request'].update(ignore_accents=True,short_text_mode='on',delivery_prompt=character_delivery()[row['request']['speaker']])
        row.update(state='READY',reason='last cumulative take via automatic short v7')
        rows.append(row)
    if not rows:raise ValueError('no remaining one-take budgets')
    plan={**source,'rows':rows,'automatic_short_generation_policy':POLICY,'short_composition_policy':COMPOSITION_POLICY,
          'final_take_continuation':{'priority_file':str(args.priority_file.resolve()),'priority_sha256':digest(args.priority_file),
            'remaining_file':str(args.remaining_file.resolve()),'remaining_sha256':digest(args.remaining_file),
            'source_plan':str(args.source_plan.resolve()),'source_plan_sha256':digest(args.source_plan),
            'history_root':str(args.history_root.resolve()),'excluded_exhausted':exhausted,
            'owner_scope_count':len(selected),'cache_root':str(args.cache_root.resolve())}}
    store=RunStore.create(args.work_dir,plan)
    try:
        write_json(store.work/'carrier-attempt-counts.json',counts)
        write_json(store.work/'progress.json',{'status':'PREPARED','selected':len(rows),'previously_exhausted':len(exhausted),'human_review':'PENDING'})
    finally:store.close()
    print(json.dumps({'prepared':len(rows),'excluded_exhausted':len(exhausted)}))
    return 0


def run(work):
    """One serialized traversal, with durable rejection evidence and no blind retries."""
    with InterprocessGenerationLock(voice_home()/'generation.lock'):
        store=RunStore(work)
        try:
            if (store.plan.get('automatic_short_generation_policy')!=POLICY
                    or store.plan.get('short_composition_policy')!=COMPOSITION_POLICY):
                raise ValueError('work folder is not a v7 final-take continuation')
            available,detail=WhisperVerifier().probe()
            if not available:raise RuntimeError('Base unavailable before any submission: '+detail)
            (work/'producer.pid').write_text(str(os.getpid())+'\n')
            write_json(work/'progress.json',{'status':'RUNNING','selected':len(store.plan['rows']),'human_review':'PENDING'})
            pipeline=ShortPhrasePipeline(transcriber=CachedTranscriber(Path(store.plan['final_take_continuation']['cache_root'])),
                                         evidence_root=work/'automatic-evidence')
            with build_engine(generation_lock=NullGenerationLock(),character_provider='voxstage',short_phrase_pipeline=pipeline) as engine:
                code=CorpusRunner(store,engine,'required').run(continue_after_carrier_rejection=True)
            states={r['path']:store.state(r['path']) for r in store.plan['rows']}
            passing=[p for p,s in states.items() if s=='DONE'];exhausted=[p for p,s in states.items() if s=='PRESERVED']
            blocked={p:s for p,s in states.items() if s not in {'DONE','PRESERVED'}}
            result={'status':'BOUNDED_COMPLETE' if not blocked else 'STOPPED_ERROR','installed':passing,
                    'exhausted_new':exhausted,'blocked':blocked,'journal':store.summary(),
                    'previously_exhausted':store.plan['final_take_continuation']['excluded_exhausted'],'human_review':'PENDING'}
            write_json(work/'progress.json',result)
            print(json.dumps({k:len(result[k]) for k in ('installed','exhausted_new','blocked')}),flush=True)
            return code if blocked else 0
        except BaseException as exc:
            write_json(work/'progress.json',{'status':'STOPPED_ERROR','error':str(exc),'journal':store.summary(),'human_review':'PENDING'})
            raise
        finally:store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['prepare','run']);parser.add_argument('--work-dir',type=Path,required=True)
    for name in ('remaining-file','priority-file','source-plan','history-root','cache-root'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args();args.work_dir=args.work_dir.resolve()
    if args.work_dir.is_relative_to(ROOT):parser.error('use an external work folder')
    if args.mode=='run':return run(args.work_dir)
    if any(getattr(args,k) is None for k in ('remaining_file','priority_file','source_plan','history_root','cache_root')):parser.error('prepare requires scope, source, history and cache arguments')
    return prepare(args)


if __name__=='__main__':raise SystemExit(main())
