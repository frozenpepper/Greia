# Owner Recheck: Canonical Cast v0.1 Runtime Acceptance & Simulator Provenance

**Date:** 2026-08-22  
**Status:** ACCEPTANCE RECHECK COMPLETE — READY FOR OWNER REVIEW  
**Scope:** Canonical Cast v0.1 Runtime Acceptance, Bounded Negative Caching, Deliberate Fallback Screens, Authentic Simulator Provenance, Responsive Viewports.

---

## 1. Executive Summary & Resolution of Owner Review Blockers

All 6 issues identified in the Owner Review (`docs/reviews/visual/2026-08-22_canonical-cast-v01-runtime-simulator/OWNER_REVIEW.md`) have been systematically resolved and verified against the live Greia Activity Simulator:

1. **Bounded Failed-Rendition Memory Implemented & Verified:**
   - Added `BoundedCache[tuple[str, str, int, int], bool]` (max 64 entries) `_failed_renditions` to `PygameSceneRenderer`.
   - On the first failure of any non-default or default rendition, the failure is recorded.
   - Subsequent frames bypass `visual_cache.get()` for that failed key, routing directly to `fallback_variant` without disk reads or exception storms.
   - `renderer.clear()` resets `_failed_renditions` and `visual_cache` cleanly.

2. **Genuine Cold Required Default Rendition Failure Demonstrated:**
   - Injected cold corrupt-byte fault into `dani_neutral.png` with Dani selected in neutral/static mode.
   - Captured `07-default-failure.png` demonstrating the Activity's deliberate `Activity Visual Safe Fallback Mode` screen:
     `Required rendition failed: required scene visual failed: canonical_cast_showcase/dani.body (character.dani/default)`
   - No Python tracebacks, unhandled exceptions, or crash dialogs exposed to the child.

3. **Authentic Activity Simulator Provenance & Developer UI Controls:**
   - All review screenshots are full child-facing surfaces captured through the real simulator remote bridge (`http://127.0.0.1:8767/api/frame`).
   - Developer UI controls (Title, Status with mode/state/motion/resolution, Character selector buttons, View mode toggle, Motion toggle, State buttons, and Motion buttons) are rendered directly on the `PygameReferenceCanvas`.

4. **Safe-Area & Reference Canvas Conformance:**
   - Showcase fixture uses `PygameReferenceCanvas(screen, ReferenceCanvasSpec(width=1024, height=600, fit=CanvasFitMode.CONTAIN))`.
   - The top-left 80×80 Home icon area is completely clear of interactive controls and text.
   - Cast baseline, grounded contact shadows, and meadow strip remain perfectly anchored.

5. **Living Documentation Authorities Synchronized:**
   - `GREIA_CANONICAL_CAST_SYSTEM.md`, `GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`, `GREIA_ART_GRAPHICS_SYSTEM.md` (obsolete Nino removed), `2026-08-21_BASE_ART_PACK_REAUTHORING.md`, `2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`, `GREIA_VISUAL_SYSTEM_RESUME.md`, and `HANDOVER.md` are aligned with the 6 canonical characters and 5 runtime states.

6. **Clean Narrow Transfer Bundle:**
   - `GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_RUNTIME_RECHECK_2026-08-22.zip` contains strictly the 10 curated PNGs + `OWNER_RECHECK.md` + `runtime-audit.json` + `simulator-trace.json`.

---

## 2. Curated Review Evidence Directory

| File | Viewport / Setting | Mode / Action | Acceptance Verification Criteria |
| :--- | :--- | :--- | :--- |
| `01-full-fixture-normal.png` | 1024×600 normal | Ensemble, Neutral, Idle | Full fixture surface, title, developer UI buttons, 6 characters, safe-area clear. |
| `02-five-states.png` | 1024×600 normal | Neutral, Blink, Happy, Surprised, Sleepy | 5-state composite proving all 30 expressions across all 6 canonical characters. |
| `03-happy-hop.png` | 1024×600 normal | Hero Flash, Happy, Hop | Flash mid-hop vertical lift with grounded contact shadow dynamic attenuation. |
| `04-surprised-wobble.png` | 1024×600 normal | Hero Dani, Surprised, Wobble | Dani floating with surprised face and smooth lateral recoil oscillation. |
| `05-sleepy-sway.png` | 1024×600 normal | Hero Momo, Sleepy, Sway | Momo eyes-closed gentle rhythmic lateral sway. |
| `06-state-fallback.png` | 1024×600 normal | Hero Flash, Happy (corrupt) | Clean fallback to neutral/default without crashing; bounded failure caching verified. |
| `07-default-failure.png` | 1024×600 normal | Hero Dani, Neutral (corrupt) | Deliberate Activity Visual Safe Fallback Mode box displayed; no traceback exposed. |
| `08-resp-1024x600-normal.png` | 1024×600 normal | Hero Mode | 1024×600 responsive hero viewport presentation. |
| `09-resp-1024x600-large.png` | 1024×600 normal | Ensemble Mode (Leo selected) | Ensemble viewport with Leo selected and Sway motion active. |
| `10-resp-1366x768-compact.png` | 1366×768 wide | Ensemble Mode Wide | 1366×768 viewport with uniform 1024×600 canvas containment and crisp rendering. |

---

## 3. Automated Test & Asset Validation Results

```text
make visual-assets
make visual-assets-check
pytest tests/test_scene*.py tests/test_visual*.py
```
- Asset hash validation: **PASS** (100%)
- Scene Actor & Bounded Cache unit tests: **PASS** (100% — 12/12 tests passing)
- Simulator trace: **52 trace events recorded in simulator-trace.json**
