# Session 01 — Shared target extraction

**Provider calls:** Zero live synthesis/ASR/model downloads; fake external boundaries only.  
**Prerequisite:** Session 00 scoped commit and passing handoff.  
**Commit:** `Implement shared target extraction`

## Outcome

Shared target extraction.

## Preconditions

- Read README Design contract and the previous handoff; these fix all policy choices.
- Refresh main in the named repository and preserve unrelated dirty hunks. For shared
  files already dirty, record their pre-session hashes/diff; stage only this session.
- Baseline Greia commit b59d92d42; shared source is the inspected working tree,
  not an assumed pristine commit. Capture actual source SHA/hashes before editing.
- Existing heavy model/cache/voices and runtime assets are protected.

## Allowed files

```text
/Volumes/Test1/Works/voxstage/src/voxstage/production/extraction.py
/Volumes/Test1/Works/voxstage/tests/test_target_extraction.py
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

Adopted owner defaults: pinned cached multilingual Base and ignore_accents=true;
false explicitly restores strict comparison. Carry this flag through request,
policy, cache key, target location and retained-target/quality scoring. Preserve
the original script and recognizer text. Reuse the current asr_policy.py semantics.

Port the generic PCM reader/tokenizer/parser/gap/target-suffix algorithm from current Greia tools/voice_carrier.py into production/extraction.py with injected Transcriber protocol. No Greia imports, actor names, paths or installation. Return ExtractionResult with PCM path/hash, original target, raw/target ASR evidence, target-verification result and boundary metrics. Preserve exact PCM suffix and original WAV. Discarded intro text is not a gate. Keep v6 suffix threshold/ambiguity and expanded-search exact-target safety initially; ASR failures become typed per-attempt quality rejection, not manual boundary substitution. Split analysis from retained-target scoring so the target transcription can be reused in session 02. Do not automatically regenerate here. Standard library PCM operations; installed transcriber injected only.

## Tests

Port positive and negative carrier fixtures: corrupt/different-length intro, final target, target absent, ambiguous spans, quiet run absent/multiple, out-of-WAV/NaN timings, exact PCM slice, output/source alias, insufficient voiced duration. A fake recognizer sees raw once and cut once, never removed intro. Existing destination bytes survive errors. Preserve French false-reject fixtures as false-reject evidence; do not alter thresholds to force them green.

## Local gate

Working directory: `/Volumes/Test1/Works/voxstage`. Use its configured existing interpreter. In Greia,
use `/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python`
for focused voice tests; do not substitute system Python 3.14 or install packages.

```bash
python -m unittest discover -s tests -p test_target_extraction.py -v
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
