# Agent work order: regenerate the existing Greia speech corpus

**Owner authorization:** 2026-10-19, following acceptance of six v0.2 masters.
**Executable:** `tools/regenerate_voice_corpus.py` (Python 3.11+).
**Scope:** replace existing Activity and system speech with fresh VoxCPM2
recordings, using the selected character masters and an explicit performance
prompt per recording. Preserve deterministic isolated letters and syllables.
**Current state (2026-10-21):** v2 generation complete; automated screening and
human listening are separate follow-up stages. Earlier preparation counts below
are historical; use HANDOVER and the actual selected run journal for current state.

**Current post-generation follow-up (2026-10-21):** v2 generation subsequently
completed (see HANDOVER). Run the read-only automated review in
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` using the new `review` command
before declaring automated screening complete. Generation DONE and a stored
receipt score are not audio review. ASR unavailability/disabled coverage must
remain explicit; new human review stays PENDING.

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
