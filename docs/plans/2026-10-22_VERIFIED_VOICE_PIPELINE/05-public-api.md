# Session 05 — Public recording API and script adoption

**Provider calls:** Zero live synthesis/ASR/model downloads; fake external boundaries only.  
**Prerequisite:** Session 04 scoped commit and passing handoff.  
**Commit:** `Implement public recording api and script adoption`

## Outcome

Public recording API and script adoption.

## Preconditions

- Read README Design contract and the previous handoff; these fix all policy choices.
- Refresh main in the named repository and preserve unrelated dirty hunks. For shared
  files already dirty, record their pre-session hashes/diff; stage only this session.
- Baseline Greia commit b59d92d42; shared source is the inspected working tree,
  not an assumed pristine commit. Capture actual source SHA/hashes before editing.
- Existing heavy model/cache/voices and runtime assets are protected.

## Allowed files

```text
/Volumes/Test1/Works/voxstage/src/voxstage/api.py
/Volumes/Test1/Works/voxstage/src/voxstage/service.py
/Volumes/Test1/Works/voxstage/src/voxstage/schemas.py
/Volumes/Test1/Works/voxstage/src/voxstage/planner.py
/Volumes/Test1/Works/voxstage/src/voxstage/cli.py
/Volumes/Test1/Works/voxstage/src/voxstage/responses.py
/Volumes/Test1/Works/voxstage/src/voxstage/client.py
/Volumes/Test1/Works/voxstage/src/voxstage/production/coordinator.py
/Volumes/Test1/Works/voxstage/tests/test_recording_api.py
/Volumes/Test1/Works/voxstage/tests/test_production.py
/Volumes/Test1/Works/voxstage/README.md
/Volumes/Test1/Works/voxstage/CHANGELOG.md
/Volumes/Test1/Works/voxstage/VERIFICATION.md
/Volumes/Test1/Works/voxstage/skills/voxstage/SKILL.md
/Volumes/Test1/Works/voxstage/skills/voxstage/references/production.md
/Users/taio84/.claude/TOOLS_CATALOG.md
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

Activate coordinator through ProductionService, retaining VoiceDesign's existing route and saved voice library. Add /v2/recordings POST (202), GET /v2/recordings/{id}, GET /v2/recordings/{id}/result (409 while pending/failed, 200 only final VERIFIED or explicit UNVERIFIED). Existing job media route serves retained artifacts; result references only selected final PCM. RecordingClient.submit_recording returns a durable handle with result/wait/cancel; disconnection leaves job running. Stable idempotency key plus canonical immutable request fingerprint returns existing result or conflicts, never duplicates. Add voxstage record, route speak through it, and add /v2/jobs for script/segment language and production policy; render/plan use v2. Preserve /v1/jobs as explicitly legacy-unverified compatibility, with no automatic fallback from v2. Chunk original segment before carrier wrapping; show actual composites in plan. New v2 ordinary script requests default verified; missing explicit language rejects locally. Backward persisted jobs retain frozen legacy behavior with UNVERIFIED metadata. Update polling terminal states and completion summaries together. A script mixes selected chunks only after every required unit succeeds. No quality-failed mix or raw short recording is advertised as final. Preserve existing cancel/queue behavior and all pre-existing dirty hunks. Update catalog entry in place with verification capability/limits; do not create another tool entry.

## Tests

Public HTTP tests with fake renderer/verifier: default short text wraps correct locale, returned final path is cut, first failed take then pass consumes 2, three failures return terminal failure, explicit bypass returns UNVERIFIED, unknown language submits zero renders, idempotent POST after response loss submits one unit, cancel while verifying prevents publication. Test script chunks/alternatives, preview, legacy resume, API/CLI terminal exit codes, disconnect/reattach, and old voice-design/cancellation regressions.

## Local gate

Working directory: `/Volumes/Test1/Works/voxstage`. Use its configured existing interpreter. In Greia,
use `/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python`
for focused voice tests; do not substitute system Python 3.14 or install packages.

```bash
python -m unittest discover -s tests -v
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
python -m unittest discover -s tests -v
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
