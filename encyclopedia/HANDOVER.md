# Greia Encyclopedia workstream handover

**Updated:** 2026-08-28  
**Runtime pages:** **43 / 43 planned executable pages**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Current evidence:** **SOURCE-VERIFIED / HEADLESS-LIFECYCLE-SMOKE-PASS / 43-PAGE-MECHANICAL-TRAVERSAL-PASS / VISUAL+INPUT ACCEPTANCE PENDING / NARRATION ACCEPTANCE PENDING**

This is the current continuation contract. Historical construction detail remains in `encyclopedia/PROGRESS.md` and dated reviews.

---

## 1. Frozen v0.1 scope

Exactly 43 executable pages:

```text
home
animals + 6 entries
space + 10 entries
earth + 5 entries
body + 5 entries
machines + 5 entries
history + 5 entries
```

The 36 factual entry IDs are frozen by `encyclopedia/pages/catalogue.py` and the runtime registry. Do not add v0.1 topics unless the owner deliberately changes scope.

---

## 2. Runtime architecture invariants

- `main.py` remains a thin composition root.
- `enciclopedia_engine.py` owns lifecycle, explicit page registry, semantic input and bounded internal navigation only.
- Subject behavior stays in page modules.
- Runtime remains offline and low-resource: no runtime TTS, speech recognition, AI/LLM, network factual lookup or heavy physics.
- Spoken material is authoring-time prerecorded audio only.
- Greia protected Home remains platform-owned; Encyclopedia internal Back is separate.
- Italian and English are the initial locales.
- Visual/text/audio caches remain explicitly bounded.
- Acer Aspire One-class hardware remains the performance floor.
- Do not introduce giant procedural page scripts or generic abstractions without real shared invariants.

---

## 3. Research and narration authority

Every factual page has one research/wording authority under:

```text
encyclopedia/research/<section>/<entry>.md
```

Canonical narration coordination:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

The source-gate ledger checkpoint was:

```text
378 rows
378 REQUESTED
```

`378` means coordination rows, not 378 generated files.

Voice generation/review is a separate authoring workflow. Simulator acceptance does **not** wait for narration production. Only real owner listening may establish `OWNER_ACCEPTED`, and only owner-accepted recordings may be integrated into runtime audio assets.

---

## 4. Deterministic source gate — GREEN

Green source/runtime SHA:

```text
d89809a43cdfe62c85775ccdcfd04eb6e34fbd05
```

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_044052/
```

Proven there:

```text
voice sync/check                         PASS
voice rows                              378 / 378
focused Encyclopedia tests              53 / 53 PASS
make verify                           1431 / 1431 PASS
first-party Activity validations        35 / 35 PASS
accepted-audio sync check               PASS
worktree                                clean
```

Do not rerun the source gate merely to continue visual/Simulator acceptance unless relevant runtime/source changes require it.

Durable review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_SOURCE_GATE_ACCEPTANCE.md
```

---

## 5. Headless lifecycle smoke — GREEN

Owner-machine tested SHA:

```text
621c1950133151b9c89c14ec74e4628e4c665147
```

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_070951-headless-route-smoke/
```

Proven:

```text
focused Simulator tests                 45 / 45 PASS
built-in Activity detection             PASS
route                                   home[2]=learn -> activity[4]=org.greia.enciclopedia
real Shell first frame                  PASS
profile -> Collection Home              PASS
Collection route navigation             PASS
real Shell -> Encyclopedia              PASS
first Encyclopedia frame                PASS
12-second survival                      PASS
bounded semantic interaction            PASS
protected Greia Home -> real Shell      PASS
worktree                                clean
```

This proves the real Shell/Activity lifecycle lane, not full visual quality.

Durable review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_HEADLESS_LIFECYCLE_ACCEPTANCE.md
```

---

## 6. Complete 43-page mechanical traversal — GREEN

Owner-machine tested SHA:

```text
8cda9cbaa4beb4f5c38a9945479f0f4c88f8ee65
```

Evidence directory:

```text
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal/
```

Evidence ZIP:

```text
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal.zip
```

Proven:

```text
focused traversal/Simulator tests       53 / 53 PASS
mechanical traversal rc                 0
Shell -> Encyclopedia                   PASS
sections captured                       6 / 6
factual entries reached                36 / 36
semantic ACTIVATE delivered            36 / 36
before/after entry pairs               36 / 36
internal Back returns                  36 / 36
all sections -> Encyclopedia Home       PASS
protected Greia Home -> Shell           PASS
traversal-summary status                PASS
worktree                                clean
```

The evidence contains 82 PNGs: Shell/profile state, Encyclopedia Home, all six section pages, before/after frames for all 36 entries, final Encyclopedia Home and returned Shell.

This establishes complete **mechanical runtime breadth** for the frozen 43-page v0.1 base.

It does **not** establish that each signature interaction is visually/educationally correct. `changed_pixel_fraction` is diagnostic only.

Durable review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_MECHANICAL_TRAVERSAL_ACCEPTANCE.md
```

---

## 7. Unresolved child warning

Both the green lifecycle smoke and the green mechanical traversal emitted:

```text
libpng error: bad adaptive filter value
```

The runs completed and expected Simulator screenshots were valid. The warning remains unresolved and must not be attributed to the screenshot encoder without evidence. During visual evidence review, explicitly check for missing/fallback imagery that could indicate a failed PNG asset decode.

---

## 8. Current next gate — visual review first

The next step is **not another owner-machine traversal**.

The evidence ZIP from the green mechanical traversal must be uploaded to the primary/vision-capable reviewer and inspected for:

```text
all 6 section-page visual states
all 36 before/after factual-entry pairs
intended signature-interaction visibility/correctness
fallback or missing imagery, including possible libpng-related symptoms
visual hierarchy and child affordances
pre-reader/no-reading usability problems visible in the captured states
```

Until that review is complete, do not start another broad Simulator run merely for momentum.

Rolling owner-machine authority:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

That file should currently say there is **no authorized local-agent run** until the evidence ZIP has been visually reviewed and the next targeted input/responsive task is defined.

---

## 9. Acceptance layers still pending

```text
visual/signature-interaction review of captured frames
pointer vs semantic-keyboard parity sample
pre-reader/no-reading UX acceptance
responsive viewport/profile matrix
narration owner acceptance/integration
physical Acer/Pi acceptance
```

Only after visual/input/pre-reader/responsive Simulator gates pass may the label become:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```

Narration remains separate and must never be replaced with runtime TTS.

---

## 10. Key evidence authorities

Reusable broad acceptance runbook:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

Current owner-machine pointer:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Durable reviews:

```text
docs/reviews/2026-08-27_ENCYCLOPEDIA_V01_POST_BUILD_DRIFT_REVIEW.md
docs/reviews/2026-08-27_ENCYCLOPEDIA_V01_CLOSURE_TOOLING_REVIEW.md
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_SOURCE_GATE_ACCEPTANCE.md
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_HEADLESS_LIFECYCLE_ACCEPTANCE.md
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_MECHANICAL_TRAVERSAL_ACCEPTANCE.md
```
