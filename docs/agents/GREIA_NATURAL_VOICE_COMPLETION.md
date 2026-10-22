# Greia remaining recordings — natural-method completion

## Current authority and state

The owner authorized completing the remaining recordings with the natural method
on2026-10-22, after reviewing two difficult-target experiments. This is a new
bounded method allowance, not permission to restart the old high-rejection
`final-take-v7-02` run. Original667 scope has247 unresolved paths at this new
plan boundary;420 previously kept/installed paths are outside the replacement.

Work folder:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/natural-context-v1`

**Canary stopped for method review:**2 installed,3 exhausted,242 not started,
13 actual new-method calls. No more production synthesis is running. This is
an early failure of the real-corpus method, not completion of the247 recordings.
The driver stopped itself when rejected attempts exceeded60percent after at
least12 calls. Do NOT bypass `METHOD_REVIEW_REQUIRED` or silently change guards.

First successes: Tito FR `Trouve la petite pieuvre` and Momo IT `Dove ti fa male`,
both on their second take. New failures: EN Leo `W as Whale`, ES Lilli `¡Elige un
álbum!`, EN Tito `Find Oskar`, each after three takes. For the last case, two
retained targets are transcribed `Find Oscar`; investigate that exact spelling
variant rather than regenerate them. Actual spoken content remains a listening
question, not something an ASR transcript alone proves.

A separately registered8-job diagnostic checks compact style words versus no
instruction prefix on the failed W/album examples, with fixed seeds42/314159.
Inspect `2026-10-22-rejection-investigation/instruction-conditioning-v1/` and
sibling log before any diagnostic submission; never duplicate it. It changes
actual provider direction explicitly in receipts, not masters, targets or
cut/signal thresholds. No diagnostic is installed automatically.

## Implementation ownership

- `natural_carrier.py`: localized topical lead-in selection and concise native
  delivery. Number/letter/search/friend/general contexts; period and paragraph;
  no imperative pause instruction. Explicit delivery override remains possible.
- `ShortPhrasePipeline`: optional policy and pre-submission reservation callback;
  same serialized provider, v7 quiet-run target extraction and final Base checks.
- `automatic_generation.py`: versioned natural corpus adapter, up to3 tries,
  frozen recipe/semantic/master/quality/reservation validation.
- `method_budget.py`: authoritative per-call reservations and cumulative mirror.
- `natural_plan.py`: exact frozen remaining selection, prior DONE hash proof,
  originals/masters snapshot and deterministic representative canary ordering.
- `natural_run.py`: one warm engine, one cue per CorpusRunner call, progress after
  every cue and automatic poor-yield stops. Existing RunStore owns backups and
  multi-file installation/recovery; no parallel installation system.
- `record_natural_voice_priority.py`: thin prepare/run CLI.

The natural recipe is explicitly selected by this run. Ordinary requests retain
the previously documented default recipe until a wider default adoption is
accepted. Never claim that every API now uses natural prompts.

## Budgets and recovery

Each new-method cue gets at most3 actual provider calls. Historical attempts
remain in the ledger and in `carrier-attempt-counts.json`; they are never reset.
`method-reservations.json` is authoritative and written before each call. Its
mirror contains historical+new totals. A single call which succeeds does not
consume three reservations. Unknown submission/ASR/IO outcome stops recovery and
never allocates another take. A ledger/mirror crash can repair only its known
one-write window. A repeated lifecycle with reserved calls is rejected.

Preserve original plans, provider audio/receipts and human judgments. Passing
replacements are human-listening-pending. The stopped old Cinq provider job
`20261022-180337-f06676db` must never be resubmitted.

The new driver stops on3consecutive exhausted cues, >2exhausted among the last10,
<80percent passing in the first12, or >60percent rejected actual attempts once
12attempts exist. These are execution guards; per-file score>0.8, canonical
word count/numeric identity, Base/model revision and signal checks stay unchanged.

## Exact operation

Use prepared voice Python from SETUP§7, installed FFmpeg and shared VoxStage.
Do not restart/unload/cancel shared service or other projects. Both timeout
settings7200 handle normal shared-queue waits.

```bash
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
GREIA_VOXSTAGE_TIMEOUT=7200 GREIA_VOXSTAGE_HTTP_TIMEOUT=7200 \
  "$voice_python" tools/record_natural_voice_priority.py run --work-dir <external-new-plan>
```

The current v1 work folder is held for review and rejects this command. A method
correction needs evidence and an explicitly versioned processing/continuation
plan; do not mutate the frozen plan or reset attempts. Prepare requires
`--priority-file`, `--remaining-file`, `--prior-run`, `--history-root`,
`--cache-root` and an absent external `--work-dir`. Current snapshots own exact
source paths/hashes. Do not replace remaining IDs with a new broad inventory.

Supervision reads producer.pid AND actual processes, production.log, progress.json,
state.sqlite3 and automatic-evidence. READY rows are unstarted, PRESERVED means
original retained after known quality exhaustion, NEEDS_RECOVERY/FAILED indicate
an actionable stop. A live queued shared job is not a hang. On completion audit
all667 actual audio/receipt pairs against the preinstall snapshot and DONE,
backups, actual delivered quality and provider/master/job/key/raw hashes. Output
installed/exhausted/blocked/remaining lists and a separate Takeboard manifest.
Do not call the task finished while recordings remain unresolved.

## Source evidence

10 new natural-method tests PASS; full focused158 and related corpus53 PASS.
`make verify` executed but aborts in macOS/pygame high-resolution font/control
rendering, stack at hires_surface.py:558; NOT GREEN, no runtime/hardware closure.
Logs `/tmp/greia-natural-{method-tests,focused,corpus-tests,make-verify}.log`.
