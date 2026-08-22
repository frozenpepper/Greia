# Canonical Cast v0.1 — Final Capture Integrity & Acceptance Recheck

## Executive Summary
This document and its packaged visual evidence close the canonical cast v0.1 runtime and simulator acceptance gate following the owner review directives in `docs/reviews/visual/2026-08-22_canonical-cast-v01-runtime-recheck/OWNER_REVIEW_CAPTURE_INTEGRITY.md`.

All 8 blocking findings from the previous capture pass have been addressed through a strict 3-phase execution model that completely isolates normal baseline captures from injected fault states, adds on-screen self-proving diagnostic readouts, tracks node fallback statistics in `PygameSceneRenderer`, and validates responsive interface-size configurations across simulator sessions.

---

## 3-Phase Execution Architecture

```
+-----------------------------------------------------------------------------------+
| PHASE A: Clean Normal Evidence (All 30 Visual Assets Healthy)                     |
| - 01-full-fixture-normal.png (6-character ensemble, shadows, Fallback: NO)        |
| - 02-five-states.png (5-row composite: Neutral, Blink, Happy, Surprised, Sleepy)  |
| - 03-happy-hop.png (Hero Flash, Happy state, Happy Hop motion)                    |
| - 04-surprised-wobble.png (Hero Dani, Surprised state, Surprised Wobble motion)     |
| - 05-sleepy-sway.png (Hero Momo, Sleepy state, Sleepy Sway motion)                |
| - 08-resp-1024x600-normal.png (1024x600 viewport, UI: NORMAL)                    |
| - 09-resp-1024x600-large.png (1024x600 viewport, UI: LARGE)                      |
| - 10-resp-1366x768-compact.png (1366x768 viewport, UI: COMPACT, contained)        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| PHASE B: Isolated Non-Default Fallback Test                                       |
| - Injected fault: flash_happy.png corrupted with invalid byte header              |
| - Capture: 06-state-fallback.png                                                  |
| - Diagnostic readout: Req: happy | Rendered: default | Fallback: YES (default)    |
| - Character displays Flash default/neutral rendition without errors               |
| - Immediate rebuild & validation: Catalogue restored to 100% clean                |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| PHASE C: Isolated Required Default Failure Test                                   |
| - Injected fault: dani_neutral.png corrupted with invalid byte header             |
| - Capture: 07-default-failure.png                                                 |
| - SceneRenderError caught by Activity loop; renders Activity Visual Safe Fallback |
|   Mode error container; Developer chrome, title, and buttons remain intact        |
| - Zero unhandled Python crashes                                                   |
| - Immediate rebuild & validation: Catalogue restored to 100% clean                |
+-----------------------------------------------------------------------------------+
```

---

## Resolution Matrix for Owner Review Directives

| # | Owner Review Finding | Root Cause Identified | Resolution Implemented | Evidence File |
|---|----------------------|-----------------------|------------------------|---------------|
| 1 | `01-full-fixture-normal.png` was a failure state containing Dani required-default fallback | Cross-scenario pollution from earlier fault injection | Replaced sequential runs with 3-phase isolation; Phase A starts with fully verified healthy assets | `01-full-fixture-normal.png` |
| 2 | `02-five-states.png` contaminated with fallback screens | Five-states composite was captured during an active fault injection | Isolated in Phase A; captures all 6 canonical characters across all 5 states cleanly | `02-five-states.png` |
| 3 | `04-surprised-wobble.png` showed State: HAPPY with Motion: SURPRISED_WOBBLE | Semantic state button was set to HAPPY instead of SURPRISED | Directly bound state key `S` (SURPRISED) and motion key `W` (WOBBLE); verified in readout | `04-surprised-wobble.png` |
| 4 | `05-sleepy-sway.png` showed State: HAPPY with Motion: SLEEPY_SWAY | Semantic state button was set to HAPPY instead of SLEEPY | Directly bound state key `Z` (SLEEPY) and motion key `Y` (SWAY); verified in readout | `05-sleepy-sway.png` |
| 5 | `06-state-fallback.png` not self-proving | No on-screen indication of requested vs rendered variant or fallback flag | Added two-line developer diagnostic readout on fixture canvas displaying `Req: happy \| Rendered: default \| Fallback: YES (default)` | `06-state-fallback.png` |
| 6 | `07-default-failure.png` showed Greia Starting... surface | Screen captured before Activity process reached its safe fallback surface | Captured when Activity loop caught `SceneRenderError` and rendered `Activity Visual Safe Fallback Mode` box | `07-default-failure.png` |
| 7 | Responsive captures reported `UI: NORMAL` instead of `LARGE` and `COMPACT` | Simulator workspace profile preferences were not propagated to launcher environment | Set profile `interface_size` via `workspace.set_interface_size()` and verified in readout | `09-resp-1024x600-large.png`, `10-resp-1366x768-compact.png` |
| 8 | Port 8767 / child shell process collision | Lingering background simulator processes intercepted HTTP commands | Added process termination sweeps (`kill_all_simulator_procs`) before every session | All captures |

---

## Evidence Manifest

### 1. `01-full-fixture-normal.png`
- **Resolution:** 1024x600
- **Mode:** Ensemble (6 characters: Lilli, Leo, Flash, Dani, Tito, Momo)
- **State:** `NEUTRAL` | **Motion:** `IDLE_BOUNCE` | **UI:** `NORMAL`
- **Diagnostic Header:** `Req: default | Rendered: default | Fallback: NO | Canvas: 1024x600 | Screen: 1024x600`
- **Validation:** Clean ground, contact shadows, zero fallback boxes or errors.

### 2. `02-five-states.png`
- **Resolution:** 1024x3000 (5 vertically stacked 1024x600 frames)
- **Rows:**
  - Row 1: `NEUTRAL` (`Req: default | Rendered: default | Fallback: NO`)
  - Row 2: `BLINK` (`Req: blink | Rendered: blink | Fallback: NO`)
  - Row 3: `HAPPY` (`Req: happy | Rendered: happy | Fallback: NO`)
  - Row 4: `SURPRISED` (`Req: surprised | Rendered: surprised | Fallback: NO`)
  - Row 5: `SLEEPY` (`Req: sleepy | Rendered: sleepy | Fallback: NO`)
- **Validation:** Clear facial state transitions across all 6 characters with zero fallbacks.

### 3. `03-happy-hop.png`
- **Character:** `character.flash` (White rabbit, pink ear inners, heart lightning chest emblem)
- **State:** `HAPPY` | **Motion:** `HAPPY_HOP` | **UI:** `NORMAL`
- **Diagnostic Header:** `Req: happy | Rendered: happy | Fallback: NO`
- **Validation:** Hero Flash lifted in mid-hop with dynamic ground shadow.

### 4. `04-surprised-wobble.png`
- **Character:** `character.dani` (Robot, blue head, cream screen, antenna)
- **State:** `SURPRISED` | **Motion:** `SURPRISED_WOBBLE` | **UI:** `NORMAL`
- **Diagnostic Header:** `Req: surprised | Rendered: surprised | Fallback: NO`
- **Validation:** Hero Dani with open round mouth and wide eyes, wobbling horizontally.

### 5. `05-sleepy-sway.png`
- **Character:** `character.momo` (Purple friendly monster, dual antennae)
- **State:** `SLEEPY` | **Motion:** `SLEEPY_SWAY` | **UI:** `NORMAL`
- **Diagnostic Header:** `Req: sleepy | Rendered: sleepy | Fallback: NO`
- **Validation:** Hero Momo with closed serene eyes and gentle smile, swaying horizontally.

### 6. `06-state-fallback.png`
- **Character:** `character.flash`
- **State:** `HAPPY` (injected corrupt `flash_happy.png`) | **Motion:** `NONE` (static)
- **Diagnostic Header:** `Req: happy | Rendered: default | Fallback: YES (default)`
- **Validation:** Flash renders default (neutral) art cleanly; `PygameSceneRenderer` logs fallback and increments `fallback_nodes`.

### 7. `07-default-failure.png`
- **Character:** `character.dani`
- **State:** `NEUTRAL` (injected corrupt `dani_neutral.png`)
- **Visual Surface:** `Activity Visual Safe Fallback Mode` red-bordered box displaying `Required rendition failed: required scene visual failed: canonical_cast_showcase/dani.body (character.dani/default)`
- **Validation:** Fixture controls and Home button remain active and responsive without Python crashes.

### 8. `08-resp-1024x600-normal.png`
- **Resolution:** 1024x600 | **UI Size:** `NORMAL`
- **Diagnostic Header:** `UI: NORMAL | Canvas: 1024x600 | Screen: 1024x600`
- **Validation:** Standard baseline 1:1 scale reference.

### 9. `09-resp-1024x600-large.png`
- **Character:** `character.leo` (Owl with teal glasses)
- **Resolution:** 1024x600 | **UI Size:** `LARGE`
- **Diagnostic Header:** `UI: LARGE | Canvas: 1024x600 | Screen: 1024x600`
- **Validation:** Proves active profile `interface_size = large` setting.

### 10. `10-resp-1366x768-compact.png`
- **Resolution:** 1366x768 | **UI Size:** `COMPACT`
- **Diagnostic Header:** `UI: COMPACT | Canvas: 1024x600 | Screen: 1366x768`
- **Validation:** 1366x768 outer viewport with centered 1024x600 pillarbox container.

---

## Technical Audit & Verification Results

1. **Asset Integrity Check:**
   `make visual-assets-check` passed across all 30 PNG renditions.
2. **Automated Unit & Platform Tests:**
   `PYTHONPATH=src pytest tests/test_scene*.py tests/test_visual*.py` passed with 100% success.
3. **Structured Simulator Trace:**
   All 10 capture scenarios recorded in `simulator-trace.json` with matching PID, timestamps, viewport, and fallback flags.
