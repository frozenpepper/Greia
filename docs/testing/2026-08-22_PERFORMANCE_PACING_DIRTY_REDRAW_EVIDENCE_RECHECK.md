# 2026-08-22 — Performance Pacing & Dirty-Redraw Evidence Recheck

**Status:** ACTIVE LOCAL-AGENT GATE  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

## 1. Purpose

Perform a **narrow evidence-integrity recheck** of the performance work currently on `main`.

Do not redo the performance architecture from scratch. The dirty-aware renderer, explicit invalidation contracts, bounded caches and Costruiamo Ponti hot-loop reductions are the current candidate and should remain unless corrected measurements expose a real bug.

Read first:

- `docs/reviews/performance/2026-08-22_launcher-pacing-dirty-redraw/OWNER_REVIEW.md`
- `docs/testing/2026-08-22_PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTANCE.md`
- existing evidence under `docs/reviews/performance/2026-08-22_launcher-pacing-dirty-redraw/`

The attempted acceptance commit is:

`59d6f5d911c904bb2ef0b424bcebe0adff81225f`

The pre-performance baseline remains:

`d2f45f3be36d2cee1956597c5240722192275793`

Do **not** reset `main` to either commit.

---

## 2. Scope discipline

This recheck is primarily about:

- correcting measurement methodology;
- reconciling contradictory evidence;
- strengthening one or two weak behavioral tests;
- choosing active-frame pacing based on corrected measurements.

Do not begin a new broad optimization campaign.

Do not start First-Party Visual Batch 2 in this gate.

Runtime code may be changed only if the corrected evidence demonstrates a real issue.

---

## 3. Recheck A — repeat idle measurements correctly

The previous stored samples were only ~4 seconds, but the original gate required at least 15 seconds after warm-up.

Repeat B1 and B2 for both baseline and candidate under matching conditions.

### A1. Idle Collection Home

For **baseline** and **candidate**:

- warm up first;
- measure for **at least 15 continuous seconds**;
- preferably collect **3 independent runs** per implementation;
- use the same viewport and SDL/display mode;
- no input;
- no animation;
- no package/profile changes.

Record for every run:

- exact duration;
- CPU measurement method;
- process CPU time / utilization;
- draw/frame presentation count;
- loop wake cadence if instrumented;
- RSS at start/end and peak or maximum observed if practical;
- environment and viewport.

### A2. Idle populated Activity category

Repeat the same protocol in a normal populated in-category launcher page.

### A3. Physical Acer results

If physical Atom N270 measurements are used in the final report, store the **actual raw samples** in the project evidence, including:

- device identification;
- command/tool used to measure CPU;
- duration;
- launcher state;
- enough sample values or summary source to audit the claim.

If raw physical evidence cannot be captured cleanly this session, retain the host benchmark and label any prior physical observation as historical/supporting rather than part of this recheck's measured matrix.

---

## 4. Recheck B — true event-to-visible-update latency

The previous ~0.1–0.2 ms values appear to measure handler/render work after wake rather than the full idle-wait path.

Measure **wall-clock time from event injection/delivery to the frame presentation that visibly reflects it**.

Cover at least:

- pointer entering a card from clean idle;
- keyboard focus move from clean idle;
- category switch from clean idle;
- pagination from clean idle.

Use a reproducible instrumentation point around Pygame event injection/receipt and `_on_frame_presented()` or equivalent frame-present hook.

Collect at least **30 samples** across the scenarios.

Report:

- min;
- mean/median;
- p95;
- max.

The measurement must include any clean-loop 50 ms wait/wake delay.

Do not claim sub-millisecond end-to-end responsiveness unless the measurement genuinely includes that path.

---

## 5. Recheck C — launch animation continuity and cadence

The previous `performance-audit.json` records `is_continuous: false` while the prose says the launch animation passed. Resolve this directly.

Instrument one complete launch animation from start to completion.

Record frame timestamps, not only a count.

Verify:

- frames continue to be presented for the complete intended animation interval;
- the animation reaches its intended completion state;
- no unexpected long gap/hitch occurs;
- actual cadence is compatible with the intended active pacing;
- duration remains consistent with `LaunchMotion.duration_seconds` / product behavior.

Report at minimum:

- animation start timestamp;
- animation end timestamp;
- total duration;
- presented frame count;
- mean inter-frame interval;
- p95 inter-frame interval;
- maximum inter-frame gap;
- effective FPS;
- final boolean `is_continuous` based on a documented criterion.

Do not call 37.5 or 40 FPS an intended 30 FPS result without explaining the measurement window/counting method.

### Required behavioral test

Replace or supplement the weak test that merely assigns `_launching_activity_id`.

Add a focused test that proves the renderer continues requesting/presenting frames while launch animation is active and ceases the animation path correctly when it finishes.

The test should assert behavior, not private-variable tautology.

---

## 6. Recheck D — pacing strategy decision

Repeat the controlled active-frame comparison between:

1. `pygame.time.Clock.tick(30)`;
2. current manual active-frame `time.sleep(max(...))` pacing.

The clean-idle dirty-redraw behavior is **not** under dispute and should remain separate from this comparison.

Use sufficiently long/repeated active-animation samples to compare:

- CPU;
- achieved cadence;
- jitter / inter-frame variance;
- responsiveness if relevant;
- implementation simplicity.

### Decision rule

Do not declare manual `time.sleep()` superior for a negligible difference such as 0.26% versus 0.25% CPU.

If the two are effectively tied, prefer the simpler/clearer active pacing strategy and document why.

A perfectly valid architecture is, for example:

- dirty renderer: **no draw while clean**;
- clean idle: low-power wait/sleep;
- active dirty/animation frames: normal `Clock.tick(30)` pacing.

That is only an example, not a mandatory implementation. Let measurements decide.

---

## 7. Recheck E — cache invalidation evidence consistency

The current source clears `_tile_surface_cache`, `_backdrop_cache`, and `_cached_activities_key` on successful Activity discovery change, but `correctness-trace.json` says `cleared_backdrop_cache: false`.

Create a focused proof that:

1. seeds the relevant caches;
2. triggers a legitimate discovery-token/content change;
3. proves the relevant caches are invalidated/rebuilt;
4. proves the new visible state appears without unrelated user input.

Update the trace so it agrees with the source and actual test.

Add or strengthen a focused automated test for this behavior.

Also retain the parent-panel async drain proof and confirm it still produces redraw without unrelated input.

---

## 8. Recheck F — memory sanity

Resolve the prior contradiction:

- baseline B1 RSS: ~44.97 MB;
- candidate B1 RSS: ~63.42 MB;
- candidate B2 RSS: ~44.8 MB;
- summary claimed ~45 MB constant.

Do not optimize memory merely because one sample is high.

Instead:

- repeat after consistent warm-up;
- record start/end/peak or multiple periodic samples;
- determine whether the 63.42 MB value was transient, cache warm-up, measurement noise, or reproducible;
- report the result accurately.

A bounded stable increase may be acceptable. The requirement is **truthful characterization and no leak/growth trend**, not an arbitrary 45 MB target.

---

## 9. Costruiamo Ponti regression sanity

Do not redo the whole Activity review.

Run the existing focused tests and one short real Simulator crossing sanity check to confirm that any pacing change made during this recheck did not regress:

- correct block placement;
- Flash traversal;
- exact-once completion;
- next-level/victory transition.

---

## 10. Required automated verification

Run at minimum:

```bash
PYTHONPATH=src pytest tests/test_launcher_pacing_dirty_redraw.py
PYTHONPATH=src pytest tests/test_launcher*.py tests/test_costruiamo_ponti_contract.py
make validate
make visual-assets-check
```

Report exact test counts.

If you modify pacing/runtime code, also run the closest broader launcher/simulator tests that cover the changed path.

---

## 11. Evidence update contract

Update the existing directory:

`docs/reviews/performance/2026-08-22_launcher-pacing-dirty-redraw/`

Keep the owner review.

Correct/replace as necessary:

- `PERFORMANCE_REPORT.md`
- `performance-audit.json`
- `measurement-samples.json`
- `correctness-trace.json`

You may add one compact timestamp/sample file if needed for launch-frame data or physical CPU raw samples, but avoid artifact explosion.

The evidence must be internally self-consistent.

Do not preserve known-false acceptance statements merely for history; Git already preserves history.

---

## 12. Acceptance decision

Conclude with exactly one of:

- `PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTED`
- `PERFORMANCE_PACING_DIRTY_REDRAW_REQUIRES_OWNER_REVIEW`
- `PERFORMANCE_PACING_DIRTY_REDRAW_BLOCKED`

`ACCEPTED` requires:

- >=15 s warm idle measurements for B1/B2 under matching conditions;
- no known stale-UI invalidation path;
- evidence and source agree on cache invalidation;
- true event-to-visible-update latency measured including idle wait;
- launch animation explicitly measured as continuous/correct;
- active pacing choice justified by the corrected data;
- memory behavior characterized truthfully with no leak trend;
- Costruiamo Ponti remains correct;
- focused and normal validation pass.

---

## 13. Transfer bundle

Rebuild the existing root bundle:

`GREIA_PERFORMANCE_REVIEW_PACING_DIRTY_REDRAW_2026-08-22.zip`

Include the corrected performance review directory only.

Commit and push the corrected evidence, tests and any genuinely required source fixes to `origin/main`.

---

## 14. Final reply to owner

Return only:

1. final disposition;
2. corrected B1/B2 15s+ measurements;
3. true event-to-present latency statistics;
4. launch animation cadence/continuity statistics;
5. pacing choice and why;
6. memory conclusion;
7. cache-invalidation proof result;
8. exact test/validation counts;
9. exact review directory;
10. exact transfer ZIP;
11. exact pushed commit SHA.

Do not paste this runbook into chat.
