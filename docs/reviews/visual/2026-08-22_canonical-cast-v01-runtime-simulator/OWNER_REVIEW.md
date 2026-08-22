# Canonical Cast v0.1 Runtime / Simulator — Owner Review

**Date:** 2026-08-22  
**Reviewed candidate commit:** `0ed5eba13f2edcfd62f1c4204311da1baa1dab46`  
**Reviewed transfer bundle:** `GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_RUNTIME_SIMULATOR_2026-08-22.zip`  
**Original execution gate:** `docs/testing/2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md`  
**Disposition:** **SOURCE PROMOTION ACCEPTED; RUNTIME/SIMULATOR ACCEPTANCE NOT YET CLOSED — FOCUSED RECHECK REQUIRED**

## 1. What is accepted from this tranche

The tranche made real, useful progress and should not be reverted or redrawn merely because the acceptance evidence has defects.

Accepted as source/implementation candidate work:

- the six current canonical IDs: `character.lilli`, `character.leo`, `character.flash`, `character.dani`, `character.tito`, `character.momo`;
- stable promoted source under `assets/visual/characters/canonical/v0.1/`;
- historical Nino provenance with Leo as the current owl identity and no silent seventh current mascot;
- the accepted white-rabbit Flash source identity;
- the five semantic source states per character: `neutral`, `blink`, `happy`, `surprised`, `sleepy`;
- the 30 explicit build-time 256×256 runtime PNG declarations/renditions;
- the renderer-neutral `CharacterState` / `CharacterMotion` direction;
- fixed-size whole-character x/y motion rather than skeletal rigs, runtime limb composition, continuous raster resizing or Pygame rotation churn;
- the developer-only canonical-cast showcase fixture as the correct kind of acceptance harness;
- the general `SceneNode.fallback_variant` direction rather than a character-specific parallel image loader.

The actual transferred ensemble/state/motion pixels also confirm that the six characters remain visually coherent after promotion. No new pure-art cast pass is requested.

## 2. Blocking runtime issue — failed state rendition is retried every frame

The original gate explicitly required:

> if a requested non-default state rendition is unavailable/corrupt, fall back once to neutral/default and avoid retrying a known corrupt state rendition every frame.

Current `PygameSceneRenderer.draw()` attempts `visual_cache.get(node.asset_id, variant=node.variant, size=...)` on every draw. When that fails and `fallback_variant` succeeds, the renderer does not remember that the primary rendition failed.

`PygameVisualSurfaceCache` caches successful surfaces only; it does not negative-cache failures.

Therefore a corrupt `flash_happy.png` can be decoded/failed again every frame before the renderer falls back to `default`. The screenshot proves the visible fallback result, but it does **not** prove the required bounded failure behavior.

This must be corrected with a small bounded renderer-level failed-rendition memory (or an equivalently clean bounded mechanism) keyed by semantic rendition + requested size. It must be cleared with the renderer/cache and must not become an unbounded set.

Required automated proof: draw the same scene repeatedly after one primary rendition failure and assert that the failed primary load is not retried on subsequent frames while the neutral/default fallback continues to render.

## 3. Blocking evidence issue — default-rendition failure proof is not a failure proof

The transferred `09-default-fallback.png` / raw `11-default-fallback.png` visibly contains Dani rendered normally with a non-neutral expression.

The committed fixture's `SceneRenderError` fallback path instead clears the screen and renders a `Visual Fallback Mode: ...` message. Therefore the supplied image cannot demonstrate the claimed `dani_neutral.png missing -> SceneRenderError caught and handled at Activity boundary` behavior.

The recheck must:

1. start with a cold/restarted renderer/simulator;
2. corrupt/move `dani_neutral.png`;
3. explicitly select Dani + semantic `neutral` / motion `none` (or another path that actually requests runtime `default`);
4. prove the required rendition fails;
5. show the Activity's deliberate local fallback without traceback/Linux error exposure;
6. restore generated assets and validate them afterward.

## 4. Blocking evidence provenance issue — transferred screenshots do not match the committed fixture surface

The committed showcase fixture draws a title, character selector buttons, view toggle, motion toggle, state controls, motion controls and status text after drawing the scene.

The transferred 1024×600 / responsive / motion screenshots contain only the character scene and meadow strip; none of those fixture controls are visible. In addition, the curated `01-ensemble.png` and `07-large.png` are byte-identical despite being described as normal vs large-interface evidence.

That means the transfer bundle does not establish that these images are screenshots of the committed fixture running through the real Activity Simulator source-loader path.

The recheck must use the actual simulator bridge (`tools/greia_simulator_ctl.py`) and preserve enough trace evidence to establish:

- the fixture folder was loaded through the canonical simulator workflow;
- the running Activity ID is the fixture Activity;
- the screenshot is the actual full child-facing Activity surface produced by that run;
- the developer controls/status are visible where expected;
- protected system-safe navigation territory is not overlapped;
- normal/large/compact rows are genuinely distinct executions rather than relabeled copies.

Do not create synthetic scene-only composites and label them simulator screenshots.

## 5. Fixture safe-area issue to inspect during recheck

The fixture currently computes `activity_viewport_for_surface(screen)` / `safe_ui_rect()` but does not use the safe rect for layout. It also imports `PygameReferenceCanvas` without using it and manually maps controls against the full display dimensions.

This may be harmless under one simulator composition, but the original gate required normal Greia canvas/responsive/system-safe primitives and explicit proof that fixture UI does not collide with protected Home/Back regions.

During the recheck, either:

- wire the developer controls through the existing safe viewport/reference-canvas conventions; or
- demonstrate from the actual simulator surface that the current layout already receives an Activity surface excluding protected chrome and is therefore correct.

Do not add simulator-specific production behavior.

## 6. Documentation drift introduced by the reported PASS

The runtime gate required updating all living visual authorities only according to actual evidence.

Current `main` is inconsistent:

- `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md` claims runtime simulator acceptance;
- `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` appends the runtime PASS;
- `HANDOVER.md` opens with the reported runtime PASS;
- but `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` still describes the obsolete four-character `Lilli / Nino / Tito / Momo` core cast;
- and `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` still points its current checkpoint/next exact action at the earlier generic-library admission/discovery gate rather than this canonical-cast recheck.

Do not paper over this by declaring the first run accepted. The recheck must synchronize the required authorities after the evidence is valid. Earlier chronology should remain append-only.

## 7. Transfer-bundle hygiene

The original owner-transfer contract required only the curated PNGs plus `REVIEW.md` and `runtime-audit.json`.

The supplied ZIP contains 113 files, including promoted source masters and all runtime renditions, and renames the required review/audit files to `PRIMARY_REVIEW.md` / `AUDIT.json`.

This does not invalidate the source work, but the recheck package should follow the narrow transfer contract so owner review is fast and unambiguous.

## 8. Recheck boundary

Do **not**:

- redraw the cast;
- change the accepted five-state vocabulary;
- add more mascot identities;
- add skeletal animation;
- add Activity lead/supporting-character manifest metadata yet;
- reopen generic Batch B;
- claim physical Acer/Pi acceptance.

The exact next gate is:

`docs/testing/2026-08-22_CANONICAL_CAST_V01_RUNTIME_ACCEPTANCE_RECHECK.md`

If that focused gate passes, canonical cast v0.1 may be marked **SIMULATOR VISUAL REVIEW accepted** and the workstream can move to a real Activity-authoring/integration exercise. Optional lead/supporting-character metadata should be considered from demonstrated product need rather than added automatically.