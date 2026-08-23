# Greia Performance Best Practices

**Status:** living derived engineering manual
**Audience:** maintainers, coding agents, reviewers, Activity authors
**Authority:** subordinate to accepted ADRs, `AGENTS.md` non-negotiables and `docs/engineering/ENGINEERING_FOUNDATIONS.md`. Exact implemented APIs/limits remain owned by source declarations. This document collects **measured** practices, patterns and case studies; it never invents contracts.
**Founded:** 2026-08-23 (launcher hover-transition tranche)

---

## 1. Purpose and growth model

Greia targets an extreme low-resource appliance floor (first-generation Acer Aspire One class: ~1 GHz single-core Atom, software-rendered Pygame/SDL, 1024×600, ≤1 GiB RAM). Performance is a correctness concern on this floor, not a nicety.

This document is the single accumulating home for:

- the measured device cost model;
- repeatable optimization principles and patterns;
- the measurement instruments and evidence discipline;
- per-tranche case studies (appended, never rewritten);
- the Activity-facing rules destined for the authoring skill.

Growth rule: after every substantive performance tranche, **append** a case study, refresh the cost model/principles if measurements changed them, and keep the Activity-rules section aligned so the authoring skill can consume it directly.

---

## 2. Evidence discipline

### 2.1 Measure first — no folklore

Do not optimize by intuition, desktop experience or convention. The pacing-gate correction is canonical precedent: `pygame.time.Clock.tick()` was assumed to busy-spin; it does not (`tick_busy_loop()` exists separately). Every pacing/caching decision must be justified by measurement on representative hardware.

### 2.2 Classify evidence scope honestly

Use the repository evidence vocabulary. For performance work specifically:

| Scope | Establishes | Does not establish |
|---|---|---|
| Desktop/headless timing | relative regressions between code states | Acer/Pi behavior |
| Simulator | semantic contracts over synthetic HAL facts | memory/CPU/display-backend behavior |
| Physical (named machine + SHA) | real user-visible frame/CPU/memory behavior | R7 backend closure by itself |

A physical claim must name the machine, connection, source SHA and measurement mechanism, and belongs in `HANDOVER.md`, the active-plan ledger, or a dated `docs/reviews/performance/<date>_<topic>/` report.

### 2.3 Instruments

Current owned instruments:

```text
tools/profile_launcher_draw.py      # launcher draw-path phase profiler (SDL dummy video)
                                    # phases: A background, B steady cached frame,
                                    #         C hover transition, D full rebuild
```

Established ad-hoc protocol for on-device process-CPU probes (used 2026-08-23; formalize into `docs/testing/*` if reused):

```text
sample /proc/<pid>/stat utime+stime deltas at 1 Hz  → per-second CPU%
drive input via greia-devctl mousemove/click        → reproduce interaction phases
greia-devctl screenshot                              → visual correctness after each phase
```

Minimum reporting standard for a performance tranche: before/after ms-per-frame or CPU% for the named phases, RSS sanity, plus a pixel-correctness argument (see §4.12).

---

## 3. Measured device cost model

Measured on the reference Acer Aspire One (`legacy-x86-i686` developer image, Debian bookworm i386, pygame/SDL software rendering), 2026-08-23, launcher at 1024×600. Values are order-of-magnitude anchors for reasoning, not precise constants; re-measure when the display backend (R7) changes.

| Operation class | Measured magnitude | Notes |
|---|---|---|
| Opaque full-screen blit/fill (1024×600 RGB) | ~0.5–1 ms | cheap; safe per frame |
| Steady cached scene frame + flip | ~3.5 ms | background + one opaque blit + cursor + flip |
| Alpha (per-pixel) blend, converted surfaces | ~50–150 ns/px | scales with **blended area**, not draw count |
| Large RGBA panel blend (~1000×760) | ~100 ms | the 2026-08-23 dominant cost |
| Full-scene rebuild, pre-backdrop era | ~191 ms (≈5 fps) | caused visible hover stutter |
| Unconverted-surface blits | generic slow path | always convert once at cache time |
| `smoothscale` of large PNG | tens of ms | never per frame; cache by size |
| Idle poll loop (125 Hz wake + event pump) | ~10% of one core | relaxed cadence cuts this proportionally |

Consequences used throughout Greia rendering code:

1. **Blended pixels are the currency.** An alpha-blit costs roughly two orders of magnitude more per pixel than an opaque copy. Design frames around minimizing blended area, not call counts.
2. **Full-screen opaque composition is nearly free** compared with blending even one large RGBA artwork onto it.
3. **Idle cost is a duty cycle**: wake cadence × per-wake work. Both are tunable without touching frame quality.

---

## 4. Optimization principles

These are numbered so tranches and reviews can reference them (e.g., “applies P4/P5”).

### P1 — Measure before and after; pick the biggest measured cost

Profile the actual phase the user experiences (hover, launch, page flip), not synthetic microbenchmarks alone. Fix costs largest-first; stop when user-visible smoothness is reached rather than chasing micro-seconds.

### P2 — Minimize per-pixel-alpha area per frame

Prefer opaque surfaces for anything static and large (backdrops, panels, cards' final pixels). Reserve alpha blending for genuinely transient/small elements (cursor, floating pills, soft shadows). When a blended element is stable, bake it into something opaque.

### P3 — Convert decoded surfaces exactly once

`pygame.image.load()` returns unconverted surfaces that hit pygame’s generic (slow) blit path forever unless converted. Convert at cache-insert time via the injected converter seam:

```text
PygameVisualSurfaceCache(..., display_converter=pygame_display_converter())
# owner: src/greia_platform/pygame_visual_assets.py
```

Provider-free consumers (tests) pass nothing; the failure mode is graceful (unconverted fallback).

### P4 — Pre-composite static scenes into opaque backdrops

Compose theme background + wallpaper + large shared artwork into **one opaque surface**, cached by a complete key (theme identity, wallpaper identity+mtime, geometry, size), then present it with a single opaque blit. Example owner: `_draw_shared_shell_panel` in `src/greia_launcher/shared_ui_presentation.py`.

Rules:

- the key must include every input that can change pixels (colors, wallpaper path **and mtime**, panel geometry, size);
- keep the backdrop cache bounded (LRU);
- fail-soft: if any ingredient is unavailable, fall back to plain fill rather than disabling the screen.

### P5 — Separate static cache keys from dynamic state; repair incrementally

An all-or-nothing scene cache key that includes pointer hover forces a full rebuild on every hover change. Split it:

- **static part**: profile, category/page, selection, theme colors, size, locale, error state, launching-id;
- **dynamic part**: hover signature, quantized animation tick.

On dynamic-only changes, restore the affected regions **from the backdrop** (opaque copy) and redraw only those elements. Fall back to the full rebuild whenever anything exceeds the repaired class (chrome hover, missing backdrop, geometry mismatch) — the fast path is an accelerator, never a correctness dependency.

Restore margins must cover every extent the dynamic states can reach (padding + hover lift/scale + bounded wiggle/bounce amplitudes), while staying inside neighboring transparent padding so neighbors’ visible pixels are untouched.

### P6 — Cache bounds must fit the real working set

An LRU smaller than the working set thrashes: every miss re-decodes/re-scales (tens of ms each). Size bounds from measured usage (launcher shared-visual cache: 96 entries after measuring the chip/card/portal/shadow population), and keep `max_surface_pixels`-style caps so bounds cannot explode memory. Prefer shared `BoundedCache`.

### P7 — Nothing per-frame from these classes

Never inside a frame/event loop:

- image decode or `smoothscale`;
- uncached font construction or text render;
- new Surface allocation where a cached one fits;
- gradient/pattern regeneration for static content;
- filesystem stat/token checks without throttling (theme tokens: 0.25 s cadence);
- device/controller discovery or enumeration;
- storage writes (autosave belongs on idle boundaries).

Each violation class already has a canonical owner/pattern in the tree; reuse it instead of solving locally.

### P8 — Pre-render stable animation stages; cache transforms by state

Aquarium precedent: bake static day/night backgrounds once (`_BG_CACHE`) and cache directional scaled sprites keyed `(asset, w, h, facing)` (`_SCALE_CACHE`). Bridge-game precedent: pre-scale banks/trampolines/goal, cache block icons by `(id, size)`. If a stage cannot change during play, render it once.

### P9 — Render on invalidation; pace the idle loop adaptively

Input-driven rendering with dirty flags beats continuous repaint. Then tune duty cycle: quick polls immediately after input for imperceptible latency, relaxed sleep when quiet (launcher: 8 ms → 40 ms after 1 s). Quantize animation time (tick = elapsed*60) so animated frames remain cacheable.

### P10 — Every cache has an explicit invalidation story

Resize, theme/wallpaper change, locale change, catalogue rescan and profile switch must clear or re-key affected caches in the same tranche that adds the cache. A cache without an invalidation path is a stale-pixel bug, not an optimization.

### P11 — Fail soft, degrade gracefully

Optional artwork/effects wrap their lookups in typed error handling and disable only themselves (`*_disabled` flags) on failure, leaving the proven primitive renderer live. Performance features follow the same rule: the fast path may bail out to the slow correct path at any time.

### P12 — Prove optimizations pixel-equivalent

Any caching/repair optimization needs a regression test comparing its output against the naive path (e.g., forced full rebuild) under identical inputs — including a frozen clock for animation-phase determinism. See `tests/test_launcher_hover_scene_performance.py`.

### P13 — Hot loops stay allocation-free and math-driven

Motion samples are pure dataclass math (`ui_motion.py`: `HoverMotion`, `LaunchMotion`) with bounded envelopes settling exactly to neutral. No retained animation frameworks, no per-frame closures/tuples churn beyond necessity.

### P14 — Respect the interaction latency budget while saving CPU

Low idle CPU must not cost perceptible input lag. Previously accepted tolerance: interaction visible well under ~50 ms. Current adaptive scheme adds ≤40 ms worst-case after quiet periods. Re-validate against this budget when changing pacing.

---

## 5. Case studies (append-only)

### 2026-08-23 — Launcher hover-transition elimination (commit `68899e9`)

- **Symptom:** moving the pointer over icons dropped the Shell to ~5 fps on the Acer.
- **Diagnosis:** `tools/profile_launcher_draw.py` + `/proc` CPU probes: hover transitions rebuilt the whole 1024×600 scene (189.6 ms), dominated by the unconverted RGBA panel blend (~104 ms) and six card blends; hover sat inside the monolithic scene cache key.
- **Fixes:** P3 (converter + entry bound 12→96), P4 (scene backdrop), P5 (static/dynamic split + tile repair), P9/P14 (adaptive pacing), badge overlay restored from backdrop (fixes wallpaper artifact class).
- **Result:** hover 26.6 ms (37.6 fps); full rebuild 81.8 ms; steady 3.34 ms; idle CPU ~11%→~6%; sweep CPU ~32%→~16%; RSS unchanged (~153 MB). Verified visually on device; no ghosting.
- **Tests:** `tests/test_launcher_hover_scene_performance.py` (pixel equivalence, frozen-clock determinism).

### 2026-08-22 — Launcher pacing & dirty-redraw gate (accepted)

- Dirty-aware launcher rendering; replaced unconditional redraw with event-driven invalidation plus verified async invalidation paths (rescan, parent-panel drain). Idle draw calls 30 fps → 0; physical idle CPU ~95% → ~0–6%. Protocol: `docs/testing/2026-08-22_PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTANCE.md`; includes the folklore correction (§2.1).

### 2026-08-22 — First-party Activity hot-loop cleanups (Acquario Magico, Costruiamo Ponti)

- Acquario: pre-rendered ocean/abyss backgrounds (`_BG_CACHE`), bidirectional scaled-sprite cache (`_SCALE_CACHE`) removing per-frame flips/allocations (<0.15 ms background render on Atom).
- Ponti: moved bank/trampoline/goal scaling and river gradient generation out of the frame loop; block-icon cache by `(block_id, size)`; gameplay semantics protected by contract tests (P8 + P12 pattern).

---

## 6. Activity-facing rules (skill-bound)

Activities run inside the same supervised runtime and share the same hardware floor. The following rules are the Activity-authored subset of the principles above and are the intended source for extending `skills/greia-activity-authoring` (see §7). Until integrated there, treat this section as advisory for reviewers and authoritative direction for new first-party Activities.

Frame-loop prohibitions (mirror P7):

1. decode/load images, construct fonts, or render text without caches;
2. create Surfaces per frame (including overlays/gradient fills) — pre-render at load;
3. rescale/flip sprites per frame — cache by `(asset, size, orientation/state)`;
4. regenerate static scenery per frame — bake backgrounds once;
5. perform storage writes, package scans, or filesystem walks mid-frame — autosave on idle/level boundaries through Greia Storage only.

Required patterns:

6. dirty-flag/event-driven redraw; sleep or wait when nothing changed (P9);
7. bounded math animations sampled from monotonic time; settle exactly to neutral (P13);
8. explicit cache bounds + invalidation on resize/theme/locale (P6/P10);
9. target budgets: smooth gameplay ≈30 fps on the Atom-class floor; added input latency ≤50 ms (P14); idle CPU near zero when paused/static;
10. use platform helpers (`BoundedCache`, `ui_motion`, `pygame_effects` cached shadows, `activity_ui` metrics, `PygameVisualSurfaceCache` where shared visuals apply) instead of private reimplementations — parallel copies are forbidden by engineering foundations.

Measurement expectations for Activity tranches: headless simulator timings are diagnostics; claims about device behavior need the named-hardware protocol (§2.2), and semantic regressions need contract tests like the Ponti crossing-once test.

---

## 7. Authoring-skill integration plan (roadmap)

The Activity authoring skill (`skills/greia-activity-authoring/SKILL.md` + `CORE.md`) currently contains no dedicated performance contract. Planned integration, to execute as its own reviewed tranche (do not edit the skill casually in passing):

1. Add a `PERFORMANCE.md` companion to the skill that restates §6 in author workflow form, referencing this document for rationale instead of duplicating it.
2. Extend `CORE.md` frame-loop guidance with the prohibitions/patterns checklist and the budget numbers.
3. Add reviewer/validation hooks: a packaging-time static scan for obvious per-frame offenders (e.g., `pygame.image.load` outside load paths, `pygame.transform.smoothscale` inside loop constructs) is a candidate tooling task; decide scope there, not here.
4. After the first skill tranche lands, move §6’s normative home to the skill and leave a pointer here.

---

## 8. Maintenance rules

- Append case studies; never rewrite earlier ones (matches the repository append-only history rule).
- When a tranche invalidates a cost-model number or principle, update §3/§4 and cite the tranche in the change.
- Source owners referenced here (e.g., `pygame_visual_assets.py`, `shared_ui_presentation.py`, `ui_motion.py`) are declared in `docs/DOCUMENTATION.md`; if ownership moves, update both files in the same tranche.
- This manual does not replace `ENGINEERING_FOUNDATIONS.md` §5 (low-resource rules); it operationalizes them with measurements and patterns.
