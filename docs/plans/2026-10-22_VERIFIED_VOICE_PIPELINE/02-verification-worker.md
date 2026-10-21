# Session 02 — Warm verification worker

**Provider calls:** Zero live synthesis/ASR/model downloads; fake external boundaries only.  
**Prerequisite:** Session 01 scoped commit and passing handoff.  
**Commit:** `Implement warm verification worker`

## Outcome

Warm verification worker.

## Preconditions

- Read README Design contract and the previous handoff; these fix all policy choices.
- Refresh main in the named repository and preserve unrelated dirty hunks. For shared
  files already dirty, record their pre-session hashes/diff; stage only this session.
- Baseline Greia commit b59d92d42; shared source is the inspected working tree,
  not an assumed pristine commit. Capture actual source SHA/hashes before editing.
- Existing heavy model/cache/voices and runtime assets are protected.

## Allowed files

```text
/Volumes/Test1/Works/voxstage/src/voxstage/production/verification.py
/Volumes/Test1/Works/voxstage/src/voxstage/production/asr_worker.py
/Volumes/Test1/Works/voxstage/src/voxstage/production/asr_transport.py
/Volumes/Test1/Works/voxstage/tests/test_quality_verification.py
/Volumes/Test1/Works/voxstage/tests/test_asr_transport.py
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

Implement SpeechVerifier protocol, cached-model Whisper adapter, bounded subprocess transport and QualityVerdict. Probe configured VOXSTAGE_ASR_PYTHON and cached model revision without downloading; missing dependency/weights is BLOCKED_VERIFIER. Child worker loads only one Whisper model, uses offline environment and frozen language/temperature/settings, and accepts bounded JSON messages carrying request token and audio path/hash. Save raw recognizer result before parsing. Never pass expected text/initial_prompt into recognition. Use the existing normalized weighted char/token similarity policy, strict >0.8, plus final-target signal checks. Short extracted targets also require normalized token-count equality; expected repetitions stay valid. Apply internal/tail silence failure at >=1.5 seconds to final target only, not the deliberate intro pause; allow explicit per-request policy for intentional pauses. Reuse extraction target ASR for scoring; normal take gets one ASR call. Explicit off emits UNVERIFIED, not PASS. Distinguish mismatch from worker crash, timeout and model-unavailable faults. Keep one child process; terminate/reap on shutdown and retain candidate on fault. No live child/model invocation during this session; fake child transport only.

## Tests

Test 0.8 fails, >0.8 passes, empty/hallucinated text fails, short-target repeated/extra words fail even when similarity alone exceeds 0.8, one-word and Dani-like requests are checked, explicit off skips quality, missing model blocks without rendering. Assert one ordinary/two short ASR calls maximum and no expected-text prompt. Malformed replies, wrong tokens/hash, timeout, child exit and oversize JSON cannot accept or trigger a synthesis retry.

## Local gate

Working directory: `/Volumes/Test1/Works/voxstage`. Use its configured existing interpreter. In Greia,
use `/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python`
for focused voice tests; do not substitute system Python 3.14 or install packages.

```bash
python -m unittest discover -s tests -p test_quality_verification.py -v
python -m unittest discover -s tests -p test_asr_transport.py -v
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
