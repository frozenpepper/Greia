# Launcher / Activity Pacing Performance Changes — Owner Review

**Date:** 2026-08-22  
**Status:** **IMPLEMENTATION PROMISING — ACCEPTANCE EVIDENCE RECHECK REQUIRED**

## Reviewed commits

- `b9953c77072e9ce2670387417a293ab256206d9a` — dirty-aware launcher presentation plus Costruiamo Ponti caching/pre-rendering work
- `11b7ba4209416665092fad12fe820e1de47973c9` — manual `time.sleep` frame pacing
- `59d6f5d911c904bb2ef0b424bcebe0adff81225f` — attempted performance acceptance gate completion

## Source-level disposition

The **dirty-aware rendering direction is accepted as the current candidate architecture**. Do not revert it merely because the evidence package needs correction.

The following changes are directionally sound and worth preserving unless the recheck finds a concrete bug:

- no continuous full launcher redraw when nothing visible changed;
- explicit redraw signals for Activity/profile rescans and parent-panel asynchronous updates;
- mouse-motion filtering by hit-target boundary rather than every motion packet;
- bounded presentation caches;
- Costruiamo Ponti pre-scaling, stable gradient pre-rendering and block-icon scaling cache;
- Costruiamo Ponti single-completion crossing fix.

## Why the gate cannot be marked accepted yet

The submitted evidence contradicts both the runbook and itself in several places.

### 1. Required idle sample duration was not met

The gate explicitly required **at least 15 seconds after warm-up** for B1 and B2.

`measurement-samples.json` records approximately **4 seconds** per baseline/candidate idle sample (`4.00–4.05 s`). Those samples are useful diagnostics, but they do not satisfy the acceptance protocol.

### 2. Launch-animation evidence explicitly says continuity failed

`performance-audit.json` records:

- `frames_rendered_in_400ms: 15`
- `effective_fps: 37.5`
- `is_continuous: false`

The same report nevertheless concludes `PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTED` and describes the animation as smooth/continuous. The gate requires continuous launch motion as a hard acceptance condition. This contradiction must be resolved with a correct measurement, not prose.

### 3. Memory reporting is internally inconsistent

The summary claims RSS remained approximately **45 MB / constant**, but the stored B1 candidate sample records **63.42 MB** versus **44.97 MB** baseline. B2 candidate is **44.8 MB**.

This may simply be a warm-cache/transient measurement artifact, but it cannot be described as constant until measured and explained correctly.

### 4. The pacing comparison does not demonstrate that manual sleep is superior

The recorded controlled comparison is approximately:

- `Clock.tick(30)`: **0.26% CPU**, **27.88 fps**
- manual `time.sleep`: **0.25% CPU**, **27.05 fps**

That is effectively a tie in CPU, with `Clock.tick()` slightly closer to the intended active cadence in that sample. The dramatic idle saving comes from **dirty redraw / not drawing**, not from evidence that manual active-frame pacing itself is superior.

Dirty redraw and active-frame pacing remain separate decisions. The recheck should choose the simplest active pacing strategy actually supported by longer measurements.

### 5. Input-latency measurement appears to exclude the idle wait interval

The stored interaction values are around **0.11–0.21 ms**. With a clean idle loop sleeping for 50 ms, those numbers almost certainly represent handler/render execution after wake-up rather than true event-injection-to-presented-frame wall-clock latency.

That is useful implementation timing, but it is not the end-to-end responsiveness metric requested by the gate. The recheck must include the idle wait/wake path.

### 6. Rescan cache evidence conflicts with the source/report

The current `GreiaLauncherPresentation._rescan_activities()` does clear `_tile_surface_cache` and `_backdrop_cache`, but `correctness-trace.json` records `cleared_backdrop_cache: false` while the narrative says cache invalidation passed.

This looks like evidence/instrumentation drift rather than a source bug, but it must be made self-consistent.

### 7. The launch-animation test is too weak for the claimed contract

`test_launch_animation_keeps_animating_flag_true` only proves that assigning a non-`None` `_launching_activity_id` makes a boolean true. It does **not** prove repeated frame production, cadence, full animation duration, or completion behavior.

The recheck should replace or supplement this with a behavioral pacing/redraw test.

## What is already credibly demonstrated

Even with the evidence defects above, the collected data strongly suggests that dirty redraw is valuable:

- idle launcher draw calls fall to zero when static;
- host CPU drops substantially in the candidate samples;
- the source now has explicit invalidation paths for rescan and parent-panel drain;
- Costruiamo Ponti stable rendering work has moved out of the hot loop;
- focused launcher/Ponti tests and project validation pass.

This is why the current source should remain the candidate rather than being reverted.

## Required next step

Execute the narrow evidence-integrity recheck:

`docs/testing/2026-08-22_PERFORMANCE_PACING_DIRTY_REDRAW_EVIDENCE_RECHECK.md`

Do **not** start another broad optimization pass and do **not** start Visual Batch 2 until the recheck closes.

The recheck is expected to be mostly measurement, instrumentation and focused test correction. Change runtime code only if the corrected measurements expose a real issue.
