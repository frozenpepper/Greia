"""Supervise bounded natural-method calls through existing CorpusRunner transactions."""
import json
import os
from pathlib import Path
import subprocess
from .store import RunStore, write_json
from .runner import CorpusRunner
from .method_budget import MethodAttemptBudget
from .automatic_generation import NATURAL_POLICY, NATURAL_PARAKEET_FULL_POLICY, NATURAL_SPOKEN_TARGET_POLICY
from greia_voice_core.short_phrases import ShortPhrasePipeline
from greia_voice_core.natural_carrier import NaturalCarrierPolicy
from greia_voice_core.verification import WhisperVerifier, ParakeetVerifier
from greia_voice_core.locking import InterprocessGenerationLock, NullGenerationLock
from greia_voice_core.paths import voice_home
from .inventory import digest, receipt_path, safe_target


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


def aggregate_stop_reason(plan, terminal, entries):
    """Keep the historical v1 yield stop; honor the separate full-scope order."""
    from .automatic_generation import NATURAL_PARAKEET_FULL_POLICY
    if plan.get('automatic_short_generation_policy') in {NATURAL_PARAKEET_FULL_POLICY, NATURAL_SPOKEN_TARGET_POLICY}:
        return None
    return safety_reason(terminal, entries)


def _validate_original_or_installed(store, row):
    """Prove a cue is untouched or matches its own resumable transaction."""
    relative=row['path']; state=store.state(relative)
    target=safe_target(store.root,relative); target_receipt=receipt_path(target)
    original={'audio':row['original_sha256'],'receipt':row['original_receipt_sha256']}
    current={'audio':digest(target),'receipt':digest(target_receipt)}
    if state in {'READY','PRESERVED','GENERATING'}:
        if current!=original:
            raise ValueError('frozen original audio/receipt changed before production: '+relative)
        return
    if state not in {'INSTALLING','DONE'}:
        raise ValueError('cue requires explicit recovery before resuming: '+relative+' ('+state+')')
    candidate=store.work/'candidates'/relative
    candidate_receipt=receipt_path(candidate)
    if not candidate.is_file() or not candidate_receipt.is_file():
        raise ValueError('installed cue lacks its retained candidate pair: '+relative)
    expected_after={'audio':digest(candidate),'receipt':digest(candidate_receipt)}
    transactions=store.db.execute(
        'SELECT id,state,files FROM transactions WHERE path=? ORDER BY id DESC',(relative,)
    ).fetchall()
    if not transactions:
        raise ValueError('installed cue lacks a journal transaction: '+relative)
    transaction,transaction_state,raw=transactions[0]
    if transaction_state!=state:
        raise ValueError('cue and latest transaction states differ: '+relative)
    files={item['path']:item for item in json.loads(raw)}
    receipt_relative=str(receipt_path(Path(relative)))
    for pair_path,pair_key in ((relative,'audio'),(receipt_relative,'receipt')):
        item=files.get(pair_path)
        expected_candidate=Path('candidates')/pair_path
        if (item is None or item.get('before')!=original[pair_key]
                or item.get('after')!=expected_after[pair_key]
                or item.get('candidate')!=str(expected_candidate)):
            raise ValueError('transaction pair does not prove the frozen replacement: '+relative)
        backup=store.work/'backups'/str(transaction)/pair_path
        if transaction_state=='DONE' and digest(backup)!=original[pair_key]:
            raise ValueError('completed replacement lost its exact original backup: '+relative)
        if transaction_state=='INSTALLING' and digest(backup) not in {None,original[pair_key]}:
            raise ValueError('interrupted replacement backup differs from frozen original: '+relative)
        if current[pair_key] not in {original[pair_key],expected_after[pair_key]}:
            raise ValueError('replacement destination differs from journaled before/after bytes: '+relative)
        if transaction_state=='DONE' and current[pair_key]!=expected_after[pair_key]:
            raise ValueError('completed replacement is not installed at its destination: '+relative)


def validate_full_parakeet_plan(store):
    """Fail before any submission if the explicit 237-row freeze has drifted."""
    from .automatic_generation import NATURAL_PARAKEET_FULL_POLICY, natural_comparison_policy
    from greia_voice_core.number_comparison import PARAKEET_COMPARISON_POLICY
    from greia_voice_core.asr_policy import DEFAULT_PARAKEET_MODEL, DEFAULT_PARAKEET_REVISION
    from greia_voice_core.registry import VoiceRegistry

    if store.plan.get('automatic_short_generation_policy') != NATURAL_PARAKEET_FULL_POLICY:
        return
    meta=store.plan['natural_run']
    if (len(store.plan['rows'])!=237 or meta.get('execution_profile')!='natural-parakeet-v3-full237-v1'
            or meta.get('maximum_new_attempts')!=3
            or meta.get('aggregate_yield_guard') is None
            or meta.get('recognizer_model')!=DEFAULT_PARAKEET_MODEL
            or meta.get('recognizer_revision')!=DEFAULT_PARAKEET_REVISION
            or natural_comparison_policy(store.plan)!=PARAKEET_COMPARISON_POLICY):
        raise ValueError('full Parakeet policy scope/recognizer/budget does not match its version')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=store.root,text=True).strip()
    if head!=meta.get('producer_commit'):
        raise ValueError('producer commit changed after scope freeze')
    for relative, expected in meta['producer_source_hashes'].items():
        if digest(store.root/relative)!=expected:
            raise ValueError('producer source changed after scope freeze: '+relative)
    for path_key,hash_key in (('priority_file','priority_sha256'),
                              ('remaining_file','remaining_sha256'),
                              ('scope_audit_file','scope_audit_sha256')):
        if digest(Path(meta[path_key]))!=meta[hash_key]:
            raise ValueError('external source-scope artifact changed after freeze: '+path_key)
    diagnostics=meta.get('separate_diagnostic_evidence',{})
    if diagnostics.get('not_corpus_output') is not True:
        raise ValueError('ten-request diagnostic history is not separated from the corpus run')
    for key,path in diagnostics.get('files',{}).items():
        if digest(Path(path))!=diagnostics.get('sha256',{}).get(key):
            raise ValueError('separate diagnostic evidence changed after freeze: '+key)
    diagnostic_progress=json.loads(Path(diagnostics['files']['progress']).read_text())
    diagnostic_results=json.loads(Path(diagnostics['files']['results']).read_text())
    if (diagnostic_progress.get('status')!='COMPLETE' or diagnostic_progress.get('total')!=10
            or diagnostic_progress.get('no_install') is not True
            or diagnostic_progress.get('no_bulk') is not True
            or len(diagnostic_results)!=10):
        raise ValueError('separate ten-request diagnostic is incomplete or was installed')
    remaining_doc=json.loads(Path(meta['remaining_file']).read_text())
    audit=json.loads(Path(meta['scope_audit_file']).read_text())
    expected_scope=set(remaining_doc['remaining'])
    if (len(expected_scope)!=237 or expected_scope!={row['path'] for row in store.plan['rows']}
            or set(audit.get('remaining',[]))!=expected_scope
            or audit.get('remaining_categories')!={'unstarted_letters':44,'unstarted_ordinary':193,'exhausted':0}):
        raise ValueError('frozen remaining list, audit counts and plan rows differ')
    if set(meta.get('prior_completed_excluded',[])) & expected_scope:
        raise ValueError('historical completion exclusion removed a current remaining row')
    priority=json.loads(Path(meta['priority_file']).read_text())
    records={row['path']:row for row in priority['records']}
    registry=VoiceRegistry.load(store.root)
    identities={name:{'voice_id':profile.voice_id,'anchor_sha256':profile.anchor_sha256}
                for name,profile in sorted(registry.profiles.items())}
    if identities!=meta.get('master_identities'):
        raise ValueError('selected master identities changed after scope freeze')
    seen=set()
    for row in store.plan['rows']:
        relative=row['path'];request=row['request']
        if relative in seen:raise ValueError('duplicate path in full Parakeet scope')
        seen.add(relative)
        if (request.get('comparison_policy')!=PARAKEET_COMPARISON_POLICY
                or request.get('max_attempts')!=3
                or row.get('natural_carrier',{}).get('comparison_policy')!=PARAKEET_COMPARISON_POLICY):
            raise ValueError('row comparison policy or three-call budget differs: '+relative)
        source=records.get(relative)
        if source is None or any(request.get(k)!=source.get(k) for k in ('speaker','locale','text','cue_id')):
            raise ValueError('frozen row differs from exact priority request: '+relative)
        target=safe_target(store.root,relative)
        _validate_original_or_installed(store,row)
    snapshot=json.loads((store.work/'preinstall-snapshot.json').read_text())
    if (snapshot.get('plan_sha256')!=digest(store.work/'plan.json')
            or len(snapshot.get('targets',{}))!=667
            or any(snapshot['targets'].get(row['path'])!={'audio':row['original_sha256'],
                'receipt':row['original_receipt_sha256']} for row in store.plan['rows'])):
        raise ValueError('preinstall snapshot does not pin all667 pairs and every selected original')


def validate_spoken_target_plan(store):
    """Fail before submission unless the exact reviewed 77-row v4 freeze holds."""
    from .automatic_generation import NATURAL_SPOKEN_TARGET_POLICY, natural_comparison_policy
    from greia_voice_core.number_comparison import SPOKEN_TARGET_COMPARISON_POLICY
    from greia_voice_core.spoken_target import POLICY as SPOKEN_POLICY
    from greia_voice_core.asr_policy import DEFAULT_PARAKEET_MODEL, DEFAULT_PARAKEET_REVISION
    from greia_voice_core.registry import VoiceRegistry

    if store.plan.get('automatic_short_generation_policy') != NATURAL_SPOKEN_TARGET_POLICY:
        return
    meta=store.plan['natural_run']
    if (len(store.plan['rows'])!=77 or meta.get('execution_profile')!='natural-spoken-target-parakeet-v4-77-v1'
            or meta.get('maximum_new_attempts')!=3 or meta.get('aggregate_yield_guard') is None
            or meta.get('recognizer_model')!=DEFAULT_PARAKEET_MODEL
            or meta.get('recognizer_revision')!=DEFAULT_PARAKEET_REVISION
            or meta.get('spoken_target_policy')!=SPOKEN_POLICY
            or natural_comparison_policy(store.plan)!=SPOKEN_TARGET_COMPARISON_POLICY):
        raise ValueError('spoken-target plan scope, recognizer, or budget differs from its registered version')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=store.root,text=True).strip()
    if head!=meta.get('producer_commit'):
        raise ValueError('producer commit changed after spoken-target scope freeze')
    for relative,expected in meta['producer_source_hashes'].items():
        if digest(store.root/relative)!=expected:
            raise ValueError('spoken-target producer source changed after scope freeze: '+relative)
    for path_key,hash_key in (('priority_file','priority_sha256'),('remaining_file','remaining_sha256'),
                              ('scope_audit_file','scope_audit_sha256'),
                              ('approved_recovery_file','approved_recovery_sha256'),
                              ('approved_review_file','approved_review_sha256')):
        if digest(Path(meta[path_key]))!=meta[hash_key]:
            raise ValueError('spoken-target evidence changed after scope freeze: '+path_key)
    recovery=json.loads(Path(meta['approved_recovery_file']).read_text())
    audit=json.loads(Path(meta['scope_audit_file']).read_text())
    recovered_paths=sorted(item['path'] for item in recovery.get('installed',[]))
    if (len(recovered_paths)!=13 or recovery.get('review_sha256')!=meta['approved_review_sha256']
            or recovery.get('status')!='COMPLETE'):
        raise ValueError('approved-target recovery evidence is incomplete')
    if recovered_paths!=sorted(audit.get('approved_recovery_paths',[])):
        raise ValueError('approved-target recovery paths differ from the frozen scope audit')
    remaining=json.loads(Path(meta['remaining_file']).read_text())
    expected=set(remaining['remaining'])
    if len(expected)!=77 or expected!={row['path'] for row in store.plan['rows']} or set(audit.get('remaining',[]))!=expected:
        raise ValueError('spoken-target plan rows differ from the exact 77-row remaining freeze')
    registry=VoiceRegistry.load(store.root)
    identities={name:{'voice_id':profile.voice_id,'anchor_sha256':profile.anchor_sha256}
                for name,profile in sorted(registry.profiles.items())}
    if identities!=meta.get('master_identities'):
        raise ValueError('selected master identities changed after spoken-target freeze')
    for row in store.plan['rows']:
        if (row['request'].get('comparison_policy')!=SPOKEN_TARGET_COMPARISON_POLICY
                or row['request'].get('max_attempts')!=3
                or row.get('natural_carrier',{}).get('comparison_policy')!=SPOKEN_TARGET_COMPARISON_POLICY):
            raise ValueError('spoken-target row comparison policy or three-call budget differs: '+row['path'])
        _validate_original_or_installed(store,row)
    snapshot=json.loads((store.work/'preinstall-snapshot.json').read_text())
    if (snapshot.get('plan_sha256')!=digest(store.work/'plan.json') or len(snapshot.get('targets',{}))!=667
            or any(snapshot['targets'].get(row['path'])!={'audio':row['original_sha256'],
                'receipt':row['original_receipt_sha256']} for row in store.plan['rows'])):
        raise ValueError('spoken-target preinstall snapshot does not pin all667 pairs')


def run_natural(work):
    """Use one warm engine, durable reservations and immediate progress after each cue."""
    from greia_voice import build_engine
    from finish_voice_priority import CachedTranscriber
    with InterprocessGenerationLock(voice_home()/'generation.lock'):
        store=RunStore(work)
        try:
            policy_id=store.plan.get('automatic_short_generation_policy')
            if policy_id not in {NATURAL_POLICY,NATURAL_PARAKEET_FULL_POLICY,NATURAL_SPOKEN_TARGET_POLICY}:
                raise ValueError('not a natural-method plan')
            full_parakeet=policy_id in {NATURAL_PARAKEET_FULL_POLICY,NATURAL_SPOKEN_TARGET_POLICY}
            validate_full_parakeet_plan(store)
            validate_spoken_target_plan(store)
            progress=json.loads((work/'progress.json').read_text())
            if progress['status'] in {'OWNER_STOPPED','METHOD_REVIEW_REQUIRED'}:
                raise ValueError('run stopped for owner/method review; do not blindly resume')
            from .natural_continuation import validate_handoff
            validate_handoff(store)
            verifier=ParakeetVerifier() if full_parakeet else WhisperVerifier()
            ready,detail=verifier.probe()
            if not ready:raise RuntimeError(('Parakeet unavailable: ' if full_parakeet else 'Base unavailable: ')+detail)
            budget=MethodAttemptBudget(store);budget.reconcile_mirror()
            pipeline_kwargs={'policy':NaturalCarrierPolicy(),'attempt_reservation':budget.reserve,
                'evidence_root':work/'automatic-evidence'}
            if full_parakeet:
                # Use one pinned Parakeet collaborator for isolated candidate
                # extraction and final decoded-package verification.
                pipeline_kwargs['verifier']=verifier
            else:
                pipeline_kwargs['transcriber']=CachedTranscriber(Path(store.plan['natural_run']['cache_root']))
            pipeline=ShortPhrasePipeline(**pipeline_kwargs)
            (work/'producer.pid').write_text(str(os.getpid())+'\n')
            with build_engine(generation_lock=NullGenerationLock(),character_provider='voxstage',
                              short_phrase_pipeline=pipeline,verifier=verifier) as engine:
                while True:
                    code=CorpusRunner(store,engine,'required').run(limit=1,continue_after_carrier_rejection=True)
                    states=[(r['path'],store.state(r['path'])) for r in store.plan['rows']]
                    terminal=[(p,s) for p,s in states if s in {'DONE','PRESERVED'}]
                    entries=budget.snapshot()['entries']
                    blocked={p:s for p,s in states if s not in {'READY','DONE','PRESERVED'}}
                    # The new owner order authorizes all237 exact requests; keep
                    # per-record gates, but do not apply the old aggregate-yield
                    # hold from the superseded v1 production policy.
                    reason=aggregate_stop_reason(store.plan,terminal,entries)
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
