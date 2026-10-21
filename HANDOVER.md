# Greia — Current Engineering Handover

**Purpose:** the short current state for contributors and agents: active workstreams, recent results, blockers and next steps. It is not an archive.
**Public-source readiness:** IN PROGRESS. Root entry points exist (`LICENSE`, `NOTICE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`); the licensing/provenance audit is open (see `NOTICE.md`).
**Ordinary-family release:** NOT READY (`docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`).

Entries dated before 2026-10-15 were removed from this file in the 2026-10-16 open-source cleanup. Read them with `git show 101e332a:HANDOVER.md`; lessons from that period are indexed in `docs/archive/README.md`.

Add new entries at the top of **Recent entries**, newest first.

## Active workstreams

Blocking and lifecycle authorities (rules in `AGENTS.md`):

- **Architecture remediation**: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` is the blocking plan for its remaining non-lifecycle obligations.
- **Install, update and release lifecycle**: `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` (ADR 0036 successor).
- **Cross-hardware robustness**: `docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md`, subordinate to the remediation plan; root causes go to `docs/INSTALLATION_ISSUES_LOG.md`.
- **Art and visual system**: `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`, resumed through `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`; Encyclopedia subplan `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`.
- **Parent authentication/runtime acceptance**: the single protocol is `docs/testing/2026-09-08_PARENT_UNIFIED_AUTH_RUNTIME_ACCEPTANCE.md`; production pairing and encrypted transport remain release blockers.
- **Testing route**: `docs/testing/LOCAL_AGENT_START_HERE.md`; local-agent queue `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.

Scoped owner-authorized workstreams (moved verbatim from `AGENTS.md` on 2026-10-16):

**Current owner-authorized Activity release + Creations workstream:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` is the **single unified product/content implementation plan** for the typed child Creations Library, universal pre-reader picker/viewer, adaptable disk budget, Painting/Shape Garden/Theatre/voice/text interoperability, complete built-in Activity quality audit, and deliberate catalogue selection. Continue from `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PROGRESS.md` and append accurate session results. This owner-requested scoped program coordinates those features but **does not supersede** the architectural-remediation and release-install/first-boot lifecycle authorities above; those still govern safety prerequisites, image installation, update, rollback and hardware acceptance. Product/source work may proceed in parallel without making hardware claims. Do not spin up a second competing catalogue, picker, or creative-media plan.

**Owner-authorized localization workstream (2026-10-12):**
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md` is the
scoped implementation plan for reducing misleading language choices,
completing EN/IT gaps, and extending real installer/OS/Parent/Activity
text and voice support to ES/FR. Its standing local-agent speech design and cue-source authority is
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_VOICE_PRODUCTION.md`.
**Current existing-corpus replacement work order (owner instruction 2026-10-19):**
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`, executed with
`tools/regenerate_voice_corpus.py`. It explicitly permits fresh replacement
with new masters and per-recording acting prompts, preserving deterministic
isolated letters/syllables and backups. V2 production has completed: 4,168 DONE,
741 PRESERVED, zero blocked or unresolved rows. Every new take remains
listening-pending. Source fixes needed to operate the tool and packaging are
authorized by this work order; ordinary queue-only restrictions do not block
that requested task. Post-generation screening follows
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`; automatic coverage and human
acceptance are separate from generation DONE.
**Earlier add-only voice-production work order:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`
(owner instruction 2026-10-14; archived full-run instruction). The owner approved
every **currently authored** EN/IT/ES/FR text translation, and personally
reviewed and approved **all committed recordings**. New missing files from
the targeted task still need fresh acceptance. Neither decision promotes ES/FR.
An available, registered zero-new-spend local Greia Voice Engine provider may
be used to record without waiting for a future Modal provider, but paid
cloud/model installation still needs separate explicit cost approval.
**Owner-directed shared localization consolidation (2026-10-15):**
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`
is the active bounded design for reusing the existing `LocalizedResources`
owner for semantic text/audio IDs, file-exists selected-locale lookup and
English fallback for **all** speech, and gradual migration of Activity-local
loaders. Existing committed audio is **owner-reviewed and accepted**;
never regenerate it for perceived provenance problems. The user does **not**
want file anti-tampering, signing or elaborate asset verification; users may
edit their files. Follow the focused new-recordings assignment in
`docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`.
Update the Activity-creation skill/voice companion **after the code API is real**;
retain the current callable interface meanwhile. This refactor does not
independently promote ES/FR system selection.
The sole practical local-agent task queue remains
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.
**Owner decision 2026-10-17:** EN, IT, ES and FR are all released and
selectable (selectors offer exactly these four); missing voice lines in all
four languages are owner-approved for recording with the local voice tooling
(no paid spend without approval).
This scope does not override ADR 0028, accepted architecture,
installer/first-boot/lifecycle test gates or the Creations/Activity
audit programme. Do not invent a second language registry or silently
promote unvoiced locales.

## Recent entries

## 2026-10-21 — Momo/Tito masters selected; new Dani v4 audition set

Owner saved **Momo v3 candidate 1** and **Tito v3 candidate 1** as approved;
Momo 2, Tito 2 and both Dani v3 candidates are rejected. Decisions were read
from the live Takeboard session and its saved `auditions.reviewed.json`.
Selected immutable IDs: `greia-audition-20261021-momo-v3-01` and
`greia-audition-20261021-tito-v3-01`. Exact approved source WAVs and provenance
are durably archived under `assets/source/audio/character-voice-masters/v0.3/`
and external `accepted-masters/2026-10-21-v3/`. SHA equality and mono PCM16
48kHz headers/durations verified (14.24s Momo / 11.84s Tito).

This is a selected-source checkpoint. Active canonical registry remains v0.2;
no runtime audio or generation receipt changed and no 1,340-file run started.
Do not redesign these approved Momo/Tito voices. Dani remains the open choice.

Three new, distinct Dani sound-only descriptions omit robot/buzzy/nasal persona
cues: A warm adult baritone (seed 64100), B adult contralto (64200), C low-middle
androgynous (64300). Shared VoxStage jobs respectively
`20261021-084311-4e1f545d`, `20261021-084312-11543bdb`,
`20261021-084314-362a30b8` all completed: 11.68s / 15.20s / 15.84s.
These labels describe requested properties, not agent listening approval.
New candidates remain unreviewed. Queue was initially idle, and the model was
unloaded after all three completed; no other project jobs were altered.

New listening batch: external `2026-10-21-dani-v4/auditions.json`, served at
http://127.0.0.1:8797/. Reference player compares the previously rejected Dani
v3 candidate 1 (not an accepted master). Existing 8794/8795/8796 sessions and
human decisions remain intact. Browser checks show three entries and playable
new/reference media, no fabricated review decisions. No software code changed
or tests rerun; previous 5,491-test gate remains NOT GREEN for its recorded
inherited failures. No phase/runtime/physical/release acceptance is claimed.

**Next:** owner selects Dani A/B/C (or rejects them), then selected-set registry
promotion and representative multilingual cloned-line checks before freezing
and running the corrected 1,340-file replacement. Preserve approved Momo/Tito
bytes/IDs. New generations still require their own acceptance.

## 2026-10-21 — Owner review policy v2; voice identity separated from acting

**Owner direction:** tail/internal pauses below 1.5s should not warn; automated
transcript PASS requires similarity strictly above 0.8 and other checks clear.
Added shared `review_policy.py`, aligned live Whisper default and review, and
added corpus `reassess --evidence-dir` to check unchanged saved evidence then
apply policy without another ASR run. Metadata/real silence and unrelated flags
remain; ASR exclusions never become transcript verification. Original reports
and receipts are untouched. Executed full reassessment: **3,073 PASS / 1,094 WARN /
1 FAIL**. ASR 1,611 PASS / 863 WARN / 1,693 excluded / 1 unrun (silent Bear).
Reports: external `2026-10-21-full-review-policy-v2/`; new listening batch/URL:
`2026-10-21-listening-policy-v2/batch.json`, http://127.0.0.1:8796/.

**Human decisions protected:** browser had 104 unsaved owner reviews. Exported
that exact draft, preserved its separate backup, and copied reviews by matching
ID/audio into the new batch: **82 approved / 22 rejected / 4,064 unreviewed**.
These are the owner's JSON decisions, not machine approvals or promoted receipts.
The original tab/server on 8794 remains intact with its 104 dirty records. Backup:
new listening folder `owner-draft-before-policy-v2.json`; no drafts were discarded.

**Owner diagnosis:** Dani/Momo/Tito are too high/excited; Momo inconsistent; Tito
aged/hyperactive. Investigation confirmed duplicated persona + generic excitement
in old default/explicit corpus prompts. It is a plausible contributor, not proof
of the sole acoustic cause. Owner clarified fixed register/pitch, timbre, age and
texture belong only in master design. All six default entries now use neutral,
unhurried delivery; per-cue overrides should contain only line-specific acting.
VoxStage clone wiring was traced and does not automatically repeat saved master
descriptions. Frozen v2 overrides/receipts remain historical evidence, not inputs
to reuse for the new run.

**New master auditions executed:** two seeds each for Dani/Momo/Tito, using the
existing shared worker. Six new immutable candidate IDs, natural common 46-word
script, requested grounded registers and restrained reference acting. Dani
16.00/14.88s, Momo 14.24/14.88s, Tito 11.84/12.32s. Candidate WAVs, requests/jobs,
Takeboard batch and a replacement draft live at external
`2026-10-21-calm-masters-v3/`, http://127.0.0.1:8795/. No canonical master or
runtime recording was replaced. Listening/transcript completeness remain pending.
Shared queue emptied, model unloaded, server retained. Reference research says
5–30s is practical; old 7–10s refs are within range, not shown to be token-capped.
See `docs/reviews/2026-10-21_VOICE_DIRECTION_AND_REFERENCE_REVIEW.md` for primary
links, actual backend trace and job evidence.

**Verification:** 72 focused voice tests PASS (1.48/1.5/1.52s, 0.8 boundary,
reassessment without ASR, stale evidence rejection, neutral defaults). Full
`make -k verify`: 5,491 tests, inherited 1 MBR diagnostic failure, 4 errors
(ARM64 builder expectation, profile executable permission, two missing lsblk
installer tests), 8 skips. Project validation retains ARM64 restriction;
shell/footprint completed. Gate NOT GREEN. External logs:
`2026-10-21-review-policy-v2-tests.log`, `2026-10-21-review-policy-v2-verify.log`.

**Next:** owner listens/selects one new candidate per character, then multilingual
cloned-line checks before a new frozen replacement plan. Draft scope is 1,340 DONE
files: Dani 392 / Momo 284 / Tito 664; neutral/line-specific performance overrides
prepared, other characters and deterministic targets preserved. Draft is NOT run
or ready to freeze against old references. It needs the selected new masters.
No architecture/lifecycle/runtime/physical release gate closes here.

## 2026-10-21 — Shared Takeboard listening tool delivered; Greia exporter added

The completed automated traversal (preceding entry) now has a loadable human
listening batch at `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-listening/batch.json`:
4,168 recordings, selected master comparisons, spoken text, direction/generation
metadata and automated findings. All human fields start **unreviewed**; no receipt,
audio, frozen plan, journal or runtime acceptance was changed. Read-only exporter:
`tools/export_voice_review_batch.py`; it refuses partial reports and existing outputs.

Owner-authorized shared tool **Takeboard** lives in its own project/repository,
`/Volumes/Test1/Works/takeboard`, https://github.com/frozenpepper/takeboard (private).
It has a versioned generic JSON contract, local HTML UI, bounded 50-row pages,
filter/search, generated/reference players, keyboard navigation, human states,
1–5 scores/notes/reviewer, atomic explicit saving and JSON export/reload. CLI is
`takeboard`; source resumes matching `.reviewed.json`, and exported media_root
is absolute so Downloads does not break playback. Setup, agent operations, voice
and OS skills, architecture pointer, shared catalog and both agent skill links
are updated. The shared core has no Greia imports, ASR, model or runtime coupling.
Exact launch/usage and integration boundary: automated review procedure §6.

**Verification executed:** standalone Python 19 checks PASS; JavaScript 2 tests
PASS including 20,000-entry state/filtering and lossless roundtrip; Greia adapter
3 focused tests PASS. Actual in-app browser loaded the 18 MiB/4,168-entry batch
with exactly 50 rows and working WAV/reference metadata, zero narrow-panel
horizontal overflow. Disposable two-row data exercised edit/save/page reload,
actual downloaded JSON reload, file-picker import and keyboard J/1/0. No real
batch decisions were fabricated. A startup input race was caught and fixed;
server also rejects stale tabs after batch switching. Browser proof does not
constitute listening or desktop-wide/physical acceptance.

Full `make -k verify` ran 5,484 existing tests: 1 known MBR assertion failure,
4 inherited errors (ARM64 builder expectation, build_profile executable permission,
two missing-lsblk installer tests), 8 skips; project validation also failed on
ARM64 restriction, shell/footprint steps completed. The three exporter tests
were added after discovery started and ran separately; no false 5,487-test gate
claim. Full gate remains NOT GREEN. External log:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-takeboard-greia-verify.log`.
Standalone exact evidence is in its `VERIFICATION.md` and external QA/log files.

**Next:** open http://127.0.0.1:8794/ and listen/score, saving the sibling
`batch.reviewed.json` or exporting. A detached local server is running; its PID,
launch input and log are in the listening folder's `takeboard-process.json` and
`takeboard-server.log`. To restart: `takeboard serve <absolute batch.json> --port 8794`.
Saved JSON is portable review data; applying it to canonical Greia assets is
separate work. Silent EN Bear and other findings remain unchanged. No phase,
audio acceptance or image release is closed. Unrelated untracked artifacts remain.

## 2026-10-21 — Full V2 corpus automated review completed

The unfiltered cached-Whisper review completed on the frozen V2 run with
**4,168/4,168 DONE recordings covered** and **741 PRESERVED recordings excluded
by policy**. The terminal summary is `complete=true`,
`full_corpus_coverage=true`, and `generation_problems={}`. Results: **2,905
PASS, 1,262 WARN, 1 FAIL**. Eligible ASR is not fully complete only because the
single hard-silence FAIL did not proceed to ASR: **1,853 ASR PASS, 621 ASR WARN,
1,693 NOT_APPLICABLE_POLICY, 1 NOT_RUN_ERROR**. The process finished its
traversal; the report's `human_acceptance_granted` is false. No audio, receipt,
generation state, or acceptance was changed.

The sole FAIL is
`activities/officina_dei_suoni/assets/audio/en/bear.wav`: installed WAV RMS
**-77.7 dBFS** (effectively silent). Its installed SHA matches the PENDING
receipt and the exact frozen Leo/English `Bear` request; this is a real bad-take
finding, not a verifier crash. There were **621 ASR transcript mismatch WARNs**,
539 long-tail silence, 165 long-leading silence, 122 low-level, and 72 long
internal-pause flags. One additional cue,
`activities/mondo_contrari/locales/en/audio/big.wav`, raised
`POSSIBLE_PROMPT_LEAKAGE`: Whisper transcribed “playful, clear words” from the
acting direction along with the expected line. These flags need human listening;
they do not prove pronunciation, language, identity, mood or child intelligibility.

Evidence is external at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-full-automated-review/`
(configuration, 4,168 per-cue records, `review.jsonl`, 4,168-row
`listening_queue.csv`, terminal summary, and process/package metadata), with
console log
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-full-automated-review.log`.
The prepared Greia Python and cached `mlx-community/whisper-tiny` were used; no
installation/download occurred. The separate VoxStage queue was inspected and
all Depleted Rain jobs/model were left untouched.

**Next exact step:** build the owner-authorized generic local HTML listening
tool against this report's queue/records, then work the prioritized queue with
human states, scores and notes. Keep every replacement `human_review=PENDING`
until a person listens and records acceptance. No synthesis, audio repair,
source fix, release decision, or human listening acceptance is included here.

## 2026-10-21 — Whisper blocker corrected: use prepared authoring Python

The previous automated-review blocker was scoped to the wrong interpreter,
not the prepared Greia environment. Global `/opt/anaconda3/bin/python3` has
NumPy 2.0.2 and an ABI-incompatible compiled Numba 0.60.0. The existing
`~/Library/Application Support/Greia/voice-production/venv/bin/python` imports
mlx-whisper 0.4.3 successfully with NumPy 2.5.2, Numba 0.67.0 and MLX 0.32.1.
Cached whisper-tiny revision `78c52ab98ca87f570bc57ad852e15ef7060f9f76`
was available. No packages, weights, global Python or shared synthesis stack
were changed. This corrects the preceding entry's implication that ASR setup
needed repair before review could run.

**Executed live ASR proof:** existing `review --asr auto` command, using that
explicit interpreter, filtered to
`activities/alfabeto_leo/assets/audio/*/ask_A.wav`, four installed languages.
All four ran ASR: EN/ES/IT transcript PASS (scores 1.0/0.899/0.7265), FR WARN
(0.2721). EN/IT also flag LONG_TRAILING_SILENCE. Overall 1 PASS, 3 WARN,
0 BLOCKED, command exit 2 as expected for findings. These flags are retained
for investigation; no regeneration or human acceptance occurred. The shared
VoxStage queue was inspected; other-project jobs were preserved. This bounded
Whisper-tiny pass did not load another large synthesis model.

Evidence: external `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-whisper-recovery/`
(configuration, individual records, review.jsonl, listening_queue.csv, summary)
and sibling `2026-10-21-whisper-recovery.log`. Four clips are not full-corpus
coverage. The runbook, SETUP, setup manual, engine quick start, voice skill and
external v2 RUNBOOK now give explicit prepared-interpreter commands.

**Next:** use that interpreter and a fresh external report folder for the full
4,168-cue automated pass per `GREIA_AUTOMATED_VOICE_REVIEW.md`, investigate
flags and retain the separate human listening gate. Documentation/procedure
correction only; no source changed or test suite rerun this turn. The preceding
recorded full verification failures remain open. No phase/release acceptance.

## 2026-10-21 — Automated voice review command and agent procedure

Implemented `tools/regenerate_voice_corpus.py review` and
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`: installed WAV/OGG decode/signal
screening, frozen request/receipt consistency, cached-only eligible Whisper ASR,
possible prompt leakage flags, resumable external reports and a prioritized
listening CSV. Review holds the existing generation lock and reads the journal
read-only; it never synthesizes, changes audio/receipts or grants acceptance.
Partial traversal, ASR off/unavailable and policy exclusions are explicit.
Source collaborators belong to `greia_voice_core` and `greia_voice_corpus`;
setup, engine/design docs and all affected living skills/manuals now route here.

**Executed evidence:** 68 focused voice tests PASS, including known silence,
prompt leakage, unavailable/runtime-failing ASR, unchanged-input resume and
source/journal preservation. Installed v2 pilot: eight signal/metadata PASS
with ASR off; separate two-clip ASR pilot BLOCKED because host Whisper cannot
import (`numpy.core.multiarray failed to import`). Reports/logs are external at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-automated-review-smoke/`
and `2026-10-21-voice-review-tests.log`. These bounded pilots are not full
4,168-clip review or human acceptance. No downloads or generation occurred.

`make -k verify` ran 5,484 tests: 1 known MBR diagnostic assertion failure,
4 errors (unsupported ARM64 builder assumption, non-executable build_profile.py,
and two installer tests requiring missing lsblk), 8 skips. Full gate is NOT
GREEN; these are outside this voice change. Project validation also fails
on the existing ARM64 builder restriction; shell and footprint steps completed.
Full log:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-voice-review-make-verify.log`.
This also corrects the preceding entry's attribution of all four errors to
three lsblk tests plus permissions: the actual split includes the ARM64 test.

**Next exact step:** select the existing prepared ASR environment per SETUP,
resolve its readiness without modifying the shared synthesis stack, then run
pilot/full commands in the new procedure with fresh external reports. Automated
flags require investigation; all replacement takes remain human-review PENDING.
No remediation phase, runtime, physical or release acceptance is closed.

## 2026-10-21 — V2 corpus replacement completed; verification recorded

The owner-authorized V2 journal is complete: **4,168 DONE, 741 PRESERVED, zero
READY, FAILED, NEEDS_RECOVERY, or BLOCKED**. The interrupted French strawberry
cue was resumed only after correlating its original, plan request, last job and
absence of a candidate or prior POST; job `20261020-235846-ff7ff0a5` completed.
Bean's runner timeout was reconciled to completed VoxStage job
`20261021-000412-50cad22f` by exact idempotency key and frozen request/master
metadata, then installed offline through the existing transaction path without
another inference. Final DONE receipts, requests, and output hashes were checked;
all replacements remain `human_review=PENDING`.

VoxStage queue is empty and its model was unloaded after the serial batch. The
final `make verify` ran 5,472 tests: **1 failure, 4 errors, 8 skipped**. The
remaining failures are the known host-only MBR diagnostic mismatch, missing
macOS `lsblk` (three installer errors), and non-executable
`tools/build_profile.py`; Encyclopedia's size regression was fixed while
preserving its 50 MiB cap. See the four-language progress ledger and external
run journal for detailed evidence. No ASR or human listening, GUI, Simulator,
or physical acceptance is claimed. Current source, docs, regenerated corpus,
receipts, manifests, and identified leftover deletions are being selectively
published to `main`; unrelated `final.mp4`, `launch-video/`, and the separate
review audit remain untouched.

## 2026-10-19 — Corpus replacement checkpoint: 700 complete

The resumed owner-authorized full READY pass remains active in shell session
`85073`. Current status: **700 DONE, 1 GENERATING, 3,842 READY,
167 BLOCKED_METADATA, 598 PRESERVED**; current cue is Encyclopedia Greia EN
`activities/enciclopedia_greia/assets/audio/en/body/senses_hearing.ogg`.
VoxStage PID `19719` is the sole loaded worker. The pass has advanced through
English animal and body facts; long narration cues take roughly 15–60 seconds
each. No additional failures or recovery transactions have appeared since the
explicit idle-confirmed retry of Bottega ES `prompt_order_length.wav` (job
`20261019-201240-59474c63`).

All replacement receipts remain `human_review=PENDING`. Whisper verification is
off on this host; no ASR or human listening acceptance is claimed. The 167
metadata gaps remain excluded while independent READY work proceeds. Logs,
journal, candidates and recoverable originals remain in
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
Unrelated untracked `final.mp4` and `launch-video/` remain preserved. Continue
monitoring the same run and inspect any uncertain VoxStage job before retrying.

## 2026-10-19 — Corpus replacement checkpoint: 602 complete

The resumed full READY pass is active in shell session `85073`. Latest status:
**602 DONE, 1 GENERATING, 3,940 READY, 167 BLOCKED_METADATA, 598 PRESERVED**;
current cue is Costruiamo Ponti IT `too_heavy.wav`. VoxStage PID `19719` is loaded
with one active job. The earlier failed cue, Bottega delle Misure ES
`prompt_order_length.wav`, produced effectively silent audio; its original was
untouched, the job failed terminally with no candidate output, and queue 0 was
confirmed before an explicit single-cue retry. Fresh job
`20261019-201240-59474c63` completed and was transactionally installed with its
receipt PENDING. The full pass has resumed past it; no further failures are
recorded. External logs, journal, candidates and backups remain under
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.

Whisper remains unavailable and verification is off; no listening acceptance is
claimed. The 167 metadata blockers remain unresolved and are skipped while READY
cues continue. This checkpoint supersedes prior running counts; next continue
monitoring and inspect any exact job before an explicit idle-confirmed retry.


## 2026-10-19 — Corpus replacement checkpoint: 304 complete

Latest status for the active serial full pass (session `45485`): **304 DONE,
1 GENERATING, 4,238 READY, 167 BLOCKED_METADATA, 598 PRESERVED**. Current cue:
Baia delle Orche FR activity-title. VoxStage PID `19719` remains the sole loaded
worker. The producer heartbeat and per-cue journal transactions continue without
FAILED or NEEDS_RECOVERY rows. Completed receipts remain `human_review=PENDING`;
Whisper is unavailable and verification remains off.

The pass has completed the four-language Alfabeto Leo set and substantial
Baia delle Orche cues. The 167 exact-script blockers are unchanged and continue
to be skipped independently. External work directory, backups and logs remain
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
Continue monitoring and recover only source-backed scripts; this checkpoint
supersedes earlier running counts below.


## 2026-10-19 — Corpus replacement checkpoint: 198 complete

The active full READY pass (shell session `45485`) has **198 DONE, 1 GENERATING,
4,344 READY, 167 BLOCKED_METADATA, and 598 PRESERVED**. Current cue: Alfabeto Leo
IT `ask_G.wav`. VoxStage is the same single worker (PID `19719`), and the external
production log/journal remain at `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
The stream is progressing with heartbeats; there are no FAILED or NEEDS_RECOVERY
rows. Completed receipts remain listening-pending. No exact-source recovery has
yet substantiated an override for the 167 blocked rows, which continue to be
skipped while READY work runs. This newer checkpoint supersedes the count in the
prior in-progress entries below.


## 2026-10-19 — Corpus replacement checkpoint: 101 complete

The full READY run remains active in shell session `45485`; the external log and
journal are under `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
Latest exact status: **101 DONE, 1 GENERATING, 4,441 READY, 167 BLOCKED_METADATA,
598 PRESERVED**. The current cue is Alfabeto Leo ES `guess_prompt.wav`. VoxStage
PID `19719` remains loaded with one job, and the runner is emitting completed
transaction heartbeats. No failures or recovery states have appeared. All new
receipts remain `human_review=PENDING`; no listening or ASR acceptance is claimed.

Source/history review has not yielded enough exact-script evidence to resolve any
of the 167 blockers, so READY work continues independently. Preserve the four-cue
pilot and all subsequent originals/journal outside Git. Next: continue monitoring
the serial run and investigate exact blocked scripts; do not resubmit an uncertain
provider request or alter DONE rows. This checkpoint supersedes the earlier
in-progress count below without changing its historical record.


## 2026-10-19 — Full voice corpus replacement running (SOURCE / LOCAL RECORDING, in progress)

The owner-authorized replacement is now using the prepared external run at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
`plan.json` matches the current v0.2 registry manifest SHA
`0f96de93a42b9f11f16f16a9aeaf479615509fbc9b5fb93812cadbdae694c64e` and
freezes all six acting prompts. The 4-cue technical pilot completed; its outputs
and all later replacements have journaled originals, receipts, and derived
catalogue updates outside Git. Receipts remain `human_review=PENDING`.

Full serial production is active in shell session `45485`; log:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/production.log`.
Latest status at this entry: **25 DONE, 1 GENERATING, 4,517 READY,
167 BLOCKED_METADATA, 598 PRESERVED**. The active cue is
`activities/alfabeto_leo/assets/audio/en/ask_J.wav`. Shared VoxStage worker PID
`19719` is loaded with one running job; heartbeats and completed transactions
are advancing. Optional Whisper is unavailable due the host NumPy/Numba mismatch;
verification is explicitly off. No human listening or ASR acceptance is claimed.

The 167 blocked rows remain unresolved pending exact source/history scripts;
independent READY rows continue. No production failure or source bug has occurred.
Preserve `final.mp4` and `launch-video/`. Next: keep monitoring the full run,
continue exact-script recovery and `resolve` only substantiated gaps, then report
final counts/retries, update this handover and the rollout progress ledger, and
commit/push the clearly reviewable PENDING replacements with backups/journal
retained externally. Human acceptance and release publication remain separate.


## 2026-10-19 — Corpus regeneration tool and per-recording performance direction

**Owner scope:** prepare a Python tool for the next agent to replace existing Activity/system speech with the new masters/model, preserving deterministic isolated letters/syllables, showing progress, and supplying a launch/monitor/repair Markdown handoff. The owner then required tone/mood prompts for every recording. This explicitly permits the scoped replacement; it does not mean future takes have been listened to.

**Implemented:** `tools/regenerate_voice_corpus.py` (`plan`, `resolve`, `run`, `status`, `retry`, `restore`), with focused collaborators in `tools/greia_voice_corpus/`. It inventories existing files using receipts and source catalogues/full Encyclopedia scripts, freezes semantic requests and acting prompts, uses one warm serial VoiceEngine with VoxStage forced, displays progress/15-second heartbeat, stages candidates, backs up originals and journals recoverable audio/receipt/catalogue replacement. It preserves uncertain provider failures for operator inspection and never silently resubmits them. Restore walks transactions in reverse and refuses later-edit conflicts. Shared manifest/review rows and Activity audio checksums update with replacements; new receipts remain human-review PENDING. `VoiceRequest.delivery_prompt`, CLI `--delivery-prompt`, batch and warm service now carry performance direction. Six editable defaults in `tools/greia_voice_core/character_delivery.json` apply to normal VoxStage production as well. Chatterbox/native reject an explicit unsupported prompt. The implementation remains modular; no child-runtime or second model producer was added.

**Prepared inventory:** `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/` contains plan, SQLite state, initial `blocked.csv` and override template: **5,308 files, 4,543 READY, 167 BLOCKED_METADATA, 598 PRESERVED** (441 isolated letter/syllable files, 150 historical shared clips, six masters and one boot chime). The 167 older files need exact script/identity recovery; do not invent text or hide them as successful skips. `resolve` can repair only these blocked rows without rerecording DONE work. All READY cues have explicit prompts. Ordinary runtime recordings and selected masters remain unchanged in this preparation turn; the full corpus production run was NOT launched.

**Evidence:** **52 focused voice tests PASS**. One real external Lilli/English/custom-direction OGG smoke completed in VoxStage job `20261019-100927-df5c3cf4`; the persisted worker request and recording direction match the prompt and the receipt identifies the selected v0.2 master with human review PENDING. This proves transport/production, not audible acting acceptance. The shared model was unloaded afterward. Final `make -k verify` on the completed code ran **5,468 tests: 1 failure, 4 errors, 8 skips**, the same inherited ARM64 profile, CLI executable mode, two macOS `lsblk` installer and stale MBR-message cases as the preceding migration review. Project validation still fails at the inherited ARM64 builder assumption; shell/footprint ran. Full aggregate gate is NOT GREEN. Evidence: `docs/reviews/2026-10-19_VOICE_CORPUS_TOOL.md` and external `2026-10-19-corpus-inventory-v3/{voice-tests.log,make-verify-final.log,delivery-smoke*}`. No release-image/Simulator/physical listening proof or remediation-phase closure.

**Next exact step:** the local agent follows `docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`: recover the 167 missing legacy scripts where possible, inspect/pilot the character performance defaults, launch/resume the production run, monitor status/jobs, fix owning modules if necessary, and retain backups plus new listening-pending receipts. The runbook is the current executable replacement order within the existing four-language workstream. Relevant source manuals/skills, earlier work-order overrides and the one local-agent queue were updated; ignored installed skill copies were refreshed. Unrelated untracked `final.mp4`/`launch-video/` remain preserved.

## 2026-10-19 — RC installer rebuilt from current `main` and flashed to the LaCie

**Evidence class: SOURCE + BUILD/MEDIA READ-BACK GATES. No QEMU boot, no physical Acer install in this turn.**

- Pulled `main` `6965adb9` → `b750e714` (clean tree) and built `legacy-x86-i686-rc` through the documented front door (`tools/build-and-flash-development-usb.sh`, inside `unshare --mount --propagation private`, operator public key `SHA256:0oRmaFqZpIYFsGj0N2++I6oma2kHtqdOQMQjXITYVXU`).
- Flashed the whole-device-authorized LaCie `/dev/sdc` (`iamaKey`, serial `eca3505216d7d3`, 7.5 GiB, `TRAN=usb RM=1`), previously mounted and unmounted before writing.
- **Image** SHA-256 `d177baec8ba0cf8229fee05512e1a1e4ec31994a3152b88fca229dfee199f514`; live media id `a7f03fe3-2240-48e6-9c53-811c35765b26`; payload accounted **1,201 MiB** (< 1,300 gate); `boot_console_policy=quiet`.
- **Gates:** artifact verification PASS, live USB read-only verification PASS, `usb_readback_verification=PASS`, `loop_hygiene_verification=PASS`; independent verifier re-run PASS; no Greia loop devices left. Log `out/rc-build7-b750e714.log`; plan entry appended to the 2026-09-15 lifecycle plan.
- **Next exact step:** install from this LaCie on the reference Acer through the graphical installer, then run premortem §5 F1–F19 including the hidden `verbose` recovery check (F2), and record physical results here.

## 2026-10-19 — Owner-selected v0.2 masters and VoxStage/VoxCPM2 default

**Owner direction:** the six selected masters and 24 EN/IT/FR/ES comparison samples are accepted; adopt the new masters and provider as the Voice Studio / general character-production default, retaining Chatterbox. Active registry is now `assets/audio/characters/canonical/v0.2/manifest.toml`; exact source WAVs and portable design/selection provenance are in `assets/source/audio/character-voice-masters/v0.2/`. The old v0.1 set is historical. Existing accepted runtime audio and receipts are unchanged.

**Implementation:** `composition.py` selects VoxStage by default for all six characters (including Dani); `voxstage_provider.py` adapts semantic requests and `voxstage_client.py` reuses the existing serialized local worker. No second model stack or child-runtime synthesis was added. Missing library entries import the exact repository reference/transcript without overwriting saved IDs. Chatterbox is explicitly selected by `--character-provider chatterbox` or `GREIA_VOICE_CHARACTER_PROVIDER`; there is no silent fallback. Dani's existing speech kind remains compatible; pedagogical pronunciation retains native/system routing. The warm client now separates its ten-second connection deadline from the generation response deadline. Canonical installation handles six WAV masters and six WAV references. Runtime asset composition hides canonical authoring references and removes earlier leaked copies from reused staging roots; shared playable audio remains installed. Docs, setup, operations and relevant skills/work orders reflect these contracts. Ignored local `.agents/skills/` copies were also refreshed from the canonical affected skill directories.

**Evidence so far:** 37 focused voice/packaging tests pass; installer check verifies all twelve canonical files. Real default `generate`, five-character `batch` and `serve/request` calls produced review audio/receipts for all six selected voices; retained Chatterbox generated in offline mode from cached weights; native pedagogical speech also generated. Smoke clips remain human-review pending. Source base was refreshed from `43045003e` to concurrent upstream `245ed1573`; the final `make -k verify` ran 5,449 tests with the same five deterministic baseline cases failing (1 failure, 4 errors, 8 skipped); the launcher-memory test passed this time. The aggregate gate is NOT GREEN. Project validation fails at the same inherited ARM64 builder assumption, reproduced on untouched baseline. All 45 Activity validators, shell syntax and footprint checks PASS independently, and bytecode cleanup completed. The earlier full run executed 5,437 tests (2 failures, 4 errors, 8 skipped): five deterministic failures reproduce on untouched `43045003e` (ARM profile assumptions, non-executable build-profile CLI, two macOS `lsblk` installer tests, stale MBR error expectation). The launcher-memory failure passed in isolated baseline execution and is not claimed fixed. Optional Whisper is unavailable in this host's Anaconda/NumPy environment; synthesis checks used verification off. No image rebuild or physical playback proof is claimed.

**Continuation:** voice migration implementation is SOURCE-CLOSED; use `voxstage start` then `python3 tools/greia_voice.py doctor` for new production. Existing upstream test/project-validator failures and the optional host Whisper environment remain separate follow-up work. New clips still require human listening. No remediation or lifecycle phase is closed by this authoring-provider migration. Full evidence/commands are in `docs/reviews/2026-10-19_VOXSTAGE_VOICE_MIGRATION.md`.

## 2026-10-19 — Research-led Pi 400/500 verification (read-only boot evidence; installer still blocked)

**Baseline:** main 43045003e39c4d020647309760d19a41182b98f3. Independently checked Raspberry Pi's official autoboot/tryboot/config.txt and kernel documentation, firmware release notes, reported A/B GPT/partition-walk failures (rpi-eeprom #818, corrupted autoboot forums), and Raspberry Pi rpi-image-gen's boot-device-backed slot and persistent-state design. Findings and source references: `docs/reviews/2026-10-19_RASPBERRY_PI_RESEARCH_LED_VERIFICATION.md`.

**Changes:** strengthened built-in Pi MMC policy to require 32-hex-digit CID rather than arbitrary nonempty text; updated fake SD test identity and added negative invalid-CID assertion. New **read-only** `greia_platform.pi_boot_observation` decodes firmware's big-endian 4-byte selected-partition and tryboot properties, compares them with canonical `autoboot.txt`, slot-root P5/P6 PARTUUIDs and the Linux root= parameter; rejects contradictory facts. Eight focused tests added, including negative boot-state cases. It never arms trial boot or commits accepted slot.

**Verification:** Python 3.13 local syntax compile and isolated new-module harness 8/8 PASS, with temporary stand-ins for two other Greia module APIs; NOT full-repo tests. No `make verify`, image build, loopback geometry, QEMU, real EFI/firmware or Pi hardware evidence. **Pi installer continues to refuse before erase; not bootable/not released**. Exact next steps: run full-repo focused tests and make verify, physical **read-only** Pi EEPROM/model/MMC diagnostics, loopback DOS partition validation, implement native ARM media + firmware boot + recovery/update transaction, then owner-approved physical destructive acceptance. No Github Actions or paid cloud runners without opt-in.


## 2026-10-19 — Pi verification pass 2: slotted-dataclass policy failure and malformed FDT assets

**Baseline reviewed:** main `e37aa437a3cdcc87c65fc26bd36a43ca25b7751a`. Source inspection reconfirmed executable Pi adapter, MBR sizing and early non-destructive full-installer refusal. An independent Python reproduction confirmed that zero-argument `super()` in `@dataclass(frozen=True, slots=True)` can throw `TypeError`; the Pi removable-card policy did exactly that when built-in CID proof was absent. Replaced with explicit parent-method delegation. Added `lsblk` JSON → sysfs Pi 500 MMC CID → policy target-selection integration test (including a USB installer competitor) and negative no-exception cases. Boot-asset stager now rejects non-FDT/truncated DTB and overlay containers, with corresponding tests. Read `docs/reviews/2026-10-19_RASPBERRY_PI_INSTALLER_SOURCE_REVIEW.md` § follow-up verification pass 2 for full findings and first-run test commands.

**Evidence limitations:** no Greia Python tests, `make verify`, real parted/mkfs, ARM64 composition, QEMU or Pi hardware tests executed in this turn. Native Pi installation remains **NOT IMPLEMENTED END TO END**; early fail-closed before erase is intentionally preserved. Next action: local source tests, then only authorized disposable loop geometry, then finish ARM setup/live and native Pi firmware A/B/recovery before any physical erasure.


## 2026-10-19 — Pi 400/500 WIP source consolidated on main after adversarial review (UNVERIFIED)

Owner asked for Pi installer implementation and review. The earlier draft PR #10 at `9f209139` had a serious source/claim regression: the final committed `PiMbrTrybootAbAdapter` was STILL deferred/64 MiB despite an intermediate blob being executable/256 MiB. This review discovered it by fetching the committed file. The new `main` changes reconstruct the executable Pi DOS P1/P2/P3 256 MiB FAT, P4 extended, P5-P7 ext4 A/B/PERSIST adapter, account for logical EBR alignment in exact minimum capacity, reuse observed MBR PARTUUIDs, and check the Pi built-in microSD target policy before emitting destructive commands. Source also adds Pi 400/500 ARM64 experimental profiles and package maps (builder correctly refuses ARM64 still), offline board-specific boot-file staging with uncompressed AArch64 Image-header preflight, and sysfs Pi MMC-host/card-CID observation while preserving USB/removable safety. Full Pi install transaction still **refuses prior to wipe** until the ARM media and native firmware installer are complete.

**Evidence scope:** source review and changed test sources only; `make verify`, full Python tests, actual partition commands, ARM64 build, QEMU and physical Pi tests were NOT executed here. The correct binding review, risks, test order and further work are in `docs/reviews/2026-10-19_RASPBERRY_PI_INSTALLER_SOURCE_REVIEW.md`. Raspberry Pi installation is **NOT COMPLETE**, not yet installed or safe to try on user media. Continue from the active 2026-09-15 lifecycle plan (not a competing Pi plan). Do not mark Pi released from these source changes.


## 2026-10-18 — Installer completion button repaired (root finish-marker path); live shutdown hang still open on the Acer

**Evidence class: SOURCE + QEMU reproduction of the denial. Physical retest pending.**

- **Owner report:** the final "I'm ready — turn off" button did nothing; pressing the laptop's physical power button produced a black, powered-on screen that never switched the machine off (forced reset needed). On the previous image the same screen showed the Syslinux banner.
- **Confirmed defect:** the button's `systemctl poweroff` ran as the installer's unprivileged `nobody` identity with no logind session; logind/polkit answered `Call to PowerOff failed: Access denied` (QEMU-reproduced against the live image). The black screen came from the physical button's root logind shutdown, not from the button.
- **Fix:** the UI now writes `/run/greia-installer/finish-request` in the RuntimeDirectory it already owns (same pattern as `release-boot-cover`); a root `greia-installer-finish.path` unit watches exactly that file and activates the one-shot `greia-installer-finish.service`, whose helper raises shutdown visibility (`SetShowStatus yes`, kernel console loglevel 8) and then performs the single `systemctl poweroff`. Composer enables the path unit; `verify-composed-root.sh` requires the pair, the helper and the enable symlink; the completion page shows a manual fallback (EN/IT/ES/FR) if the marker write fails. No new package, daemon or polkit rule.
- **Tests:** `test_installer_state` (marker + fallback), `test_rc_image_contract` (unit/compose/verifier/UI contracts), `test_system_overlay_contract` (UI writes the marker, no direct unprivileged poweroff), localization set-equality; focused runs green.
- **Rebuilt, flashed, QEMU-verified** (`6f3c809c`; image `47ab4ec6…b6a0`, live media `a1d8e713…a8c6`, payload 1,203 MiB): the finish path was active, an unprivileged `nobody` marker powered the VM off, and frame capture shows the Greia splash as the final visible frame with no terminal text (the helper lowers PID1's log level to `emerg` only for the final power-off; `systemd-shutdown` inherits it). Artifact verification PASS, USB read-back PASS, loop hygiene PASS. Evidence: `docs/reviews/acer/2026-10-18_QUIET_SHUTDOWN_QEMU_VERIFICATION/`.
- **Owner retest:** the on-screen button now powers the Acer off. The first successful shutdown showed a diagnostic transcript and then `systemd-shutdown` teardown warnings over the Greia cover. The visibility raise was removed; because PID1 forwards its log level to `systemd-shutdown`, the root finish helper now lowers the manager `LogLevel` to `emerg` just before `systemctl poweroff`. QEMU frame capture of the shutdown ends on a clean Greia splash with no terminal text; the composed-root verifier enforces both the silence and the rejection of status/printk raising. Rebuild/reflash with this refinement is in progress; physical closure for F18 remains.
- **Next exact step:** rebuild + reflash the RC with this fix, retest the on-screen button, and capture the hung shutdown stage from the `verbose` boot if it persists.

## 2026-10-18 — Quiet RC: stock Syslinux banner cleared, rebuilt, reflashed, QEMU-verified

**Evidence class: SOURCE + SIMULATOR VISUAL REVIEW (QEMU) + build/media read-back gates. Physical Acer re-acceptance pending.**

- **Owner report:** the stock `SYSLINUX 6.04 EDD … Copyright (C) 1994-2015 H. Peter Anvin et al` banner stayed visible for the whole quiet kernel/initramfs phase (and again when the machine re-booted the stick after a shutdown), making the boot look like Syslinux's. Owner decision 2026-10-18: cut it on the quiet path. The 2026-08-20 rollback had bundled the form-feed `DISPLAY` file with the fatal `console=null` change; the two are now separated.
- **Implemented (`529accef`):** `build/live-syslinux/clear.msg` (one `0x0c` byte) consumed only by the quiet template via `DISPLAY /boot/syslinux/clear.msg`; `tools/build-live-usb.sh` places the byte on quiet media only; `tools/verify-live-usb.sh` requires the directive and byte-compares the file on read-back, and refuses any `DISPLAY` on diagnostic media. `console=tty1` + `panic=0` are unchanged, a panic still prints on tty1, the diagnostic template stays fully observable, and the hidden `verbose` recovery label is untouched.
- **Gates:** focused RC/boot/diagnostics tests green; `make verify` fast lane ran 5,395 tests with the same single pre-existing `morbidi_mostriciattoli` startup-budget flake (0.278s vs 0.25s on this host; unrelated, first seen before this tranche); `validate`, `shell-check`, `footprint` PASS.
- **Rebuilt, flashed, verified** through the front door inside `unshare --mount --propagation private`: artifact PASS, USB read-back PASS, loop hygiene PASS. Image SHA-256 `b92cfd58f2967fa581d88a5c675f6926bbf979869318bb302570b5a416aff2f2`, live media id `d60ca3a7-372a-4b48-92fb-55c75077daa9`, payload 1,203 MiB (<1,300 gate). On-media `clear.msg` is the exact form-feed byte.
- **QEMU of the flashed stick** (snapshot; `-cpu n270`): black with no Syslinux text at 0.8 s and 1.5 s; Greia installer language screen at 190 s with `greia-installer.service` active, Xorg on `vt1`, no shell. Evidence: `docs/reviews/acer/2026-10-18_QUIET_BANNER_CLEAR_QEMU_VERIFICATION/`.
- **Shutdown clarification:** the installer completion page already instructs "After the computer turns off, remove the USB key, then turn the computer on again." With the key still inserted, the firmware re-boots the stick — now without the lingering Syslinux banner. A hang *during shutdown with the key removed* would be a separate installed-system issue and needs the on-device journal.
- **Next exact step:** physical Acer re-acceptance from this LaCie: graphical install, premortem §5 F1–F19, and the hidden `verbose` recovery check (F2) once.

## 2026-10-18 — RC installer rebuilt, flashed to the LaCie, QEMU-verified quiet boot

**Evidence class: SOURCE build/flash gates + SIMULATOR VISUAL REVIEW (QEMU). No physical Acer install in this turn.**

- **Root cause confirmed on the failing media:** the 2026-10-17 stick's
  `boot/syslinux/syslinux.cfg` carried `console=null`. The Debian 686 kernel
  has no `ttynull` driver, so PID 1 had no console and live-boot died before
  anything rendered; `panic=0` left the Syslinux banner frozen on screen. The
  source fix was already committed (`672ae910`: quiet = `console=tty1`;
  `ee7a40d1`: restart + exit-cover recovery).
- **Rebuilt and flashed:** `legacy-x86-i686-rc` at `ee7a40d1` with the operator
  public key, written to `/dev/sdc` (LaCie iamaKey `eca3505216d7d3`).
  `Developer installer artifact verification: PASS`,
  `Greia live USB read-only verification: PASS`. Image SHA-256
  `07240e27416b9801d8b981e43c383d79425697e545402e61d6964a18127b12ac`,
  live media id `22857a5a-9fdb-4d9c-923d-ab659eed38ff`, target payload
  1,203 MiB (below the 1,300 MiB owner gate).
- **QEMU boot of the flashed media** (snapshot mode; stick unmodified):
  Syslinux quiet entry → Greia boot splash (no kernel/systemd/login/cursor
  text) → installer language screen, `greia-installer.service` active, Xorg on
  `vt1`, no shell visible. Evidence and exact commands:
  `docs/reviews/acer/2026-10-18_RC_INSTALLER_QEMU_BOOT_VERIFICATION/`.
- **Host/build lessons:** run the front door inside
  `unshare --mount --propagation private` on this desktop host. A plain run
  leaked the chroot rootfs mount into ~18 system-service mount namespaces; loop
  teardown then failed EBUSY. The leaked namespaces were cleaned manually, but
  one kernel-pinned `/dev/loop37` remains and will clear on the next reboot.
  QEMU i386 must use `-cpu n270` (or `build/verify-image-qemu.sh`, which picks
  it): `pentium3` lacks SSE2, NumPy import fails, and the installer restart
  budget trips `start-limit-hit` behind the Greia cover — a misleading
  "stalled splash" with no image defect.
- **Open:** physical Acer install/first-boot from this stick; hidden Syslinux
  `verbose` recovery path once; the live installer root has SSH but no
  `greia-devctl`/sudoers while `INSTALLER_IMAGE_CREATION_AND_BOOT.md` §13.5
  lists a live `greia-devctl status` remote check (source/docs mismatch; the
  installed target ships it).
- **Next exact step:** install from this LaCie on the reference Acer through
  the graphical installer, then run the premortem §5 F1–F19 first-boot
  checklist.

## 2026-10-17 — Installer quiet-boot and crash-recovery source publication

**Evidence class: SOURCE.** `make verify` passed on the installer changes
over parent `672ae9101`: 5,395 fast-lane tests, 8 skipped, project/Activity
validation, shell syntax and source footprint checks. Log:
`/tmp/greia-installer-commit-verify.log` (local transient evidence).
The installer changes preserved from the working tree add `nonetworking` to
live GRUB/Syslinux/SD entries and the live boot contract. This disables
live-boot's ifupdown preconfiguration; userspace iwd/networkd ownership is
unchanged. The installer unit uses `Restart=always` because xinit can exit
successfully after its client crashes, with five starts per 300 seconds and
an `ExecStopPost` helper that attempts to repaint the existing framebuffer
cover. The composed-root verifier requires the restart policy and executable
helper; regression tests cover these contracts.

**Scope:** source publication only. Comments in the inherited changes report
QEMU observations, but this turn has not rerun QEMU, built/flashed an image,
installed a device or established physical visual acceptance. Video work is
excluded from this commit.

**Next exact step:** validate the rebuilt RC image through the existing
lifecycle/runbook route, including Wi-Fi availability, installer crash/retry
exhaustion, quiet-screen handoff and owner recovery. Earlier release and
hardware blockers remain open.

## 2026-10-17 — Release-candidate preparation (SOURCE; image not yet built)

**Evidence class: SOURCE** (`make test` 5,353 OK at d253e6c2) **+ PHYSICAL** for the Acer parity audit and mic measurements. Nothing below has run in a built image yet.

**Owner decisions:** next image is a release candidate (`build/profiles/legacy-x86-i686-rc.toml`): quiet boot/login, SSH on, one build; four languages released (en/it/es/fr, selectors offer exactly these); missing voice lines approved; image ceiling 1,300 MiB; Wi-Fi joined in the installer must carry over; first-boot profile wizard; build only on the owner's Debian Mac mini (192.168.68.113, no Docker), flash only the 8 GB LaCie — key auth + passwordless sudo to be set up by the owner (agents never type passwords).

**Landed:** parity audit (`docs/reviews/acer/2026-10-17_ACER_REPO_PARITY_AUDIT.md`), pre-mortem (`docs/reviews/2026-10-17_RC_IMAGE_PREMORTEM.md`), RC build source (3a4455d1: console policy, operator public key, bounded `greia-devctl source-deploy`, netdev, loud mic plugin build + `power_save=0`, live installer assets, persistent dev journal; runbook `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §13), mic filter config/probe fixes (20e35480; review `docs/reviews/acer/2026-10-17_ACER_MIC_NOISE_FILTER.md` — image-built plugin was missing on the Acer), Parent panel polish (8232b7c3), installer redesign + boot animation + Wi-Fi carry-over (d79b0b38, 3b391572), first-boot wizard (c822d2d8), Shell controller routing (e6f6f523), four-language release + 1,557 voice lines + device-locale fix (d253e6c2; ledger `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_RECORDING_LEDGER_2026-10-17.csv`).

**Open:** wiring of ~34 MiB recorded-but-unplayed Activity lines (in progress); 53 short new clips flagged for a human listen; the current Acer needs `tools/dev_source_deploy.py --legacy-generic-sudo` until reimaged; quiet-boot recovery paths unproven on the Acer; A/B installs don't carry Wi-Fi.

**Next exact step:** owner provides the Mac mini account (key + NOPASSWD sudo) → freeze a commit, run the pre-build gates (premortem G1–G11), build `legacy-x86-i686-rc` with `--operator-key`, verify, flash the identified LaCie, install on the Acer through the graphical installer, then run the first-boot checklist (premortem F1–F19).

## 2026-10-17 — Acer: playable games, mouse-first controls, launch hand-off, faster launches

**Evidence class: PHYSICAL (developer Acer, remote `xdotool` input — not physical-input evidence) + SOURCE.** Details and tables: `docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md` (sections from "Game verification at fce322b9" to "Final child-path sweep at 4d6e9c5e"); `make test` green at each commit (last 5,157 tests).

**Done (fce322b9 … df4454c6):**
- **Motion games playable on the Atom:** root cause was SDL per-pixel-alpha blits (~0.22 µs/px ≈ 134 ms full screen on pygame 2.1.2/SDL 2.26.5); `greia_platform.pygame_blit` RLE preparation in games, the control kit and cast poses; deadline frame pacing. Colline 4 → 24 fps, Dolphin 4.3 → 24, Volo 12 → 24, Treno 8.7 → 20, others 19–24; scenes come to rest when the child stops (no self-finishing; owner OK'd Colline's hold-to-drive).
- **Mouse-first controls (owner rule):** compact control clusters + keycap keyboard hints (`ControlLayout.cluster`, `activity_keyboard_hint`, `ui.keycap.*`, catalogue 0.8.0) in 13 Activities; rules in `docs/product/ACTIVITY_INPUT_STANDARDS.md` and ADR 0037 §4a/§4b; audit `docs/reviews/activities/2026-10-16_CONTROL_PLACEMENT_AUDIT.md` (all items closed).
- **Audio:** Activity mixer lease (closes after 30 s with no input/motion; Sound/Channel guarded — pygame 2.1.2 segfaults on a closed mixer); paced, faster synthesis with shared primitives in `greia_platform.pygame_audio` (242 cues byte-identical).
- **Launch:** Shell launch card shown before `supervisor.start` and repainted by the Activity in a hidden-then-shown first window (black 1.3–4.3 s → 0 frames); protected Home visible from the card and cancels a loading launch (ADR 0019 §8); single-pass validation + per-session validation cache for unchanged built-ins (Encyclopedia repeat launch 14 → 5.3 s).
- **Tooling/docs:** `tools/dev_source_deploy.py`; `validate_activity` enforces the runtime import allowlist (`cmath`, `numbers` added); Activity authoring skill consolidated with a one-shot checklist and a keep-current rule (owner request).

**Open:** Quattro Amici token drop 10–16 fps; first launch after a Shell restart ~8 s median (a deploy-time validation record would remove the first-launch parse); Web Activities don't use the launch cover; two observed Home taps on a Collection page logged the profile out (check intended behaviour); Treno is hidden by the test profile's parental filter (no in-play fps); the badge card waits for a tap and its description touches the card edge; `final.mp4` and `launch-video/` at the repo root are another session's untracked work.

**Next exact step:** re-film launches on df4454c6 through the Shell (0 black frames, Home visible from the card), then Quattro Amici token drop, then the deploy-time validation record in `tools/dev_source_deploy.py` / image build.

## 2026-10-16 — Acer reference device: in-place deploys, three sweeps, performance fixes

**Evidence class: PHYSICAL (developer Acer Aspire One, Atom N270 i686, 1 GB, Debian 12, Python 3.11) for the measured items; input was remote `xdotool`, never physical-input evidence.** Full method, per-Activity tables and what was not verified: `docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md` (sweep at 0148f113, re-sweep at 0f560c2e, third sweep at 15212f44, targeted re-measure at a8be76d7).

**Deploy method:** `tools/dev_source_deploy.py deploy --target <operator>@<device>` (stage from `git archive HEAD` with the compose filter, parse-gate under the device Python, swap `/opt/greia-os` root-owned 555/444, rebuild the read-only bytecode prefix, restart, health). Documented in `docs/agents/GREIA_AGENT_OPERATIONS.md` §8. The old `tools/deploy_to_acer.py` is not this procedure.

**Fixed on device (commits 2af434da … 5a30a895):** Shell crash on every launch (profile dir modes); launch path (startup imports, read-only bytecode prefix, ready timeout policy, deferred sound synthesis past READY, `SDL_FRAMEBUFFER_ACCELERATION=0`); `FrameGovernor` for all 45 Activities (low-end profile, decoration freeze, blocking idle wait); pointer save-under; idle-hint back-off 6/12/24 s; Shell memory bounds; Shell mixer idle-close; stale Collection strip on Home; Shape Garden and Pasticceria history keys over the 64-byte limit (badge never fired) plus a key-bounds test over every Activity and stderr reporting of rejected events; Foresta/Sillabe/Orchestra never settling.

**Measured (first sweep → a8be76d7):** launch via Shell crash/16.3 s → 7.4 s median; Activity idle CPU 88% → ~7–16% (painting/writing 19%); Activity RSS 145–197 → 61–124 MB; Shell RSS flat at ~145 MB over a full catalogue walk; Shell CPU while an Activity runs 2.0–2.4%; Home idle 2.4%; pointer repaint 380/435 → 53/53 ms (painting/writing); NRestarts 0, no OOM. Writing "lost spaces" was a harness artefact (withdrawn).

**Open:** Activity-side audio device keeps ~6% busy on static screens and the first input after a static screen arrives ~250 ms late (worker in progress on shared platform code); Home pointer ~230 ms median; first Home after a Shell restart ~50% CPU for 20–40 s; badge card waits for a tap (by design?) and its description touches the card's right edge; time-left pill re-check needs a configured play limit; new-Activity-folder creation under the Parent-owned profile tree not exercised on device. The device profile carries sweep history sessions, two Shape Garden creations, one badge/star.

**Next exact step:** land the Activity audio-idle/wake-latency fix, redeploy with `tools/dev_source_deploy.py`, re-measure idle CPU and static-screen input latency, then `cleanup` the device backup.

## 2026-10-16 — Test suite: fast/full lanes, os.sync fix, leak fix, duplicate pruning

**Evidence class: SOURCE** (local macOS runs, other agents' suites and builds running concurrently). No hardware.

- **Lanes** (owner `tests/suite_lanes.py`, runner `tools/run_tests.py`, pytest adapter `tests/conftest.py`): `make test`/`make verify` = fast lane; `make test-full`/`make verify-full` adds the heavy evidence suites (`tests/test_x8_qemu/*`, install RSS gate, whole-repository sweeps); `make test-slow` runs only those. Run `verify-full` before claiming install/update/release/lifecycle work complete. Naming a module explicitly always runs it.
- **Root cause of the 73-min suite:** durable boot/update writers call host-wide `os.sync()` (3.3 s per call on this Mac under load). The test process now neutralises only that call (fsync/rename/dir-sync/re-read still run); production code unchanged. The "hang after the summary" was a test blocked in that call (`grub_ab.py:949`).
- **Leak:** simulator supervision tests orphaned `greia_simulator/python_activity.py` when READY timed out; they now share `tests/simulator_supervision.py` (bounded load-tolerant waits + `addCleanup` reaper).
- **Measured:** before 5,341 tests / 73.5 min (pytest, loaded). After: fast lane 4,936 tests in 370 s (~6.6 min wall); slow lane 465 tests in 169 s, all green. Fast-lane red at the time were other sessions' uncommitted work only (`test_launcher_long_session_memory`, Corsa Bacche READY-after-present).
- Deleted 16 exact-duplicate or Markdown-prose tests (see commit `9434cc09`).

## 2026-10-16 — Badges: celebration moment, trophy shelf, flat award art, 15 badges

**Evidence class: SOURCE + DESKTOP VISUAL REVIEW** (headless 1024x600 / 800x480 renders, macOS). No Acer deploy, no audible review, no Simulator/VM/physical evidence.

**Done:** post-Activity celebration is now a character moment driven by the Shell loop's incremental frame hook (no blocking sleep): card scale-in, badge overshoot, sparkles (gold/secret: star bursts + confetti), greeter reaction via `HomeAnimator.react`, one accepted `celebrate.success` clip for the first badge of a return (non-interrupting), static while waiting (0 frames), then the badge flies into the Home star which bounces and increments (`achievement_celebration.py`, `achievement_presentation.py`). Badge Library is a trophy shelf (2×4 per page, locked tier silhouettes, secrets absent, star-pill count without denominator, tap → hop + `praise.general`/`encourage.progress` with 3 s cooldown; idle 0 frames). Home star joins the keyboard/controller focus cycle (Up from the top row or Tab after the last portal; Tab continues to the greeter). Award frames redrawn as flat SVG masters → `ui.award.<family>` renditions 160/112/64 + locked (procedural renderer kept as fallback). Policy has 15 badges (+8 from existing events; dolphin silver = 15 pearls in one journey); en/it/es/fr copy. A badge whose Activity is not loaded is now dropped with a warning instead of disabling all badges. ADR 0025 / product / badge-library / Activity-art docs describe the implemented subset.

**Tests:** `test_achievement_celebration` (new), `test_pygame_achievements`, `test_achievements`, `test_achievement_art`, `test_achievement_localization`, `test_achievement_emblem_cache`, `test_failsoft_volume_headroom`, `test_launcher_home_layout`, `test_launcher_home_animator`, `test_launcher_pacing_dirty_redraw` and Home/collection/navigation suites: PASS locally. `make visual-assets-check` PASS. Full `make verify` not run.

**Next exact step:** on the Acer, earn a badge (e.g. Shape Garden) and check the celebration frame cost/feel and the shelf hop with keyboard, pointer and controller; listen to the cheer clip level.

## 2026-10-16 — Interactive Home: greeter reactions, apple tree, sun sparkles, drifting clouds

**Evidence class: SOURCE + DESKTOP VISUAL REVIEW** (headless 1024x600 renders, macOS). No Acer deploy (another session's timed sweep was running there); Acer CPU/idle acceptance is still open.

**Done:** new `src/greia_launcher/home_animator.py` (`HomeAnimator`, `HomeGreeterVoice`, bounded effects), `home_scenery.py` (cover-mapped scene geometry, collision-checked against portals/HUD), `home_animation_presentation.py` (`HomeAnimationMixin`, after `AchievementLibraryMixin` in `GreiaChildShell`). The greeter is no longer baked into the Home cache: it greets (`pose_cheer`), rests, blinks while awake, hops + speaks on tap (first tap per boot = accepted `_intros` clip, then `praise.general`/`ready.go`; non-interrupting, 3 s cooldown, ≤4/min), sleeps after 60 s and wakes on input; it is a keyboard/controller focus stop (Left from a first-column portal; Enter/south). Tap the tree → apple falls (≤3), sun → sparkles, cloud → puff. Loop: new `_present_ambient_frame`/`_ambient_wait_seconds` hooks; dirty rects restored from the cached Home frame; ≤24 fps; zero redraws after the 20 s awake window. `home_landscape.svg` lost its three baked clouds (re-rendered with `rsvg-convert`; `make visual-assets-check` PASS); static surfaces compose `cloud.large.01`/`cloud.small.01` at rest. `shared_character_audio_path(take=)` and `shared_character_intro_path` added; `SpokenLabelPlayer.play_if_idle`.

**Measured (this Mac, dummy SDL):** busy dirty frame mean ≈1.5 ms (animator logic ≈0.1–0.2 ms), drift-only frame ≈0.1 ms, max dirty area 9.7 % of 1024x600, 0 `pygame.Surface` constructions and 0 transform calls over 200 ticks.

**Next exact step:** on the Acer, Home idle `top` over 60 s (≤2.5 % target) and during cloud drift (≤12 %), then a hands-on tap check of greeter/tree/sun/cloud and controller focus.

## 2026-10-16 — Open-source cleanup: dead tests, docs archive, public entry points

**Evidence class: SOURCE + documentation.** Focused tests only (`test_boot_progress_contract`, `test_hardware_enablement_build_contract`, `test_makefile_hygiene`, `tools/validate_project.py`: PASS on the local macOS checkout). No full `make verify` was run for this tranche: it takes about 85 minutes and two other sessions were running suites at the same time. No hardware.

**Done (owner-requested cleanup pass):**
- `078812ef`: removed dead tests (an empty stub file and doc-wording/file-exists assertions) and 15 one-off scripts (13 `tools/generate_*_audio.py`, `run_r7_final_gap_closure.py`, `probe_direct_graphics.py`). The viaggio/stelle generators remain while their Activity research notes cite them.
- `23431344`: owner decision for pre-2026-10-15 history: 53 lesson-bearing reviews, investigations and decision reports moved verbatim to `docs/archive/` (each indexed with its lesson in `docs/archive/README.md`); about 640 screenshots, capture traces, finished runbooks, session handovers and superseded plans deleted (git history keeps them). Everything still cited by a living authority stayed in place: `docs/design/**`, Encyclopedia visual evidence, asset-pack provenance reviews, ADR/skill-cited procedures and the Parent auth protocol. The policy is recorded in `docs/DOCUMENTATION.md` §7.
- `6cf17c6d`: `LICENSE` (MPL-2.0 text), `NOTICE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `requirements-dev.txt`, a new public `README.md`, the OFL beside the website font copies, `.gitignore` for local tool state, and `opencode.json` untracked.
- This entry's commit: `AGENTS.md` slimmed (dated workstream routing moved into **Active workstreams** above; standing decisions kept as rules), and `HANDOVER.md` trimmed to entries from 2026-10-15 onwards.
- `e8266cb2`: voice receipts no longer embed the author's checkout path. The engine records `request.output` repo-relative, and 2,090 committed receipts were stripped of the absolute prefix (no audio changed).
- Follow-up commit: `tests/test_public_doc_links.py` checks that relative links in the public entry documents resolve; `SETUP.md` and the release-readiness gate (secret-audit and public-files status) are updated.
- Test pruning was split by agreement: the "Greia parent mobile app" session owns timing-driven pruning of the remaining suite.

**Open (owner decisions or follow-ups):**
1. Licensing/provenance (`NOTICE.md`): about 1,350 recordings were made with macOS system voices (`say`), and their redistribution terms must be checked; the character voice references are marked redistribution-pending; the art is AI-assisted. The full CC BY 4.0 legal text and SPDX headers are not added yet.
2. Enable GitHub private vulnerability reporting (`SECURITY.md` points to it), and decide whether the public repository keeps the full git history. The history scan found no keys, tokens or Wi-Fi secrets; older revisions of the handover and the receipts still contain local `/Users/...` paths and home-LAN addresses (the current tree no longer does).
3. Done later the same day: `tests/test_activity_wave34_35_github_recovery.py` and `tests/test_p7_batch3_source_regressions.py` were merged into `test_clinica_cuccioli_refactor.py`, `test_activity_baia_delle_orche.py`, `test_activity_acquario_magico.py` and `test_activity_cucciolo_mio.py` (9 tests moved; 1 duplicate of the Cucciolo manifest test dropped). All four files PASS (20, 35, 33 and 25 tests). The local-agent queue commands were updated to match.

**Next exact step:** run a full `make verify` on a quiet machine; the owner decides items 1 and 2.

## 2026-10-16 — All 45 Activities reworked (P7 W0–W3)

**Evidence class: SOURCE + headless desktop review** (Pygame dummy drivers at 1024×600 / 800×480 / 480×320, app-loop tests, one BEFORE/AFTER sheet reviewed per Activity). **No hardware, no VM/Acer/Pi, no audible review** (no new audio exists). `[release].status` remains `draft` for every Activity. Unit suite at the end of the span: 5,300 tests with 2 failures, both fixed afterwards and not re-run; **a full `make verify` on the final head (~85 min) is still owed**.

**Shipped (SOURCE):** every Activity was reworked (or, for the three child favourites, conservatively polished) as one end-to-end commit; per-Activity table with SHAs in `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md` §6a. Same span: shared vocabulary audio bank with locale fallback (`00d303a5`, `shared_vocab_audio_path`), 62 vocabulary pictures in the shared library (`a779b10f`, catalogue 0.7.0), Encyclopedia E4 complete (`7b1f6b2c`: 36 authored storybook scenes, canonical cairo backend, `--check` reproduces 43/43 PNGs), `set_alpha(None)` transparency fix (`11a61e59`), stdlib `abc` allowed in the child runtime (`ab0fabc7`), fail-soft unrecorded sessions, Parent API Activity policy for Parent-installed Activities (`8d1588f3`), Python 3.11 f-string fixes in the Parent panel (`ce2e2c95`, `7f745bca`; the child Shell failed to import on Debian 12 before this), My Greia rework with the new platform API `set_curated_wallpaper` / `WallpaperImporter.install_curated` (`677f0cd1`), painting gallery focus/selection fix (`552011a1`).

**Key decisions:**
- **One Activity = one core experience** (levels of one loop are fine; no multi-game hubs). All merges cancelled; related Activities are grouped by the Shell theme folders (Sea folder: Aquarium, Orca Bay, Submarine, Dolphin), never by merging.
- **Child favourites (Aquarium, Orca Bay, Submarine) were polished conservatively:** same controls, colours and scale, library art, optional never-failing prompts; reviewers compare BEFORE vs AFTER for drift.
- **One feedback grammar** (`CastFeedback`: cheer / think + demonstration / shared cast completion scene), graduated hints, never answer-revealing UI, canonical cast only, platform pointer always visible.
- **Shared vocabulary audio bank:** noun clips live once under `assets/audio/vocab/v1/<locale>/<noun_id>.wav`; Activities must not copy noun clips. Shared numbers use the not-yet-implemented `shared_number_audio_path` (named by Pasticceria).
- **Child work is sacred:** paged galleries, deliberate delete with preview, no eviction, no blank saves (details in the Activity authoring skill).

**Open items:**
1. **Voice approval (owner):** every requested line is in `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_REQUESTED_2026-10-16.md` (shared numbers 0–25, colours, positions, shapes, nouns, then per Activity). Nothing generated; local Voice Studio (zero new spend) may produce candidates after approval. ES/FR stay staged (known ES/FR clip defects listed there and in P7 §8).
2. **Follow-ups** (P7 §8): kit gaps (calm completion variant, completion icon param, multi-cast completion, selection-follows-focus, graduated hint helper, shared confirm-delete/status-icon/burst/sound-bank pieces), F3 platform voice recorder, F4 runtime pointer guarantee, library migration/promotion of Activity-private art, disk pass on runtime PNG sizes (Serra ~930 KB) against the ≤800 MiB core budget, Parent-side wallpaper import, Flash/Tito avatars, Acquario/Quattro Tito clip paths via `shared_character_audio_path`.
3. **Stale docs to correct on touch:** `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md` (old Writing toolbar), ADR 0037 (Casa pilot's old banner/OK pill), `tools/generate_*_audio.py` for Casa/Luci/Bosco (old lines), "246" Encyclopedia string count elsewhere (now 260). The authoring skill was refreshed in this tranche.
4. W4 (new Activities: Tidy-Up Time, Robot Path, Float Lab) not started; Sound Blender / Story Time await voice approval.

**Next exact step:** run the full `make verify` on the final head (~85 min) and record the result here; then owner review of the voice-line list, then the library-migration/disk pass before any `[release]` status change.

## 2026-10-16 — Parent API Activity policy now covers Parent-installed Activities

**Evidence class: SOURCE only** (local macOS checkout, Python 3.12). No Linux image, VM, Acer or Pi run; the HTML Parent client was not exercised in a browser.

**Defect:** `PUT/GET /api/v1/profiles/{id}/activity-policy` validated override ids and computed `effective_activity_ids` from the built-in registry only, while the package-enabled composition's `GET /activities` also lists Parent-installed Activities. The HTML Parent client (`Greia-Parent-App-Html`, `src/views_activities.js`) PUTs an override entry for *every* listed Activity (`null` = automatic), so "Save Activity choices" returned 400 `invalid_activity_policy` as soon as one Activity had been installed through `POST /activities/install`, and installed Activities could not be shown/hidden per child. The child Shell already applied profile policy to built-ins + Parent-installed Activities (`greia_launcher/presentation.py` composes both sources and runs the same `ActivityDiscoveryService`), so Parent and Shell disagreed.

**Fix (`src/greia_parent/api_server.py`, `src/greia_parent/package_api.py`):**
- New overridable hook `ParentApiApplication.policy_activity_catalogue()` (base: built-ins) used for both override validation and `effective_activity_ids`; `PackageParentApiApplication` overrides it with built-ins + the active Parent-installed set — the same registrations `GET /activities` lists (shared `_catalogue_registrations()`); no new registry. If the installed set cannot be loaded, the policy view degrades to built-ins, mirroring the Shell's fallback.
- Clearing (`null` / `"default"`) is accepted for any well-formed id, so stale overrides left behind by Activity removal can always be dropped; a non-automatic value for an unlisted id is still rejected.
- Catalogue resolved once per update (was discovered twice), and a complete PUT body no longer projects the current policy first. Built-in validated discovery costs ~14 s per call on this Mac dev tree, so the PUT path previously took ~40 s; worth measuring on the Acer.

**Tests:** `tests/test_parent_api.py::PackageActivityPolicyCatalogueTests` (6): installed Activity in catalogue + effective set; `always_hide`/`always_show` for an installed id accepted and applied; client-shaped HTTP PUT with `null` for every listed id → 200; stale id cleared with `null`/`"default"` after uninstall (non-null still rejected); base composition clears unknown ids but rejects malformed ids; unloadable installed set degrades to built-ins. Focused run: 6/6 OK. Full gate: `make verify` test step ran 4,852 tests: 2 failures, 8 skipped, both outside the Parent API and both passing when re-run in isolation on this tree and on clean `origin/main` (`test_activity_sottomarino…test_app_loop_follows_orders_to_a_star_and_saves`: no voice cue spoken; `test_headless_greia_activity…test_real_activity_bootstrap_publishes_frames_to_owned_bridge`: exit 4). They look load-dependent: concurrent test processes were running during the suite. Treat them as flaky, not fixed. `test_parent_api.py` re-run on the final code: 34/34 OK. `make validate shell-check footprint`: exit 0.

**Docs:** `docs/design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md` §3.2 states the catalogue/clearing contract.

**Next:** exercise "Save Activity choices" from the HTML Parent client against a developer image with one Parent-installed Activity (PHYSICAL/VM evidence still owed). Developer-remote Activities (developer mode) are not listed by the Parent API and therefore remain non-overridable; clearing them still works.

## 2026-10-15 — Design & art tranche: Shell redesign, shared art library, control kit, custody fixes, P7 program

**Evidence class: SOURCE + headless desktop review only** (Pygame dummy drivers at 1024×600 / 800×480 / 480×320). No Linux image, VM, Acer, Pi or audible/physical evidence. Complements the "New primary agent" entry below; it does not repeat it. Commits `ba4e6ab6..d98806e2` on `main`; the main agent owns the full-suite run.

**Shipped (SOURCE):**
- **Art direction:** `docs/design/GREIA_SVG_AUTHORING_RULES.md` is the binding SVG recipe; Opus is the SVG model. Dead/superseded assets retired (~7.5 MiB), image installs only `assets/visual/runtime/` + catalogues. Core icons are now a complete flat family (29 SVG, catalogue 1.2.0, `tools/build_core_icons.py` SVG-only build with `--check`); 8 placeholder Activity icons redrawn; cast poses `pose_cheer`/`pose_point`/`pose_think` for all six characters.
- **Shared art library v1 (catalogue 0.6.0, 297 visuals / 518 variants):** `bg.*`, `prop.*`, `creature.*`, `icon.hud.*`, `fx.*`, cast variants (sad/angry/silly/pose_wave/pose_play). Registered in `assets/catalog/shared_visuals_v1_source.toml`; inventory in `assets/visual/README.md`. No Activity consumes it yet (W2 starts that). Installed runtime visuals are now ~8.9 MB.
- **Shell redesign:** storybook Home + profile picker (layered meadow scene, six hue-coded portals, profile cast character greets), Collection pages (large hue cards, arrows + dots), **theme folders** (a `discovery_tags` theme with ≥3 visible members gets one folder tile, one level deep; first theme: Sea = acquario, baia, sottomarino, viaggio_delfino), My Creations gallery/picker, launch wait screen. Fixed sub-collection chooser, empty-Collection Back, reversed gallery arrows.
- **Shared control kit (ADR 0037):** `greia_platform.activity_controls` (PillButton, IconButton, ToolStrip, HudChip, ProgressDots, PromptBanner + keyboard/D-pad/stick/south focus), `activity_feedback.CastFeedback`, cast completion scene. Pilots: `pasticceria_magica`, `casa_del_dieci`.
- **Fail-soft:** Shell survives and Activities launch as unrecorded sessions when history/child-data headroom is exhausted (`UnrecordedSessionHistory`; no rewards/progression mutation, `history_unavailable` answer).
- **Language/case pass over all 45 Activities** (batches 1–4: hardcoded Italian, ADR 0034 case policy, glyph boxes, profile language, protected chrome).
- **Creation custody:** Painting/Writing galleries page through every item; New refuses at cap instead of discarding; Teatrino no longer evicts silently; deliberate delete-with-preview (Keep default) in Teatrino/Voice Stories; no blank saves. `tests/test_creation_custody.py` (32 tests).
- **Blocker fixes:** Quattro Amici drop animation, Sottomarino depth control, Marble soft-lock, Nanna tap-tap, Morbidi gallery/face overlay, missing keyboard/controller paths (Specchi, Ponti), completion screens keep the platform pointer live.
- **Governance:** four Activity design audits (`docs/reviews/activities/2026-10-15_activity_design_audit/`); **P7 Activity Quality Program** (`docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md`).

**Owner decisions (P7):** one Activity = one core experience; multi-game hubs are not a standard; **all merges cancelled** (45 cards stay; Aquarium/Orca Bay/Submarine kept separate as child-testing favourites); related Activities are grouped only by Shell theme folders via `discovery_tags`; new standalone candidates Tidy-Up Time, Robot Path, Float Lab (W4); Sound Blender / Story Time deferred pending voice approval.

**Open / next:** (1) **voice approval pending** — F6 shared spoken numbers 0–20 + direction words, Sound Blender/Story Time (local Voice Studio, zero new spend; nothing recorded). (2) The theme-folder tile needs a stronger folder silhouette (reads as a card). (3) Delete-confirm dialog is small for a child target. (4) W2 Activity reworks on the library + kit (ladders first: number, literacy, creative anchors), then W3/W4; F2–F5 foundations (shared drafts gallery, voice recorder, hidden-cursor pointer, hint helper) still TODO. (5) Image group names `pip*` vs `greia*` migration unfinished. (6) Library assets unconsumed by Activities; Simulator/VM/physical visual review still owed.

## 2026-10-15 — New primary agent: source gate green locally, Shell fail-soft, Activity UI text pass

**Who/where:** Claude Opus 5.5 is now the project's primary agent, working on a local checkout (macOS, Python 3.12, Pygame 2.6.1) directly on `main`, delegating bounded work to subagents. Local `main` was fast-forwarded from `e1ab2426` to `a76d694d` before work.

**Evidence (SOURCE only):** first full local execution — baseline 4,334 tests / 185 failures / 67 errors; now **`make verify` PASS (4,372 tests OK, 8 skipped)**. All 45 Activities launch and render a first frame headlessly at 1024×600 (`tools/headless_greia_activity.py`). No Linux image, VM, Acer, Pi or audible playback evidence.

**Fixed:** test hermeticity (`tests/hermetic_volume.py`, resolved temp roots, quoted paths; pytest-only modules converted so `make verify` runs them); Shell no longer crashes at profile selection when child-data headroom is exhausted (history/achievements degrade, writes still refused); Simulator models an 8 GiB device volume instead of the host disk; Parent panel pointer-settings crash; ~17 Activities' hardcoded Italian / case-policy bypass / glyph boxes / wrong profile language; many stale tests. Details: architecture-remediation plan progress entry of 2026-10-15.

**Decisions:** (1) SVG art authoring model bake-off (Haiku/Sonnet/Opus/Fable, identical brief: Activity icon, on-model Leo pose, layered scene) → **Opus** selected for all Greia SVG authoring. (2) Icon/art family direction: flat constraint-native vector per style guide §20; the 39 glossy-3D core icons are the outlier to be redrawn. (3) Owner removed ~3 GB of ignored leftovers (TBag/runs, tmp/, Archive.zip, old review zips).

**Open / next:** Activity launch still fails closed (`PLATFORM_FAILURE`) on a full device because `start_session` is refused — next fail-soft step; remaining ~27 Activities not yet audited for language/case leaks; image group names `pip*` vs `greia*` migration unfinished; asset-library pass and Activity design/gameplay upgrades (owner mandate 2026-10-15) starting.

## 2026-10-15 — Greia shared localization: regional fallback + 13 Activity entrypoints

**Owner's active direction:** One Greia localization handler returns child-visible strings or existing approved prerecorded audio paths by stable IDs; all speech (including phonemes) uses selected-language recording, otherwise English, otherwise silence. No file anti-tamper infrastructure. All 3,723 shipping WAV/OGG/FLAC/MP3 artifacts remain approved and unmodified. The active plan is `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`, tracked by its sibling `PROGRESS.md`. Keep ES/FR staged in the selector until proper independent release/playback acceptance.

**Source changes in this session:** `src/greia_platform/localization.py`: correct BCP-47 regional-to-base-to-English ordering for both `.text()`, `.audio_path()` and eager `.speech_paths()`; `audio_path(key, variant=...)` now looks for a variant filename before neutral when using conventional asset paths. No new locale registry, format, manifest language promotion or synthesis.

**Sound managers consolidated:** Word Forest, Alphabet Leo, Measurement Workshop and Ten House now rely on `LocalizedResources.speech_paths()` for selecting localized prerecorded clips. Their pygame mixer, effects, queue/cache policy and source file names are preserved; directly constructed historical audio managers still work.

**Entry-point factory cleanup:** Word Forest, Magic Syllables, Rhyme Festival, Sound Workshop, Momo's Lights, Number Garden, Magic Mirrors, Opposites, Orca Bay, Number Forest, Momo's Faces, Four Seasons and Quattro Amici's app-builder now use `activity_resources(package_root)` / manifest-aware context instead of rebuilding hard-coded `ActivityLocaleSupport.localized(("it","en"))`. Existing `activity.toml` files still declare exactly IT/EN. Momo/Seasons window title now uses localized `activity.title`. **Actual source bug fixed:** Quattro Amici character speech previously received the raw requested locale, even when UI had fallen back to an unsupported locale's IT default; now both receive the effective resolved language. Purely synthesized sound effects and child-microphone/creation audio deliberately are *not* migrated.

**Tests authored:** `tests/test_shared_localized_audio_paths.py` now covers regional fallback, semantic-variant conventional file precedence, manifest language contexts for newly updated Activity roots. Prior suite already covers 10 real ES/FR packaged voice examples, My Time, Encyclopedia, Dolphin, Submarine, semantic aliases, EN fallback and standalone locale tests. **All tests remain UNEXECUTED** in this GitHub-only session, with no GitHub status checks/workflows on current commits. Do not claim runtime/GUI/physical PASS; no local agent was needed for source modifications. Fast verification when a runnable checkout is available: `PYTHONPATH=src:. python3 -m pytest -q tests/test_localization.py tests/test_localization_variants.py tests/test_shared_localized_audio_paths.py tests/test_launcher_spoken_labels.py tests/test_activity_foresta_parole.py tests/test_activity_sillabe_magiche.py tests/test_activity_quattro_amici.py tests/test_activity_faccine_momo.py tests/test_activity_quattro_stagioni.py`.

**Artifact integrity observation, NOT tamper-control policy:** Compared the complete Git trees at starting HEAD `2e82fb7662a6272b3bfdba60ce17fc1e1a3bcdd0` and latest checkpoint `5280ab0ce8e436fec8256506565251025faa0500`; all **3,723 prerecorded audio blob IDs** are exactly unchanged, zero added/deleted. This is only to confirm engineering did not replace any user-approved recordings. No ongoing file protection required.

**Next work:** run focused Python tests when feasible, fix their actual results, investigate remaining child-facing UI strings outside bundle lookups and test representative voice interaction/playback on a real runnable shell/Simulator. The separate missing-only recording order is `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`. Do not generate duplicate clips, enable ES/FR just from source code, or build new policy scaffolding.

## 2026-10-15 — Shared localized speech: My Time sound-file hookup and legacy title support

**Scope:** Follow-on to the 11-Activity shared-audio migration. GitHub source only; **no audio rerecording, no user-file anti-tamper system, no system language promotion**. Source authorities: `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md` and its sibling `PROGRESS.md`. Owner decisions continue: all committed WAV/OGG owner-reviewed/approved, selected language first / English fallback / silence for all speech including literacy for now.

**Real bug located and repaired:** `activity_incubator/tempo_di_greia/time_audio.py` previously called `resources.audio_cue(cue, allow_fallback=False)` for each of seven semantic narration IDs, but both EN/IT `locales/*.json` dictionaries have `"audio": {}`. The approved audio **already exists** under `locales/en/audio/` and `locales/it/audio/` with underscore filenames `presenter_welcome.wav`, `instruction_clock.wav`, etc.; source returned no cues despite existing recordings. The adapter now calls `resources.audio_path(cue, filename=f"{cue.replace('.', '_')}.wav")`, so source-selected file or English fallback is returned; existing sound cache/lazy decode/channel/first-frame sequence remains unchanged. `activity_incubator/tempo_di_greia/main.py` now composes `activity_resources(package_root)` from the manifest/profile owner, instead of building an Activity-local locale context.

**Launcher:** Standard `activity.title` lookup previously recognized the normal `activity-title.wav` title convention but not My Time's approved `activity_title.wav`. `src/greia_platform/localization.py` recognizes both variants, preferring the conventional hyphen; no duplicated files or JSON catalogue additions. `src/greia_launcher/spoken_labels.py` continues to use the shared resolver and therefore picks up the fix automatically.

**Tests committed but unexecuted:** updated `tests/test_activity_time_audio.py` (remove stale Italian fallback expectation, fixture for French→English fallback and real IT/EN 7-cue files), `tests/test_shared_localized_audio_paths.py` (real My Time title and synthetic underscore fallback), and `tests/test_launcher_spoken_labels.py` (actual My Time English/Italian title + French English fallback). All 14 narration WAV paths and both title WAVs verified present in nontruncated main Git tree. **No actual Python tests, Pygame decode/GUI/live audio or hardware tests run.** Do not claim acceptance. My Time is incubated and not released.

**Documentation:** `activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md` no longer falsely claims generation/owner listening missing; approved audio hookup is recorded and release caveat retained. Updated main localization implementation plan and `PROGRESS.md` (third slice). No local agent was used for this source work.

**Next:** execute focused `PYTHONPATH=src:. python3 -m pytest -q tests/test_localization.py tests/test_shared_localized_audio_paths.py tests/test_activity_time_audio.py tests/test_launcher_spoken_labels.py` in a runnable checkout, then repair actual test findings; subsequent targeted first-frame My Time Pygame audio playback on the small device/simulator and remaining ES/FR release review. Do not run an elaborate gate or regenerate owner-approved clips to address a source resolver issue. The independent exact local recording task remains `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`.

## 2026-10-15 — SHARED LOCALIZATION CONTINUATION: 11 MORE ACTIVITY VOICE INTEGRATIONS

**Source authority:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`; progress ledger `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PROGRESS.md`; Activity authoring contract `skills/greia-activity-authoring/SKILL.md`.

**Owner decisions still apply:** all committed voice files are personally owner-approved; do not regenerate/overwrite. No anti-tamper framework. For all clips including pronunciation, selected-locale file → English file → optional silence; voice producer remains an authoring-time tool. ES/FR remain staged and unselectable until later independent acceptance.

**New code in GitHub main this slice:**
- `src/greia_platform/localization.py`: ordinary prerecorded speech now resolves from both `assets/audio/<lang>/` and `locales/<lang>/audio/`. Added `LocalizedResources.speech_paths()` for legacy SoundManagers that eagerly cache short clips, with selected-language priority and English fallback; mixed-case names are filename aliases, not invalid semantic IDs. Added `shared_character_audio_path(project_root, speaker, cue_id, locale)` for existing v0.2 shared Flash/Leo speech with identical language policy. Greia localization returns Paths only; decoding/mixer/effects stay game-owned.
- Migrated 11 additional Activity voice owners: `bosco_numeri/bosco_audio.py`, `festa_delle_rime/rhyme_audio.py`, `officina_dei_suoni/sound_audio.py`, `luci_di_momo/firefly_audio.py`, `faccine_momo/momo_audio.py`, `mondo_contrari/contrari_audio.py`, `quattro_stagioni/tree_audio.py`, `il_giardino_dei_numeri/giardino_audio.py`, `specchi_magici/mirror_audio.py`, `baia_delle_orche/orca_audio.py`, `quattro_amici/quattro_audio.py`. Existing composition roots that create these classes now inject the shared resolver. Legacy direct constructors retain optional compatibility args. Procedural-only SFX engines were intentionally not refactored.
- Found a **real EN/IT versus ES/FR asset layout split** in Momo Faces, Opposites and Four Seasons: EN/IT voices under `locales/{it,en}/audio`; owner-approved ES/FR voices under `assets/audio/{es,fr}`. Shared `speech_paths` now finds the correct file for each without moving/re-recording anything.
- `tests/test_shared_localized_audio_paths.py` extended with actual owner-approved ES/FR filenames for ten Activities, legacy two-folder support, mixed-case legacy stems, English fallback, and shared v0.2 character recordings. Two Spanish curriculum test expectations were corrected to existing source-native filenames after checking GitHub full tree. **Tests authored but NOT executed**.
- Live Activity authoring skill updated for `speech_paths()` and `shared_character_audio_path()`; existing design/progress documents updated. No new task scaffolding.

**Source evidence:** GitHub commits/readbacks and nontruncated complete tree/path comparison. **Not yet verified:** Python unit tests, full-run Activity tests, Pygame audio decode/timing/first-frame, child GUI language context, installed Acer or four-language selector. No local agent needed for this GitHub-only source work. Current follow-up focus: run relevant existing source tests in a runnable checkout when available; fix actual errors if found; finish small remaining integration spots (e.g. incubated My Time and independent system collection sound owners only if ad hoc locale logic is confirmed) without changing approved audio bytes. No promise of a PASS until execution evidence exists. The separate local agent instruction for 35 missing clips remains `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`.

## 2026-10-15 — SHARED LOCALIZATION AND AUDIO: FIRST REAL CODE SLICE COMMITTED

**Project direction (owner):** one Greia-owned Activity/localization subsystem for semantic `text(key)` and prerecorded `audio_path(key)`; requested-locale file if present, else English recording, else silence, **including literacy/phonemes for now**. No anti-tamper/asset signing. All prior committed recording bytes personally approved; no changes to WAV/OGG or receipts. This implementation is **not** full four-language release. Main source of truth: `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`; execution progress: sibling `PROGRESS.md`.

**Implemented via GitHub main in this session:** `src/greia_platform/localization.py` extends existing `LocalizedResources`: `audio_path(key, *, variant, filename, allow_fallback)` optional file path, compatible file-aware `audio_cue(key)`, locale-directory projection from existing EN semantic mappings and legacy IT-only aliases, conventional `assets/audio/<lang>/<key>.wav|.ogg` and title file, English fallback, plus `activity_resources(package_root)` manifest/profile composition. The English text catalogue is preferred over package default on missing selected-locale strings. Profile/device language and `activity.toml` language declarations remain authoritative. Basic path safety kept; no anti-tamper logic added.

`src/greia_launcher/spoken_labels.py`: launcher Activity-title audio now uses shared `activity_resources`-style runtime resolution (with its independent catalogue language context); collection-label code unaffected. Existing code in Encyclopedia, Dolphin and Submarine already calls `LocalizedResources.audio_cue`, so source integration now reaches their owner-approved staged ES/FR files with no duplicate per-locale JSON audio map.

**Migrated source audio owners:** `activities/bottega_delle_misure/measure_audio.py`, `activities/casa_del_dieci/ten_house_audio.py`, `activities/sillabe_magiche/sillabe_audio.py`, `activities/alfabeto_leo/alfabeto_audio.py`, `activities/foresta_parole/foresta_app.py`; composition roots where needed inject existing shared resources. These still own sound caches, channels, timing, Pygame decode, nonverbal synthesized sound effects, and gameplay. `bottega_delle_misure/main.py`, `casa_del_dieci/main.py`, `alfabeto_leo/main.py` now use `activity_resources` for manifest-aware selected locale. Other legacy Activities remain for incremental migration; DO NOT mass replace Pygame sound engines.

**Testing:** `tests/test_shared_localized_audio_paths.py` was committed with actual asset-path expectations for ES/FR Encyclopedia/Dolphin/Submarine, IT-only Submarine alarm mapping, EN fallback/absent files, title path, conventional filename and Activity factory; `tests/test_localization.py` updated one legacy assertion for new owner-policy English fallback. **Tests NOT RUN:** GitHub source connector exposes no Python execution of repo and automatic Actions/status checks returned none. No local Pygame run, screenshot, physical Acer or complete project tests. Do not claim passing tests or L6 release readiness.

**Documentation:** `skills/greia-activity-authoring/SKILL.md`, `VOICE_GENERATION.md`, `LAUNCHER_SPOKEN_LABELS.md` now teach the *actually introduced* `activity_resources` + `.text` + `.audio_path` interface; stage progress and design docs updated. All commits are on `main`. No local agent needed for this work; separate precise voice recording order `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md` remains valid.

**Next coding slice:** read each remaining speech-owning Activity loader, migrate its locale and file selection (not audio synthesis/caching) to `LocalizedResources.audio_path` with occasional legacy filenames, extend focused tests, and run the existing small Python/Pygame suites when execution environment is available. Important test commands: `PYTHONPATH=src python3 -m unittest discover -s tests -p test_localization.py -v`; `PYTHONPATH=src python3 -m unittest discover -s tests -p test_shared_localized_audio_paths.py -v`; relevant Activity-specific tests; launcher spoken labels. If tests find regressions, repair source and retain all approved recordings. Do not enable ES/FR in normal selector solely on resolver changes.

## 2026-10-15 — Shared localization and voice resolution direction (OWNER DECISION, DESIGN COMMITTED)

**Owner decision:** Greia should standardize the public Activity-facing localization subsystem: each Activity requests `text(key)` or prerecorded `audio_path(key)` by stable semantic ID; a central Greia resolver handles child/profile language, existing locale files, English fallback and legacy filename aliases. Existing code already has most of this as `greia_platform.localization.LocalizedResources`, but many Activity SoundManagers use direct locale-specific file loaders. **No crypto/anti-tamper/checksum gates; user modifications are acceptable.** **English fallback for all speech, including phonemes/literacy, is approved for now.** All committed sound clips have been personally listened-to and approved by owner; keep originals intact.

**Concrete design/implementation plan added:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md` (linked from `AGENTS.md` and rollout `PLAN.md`). Ordered implementation: extend the existing runtime-neutral localization API/factory; make semantic audio resolution file-aware and English-fallback using single canonical key→legacy filename mapping plus conventional paths; migrate Encyclopedia/Dolphin/Submarine, then Word Forest/Syllables/Alphabet/others; share launcher resolver; add focused tests; **then** update the live Activity-authoring skill and its voice companion to actual code API. Preserve Activity Pygame channels/cache and educational lesson logic; no global re-record, no runtime TTS. This turn is **source evaluation + design/doc commits only**, no source runtime logic changed and no Python/Pygame/device execution. The earlier handover request for **strict native phoneme fallback** is superseded by today's owner choice. `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md` remains the separate targeted record-only order.

## 2026-10-15 — Owner reaffirms all integrated recordings approved; targeted missing-voice order created

**Product decision:** all **already committed** recordings were personally reviewed/approved by the owner. Their bytes and voice identities are final. Do **not** regenerate, reject or reapprove them. Corrected `docs/reviews/2026-10-15_FOUR_LANGUAGE_VOICE_INTEGRATION_SOURCE_REVIEW.md` to recognize this unequivocally. Remaining integrator issues are about preventing future accidental replacements, **not** a claim existing audio is invalid.

**Playback direction:** The owner wants normal semantic narration and UI cues resolved using consistent filenames: requested locale file if present, else English counterpart, else silence. Launcher *collection* spoken labels already do that; launcher *Activity title* and Activity `LocalizedResources.audio_cue()` currently require JSON audio-map entries. ES/FR Encyclopedia/Dolphin/Submarine voice files are already owner-approved but inaccessible through their empty `audio` maps. Later GitHub engineering should derive the per-locale path from the stable English cue-to-filename mapping, with bounded path validation and exceptional aliases, rather than duplicate all JSON mappings; default English audio is acceptable for general narration but can be pedagogically incorrect for language phonemes, so use strict no-cross-language fallback for educational targets. ES/FR remain not selectable until independent release validation.

**New standalone local recording job:** `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md` committed to `main`. Exact 35 candidate locations checked against main and skipped if already present: four Bottega/Casa ES/FR titles; 14 missing physical Submarine audio stems per locale (28); EN/ES/FR alarm speech for `voice.btn.alarm` source call (3, IT already exists). Script includes ready-made, proposed text, Voice Studio doctor, a self-contained Python job generator producing `targeted-gaps.csv`, serial JSONL batch commands, receipts/hash check, stop conditions and ZIP handover. New candidates require their own listening acceptance before integrating. **Never invoke `tools/integrate_reviewed_voices.py` for this missing-only job**; no overwrites or source/hardware/selector changes authorized.

**Evidence:** GitHub source/path/code and complete nontruncated repository tree, no local sound generation, Pygame GUI, connected physical device or live hearing in this turn. Continue fixing source playback policy separately from local agent's missing-only recordings.

## 2026-10-15 — Independent GitHub SOURCE REVIEW of four-language voice integration

**Pinned reviewed source:** `e1ab2426cf1623ce46b000c2e92973033cdf3f64`; previous baseline `b3edfa6760d91c15d7616440a9e08e81d1eb76b9`. **Review report (authoritative findings):** `docs/reviews/2026-10-15_FOUR_LANGUAGE_VOICE_INTEGRATION_SOURCE_REVIEW.md`. This review is **source-only**; no binaries regenerated, no Python/Pygame, OS image, replay or hearing assessment was executed by the GitHub reviewer. The owner's reported content/audio approval remains recorded and is not being retracted.

**Confirmed findings:** `tools/integrate_reviewed_voices.py` unconditionally overwrites canonical audio, sets every parseable receipt `human_review=APPROVED` without checking exact accepted ledger rows, tolerates missing receipts, does not validate destination/cue/locale/source SHA, and preserves absolute workstation `request.output` in committed receipts. Complete before/after Git-tree diff showed **609 previously existing audio blobs changed**. The **199 ES + 199 FR Encyclopedia narration assets** and **7 ES + 7 FR Dolphin narrated clips** lack corresponding ES/FR `audio` catalogue keys; both players require `LocalizedResources.audio_cue`. `bottega_delle_misure` and `casa_del_dieci` each lack ES and FR title recordings (4 total); Submarine ES/FR have 41 recordings each versus 55 EN, with 14 absent source-language cue stems per target. Submarine's dedicated EN/IT `sub_title.wav` path is valid and should not be falsely reported missing. All 45 real direct Activity manifests were accounted for. `GLA-014/015` and HANDOVER claim audio imported/owner approved, **not** completed four-language runtime mapping, speech and release acceptance.

**Next exact work:** preserve every recorded candidate/accepted asset; repair promotion as manifest-driven fail-closed and non-overwriting, attach/detach portable review receipts, fill semantic ES/FR audio maps from existing recordings, inspect missing Submarine/two titles, then targeted source/player tests. Do not re-record all audio or enable ES/FR selector to paper over the defects. Report is committed on `main`.

## 2026-10-15 — Owner audio approval; full multi-language voice integration across all 45 Activities and system surfaces

**Owner instruction:** "ok, all audio approved, commit everything please to giithub".
All generated voice candidates and receipts produced under the 2026-10-14 four-language voice recording order have been reviewed and approved by the repository owner.

**Work completed:**
- Executed `tools/integrate_reviewed_voices.py` to promote 2,331 voice files (.wav, .ogg) and 2,331 corresponding `.receipt.json` records into canonical repository asset paths:
  - All 45 built-in Activities in `activities/<app>/locales/<locale>/audio/activity-title.wav` (with receipts) for ES and FR.
  - All 16 voice-active learning Activities (`foresta_parole`, `sillabe_magiche`, `officina_dei_suoni`, `festa_delle_rime`, `alfabeto_leo`, `enciclopedia_greia`, `sottomarino_giramondo`, etc.) in `activities/<app>/assets/audio/<locale>/` for all missing cues.
  - Launcher spoken collection labels in `assets/audio/system/launcher-labels/<locale>/` including `my_creations.wav` for EN, IT, ES, FR.
  - Incubated My Time speech cues in `activity_incubator/tempo_di_greia/locales/<locale>/audio/`.
- All `.receipt.json` files marked `human_review: "APPROVED"` with owner acceptance note.
- `RECORDING_LEDGER.csv` and `app-progress.csv` updated to `ACCEPTED`.
- Unit tests verified clean: `test_*voice*.py` (29 tests), `test_staged_syllable*.py` (7 tests), `test_four_language_activity_runtime_text.py` (10 tests).
- Updated `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` for GLA-010 (PASS), GLA-014 (PASS), and GLA-015 (AUDIO INTEGRATED).
