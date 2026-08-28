# Greia Encyclopedia workstream handover

**Updated:** 2026-08-28  
**Runtime pages:** **43 / 43 planned executable pages**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Current evidence:** **SOURCE-VERIFIED / HEADLESS-LIFECYCLE-SMOKE-PASS / 43-PAGE-MECHANICAL-TRAVERSAL-PENDING / NARRATION ACCEPTANCE PENDING**

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
- `enciclopedia_engine.py` owns only lifecycle, explicit page registry, semantic input and bounded internal navigation.
- Subject behavior stays in page modules.
- No runtime TTS, speech recognition, AI/LLM, network factual lookup or heavy physics.
- Spoken material is authoring-time prerecorded audio only.
- Greia protected Home remains platform-owned; Encyclopedia internal Back is separate.
- Italian and English are the initial locales.
- Visual/text/audio caches remain explicitly bounded.
- Acer Aspire One-class hardware remains the performance floor.
- Do not introduce giant procedural page scripts or generic abstraction layers without real shared invariants.

---

## 3. Research and narration authority

Every factual page has one authority under:

```text
encyclopedia/research/<section>/<entry>.md
```

Canonical narration coordination:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

Current Encyclopedia ledger state remains:

```text
378 rows
378 REQUESTED
0 RECORDED_UNREVIEWED
0 OWNER_ACCEPTED
```

`378` means request rows, not generated files.

Voice generation/review is a separate authoring workflow. Simulator acceptance does **not** wait for narration production. Only real owner listening can set `OWNER_ACCEPTED`, and only accepted rows may be integrated into runtime audio assets.

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
voice-sync                           PASS
voice-sync-check                     PASS
voice rows                           378 / 378
focused Encyclopedia tests            53 / 53 PASS
make verify                         1431 / 1431 PASS
first-party Activity validations      35 / 35 PASS
accepted-audio sync check              PASS (0 OWNER_ACCEPTED)
git diff --check                       PASS
worktree postflight                    clean
```

Do not rerun the source gate merely to continue Simulator acceptance unless Encyclopedia runtime/source changes.

---

## 5. Headless Simulator harness history

### 5.1 Duplicate-identity failure

The first headless attempt incorrectly republished the built-in Encyclopedia as developer-unsigned. Greia's duplicate-ID guard correctly rejected it. The helper now recognizes built-in Activities and never republishes them.

### 5.2 Collection-first routing failure

The second attempt reached the real Shell but treated the raw Activity registry as the child navigation grid. That was wrong because production Greia is Collection-first:

```text
profile picker
→ Collection Home
→ optional adaptive sub-Collection
→ Activity cards
→ Activity
```

The helper now uses typed `ShellLaunchRoute` derived from the same profile-visible `ActivityCatalogue`, including profile visibility/age/challenge policy.

### 5.3 Corrected lifecycle smoke — GREEN

Owner-machine SHA:

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
bounded semantic RETURN interaction     PASS
protected Greia Home -> real Shell      PASS
headless smoke rc                       0
worktree                                clean
```

This is a real lifecycle acceptance checkpoint. It proves Shell ↔ Encyclopedia launch/survival/input/Home-return plumbing, **not** all 43 pages and not subjective UX quality.

The child log also contained:

```text
libpng error: bad adaptive filter value
```

The four captured smoke PNGs were valid and the run passed. Therefore this warning is non-blocking evidence but remains diagnostically unresolved. Do not claim it is caused by the screenshot encoder; it may represent a PNG asset decode that fell back visually.

Durable review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_HEADLESS_LIFECYCLE_ACCEPTANCE.md
```

---

## 6. Current next gate — 43-page mechanical traversal

Tool:

```text
tools/encyclopedia_v01_headless_traversal.py
```

Contract tests:

```text
tests/test_encyclopedia_v01_headless_traversal.py
```

Single operator instruction:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

The tool must, in one real Shell-launched session:

```text
capture Encyclopedia Home
capture all 6 section pages
reach all 36 factual entries
send one bounded primary semantic ACTIVATE interaction per entry
capture before/after PNGs for every factual entry
return from every entry through internal semantic Back
return from each section to Encyclopedia Home
return through protected Greia Home to the real Shell
```

It uses semantic keyboard navigation only for Encyclopedia content. It does not instantiate page classes, read hidden page state, or use pointer coordinates to locate hotspots.

A changed frame is **not** equivalent to visual/signature acceptance. The mechanical tool records change metrics and screenshots; the next visual review must inspect whether the intended interaction is actually understandable and correct.

---

## 7. Acceptance layers that remain separate

After mechanical traversal passes, still pending:

```text
visual/signature-interaction review of captured before/after frames
pointer vs semantic-keyboard parity sample
pre-reader/no-reading UX review
responsive viewport/profile matrix
narration owner acceptance/integration
physical Acer/Pi acceptance
```

Only after Simulator visual/input/pre-reader/responsive gates pass may the label become:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```

Narration remains a separate gate and must never be replaced with runtime TTS.

---

## 8. Evidence authorities

Reusable acceptance runbook:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

Current local-agent task:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Key reviews:

```text
docs/reviews/2026-08-27_ENCYCLOPEDIA_V01_POST_BUILD_DRIFT_REVIEW.md
docs/reviews/2026-08-27_ENCYCLOPEDIA_V01_CLOSURE_TOOLING_REVIEW.md
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_HEADLESS_LIFECYCLE_ACCEPTANCE.md
```
