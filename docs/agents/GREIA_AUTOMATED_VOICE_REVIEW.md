# Automated review of generated Greia speech

**Status:** current procedure for reviewing the **2026-10-19 frozen replacement corpus**; its Whisper evidence lane is historical/model-specific (last reviewed 2026-10-26).
**Entry point:** `tools/regenerate_voice_corpus.py review`.
**New VoiceEngine generation:** uses pinned multilingual **Parakeet-TDT v3** by default, not the frozen corpus's Whisper Base review path. See `SETUP.md` §7 and `tools/greia_voice_core/asr_policy.py`.
**Owner:** Voice Production Engine; no Activity-owned ASR/FFmpeg scripts.

Generation DONE means the file was produced and installed. Follow generation
with this separate automated review, then listening review. Automated reports
never change `human_review`, approve assets, regenerate speech or replace files.
An automated PASS is a screening result, not audible/product acceptance.

## Frozen corpus-review model and comparison (2026-10-22)

This historical corpus-review command uses cached multilingual Whisper Base;
it does **not** change the Parakeet v3 default used for new VoiceEngine requests.
The frozen review lane's model is
`mlx-community/whisper-base-mlx` revision
`1e3e249fb8d01c655324bd6841b1deadffd6d04c`. Screen policy v4 ignores accent/diacritic
errors by default. `--strict-accents` on review/reassess restores strict comparison;
per-request JSON/Python uses ignore_accents=false. Authored text stays unchanged.
Use a fresh report directory after changing model/comparison configuration.
Live review and explicit reassessment now share locale-aware number policy
`locale-number-tokens-v2`: spelled0–100 ↔digits in EN/IT/FR/ES, exact numeric
identity (wrong values/codes/signs/decimals remain different), no marker-based
score inflation. Reassessment passes each frozen request's locale; old ad-hoc
records without locale keep explicit `legacy-text-no-locale` comparison rather
than guessing English. No old transcript/audio or human decision is rewritten.
Reassessment reads saved transcripts and re-scores them; it does not relabel old
Tiny recognition as Base recognition or alter audio/human reviews.

## 1. Prepare

Read `SETUP.md` §7, `skills/greia-voice-production/SKILL.md`, the generation work
order and the run's frozen plan. Use the prepared Greia authoring Python, with
FFmpeg available. All model work is local; no hosted Actions/cloud service.

```bash
cd '/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia'
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
voice_run='/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-v2/run'
"$voice_python" tools/regenerate_voice_corpus.py status --work-dir "$voice_run"
```

For the completed v2 batch, expect 4,168 DONE and 741 PRESERVED, with no active
or unresolved states. Review reads the **installed WAV/OGG**, including the
actual compressed Encyclopedia rendition, rather than accepting an earlier
provider master as proof of the packaged clip. Preserved letters/syllables,
staged vocabulary and historical material are outside this replacement review.

Stop the Greia generation producer before review; review holds the same
generation lock and reads its SQLite journal in read-only mode. For ASR, inspect
the shared VoxStage queue and release the model only when that shared worker is
idle and it is appropriate to finish your session. Do not stop another project's
jobs or load competing large models. Signal-only review needs no synthesis model.

This frozen-corpus reviewer permits **installed dependencies and cached Whisper weights only**.
That restriction applies to this command, not to the Parakeet v3 verifier used by
new VoiceEngine generation.
It does not install packages or download weights. ASR model calls force offline
Hugging Face resolution. If dependencies/weights are unavailable, record the
blocker and select the correct existing authoring environment per SETUP. Do not
modify the shared VoxStage environment or install another stack as a workaround.
Installation/new downloads retain the normal setup/cost authorization rules.

## 2. Run a pilot and then the complete automated pass

Use a dedicated external report directory. A limited pilot verifies the command
and report behavior; it cannot satisfy full-corpus coverage.

```bash
"$voice_python" -u tools/regenerate_voice_corpus.py review --work-dir "$voice_run" \
  --report-dir /Volumes/Test1/Works/Greia-voice-auditions/voice-review-pilot \
  --asr auto --limit 12
```

For the full pass, omit limit/filter:

```bash
set -o pipefail
"$voice_python" -u tools/regenerate_voice_corpus.py review --work-dir "$voice_run" \
  --report-dir /Volumes/Test1/Works/Greia-voice-auditions/voice-review-full \
  --asr auto 2>&1 | tee /Volumes/Test1/Works/Greia-voice-auditions/voice-review-full.log
```

`--asr auto` probes code/cached-weight readiness once. Eligible clips get the
existing **frozen-corpus Whisper** verifier with verification REQUIRED. An unavailable verifier
is **BLOCKED**, not successful verification. The tool still runs signal checks
so ASR setup does not conceal corrupt audio. Use `--asr off` with a **different
report directory** for an intentionally technical-only pass; its speech screen
is incomplete and the command cannot return complete-review success.

**Historical environment recovery (2026-10-21; Tiny evidence):** use the explicit
`voice_python` above. The prepared Greia environment imports Whisper with
NumPy 2.5.2 and Numba 0.67.0 and resolves the cached model
`mlx-community/whisper-tiny` revision
`78c52ab98ca87f570bc57ad852e15ef7060f9f76`. No installation/download is needed.
Global `/opt/anaconda3/bin/python3` uses NumPy 2.0.2 with incompatible compiled
Numba 0.60.0 and fails with `numpy.core.multiarray failed to import`.
The original two-clip BLOCKED pilot used that wrong interpreter; it did not
establish a workstation-wide Whisper blocker. Do not downgrade global NumPy or
change the working shared VoxStage environment. The earlier generation pass
used ASR off and has not retrospectively acquired full transcript verification.
On another workstation locate its prepared environment via SETUP rather than
copying this machine-local path or assuming unqualified `python3` is correct.

Live recovery proof: the installed Alphabet `ask_A.wav` clip in EN/IT/ES/FR
ran through this command successfully with ASR on. Transcript results were
EN/IT/ES PASS and FR WARN; EN/IT also flagged long trailing silence. Overall
1 PASS, 3 WARN, zero BLOCKED; exit 2 correctly retained findings. Evidence:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-whisper-recovery/`.
This proves working transcription, not all-corpus coverage or listening approval.

## 3. What the automated checks actually measure

| Check | Result / action |
|---|---|
| Installed file/receipt matches frozen text, locale, cue, speaker, prompt, provider, selected master, byte count and output SHA | FAIL on mismatch; investigate concurrent edits or incorrect integration |
| Bounded decode to temporary mono PCM16 at 22,050 Hz | FAIL if undecodable, empty or duration outside 0.12–120 seconds |
| Signal RMS | FAIL at ≤−65 dBFS (effectively silent); WARN below −40 dBFS |
| PCM saturation | WARN when ≥0.1% samples have absolute amplitude ≥32,760 |
| Leading silence | WARN at ≥0.4 seconds (unchanged) |
| Trailing silence | WARN at ≥1.5 seconds |
| Internal pause | WARN at ≥1.5 seconds |
| Eligible ASR transcript against exact expected text | Existing canonical scorer; PASS strictly above 0.8, WARN at or below 0.8 |
| Unexpected ASR tokens matching direction vocabulary | Possible prompt leakage WARN when at least two extra words of ≥5 characters match the acting prompt |

Signal analysis uses 20ms RMS frames with activity threshold approximately
−50 dBFS. These numerical thresholds are versioned screening heuristics, not
universal speech-quality rules. Soft/bedtime speech, expressive pauses,
exclamations, lossy decoding and ASR mistakes can legitimately produce warnings.
Keep the original evidence and inspect the clip; do not trim, amplify or rerender
automatically to make counts green. Threshold/policy changes require a new
review-policy version and new reports.

ASR retains the existing engine eligibility policy: **Dani**, pedagogical kinds,
single-word/tiny utterances and scripts over 500 characters are reported
`NOT_APPLICABLE_POLICY`. This is visible excluded coverage, not pronunciation
approval. In particular, word/number/letter correctness still needs listening.
Whisper is given the expected language; it is **not an independent language
identifier**. Metadata identity does not prove audible voice identity. There
is no installed automated character-similarity, mood, pronunciation or
small-speaker intelligibility judge; these remain explicitly unassessed.

The leakage check is a suspicion flag, not proof. It can miss leakage in another
language or ASR transcription errors. Inspect the raw transcript alongside the
expected words, direction and actual recording. Repetitions, omissions and wrong
numbers can also require listening even when the aggregate score exceeds 0.8.

## 3a. Owner policy v3 and saved-evidence reassessment (updated 2026-10-22)

`greia-audio-screen-v3` retains v2 silence/score thresholds and ignores diacritics
by default. It ignores internal pauses and trailing silence below
1.5 seconds; exactly 1.5 seconds warns. ASR scores must be **strictly greater
than 0.8**. A high score plus clean applicable signal checks yields automated
PASS. Metadata/decode/silence failures, clipping, low level, leading-silence and
prompt-leakage checks still count. PASS is separate from voice preference and
human acceptance. ASR exclusions remain visible; a signal-only PASS is not
transcript verification. Shared thresholds live in `review_policy.py` and are
also the default for new VoiceEngine Whisper verification.

To change policy without running ASR again, reuse a finished report:

```bash
"$voice_python" -u tools/regenerate_voice_corpus.py reassess \
  --work-dir "$voice_run" \
  --evidence-dir /Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-full-automated-review \
  --report-dir /Volumes/Test1/Works/Greia-voice-auditions/a-fresh-policy-v2-report \
  --asr auto
```

This checks current plan/master metadata and audio/receipt fingerprints against
saved evidence, then applies the new policy to saved metrics/transcripts. It
never calls ASR or edits the source report; changed/missing evidence fails
instead of being reused. Run a fresh live review for those files. The new report
configuration identifies the evidence source and `REASSESSED_SAVED_EVIDENCE`.
This is a threshold reassessment, not fresh acoustic or ASR measurement.

Executed full v2 reassessment: **3,073 PASS / 1,094 WARN / 1 FAIL**.
ASR dispositions: 1,611 PASS / 863 WARN / 1,693 policy exclusions / 1 unrun
because the silent Bear failed first. Original measurements remain intact.
At the v2 reassessment checkpoint, `2026-10-21-listening-policy-v2/batch.json`
under the external auditions root was served at http://127.0.0.1:8796/. The original 8794 tab
is retained; its 104 unsaved owner decisions were exported and copied exactly
into the v2 batch (82 approved, 22 rejected), with a separate draft backup.
Do not reinterpret these human states as a machine-generated approval.

## 4. Reports, progress and resume

The report directory contains:

- `configuration.json`: frozen input-plan SHA, review policy, selected reference
  IDs/hashes, ASR mode, verifier/model ID and score threshold;
- `records/*.json`: per-recording metrics, flags, ASR evidence, exact request,
  input fingerprint and review time;
- `review.jsonl`: consolidated results;
- `listening_queue.csv`: **all selected recordings**, prioritized FAIL → BLOCKED
  → WARN → PASS, retaining expected text, transcript and errors;
- `summary.json`: coverage counts, ASR availability/exclusions, unassessed
  properties, and an explicit `human_acceptance_granted=false`.

Progress prints each cue and a 15-second heartbeat during long calls. The
summary is checkpointed every 25 records with `complete=false` until the command
finishes. After interruption, repeat the identical command/report directory:
unchanged completed results are reused; changed audio/receipts are rechecked.
BLOCKED/error records are retried so repairing ASR readiness can make progress.
Do not edit reports to remove warnings. Changing plan/configuration requires
a new report directory; after changing verifier implementation/cached model
weights or dependencies, use fresh reports rather than trusting old cache.
Retain Python/package/model version details with the review evidence.

Exit codes:

- **0:** full DONE-corpus coverage, all applicable ASR screening completed, no
  FAIL/WARN/BLOCKED rows. Human acceptance is still pending.
- **2:** suspect audio/metadata/transcript findings or a command error; inspect
  rows and console diagnostics.
- **3:** incomplete coverage/speech screen, disabled or unavailable ASR, or
  unresolved generation states (provided no FAIL/WARN already caused exit 2).
- **130:** interrupted; reports/cache retained.

`summary.complete=true` means the selected command finished. Separately check
`full_corpus_coverage`, `eligible_asr_complete`, `asr_counts` and all problem
counts. A 12-clip pilot or signal-only run must never be reported as a full
automated speech review. The generation journal's DONE counters remain unchanged.

## 5. Act on findings and retain listening acceptance

1. Inspect hard decode/silence/metadata failures first, then ASR mismatches,
   possible prompt leakage, clipping and pause warnings. Keep a per-path issue
   decision with evidence; don't waive an entire locale or character by count.
2. A cached-model/dependency blocker is setup work, not a reason to rerender.
   Preserve existing approved masters and scripts. Do not substitute another
   character or translate text to work around a flag.
3. Confirm suspected defects against the actual words and recording. Repairs
   use the existing authorized VoiceEngine/corpus backup and replacement flow;
   review itself never changes media, receipts, plan, acceptance or journal.
4. Review new/repacked takes again. Old review results describe the old output
   fingerprint, not later audio. Recompute reports after any packaging change.
5. Listen to every replacement before declaring human acceptance. Prioritize
   flagged clips, ASR policy exclusions, each character×language, long narration,
   numbers and words, identity/acting, wrong language, prompt speech, onset/tail
   clipping and real small-speaker playback. Do not claim the model listened if
   its audio input is unavailable.
6. Record automated coverage and unresolved rows separately from human review
   in HANDOVER and the existing voice progress ledger. Keep generation complete,
   automated screening complete, human acceptance and image release distinct.

`tools/audit_voice_receipts.py` is still useful for auditing previously stored
scores. It **does not run ASR or decode audio**. Its exit 0 for NOT_RUN/
NOT_APPLICABLE receipts is not a replacement for this procedure.

## 6. Listen and return structured decisions with shared Takeboard

The owner-authorized shared listening tool is `/Volumes/Test1/Works/takeboard`
(`takeboard` CLI, shared catalog and skill). It is generic; Greia owns only its
manifest exporter, `tools/export_voice_review_batch.py`:

```bash
python3 tools/export_voice_review_batch.py \
  --report-dir /Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-full-automated-review \
  --output /Volumes/Test1/Works/Greia-voice-auditions/a-new-listening-batch.json
takeboard check /Volumes/Test1/Works/Greia-voice-auditions/a-new-listening-batch.json
takeboard serve /Volumes/Test1/Works/Greia-voice-auditions/a-new-listening-batch.json
```

The exporter refuses incomplete traversal or an existing output. Do not overwrite
an existing listening manifest to refresh it. The prepared real batch is already
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-listening/batch.json`.
Open http://127.0.0.1:8794/ while its server is running. It includes all 4,168
recordings, canonical master players, exact words/direction, automated evidence
and initially **unreviewed** human fields. Machine FAIL/WARN never prefill rejection.

Use filters and players, then edit state, score, reviewer and notes. **Save reviews**
writes sibling `batch.reviewed.json`; **Export JSON** downloads a full snapshot.
Reopen source to resume its matching reviewed output or load exported JSON using
Open batch. The generic README explains media paths, keyboard navigation and
saving conflicts. Saves do not update Greia receipts, generation journal, source
media or shared catalogue acceptance. Consuming human decisions for promotion or
repair remains a separate explicitly scoped Greia operation; no automatic importer
is introduced by this tool.

### 2026-10-21 — Current v3 listening batch

After the separately authorized v3 corpus replacement, the complete fresh batch
is `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/takeboard/batch.json`.
It contains 1,340 recordings, all initially unreviewed, from Dani (392), Momo
(284) and Tito (664) across EN/IT/ES/FR. Takeboard validated it and serves it at
`http://127.0.0.1:8799/`; existing review ports 8794–8798 were left untouched.
The full automated report and prioritized 1,340-row listening queue are in
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/full-automated-review/`.
Results were 1,115 PASS / 225 WARN / no FAIL/BLOCKED; all receipt states remain
`human_review=PENDING`. The batch's saved `.reviewed.json`, if created by the
owner, will contain decisions only and does not automatically modify Greia.
