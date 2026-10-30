# 2026-08-22 — Performance Pacing & Dirty-Redraw Acceptance

**Status:** ACTIVE LOCAL-AGENT GATE  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

## 1. Purpose

Validate and, where necessary, correct the recent performance work before any further broad optimization or First-Party Visual Batch 2 work.

The candidate performance changes are primarily:

- `b9953c77072e9ce2670387417a293ab256206d9a` — dirty-aware launcher rendering and Costruiamo Ponti pre-scaling/pre-rendering;
- `11b7ba4209416665092fad12fe820e1de47973c9` — replacement of Pygame clock pacing with manual `time.sleep()` pacing.

The owner review is:

`OWNER_REVIEW.md` (archived; see git history)

Read it before modifying source.

This gate is not permission for a broad performance rewrite. Measure first, repair concrete problems, and preserve architecture/product behavior.

---

# 2. Important correction to the working premise

Do **not** assume `pygame.time.Clock.tick()` is inherently a busy-spin implementation.

Pygame has a distinct `tick_busy_loop()` API for busy-loop timing. The choice between `Clock.tick()`, `time.sleep()`, event waiting, or another simple pacing strategy must be justified by actual measurements on the available development environment and by Greia's target constraints.

Do not optimize by folklore.

---

# 3. Phase A — establish a reproducible baseline

Use the pre-performance launcher source at commit:

`d2f45f3be36d2cee1956597c5240722192275793`

as the comparison baseline for launcher pacing/idle behavior.

Do **not** reset or rewrite `main`.

Use a temporary worktree, temporary checkout, or another clean comparison mechanism. Keep all persistent evidence inside the Greia project tree.

Record:

- OS / Python / Pygame versions;
- whether each measurement is normal-window SDL, simulator/headless SDL, or another environment;
- CPU measurement mechanism;
- sample duration;
- viewport;
- active UI state;
- whether the mouse/pointer is moving;
- whether animation is active.

Headless results are useful for regression comparison but must **not** be described as physical-device performance.

---

# 4. Phase B — launcher performance matrix

Measure the baseline and current candidate implementation under the same conditions.

At minimum cover:

## B1. Idle Collection Home

No input, no animation, no package changes.

Measure for at least 15 seconds after warm-up:

- process CPU utilization;
- number of draw calls / frame presentations if instrumentable without distorting results;
- loop wake/poll cadence;
- resident memory sanity.

The current candidate should demonstrate a clear reduction in unnecessary idle work versus the pre-performance baseline.

Do **not** invent a percentage target merely to pass. Report the measured delta.

## B2. Idle in-category Activity catalogue

Use a populated category page with normal cards/icons/titles.

Same measurements as B1.

## B3. Pointer/keyboard interaction responsiveness

Exercise:

- hover transition;
- keyboard focus movement;
- category switching;
- pagination;
- full-title disclosure;
- back-to-Collection-Home navigation.

Measure or timestamp input-to-visible-update latency in a reproducible way.

The 50 ms idle sleep in the candidate implementation means interaction should ordinarily become visible well below a human-noticeable lag. If measurements show a material sluggishness regression, fix the pacing/event-wait approach rather than accepting it for lower CPU.

## B4. Launch animation

Exercise the complete launch animation.

Verify:

- continuous animation frames are still produced;
- intended timing/duration remains correct;
- no visible hitch from the dirty-frame optimization;
- CPU/frame behavior is recorded.

## B5. Resize / responsive invalidation

Resize/window-change paths where supported.

Verify the frame invalidates immediately and caches/layout are refreshed once as intended.

---

# 5. Phase C — dirty-redraw correctness audit

This is a hard acceptance requirement.

A dirty-aware renderer is only valid if every visible state transition has a reliable invalidation path.

Inspect the launcher source and build a short table of visible-state producers and how each causes redraw.

At minimum test the following without relying on an unrelated pointer/key event afterward:

## C1. Activity registry / package rescan

Trigger a legitimate discovery-token change using the normal development/package mechanism.

Verify that:

- `_rescan_if_due()` detects it;
- catalogue/runtime services update as intended;
- the visible launcher updates **without requiring a later user input event**.

If the current API does not expose whether a rescan changed visible state, prefer a clean change signal/boolean or equivalent explicit invalidation contract.

Do not solve this by redrawing the entire launcher continuously again.

## C2. Parent panel asynchronous drain

If `parent_panel.drain()` can change visible content without a Pygame input event, prove that such a change invalidates the frame.

If it cannot change visible content, document why from source/contracts.

If needed, make its update result explicit rather than adding an arbitrary always-redraw loop.

## C3. Catalogue/error/status state

Exercise at least one fail-soft catalogue/error state transition and verify it appears/disappears without stale pixels.

## C4. Mode/profile-visible changes

Review mode/profile state transitions for any paths that can become visible asynchronously. Test the relevant ones.

## C5. Cache invalidation

Verify dirty rendering does not preserve stale cached activity/card/category surfaces after:

- resize;
- catalogue content change;
- locale/title-affecting state if supported;
- icon/package change in a development rescan scenario.

---

# 6. Phase D — pacing strategy comparison

Compare at least these two realistic strategies in a controlled local benchmark:

1. Pygame `Clock.tick()`-based pacing using the pre-performance behavior or an isolated equivalent;
2. current manual `time.sleep()` candidate pacing.

You may test an event-aware wait strategy too if it is simple and architecture-compatible, but do not introduce a new scheduler/framework merely for this gate.

Compare:

- idle CPU;
- active 30 FPS pacing stability;
- input responsiveness;
- timing jitter where practical;
- implementation complexity/failure modes.

Choose the simplest strategy supported by the measurements.

If manual `time.sleep()` wins, keep it and document why.

If `Clock.tick()` is equal/better, restore/use it without treating that as failure of the dirty-render optimization.

The dirty-redraw decision and frame-pacing decision are separate concerns.

---

# 7. Phase E — Costruiamo Ponti performance/correctness proof

The recent Activity optimization moved stable work out of the frame loop. Validate that independently.

Prove through source instrumentation/tests where practical that stable paths no longer repeatedly perform:

- bank image smoothscaling every frame;
- trampoline/goal scaling every frame;
- block icon scaling for an already-cached `(block_id, size)` pair;
- river/canyon full gradient regeneration every frame.

Then exercise real gameplay through Simulator and verify:

- placing bridge blocks still works;
- correct/incorrect block feedback remains correct;
- Flash traverses the bridge correctly;
- reaching the final bank completes exactly once;
- star/storage/event semantics remain correct;
- trampoline/failure behavior remains correct;
- next-level/victory transition still works.

Performance work must not alter gameplay semantics accidentally.

---

# 8. Tests

Add focused tests only where they enforce meaningful contracts.

Useful targets include:

- dirty invalidation after registry rescan;
- redraw invalidation on asynchronous visible-state updates;
- no redraw when truly idle;
- continuous redraw while launch animation is active;
- pacing helper behavior if pacing is factored cleanly;
- Costruiamo Ponti crossing-completes-once regression.

Do not write tests that merely assert private variable names or duplicate implementation line-by-line.

Run at minimum:

```bash
make validate
make visual-assets-check
PYTHONPATH=src pytest tests/test_launcher*.py tests/test_costruiamo_ponti_contract.py
```

Also run any newly added focused performance/redraw tests explicitly and report exact counts.

---

# 9. Evidence and report

Create:

`docs/reviews/performance/2026-08-22_launcher-pacing-dirty-redraw/` (archived; see git history)

Preserve the existing owner review there.

Add:

- `PERFORMANCE_REPORT.md`
- `performance-audit.json`
- `measurement-samples.json` or `.csv`
- `correctness-trace.json`

Include only a few screenshots if they materially prove dirty-state correctness, for example:

- package/catalogue state before rescan;
- visible state after rescan with no user event;
- one launch-animation state;
- one Costruiamo completion state.

Do not create a large decorative screenshot suite for a performance gate.

The report must clearly distinguish:

- measured result;
- inference;
- simulator/headless scope;
- untested physical-hardware claims.

---

# 10. Acceptance decision

Conclude with exactly one of:

- `PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTED`
- `PERFORMANCE_PACING_DIRTY_REDRAW_REQUIRES_OWNER_REVIEW`
- `PERFORMANCE_PACING_DIRTY_REDRAW_BLOCKED`

Acceptance requires all of the following:

- meaningful idle-work reduction demonstrated against baseline;
- no known stale-UI invalidation path;
- active launch motion remains smooth/correct;
- input responsiveness is not materially degraded;
- pacing choice is measurement-backed rather than premise-backed;
- Costruiamo Ponti performance changes preserve gameplay semantics;
- focused tests and normal validation pass.

---

# 11. Documentation sync

If and only if the gate reaches an acceptance-ready result, update the appropriate performance/runtime notes in:

- `HANDOVER.md`
- relevant launcher/runtime design documentation;
- `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` only insofar as the performance foundation changes the visual-workstream continuation state.

Also clean any stale checkpoint that still claims the generic discovery tooling or already-completed visual exercises are the current next action.

Do not start First-Party Visual Batch 2 in this same gate.

---

# 12. Transfer bundle and final reply

Create one compact root review bundle:

`GREIA_PERFORMANCE_REVIEW_PACING_DIRTY_REDRAW_2026-08-22.zip`

Include the performance review directory contents only.

Commit and push all accepted/fixed source, tests, reports and documentation to `origin/main`.

Final reply to the owner must contain only:

1. concise result/disposition;
2. key before/after measurements;
3. bugs found/fixed, especially dirty invalidation issues;
4. exact verification results;
5. exact review directory;
6. exact transfer ZIP path/name;
7. exact pushed commit SHA.

Do not paste this protocol back into chat.
