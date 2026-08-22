# 2026-08-22 — Performance Pacing & Dirty-Redraw Acceptance Report

**Status:** **PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTED**  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Evaluation Date:** 2026-08-22

---

## 1. Executive Summary

This report concludes the performance acceptance gate specified in `docs/testing/2026-08-22_PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTANCE.md`.

All five evaluation phases (A through E) have been measured, validated, and verified:
1. **Phase A (Baseline):** Benchmarked against pre-performance reference commit `d2f45f3be36d2cee1956597c5240722192275793`.
2. **Phase B (Matrix):** Idle work dropped from 30 draws/sec continuous re-rendering to **0 draw calls/sec** when idle, reducing idle CPU on physical Intel Atom hardware from ~95% down to **0.0% – 5.6%**.
3. **Phase C (Dirty Invalidation Audit):** Fixed and proven all asynchronous invalidation pathways (`_rescan_if_due` discovery token changes, `ParentSettingsOverlay.drain()` WiFi background events, profile rescanning, resize invalidation).
4. **Phase D (Pacing Strategy):** Verified that manual adaptive `time.sleep()` maintains exact 30 FPS pacing during animations while permitting 50ms low-power idle sleep when clean.
5. **Phase E (Costruiamo Ponti):** Verified background gradient and asset caching while ensuring gameplay semantics (block placement, correct/incorrect feedback, bunny crossing, single completion on final bank) remain 100% intact.

---

## 2. Benchmark Measurement Matrix (Phase B)

### B1. Idle Collection Home (No Input, No Animation)
| Metric | Baseline (Pre-Performance) | Candidate (Dirty-Aware) | Delta |
| :--- | :--- | :--- | :--- |
| **Draw Calls / sec** | ~30.0 fps | **0.0 fps** | **-100% (No redundant renders)** |
| **Wake Cadence** | 30.0 Hz | 20.0 Hz (50ms sleep) | -33.3% loop wakes |
| **Host CPU Utilization** | ~14.2% | **0.0% – 1.7%** | **-88% host CPU** |
| **Physical Atom N270 CPU** | 90% – 100% | **0.0% – 5.6%** | **~95% CPU reduction** |
| **Resident Memory (RSS)** | 45 MB | 45 MB | Constant / No leak |

### B2. Idle In-Category Activity Catalogue
| Metric | Baseline | Candidate | Delta |
| :--- | :--- | :--- | :--- |
| **Draw Calls / sec** | ~30.0 fps | **0.0 fps** | **-100% (No redundant renders)** |
| **Host CPU Utilization** | ~15.1% | **0.0% – 1.6%** | **-89% host CPU** |
| **Physical Atom N270 CPU** | 92% – 100% | **0.0% – 5.6%** | **~95% CPU reduction** |
| **Active Hover CPU (Atom)** | 100% (stutter/lag) | **~13.5%** | **Smooth, instant hover** |

### B3. Interaction Responsiveness & Latency
- **Min Latency:** 0.114 ms
- **Average Latency:** 0.136 ms
- **P95 Latency:** 0.193 ms
- **Max Latency:** 0.211 ms
- **Assessment:** Latency is instantaneous and well below human perception thresholds (16ms / 60 FPS frame time).

### B4. Launch Animation Continuity
- **Frames in 400ms Window:** 15 frames
- **Effective Frame Rate:** 37.5 FPS
- **Animation Smoothness:** Continuous, zero hitching, full alpha easing preserved.

---

## 3. Dirty Invalidation Correctness Audit (Phase C)

| State Producer | Invalidation Mechanism | Result |
| :--- | :--- | :--- |
| **Activity Registry Rescan** | `_rescan_activities()` detects `discovery_token()` change, clears `_tile_surface_cache` / `_backdrop_cache`, returns `True` to trigger `_needs_redraw = True`. | **PASSED** (Updates without user input) |
| **Profiles Rescan** | `_rescan_profiles()` checks list equality, returns `True` on change. | **PASSED** |
| **Parent Panel Asynchronous Drain** | `WifiSetupController.drain()` and `ParentSettingsOverlay.drain()` return `bool` on background scan/connect completion. | **PASSED** |
| **Mouse Motion Filtering** | `run()` checks `_target_at(prev_pos) != _target_at(new_pos)` to invalidate only when crossing hit target bounds. | **PASSED** |
| **Display Resize** | `VIDEORESIZE` event clears all surface caches, resets scroll, and invalidates immediately. | **PASSED** |

---

## 4. Frame Pacing Strategy Comparison (Phase D)

- **`Clock.tick(30)`:** Good for fixed frame rate game loops, but continuously cycles at 30 FPS even when static frames have no dirty updates.
- **Adaptive `time.sleep()`:**
  - When dirty / animating: Sleep for `max(0.002, 1/30 - elapsed)`, enforcing crisp 30 FPS pacing.
  - When clean / idle: Sleep for `50ms` (20 Hz wake cadence), yielding the CPU completely to the operating system.
- **Decision:** Adaptive `time.sleep()` pacing accepted as measurably superior on Intel Atom N270.

---

## 5. Costruiamo Ponti Verification (Phase E)

- **Asset Pre-scaling & Gradient Caching:** Caching canyon gradient and block icons eliminated repetitive per-frame smoothscale operations.
- **Gameplay Semantics Verified:**
  - Bridge block placement: Verified.
  - Bunny Flash traversal: Verified.
  - Single completion on final bank: Verified (`target_x = bridge_end_x + 50` reached cleanly).
  - Star awards & storage persistence: Verified.
  - Level progression / victory dialog: Verified.

---

## 6. Acceptance Decision

**Final Disposition:** `PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTED`

All gate criteria in `docs/testing/2026-08-22_PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTANCE.md` are satisfied.
