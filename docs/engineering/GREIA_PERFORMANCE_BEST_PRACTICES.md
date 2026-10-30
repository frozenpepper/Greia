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
- the Activity-facing rules consumed by the Activity authoring skill.

Growth rule: after every substantive performance tranche, **append** a case study, refresh the cost model/principles if measurements changed them, and keep the Activity-facing summary aligned with `skills/greia-activity-authoring/ENGINEERING.md`.

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

A physical claim must name the machine, connection, source SHA and measurement mechanism, and belongs in `HANDOVER.md`, the active-plan ledger, or a dated `docs/reviews/performance/<date>_<topic>/` (archived; see git history) report.

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
| `smoothscale` of large PNG | tens of ms | Activities never per frame; cache by size. The platform canvas resamples once per full frame only when the display is scaled below the hi-res threshold (or hi-res is off); with hi-res active it is 1:1; pointer/region updates never resample the frame |
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

### 2026-08-23 — Parent Settings overlay: dead text input + UI-thread stalls (commit `3c3e91f`)

- **Symptoms:** the chord-opened (hold S+T) Parent Settings panel was "super slow" and its password field accepted no characters.
- **Diagnosis:** two independent defect classes:
  - *Input:* SDL delivers `TEXTINPUT` only while `pygame.key.start_text_input()` is active; nothing activated it for parent-panel mode, so typed characters never arrived (KEYDOWN-only keys like Enter/Backspace still worked — classic mixed-delivery symptom).
  - *Stalls:* `SshMaintenanceProvider.status()` shells out to systemctl twice plus a route probe; the Info tab called it **every frame**, the SSH tab blocked mid-draw every ~2 s and `drain()` double-polled. Additionally the full-screen translucent dim was alpha-blended on every redraw (~100 ms class per keystroke), and the Audio tab parsed its TOML store per frame.
- **Fixes:** centralized `_enter_parent_panel`/`_exit_parent_panel` transitions managing text input + event clearing (P10-style explicit lifecycle); SSH status moved to a worker thread + queue consumed by `drain()` with cached-snapshot rendering and honest placeholders (Wi-Fi controller pattern reused); dim composited once per picker-state change into an opaque surface (`dim_surface()` + `draw_backdrop=False`, P4/P2); mic gain served from a throttled cache (P7).
- **Result (physical Acer):** chord → auth dialog → typed password dots visible → unlock → all five tabs render; Info/SSH tabs idle at **6–9 % launcher CPU** (previously subprocess-per-frame); close restores the picker cleanly.
- **Lesson:** input delivery and rendering cost live at different layers — a field can render correctly yet receive no events; verify both pipelines when a widget "stops working". Subprocess/status calls are per-second background work, never per-frame work (P7).

### 2026-08-22 — Launcher pacing & dirty-redraw gate (accepted)

- Dirty-aware launcher rendering; replaced unconditional redraw with event-driven invalidation plus verified async invalidation paths (rescan, parent-panel drain). Idle draw calls 30 fps → 0; physical idle CPU ~95% → ~0–6%. Protocol: `docs/testing/2026-08-22_PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTANCE.md`; includes the folklore correction (§2.1).

### 2026-08-22 — First-party Activity hot-loop cleanups (Acquario Magico, Costruiamo Ponti)

- Acquario: pre-rendered ocean/abyss backgrounds (`_BG_CACHE`), bidirectional scaled-sprite cache (`_SCALE_CACHE`) removing per-frame flips/allocations (<0.15 ms background render on Atom).
- Ponti: moved bank/trampoline/goal scaling and river gradient generation out of the frame loop; block-icon cache by `(block_id, size)`; gameplay semantics protected by contract tests (P8 + P12 pattern).

---

## 6. Activity-facing rules

The canonical practical Activity implementation rules now live in:

```text
skills/greia-activity-authoring/ENGINEERING.md
```

That skill companion is mandatory for new/substantively changed first-party Activity implementation and is indexed by `skills/greia-activity-authoring/SKILL.md`.

The measured rationale remains here. The synchronized Activity subset is:

1. no image decode/load, uncached font construction/stable text rendering, reusable sprite scale/flip, large unchanged Surface allocation, static scenery regeneration, filesystem/device/subprocess/config parsing or durable storage writes in normal frame/event hot paths;
2. pre-render static scene layers and cache reusable transforms by semantic state;
3. use dirty/invalidation-driven redraw for static/turn-based presentation where practical;
4. keep every cache bounded with a complete key and explicit invalidation/re-key path;
5. make optimized paths fail-soft with a correct fallback;
6. use bounded monotonic-time animations that settle exactly to a neutral/end state;
7. test visual fast paths against the correct/naive path and protect gameplay semantics with independent contract tests;
8. working targets remain ~30 fps on Atom-class hardware, <=50 ms added input latency and near-zero idle CPU for static/paused Activities where architecture permits;
9. reuse shared Greia resource/cache/motion/UI primitives rather than copying local infrastructure;
10. desktop/simulator timing remains diagnostic; named hardware + exact SHA is required for physical performance claims.

The Activity engineering companion additionally owns code-structure/OOP/decomposition rules because performance and maintainability share the same ownership/reuse concerns.

---

## 7. Activity-skill integration status

**Completed 2026-08-23.**

The integration tranche created:

```text
skills/greia-activity-authoring/ENGINEERING.md
```

and updated the Activity skill index so implementation work must consume it.

The completed integration deliberately chose a dedicated engineering companion rather than bloating `CORE.md` with repeated performance rationale. `CORE.md` remains the general Activity contract; `ENGINEERING.md` owns practical code structure, OOP/polymorphism, `main.py` decomposition, hot-loop rules, performance targets, cache/invalidation discipline, comments/docstrings and engineering review gates.

Potential future tooling remains separate from the documentation contract. A static linter for obvious hot-loop offenders may be useful, but it must be designed against real code structure and must not substitute simplistic regex enforcement for review/profiling.

---

## 8. Maintenance rules

- Append case studies; never rewrite earlier ones (matches the repository append-only history rule).
- When a tranche invalidates a cost-model number or principle, update §3/§4 and cite the tranche in the change.
- Keep §6 aligned with `skills/greia-activity-authoring/ENGINEERING.md` whenever Activity-facing performance guidance changes.
- Source owners referenced here (e.g., `pygame_visual_assets.py`, `shared_ui_presentation.py`, `ui_motion.py`) are declared in `docs/DOCUMENTATION.md`; if ownership moves, update both files in the same tranche.
- This manual does not replace `ENGINEERING_FOUNDATIONS.md` §5 (low-resource rules); it operationalizes them with measurements and patterns.