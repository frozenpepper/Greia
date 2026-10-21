# Session 04 — Two-queue scheduler and retries

**Provider calls:** Zero live synthesis/ASR/model downloads; fake external boundaries only.  
**Prerequisite:** Session 03 scoped commit and passing handoff.  
**Commit:** `Implement two-queue scheduler and retries`

## Outcome

Two-queue scheduler and retries.

## Preconditions

- Read README Design contract and the previous handoff; these fix all policy choices.
- Refresh main in the named repository and preserve unrelated dirty hunks. For shared
  files already dirty, record their pre-session hashes/diff; stage only this session.
- Baseline Greia commit b59d92d42; shared source is the inspected working tree,
  not an assumed pristine commit. Capture actual source SHA/hashes before editing.
- Existing heavy model/cache/voices and runtime assets are protected.

## Allowed files

```text
/Volumes/Test1/Works/voxstage/src/voxstage/production/coordinator.py
/Volumes/Test1/Works/voxstage/src/voxstage/production/scheduling.py
/Volumes/Test1/Works/voxstage/src/voxstage/production/resources.py
/Volumes/Test1/Works/voxstage/tests/test_production_scheduler.py
```

Also update this session's handoff evidence outside source; no additional code files.

## Forbidden changes

- No new voice/master, semantic text, translation, native pedagogical policy,
  runtime installation, paid/hosted execution, model install or bulk corpus job.
- No second renderer/server, manual acceptance shortcut, silent warning success,
  quality threshold relaxation, unbounded retry or unrelated dirty-file commit.
- Public defaults remain unchanged until session 05 activates the complete path.

## Evidence and source decisions

README Evidence baseline traces the real owners: Greia's lock/serial loops and
nested wrapper block independent progress; shared VoxStage owns the renderer/job
storage; Whisper-tiny false rejects make terminal failure and retained candidates
necessary. The selected work belongs in VoxStage, with no cross-project imports.
The immutable French evidence is external in the 2026-10-22-target-suffix-v5 run.

## Exact implementation

Implement ProductionCoordinator.submit/step/complete/cancel/resume and worker interfaces over the ledger. One existing renderer, one verifier subprocess, one coordinator writer. No GPU work under service.guard. Reserve one of eight candidate credits before generating, persist raw then dispatch verification, and release credit after verdict commits. Select ready units round-robin by parent job and enqueue failed units after the job's other ready work. Retry only named quality failures up to total 3; unavailable/crashed verifier pauses same audio. Generation must advance to N+1 while N waits for verification whenever a candidate credit is available. Implement accelerator_mode serialized/overlap with one explicit inference lease; default serialized, alternate ready stages unless the candidate bound requires verification first. Persist cancellation before dispatch. Workers return messages, never write job.json. Emit a timestamped renderer_acquired event at the actual backend invocation boundary carrying job/unit/attempt/seed and a matching finished/error event; session 07 counts these events and reconciles them with raw artifacts. A counter assigned from planned work is not evidence. Keep scheduler disconnected from live public routes until session 05.

## Tests

Event-controlled fake workers prove generation B starts before verification A completes in overlap mode; serialized mode never overlaps GPU sections; CPU postprocessing does not hold inference lease. Assert retry seed differs, original voice/text stay fixed, exact three-take max, final failure has no approved path, stalled verifier bounds raw backlog at 8, cancellation prevents retry, restart skips completed synthesis, one failed chunk does not rerender its siblings, and two clients cannot own the same stage.

## Local gate

Working directory: `/Volumes/Test1/Works/voxstage`. Use its configured existing interpreter. In Greia,
use `/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python`
for focused voice tests; do not substitute system Python 3.14 or install packages.

```bash
python -m unittest discover -s tests -p test_production_scheduler.py -v
```

Expected: exit 0 for every named source test, no skipped predicates; session 07
instead records each exact live predicate and stops after its fixed budget.
For a substantive Greia implementation commit, attempt the repository-required
`make verify PYTHON=/opt/anaconda3/bin/python3` once, retain the full log externally
and distinguish inherited abort/failures from focused voice proof. Do not claim a
green full gate from focused tests or repeatedly chase unrelated environment errors.

## Cumulative gate

```bash
cd /Volumes/Test1/Works/voxstage
python -m unittest discover -s tests -p test_production_policy.py -v
python -m unittest discover -s tests -p test_target_extraction.py -v
python -m unittest discover -s tests -p test_quality_verification.py -v
python -m unittest discover -s tests -p test_asr_transport.py -v
python -m unittest discover -s tests -p test_production_ledger.py -v
python -m unittest discover -s tests -p test_production_scheduler.py -v
```

Expected: all prior named tests execute against current session source. Record
command, interpreter, commit/tree fingerprint, test count, exit code and observed
provider-call count. Source sessions require zero live acquisition calls. Preserve
all artifacts externally with hashes; missing/skipped commands fail this gate.

## Stop conditions

- Required gate fails, code needs an unlisted file, or a policy choice differs
  from README. Amend the plan before expanding work.
- A worker could publish failed audio, an old job would be reinterpreted, or
  the current intermediate commit depends on a later safety check.
- Protected dirty hunk, canonical master or prior runtime asset would change.

## Handoff

Return scoped diff, source commits and dirty-hunk accounting, exact gate results,
artifact hashes, provider-call count, lifecycle/cleanup proof, remaining unproved
predicates and the next numbered session. Session 07 additionally returns the
30-request result matrix, 12-take resource comparison, exact attempt totals,
restart/disconnect evidence and listening page; failed predicates stay failed.
