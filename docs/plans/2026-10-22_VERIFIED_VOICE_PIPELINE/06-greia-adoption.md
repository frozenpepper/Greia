# Session 06 — Greia engine and corpus adoption

**Provider calls:** Zero live synthesis/ASR/model downloads; fake external boundaries only.  
**Prerequisite:** Session 05 scoped commit and passing handoff.  
**Commit:** `Implement greia engine and corpus adoption`

## Outcome

Greia engine and corpus adoption.

## Preconditions

- Read README Design contract and the previous handoff; these fix all policy choices.
- Refresh main in the named repository and preserve unrelated dirty hunks. For shared
  files already dirty, record their pre-session hashes/diff; stage only this session.
- Baseline Greia commit b59d92d42; shared source is the inspected working tree,
  not an assumed pristine commit. Capture actual source SHA/hashes before editing.
- Existing heavy model/cache/voices and runtime assets are protected.

## Allowed files

```text
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/verify_voice_pipeline.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/voice_carrier.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/models.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/engine.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/providers.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/voxstage_provider.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/voxstage_client.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/verification.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/service.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/locking.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_corpus/carriers.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_corpus/carrier_generation.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_corpus/runner.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_corpus/store.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tools/greia_voice_core/README.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/docs/agents/GREIA_SPOKEN_CARRIER_EXTRACTION.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/SETUP.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/skills/greia-voice-production/SKILL.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tests/test_greia_verified_pipeline.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tests/test_greia_voice_tool.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tests/test_greia_voxstage.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tests/test_voice_carrier.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tests/test_voice_carrier_generation.py
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia/tests/test_greia_voice_corpus.py
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

Default VoiceRequest max_attempts becomes 3 and verified default required for normal character speech. Add immutable short-text policy fields, logical request ID and async submit/generate_many; generate remains a blocking wrapper. Provider capability contract declares shared quality ownership. VoxStageProvider sends exact semantic target and explicit locale/policy to shared recording API, waits for VERIFIED/explicit UNVERIFIED only and returns final PCM/provenance; no second local verify or regeneration loop. Remove default VoxStage's Greia global generation lock across service/batch/provider waits; shared server lease serializes the model. Preserve legacy Chatterbox locking, per-run corpus writer lease and per-output publication exclusion; reject duplicate output destinations before provider work. Legacy Chatterbox advertises unsupported verified-v2 capability and rejects that policy before rendering; explicit legacy bypass remains available, no provider switch. Native pedagogical route stays outside carrier/Whisper with explicit exemption receipt. Replace default server serial socket processing with bounded request handling to coordinator-backed submit/wait semantics; no local model thread concurrency. Batch and corpus maintain a rolling 8-job window and single writer for completions/install transactions. Remove double carrier wrapping and independent attempt budgets for new plans; retain historical plan recognition and require new policy-versioned plans. Import cumulative prior corpus generation counts and available raw artifacts; remaining fresh budget is max(0, 3-used). Never reset that budget by creating another shared request. An exhausted cue returns unresolved with no generation, unless the owner has explicitly established a new recording operation. Retain portable output encoding, backups, canonical master hashes and pending human reviews. Standalone carrier CLI delegates generic extraction to shared tool via an explicit client/capability boundary, not an import that makes all Greia installs require MLX packages. Add tools/verify_voice_pipeline.py as a thin acceptance client with --source-plan, --output-dir, --benchmark-pairs, --max-total-generations and --run flags. Dry-run is default: freeze exact short/ordinary requests by README rules and report a 102-call absolute maximum (12 benchmark + 90 production attempts). Live --run requires the same manifest hash, verifies tool/source capability IDs, records server renderer-acquisition events and saved artifact hashes, reconciles all attempt totals, and exits nonzero on any failed live predicate without adding retries. Use the shared public client, never backend imports or direct synthesis. Write JSON results and Takeboard manifest externally. Unit-test this driver using fake HTTP responses, clock and resource samples. Update setup readiness to check shared verifier and selected interpreter. Do not install a model or resume the existing corpus.

## Tests

Public Greia tests fake only loopback transport: all six voices/four locales, short/long routing, no nested intros, no local ASR duplication, max3 shared takes even through corpus retries, concurrent client accept/bounded batch lookahead, out-of-order final IDs, explicit off, missing capability/verifier, native pedagogical preservation, unchanged masters and existing output transaction backups. Old frozen plans reject changed policy instead of silently adopting it. Verify signal/package/receipt errors do not trigger a new provider take.

## Local gate

Working directory: `/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia`. Use its configured existing interpreter. In Greia,
use `/Users/taio84/Library/Application Support/Greia/voice-production/venv/bin/python`
for focused voice tests; do not substitute system Python 3.14 or install packages.

```bash
PYTHONPATH=src:tools python -m unittest tests.test_greia_verified_pipeline tests.test_greia_voice_tool tests.test_greia_voxstage tests.test_voice_carrier tests.test_voice_carrier_generation tests.test_greia_voice_corpus -v
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
