# Target-only voice extraction v7 — 2026-10-22

## Scope and state

**SOURCE + LOCAL TESTS + SAVED-AUDIO ASR REPLAY. Not human listening acceptance.**
This corrects the mechanism identified in
[the rejection diagnosis](2026-10-22_VOICE_REJECTION_DIAGNOSIS.md).
Normal automatic VoiceEngine short requests now use separately versioned v7.
The historical v6 cutter and frozen corpus plans are unchanged. Bulk production
remains deliberately stopped. No synthesis or corpus installation was performed
for this correction.

Source owners:

- `tools/voice_carrier_search.py`: bounded PCM-first target-only extraction.
- `tools/greia_voice_core/number_comparison.py`: exact locale number comparison.
- `short_policy.py`: safe localized intro selection; existing routing thresholds.
- `short_phrases.py`: normal API orchestration and cumulative per-call retry cap.
- `target_quality.py`: shared delivered-audio comparison/signal gate. Number-aware
  comparison is version-tagged; historical v6 receipt behavior is retained.

## Mechanism and acceptance

Raw intro recognition is no longer a prerequisite. Search measures 10 ms PCM
frames for quiet runs ≥200 ms, RMS ≤−42 dBFS / peak ≤−30 dBFS, starting ≥350 ms
and leaving ≥120 ms following PCM. A suffix begins 100 ms before the run ends.
At least 80 ms energetic speech must exist before and after the cut. More than
six runs rejects before ASR; evidence materialization is bounded to six suffixes.
Each candidate is independently transcribed with the existing pinned Base
recognizer, without expected-text prompting. Exactly one must qualify.

Normal API extraction uses score **strictly >0.8**, equal canonical unit count
and identical numeric sequence. Direct Python `required` mode requires exact
canonical units. The first exact-only prototype was rejected for rollout after
saved replay exposed regressions; the final policy retains the owner's >0.8
threshold with explicit extra-word/wrong-number guards. It never selects the
highest of several qualifying suffixes.

Listed cardinal spellings/digits 0–25 are equivalent for EN/IT/FR/ES, including
listed compounds. No fuzzy aliases or arbitrary joined-word splitting. Signed or
decimal formats and leading-zero codes remain distinct. Accents default to
insensitive with a strict override. If the complete target is in the intro, the
normal policy selects a predefined alternate; direct extraction rejects the
unsafe configuration.

The actual packaged audio still passes final ASR and unchanged signal checks.
Internal/trailing silence below 1.5 s does not warn; leading silence ≥0.4 s and
other signal flags still block. No experimental gain normalization was installed.
ASR/IO failures stop for recovery, rather than being mistaken for an acoustic
rejection that spends another provider take. Failed cuts preserve existing
outputs; retained sources, receipts and search evidence remain available.

## Saved-source replay

External evidence root:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/`

The exact final extraction/comparison/quality source hashes are captured in
`v7-warn-source-replay/preregistered-scope.json`. Final replay reused identical
source audio and hash-keyed Base responses, with actual 22,050 Hz packaging and
final delivered-audio screening. Raw sources were checked against their provider
receipt hashes. This is a comparison/extraction test, not a fresh synthesis test.

| Previous first-pass state | Sources | v7 delivered PASS | Quality WARN | Extraction rejected |
|---|---:|---:|---:|---:|
| DONE | 39 | 36 | 0 | 3 |
| FAILED | 297 | 27 | 3 | 267 |

All **66 extra-word negative controls** and **17 wrong-number controls** rejected
on the same saved PCM/ASR. The controls test meaningful sensitivity; they do not
establish that every possible wrong phrase is detectable by Base. No candidate
was installed or human-approved. `v7-source-summary.json`, replay scripts,
`results.json`, final replay log and `wrong-number-controls.json` retain exact
per-recording outcomes. The earlier exact-only replay remains historical evidence
in `v7-source-replay/`; its counts must not be presented as the final policy.

### Three formerly DONE sources held by v7

- Italian `alfabeto_leo/.../ask_Z.wav`: candidate transcripts contain extra units;
  the older corpus route did not enforce final token-count agreement.
- French `baia_delle_orche/.../jump_oskar.wav`: this cut recognizes
  `Fais sautez Oscar.`, below threshold, whereas the older cut recognized
  `Fais sauter Oscar.`. This is unresolved ASR/cut sensitivity, not a listening
  judgment or proof that the installed take is bad.
- Italian `bosco_numeri/.../ask_10.wav`: candidate recognizes a wrong additional
  number (`9 ... 10`); the new numeric/count guards hold it.

Existing installed audio was not overwritten or retrospectively rejected.
These cases remain explicit regression/recovery evidence; do not claim perfect
preservation of all old machine passes or silently add a v6 fallback.

## Verification

- Final focused voice suite: **111 tests PASS** with Anaconda Python 3.12.7,
  dummy SDL, `PYTHONPATH=src:tools`; `final-focused-voice-anaconda.log`.
- This includes 15 v7 cutter tests; normal API routing/retry/service tests with
  all six actors × four languages; fatal ASR/disk faults; number/quality/prefix
  tests (104 independent locale/value vectors); and legacy cutter controls.
- Prepared voice venv broad discovery hit its missing `pygame` import in
  `test_voice_creations`; this is recorded in `final-focused-voice.log`, not
  claimed as a pass. The Anaconda run above includes that module.
- Corpus suite: **18 PASS**; priority finisher suite: **4 PASS**,
  `final-corpus-tests.log`.
- Final source-frozen `make verify PYTHON=/opt/anaconda3/bin/python3`:
  **5,711 tests, 1 failure, 3 errors, 8 skips, 247.321 s**. Full gate NOT GREEN.
  Failures are the previously observed ARM64 profile resolution, two installer
  tests requiring unavailable macOS `lsblk`, and MBR diagnostic expectation.
  Log: `make-verify-final-v7.log`. These do not establish release readiness.
- Scoped `git diff --check` passes for this change. Whole-worktree whitespace
  checking also reports unrelated pre-existing CRLF `review.csv` files; preserved.

## Next exact corpus work

1. Keep `resume-shared-short-delivery-production-03` stopped. Do not edit frozen
   plans or launch another unchanged v6 pass.
2. Add a separately versioned corpus recovery adapter using existing
   `prepare_saved_candidate` / CorpusRunner transactions. Map v7 policy/status
   metadata explicitly; existing corpus code expects v6 `warn|required` values.
   Enforce canonical counts/numbers in final quality, not just extraction.
3. Recover saved sources before synthesis. Reconcile each path, original,
   selected master, provider request/job/hash and cumulative three-take budget.
   Recover completed `20261022-142854-3615cf58` from `letterA-provider-job/`,
   never resubmit it. No approval thresholds or scope expansion.
4. Test that adapter with provider submission forbidden, passing and failing
   controls, transaction recovery and the complete saved replay. Only then
   promote qualifying saved candidates as listening-pending and consider any
   still-authorized remaining attempts. Do not label ASR evidence as listening.
