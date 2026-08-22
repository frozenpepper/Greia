# Launcher / Activity Pacing Performance Changes — Owner Review

**Date:** 2026-08-22  
**Status:** **PROMISING SOURCE CHANGES — PERFORMANCE ACCEPTANCE NOT YET CLOSED**

## Reviewed commits

- `b9953c77072e9ce2670387417a293ab256206d9a` — dirty-aware launcher presentation plus Costruiamo Ponti caching/pre-rendering work
- `11b7ba4209416665092fad12fe820e1de47973c9` — manual `time.sleep` frame pacing

## What looks good

The general direction of the first performance commit is sound:

- static launcher frames no longer need to be redrawn/flipped continuously when nothing visible changed;
- Costruiamo Ponti avoids repeated scaling of stable PNGs;
- block icon scaling is cached;
- stable world gradients are pre-rendered rather than rebuilt line-by-line every frame;
- the crossing correctness fix is useful independently of the performance work.

These are appropriate optimizations for Greia's low-resource target philosophy because they remove unnecessary work rather than lowering visual quality.

## What is not yet accepted

### 1. The `Clock.tick()` premise is not established

The follow-up commit describes `pygame.time.Clock.tick()` as busy-spin pacing. That is not a safe premise: Pygame distinguishes ordinary `tick()` from the explicitly CPU-hungry `tick_busy_loop()` path.

Manual `time.sleep()` may still be the better choice on Greia's target environment, but that must be demonstrated by measurements rather than assumed from the API name.

### 2. Dirty redraw introduces invalidation correctness risk

`GreiaLauncherPresentation.run()` now redraws only when `_needs_redraw`, launch animation, or first-frame state says it should.

That is a good optimization only if every visible asynchronous change invalidates the frame.

Current source calls paths such as `_rescan_if_due()` and parent-panel draining without an obvious dirty/change signal. A parent-installed Activity appearing, asynchronous parent-panel state changing, or another non-input-visible transition could therefore leave stale pixels until a later user event.

This must be tested explicitly and repaired through clear invalidation contracts where necessary.

### 3. No owner-grade performance evidence yet

Source-level plausibility is not enough for performance claims. We need before/after measurements covering idle Shell load, active animation, event responsiveness, frame pacing and at least one representative Activity.

## Disposition

Do **not** revert the work merely because it is unaccepted. Keep it as the current candidate implementation and run the focused acceptance gate.

No broad additional performance refactor should begin until this gate establishes:

1. that the dirty-aware renderer actually reduces idle work;
2. that all visible state changes invalidate correctly;
3. that the chosen pacing mechanism is measurably appropriate;
4. that interaction latency and animation smoothness remain acceptable;
5. that the Activity-side caching improvements do not change gameplay semantics.
