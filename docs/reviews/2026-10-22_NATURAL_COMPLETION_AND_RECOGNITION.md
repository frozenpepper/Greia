# Natural voice completion and recognition diagnosis — 2026-10-22

## Result for the owner

**Not complete.** Five of the247 previously unresolved recordings are now
installed, pending listening. The total frozen667 has425 kept/installed and242
unresolved. Both production stages stopped on poor yield; neither may be blindly
restarted. The results do not meet the owner's tolerance of roughly one failed
attempt in ten.

Actual installed/current-candidate hash audit:

| Recording | How it passed |
| --- | --- |
| Tito FR `Trouve la petite pieuvre` | Natural take2 |
| Momo IT `Dove ti fa male?` | Natural take2 |
| Leo IT `Sei!` | Ordinary-speech take3 |
| Tito EN `Find Oskar` | Saved take2, explicit Oscar/Oskar spelling comparison |
| Lilli EN `Find two the same!` | Saved take2, explicit two/to acoustic comparison |

Exactly5of667 audio/receipt pairs changed and662remain unchanged against the
natural run's snapshot. Recoveries each independently proved1changed666unchanged
at their own installation boundary. Original sources, receipts, masters and
reserved provider-call budgets remain retained. The25actual corpus submissions
are13in the first natural stage and12in the speech stage. No new allowance was
given to an attempted cue; the speech stage moved only zero-use allowances.
Diagnostics use separate declared budgets and were not installed.

Remaining categories:45unstarted letter-name cues,193unstarted ordinary phrases,
4exhausted cues (EN W as Whale, ES Elige un álbum, FR Trouve Oskar, EN Basket full).
Exact IDs and actual installation audit are external:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/natural-completion-audit-v1/`.
Takeboard: <http://127.0.0.1:8811/>. Human acceptance is not inferred.

## Experiments and their limits

| Experiment | Actual result | Disposition |
| --- | --- | --- |
| Compact instructions vs no instruction |1/8final passes | No selected prompt change |
| Fixed three-copy recognition of saved cuts |0of4baseline qualifiers retained;0new passes across39cuts | Rejected; wrong-number controls not pursued after positive gate failure |
| Rich lexical context, explicit spoken W, two seeds on four failures |1/8final passes; preregistered7/8gate failed | No bulk adoption |
| Full-source contextual Base recognition at existing fixed PCM cuts |10unique target matches among41saved sources; all41uncut intro controls rejected | Diagnostic only; not installed or selected |

The last diagnostic requires all timestamped words after the already measured
cut and rejects a word crossing that boundary. It neither requires correct intro
wording nor supplies an expected-text prompt. It includes an explicitly declared
shadow Oscar/Oskar spelling comparison and exact English acoustic variants.
It is not the previous experiment that merely repeats a clip.

Examples of recognition instability on the same retained speech:

| Isolated recognition | Recognition with surrounding speech |
| --- | --- |
| W as well | double you as whale |
| Basket4 | basket full |
| Toute oscar | Trouve Oscar |
| Eligione al boom | Elige un álbum |

These are ASR observations, not proof of pronunciation or listening acceptance.
Context can bias recognition. Forty-one uncut-intro controls do not establish
wrong-number/extra-word sensitivity or validate the final packaged delivery.
No claim of90percent reliability follows from10of41observations.

## Implemented source boundaries

- Default/current and historical number policies remain unchanged. Separately
  versioned saved-recovery opt-ins add English Oskar/Oscar and exact English
  one/won,two/to/too,four/for,eight/ate at corresponding positions, plus W as
  double-u/double-you. Different numbers and extra words still fail.
- The v7 cutter accepts an explicit comparison policy; target checking and saved
  receipt validation use that exact declared policy. Historical receipts retain
  their semantics and original expected text/transcript.
- `natural_continuation.py` hands off only READY rows with zero reservations,
  unchanged originals/registry and a hash-pinned one-child handoff. Attempted
  rows cannot silently acquire another budget.
- Existing CorpusRunner/RunStore own installation, backups and recovery.

Focused165voice tests and53related corpus tests PASS. Latest full `make verify`
executed and aborted with trap6; it is NOTGREEN. A preceding full run executed
5765tests with1failure3errors8skips in existing MBR/build-profile/installer-host
areas. Logs `/tmp/greia-natural-repair-final-{focused,corpus,make-verify}.log`.

## Next exact work — saved audio first

1. Reconstruct recognition context from the original prefix up to the fixed cut
   followed by the **actual decoded packaged target**, using the existing
   AudioPipeline. Retain exact hashes, prefix frame count and source/job/request/
   master provenance. No change to delivered audio or measured cut.
2. Transcribe this reconstructed context without expected text. Compare all
   words after the exact prefix duration; reject boundary-straddling words,
   missing words, wrong numbers, extra words and ambiguous matching cuts. Do not
   demand correct intro words. Keep isolated recognition visible separately.
3. Before adoption, replay all41saved sources, earlier known-good sources and
   actual extra-word/wrong-number/name/prefix-leak negatives. Check WAV and OGG
   delivery. Provider submission must be forbidden. Preserve existing isolated
   passes when adding a separately versioned corroborating strategy, and reject
   conflicting/ambiguous boundary evidence.
4. Only a proved final-delivery strategy may enter a separately versioned engine
   seam and saved-source recovery adapter. Recover qualifying existing sources
   before any new synthesis. Keep budgets and historical plans untouched.
5. Resume unused allowances only after the method has actual evidence; do not
   reset exhausted budgets or treat a small successful sample as population proof.

External artifacts are immutable evidence; progress and any correction notes must
accurately distinguish current-source implementation, diagnostic observations,
installation and human listening. No hosted/paid work or shared-worker restart.


## Registered final-delivery replay — running

The saved-only experiment `final-delivery-context-v1` is running82sources
(41recent,24earlier saved,17wrong-number), both WAV and OGG. It packages and
independently decodes each suffix, then verifies exact decoded payload PCM
concatenation after the original prefix. It keeps every measured candidate;
unique acceptance is required, including the union of isolated and contextual
observations. Signal/score/count/numeric gates remain unchanged.

Controls include actual complete-intro payloads, actual source-prefix speech
appended after targets, wrong numbers and wrong names. Protected snapshots cover
all667current audio/receipt pairs, raw sources/receipts and both run plans and
budgets. The script forbids provider API access and caps offline ASR observations
at1200; all exact observations use the existing cache. No synthesis/installation.
Acceptance was registered before replay:zero negative false accepts,>=90percent
prior-positive preservation and>=80percent prior-context transfer, protected
hashes unchanged. These are diagnostic predicates and do not establish live yield.

`audit-final-delivery-context.py` is a separate cache-only structural auditor:
packaged/decoded/context hashes; exact original prefix and decoded-payload PCM;
exact cache identity; complete text-to-word timestamp coverage; finite bounded
ordered word timings; all after-boundary words and straddling words must match
cached evidence. It never calls ASR. Any structural issue disqualifies contextual
evidence. Run only on COMPLETE output, inspect actual artifacts, and recompute
conservative results before any integration. No engine strategy is selected yet.
