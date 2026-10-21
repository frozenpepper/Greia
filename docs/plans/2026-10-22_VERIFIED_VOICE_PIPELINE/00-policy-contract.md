# Session 00 — Production policy and regression fixtures

**Provider calls:** Zero live synthesis/ASR/model downloads; fake external boundaries only.  
**Prerequisite:** Current baseline snapshot and owner design adoption.  
**Commit:** `Implement production policy and regression fixtures`

## Outcome

Production policy and regression fixtures.

## Preconditions

- Read README Design contract and the previous handoff; these fix all policy choices.
- Refresh main in the named repository and preserve unrelated dirty hunks. For shared
  files already dirty, record their pre-session hashes/diff; stage only this session.
- Baseline Greia commit b59d92d42; shared source is the inspected working tree,
  not an assumed pristine commit. Capture actual source SHA/hashes before editing.
- Existing heavy model/cache/voices and runtime assets are protected.

## Allowed files

```text
/Volumes/Test1/Works/voxstage/src/voxstage/production/policy.py
/Volumes/Test1/Works/voxstage/src/voxstage/production/contracts.py
/Volumes/Test1/Works/voxstage/src/voxstage/production/__init__.py
/Volumes/Test1/Works/voxstage/tests/test_production_policy.py
/Volumes/Test1/Works/voxstage/tests/fixtures/voice_quality_cases.json
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

Add immutable ProductionPolicy, ShortTextPolicy, VerificationPolicy and RecordingRequest/RecordingResult types in the named modules. Defaults: required verification, max_attempts=3 (range 1–3), max_words=4, max_alnum=None, short mode auto. Define all README states and retryable codes as enums. Define normalize_words with NFC/casefold/internal apostrophes and keep supplied accents. Freeze resolved prefixes, composite text, language, direction and settings before attempt allocation. Exclude no character ID. Explicit missing locale, empty text, unsupported locale, invalid policy or oversize composite are pre-generation errors. Policy resolution must be pure. Store small JSON transcript/timing fixtures from the two French v5 rejections, with external source paths/hashes; do not copy WAVs into Git. Keep new modules unreferenced by public production routes until session 05.

## Tests

Assert 4 words wraps, 5 does not; apostrophes and accents; max_alnum AND semantics; verification defaults required; 3 is the hard cap; no quality downgrade for Dani; both off means no ASR; quality off plus auto carrier still declares alignment requirement; no target/delivery rewriting. Fixture hashes must match externally saved evidence. Never invoke a real backend.

## Local gate

Working directory: `/Volumes/Test1/Works/voxstage`. Use its configured existing interpreter. In Greia,
use `/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python`
for focused voice tests; do not substitute system Python 3.14 or install packages.

```bash
python -m unittest discover -s tests -p test_production_policy.py -v
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
