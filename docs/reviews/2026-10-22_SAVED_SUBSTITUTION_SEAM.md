# Disabled saved-WAV substitution seam — 2026-10-22

## Implementation boundary

The broad packaged-context strategy remains rejected under its original gates.
This tranche adds a narrower, optional collaborator, disabled by default. No
ordinary VoiceEngine/ShortPhrasePipeline/corpus caller enables it. OGG and all
historical/default number policies are unchanged. No new generation or install.
The corpus therefore remains 427 kept/installed,240 unresolved; new receipts
from earlier installs remain human-listening-pending.

Source owners:

- `context_timing.TimedTargetSlice`: complete finite ordered full-transcript
  word coverage, physical boundary slicing, explicit straddling evidence.
- `contextual_target.ContextualTargetChecker`: exact raw suffix and actual
  packaged/decoded PCM derivation; signal analysis; isolated hard veto; only
  then prefix plus actual delivery reconstruction and contextual comparison.
- `PackagedCandidateVerifier`: package/decode each bounded cutter candidate
  through the same checker. At most two ASR calls per observation.
- `voice_carrier_search.extract(candidate_verifier=...)`: explicit separately
  versioned injection; unchanged six-candidate bound and unique qualifying cut.
  Exact text alone cannot override a collaborator's warning/flags. Malformed
  verification is fatal uncertainty, not an acoustic retry.
- `TargetQualityChecker(context_checker=...)`: explicit final-delivery seam;
  exact original source and actual packaged WAV are mandatory when injected.

Metadata distinguishes isolated/contextual observations and prefix heard on
fallback, without requiring correct intro wording. A valid clock does not prove
ASR heard all speech. Human listening and exact provider/master/request identity
remain separate requirements. Current saved adapter deliberately does not accept
this extraction version; no installation integration is claimed.

## Executed source checks

25 new provider-free tests cover canonical 48kHz→22050 packaging with actual
FFmpeg, count/number vetoes in four locales, the captured Spanish false-approval
transcript, missing/extra words, bad signals, corrupted payloads, altered source
suffix, OGG refusal, incomplete/overlapping/nonfinite/straddling word times,
unique-cut selection, malformed collaborator evidence and final-check routing.
Voice discovery: **190 tests PASS** (includes existing default-v7 tests), log
`/tmp/greia-context-seam-focused-final.log`.

`make verify PYTHON=/opt/anaconda3/bin/python3` executed locally on this source
and aborted in test execution with **Abort trap:6**, log
`/tmp/greia-context-seam-make-verify-real-scalars.log`; NOT GREEN. An earlier run ended
Trace/BPT trap:5. No full-suite or hardware acceptance is claimed.

## Held-out saved-audio validation

External folder:
`2026-10-22-rejection-investigation/saved-substitution-heldout-v1/`.
Registered before observation:48 cases, excluding every raw hash in the prior82:
16 earlier isolated positives (4/locale),12 prior lexical substitution failures
(3/locale),16 actual uncut-intro payload controls,4 wrong-number controls (EN/FR).
Four-locale number equivalence/conflicts additionally have unit coverage.
All controls use saved audio; provider API access is forbidden. Current runtime
pairs, source/receipt/plan/budget identities are protected by1554 hashes.

Narrow preregistered screening predicates: at least15/16 positives retained,
at least1 held-out substitution rescue, zero bad-control approvals and zero
protected changes. These are new limited saved-recovery criteria; they do not
replace or relabel the failed broad experiment, establish90percent live yield,
select a production recipe or authorize installation.

The initial traversal stopped after16 cases/19 ASR calls at W as Whale because
contextual word timestamps were invalid. It did not accept that observation.
The diagnostic had failed to persist the full failed ASR response; this is an
evidence gap, not grounds to reroll recognition. The source is held/rejected in
this replay, with original error retained. An explicit diagnostic amendment
preserves the same cases/gates, resumes only later cases and persists subsequent
exact ASR responses before timing interpretation. Future invalid clocks abstain
for that source; other infrastructure errors still stop the traversal. No PCM,
clock acceptance rule, score threshold, master or generation budget changed.

Read actual `progress.json`, `results.json`, `asr-observations/`, registration
and first-stop evidence before concluding anything. Independent audit of any
accepted contextual observation and source/master/request/transaction tests are
still required before a saved-source installation policy can be introduced.

## Final results and a real scalar-type correction

V1 completed48cases/62offline ASR observations:15/16 prior positives preserved,
zero of20 bad controls approved, zero substitutions rescued. Its original gate
FAILED. All12 contextual substitution branches hit the same validator error.
Inspection found **a new implementation bug**: the validator required
`type(timestamp) in (int, float)`, whereas installed mlx-whisper word timing
arithmetic returns NumPy real scalars. Saved observations have numerically valid
clocks; JSON serialization turns those values into ordinary floats. This was
not evidence that all recognizer clocks were malformed, and it is not a claim
about a bug in the prior default v7 verifier.

The validator now accepts `numbers.Real`, explicitly excludes booleans and keeps
all identical finite, positive-duration, ordered, full-coverage and physical
boundary predicates. A test reproduces actual NumPy float64 timestamps. Strings,
NaN, infinity, overlaps and straddling still reject. No clock boundary or score
threshold was relaxed.

A separately registered **v2 cache-only correction** preserves original v1's
failure and first16 outcomes, then reuses exact hash/locale-pinned ASR responses.
It makes zero new ASR/provider calls and installs nothing. Three sources remain
held: the uncaptured initial W response and two multi-candidate sources whose
later suffixes were never observed after v1's early errors. Missing evidence
never counts as a pass and was not filled by rerolling recognition.

V2: **15/16 positives retained;1/12 substitution sources rescued;0/20 bad controls
approved;1554 protected hashes unchanged.** The one rescue is ES `J de Jirafa`,
isolated `Jota de girafa` score0.6367 →contextual `J de girafa` score0.8242,
with matching count/numbers and no signal flags. These are recognizer spellings,
not a listening judgment. The separately registered *narrow* screening gates pass;
original broad transfer gates and original v1 failure remain unchanged. This
small rescue rate does not establish the owner's desired live-generation yield.

Independent cache-only audit checks all16 accepted payload/source physical proofs
and the single accepted contextual reconstruction, exact original prefix/payload,
cache identity, complete word coverage/order, fixed-boundary retained words and
isolated count/number veto: **zero issues**, protected hashes unchanged. Evidence
`.../saved-substitution-heldout-v2/{registered-scope.json,results.json,progress.json,
independent-audit.json}`; exact scripts remain beside that folder. It is not yet
provider/master/request reconciliation or installation-transaction proof.

## Next exact boundary

Keep bulk runs held and defaults unchanged. Before any install, add an explicit
separately versioned **saved-only** adapter using existing prepare_saved_candidate,
CorpusRunner and RunStore. It must preserve actual isolated/context observations,
recheck final packaged delivery independently, reconcile exact raw/receipt/job/key/
master/request identities, require complete bounded candidate coverage and prove
provider-forbidden transaction recovery plus negative master/request/payload tests.
Replay qualifying existing saved candidates before any new synthesis. Reject or
hold incomplete observations; no exhausted cue gains new takes. Only then may
exact passing saved WAV candidates install as human-listening-pending. A broad
production restart still needs separate evidence of acceptable real yield.
