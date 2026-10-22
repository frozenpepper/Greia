"""Supervise bounded natural-method calls through existing CorpusRunner transactions."""
import json
import os
from pathlib import Path
from .store import RunStore, write_json
from .runner import CorpusRunner
from .method_budget import MethodAttemptBudget
from .automatic_generation import NATURAL_POLICY
from greia_voice_core.short_phrases import ShortPhrasePipeline
from greia_voice_core.natural_carrier import NaturalCarrierPolicy
from greia_voice_core.verification import WhisperVerifier
from greia_voice_core.locking import InterprocessGenerationLock, NullGenerationLock
from greia_voice_core.paths import voice_home


def safety_reason(terminal, entries):
    """Stop poor real-corpus yield without changing any per-file acceptance rule."""
    if len(terminal)>=3 and all(s=='PRESERVED' for _,s in terminal[-3:]):
        return 'three consecutive recordings exhausted all three natural-method takes'
    recent=terminal[-10:]
    if len(recent)==10 and sum(s=='PRESERVED' for _,s in recent)>2:
        return 'more than20percent of last10 recordings exhausted'
    if len(terminal)==12 and sum(s=='PRESERVED' for _,s in terminal)>2:
        return 'fewer than80percent of the representative12-recording canary passed'
    attempts=sum(len(entries[p]['attempts']) for p,s in terminal)
    passed=sum(s=='DONE' for p,s in terminal)
    if attempts>=12 and (attempts-passed)/attempts>.60:
        return 'more than60percent of actual generation attempts rejected'
    return None


def run_natural(work):
    """Use one warm engine, durable reservations and immediate progress after each cue."""
    from greia_voice import build_engine
    from finish_voice_priority import CachedTranscriber
    with InterprocessGenerationLock(voice_home()/'generation.lock'):
        store=RunStore(work)
        try:
            if store.plan.get('automatic_short_generation_policy')!=NATURAL_POLICY:
                raise ValueError('not a natural-method plan')
            progress=json.loads((work/'progress.json').read_text())
            if progress['status'] in {'OWNER_STOPPED','METHOD_REVIEW_REQUIRED'}:
                raise ValueError('run stopped for owner/method review; do not blindly resume')
            ready,detail=WhisperVerifier().probe()
            if not ready:raise RuntimeError('Base unavailable: '+detail)
            budget=MethodAttemptBudget(store);budget.reconcile_mirror()
            pipeline=ShortPhrasePipeline(policy=NaturalCarrierPolicy(),attempt_reservation=budget.reserve,
                transcriber=CachedTranscriber(Path(store.plan['natural_run']['cache_root'])),evidence_root=work/'automatic-evidence')
            (work/'producer.pid').write_text(str(os.getpid())+'\n')
            with build_engine(generation_lock=NullGenerationLock(),character_provider='voxstage',short_phrase_pipeline=pipeline) as engine:
                while True:
                    code=CorpusRunner(store,engine,'required').run(limit=1,continue_after_carrier_rejection=True)
                    states=[(r['path'],store.state(r['path'])) for r in store.plan['rows']]
                    terminal=[(p,s) for p,s in states if s in {'DONE','PRESERVED'}]
                    entries=budget.snapshot()['entries']
                    blocked={p:s for p,s in states if s not in {'READY','DONE','PRESERVED'}}
                    reason=safety_reason(terminal,entries)
                    remaining=[p for p,s in states if s=='READY']
                    status=('STOPPED_ERROR' if blocked or code==2 else 'METHOD_REVIEW_REQUIRED' if reason else
                            'RUNNING' if remaining else 'BOUNDED_COMPLETE')
                    result={'status':status,'installed':[p for p,s in terminal if s=='DONE'],
                        'exhausted':[p for p,s in terminal if s=='PRESERVED'],'remaining':remaining,'blocked':blocked,
                        'new_attempts':sum(len(e['attempts']) for e in entries.values()),'reason':reason,
                        'journal':store.summary(),'human_review':'PENDING'}
                    write_json(work/'progress.json',result)
                    print(json.dumps({k:result[k] for k in ('status','new_attempts','journal','reason')}),flush=True)
                    if status!='RUNNING':return 0 if status=='BOUNDED_COMPLETE' else 2
        except BaseException as exc:
            write_json(work/'progress.json',{'status':'STOPPED_ERROR','error':str(exc),'journal':store.summary(),'human_review':'PENDING'})
            raise
        finally:store.close()
