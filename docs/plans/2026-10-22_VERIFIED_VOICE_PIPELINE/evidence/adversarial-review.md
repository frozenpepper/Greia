# Design review — 2026-10-22

Planning review only; no source/test/live execution proof.

## Pass 1: contracts and hidden choices

- Nested corpus, VoiceEngine and shared retries could produce nine takes: resolved
  with one shared budget, engine capability ownership, and no local reroll.
- Current warning result exposes last failed audio: resolved by FAILED_QUALITY
  with no final approved output; diagnostic candidates are separately typed.
- A verifier crash could burn three voices: infrastructure blocks and resumes the
  same audio; only measured quality failures allocate another synthesis attempt.
- Quality-off cannot guarantee zero ASR when cutting needs alignment: the two
  independent policy flags and UNVERIFIED result make the residual work explicit.
- Original script chunking could separate intro from target: chunk first, then
  freeze one indivisible composite; oversize composite rejects before rendering.
- Existing Dani and tiny-speech exclusions would bypass the feature: default v2
  checks all ordinary character speech; pedagogical semantics remain separate.
- Concurrent stale job dictionaries could erase results/cancellation: coordinator
  sole writer, fsynced transitions and lease-fenced completion messages.
- Old shared callers lack explicit locale: versioned v2 recording/script routes
  and updated CLI defaults; v1 stays legacy-unverified with no silent fallback.
- Generic code in Greia would fork the shared production mechanism: shared core
  owns quality/extraction; Greia supplies identities and installation transactions.
- Voice-design and Chatterbox could be falsely advertised as v2 verified: audition
  workflow stays distinct; unsupported quality capability rejects before rendering.
- Retrying after three false Whisper failures remains a real cost/quality tradeoff,
  not solved by queue architecture. Persist all failures and cap the budget.

## Pass 2: intermediate safety and performance

- Sessions 00–04 add inactive modules; no public default changes until complete
  ledger/scheduler/verifier path exists in 05. Greia adoption occurs only in 06.
- Source sessions do not touch live ML, existing jobs, masters or runtime audio.
- One verifier subprocess and eight candidate credits bound backlog; a blocked
  verifier halts admission without losing pending work or filling disk indefinitely.
- Two queues on this 16 GiB MLX host do not prove safe GPU overlap. Serialized
  resource arbitration is initial policy; opt-in overlap needs measured throughput,
  latency and memory evidence from fixed paired inputs.
- Script mixes wait for selected chunks; one failed chunk does not rerender all
  siblings, and partial failed raw audio cannot leak as the final short target.
- Timeout and crash do not imply the provider call never happened. Same key/seed,
  raw-file reconciliation, durable attempt allocation and UNKNOWN_SUBMISSION keep
  the three-take bound honest; no unconditional exactly-once claim is made.
- Live acceptance has a real thin driver built in 06, a dry-run manifest and 102
  maximum renderer calls. A failure does not authorize more takes or bulk restart.
- Existing shared dirty files are recorded in source-baseline.json; implementing
  this design must reconcile, not reset or wholesale commit those changes.

Remaining unproved predicates: actual ASR throughput, GPU overlap resource safety,
model false-rejection rate across the cast, and the future end-to-end implementation.
These remain live gates, not claims of success.

## Final reconciliation

- A similarity score can pass an extra/repeated short-target word. Added a short
  target token-count guard instead of pretending the scalar score is sufficient.
- Current global Greia lock could still serialize all clients after adding queues.
  Default VoxStage removes that client model lock; legacy local model ownership
  and corpus/output transaction leases stay explicit. Blocking convenience calls
  are not used as the batch scheduler.
- Final-target silence checks must not reject a deliberately long disposable
  carrier pause. Only delivered target audio is judged for final silence limits.
