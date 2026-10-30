# Greia remaining recordings — natural-method completion

## Current owner-authorized run — exact 237-row Parakeet replacement (2026-10-23)

The owner explicitly authorized a new, separately versioned replacement allowance
for every row in the latest frozen `natural-completion-audit-v5/remaining.json`:
237 total (44 letter cues, 193 ordinary; EN15/ES45/FR114/IT63). Do not apply
the earlier 7/25 saved-screen yield stop to this new order, and do not resume or
rewrite any held v1 plan. The completed external run is
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-natural-parakeet-full-237-v1/`;
the exact plan SHA, PID, progress/log and latest state are in `HANDOVER.md`.

The plan pins local Parakeet-TDT v3 revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`, comparison
`locale-number-tokens-v3-chck-orthographic`, the selected masters and all 667
pre-install audio/receipt pairs. It uses the existing natural-carrier phrase and
delivery recipe, normal VoiceEngine/CorpusRunner transactions, and at most three
new actual provider calls for each exact remaining row. Old attempt totals stay
in history and do not consume or reset the new authorization. Known per-cue
quality failures may use the remaining new attempts; provider, recognizer or
installation uncertainty stops for exact recovery without resubmitting. Passing
replacements retain external originals/backups and `human_review=PENDING`.
The earlier ten-cue Parakeet diagnostic is hash-pinned but not counted as corpus
output. The run finished `BOUNDED_COMPLETE`: 147 installed/Parakeet-PASS,
90 originals preserved after quality exhaustion, 0 remaining or blocked, and
498 new calls (86/41/110 cues used 1/2/3 calls). The terminal audit verifies
all 667 snapshot pairs: 147 replacement transactions with exact backups, 90
unchanged originals, and 430 unchanged out-of-scope pairs. Provider job IDs,
idempotency keys, selected-master identities and receipt hashes are recorded in
the external audit.

The unreviewed Takeboard batch is
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-natural-parakeet-full-237-v1/takeboard-listening.json`,
served at `http://127.0.0.1:8818/`. It includes 498 raw carriers, 583
materialized target cuts, 13 retained failed package candidates and 147
installed finals. Twenty search geometries were explicitly discarded before
audio materialization by voiced/energy preconditions; no candidate file is
unexplained. Human listening remains required for acceptance.

Producer implementation commits are `772df9cb7` and `14a93e74c`. The complete
voice-pattern suite passed 231/231 on the final producer source before launch.
The full repository gate was executed after the run; see
`2026-10-23_FULL_PARAKET_VOICE_CORPUS_REPLACEMENT.md` (archived; see git history) for the exact
result and remaining limitations.

## Historical ten-cue diagnostic — Parakeet v3 (2026-10-23)

The engine verification backend for new requests is now cached local multilingual
Parakeet-TDT v3 (`mlx-community/parakeet-tdt-0.6b-v3`, revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`). A separately registered ten-cue
end-to-end diagnostic through the public VoiceEngine produced 6 automated
packaged-audio PASS results and 4 quality rejections after 21 actual jobs. Each
request stopped at first pass or three tries. The natural-carrier policy was
explicitly injected for this diagnostic only; production prompt defaults,
thresholds and corpus budgets are unchanged. Passing outputs remain
`human_review=PENDING`. Takeboard has all 21 raw attempts, 24 cuts and 6 passed
packages as an unreviewed batch at `http://127.0.0.1:8816/`.

Evidence and per-case results: `2026-10-23_PARAKEET_VOICE_PIPELINE.md` (archived; see git history)
and external directory
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/parakeet-v3-pipeline-10-v1/`.
At this diagnostic's time, the prior saved/context natural-corpus pipeline was held (combined frozen-667
audit: 10 changed/657 unchanged, 430 kept/installed, 237 remaining). The ten-cue
result did not itself authorize bulk restart. The later explicit 237-row owner
order above is separate authority; its outputs still need human listening.

## Historical corpus state before the authorized replacement (2026-10-23)

Read `2026-10-22_SAVED_CONTEXT_CORPUS_ADAPTER.md` (archived; see git history) for the full
saved-source recovery evidence. The newer engine diagnostic is above; it is a
separate ten-cue API check and does not continue the corpus run. The diagnostic
reconciliation adapter recovered two registered saved sources: French Tito
`Trouve Oskar` (`20261022-194837-c8fd5222`) and English Leo `W as Whale`
(`20261022-194704-4881f8f0`). Their explicit selected comparison policies,
full provenance checks, and normal recoverable transactions are recorded in
`context-diagnostic-recovery-v1/install-audit.json` (PASS, 2 changed pairs,
665 unchanged pairs, 1,559 other protected hashes unchanged). No new provider
or recognizer calls and no budget/threshold changes; both takes remain
`human_review=PENDING`.

At that audit boundary the frozen-667 scope had 10 changed/657 unchanged, 430 kept or
installed, and 237 remaining: 44 letters, 193 ordinary, 0 exhausted. Takeboard
is `http://127.0.0.1:8814/` with ten pending clips. The C-as-Cat source belongs
to already-resolved `alfabeto_leo.letter_C.en`; never reuse it for
`foresta_parole.find_c` by text alone. The previous bulk producers were held. The
current saved-evidence yield screen is 7/25 for corpus parent/child cases
(28%), not sufficient to restart bulk work.

Current source verification: 212 voice tests and 32 focused policy tests PASS.
Full local `make verify` aborts at the test stage (`Abort trap: 6`), NOT GREEN.
The next action for current voice continuation is owner listening to the new
Takeboard batch described above. Do not continue corpus generation from either
the diagnostic pass count or the older saved-evidence yield screen.

## Prior state — 2026-10-22

Read `2026-10-22_SAVED_CONTEXT_CORPUS_ADAPTER.md` (archived; see git history) first for latest
method results and exact next work. Both bulk producers remain held; no new
synthesis. Actual audit8changed659unchanged of667,428kept/installed,239remaining:
44unstartedletters,193unstartedordinary,2exhausted(EN W as Whale,FR Trouve Oskar).
Takeboard8813has eight pending clips; historical8811/8812 batches remain unchanged.
Latest exact IDs/audit: `2026-10-22-rejection-investigation/natural-completion-audit-v4/`.

The explicit recorded-only saved adapter is implemented and used once: Spanish
Leo JdeJirafa qualified at contextual .8242, isolated .6367. Exactly1pair changed,
666unchanged, originals backed up, selected job/master/request/source proven,
3take budget unchanged and2old ASR observations imported by exact identity.
No new synthesis/recognition; humanPENDING.203voice +22corpus/finisher testsPASS.
Fullverify5804tests:known1failure3errors8skips, NOTGREEN.
Next audit239 remaining against other exact saved/cached sources before more
synthesis; preserve unknown/partial evidence and old failed experimental gates.

## Historical method investigation

The82source packaged-context experiment completed and FAILED:one uncut-intro
OGG false approval,25/28OGG prior positives preserved. Independent structural
audit418recorded observations foundzero issues; structural validity alone did
not make ASR complete. The separately registered conservative v2 hard isolated
count/number veto rejects all204bad-control observations and preserves28/28WAV,
25/28OGG positives, but transfers7/10WAV,6/10OGG earlier context matches; both
fail the original80percent gate. Neither context strategy selected or installed.
Do not lower these historical gates or call the12qualifying sources live yield.

Two diagnostic takes already pass existing isolated checks:Basket full EN1.0,
Elige un álbum ES0.8593. They were recovered through the UNCHANGED v7 saved
adapter/transactions, without contextual admission or new synthesis. Actual
Spanish ASR Elie un álbum and compact English transport direction are retained.
Saved plans explicitly reconcile semantic cue aliases, exact selected masters,
raw/job/key/request/hash proofs, planned versus actual delivery and pending human
review. Corpus reservations stay25; all16separate diagnostic submissions and
lifetime per-cue totals are pinned in diagnostic-generation-ledger-v1.json.

Latest source/evidence: `2026-10-22_SAVED_SUBSTITUTION_SEAM.md` (archived; see git history).
The optional disabled seam is implemented; held-out48-case v1 failed due a new
NumPy real-scalar timing bug. Corrected cache-only v2 retains15/16positives,
rescues1/12substitution sources, rejects20controls with1554protected hashes
unchanged; independent16physical/1clock audit0issues. Three incomplete sources
stay held; no reroll, synthesis or install.190voice testsPASS; fullverify abort6.
Next exact step is explicit saved-only adapter/final-check/provenance and
provider-forbidden transaction tests before recovery, with all bulk holds kept.
This narrow result does not promote the failed broad experiment or prove live
yield.

Historical proposed scope was an optional initially disabled WAV-only saved-substitution
checker/candidate seam with hard isolated count/number veto, PCM/cache/timestamp
coverage proofs and held-out saved controls. Keep defaultv7 and OGG unchanged;
no general method adoption or bulk restart from failed experiments. The safety
review owns exact next steps. Original plans, sources, receipts, masters and all
call histories remain preserved. Full verification remainsNOTGREEN.

## Initial authority and historical stage boundary

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

## Latest continuation (supersedes only the running-state description above)

Conditioning diagnostic finished8jobs: compact direction1/4pass, no instruction
0/4. No new prompt default is selected. Exact saved Oskar attempt02 was recovered
under opt-in `target-only-v7-saved-oskar-en-v1` /
`locale-number-tokens-v2-oskar-en-v1`: only English Oscar/Oskar spelling equality
is added. Raw transcript is retained; wrong names, extra words and numbers stay
rejected. Normal and historical v1/v2 policies are unchanged. Installed pending;
audit1of667pairs changed,666unchanged, zero synthesis or budget changes. Evidence
`2026-10-22-rejection-investigation/natural-oskar-recovery-v1/`.

The parent247run stays held. Its197never-submitted ordinary phrases use
`natural-context-speech-v1`, with the same recipe/gates/guards and their ORIGINAL
unused allowances.45unstarted letter-name cues are explicitly held separately;
the two other exhausted examples remain unresolved, with no fresh allowance.
This partition is not a claim of successful method repair. Actual early results
still govern whether the ordinary stage may continue.

`natural_continuation.prepare_unstarted` requires parent METHOD_REVIEW_REQUIRED,
unchanged originals/registry and zero reservations; it excludes specified topics,
records held IDs and a one-child parent handoff before creating the child.
`validate_handoff` pins source plan/ledger and child path/plan/scope before calls.
The external exact preparation script is
`2026-10-22-rejection-investigation/prepare-natural-speech-continuation.py`;
DO NOT rerun it: the child exists and the handoff rejects duplication.
Current run uses the exact run command below with `natural-context-speech-v1`.
Inspect actual producer.pid/log/progress; a historical PID is not live evidence.

At this stage boundary423of667are kept/installed,244unresolved. All new
recordings human-listening-pending. Every stage must audit actual installation
pairs, saved source provenance and retained budgets, then keep the remaining
letter/exhausted/unstarted lists explicit. Do not claim all files completed.

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
