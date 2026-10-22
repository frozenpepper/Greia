# Packaged-context verification safety review — 2026-10-22

## Current result

**Seven installed from the 247 remaining scope;240 remain.** The frozen 667 has 427
kept/installed and 240 unresolved:45 unstarted letters,193 unstarted ordinary lines,
2 exhausted lines (EN W as Whale and FR Trouve Oskar). All new receipts remain
human-listening-pending. Both bulk producers remain held. No new synthesis ran
in this tranche.

Two existing diagnostic takes independently passed the unchanged isolated Base
score/count/number/signal gates and were recovered using the existing v7 saved
adapter and CorpusRunner transactions:

| Recording | Actual isolated transcript | Score | Saved source |
| --- | --- | --- | --- |
| Momo EN Basket full! | Basket full. |1.0|lexical seed314159, job20261022-194807-1858b39f|
| Lilli ES ¡Elige un álbum! | Elie, un álbum! |0.8593|instruction compact-style seed314159|

The Spanish observation is retained verbatim; it is not an assertion about
pronunciation. Its actual transport instruction was `warm, calm, clear speech`,
while the planned semantic prompt was Spanish. The experimental override is
preserved and explicitly reconciled with the exact job manifest; no receipt was
rewritten to hide it. Each recovery proves 1 changed and 666 unchanged pairs, unchanged
corpus budgets and original source hashes, exact job/key/request/master/output
identity. The first Basket preflight mistakenly compared composite raw text to
target text, failed before creating a run/installing anything, and was corrected
to compare semantic and composite requests separately. Its failed log remains.

Combined actual installation audit proves 7 changed and 660 unchanged audio/receipt pairs.
Historical five/six-recording audits remain preserved. Latest external evidence:
`2026-10-22-rejection-investigation/natural-completion-audit-v3/` and
`natural-{basket,album}-recovery-v1/`. Takeboard <http://127.0.0.1:8812/> has seven
pending clips with selected masters; old batch/reviews remain intact.

`diagnostic-generation-ledger-v1.json` pins all 16 previously generated diagnostic
jobs across four cues, including their actual transport directions. Corpus
ledgers still retain 25 new-method submissions (13+12). Diagnostic calls are
separately retained in per-cue evidenced lifetime totals; they were not erased
or converted into a fresh corpus allowance. Neither recovery submits a job.

## Completed82-source packaged-context experiment

The immutable replay covered41 recent sources,24 earlier sources and17 wrong-number
sources in WAV and OGG. It made 708 offline ASR observations, with provider access
forbidden. The exact decoded delivered payload was concatenated after the source
prefix ending at the fixed cut. All words after that frame boundary were scored;
straddling words rejected. No expected-text prompt or intro wording agreement.

Independent cache-only structural audit checked 418 recorded observations: no
hash/PCM/timestamp-coverage/word-order issues. All protected raw sources, receipts,
plans, budgets and667installed pairs remained unchanged during the experiment.

**The original experiment FAILED.** One of 204 negative control observations was
incorrectly accepted. An OGG payload deliberately containing the complete uncut
intro was accepted by the contextual branch because ASR collapsed repeated intro
speech. Isolated ASR correctly exposed the extra words. Structural correctness
of timestamps does not prove the transcript includes every actual spoken word.
The original format results remain frozen:

| Original experiment | WAV | OGG |
| --- | --- | --- |
| Earlier qualifying isolated positives preserved |28/28|25/28|
| Prior raw-context matches transferred |10/10|9/10|
| Negative false accepts |0/102|1/102|

OGG also missed the registered 90 percent positive-preservation minimum.
No contextual verifier was integrated or used for installation.

## Conservative replay: context cannot overrule hard isolated evidence

The separately registered **post-diagnosis** v2 replay adds a veto: contextual
fallback requires nonempty isolated text, matching isolated canonical word count
and numeric sequence, and a clean structural audit. Existing isolated passes
remain passes; accepted measured boundaries must still be unique. No new ASR,
recognizer reroll, synthesis, signal/score threshold change or installation.

| Conservative v2 | WAV | OGG |
| --- | --- | --- |
| Earlier positives preserved |28/28|25/28|
| Prior raw-context matches transferred |7/10|6/10|
| Negative false accepts |0/102|0/102|
| Recent41sources with one qualifying boundary |12|12|

**Both formats still fail the original transfer criterion of 80 percent.** Do not
relabel this as a successful original experiment or silently drop OGG. The three
WAV transfers vetoed had explicit isolated count/number conflicts: Toute vos
gares, Eli qué un álbum, and Basket4. Preserving those hard conflicts is deliberate.
The result is promising only as a narrower substitution-rescue mechanism.
The 12 qualifying recent sources cover the 9 already attempted cue identities, but
this post-hoc coverage is not live yield or owner listening acceptance.

External `count-number-veto-v2-registration.json` and `...-results.json` retain
the fixed predicates. `replay-context-hard-invariant-veto.py` reproduces those
results exactly from hash-pinned observations without ASR. Originalv1failure
remains unchanged. Both contextual versions remain unselected.

## Next bounded work

Develop an **optional, initially disabled, WAV-only saved-substitution verifier**
with the hard isolated count/number veto; do not deploy it as a general solution
or resume bulk based on the failed transfer experiment. Keep OGG on the existing
isolated verifier. A narrower recovery contract must explicitly acknowledge the
old failed gates and be validated on held-out saved sources before installation.

Use existing source owners rather than an independent pipeline:

1. A focused context-check collaborator behind TargetQualityChecker packages the
   fixed original suffix, reconstructs original prefix plus actual decoded target,
   verifies PCM/cache provenance, and requires complete finite ordered word-time
   coverage. Preserve isolated/context observations and truthful strategy metadata.
2. The cutter needs an explicit injected candidate-verification seam because v7
   currently rejects before final target screening. Preserve its bounded PCM
   candidates and ambiguity rejection. Defaultv7 stays unchanged; new extraction
   and saved-adapter policy metadata must be explicit. Do not describe contextual
   recognition as raw-intro ASR not run; intro correctness is simply not required.
3. Tests must reject the captured uncut-intro false approval, extra words, wrong
   numbers, mismatched counts, malformed/partial timestamps, altered payloads,
   ambiguous cuts and wrong source/master/request. Provider submission forbidden.
   Validate held-out real saved WAV positives/negatives in addition to the 82 sources;
   do not choose easier examples or lower score/count/signal thresholds.
4. Only a proved limited saved-recovery policy may install qualifying exact saved
   sources through normal transactions. Preserve all call histories and PENDING
   reviews. New bulk synthesis still needs evidence of acceptable real yield.

This turn changed no engine source/defaults. Existing full verification remains
NOTGREEN as recorded in the preceding report; no new implementation test claim.


## Subsequent bounded implementation

`2026-10-22_SAVED_SUBSTITUTION_SEAM.md` records the disabled optional source seam,
held-out48-case test, actual NumPy timestamp type correction and cache-only v2
limited result. It supersedes only the next-work description above. Original
failed broad gates remain failed; no new synthesis/install or production adoption.
