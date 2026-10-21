# Agent work order: regenerate the existing Greia speech corpus

**Owner authorization:** 2026-10-19, subsequently scoped to the selected v0.3
master set by owner direction on 2026-10-21.
**Executable:** `tools/regenerate_voice_corpus.py` (Python 3.11+).
**Scope:** replace existing Activity and system speech with fresh VoxCPM2
recordings, using the selected character masters and an explicit performance
prompt per recording. Preserve deterministic isolated letters and syllables.
**Current state (2026-10-21):** the owner-authorized v3 replacement is complete:
1,340 DONE, 3,575 PRESERVED, with no unresolved journal states. Its full policy-v2
automated review covered every replacement and all eligible ASR work; see the
completion entry below, HANDOVER and the external run/report directories.
Earlier preparation counts and v2 review evidence are historical snapshots.

**Current post-generation follow-up (2026-10-21):** automated screening is
complete for v3, with 1,115 PASS and 225 WARN; there are no FAIL or BLOCKED rows.
The full report and prioritized queue are external. Human acceptance remains
PENDING for all 1,340 replacements; the separate Takeboard batch is served on
the fresh local port recorded below. Generation DONE and automated PASS are not
audible/product acceptance.

This is the current executable **replacement** work order within the existing
four-language rollout. It supersedes the older add-only/no-regeneration
instructions for this explicitly requested operation. Ordinary future additions
still use `tools/greia_voice.py` and the normal listening process.

The owner authorized regeneration and replacement; do not ask for that permission
again. New output is nevertheless `human_review=PENDING`: accepting a master
does not mean a human has listened to each newly generated sentence. Do not use
`integrate_reviewed_voices.py` here: its add-only behavior and approval stamping
are inappropriate for these fresh recordings. Never relabel a whole corpus
APPROVED from a successful process exit.

## 1. Read and preserve the current checkout

Read `AGENTS.md`, `SETUP.md` §7, `HANDOVER.md`,
`skills/greia-voice-production/SKILL.md`, and
`docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md`.

Work on current `main`; fetch/fast-forward safely before changing source.
Preserve unrelated changes. At preparation time, `final.mp4` and `launch-video/`
were unrelated untracked work. No hosted Actions, paid service, model download,
image build or device installation is authorized by this work order.

```bash
cd '/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia'
git status --short
git fetch origin main
git log -1 --oneline
python3 --version
voxstage start
python3 tools/greia_voice.py doctor --character-provider voxstage
```

The shared local worker and cached model are already installed on this Mac.
Read `character_production_ready`, reference checks and FFmpeg readiness. The
optional Whisper environment is currently unavailable (NumPy/Numba mismatch).
This tool deliberately defaults to `--verification off`, rather than pretending
ASR ran. It never accepts speech by ASR. `auto` and `required` are available;
`required` follows the engine's existing eligibility rules (Dani and tiny
utterances remain human-only). Do not install a second ML stack to run it.

Stop a Greia warm `serve` process before a corpus run. The runner holds the
existing global generation lock for its whole pass, uses one engine, forces
VoxStage even if the environment selects Chatterbox, and submits serially.
Other projects also share VoxStage; inspect its queue before starting.

## 2. Performance prompts

Editable six-character defaults:
`tools/greia_voice_core/character_delivery.json`.
They describe the acting (tone, mood, rhythm and energy); saved masters carry
speaker identity. Keep directions concise and compatible with the words. Lilli
is a sparkling storybook unicorn, Flash is springy/playful, Dani an earnestly
curious cartoon robot, Tito a cheeky explorer, Momo a warm comic creature, Leo
an expressive encouraging guide. Do not redesign or replace the reference WAV.

Each planned cue snapshots its exact `delivery_prompt`. The provider sends:

```text
Speak naturally in <English|Italian|French|Spanish>. <delivery_prompt>
```

as VoxStage segment delivery, separate from the spoken transcript. The request
receipt records `delivery_prompt`; `generation_parameters` records both it and
`effective_delivery`, plus job ID, seeds, reference and renderer. These are
probabilistic performance instructions, not a guarantee of audible emotion or
language. Listen for identity drift, excessive acting and spoken prompt leakage.

Use `plan --delivery-file /absolute/custom-directions.json` to choose another
complete six-character preset. Per-cue overrides can supply `delivery_prompt`.
Edit before planning: changing the default file does not alter an existing plan.
To change a READY/DONE cue's planned direction, finish/restore that run and create
a deliberate new plan; do not silently rewrite its history. The normal CLI also
supports `--delivery-prompt`, and batch/service requests accept the same field.
Chatterbox/native explicitly reject a nonempty unsupported delivery prompt.

## 3. Inventory before the long run

Use a new work directory **outside the repository**, with space for original
audio backups, candidates and metadata snapshots. Keep it until listening and
publication are complete. Do not reuse/delete another run's directory.

```bash
voice_run='/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-production'
python3 tools/regenerate_voice_corpus.py plan --work-dir "$voice_run"
python3 tools/regenerate_voice_corpus.py status --work-dir "$voice_run" --details
```

Planning only reads repository audio; it never synthesizes or replaces it.
`plan.json` is the complete inventory and frozen requests, `state.sqlite3` the
durable journal, `blocked.csv` the initial missing-metadata report, and
`overrides.template.json` the editable starting point for missing scripts.
An exit code of 2 with `BLOCKED_METADATA` is an actionable inventory result.

The preparation inventory inspected **5,308 files** across all 45 Activities,
`assets/audio` (shared character, first-boot, launcher, vocabulary and number
banks) and `activity_incubator` (My Time). It found:

| Inventory class | Files |
|---|---:|
| READY | 4,543 |
| BLOCKED_METADATA | 167 |
| Deterministic isolated syllable/letter cues preserved | 441 |
| Historical shared v0.1 preserved | 150 |
| Active canonical master references preserved | 6 |
| Non-speech boot chime preserved | 1 |

Counts are a dated snapshot, not hardcoded success thresholds. The tool scans
existing files, not absent feature requests. Website/video narration, audition
folders and master source libraries are outside this runtime-corpus scope.
All supported output formats are WAV/OGG. Unknown media is reported, never
silently classified as a sound effect. Symlinks and escaping paths are refused.

**Exception policy:** preserve `syl_*` and isolated `letter_*` in Syllable Magic,
source-owned isolated Word Forest letters, and pedagogical single-letter
scripts. A complete alphabet phrase such as “A come Ape” and a “find ma”
instruction are regenerated. Numbers and complete words are regenerated too;
this migration maps the former generic pedagogical speaker to Leo, or Tito
for Number Woods. Per-cue explicit speaker/kind overrides can refine that
assignment. Normal `pedagogical_speech` routing elsewhere remains native.

Scripts come from existing receipts, shared manifests, locale audio/caption
bindings, the Encyclopedia narration ledger and existing Stars/Dolphin semantic
producers. Another language's receipt may establish a cue's speaker/kind, never
its transcript. Narration uses its full approved ledger wording, not a short
screen heading. The inherited source census has 398 `caption_key` advisories
on legacy EN/IT Encyclopedia narration; this tool resolves those full scripts
from `encyclopedia/VOICE_RECORDING_REQUESTS.md`. They are retained in the plan
for context, not counted as 398 missing narration scripts.

## 4. Resolve the 167 legacy metadata gaps

Initial gaps: Casa del Dieci 36, Luci di Momo 32, Specchi Magici 28,
Bottega delle Misure 26, Sillabe Magiche 22, Baia delle Orche 12,
Festa delle Rime 7, Foresta delle Parole 4. These older files lack full scripts
or semantic identity in the current checked-in metadata. Do not guess their
words from filenames, translate a sibling recording or substitute a caption
for a longer spoken line. Recover exact authored scripts from their original
source/history where available; report genuinely absent scripts to the owner.
Audio transcription is evidence for review, not automatic script approval.

Copy the template to a project-local external `overrides.json` and fill only
resolved entries; remove remaining unresolved entries from that override file.
Keys are exact repository-relative audio paths. For example (illustrative
path/script, not an additional authorized cue):

```json
{
  "activities/example/assets/audio/en/welcome.wav": {
    "speaker": "leo",
    "kind": "character_dialogue",
    "locale": "en",
    "text": "Exact existing authored transcript.",
    "cue_id": "example.welcome.en",
    "delivery_prompt": "Warm, curious and encouraging; clear, relaxed pacing."
  }
}
```

Apply corrections without regenerating completed cues:

```bash
python3 tools/regenerate_voice_corpus.py resolve --work-dir "$voice_run" \
  --overrides /absolute/overrides.json
python3 tools/regenerate_voice_corpus.py status --work-dir "$voice_run" --details
```

`resolve` updates only currently blocked rows and checks that their original
audio/receipt has not changed. Repeat after recovering further scripts. It
does not change READY/DONE requests. Keep evidence of recovered scripts in
the handover. A proven non-speech/obsolete historical file may instead use an
override object with `preserve_reason`; never use that to hide unresolved live
speech. Deterministic exceptions cannot be overridden into generation.
`blocked.csv`/the template describe the initial inventory; live status is the
authority after `resolve`.

## 5. Pilot, run, monitor

Pilot a few short cues, inspect receipts and listen before the long pass:

```bash
python3 -u tools/regenerate_voice_corpus.py run --work-dir "$voice_run" \
  --limit 4 --match 'assets/audio/characters/shared/v0.2/*/en/*' --verification off
```

The pilot **does replace** these chosen runtime files, with recoverable backups.
Exit 3 means remaining READY work; exit 2 also reflects any metadata blockers.
The production pass resumes without regenerating DONE cues:

```bash
set -o pipefail
python3 -u tools/regenerate_voice_corpus.py run --work-dir "$voice_run" \
  --verification off 2>&1 | tee -a "$voice_run/production.log"
```

Another terminal/agent can monitor while it runs:

```bash
python3 tools/regenerate_voice_corpus.py status --work-dir "$voice_run" --watch
```

Progress shows completed/total, current character/language/path, per-pass count,
elapsed time and status totals. A heartbeat prints every 15 seconds during
generation. The optional status watcher refreshes every ten seconds. An active
heartbeat proves the client is alive, not that inference is progressing: inspect
`voxstage jobs list`, then `voxstage jobs get JOB_ID` for actual worker status.
No extra inference worker or parallel generation process is needed.

The tool stages and validates a complete engine audio/receipt pair, journals
the replacement, saves originals, then atomically replaces each file. Audio,
receipt and derived metadata form a **recoverable multi-file transaction**;
they are not one filesystem-wide atomic rename. Do not publish/package while
a transaction is INSTALLING. Re-running completes a partial transaction.
Shared manifest rows/review CSV and existing Activity `audio_manifest.sha256`
entries update with the audio. Shared rows become PENDING, never approved.
Original metadata is backed up with the corresponding transaction too.

The first production/installation error stops the producer. FAILED and
NEEDS_RECOVERY states block further jobs until explicitly resolved. Metadata
blockers are skipped while independent READY work can advance. A limited pass
can therefore replace a useful batch and still exit nonzero honestly.

## 6. Interruptions and bugs

Ctrl-C/SIGTERM leaves the durable journal. It does not cancel an external
VoxStage job. Before retrying, inspect that job, its error and queue. If a
complete matching staged pair exists, `run` can reuse it. An uncertain in-flight
cue without that pair becomes NEEDS_RECOVERY and is never auto-resubmitted.

```bash
python3 tools/regenerate_voice_corpus.py status --work-dir "$voice_run" --details
voxstage jobs list
voxstage jobs get JOB_ID
```

Preserve the reported job ID/submission key and `.result.json`. If interruption
occurred before the result was written, correlate the worker's recent job list
with the active path, voice and submission time. Do not reset its state while
the worker is still running. After investigating/fixing the source bug or a
failed provider job and establishing the worker is idle:

Substitute the exact failed cue path from `status --details` for the illustrative
`activities/example/...` path below.

```bash
python3 tools/regenerate_voice_corpus.py retry --work-dir "$voice_run" \
  --path 'activities/example/assets/audio/en/welcome.wav' \
  --acknowledge-provider-idle
python3 -u tools/regenerate_voice_corpus.py run --work-dir "$voice_run" --limit 1
```

`retry` archives failed candidates, checks the original destination, and resets
only that cue. It authorizes a **fresh attempt**, not recovery of the same
external job. Investigate completed output before spending another generation.
ASR warnings leave originals untouched; inspect/revise a failed take rather
than passing its files through an approval-stamping importer.

Bug ownership:

- inventory/classification/scripts: `tools/greia_voice_corpus/inventory.py`;
- replacement/recovery/restore: `store.py`;
- shared/checksum metadata: `catalogues.py`;
- serial lifecycle/heartbeat/candidate checks: `runner.py`;
- CLI/overrides: `tools/regenerate_voice_corpus.py`;
- prompts/defaults: `greia_voice_core/direction.py`, `character_delivery.json`;
- synthesis/transport/packaging: existing `greia_voice_core` provider/engine.

Fix the owning module; do not invent a second synthesizer or bypass the engine.
Add a focused regression, run the voice suites and required repository gate:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tools:. python3 -m unittest discover \
  -s tests -p 'test_greia_vo*.py' -v
make verify
```

The preceding provider migration review documents unrelated inherited ARM64
profile/installer host failures. Report the exact current gate result; do not
claim a prior PASS or fix unrelated Pi/installer work as part of voice repair.

## 7. Restore and completion

After generation, execute the automated review procedure:
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`. Its reports check installed audio
and exact frozen requests without changing this run or acceptance. Resolve or
document FAIL/WARN/BLOCKED results, and retain the separate listening gate.

To undo this entire run (including a partially installed pair), while no other
producer is running:

```bash
python3 tools/regenerate_voice_corpus.py restore --work-dir "$voice_run"
```

Restore walks transactions newest first, returning original audio, receipts and
metadata and removing receipts that did not exist originally. It refuses to
erase later edits. Investigate a conflict; do not delete the journal/backups or
force a broad Git reset. A restored run cannot be resumed into production;
create a new plan. Restore intentionally covers the whole run, not one file
whose shared manifest changes might depend on earlier transactions.

Exit codes: **0** complete replacement or successful utility operation;
**2** error, unresolved metadata, ASR warning or recovery work;
**3** READY work remains (limit/filter); **130** interrupted. `status` returning
0 means the status query worked, not corpus acceptance. Zero generation exit
means all non-excluded inventory rows are DONE, not that they were heard.

At completion: report counts by Activity/character/language, all preserved and
unresolved rows, actual worker failures/retries and receipt review states.
Check for newly added runtime speech since the original plan; inventory is a
snapshot. Listen to every replacement before declaring the corpus accepted;
at minimum prioritize all language/character combinations, long narrations,
numbers/words moved from native voices and every failed/retried take. Do not
publish a release image with review-pending speech.

Update HANDOVER, the existing four-language progress file and active
architecture-plan ledger with exact evidence. Commit/push coherent accepted or
clearly reviewable source/assets to `main`, preserving unrelated work. Keep the
external journal/backups and logs; no candidates, models or caches in Git.
Finish with `voxstage unload` once the shared worker is idle and this production
session is finished. Record remaining human-review work separately.

## 2026-10-21 correction: next three-character replacement

The owner rejected Dani/Momo/Tito's current sound: overly high/excited, inconsistent
Momo, aged/hyperactive Tito. Master identity controls pitch/register, age, timbre and
texture; recording prompts control only line-specific performance. Six neutral
default entries now replace the old recurring persona/acting descriptions.
The external v2 builder's PERSONA prefix and exaggerated generic praise are
confirmed contributors in prompt evidence, not proof of the sole acoustic cause.
Do not reuse those overrides for a new run or edit their frozen old receipts.

Two new master auditions per character are at external
`2026-10-21-calm-masters-v3/auditions.json`, served by Takeboard on 8795.
Dani 16.00/14.88s; Momo 14.24/14.88s; Tito 11.84/12.32s. They are new immutable
voice IDs, unselected and not installed. Current accepted registry bytes remain.
Master selection requires owner listening, then multilingual cloned-line checks
before bulk replacement. The draft scope is 1,340 DONE cues (392 Dani, 284 Momo,
664 Tito); deterministic isolated targets and other characters remain preserved.
`replacement-overrides.DRAFT.json` strips identity prefixes and tones down generic
performance. It is not a new frozen plan or authority to run with old masters.

Model reference guidance/research and job evidence:
`docs/reviews/2026-10-21_VOICE_DIRECTION_AND_REFERENCE_REVIEW.md`. The engine now
uses policy v2 screening; see automated review procedure §3a for reassessment.

### Owner master choices — 2026-10-21 follow-up

Owner saved Momo candidate 1 and Tito candidate 1 as approved in the v3 audition
batch. Their immutable IDs are `greia-audition-20261021-momo-v3-01` and
`greia-audition-20261021-tito-v3-01`; source WAVs/provenance are archived under
`assets/source/audio/character-voice-masters/v0.3/`. Both Dani v3 candidates were
rejected. Three new Dani v4 sound-only directions are being auditioned; no
canonical registry or runtime file is replaced until that selection/clone-check
step is ready. Do not rerender the already selected Momo/Tito references.

## 2026-10-21 correction: selected v0.3 masters and scoped corpus run

The owner selected Dani v5 candidate 02, Momo grounded v3 candidate 01, and Tito
grounded v3 candidate 01. Exact immutable VoxStage IDs are
`greia-audition-20261021-dani-v5-02`,
`greia-audition-20261021-momo-v3-01`, and
`greia-audition-20261021-tito-v3-01`. Dani candidates 01/03 are rejected in the
saved review. Their hashes, approval evidence and exact source bytes are archived
in `assets/source/audio/character-voice-masters/v0.3/`. Active semantic IDs are
`greia.dani.v3`, `greia.momo.v3`, and `greia.tito.v3`; Lilli, Leo and Flash retain
their v0.2 IDs and source bytes. The v0.2 canonical master registry/source
masters and prior v2 frozen plan/run journal remain unchanged. Runtime audio and
receipts selected in the v3 frozen scope were replaced in place; their original
bytes and receipts are retained in the v3 external run backups.

No v0.3 multilingual cloned-line comparison has been owner-accepted. A 12-output
VoiceEngine batch (one selected character × EN/IT/ES/FR) is a technical route and
receipt sanity check only; it does not certify audible identity, pronunciation,
performance, or human acceptance. All corpus outputs stay `human_review=PENDING`.

The frozen external v3 plan is
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/run-v1/`.
It uses `replacement-overrides.DRAFT.json` from the completed v2 plan plus the
neutral `character_delivery.json`. Reconciled READY scope: Dani 392 (EN 102, IT
102, ES 94, FR 94), Momo 284 (71 per locale), Tito 664 (166 per locale), total
1,340. All 1,340 exact source hashes, scripts and locales match the prior plan;
only selected-master identity and acting direction change. The new plan preserves
3,575 rows, including every row/path from v2 and six additional canonical v0.3
references; no old path was dropped. Other characters, deterministic isolated
letters/syllables, historical master/source libraries and unrelated user files
remain outside the generated scope. See the external run's `plan.json` and
status journal for the frozen scope and reconciliation.

## 2026-10-21 completion: v0.3 corpus production and automated screen

Serial VoiceEngine production completed with exit 0: **1,340 DONE, 3,575
PRESERVED, zero READY/FAILED/NEEDS_RECOVERY/BLOCKED**. Counts: Dani 392 (EN/IT
102 each, ES/FR 94 each), Momo 284 (71 per locale), and Tito 664 (166 per
locale). Deterministic isolated letters/syllables and unrelated preserved rows
were not replaced. The previous frozen v2 plan/run journal remains unchanged;
original in-scope installed bytes and receipts are recoverable from the v3
external run backups.

One Dani/EN `Toot toot!` request was rejected because VoxStage job
`20261021-143034-b8c58196` produced effectively silent audio with no result.
The producer exited 2, the failed job was inspected, no candidate WAV existed,
the original hash was unchanged, and the provider running list/queue were empty.
The documented idle-confirmed one-cue retry succeeded as job
`20261021-143155-c79f82e8`; that cue remains PENDING human review. The resumed
full pass completed with exit 0. Details are in external `run-v1/recovery-002.md`
and the resume log/exit record.

The required prepared-local-Python review used policy `greia-audio-screen-v2`
and cached `mlx-community/whisper-tiny`; full coverage and eligible ASR are
complete. Results: **1,115 PASS / 225 WARN / 0 FAIL / 0 BLOCKED**. ASR was 608
PASS, 199 WARN and 533 `NOT_APPLICABLE_POLICY`; WARN flags comprise 199 ASR
mismatch/error, 13 trailing silence ≥1.5s, 11 leading silence, 6 low level and
1 internal pause. Exit 2 represents retained warnings, not incomplete traversal.
No report changed audio or acceptance. Speaker identity, acting/mood,
pronunciation truth, independent language identification and small-speaker
intelligibility remain unassessed.

Full report and per-cue evidence are at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/full-automated-review/`;
the log is `full-automated-review.log`. Exported and validated Takeboard batch
`takeboard/batch.json` contains all 1,340 rows, all `unreviewed`, with character
counts Dani 392 / Momo 284 / Tito 664 and locale counts EN 339 / IT 339 / ES
331 / FR 331. It is served at `http://127.0.0.1:8799/`; the PID/log are beside
the batch and existing ports 8794–8798 were left untouched. All new receipt
`human_review=PENDING` states remain open. Prioritize the 225 machine warnings
and 533 ASR-policy exclusions, then listen across every character/language
combination, long narration, numbers/words, identity and acting. Machine results
never establish owner acceptance.

## 2026-10-21 correction: spoken-carrier parser v3 and paused priority recovery

The six-actor review-led short-cue first pass finished at 389 DONE / 274
FAILED in its continuation (plus four earlier DONE, 393 installed total). New
outputs remain listening-pending; no new provider requests or automatic retries
are running. The frozen source plan and its failed-run journal remain unchanged.
The 274 failed raw carrier candidates are indexed by the separate external
recovery ledger at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/recovery-v2/recovery-v3-plan.json`.

`tools/voice_carrier.py` now identifies itself as
`greia-spoken-carrier-extractor-v3`. Whisper may emit punctuation-only timed
entries, split French/Italian apostrophe clitics across entries, group multiple
lexical words in a single timed entry, or assign zero-duration suffix tokens.
The parser discards punctuation only from lexical comparison while checking
its timestamps and clip bounds; clitic tokens share one indivisible aligned
span; grouped tokens share their source span; and the known prefix boundary
must fall between whole timed spans. A zero-duration prefix or first target
entry still rejects. Zero-duration non-boundary suffix entries may pass only
with exact prefix, a valid first-target timestamp, and all clip-bound checks.
The unique guarded low-energy PCM gap, 200 ms minimum run, endpoint guards,
padding and voiced-output floor are unchanged. Parse failures now retain the
original word entries as evidence.

Offline v3 recovery pilot used only captured raw candidates, not synthesis.
French `sub_creature_turtle` passed exact raw/extracted ASR and the unchanged
gap gate (cut sample 38,895); the resulting candidate is not installed.
English `not_now` remained rejected because its only low-energy run was 140 ms
inside a 260 ms timestamp gap, shorter than the unchanged 200 ms minimum.
French `letter_E` had an exact prefix and measurable gap, but ASR heard the
suffix as “et comme est ce cargo”; it is explicitly a target-warning candidate,
not a pass. Human listening remains pending. Focused carrier, policy,
generation and corpus suites: 42/42 PASS. The final normal-environment
`make verify` used Python 3.14.6 and ran 3,180 tests: FAILED (31 failures,
244 errors, 6 skipped). The complete log is
`/tmp/greia-short-carrier-v3-make-verify.log`. The aggregate is not attributed
to the extractor without examining individual traces.

### Primary-verified v4 and resumed priority work

See `GREIA_SPOKEN_CARRIER_EXTRACTION.md` for the coincident-boundary repair.
The owner narrowed production to low-score/strong-warning short recordings;
remaining short clips are isolated in the external `triage/remaining-deferred`
CSV/JSON and must not be bulk regenerated. `retry-v4/run` freezes 266 unresolved
priority paths after seven saved-audio recoveries, retaining exact masters and
target words with explicit pause direction and at most three cumulative fresh
generations. Completed uncertain provider jobs must be found by idempotency-key
metadata, not by treating the key as a job ID. No clipping or score warnings
may be relabelled human acceptance. Exact current evidence is in HANDOVER.

### 2026-10-22 correction: target-suffix v5; bulk stopped

The owner clarified that the disposable intro may be noisy or mispronounced.
`voice_carrier.py` now locates the final target without requiring exact intro
recognition or an exact number of recognized intro words. Adjacent-span search
requires exact independent retained-target verification, never removed-intro
verification. See `GREIA_SPOKEN_CARRIER_EXTRACTION.md`. Frozen v4 plans deliberately
fail the algorithm-version gate under v5. The 266-priority retry and queued
sunhat follow-up remain stopped. Do not resume them or synthesize replacements
merely because a saved recording fails ASR. Stage v5 saved-audio replays externally
and distinguish CUT_CREATED, target warning, and human listening acceptance.
