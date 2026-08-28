# Greia Encyclopedia workstream handover

**Updated:** 2026-08-28  
**Runtime pages:** **43 / 43 planned executable pages**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Current evidence:** **SOURCE-VERIFIED AT PRIOR SHA / HEADLESS-LIFECYCLE-SMOKE-PASS / 43-PAGE REACHABILITY+BACK PASS / VISUAL REPAIRS LANDED + REVERIFY PENDING / NARRATION ACCEPTANCE PENDING**

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

## 4. Deterministic source gate — prior GREEN checkpoint

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

Runtime visual source has changed since that checkpoint, so the current repair tranche must run the source gate exactly once after the traversal-harness fix is committed.

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
route                                   home[2]=learn -> activity[4]=org.greia.enciclopedia
real Shell -> Encyclopedia              PASS
first Encyclopedia frame                PASS
12-second survival                      PASS
bounded semantic interaction            PASS
protected Greia Home -> real Shell      PASS
worktree                                clean
```

Durable review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_HEADLESS_LIFECYCLE_ACCEPTANCE.md
```

---

## 6. 43-page mechanical traversal — reachability/back GREEN

Owner-machine tested SHA:

```text
8cda9cbaa4beb4f5c38a9945479f0f4c88f8ee65
```

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal/
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal.zip
```

Mechanically proven:

```text
focused traversal/Simulator tests       53 / 53 PASS
Shell -> Encyclopedia                   PASS
sections reached                        6 / 6
factual entries reached                36 / 36
semantic ACTIVATE delivered            36 / 36
internal Back returns                  36 / 36
all sections -> Encyclopedia Home       PASS
protected Greia Home -> Shell           PASS
traversal-summary status                PASS
worktree                                clean
```

This establishes complete 43-page runtime reachability and Back/Home continuity.

The run created 36 `before` and 36 `after` files, but the later visual review found that **two of those pairs are not coherent entry-interaction comparisons**; see §7.

Durable mechanical review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_MECHANICAL_TRAVERSAL_ACCEPTANCE.md
```

---

## 7. Primary visual evidence review — repair required

The actual uploaded screenshot ZIP was reviewed visually by the primary/vision-capable reviewer.

Durable review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_VISUAL_EVIDENCE_REVIEW.md
```

### 7.1 Positive result

The core visual architecture is viable at 1024×600:

- coherent procedural style;
- large, clear focus targets;
- six distinctive section worlds;
- clear internal Back vs protected Greia Home;
- presenter characters render normally;
- most first interactions produce understandable visual changes;
- no broad frame corruption or obvious global missing-asset fallback.

### 7.2 Capture race — Sun and Neptune

These files are not coherent entry-before states:

```text
space.sun-before.png
space.neptune-before.png
```

They still display the animated Space section. The corresponding `after` files display the Sun/Neptune entry pages.

Therefore the previous archive provides:

```text
43 / 43 page reachability       PASS
36 / 36 Back continuity         PASS
34 / 36 coherent first-action visual pairs
```

The likely cause is generic traversal timing: the helper accepted the first later global Activity frame even when that frame belonged to the previous animated page. This is a harness/evidence defect, not a Sun/Neptune runtime defect.

### 7.3 Pyramids caption overflow — runtime defect

`history.pyramids-before.png` showed the approved Italian intro wording overflowing horizontally outside the caption panel at 1024×600.

The primary agent has already fixed `pages/pyramids.py` so layout adapts to the authoritative wording: it prefers a fitted single line, then a balanced two-line caption, with a defensive final fallback. The wording itself was not changed.

### 7.4 Body Teeth target contrast — runtime/pre-reader defect

`sections/04-body.png` showed the Teeth target as nearly blank because light enamel circles were drawn on an almost-identical warm-white target disk.

The primary agent has already fixed `pages/body.py` with a stronger pastel enamel fill and darker compact outline, preserving navigation and content.

### 7.5 UX notes, not yet blockers

- Home `TANTO TEMPO FA` remains more abstract than the other section portals and may merit a more concrete historical icon later.
- Some default first ACTIVATE states are subtle; the old mechanical run exercises only one default-focus action and does not certify every multi-step signature interaction.

---

## 8. `libpng` warning remains diagnostic

Both the lifecycle smoke and mechanical traversal emitted:

```text
libpng error: bad adaptive filter value
```

The visual review found no broad missing presenter, broken section composition or obvious blank asset placeholder that explains it.

The warning remains unresolved diagnostic evidence. Do not assign it to the screenshot encoder or a specific asset without direct evidence. Do not block the visual repair tranche on speculative repair of this warning.

---

## 9. Current exact owner-machine task

Rolling pointer:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Dedicated authoritative task:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_VISUAL_REPAIR_LOCAL_AGENT.md
```

Required sequence:

```text
safe update
→ implement only generic traversal page-transition settle contract + regression
→ focused tests once
→ commit/push harness/test fix
→ source gate once (runtime source changed)
→ fresh 43-page traversal once
→ evidence ZIP
→ stop for primary visual review
```

The harness fix must remain generic: no Sun/Neptune special cases, hidden page-state hooks or pointer-coordinate discovery.

---

## 10. Acceptance layers still pending

```text
fresh visual re-review after repair/recapture
complete signature-interaction review beyond one default ACTIVATE where needed
pointer vs semantic-keyboard parity sample
pre-reader/no-reading final acceptance
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

## 11. Key evidence authorities

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_SOURCE_GATE_ACCEPTANCE.md
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_HEADLESS_LIFECYCLE_ACCEPTANCE.md
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_MECHANICAL_TRAVERSAL_ACCEPTANCE.md
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_VISUAL_EVIDENCE_REVIEW.md

docs/testing/GREIA_ENCYCLOPEDIA_V01_VISUAL_REPAIR_LOCAL_AGENT.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```
