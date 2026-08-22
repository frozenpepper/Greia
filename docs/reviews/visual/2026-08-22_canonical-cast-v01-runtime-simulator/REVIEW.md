# Canonical Cast v0.1 — Runtime Simulator Acceptance Review

**Date:** 2026-08-22  
**Authority:** `docs/testing/2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md`  
**Evidence Classification:** `SIMULATOR VISUAL REVIEW`  
**Candidate Source:** `assets/visual/characters/canonical/v0.1/`  
**Runtime Renditions:** `assets/visual/runtime/v1/characters/` (30 PNGs)  

---

## 1. Executive Summary

This gate promotes Greia's six canonical mascots (**Lilli, Leo, Flash, Dani, Tito, Momo**) into stable source assets, compiles their 30 build-time runtime renditions (5 states each), integrates renderer-neutral semantic state and motion transforms into `greia_platform.scene_actor`, and proves the complete runtime integration via the real Greia Activity/Scene pipeline across 6 responsive viewports and fault-injection cases.

---

## 2. Core Gate Verification Results

### 2.1 Stable Source Promotion
- Promoted all 6 characters into `assets/visual/characters/canonical/v0.1/` with `catalog.toml`, `README.md`, `MOTION.md`, `source_master.svg`, 5 registered state SVGs, and authoring components.
- Historical Nino owl provenance documented; zero runtime aliasing.

### 2.2 Build-Time Runtime Renditions
- Declared all 6 characters and 5 variants (`default`, `blink`, `happy`, `surprised`, `sleepy`) in `assets/catalog/shared_visuals_v1.toml`.
- Built and validated all 30 PNG renditions (256×256) via `make visual-assets` and `make visual-assets-check`.

### 2.3 Semantic State & Motion Pipeline
- `greia_platform.scene_actor` supports typed enums `CharacterState` and `CharacterMotion`.
- Cheap whole-character translation (`idle_bounce`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway`) preserves grounded contact shadow geometry.
- `SceneNode.fallback_variant`: Missing non-default state renditions cleanly fall back once to `default` neutral without crashing or throwing tracebacks.

### 2.4 Activity Simulator Acceptance Matrix
- **11.1 Neutral Ensemble (1024×600):** All 6 characters rendered in harmonious lineup with correct aspect ratios, zero stretching, and grounded shadows (`01-ensemble.png`).
- **11.2 5 States Proof:** Verified all 5 states (`neutral`, `blink`, `happy`, `surprised`, `sleepy`) with zero registration drift (`02-five-states.png`).
- **11.3 Motion Proof:** Captured mid-hop (`03-happy-hop.png`), mid-wobble (`04-surprised-wobble.png`), and mid-sway (`05-sleepy-sway.png`).
- **11.4 Non-Default State Fallback:** Corrupted `flash_happy.png`; verified Flash fell back to `flash_neutral.png` cleanly (`08-state-fallback.png`).
- **11.5 Default Rendition Failure:** Corrupted `dani_neutral.png`; verified Activity caught `SceneRenderError` and displayed graceful fallback without crashing shell (`09-default-fallback.png`).
- **11.6 Motion Disabled:** Verified full ensemble static mode (`10-motion-disabled.png`).
- **12.0 Responsive Matrix:** Verified 6 viewports (1024×600 normal, 1024×600 large, 1280×800 normal, 1366×768 compact, 1920×1080 normal, 1111×700 normal).
- **13.0 Cache Sanity:** Observed 300 frames (10 seconds); cache entries settled into a bounded working set (8 entries out of max 32) with zero continuous raster churn.

---

## 3. What Remains Unproven
- Physical Acer/Raspberry Pi hardware touch-latency and thermal profiling (physical gate required for hardware signoff).
- Web canvas WebGL backend integration (future milestone).
