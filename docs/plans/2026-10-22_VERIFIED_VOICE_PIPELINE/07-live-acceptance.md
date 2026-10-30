# Session 07 — Controlled local acceptance and resource gate

**Provider calls:** Bounded local installed-model calls only; limits in Exact implementation.  
**Prerequisite:** Session 06 scoped commit and passing handoff.  
**Commit:** `Record bounded verified-pipeline live evidence`

## Outcome

Controlled local acceptance and resource gate.

## Preconditions

- Read README Design contract and the previous handoff; these fix all policy choices.
- Refresh main in the named repository and preserve unrelated dirty hunks. For shared
  files already dirty, record their pre-session hashes/diff; stage only this session.
- Baseline Greia commit b59d92d42; shared source is the inspected working tree,
  not an assumed pristine commit. Capture actual source SHA/hashes before editing.
- Existing heavy model/cache/voices and runtime assets are protected.

## Allowed files

```text
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/docs/plans/2026-10-22_VERIFIED_VOICE_PIPELINE/ACCEPTANCE_RESULT.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/HANDOVER.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
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
necessary. The selected work belongs in Greia, with no cross-project imports.
The immutable French evidence is external in the 2026-10-22-target-suffix-v5 run.

## Exact implementation

Source edits forbidden in this session. Store all live audio/logs under /Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-verified-pipeline-acceptance/. Preflight configured cached verifier/model, both repository commit SHAs, selected immutable masters, queues idle for this project, no unrelated jobs stopped. Freeze 24 short requests (six canonical actors × en/it/es/fr) by taking lexicographically first eligible non-pedagogical path per pair from the existing frozen priority plan, preserving exact text; save manifest before generation. Add six ordinary five-plus-word cues, one per actor, from that same frozen plan. No invented translations. Hard upper bound 90 fresh synthesis takes (30 units ×3), no additional reroll. Before that corpus-independent trial, benchmark 6 matched ordinary requests once in serialized mode and once in overlap mode (12 takes, max_attempts=1), same voices/text/seeds; retain unverified benchmark outputs separately. Measure wall time, generation/ASR stage times, backlog, process RSS/system memory pressure and failures. Enable overlap for the 30-unit trial only if total wall time improves at least 10%, generation p95 does not regress more than 20%, no pressure/OOM/worker failures, and logical results/counters remain truthful. Otherwise keep serialized and report no concurrency speedup. Verify API result points to cut target, zero intro in final short targets by listening review page, all retries bounded and evidence retained. Explicitly interrupt one verifier stage on saved candidate, restart/recover same audio with zero new render; disconnect/reconnect client same job. Export Takeboard exact raw/cut/attempts and unresolved list. No runtime install, no owner approval inferred, no bulk restart.

## Tests

Provider-free suites from 00–06 must already pass. Live asserts counts at renderer acquisition, not from self-reported receipts; post bounded request matrix, inspect raw/cut content and final result status, plot/reconcile stage times, ASR scores, attempts and memory. Any failed automatic result remains unresolved; no manual boundary or human override is counted as pipeline success. Listening result is owner evidence separately from automated PASS.

## Local gate

Working directory: `/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia`. Use its configured existing interpreter. In Greia,
use `/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python`
for focused voice tests; do not substitute system Python 3.14 or install packages.

```bash
"/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python" tools/verify_voice_pipeline.py --source-plan /Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/retry-v4/run/plan.json --output-dir /Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-verified-pipeline-acceptance --benchmark-pairs 6 --max-total-generations 102
"/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python" tools/verify_voice_pipeline.py --source-plan /Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/retry-v4/run/plan.json --output-dir /Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-verified-pipeline-acceptance --benchmark-pairs 6 --max-total-generations 102 --run
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
python -m unittest discover -s tests -v
cd "/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia"
PYTHONPATH=src:tools python -m unittest tests.test_greia_verified_pipeline tests.test_greia_voice_tool tests.test_greia_voxstage tests.test_voice_carrier tests.test_voice_carrier_generation tests.test_greia_voice_corpus -v
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
