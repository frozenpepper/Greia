# Voice rejection diagnosis — 2026-10-22

## Operational correction

The parent monitored process liveness for too long without investigating the
rejection rate. A running producer was not evidence of an effective production
process. Following the owner's challenge, PID 86480 was stopped with SIGTERM
before further second-pass submissions. No shared service or other project was
stopped. The already submitted Leo IT letter_A job
`20261022-142854-3615cf58` completed and its exact output was preserved externally;
no duplicate submission, ASR acceptance or installation occurred for that job.

The first pass installed 39 files and rejected 297 of 336. The previous 292
current files remain kept, so this continuation had 331 kept/installed and 336
unresolved across its frozen 667 scope. The next pass had begun with 287 eligible
rows, but is now stopped for diagnosis. Cumulative generation budgets are not
reset. Installed output remains human-listening-pending.

## All 297 rejection records inspected

| Rejection | Count |
|---|---:|
| Raw timestamped ASR could not match final target suffix | 145 |
| Final packaged-target quality WARN | 80 |
| Expanded boundary required an exact target transcript | 27 |
| No qualifying guarded quiet run | 25 |
| Ambiguous raw target suffix alignment | 15 |
| Multiple qualifying guarded quiet runs | 5 |

The 80 final quality warnings comprise 53 with no signal flags, 17 with leading
silence only, six with low level only, and four with both. Twelve scored above
0.8 but were rejected by signal flags. Internal/trailing silence thresholds remain
1.5 seconds; their policy was not the reason for those twelve. Leading silence
still has a separate 0.4-second heuristic, measured with an absolute -50 dBFS
activity floor. A flag from that detector is not a listening judgment.

## Mechanisms and concrete defects

1. **Raw ASR is an unnecessary preliminary blocker.** v6 requires a matching
   final target suffix in the full intro-plus-target transcript before cutting.
   Bad or missing recognition there prevents independent target-only recognition.
   This contradicts the intended tolerance of corrupted disposable speech.
2. **Numeric representation is not normalized.** `Huit` versus `8`, `Trois`
   versus `3`, and `La casa del diez` versus `la casa del 10` are text
   representation differences that the old exact/score gates reject.
3. **Boundary finding is stricter than final similarity policy.** Multiple quiet
   intervals reject before independent retained-target comparison; expanded
   searches demand exact spelling even when the final requested policy permits a
   score above 0.8. Changing that needs a distinct, evidenced extraction policy,
   not relabeling a frozen v6 result or globally loosening thresholds.
4. **Some final signal warnings reject otherwise matching transcripts.** Actual
   delivered signal/level and possible retained silence need inspection; treating
   every such warning as a reason for new synthesis wastes takes.
5. **Many target-only transcripts remain different.** These observations do not
   distinguish synthesis errors from Base recognition errors. They must not be
   reported as proven bad audio or silently accepted.

## Executed saved-audio probes

No new TTS jobs were submitted for these probes. Raw source hashes were checked;
source audio, source receipts, installed runtime files and human states were not
rewritten. New cuts/results are external diagnostic artifacts only.

First fixed sample: 23 rejected files covering available locale/reason pairs and
explicit signal/numeric examples; 31 pause-based cuts. Candidate pauses were
selected from PCM before target recognition, using the existing 200 ms minimum,
-42 dBFS RMS/-30 dBFS peak limits, up to six longest qualifying intervals, and
retaining 100 ms before the end of each interval. There was no target prompt.
Whisper Base independently transcribed retained tails. Four recordings had a
unique exact target; pure gain normalization of the same 31 cuts did not improve
that count. This is evidence against attributing the failure rate to volume alone.

Full replay: **297 files, 399 candidate cuts**; 14 had no qualifying candidate.
Twelve files had one exact recognized target; 25 had one exact target after the
isolated number-equivalence prototype. Twenty had one candidate with the existing
score strictly above 0.8; this is a different predicate and not an extra 20 files.
There were no multiple-exact-target cases in this dataset.

Examples recovered by target-only recognition/number comparison include
`Thirteen!` → `13`, `Twenty-one!` → `21`, `Treize !` → `13`,
`¡Cuatro luciérnagas!` → `4 luciernagas`, and the EN/ES Ten House titles.
`Trouve Kiko` → `Trouve-Kiko` also matched after a PCM-selected cut.

The 25 number-aware-exact candidates were then packaged through the real
AudioPipeline to 22,050 Hz PCM16 and transcribed again. **21 still matched and
had no existing signal flags.** A separate peak-bounded RMS gain experiment
produced 23 machine-qualified candidates. Neither set was installed. These are
candidate recovery results, not a deployment-ready replacement algorithm or
human listening approval. The remainder is unresolved, not proven inaudible.

## Isolated comparison repair and evidence boundary

A focused prototype canonicalizes exact 0–25 number spellings/digits for EN, IT,
FR and ES, preserving other words and extra/missing tokens. Accent-insensitive
comparison defaults on, with a strict override. Hyphens separate lexical tokens;
listed compounds such as `dix-sept` become one numeric comparison unit. It does
not invent timestamps, use phonetic/fuzzy aliases, or split arbitrary joined words.
Parent inspected the prototype, rejected its first overly specific joined-word
handling, requested correction and reran the corrected eight tests: PASS,
including 104 independent locale/value vectors and negative/strict cases.
It is not integrated into the frozen production implementation.

External evidence root:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/`

- `summary.json`, `preregistered-sample.json`, `probe-results.json`
- `full-pause-replay/preregistered-sample.json`, `probe-results.json`, ASR cache
- `gain-probe-results.json`, `delivery-validation-results.json`
- probe Python sources/logs, `number-equivalence/` source/tests
- `letterA-provider-job/` exact completed-job recovery
- `rejection-comparison.json`: all 297 raw/trial-cut comparisons for Takeboard

Takeboard is served at `http://127.0.0.1:8805/`. Audio is a trial cut where one
exists; its reference is explicitly the raw composite, not a selected master.
No-pause entries are labeled UNCUT RAW. All human states remain unreviewed.
Manifest validation passed and the server returned HTTP 200; no new browser
interaction/listening acceptance is claimed.

## Resume gate

Do not restart another bulk pass with unchanged v6 policy. Next work is a
separately versioned, modular extraction/comparison correction, with positive
and negative controls and broad saved-audio replay before any new synthesis.
Keep source truth, final delivered ASR, human listening and installation distinct.
Replay prior sources first; preserve exact masters, originals and cumulative
three-take budgets. The supervision heartbeat now records this diagnostic stop
and must not autonomously restart the historical producer.
