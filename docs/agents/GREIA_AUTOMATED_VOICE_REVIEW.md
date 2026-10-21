# Automated review of generated Greia speech

**Status:** current post-generation procedure, 2026-10-21.
**Entry point:** `tools/regenerate_voice_corpus.py review`.
**Owner:** Voice Production Engine; no Activity-owned ASR/FFmpeg scripts.

Generation DONE means the file was produced and installed. Follow generation
with this separate automated review, then listening review. Automated reports
never change `human_review`, approve assets, regenerate speech or replace files.
An automated PASS is a screening result, not audible/product acceptance.

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

The reviewer permits **installed dependencies and cached Whisper weights only**.
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
existing Whisper verifier with verification REQUIRED. An unavailable verifier
is **BLOCKED**, not successful verification. The tool still runs signal checks
so ASR setup does not conceal corrupt audio. Use `--asr off` with a **different
report directory** for an intentionally technical-only pass; its speech screen
is incomplete and the command cannot return complete-review success.

**Verified environment correction (2026-10-21):** use the explicit
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
| Leading/trailing silence | WARN at ≥0.4 seconds each |
| Internal pause | WARN at ≥0.8 seconds |
| Eligible ASR transcript against exact expected text | Existing canonical scorer, threshold 0.72; WARN below threshold |
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
numbers can also require listening even when the aggregate score exceeds 0.72.

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
