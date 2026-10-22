# Recorded-only saved contextual corpus recovery — 2026-10-22

## Current continuation — 2026-10-23

The explicit registered-diagnostic reconciliation path recovered and installed
two more exact saved sources through the same `prepare_saved_candidate`,
`CorpusRunner`, and `RunStore` transaction. French Tito `Trouve Oskar` used
completed job `20261022-194837-c8fd5222` under
`target-only-v7-saved-wav-context-oskar-v1`; English Leo `W as Whale` used
`20261022-194704-4881f8f0` under the existing finite
`target-only-v7-saved-wav-context-spoken-en-v1`. The actual install audit is
PASS: 2 audio/receipt pairs changed, 665 frozen pairs unchanged and 1,559 other
protected hashes unchanged. Both new receipts remain `human_review=PENDING`.
No provider or recognizer call was made and no attempt budget or threshold was
changed.

The combined frozen-667 audit is now **10 changed / 657 unchanged; 430 kept or
installed and 237 remaining** (44 letters, 193 ordinary, 0 exhausted).
Takeboard `http://127.0.0.1:8814/` contains the ten pending recordings. This is
source/install and machine-screening evidence only; owner listening is pending.
The latest files are under
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/`:
`context-diagnostic-recovery-v1/{install-audit.json,lineage-decisions.json}` and
`natural-completion-audit-v5/{audit.json,remaining.json,listening.json}`.

`diagnostic_reconciliation.py` pins a one-result registered diagnostic to the
original frozen row, remaining/priority snapshots, Activity family, exact raw
WAV and receipt, completed provider job, master/request, and attempt ledgers.
Literal matches use the unchanged comparison policy. A spoken lexical variant
requires an explicit registered equivalence policy: the Oscar/Oskar spelling
policy is deliberately selected for this saved French result, and the existing
finite English spoken policy for W. Reconciliation never changes a historical
plan or the original target text. The C-as-Cat candidate was traced to the
already-resolved `alfabeto_leo.letter_C.en` source; it is not eligible for
`foresta_parole.find_c` merely because the words match.

Focused verification recorded for this source is 212 voice tests PASS and 32
focused policy tests PASS (`/tmp/greia-diagnostic-allvoice.log`,
`/tmp/greia-diagnostic-policy-tests.log`). Local `make verify` still aborts in
the test stage (`Abort trap: 6`), so it is NOT GREEN
(`/tmp/greia-diagnostic-reconciliation-make-verify.log`). The earlier broad
context gates remain FAILED. Recorded-only yield reassessment is 7/25 (28%) for
the corpus parent/child groups, far below the desired 90%; it does not authorize
the 237-row restart.

**Next bounded investigation:** use only already-retained source audio,
packaged candidates, and pinned Base observations to classify the 25 corpus
parent/child outcomes by isolated transcript/count, contextual transcript,
word-clock coverage, and final packaged replay. Produce a case table identifying
the earliest failed predicate for each of the 18 rejected rows. Do not invoke
ASR, synthesis, models or workers, change gates, or install anything. This
read-only failure-stage attribution will distinguish an upstream short-speech
recognition issue from an extractor/context/final-replay mismatch before any new
method is proposed. Bulk production remains held.

## Current result

**One existing recording recovered and installed; no synthesis or new ASR.**
Spanish Leo `J de Jirafa`, job `20261021-171835-83d3e04d`, remains
human-listening-pending. Current frozen667 classification is **428 kept/installed,
239 unresolved**:44 unstarted letters,193 unstarted ordinary phrases,2 exhausted
(EN W as Whale and FR Trouve Oskar). Existing bulk producers remain held.

Actual one-run audit proves exactly1 audio/receipt pair changed and666 unchanged,
valid original backups,1,555 other protected hashes unchanged, exact selected
Leo v2 master/provider job/key/request/raw+receipt identities and unchanged
cumulative3-take count. The saved raw hash is
`2a55bfba98827c98e70665e6373b9a103582513a6b1371fcbdcf1fe3e71cc3d0`.
The selected reference hash is
`1d8b3fae0e8e355188d268ccfde8fb06ae2f7cc5ea3905d5a54f68064512eac1`.

Combined actual audit against the original natural-method667 snapshot proves
**8 changed and659 unchanged** pairs. New eight-recording comparison batch:
<http://127.0.0.1:8813/>. Earlier8811/8812 batches and human-review files are intact;
existing saved human decisions are carried when present. Takeboard schema/media
check passed. No browser interaction or listening acceptance is claimed.

## Source integration and boundaries

The explicit policy is `target-only-v7-saved-wav-context-v1`, selected only with
`recover_voice_candidates.py --policy ...`. Normal generation, short routing,
defaultv7 extraction, OGG and historical number/comparison policies are unchanged.
The failed broad context experiment remains failed; this is limited saved recovery.

- Existing prepare_saved_candidate packages/extracts; existing CorpusRunner and
  RunStore own installation, backup and interrupted transaction recovery.
- `context_recovery` validates pinned original source plan, current remaining
  scope, raw/receipt/completed job/master/request identity and the copied source.
  The CLI requires the existing version1 source-selection manifest. No frozen
  historical plan is rewritten. Original destination hashes still must match.
- `context_evidence.RecordedTranscriber` reads exact existing Base observations
  by audio hash/locale/pinned model/revision/settings. It has no recognition or
  provider fallback. Missing or mismatched evidence stops; no recognition reroll.
- The checker persists full isolated/context observations with identity/hash
  witnesses **before** interpretation, preserving malformed timing responses too.
- `context_evidence.validate_quality` reproduces exact source suffix, actual
  packaged/decoded WAV and prefix-plus-delivered payload; recomputes signal,
  isolated hard count/number veto and complete ordered finite word-clock rules
  from retained full observations. It verifies actual selected strategy, score,
  flags, accent policy and payload hashes without invoking ASR.
- Admission rechecks **every** bounded candidate, not just the chosen success;
  incomplete/ambiguous coverage fails. The actual final packaged target gets a
  separate recorded check. Boundary movement is refused. OGG is refused.
- Saved-only runs cannot synthesize, spend or reset attempt budgets. Exact new
  receipts preserve actual old transport direction and human PENDING state.

The default scope remains opt-in maintainer recovery, not general approval to
start bulk generation or adopt contextual verification for ordinary requests.

## Actual recovery evidence

External root:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/`.

- `context-j-recovery-v1/selection.json`: exact unresolved target/source job pins.
- `context-j-recovery-v1/preinstall-snapshot.json`: refreshed actual protected
  state and imports of2 existing exact isolated/context ASR responses from the
  held-out experiment. Source/cache hashes checked; no new observations obtained.
- `context-j-recovery-v1/run/`: frozen opt-in plan, staged candidates, full ASR
  witnesses, final checks, transaction journal, original pair backups and source.
- `context-j-recovery-v1/{stage.log,install.log,install-audit.json}`: one DONE.
- `natural-completion-audit-v4/{audit.json,remaining.json,listening.json}`: exact
  combined status/current remaining IDs. Old audits remain historical.

Final actual packaged quality is0.8242, contextual `J de girafa.`; isolated
`Jota de girafa.` is0.6367. Both spellings remain visible. This is ASR screening,
not proof of pronunciation or human approval. Actual generation parameters retain
the earlier conversational/pause instruction; they are not relabelled as the
newer period/warm production direction.

The first external preflight invocation lacked the repository root on PYTHONPATH
and failed imports before making a run or changing any file. Corrected invocation
completed; no provider/recognizer retry occurred. Preinstall source reconciliation
confirmed this held-out candidate was still in the exact240 remaining IDs.

## Executed checks

13 new provider-forbidden tests cover stage/install/resume/restore, interrupted
receipt installation, exact job/master/request negatives, missing cache and wrong
observation identity, tampered full transcript, missing fallback witness,
incomplete candidate coverage, missing final independent check, concurrent
original changes and synthesis refusal even at an existing3-take budget.

**203 voice tests PASS;22 corpus/finisher tests PASS.** Logs:
`/tmp/greia-context-adapter-allvoice-final.log`,
`/tmp/greia-context-adapter-corpus-tests.log`.
Full local `make verify` completed5804tests with the known1failure,3errors and
8skips: MBR observed-identity message expectation, build profiles and two installer
host completion tests. **NOT GREEN.** Log
`/tmp/greia-context-adapter-make-verify-final.log`; no full-suite/hardware closure
is inferred from the focused tests.

## Next exact work

Audit the239 current remaining IDs against previously retained saved candidates
and exact observations before any synthesis. Reuse the now-tested recorded-only
adapter for compatible frozen sources; preserve/hold incomplete observations and
baseline/source-plan mismatches. Other source-plan forms need an explicit tested
reconciliation extension, never changes to historical plans or request truth.
Any additional observation or comparison policy must be separately registered,
with actual controls and unchanged recorded attempt history. No new takes for
exhausted cues. Bulk restart still needs evidence of acceptable live yield; this
single saved rescue does not establish90percent generation reliability.


Initial cache discovery (no ASR/provider/install) found3 previously qualifying WAV
sources with4 possible text/locale/speaker matches among239 remaining. This is
**discovery only**, not admission: lexical-context natural-035/Trouve Oskar,
natural-038/W as Whale, and earlier-2/C as Cat. Actual W cue ID selects the
alphabet Activity; it must not be silently reused for the Forest cue merely
because the phrase matches. The C source is a canonical-rate diagnostic copy
without a provider receipt beside it; trace its original native source/receipt
and exact transform before recovery. The two lexical diagnostics need explicit
source-plan reconciliation. Evidence: `context-remaining-cached-inventory-v1.json`.
No source has been assigned new takes. A first inventory command lacked module
PYTHONPATH and failed before writing; corrected read-only discovery completed.
