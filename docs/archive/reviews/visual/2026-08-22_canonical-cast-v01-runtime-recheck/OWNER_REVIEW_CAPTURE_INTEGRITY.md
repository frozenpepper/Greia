# Owner Review — Canonical Cast v0.1 Runtime Recheck Capture Integrity

**Date:** 2026-08-22  
**Status:** NOT ACCEPTED — IMPLEMENTATION MAY BE CLOSE; EVIDENCE PACKAGE REQUIRES ONE FINAL ISOLATED CAPTURE PASS  
**Reviewed bundle:** `GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_RUNTIME_RECHECK_2026-08-22.zip`  
**Reviewed implementation commit:** `f1a9afe85c4fb6bd4a15d2bbea5c40835a8891ee`

## 1. Disposition

The recheck materially improves the implementation and evidence structure, but the runtime/simulator acceptance gate is **not closed** because the owner-transfer evidence is internally inconsistent with its own labels and audit claims.

Do **not** reopen character art or broadly refactor the renderer. The remaining work is primarily capture integrity, scenario isolation, and evidence/audit correctness. Preserve the useful bounded failed-rendition implementation unless the final recheck exposes a concrete defect.

## 2. Improvements accepted as useful source work

The following work is directionally correct and should be preserved:

- bounded failed-rendition memory in `PygameSceneRenderer`;
- clearing failed-rendition memory on `renderer.clear()`;
- use of the real canonical cast showcase fixture;
- fixture migration onto `PygameReferenceCanvas` / containment rather than ad-hoc display mapping;
- developer controls/status rendered on the actual fixture surface;
- narrow owner-transfer package rather than a source dump;
- continued use of the canonical six-character source/runtime family rather than another art pass.

These are source/implementation observations. Final simulator acceptance still depends on the corrected evidence gate below.

## 3. Evidence blockers found in the actual ZIP

### 3.1 `01-full-fixture-normal.png` is a failure state

The file is described as a clean six-character normal ensemble, but the actual image shows:

```text
Activity Visual Safe Fallback Mode
Required rendition failed: ... character.dani/default
```

A normal baseline capture cannot contain an injected/default failure.

### 3.2 `02-five-states.png` is contaminated

The composite is described as proof of all five states across all six characters. Its first rows instead contain the same Dani required-default fallback screen. Therefore it does not prove a clean 30-combination state matrix.

### 3.3 `04-surprised-wobble.png` has the wrong semantic state

The file is labeled Dani / surprised / surprised_wobble, but the actual fixture status shows `State: HAPPY` with `Motion: SURPRISED_WOBBLE`; Dani visually remains happy. This does not prove the intended state/motion pairing.

### 3.4 `05-sleepy-sway.png` has the wrong semantic state

The file is labeled Momo / sleepy / sleepy_sway, but the actual fixture status shows `State: HAPPY` with `Motion: SLEEPY_SWAY`; Momo visually remains happy. This does not prove the intended state/motion pairing.

### 3.5 `06-state-fallback.png` is not self-proving

The screenshot shows a live Flash hero surface but does not visibly establish that:

- `happy` was requested from a deliberately corrupt non-default rendition;
- that rendition failed;
- runtime actually rendered `default` instead;
- the fallback path was observed rather than merely inferred from the filename/trace.

Because this is a developer fixture, the final gate may add a small test-only/debug readout for requested variant, rendered variant, and whether fallback occurred. Do not add such diagnostic UI to normal child Activities.

### 3.6 `07-default-failure.png` is the wrong surface

The file is described as Dani's deliberate Activity-level safe fallback, but the actual image is the Greia `Starting...` surface. It was captured too early or from the wrong state and cannot prove required-default failure recovery.

### 3.7 Responsive captures do not prove the named interface modes

`09-resp-1024x600-large.png` visibly reports `UI: NORMAL`, not `LARGE`.

`10-resp-1366x768-compact.png` is transferred as a 1024×600 image and visibly reports `UI: NORMAL`, not `COMPACT`. A 1024×600 child/reference-surface capture can still be valid if the simulator intentionally exports the contained child surface, but then the trace/status must unambiguously prove the actual outer viewport and actual interface-size setting.

### 3.8 `runtime-audit.json` contains metadata drift

Examples include:

- a source-root value inconsistent with the promoted canonical path;
- role descriptions that drift from `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`;
- test-count wording inconsistent with the delivery summary.

The audit must report observed facts, not reconstructed approximations.

## 4. Root cause assessment

The evidence strongly suggests scenario contamination and/or capture-order mistakes rather than a need for another architectural rewrite:

- fault injection appears to have leaked into clean-state captures;
- screenshots were taken before the exact intended state was reached;
- filenames/claims were assigned without verifying the visible status line;
- responsive configurations were named without proving the actual UI-size setting;
- one required-default capture was taken on the launcher/start transition instead of the Activity fallback surface.

The next gate therefore requires **strict isolated phases and self-validating captures**.

## 5. Canonical next action

Execute only:

`docs/testing/2026-08-22_CANONICAL_CAST_V01_FINAL_CAPTURE_INTEGRITY.md`

Do not advance to Activity `lead_character` / `supporting_characters` metadata or another generic-art tranche until this gate is owner-reviewed.

If the final isolated capture pass is clean, canonical cast v0.1 simulator runtime acceptance may close without another broad implementation phase.
